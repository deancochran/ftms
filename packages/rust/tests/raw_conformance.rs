use ftms::*;
use jsonschema::{Draft, JSONSchema};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

const VS: &str = include_str!("../../../shared/conformance/values/v1/schema.json");
const VV: &str = include_str!("../../../shared/conformance/values/v1/vectors.json");
const VC: &str = include_str!("../../../shared/conformance/values/README.md");
const IV: &str = include_str!("../../../shared/conformance/inspection/v1/fixtures.json");
const IC: &str = include_str!("../../../shared/conformance/inspection/v1/README.md");
const CS: &str = include_str!("../../../shared/conformance/controls/v1/schema.json");
const CV: &str = include_str!("../../../shared/conformance/controls/v1/vectors.json");
const CC: &str = include_str!("../../../shared/conformance/controls/README.md");

#[derive(Debug)]
struct Outcome {
    id: String,
    category: &'static str,
    direction: &'static str,
    error: Option<String>,
}
fn run_direction(
    out: &mut Vec<Outcome>,
    id: &str,
    category: &'static str,
    direction: &'static str,
    test: impl FnOnce(),
) {
    let error = std::panic::catch_unwind(std::panic::AssertUnwindSafe(test))
        .err()
        .map(|panic| {
            if let Some(s) = panic.downcast_ref::<String>() {
                s.clone()
            } else if let Some(s) = panic.downcast_ref::<&str>() {
                (*s).to_owned()
            } else {
                "non-string panic".to_owned()
            }
        });
    out.push(Outcome {
        id: id.to_owned(),
        category,
        direction,
        error,
    });
}
fn hash(s: &str) -> String {
    format!("{:x}", Sha256::digest(s.as_bytes()))
}
fn git(a: &[&str]) -> String {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    String::from_utf8(
        std::process::Command::new("git")
            .arg("-C")
            .arg(root)
            .args(a)
            .output()
            .expect("git")
            .stdout,
    )
    .expect("UTF-8")
    .trim()
    .to_owned()
}
fn report(
    name: &str,
    schema: Option<&str>,
    vectors: &str,
    contract: &str,
    ids: &[String],
    out: &[Outcome],
) {
    let passed = out.iter().filter(|x| x.error.is_none()).count();
    let failed = out.len() - passed;
    let mut category_ids =
        std::collections::BTreeMap::<&str, std::collections::BTreeSet<&str>>::new();
    for x in out {
        category_ids.entry(x.category).or_default().insert(&x.id);
    }
    let categories = category_ids
        .into_iter()
        .map(|(category, ids)| (category, ids.len()))
        .collect::<std::collections::BTreeMap<_, _>>();
    let outcomes = out
        .iter()
        .map(|x| {
            format!(
                "{}:{}:{}={}",
                x.category,
                x.id,
                x.direction,
                if x.error.is_none() {
                    "passed"
                } else {
                    "failed"
                }
            )
        })
        .collect::<Vec<_>>()
        .join(", ");
    let failures = out
        .iter()
        .filter_map(|x| {
            x.error
                .as_ref()
                .map(|e| format!("{}:{}:{}: {e}", x.category, x.id, x.direction))
        })
        .collect::<Vec<_>>()
        .join(" | ");
    eprintln!("FTMS Rust {name}: head={} dirty={} schemaSha256={} vectorsSha256={} contractSha256={}; cases={} categoryCases={:?} assertions={} passed={} failed={} unsupported=0 skipped=0; outcomes=[{}]; nonpasses=[{}]; runnerErrors=[]",git(&["rev-parse","HEAD"]),!git(&["status","--porcelain"]).is_empty(),schema.map(hash).unwrap_or_else(||"none".into()),hash(vectors),hash(contract),ids.len(),categories,out.len(),passed,failed,outcomes,failures);
}
fn corpus(schema: &str, text: &str) -> Value {
    let s: Value = serde_json::from_str(schema).expect("runner error: parse schema");
    let v: Value = serde_json::from_str(text).expect("runner error: parse vectors");
    let validator = JSONSchema::options()
        .with_draft(Draft::Draft202012)
        .compile(&s)
        .expect("runner error: compile schema");
    if let Err(errors) = validator.validate(&v) {
        panic!(
            "runner error: schema validation: {}",
            errors.map(|x| x.to_string()).collect::<Vec<_>>().join("; ")
        )
    };
    v
}
fn ids(cases: &[Value]) -> Vec<String> {
    assert!(!cases.is_empty(), "runner error: empty corpus");
    let mut seen = std::collections::HashSet::new();
    cases
        .iter()
        .map(|c| {
            let id = c["id"]
                .as_str()
                .expect("runner error: missing id")
                .to_owned();
            assert!(seen.insert(id.clone()), "runner error: duplicate id {id}");
            id
        })
        .collect()
}
fn bytes(v: &Value, k: &str) -> Vec<u8> {
    v[k].as_array()
        .unwrap()
        .iter()
        .map(|x| x.as_u64().unwrap() as u8)
        .collect()
}
fn kind(s: &str) -> RangeKind {
    match s {
        "speed" => RangeKind::Speed,
        "inclination" => RangeKind::Inclination,
        "resistance" => RangeKind::Resistance,
        "heartRate" => RangeKind::HeartRate,
        "power" => RangeKind::Power,
        _ => panic!("kind"),
    }
}
fn unit(n: u64) -> RangeUnit {
    [
        RangeUnit::KilometresPerHour,
        RangeUnit::Percent,
        RangeUnit::Level,
        RangeUnit::BeatsPerMinute,
        RangeUnit::Watts,
    ][n as usize]
}
fn raw_range(v: &Value) -> RawRange {
    RawRange {
        kind: kind(v["kind"].as_str().unwrap()),
        minimum: v["minimum"].as_i64().unwrap() as i32,
        maximum: v["maximum"].as_i64().unwrap() as i32,
        increment: v["increment"].as_i64().unwrap() as i32,
        scale_divisor: v["scaleDivisor"].as_u64().unwrap() as u16,
        unit: unit(v["unit"].as_u64().unwrap()),
    }
}
fn request(c: &Value) -> ControlRequest {
    let values = c["decoded"]["operands"].as_array().unwrap();
    let mut operands = [0; 5];
    for (i, x) in values.iter().enumerate() {
        operands[i] = x.as_i64().unwrap() as i32
    }
    ControlRequest {
        opcode: c["decoded"]["opcode"].as_u64().unwrap() as u8,
        operands,
        operand_count: values.len(),
    }
}
fn response(c: &Value) -> ControlResponse {
    let d = &c["decoded"];
    ControlResponse {
        request_opcode: d["requestOpcode"].as_u64().unwrap() as u8,
        result_code: d["resultCode"].as_u64().unwrap() as u8,
        parameter: d["parameter"].as_u64().unwrap() as u8,
        low: d["low"].as_u64().unwrap() as u16,
        high: d["high"].as_u64().unwrap() as u16,
        unknown_request: d["unknownRequest"].as_u64().unwrap() as u8,
        unknown_result: d["unknownResult"].as_u64().unwrap() as u8,
        unexpected_parameters: d["unexpectedParameters"].as_u64().unwrap() as u8,
    }
}

