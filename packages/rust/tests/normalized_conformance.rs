//! Host-only codec-v1 adapter. Production projections remain allocation-free `no_std` APIs.
use ftms::{
    decode_control_response, decode_features, decode_range, measurement::*, normalized::*,
    status::*, ControlOptions, Error, RangeKind, RangeOptions,
};
use jsonschema::{Draft, JSONSchema};
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::{collections::HashSet, process::Command};

const SCHEMA: &str = include_str!("../../../shared/conformance/v1/schema.json");
const VECTORS: &str = include_str!("../../../shared/conformance/v1/vectors.json");
const CONTRACT: &str = include_str!("../../../shared/conformance/README.md");
const CATEGORIES: [&str; 7] = [
    "features",
    "ranges",
    "controls",
    "controlResponses",
    "measurements",
    "statuses",
    "diagnostics",
];
const COUNTS: [usize; 7] = [35, 7, 21, 12, 8, 4, 10];

fn hash(x: &str) -> String {
    format!("{:x}", Sha256::digest(x.as_bytes()))
}
fn bytes(c: &Value) -> Vec<u8> {
    c["bytes"]
        .as_array()
        .unwrap()
        .iter()
        .map(|v| v.as_u64().unwrap() as u8)
        .collect()
}
fn kind(s: &str) -> MeasurementKind {
    match s {
        "00002acd-0000-1000-8000-00805f9b34fb" => MeasurementKind::Treadmill,
        "00002ace-0000-1000-8000-00805f9b34fb" => MeasurementKind::CrossTrainer,
        "00002acf-0000-1000-8000-00805f9b34fb" => MeasurementKind::StepClimber,
        "00002ad0-0000-1000-8000-00805f9b34fb" => MeasurementKind::StairClimber,
        "00002ad1-0000-1000-8000-00805f9b34fb" => MeasurementKind::Rower,
        "00002ad2-0000-1000-8000-00805f9b34fb" => MeasurementKind::IndoorBike,
        _ => panic!("unknown UUID"),
    }
}
fn range_kind(s: &str) -> RangeKind {
    match s {
        "speed" => RangeKind::Speed,
        "inclination" => RangeKind::Inclination,
        "resistance" => RangeKind::Resistance,
        "heartRate" => RangeKind::HeartRate,
        "power" => RangeKind::Power,
        _ => panic!("unknown range"),
    }
}
fn error_code(e: Error) -> &'static str {
    match e {
        Error::WrongLength { .. } => "length",
        Error::InvalidRange => "range",
        _ => "malformed_response",
    }
}

// Exact objects/arrays, recursive subset objects, and metric tolerance deliberately
// live in this host adapter rather than weakening production result types.
fn exact(a: &Value, b: &Value) -> bool {
    match (a, b) {
        (Value::Object(a), Value::Object(b)) => {
            a.len() == b.len() && a.iter().all(|(k, v)| b.get(k).is_some_and(|x| exact(v, x)))
        }
        (Value::Array(a), Value::Array(b)) => {
            a.len() == b.len() && a.iter().zip(b).all(|(x, y)| exact(x, y))
        }
        (Value::Number(a), Value::Number(b)) => a.as_f64() == b.as_f64(),
        _ => a == b,
    }
}
fn subset(a: &Value, b: &Value) -> bool {
    match (a, b) {
        (Value::Object(expected), Value::Object(actual)) => expected
            .iter()
            .all(|(k, v)| actual.get(k).is_some_and(|x| subset(v, x))),
        (Value::Array(expected), Value::Array(actual)) => {
            expected.len() == actual.len() && expected.iter().zip(actual).all(|(x, y)| subset(x, y))
        }
        _ => exact(a, b),
    }
}
fn metric(actual: Option<Value>, expected: &Value) -> bool {
    match (actual, expected) {
        (Some(Value::Number(a)), Value::Number(b)) => match (a.as_f64(), b.as_f64()) {
            (Some(x), Some(y)) => x.is_finite() && (x - y).abs() < 0.005,
            _ => false,
        },
        (Some(a), b) => &a == b,
        _ => false,
    }
}

