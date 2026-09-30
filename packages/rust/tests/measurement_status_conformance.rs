mod support;

use ftms::{measurement::*, status::*, ControlRequest, Error};
use serde_json::{json, Value};
use support::*;

const MS: &str = include_str!("../../../shared/conformance/measurements/v1/schema.json");
const MV: &str = include_str!("../../../shared/conformance/measurements/v1/vectors.json");
const MC: &str = include_str!("../../../shared/conformance/measurements/README.md");
const SS: &str = include_str!("../../../shared/conformance/statuses/v1/schema.json");
const SV: &str = include_str!("../../../shared/conformance/statuses/v1/vectors.json");
const SC: &str = include_str!("../../../shared/conformance/statuses/README.md");
const CS: &str = include_str!("../../../shared/conformance/compatibility/v1/schema.json");
const CV: &str = include_str!("../../../shared/conformance/compatibility/v1/vectors.json");
const CC: &str = include_str!("../../../shared/conformance/compatibility/README.md");

#[test]
fn measurement_literal_directions() {
    let data = corpus(MS, MV);
    let cases = data["cases"].as_array().unwrap();
    unique(cases);
    let mut report = Report::default();
    for case in cases {
        let id = case["id"].as_str().unwrap();
        let category = format!("kind-{}", case["kind"]);
        report.run(id, &category, "decode", || {
            let bytes = bytes(&case["bytes"]);
            let got = measurement_kind(&case["kind"])
                .and_then(|kind| decode_measurement(kind, &bytes, MeasurementOptions::default()));
            let json = match got {
                Ok(m) => measurement_json(m),
                Err(Error::InvalidKind) => json!({"error":3}),
                Err(Error::WrongLength { .. }) => json!({"error":2}),
                Err(e) => panic!("unexpected decoder error {e:?}"),
            };
            assert_eq!(json, case["decoded"]);
        });
        if case["encode"] == true {
            report.run(id, &category, "encode", || {
                let mut out = [0xa5; 64];
                let n = encode_measurement(
                    &raw_measurement(&case["decoded"]),
                    MeasurementOptions::default(),
                    &mut out,
                )
                .unwrap();
                assert_eq!(&out[..n], bytes(&case["bytes"]));
                assert!(out[n..].iter().all(|b| *b == 0xa5));
            });
        }
    }
    report.finish("measurements/v1", Some(MS), MV, MC, 26, 47);
}

fn control_parameter(v: &Value) -> Option<ControlRequest> {
    if v.is_null() {
        return None;
    }
    let raw = v["operands"].as_array().unwrap();
    let mut operands = [0; 5];
    for (dest, value) in operands.iter_mut().zip(raw) {
        *dest = i32::try_from(value.as_i64().unwrap()).unwrap();
    }
    Some(ControlRequest {
        opcode: u8::try_from(number(&v["opcode"])).unwrap(),
        operands,
        operand_count: raw.len(),
    })
}
fn machine(v: &Value) -> RawMachineStatus {
    RawMachineStatus {
        opcode: number(&v["opcode"]) as u8,
        action: number(&v["action"]) as u8,
        parameter: control_parameter(&v["parameter"]),
        unknown_opcode: number(&v["unknownOpcode"]) == 1,
        reserved_value: number(&v["reservedValue"]) == 1,
        truncated: number(&v["truncated"]) == 1,
        trailing_bytes: number(&v["trailingBytes"]) == 1,
    }
}
fn machine_json(v: RawMachineStatus) -> Value {
    json!({"opcode":v.opcode,"action":v.action,"parameter":v.parameter.map(|p| json!({"opcode":p.opcode,"operands":p.operands[..p.operand_count]})),
        "unknownOpcode":u8::from(v.unknown_opcode),"reservedValue":u8::from(v.reserved_value),"truncated":u8::from(v.truncated),"trailingBytes":u8::from(v.trailing_bytes)})
}
fn training_json(v: RawTrainingStatus<'_>) -> Value {
    json!({"flags":v.flags,"code":v.code,"textOffset":v.text_offset,"textSize":v.text.len(),"textHex":hex(v.text),
        "textPresent":u8::from(v.text_present),"extendedString":u8::from(v.extended_string),
        "reservedValue":u8::from(v.reserved_value),"invalidFlags":u8::from(v.invalid_flags),
        "invalidUtf8":u8::from(v.invalid_utf8),"truncated":u8::from(v.truncated),
        "trailingBytes":u8::from(v.trailing_bytes),"reservedFlags":v.reserved_flags})
}