#[test]
fn outcomes_execute_second_direction_after_first_failure() {
    let mut out = Vec::new();
    run_direction(&mut out, "injected", "self", "encode", || {
        panic!("injected")
    });
    let mut ran = false;
    run_direction(&mut out, "injected", "self", "decode", || {
        ran = true;
    });
    assert!(ran);
    assert_eq!(out.len(), 2);
    assert_eq!(out.iter().filter(|x| x.error.is_none()).count(), 1);
    assert_eq!(out.iter().filter(|x| x.error.is_some()).count(), 1);
}

#[test]
fn values_v1_reports_independent_literal_directions() {
    let c = corpus(VS, VV);
    let cases = c["cases"].as_array().unwrap();
    let all = ids(cases);
    let mut out = Vec::new();
    for v in cases {
        let id = v["id"].as_str().unwrap();
        let b = bytes(v, "expectedBytes");
        if v["operation"] == "features" {
            let expected = RawFeatures {
                machine: v["machine"].as_u64().unwrap() as u32,
                target: v["target"].as_u64().unwrap() as u32,
            };
            run_direction(&mut out, id, "features", "encode", || {
                assert_eq!(encode_features(expected), b.as_slice())
            });
            run_direction(&mut out, id, "features", "decode", || {
                assert_eq!(decode_features(&b), Ok(expected))
            });
        } else {
            let expected = raw_range(v);
            run_direction(&mut out, id, "ranges", "encode", || {
                let mut b2 = [0; 6];
                let n = encode_range(expected, RangeOptions::default(), &mut b2).unwrap();
                assert_eq!(&b2[..n], b.as_slice())
            });
            run_direction(&mut out, id, "ranges", "decode", || {
                assert_eq!(
                    decode_range(expected.kind, &b, RangeOptions::default()),
                    Ok(expected)
                )
            });
        }
    }
    report("values/v1", Some(VS), VV, VC, &all, &out);
    assert!(out.iter().all(|x| x.error.is_none()));
}

