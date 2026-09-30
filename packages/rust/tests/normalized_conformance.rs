//! Host-only codec-v1 normalized Feature accounting; production stays `no_std`.
use ftms::{
    decode_features,
    normalized::{normalize_features, MachineFeature as M, TargetFeature as T},
};
use jsonschema::{Draft, JSONSchema};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::HashSet;
const SCHEMA: &str = include_str!("../../../shared/conformance/v1/schema.json");
const VECTORS: &str = include_str!("../../../shared/conformance/v1/vectors.json");
const CONTRACT: &str = include_str!("../../../shared/conformance/README.md");
fn hash(x: &str) -> String {
    format!("{:x}", Sha256::digest(x.as_bytes()))
}
fn enabled(f: &ftms::normalized::NormalizedFeatures, name: &str) -> bool {
    let (machine, bit) = match name {
        "averageSpeedSupported" => (true, 0),
        "cadenceSupported" => (true, 1),
        "totalDistanceSupported" => (true, 2),
        "inclinationSupported" => (true, 3),
        "elevationGainSupported" => (true, 4),
        "paceSupported" => (true, 5),
        "stepCountSupported" => (true, 6),
        "resistanceLevelSupported" => (true, 7),
        "strideCountSupported" => (true, 8),
        "expendedEnergySupported" => (true, 9),
        "heartRateMeasurementSupported" => (true, 10),
        "metabolicEquivalentSupported" => (true, 11),
        "elapsedTimeSupported" => (true, 12),
        "remainingTimeSupported" => (true, 13),
        "powerMeasurementSupported" => (true, 14),
        "forceOnBeltSupported" => (true, 15),
        "userDataRetentionSupported" => (true, 16),
        "speedTargetSettingSupported" => (false, 0),
        "inclinationTargetSettingSupported" => (false, 1),
        "resistanceTargetSettingSupported" => (false, 2),
        "powerTargetSettingSupported" => (false, 3),
        "heartRateTargetSettingSupported" => (false, 4),
        "targetedExpendedEnergySupported" => (false, 5),
        "targetedStepNumberSupported" => (false, 6),
        "targetedStrideNumberSupported" => (false, 7),
        "targetedDistanceSupported" => (false, 8),
        "targetedTrainingTimeSupported" => (false, 9),
        "targetedTimeTwoHRZonesSupported" => (false, 10),
        "targetedTimeThreeHRZonesSupported" => (false, 11),
        "targetedTimeFiveHRZonesSupported" => (false, 12),
        "indoorBikeSimulationSupported" => (false, 13),
        "wheelCircumferenceSupported" => (false, 14),
        "spinDownControlSupported" => (false, 15),
        "targetedCadenceSupported" => (false, 16),
        "supportsERG" => return f.supports_erg(),
        "supportsSIM" => return f.supports_sim(),
        "supportsResistance" => return f.supports_resistance(),
        _ => panic!("unknown feature {name}"),
    };
    let machines = [
        M::AverageSpeed,
        M::Cadence,
        M::TotalDistance,
        M::Inclination,
        M::ElevationGain,
        M::Pace,
        M::StepCount,
        M::ResistanceLevel,
        M::StrideCount,
        M::ExpendedEnergy,
        M::HeartRateMeasurement,
        M::MetabolicEquivalent,
        M::ElapsedTime,
        M::RemainingTime,
        M::PowerMeasurement,
        M::ForceOnBelt,
        M::UserDataRetention,
    ];
    let targets = [
        T::Speed,
        T::Inclination,
        T::Resistance,
        T::Power,
        T::HeartRate,
        T::ExpendedEnergy,
        T::StepNumber,
        T::StrideNumber,
        T::Distance,
        T::TrainingTime,
        T::TimeTwoHrZones,
        T::TimeThreeHrZones,
        T::TimeFiveHrZones,
        T::IndoorBikeSimulation,
        T::WheelCircumference,
        T::SpinDown,
        T::Cadence,
    ];
    if machine {
        f.supports_machine(machines[bit])
    } else {
        f.supports_target(targets[bit])
    }
}
fn compare(actual: bool, expected: bool) -> Result<(), String> {
    if actual == expected {
        Ok(())
    } else {
        Err(format!("expected {expected}, got {actual}"))
    }
}
#[test]
fn normalized_feature_v1_accounting() {
    let schema: Value = serde_json::from_str(SCHEMA).unwrap();
    let vectors: Value = serde_json::from_str(VECTORS).unwrap();
    JSONSchema::options()
        .with_draft(Draft::Draft202012)
        .compile(&schema)
        .unwrap()
        .validate(&vectors)
        .map_err(|e| e.map(|x| x.to_string()).collect::<Vec<_>>().join("; "))
        .unwrap();
    let mut ids = HashSet::new();
    let mut pass = 0;
    let mut failures = Vec::new();
    for c in vectors["features"].as_array().unwrap() {
        let id = c["id"].as_str().unwrap();
        assert!(ids.insert(id));
        let b = c["bytes"]
            .as_array()
            .unwrap()
            .iter()
            .map(|x| x.as_u64().unwrap() as u8)
            .collect::<Vec<_>>();
        let f = normalize_features(decode_features(&b).unwrap());
        if let Some(expected) = c.get("expected").and_then(Value::as_object) {
            for (name, value) in expected {
                if let Err(e) = compare(enabled(&f, name), value.as_bool().unwrap()) {
                    failures.push(format!("{id}.{name}: {e}"));
                }
            }
        } else {
            let actual = (0..37).filter(|_| false).count();
            let _ = actual;
            for name in c["expectedTrue"].as_array().unwrap() {
                if !enabled(&f, name.as_str().unwrap()) {
                    failures.push(format!("{id}.{} expected true", name.as_str().unwrap()));
                }
            }
        }
        pass += 1;
    }
    let total: usize = [
        "features",
        "ranges",
        "controls",
        "controlResponses",
        "measurements",
        "statuses",
        "diagnostics",
    ]
    .iter()
    .map(|k| vectors[*k].as_array().unwrap().len())
    .sum();
    eprintln!("FTMS Rust normalized codec-v1: schemaSha256={} vectorsSha256={} contractSha256={}; total={} passed={} failed={} unsupported={} skipped=0; supported=features:{}",hash(SCHEMA),hash(VECTORS),hash(CONTRACT),total,pass-failures.len(),failures.len(),total-ids.len(),ids.len());
    assert_eq!(ids.len(), 35);
    assert_eq!(total, 97);
    assert!(failures.is_empty(), "{}", failures.join("; "));
}
#[test]
fn normalized_feature_comparator_selftest() {
    assert!(compare(true, true).is_ok());
    assert!(compare(true, false).is_err());
}