fn feature_value(f: NormalizedFeatures, name: &str) -> bool {
    let machine = [
        MachineFeature::AverageSpeed,
        MachineFeature::Cadence,
        MachineFeature::TotalDistance,
        MachineFeature::Inclination,
        MachineFeature::ElevationGain,
        MachineFeature::Pace,
        MachineFeature::StepCount,
        MachineFeature::ResistanceLevel,
        MachineFeature::StrideCount,
        MachineFeature::ExpendedEnergy,
        MachineFeature::HeartRateMeasurement,
        MachineFeature::MetabolicEquivalent,
        MachineFeature::ElapsedTime,
        MachineFeature::RemainingTime,
        MachineFeature::PowerMeasurement,
        MachineFeature::ForceOnBelt,
        MachineFeature::UserDataRetention,
    ];
    let target = [
        TargetFeature::Speed,
        TargetFeature::Inclination,
        TargetFeature::Resistance,
        TargetFeature::Power,
        TargetFeature::HeartRate,
        TargetFeature::ExpendedEnergy,
        TargetFeature::StepNumber,
        TargetFeature::StrideNumber,
        TargetFeature::Distance,
        TargetFeature::TrainingTime,
        TargetFeature::TimeTwoHrZones,
        TargetFeature::TimeThreeHrZones,
        TargetFeature::TimeFiveHrZones,
        TargetFeature::IndoorBikeSimulation,
        TargetFeature::WheelCircumference,
        TargetFeature::SpinDown,
        TargetFeature::Cadence,
    ];
    let names = [
        "averageSpeedSupported",
        "cadenceSupported",
        "totalDistanceSupported",
        "inclinationSupported",
        "elevationGainSupported",
        "paceSupported",
        "stepCountSupported",
        "resistanceLevelSupported",
        "strideCountSupported",
        "expendedEnergySupported",
        "heartRateMeasurementSupported",
        "metabolicEquivalentSupported",
        "elapsedTimeSupported",
        "remainingTimeSupported",
        "powerMeasurementSupported",
        "forceOnBeltSupported",
        "userDataRetentionSupported",
        "speedTargetSettingSupported",
        "inclinationTargetSettingSupported",
        "resistanceTargetSettingSupported",
        "powerTargetSettingSupported",
        "heartRateTargetSettingSupported",
        "targetedExpendedEnergySupported",
        "targetedStepNumberSupported",
        "targetedStrideNumberSupported",
        "targetedDistanceSupported",
        "targetedTrainingTimeSupported",
        "targetedTimeTwoHRZonesSupported",
        "targetedTimeThreeHRZonesSupported",
        "targetedTimeFiveHRZonesSupported",
        "indoorBikeSimulationSupported",
        "wheelCircumferenceSupported",
        "spinDownControlSupported",
        "targetedCadenceSupported",
    ];
    if let Some(i) = names.iter().position(|x| *x == name) {
        return if i < 17 {
            f.supports_machine(machine[i])
        } else {
            f.supports_target(target[i - 17])
        };
    }
    match name {
        "supportsERG" => f.supports_erg(),
        "supportsSIM" => f.supports_sim(),
        "supportsResistance" => f.supports_resistance(),
        _ => panic!("unknown feature mapping {name}"),
    }
}
fn feature_json(f: NormalizedFeatures) -> Value {
    let mut m = Map::new();
    for n in [
        "averageSpeedSupported",
        "cadenceSupported",
        "totalDistanceSupported",
        "inclinationSupported",
        "elevationGainSupported",
        "paceSupported",
        "stepCountSupported",
        "resistanceLevelSupported",
        "strideCountSupported",
        "expendedEnergySupported",
        "heartRateMeasurementSupported",
        "metabolicEquivalentSupported",
        "elapsedTimeSupported",
        "remainingTimeSupported",
        "powerMeasurementSupported",
        "forceOnBeltSupported",
        "userDataRetentionSupported",
        "speedTargetSettingSupported",
        "inclinationTargetSettingSupported",
        "resistanceTargetSettingSupported",
        "powerTargetSettingSupported",
        "heartRateTargetSettingSupported",
        "targetedExpendedEnergySupported",
        "targetedStepNumberSupported",
        "targetedStrideNumberSupported",
        "targetedDistanceSupported",
        "targetedTrainingTimeSupported",
        "targetedTimeTwoHRZonesSupported",
        "targetedTimeThreeHRZonesSupported",
        "targetedTimeFiveHRZonesSupported",
        "indoorBikeSimulationSupported",
        "wheelCircumferenceSupported",
        "spinDownControlSupported",
        "targetedCadenceSupported",
        "supportsERG",
        "supportsSIM",
        "supportsResistance",
    ] {
        m.insert(n.into(), Value::Bool(feature_value(f, n)));
    }
    Value::Object(m)
}