#[test]
fn status_literal_directions() {
    let data = corpus(SS, SV);
    let cases: Vec<_> = data["machine"]
        .as_array()
        .unwrap()
        .iter()
        .chain(data["training"].as_array().unwrap())
        .cloned()
        .collect();
    unique(&cases);
    let mut report = Report::default();
    for case in &cases {
        let id = case["id"].as_str().unwrap();
        let category = case["operation"].as_str().unwrap();
        report.run(id, category, "decode", || {
            let b = bytes(&case["bytes"]);
            let actual = if category == "machine" {
                machine_json(decode_machine_status(&b))
            } else {
                training_json(decode_training_status(&b))
            };
            assert_eq!(actual, case["decoded"]);
        });
        if case["encode"] == true {
            report.run(id, category, "encode", || {
                let mut out = [0xa5; 64];
                let d = &case["decoded"];
                let n = if category == "machine" {
                    encode_machine_status(&machine(d), &mut out).unwrap()
                } else {
                    let text = unhex(&d["textHex"]);
                    let value = RawTrainingStatus {
                        flags: number(&d["flags"]) as u8,
                        code: number(&d["code"]) as u8,
                        text: &text,
                        ..RawTrainingStatus::default()
                    };
                    encode_training_status(&value, &mut out).unwrap()
                };
                assert_eq!(&out[..n], bytes(&case["bytes"]));
                assert!(out[n..].iter().all(|b| *b == 0xa5));
            });
        }
    }
    report.finish("statuses/v1", Some(SS), SV, SC, 38, 63);
}

#[test]
fn explicit_compatibility_profiles() {
    // Include the already implemented Range variants so the entire corpus is
    // accounted for. Neither measurement nor range options select each other.
    let data = corpus(CS, CV);
    let cases = data["cases"].as_array().unwrap();
    unique(cases);
    let mut report = Report::default();
    for case in cases {
        let id = case["id"].as_str().unwrap();
        let area = case["area"].as_str().unwrap();
        for direction in ["encode", "decode"] {
            report.run(id, area, direction, || {
                let b = bytes(&case["bytes"]);
                if area == "measurement" {
                    let opts = options(&case["options"]);
                    if direction == "decode" {
                        assert_eq!(
                            measurement_json(
                                decode_measurement(
                                    measurement_kind(&case["kind"]).unwrap(),
                                    &b,
                                    opts
                                )
                                .unwrap()
                            ),
                            case["expected"]
                        );
                    } else {
                        let mut out = [0; 64];
                        let n =
                            encode_measurement(&raw_measurement(&case["expected"]), opts, &mut out)
                                .unwrap();
                        assert_eq!(&out[..n], b);
                    }
                } else {
                    use ftms::*;
                    let d = &case["expected"];
                    let r = raw_range(d);
                    let opt = RangeOptions {
                        resistance_format: match case["options"]["resistanceFormat"]
                            .as_str()
                            .unwrap()
                        {
                            "uint8Whole" => ResistanceRangeFormat::Uint8Whole,
                            "signed16Tenths" => ResistanceRangeFormat::Signed16Tenths,
                            _ => panic!("runner error: range format"),
                        },
                    };
                    if direction == "decode" {
                        assert_eq!(
                            range_json(decode_range(range_kind(&case["kind"]), &b, opt).unwrap()),
                            *d
                        );
                    } else {
                        let mut out = [0; 6];
                        let n = encode_range(r, opt, &mut out).unwrap();
                        assert_eq!(&out[..n], b);
                    }
                }
            });
        }
    }
    report.finish("compatibility/v1", Some(CS), CV, CC, 9, 18);
}

#[test]
fn runner_rejects_invalid_fixtures_and_records_failures() {
    let mut invalid = corpus(MS, MV);
    invalid["cases"][0]["decoded"]["present"] = json!("not an integer");
    assert!(failure(|| {
        corpus(MS, &invalid.to_string());
    })
    .is_some());
    assert!(failure(|| unique(&[])).is_some());
    assert!(failure(|| unique(&[json!({"id":""})])).is_some());
    assert!(failure(|| unique(&[json!({"id":"x"}), json!({"id":"x"})])).is_some());
    let mut report = Report::default();
    report.run("self-test", "runner", "decode", || {
        panic!("injected failure")
    });
    assert_eq!(report.outcomes[0]["outcome"], "failed");
    assert_eq!(report.outcomes[0]["reason"], "injected failure");
    report.run("self-test", "runner", "encode", || {});
    assert_eq!(report.outcomes[1]["outcome"], "passed");
    assert!(failure(|| report.run("self-test", "runner", "encode", || {})).is_some());
}