fn profile(p: RangeProfile) -> &'static str {
    match p {
        RangeProfile::Uint16Hundredths => "uint16Hundredths",
        RangeProfile::Signed16Tenths => "signed16Tenths",
        RangeProfile::Uint8Whole => "uint8Whole",
        RangeProfile::Uint8Bpm => "uint8Bpm",
        RangeProfile::Signed16Watts => "signed16Watts",
    }
}
fn status(s: InspectionStatus) -> &'static str {
    match s {
        InspectionStatus::Valid => "valid",
        InspectionStatus::Length => "length",
        InspectionStatus::Range => "range",
    }
}
fn json_range(r: RawRange) -> Value {
    json!({"kind":match r.kind{RangeKind::Speed=>"speed",RangeKind::Inclination=>"inclination",RangeKind::Resistance=>"resistance",RangeKind::HeartRate=>"heartRate",RangeKind::Power=>"power"},"minimum":r.minimum,"maximum":r.maximum,"increment":r.increment,"scaleDivisor":r.scale_divisor,"unit":match r.unit{RangeUnit::KilometresPerHour=>0,RangeUnit::Percent=>1,RangeUnit::Level=>2,RangeUnit::BeatsPerMinute=>3,RangeUnit::Watts=>4}})
}
#[test]
fn inspection_v1_compares_complete_canonical_reports() {
    let d: Value = serde_json::from_str(IV).expect("runner error: inspection parse");
    let cases = d["cases"].as_array().unwrap();
    let all = ids(cases);
    let mut out = Vec::new();
    for c in cases {
        let id = c["id"].as_str().unwrap();
        run_direction(&mut out, id, "inspection", "inspect", || {
            let opt = if c.get("options").is_some() {
                RangeOptions {
                    resistance_format: ResistanceRangeFormat::Signed16Tenths,
                }
            } else {
                RangeOptions::default()
            };
            let x =
                inspect_range(kind(c["kind"].as_str().unwrap()), &bytes(c, "bytes"), opt).unwrap();
            let candidates=(0..x.candidate_count).map(|i|{let q=x.candidates[i].unwrap();json!({"profile":profile(q.profile),"expectedLength":q.expected_length,"status":status(q.status),"value":q.value.map(json_range)})}).collect::<Vec<_>>();
            let actual = json!({"selectedProfile":profile(x.selected_profile),"actualLength":x.actual_length,"expectedLength":x.expected_length,"status":status(x.status),"value":x.value.map(json_range),"candidates":candidates});
            assert_eq!(actual, c["expected"]);
        });
    }
    report("inspection/v1", None, IV, IC, &all, &out);
    assert!(out.iter().all(|x| x.error.is_none()));
}

#[test]
fn controls_v1_reports_independent_literal_directions() {
    let c = corpus(CS, CV);
    let mut cases = Vec::new();
    for k in ["requests", "responses", "invalid"] {
        cases.extend(c[k].as_array().unwrap().iter().cloned())
    }
    let all = ids(&cases);
    let mut out = Vec::new();
    for c in c["requests"].as_array().unwrap() {
        let id = c["id"].as_str().unwrap();
        let expected = request(c);
        let b = bytes(c, "bytes");
        let opt = if c.get("format").is_some() {
            ControlOptions {
                resistance_format: ResistanceControlFormat::Uint8Tenths,
            }
        } else {
            ControlOptions::default()
        };
        run_direction(&mut out, id, "requests", "encode", || {
            let mut b2 = [0; 11];
            let n = encode_control_request(expected, opt, &mut b2).unwrap();
            assert_eq!(&b2[..n], b.as_slice())
        });
        run_direction(&mut out, id, "requests", "decode", || {
            assert_eq!(decode_control_request(&b, opt), Ok(expected))
        });
    }
    for c in c["responses"].as_array().unwrap() {
        let id = c["id"].as_str().unwrap();
        let expected = response(c);
        let b = bytes(c, "bytes");
        if c["encode"] != false {
            run_direction(&mut out, id, "responses", "encode", || {
                let mut b2 = [0; 7];
                let n = encode_control_response(expected, &mut b2).unwrap();
                assert_eq!(&b2[..n], b.as_slice())
            });
        }
        run_direction(&mut out, id, "responses", "decode", || {
            assert_eq!(decode_control_response(&b), Ok(expected))
        });
    }
    for c in c["invalid"].as_array().unwrap() {
        let id = c["id"].as_str().unwrap();
        let b = bytes(c, "bytes");
        let e = c["error"].as_str().unwrap();
        run_direction(&mut out, id, "invalid", "decode", || {
            let got = if c["operation"] == "request" {
                decode_control_request(
                    &b,
                    if c.get("format").is_some() {
                        ControlOptions {
                            resistance_format: ResistanceControlFormat::Uint8Tenths,
                        }
                    } else {
                        ControlOptions::default()
                    },
                )
                .unwrap_err()
            } else {
                decode_control_response(&b).unwrap_err()
            };
            assert_eq!(
                match got {
                    Error::WrongLength { .. } => "length",
                    Error::InvalidKind => "kind",
                    Error::InvalidRange => "range",
                    _ => "other",
                },
                e
            )
        });
    }
    report("controls/v1", Some(CS), CV, CC, &all, &out);
    assert_eq!(out.len(), 72);
    assert!(out.iter().all(|x| x.error.is_none()));
}