fn control(r: &Value) -> NormalizedControlRequest {
    let op = r["op"].as_str().unwrap();
    match op {
        "requestControl" => NormalizedControlRequest::RequestControl,
        "reset" => NormalizedControlRequest::Reset,
        "setTargetSpeed" => {
            NormalizedControlRequest::TargetSpeedKph(r["speedKph"].as_f64().unwrap() as f32)
        }
        "setTargetInclination" => NormalizedControlRequest::TargetInclinationPercent(
            r["inclinationPercent"].as_f64().unwrap() as f32,
        ),
        "setTargetResistance" => NormalizedControlRequest::TargetResistanceLevel(
            r["resistanceLevel"].as_f64().unwrap() as f32,
        ),
        "setTargetPower" => {
            NormalizedControlRequest::TargetPowerWatts(r["powerWatts"].as_i64().unwrap() as i16)
        }
        "setTargetHeartRate" => {
            NormalizedControlRequest::TargetHeartRateBpm(r["heartRateBpm"].as_u64().unwrap() as u8)
        }
        "startResume" => NormalizedControlRequest::StartResume,
        "stopPause" => NormalizedControlRequest::StopPause {
            action: if r["action"] == "pause" { 2 } else { 1 },
        },
        "setTargetedExpendedEnergy" => {
            NormalizedControlRequest::TargetEnergyKcal(r["energyKcal"].as_u64().unwrap() as u16)
        }
        "setTargetedSteps" => {
            NormalizedControlRequest::TargetSteps(r["steps"].as_u64().unwrap() as u16)
        }
        "setTargetedStrides" => {
            NormalizedControlRequest::TargetStrides(r["strides"].as_u64().unwrap() as u16)
        }
        "setTargetedDistance" => NormalizedControlRequest::TargetDistanceMetres(
            r["distanceMeters"].as_u64().unwrap() as u32,
        ),
        "setTargetedTrainingTime" => {
            NormalizedControlRequest::TargetTrainingSeconds(r["seconds"].as_u64().unwrap() as u16)
        }
        "setTargetedTimeTwoHrZones" => {
            let x = r["seconds"].as_array().unwrap();
            NormalizedControlRequest::TargetTimeTwoHrZones([
                x[0].as_u64().unwrap() as u16,
                x[1].as_u64().unwrap() as u16,
            ])
        }
        "setTargetedTimeThreeHrZones" => {
            let x = r["seconds"].as_array().unwrap();
            NormalizedControlRequest::TargetTimeThreeHrZones([
                x[0].as_u64().unwrap() as u16,
                x[1].as_u64().unwrap() as u16,
                x[2].as_u64().unwrap() as u16,
            ])
        }
        "setTargetedTimeFiveHrZones" => {
            let x = r["seconds"].as_array().unwrap();
            NormalizedControlRequest::TargetTimeFiveHrZones([
                x[0].as_u64().unwrap() as u16,
                x[1].as_u64().unwrap() as u16,
                x[2].as_u64().unwrap() as u16,
                x[3].as_u64().unwrap() as u16,
                x[4].as_u64().unwrap() as u16,
            ])
        }
        "setIndoorBikeSimulation" => NormalizedControlRequest::IndoorBikeSimulation {
            wind_speed_mps: r["windSpeedMps"].as_f64().unwrap() as f32,
            grade_percent: r["gradePercent"].as_f64().unwrap() as f32,
            crr: r["crr"].as_f64().unwrap() as f32,
            cw_kg_per_m: r["cwKgPerM"].as_f64().unwrap() as f32,
        },
        "setWheelCircumference" => NormalizedControlRequest::WheelCircumferenceMm(
            r["circumferenceMm"].as_u64().unwrap() as u16,
        ),
        "spinDown" => NormalizedControlRequest::SpinDown {
            action: if r["action"] == "ignore" { 2 } else { 1 },
        },
        "setTargetedCadence" => {
            NormalizedControlRequest::TargetCadenceRpm(r["cadenceRpm"].as_f64().unwrap() as f32)
        }
        _ => panic!("unknown control {op}"),
    }
}
fn metric_name(s: &str) -> Option<Metric> {
    Some(match s {
        "speedMps" => Metric::SpeedMetresPerSecond,
        "averageSpeedMps" => Metric::AverageSpeedMetresPerSecond,
        "distanceMeters" => Metric::DistanceMetres,
        "inclinationPercent" => Metric::InclinationPercent,
        "rampAngleDegrees" => Metric::RampAngleDegrees,
        "positiveElevationGainMeters" => Metric::PositiveElevationMetres,
        "negativeElevationGainMeters" => Metric::NegativeElevationMetres,
        "instantaneousPaceSecondsPer500m" => Metric::InstantaneousPaceSecondsPer500Metres,
        "averagePaceSecondsPer500m" => Metric::AveragePaceSecondsPer500Metres,
        "energyKcal" => Metric::EnergyKcal,
        "energyPerHourKcal" => Metric::EnergyPerHourKcal,
        "energyPerMinuteKcal" => Metric::EnergyPerMinuteKcal,
        "hrBpm" => Metric::HeartRateBpm,
        "metabolicEquivalent" => Metric::MetabolicEquivalent,
        "elapsedTimeSeconds" => Metric::ElapsedSeconds,
        "remainingTimeSeconds" => Metric::RemainingSeconds,
        "forceOnBeltNewtons" => Metric::ForceNewtons,
        "powerWatts" => Metric::PowerWatts,
        "averagePowerWatts" => Metric::AveragePowerWatts,
        "stepRateSpm" => Metric::StepRatePerMinute,
        "averageStepRateSpm" => Metric::AverageStepRatePerMinute,
        "strideCount" => Metric::StrideCount,
        "resistanceLevel" => Metric::ResistanceLevel,
        "floorCount" => Metric::FloorCount,
        "stepCount" => Metric::StepCount,
        "strokeRateSpm" => Metric::StrokeRatePerMinute,
        "strokeCount" => Metric::StrokeCount,
        "averageStrokeRateSpm" => Metric::AverageStrokeRatePerMinute,
        "cadenceRpm" => Metric::CadenceRpm,
        "averageCadenceRpm" => Metric::AverageCadenceRpm,
        _ => return None,
    })
}
fn normalized_metric(m: &RawMeasurement, name: &str) -> Option<Value> {
    if name == "movementDirection" {
        return Some(Value::String(
            if m.backward { "backward" } else { "forward" }.into(),
        ));
    }
    let x = normalized_measurement(m, MeasurementOptions::default(), metric_name(name)?);
    match x {
        None | Some(NormalizedValue::Unavailable) => Some(Value::Null),
        Some(NormalizedValue::UnknownUnit) => None,
        Some(NormalizedValue::Number(v)) => Some(json!(v)),
    }
}
#[test]
fn normalized_codec_v1_all_cases() {
    let schema: Value = serde_json::from_str(SCHEMA).unwrap();
    let vectors: Value = serde_json::from_str(VECTORS).unwrap();
    JSONSchema::options()
        .with_draft(Draft::Draft202012)
        .compile(&schema)
        .unwrap()
        .validate(&vectors)
        .map_err(|e| e.map(|x| x.to_string()).collect::<Vec<_>>().join("; "))
        .unwrap();
    assert_eq!(vectors["schemaVersion"], 1);
    let mut ids = HashSet::new();
    let mut failures = Vec::new();
    let mut passed = 0;
    for (category, expected_count) in CATEGORIES.iter().zip(COUNTS) {
        let cases = vectors[*category].as_array().unwrap();
        assert_eq!(cases.len(), expected_count);
        for c in cases {
            let id = c["id"].as_str().unwrap();
            assert!(ids.insert(id), "duplicate ID {id}");
            record_case(id, &mut passed, &mut failures, || {
                let result: Result<(), String> = match *category {
                    "features" => {
                        let actual =
                            feature_json(normalize_features(decode_features(&bytes(c)).unwrap()));
                        if let Some(e) = c.get("expected") {
                            if exact(&actual, e) {
                                Ok(())
                            } else {
                                Err(format!("exact feature mismatch: {actual}"))
                            }
                        } else {
                            let true_set: HashSet<_> = actual
                                .as_object()
                                .unwrap()
                                .iter()
                                .filter_map(|(k, v)| v.as_bool().filter(|x| *x).map(|_| k.as_str()))
                                .collect();
                            let expected: HashSet<_> = c["expectedTrue"]
                                .as_array()
                                .unwrap()
                                .iter()
                                .map(|v| v.as_str().unwrap())
                                .collect();
                            if true_set == expected {
                                Ok(())
                            } else {
                                Err("expectedTrue set mismatch".into())
                            }
                        }
                    }
                    "ranges" => match decode_range(
                        range_kind(c["kind"].as_str().unwrap()),
                        &bytes(c),
                        RangeOptions::default(),
                    ) {
                        Ok(raw) => {
                            let r = normalize_range(raw);
                            let a = json!({"kind":c["kind"],"min":r.minimum,"max":r.maximum,"increment":r.increment,"unit":match raw.unit { ftms::RangeUnit::KilometresPerHour=>"km/h",ftms::RangeUnit::Percent=>"percent",ftms::RangeUnit::Level=>"level",ftms::RangeUnit::BeatsPerMinute=>"bpm",ftms::RangeUnit::Watts=>"watts"}});
                            if exact(
                                &a,
                                &json!({"kind":c["kind"],"min":c["expected"]["min"],"max":c["expected"]["max"],"increment":c["expected"]["increment"],"unit":c["expected"]["unit"]}),
                            ) {
                                Ok(())
                            } else {
                                Err("exact range mismatch".into())
                            }
                        }
                        Err(e) => {
                            if subset(
                                &json!({"ok":false,"code":c["expectedError"]}),
                                &json!({"ok":false,"code":error_code(e)}),
                            ) {
                                Ok(())
                            } else {
                                Err("range error mismatch".into())
                            }
                        }
                    },
                    "controls" => {
                        let raw = normalize_control_request(control(&c["request"])).unwrap();
                        let mut out = [0; 11];
                        let n =
                            ftms::encode_control_request(raw, ControlOptions::default(), &mut out)
                                .unwrap();
                        if exact(&json!(&out[..n]), &c["expectedBytes"]) {
                            Ok(())
                        } else {
                            Err("control bytes mismatch".into())
                        }
                    }
                    "controlResponses" => {
                        match decode_control_response(&bytes(c))
                            .and_then(normalize_control_response)
                        {
                            Ok(r) if c.get("expected").is_some() => {
                                let p = match r.spin_down_speeds_kph {
                                    Some((l, h)) => {
                                        json!({"kind":"spin_down_speeds","targetSpeedLowKph":l,"targetSpeedHighKph":h})
                                    }
                                    None => json!({"kind":"none"}),
                                };
                                let name = match r.result_code {
                                    1 => "success".into(),
                                    2 => "not_supported".into(),
                                    3 => "invalid_parameter".into(),
                                    4 => "operation_failed".into(),
                                    5 => "control_not_permitted".into(),
                                    x => format!("unknown_0x{x:02x}"),
                                };
                                let a = json!({"requestOpCode":r.request_opcode,"resultCode":r.result_code,"resultCodeName":name,"success":r.result_code==1,"parameter":p,"issues":if r.unknown_result {json!(["reserved_value"])}else{json!([])}});
                                if exact(&a, &c["expected"]) {
                                    Ok(())
                                } else {
                                    Err("exact response mismatch".into())
                                }
                            }
                            Ok(_) => Err("invalid response accepted".into()),
                            Err(_) if c.get("expectedError").is_some() => {
                                let actual = json!({"ok":false,"code":"malformed_response"});
                                let expected = json!({"ok":false,"code":c["expectedError"]});
                                if subset(&expected, &actual) {
                                    Ok(())
                                } else {
                                    Err("response error mismatch".into())
                                }
                            }
                            Err(e) => Err(format!("unexpected response error {e:?}")),
                        }
                    }
                    "measurements" => {
                        let m = decode_measurement(
                            kind(c["characteristicUuid"].as_str().unwrap()),
                            &bytes(c),
                            MeasurementOptions::default(),
                        )
                        .unwrap();
                        let ok = c["expectedMetrics"]
                            .as_object()
                            .unwrap()
                            .iter()
                            .all(|(n, e)| metric(normalized_metric(&m, n), e));
                        if ok {
                            Ok(())
                        } else {
                            Err("measurement metric mismatch".into())
                        }
                    }
                    "statuses" => {
                        let b = bytes(c);
                        let e = &c["expectedStatus"];
                        let a = if c["characteristicUuid"].as_str().unwrap().contains("2ad3") {
                            let s = decode_training_status(&b);
                            json!({"code":s.code,"label":match s.code {13=>"manual_mode",_=>"unknown"},"details":{"kind":"training_status","flags":s.flags,"stringPresent":s.text_present,"extendedStringPresent":s.extended_string,"trainingStatusString":core::str::from_utf8(s.text).ok()}})
                        } else {
                            let s = decode_machine_status(&b);
                            let normalized = normalize_machine_status(s).unwrap();
                            let details = match s.parameter {
                                Some(p) if s.opcode == 5 => {
                                    json!({"kind":"speed","speedKph":p.operands[0] as f64/100.0})
                                }
                                Some(p) if s.opcode == 18 => {
                                    json!({"kind":"simulation","windSpeedMps":p.operands[0] as f64/1000.0,"gradePercent":p.operands[1] as f64/100.0,"crr":p.operands[2] as f64/10000.0,"cwKgPerM":p.operands[3] as f64/100.0})
                                }
                                _ => json!({"kind":"none"}),
                            };
                            json!({"code":normalized.code,"label":normalized.label,"details":details})
                        };
                        if subset(e, &a) {
                            Ok(())
                        } else {
                            Err("status subset mismatch".into())
                        }
                    }
                    "diagnostics" => {
                        let b = bytes(c);
                        let uuid = c["characteristicUuid"].as_str().unwrap();
                        let (truncated, issues, status, metrics) = if uuid.contains("2ad3") {
                            let s = decode_training_status(&b);
                            (
                                s.truncated,
                                vec![
                                    (s.reserved_flags != 0, "reserved_flags"),
                                    (s.invalid_flags, "invalid_flags"),
                                    (s.reserved_value, "reserved_value"),
                                    (s.truncated, "truncated"),
                                ],
                                Some(s.code),
                                Map::new(),
                            )
                        } else if uuid.contains("2ada") {
                            let s = decode_machine_status(&b);
                            (
                                s.truncated,
                                vec![
                                    (s.unknown_opcode, "unknown_opcode"),
                                    (s.reserved_value, "reserved_value"),
                                    (s.truncated, "truncated"),
                                ],
                                if b.is_empty() { None } else { Some(s.opcode) },
                                Map::new(),
                            )
                        } else {
                            let m =
                                decode_measurement(kind(uuid), &b, MeasurementOptions::default())
                                    .unwrap();
                            let mut map = Map::new();
                            for n in c["expectedMetrics"]
                                .as_object()
                                .unwrap_or(&Map::new())
                                .keys()
                            {
                                map.insert(
                                    n.clone(),
                                    normalized_metric(&m, n).unwrap_or(Value::Null),
                                );
                            }
                            (
                                m.truncated,
                                vec![
                                    (m.flags & 1 != 0, "more_data"),
                                    (m.unavailable != 0, "unavailable"),
                                    (m.trailing_bytes, "trailing_bytes"),
                                    (m.reserved_flags, "reserved_flags"),
                                    (m.truncated, "truncated"),
                                ],
                                None,
                                map,
                            )
                        };
                        let got: HashSet<_> = issues
                            .into_iter()
                            .filter_map(|(yes, n)| yes.then_some(n))
                            .collect();
                        let wanted: HashSet<_> = c["expectedIssues"]
                            .as_array()
                            .unwrap()
                            .iter()
                            .map(|v| v.as_str().unwrap())
                            .collect();
                        let ok = truncated == c["expectedTruncated"].as_bool().unwrap()
                            && wanted.is_subset(&got)
                            && c.get("expectedStatusCode").is_none_or(|x| {
                                status.map(Value::from).unwrap_or(Value::Null) == *x
                            })
                            && c["expectedMetrics"]
                                .as_object()
                                .map(|x| x.iter().all(|(n, e)| metric(metrics.get(n).cloned(), e)))
                                .unwrap_or(true);
                        if ok {
                            Ok(())
                        } else {
                            Err("diagnostic mismatch".into())
                        }
                    }
                    _ => unreachable!(),
                };
                result
            });
        }
    }
    let head = Command::new("git")
        .args(["rev-parse", "HEAD"])
        .output()
        .ok()
        .and_then(|x| String::from_utf8(x.stdout).ok())
        .unwrap_or_else(|| "unknown".into());
    let dirty = Command::new("git")
        .args(["status", "--porcelain"])
        .output()
        .ok()
        .is_some_and(|x| !x.stdout.is_empty());
    let nonpasses = if failures.is_empty() {
        "none".into()
    } else {
        failures.join(" | ")
    };
    eprintln!("FTMS Rust normalized codec-v1: head={} dirty={} schemaVersion=1 schemaSha256={} vectorsSha256={} contractSha256={}; total=97 passed={} failed={} unsupported=0 skipped=0; categories=features:35,ranges:7,controls:21,controlResponses:12,measurements:8,statuses:4,diagnostics:10; nonpasses={}",head.trim(),dirty,hash(SCHEMA),hash(VECTORS),hash(CONTRACT),passed,failures.len(),nonpasses);
    assert_eq!(ids.len(), 97);
    assert!(failures.is_empty(), "{}", failures.join("; "));
}

