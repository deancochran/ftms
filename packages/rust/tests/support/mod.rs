//! Host-only adapters and evidence reports. Never compiled into the library.
#![allow(dead_code)]

use ftms::measurement::*;
use ftms::Error;
use jsonschema::{Draft, JSONSchema};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};

pub fn sha256(text: &str) -> String {
    format!("{:x}", Sha256::digest(text.as_bytes()))
}
pub fn git(args: &[&str]) -> String {
    let output = std::process::Command::new("git")
        .arg("-C")
        .arg(std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../.."))
        .args(args)
        .output()
        .expect("runner error: invoking git");
    assert!(output.status.success(), "runner error: git failed");
    String::from_utf8(output.stdout)
        .expect("runner error: git UTF-8")
        .trim()
        .into()
}
pub fn corpus(schema: &str, text: &str) -> Value {
    let schema: Value = serde_json::from_str(schema).expect("runner error: schema JSON");
    let vectors = serde_json::from_str(text).expect("runner error: vectors JSON");
    let validator = JSONSchema::options()
        .with_draft(Draft::Draft202012)
        .compile(&schema)
        .expect("runner error: compile schema");
    if let Err(errors) = validator.validate(&vectors) {
        panic!(
            "runner error: invalid schema input: {}",
            errors.map(|e| e.to_string()).collect::<Vec<_>>().join("; ")
        );
    }
    vectors
}
pub fn unique(cases: &[Value]) {
    assert!(!cases.is_empty(), "runner error: empty corpus");
    let mut ids = BTreeSet::new();
    for case in cases {
        let id = case["id"].as_str().expect("runner error: case id");
        assert!(!id.is_empty(), "runner error: empty ID");
        assert!(ids.insert(id), "runner error: duplicate ID");
    }
}
pub fn number(v: &Value) -> u64 {
    v.as_u64().expect("runner error: unsigned integer")
}
pub fn bytes(v: &Value) -> Vec<u8> {
    v.as_array()
        .expect("runner error: bytes array")
        .iter()
        .map(|x| u8::try_from(number(x)).expect("runner error: byte range"))
        .collect()
}
pub fn unhex(v: &Value) -> Vec<u8> {
    let text = v.as_str().expect("runner error: hex string");
    assert_eq!(text.len() % 2, 0);
    text.as_bytes()
        .chunks_exact(2)
        .map(|s| u8::from_str_radix(std::str::from_utf8(s).unwrap(), 16).unwrap())
        .collect()
}
pub fn hex(v: &[u8]) -> String {
    use std::fmt::Write;
    v.iter().fold(String::new(), |mut text, b| {
        write!(&mut text, "{b:02x}").unwrap();
        text
    })
}
pub fn measurement_kind(v: &Value) -> Result<MeasurementKind, Error> {
    let n = v.as_i64().expect("runner error: kind integer");
    u8::try_from(n)
        .map_err(|_| Error::InvalidKind)
        .and_then(MeasurementKind::try_from)
}
pub fn options(v: &Value) -> MeasurementOptions {
    let resistance_format = match v.get("resistanceFormat").and_then(Value::as_str) {
        None | Some("uint8Whole") => MeasurementResistanceFormat::Uint8Whole,
        Some("signed16Tenths") => MeasurementResistanceFormat::Signed16Tenths,
        _ => panic!("runner error: resistance profile"),
    };
    let treadmill_pace_format = match v.get("treadmillPaceFormat").and_then(Value::as_str) {
        None | Some("uint16") => TreadmillPaceFormat::Uint16,
        Some("uint8Legacy") => TreadmillPaceFormat::Uint8Legacy,
        _ => panic!("runner error: pace profile"),
    };
    MeasurementOptions {
        resistance_format,
        treadmill_pace_format,
    }
}
pub fn raw_measurement(v: &Value) -> RawMeasurement {
    let mut m = RawMeasurement::new(measurement_kind(&v["kind"]).unwrap());
    m.flags = u32::try_from(number(&v["flags"])).unwrap();
    m.present = u32::try_from(number(&v["present"])).unwrap();
    m.unavailable = u32::try_from(number(&v["unavailable"])).unwrap();
    let values = v["values"].as_array().unwrap();
    assert_eq!(values.len(), MEASUREMENT_FIELD_COUNT);
    for (dest, value) in m.values.iter_mut().zip(values) {
        *dest = i32::try_from(value.as_i64().unwrap()).unwrap();
    }
    m.more_data = number(&v["moreData"]) == 1;
    m.backward = number(&v["backward"]) == 1;
    m.truncated = number(&v["truncated"]) == 1;
    m.trailing_bytes = number(&v["trailingBytes"]) == 1;
    m.reserved_flags = number(&v["reservedFlags"]) == 1;
    m.bytes_read = usize::try_from(number(&v["bytesRead"])).unwrap();
    m
}
pub fn measurement_json(m: RawMeasurement) -> Value {
    json!({"kind":m.kind as u8,"flags":m.flags,"present":m.present,"unavailable":m.unavailable,"values":m.values,
        "moreData":u8::from(m.more_data),"backward":u8::from(m.backward),"truncated":u8::from(m.truncated),
        "trailingBytes":u8::from(m.trailing_bytes),"reservedFlags":u8::from(m.reserved_flags),"bytesRead":m.bytes_read})
}

pub fn range_kind(v: &Value) -> ftms::RangeKind {
    use ftms::RangeKind::*;
    match v.as_str().unwrap() {
        "speed" => Speed,
        "inclination" => Inclination,
        "resistance" => Resistance,
        "heartRate" => HeartRate,
        "power" => Power,
        _ => panic!("runner error: range kind"),
    }
}
pub fn raw_range(v: &Value) -> ftms::RawRange {
    use ftms::RangeUnit::*;
    ftms::RawRange {
        kind: range_kind(&v["kind"]),
        minimum: i32::try_from(v["minimum"].as_i64().unwrap()).unwrap(),
        maximum: i32::try_from(v["maximum"].as_i64().unwrap()).unwrap(),
        increment: i32::try_from(number(&v["increment"])).unwrap(),
        scale_divisor: u16::try_from(number(&v["scaleDivisor"])).unwrap(),
        unit: match number(&v["unit"]) {
            0 => KilometresPerHour,
            1 => Percent,
            2 => Level,
            3 => BeatsPerMinute,
            4 => Watts,
            _ => panic!("runner error: range unit"),
        },
    }
}
pub fn range_json(v: ftms::RawRange) -> Value {
    use ftms::{RangeKind::*, RangeUnit::*};
    json!({"kind":match v.kind {Speed=>"speed",Inclination=>"inclination",Resistance=>"resistance",HeartRate=>"heartRate",Power=>"power"},
        "minimum":v.minimum,"maximum":v.maximum,"increment":v.increment,"scaleDivisor":v.scale_divisor,
        "unit":match v.unit {KilometresPerHour=>0,Percent=>1,Level=>2,BeatsPerMinute=>3,Watts=>4}})
}

#[derive(Default)]
pub struct Report {
    pub outcomes: Vec<Value>,
}
impl Report {
    pub fn run(&mut self, id: &str, category: &str, direction: &str, f: impl FnOnce()) {
        assert!(
            !id.is_empty() && !category.is_empty() && !direction.is_empty(),
            "runner error: empty identity"
        );
        assert!(
            !self
                .outcomes
                .iter()
                .any(|v| v["id"] == id && v["direction"] == direction),
            "runner error: duplicate direction"
        );
        let error = failure(f);
        self.outcomes
            .push(json!({"id":id,"category":category,"direction":direction,
            "outcome":if error.is_some() {"failed"} else {"passed"},"reason":error}));
    }
    pub fn finish(
        &self,
        name: &str,
        schema: Option<&str>,
        vectors: &str,
        contract: &str,
        cases: usize,
        assertions: usize,
    ) {
        let mut categories: BTreeMap<&str, BTreeSet<&str>> = BTreeMap::new();
        let mut ids = BTreeSet::new();
        for v in &self.outcomes {
            let id = v["id"].as_str().unwrap();
            categories
                .entry(v["category"].as_str().unwrap())
                .or_default()
                .insert(id);
            ids.insert(id);
        }
        let failed = self
            .outcomes
            .iter()
            .filter(|v| v["outcome"] == "failed")
            .count();
        let failed_cases: BTreeSet<_> = self
            .outcomes
            .iter()
            .filter(|v| v["outcome"] == "failed")
            .map(|v| v["id"].as_str().unwrap())
            .collect();
        let format: Value = serde_json::from_str(vectors).expect("runner error: vectors JSON");
        let schema_id = schema.map(|s| serde_json::from_str::<Value>(s).unwrap()["$id"].clone());
        eprintln!(
            "{}",
            json!({"corpus":name,"sourceHead":git(&["rev-parse","HEAD"]),"dirty":!git(&["status","--porcelain"]).is_empty(),
            "schemaVersion":format["schemaVersion"],"schemaId":schema_id,
            "schemaSha256":schema.map(sha256),"vectorsSha256":sha256(vectors),"contractSha256":sha256(contract),
            "caseCount":ids.len(),"passedCases":ids.len()-failed_cases.len(),"failedCases":failed_cases.len(),
            "categoryCases":categories.iter().map(|(k,v)|(*k,v.len())).collect::<BTreeMap<_,_>>(),
            "assertions":self.outcomes.len(),"passed":self.outcomes.len()-failed,"failed":failed,
            "unsupported":0,"skipped":0,"runnerErrors":[],"outcomes":self.outcomes})
        );
        assert_eq!(ids.len(), cases, "runner error: case accounting");
        assert_eq!(
            self.outcomes.len(),
            assertions,
            "runner error: direction accounting"
        );
        assert_eq!(failed, 0, "see individual failure outcomes");
    }
}
pub fn failure(f: impl FnOnce()) -> Option<String> {
    std::panic::catch_unwind(std::panic::AssertUnwindSafe(f))
        .err()
        .map(|p| {
            p.downcast_ref::<String>()
                .cloned()
                .or_else(|| p.downcast_ref::<&str>().map(|s| (*s).into()))
                .unwrap_or_else(|| "non-string panic".into())
        })
}