#[test]
fn comparator_selftests_reject_contract_violations() {
    assert!(!exact(&json!(false), &json!(true))); // negative value mismatch
    assert!(!exact(&json!({"a":true}), &json!({"a":true,"b":false}))); // extra exact key
    assert!(!subset(&json!({"a":null}), &json!({}))); // null is not missing
    assert!(!subset(&json!([1, 2]), &json!([2, 1]))); // arrays preserve order
    assert!(!metric(Some(json!(0.005)), &json!(0.0))); // tolerance boundary fails
    assert!(!metric(None, &json!(0))); // zero is required
    assert!(!subset(
        &json!({"ok":false,"code":"malformed_response"}),
        &json!({"ok":false,"code":"length"})
    ));
    assert!(normalize_control_request(NormalizedControlRequest::TargetSpeedKph(655.36)).is_err());
    assert!(
        normalize_control_request(NormalizedControlRequest::TargetDistanceMetres(1 << 24)).is_err()
    );
    assert!(
        normalize_control_request(NormalizedControlRequest::WheelCircumferenceMm(6554)).is_err()
    );
    assert!(
        normalize_control_request(NormalizedControlRequest::IndoorBikeSimulation {
            wind_speed_mps: 0.0,
            grade_percent: 0.0,
            crr: 0.0256,
            cw_kg_per_m: 0.0
        })
        .is_err()
    );
    assert!(normalize_control_request(NormalizedControlRequest::TargetSpeedKph(f32::NAN)).is_err());
    assert!(normalize_control_request(NormalizedControlRequest::TargetSpeedKph(1.234)).is_err());
    assert!(normalize_control_request(NormalizedControlRequest::StopPause { action: 0 }).is_err());
    assert!(normalize_control_request(NormalizedControlRequest::SpinDown { action: 0 }).is_err());
    assert_eq!(
        normalize_control_request(NormalizedControlRequest::SpinDown { action: 2 })
            .unwrap()
            .operands[0],
        2
    );
}

fn record_case(
    id: &str,
    passed: &mut usize,
    failures: &mut Vec<String>,
    run: impl FnOnce() -> Result<(), String>,
) {
    match std::panic::catch_unwind(std::panic::AssertUnwindSafe(run)) {
        Ok(Ok(())) => *passed += 1,
        Ok(Err(e)) => failures.push(format!("{id}: {e}")),
        Err(_) => failures.push(format!("{id}: runner panic")),
    }
}

#[test]
fn runner_retains_failures_and_continues_after_panics() {
    let mut passed = 0;
    let mut failures = Vec::new();
    record_case("panic", &mut passed, &mut failures, || panic!("injected"));
    record_case("mismatch", &mut passed, &mut failures, || {
        Err("wrong code".into())
    });
    record_case("after", &mut passed, &mut failures, || Ok(()));
    assert_eq!(passed, 1);
    assert_eq!(failures, ["panic: runner panic", "mismatch: wrong code"]);
    assert_eq!(passed + failures.len(), 3);
}

#[test]
fn normalized_controls_accept_wire_grid_and_preserve_status_actions() {
    for wire in 0..=u16::MAX {
        let raw = normalize_control_request(NormalizedControlRequest::TargetSpeedKph(
            f32::from(wire) / 100.0,
        ))
        .unwrap();
        assert_eq!(raw.operands[0], i32::from(wire));
    }
    for wire in i16::MIN..=i16::MAX {
        let raw = normalize_control_request(NormalizedControlRequest::TargetResistanceLevel(
            f32::from(wire) / 10.0,
        ))
        .unwrap();
        assert_eq!(raw.operands[0], i32::from(wire));
    }
    for value in [f32::INFINITY, f32::NEG_INFINITY, -0.01, 0.305, 655.36] {
        assert!(
            normalize_control_request(NormalizedControlRequest::TargetSpeedKph(value)).is_err()
        );
    }
    for (opcode, max_action) in [(2, 2), (20, 4)] {
        for action in 1..=max_action {
            let view = normalize_machine_status(decode_machine_status(&[opcode, action])).unwrap();
            assert_eq!(view.action, Some(action));
        }
    }
    let mut response = decode_control_response(&[0x80, 5, 1]).unwrap();
    response.parameter = 1;
    assert!(normalize_control_response(response).is_err());
    response.request_opcode = 19;
    assert!(normalize_control_response(response).is_ok());
    response.result_code = 2;
    assert!(normalize_control_response(response).is_err());
    response.parameter = 2;
    assert!(normalize_control_response(response).is_err());
}
