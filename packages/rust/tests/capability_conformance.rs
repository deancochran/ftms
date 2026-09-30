//! Host-only exact capability-v1 adapter. Production remains `no_std`.
use ftms::{capabilities::*, RangeOptions};
use jsonschema::{Draft, JSONSchema};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashSet};

const SCHEMA: &str = include_str!("../../../shared/conformance/capabilities/v1/schema.json");
const VECTORS: &str = include_str!("../../../shared/conformance/capabilities/v1/vectors.json");
const CONTRACT: &str = include_str!("../../../shared/conformance/capabilities/README.md");
const PROTOCOL: &str = include_str!("../../../shared/protocol/capability-discovery.md");

fn hex(s: &str) -> Vec<u8> {
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
        .collect()
}
fn truth(v: u64) -> Truth {
    [Truth::Unknown, Truth::False, Truth::True][v as usize]
}
fn discovery(v: u64) -> Discovery {
    [
        Discovery::NotAttempted,
        Discovery::Partial,
        Discovery::Complete,
        Discovery::Failed,
    ][v as usize]
}
fn scope(v: u64) -> ServiceScope {
    [
        ServiceScope::Unknown,
        ServiceScope::Present,
        ServiceScope::Absent,
        ServiceScope::Ambiguous,
    ][v as usize]
}
fn read(v: u64) -> ReadState {
    [
        ReadState::NotAttempted,
        ReadState::Success,
        ReadState::Failed,
    ][v as usize]
}
fn expand(spec: &Value, templates: &Value) -> Value {
    let mut result = templates[spec["template"].as_str().unwrap()].clone();
    for edit in spec["edits"].as_array().unwrap() {
        apply(&mut result, edit);
    }
    result
}
fn apply(root: &mut Value, edit: &Value) {
    let op = edit.get("op").and_then(Value::as_str).unwrap_or("replace");
    let path = edit["path"].as_array().unwrap();
    fn walk(node: &mut Value, path: &[Value], op: &str, value: &Value) {
        if path.is_empty() {
            if op == "append" {
                node.as_array_mut()
                    .expect("append array")
                    .push(value.clone());
            } else {
                *node = value.clone();
            }
            return;
        }
        let key = &path[0];
        match node {
            Value::Object(m) => {
                let child = m.get_mut(key.as_str().unwrap()).unwrap();
                walk(child, &path[1..], op, value)
            }
            Value::Array(a) => {
                if key == "*" {
                    for x in a.iter_mut() {
                        walk(x, &path[1..], op, value)
                    }
                } else if key.is_array() {
                    for i in key.as_array().unwrap() {
                        walk(&mut a[i.as_u64().unwrap() as usize], &path[1..], op, value)
                    }
                } else {
                    let i = key.as_u64().unwrap() as usize;
                    if path.len() == 1 && op == "remove" {
                        a.remove(i);
                    } else if path.len() == 1 && op == "append" {
                        a[i].as_array_mut().unwrap().push(value.clone())
                    } else {
                        walk(&mut a[i], &path[1..], op, value)
                    }
                }
            }
            _ => panic!("invalid edit"),
        }
    }
    walk(root, path, op, edit.get("value").unwrap_or(&Value::Null));
}
fn actual(input: &Value) -> Value {
    let mut data: Vec<Vec<u8>> = Vec::new();
    for c in input["characteristics"]
        .as_array()
        .unwrap_or_else(|| panic!("expanded snapshot characteristics: {input}"))
    {
        data.push(hex(c["bytes"].as_str().unwrap()));
    }
    let chars: Vec<_> = input["characteristics"]
        .as_array()
        .unwrap()
        .iter()
        .zip(data.iter())
        .map(|(c, b)| {
            let u = hex(c["uuid"].as_str().unwrap());
            Characteristic {
                uuid: u.try_into().unwrap(),
                properties: c["properties"].as_u64().unwrap() as u16,
                read_state: read(c["readState"].as_u64().unwrap()),
                read_reason: c["reason"].as_u64().unwrap() as u8,
                bytes: b,
            }
        })
        .collect();
    let c7 = &input["c7"];
    let r = evaluate_capabilities::<128, 128>(
        CapabilitySnapshot {
            discovery: discovery(input["discovery"].as_u64().unwrap()),
            scope: scope(input["scope"].as_u64().unwrap()),
            generation: input["generation"].as_u64().unwrap() as u32,
            characteristics: &chars,
            c7: C7Evidence {
                bonding_supported: truth(
                    c7.get("bondingSupported")
                        .and_then(Value::as_u64)
                        .unwrap_or(0),
                ),
                feature_may_change_over_lifetime: truth(
                    c7.get("featureMayChangeOverLifetime")
                        .and_then(Value::as_u64)
                        .unwrap_or(0),
                ),
            },
        },
        RangeOptions::default(),
    )
    .unwrap();
    let p = |x: Presence| x as u8;
    let d = |x: Decode| x as u8;
    let decl = |x: Declaration| x as u8;
    let pre = |x: Prerequisite| x as u8;
    let hx = |u: &[u8; 16]| {
        use std::fmt::Write;
        u.iter().fold(String::new(), |mut text, b| {
            write!(&mut text, "{b:02x}").unwrap();
            text
        })
    };
    json!({"generation":r.generation,"discovery":r.discovery as u8,"scope":r.scope as u8,"observationCount":r.observation_count,"diagnosticCount":r.diagnostic_count,"presence":r.presence.map(p),"feature":[p(r.feature.presence),d(r.feature.decode),r.feature.input_index,r.feature.machine_raw,r.feature.target_raw,r.feature.machine_unknown,r.feature.target_unknown],"ranges":r.ranges.map(|x|json!([p(x.presence),d(x.decode),x.input_index,x.value.map(|v|vec![match v.kind{ftms::RangeKind::Speed=>0,ftms::RangeKind::Inclination=>1,ftms::RangeKind::Resistance=>2,ftms::RangeKind::HeartRate=>3,ftms::RangeKind::Power=>4},v.minimum,v.maximum,v.increment,v.scale_divisor as i32,match v.unit{ftms::RangeUnit::KilometresPerHour=>0,ftms::RangeUnit::Percent=>1,ftms::RangeUnit::Level=>2,ftms::RangeUnit::BeatsPerMinute=>3,ftms::RangeUnit::Watts=>4}])])),"operations":r.operations.map(|x|vec![x.opcode as u32,x.target_bit as u32,x.optional_in_table as u32,decl(x.declaration)as u32,pre(x.prerequisite)as u32,x.reasons]),"observations":r.observations[..r.observation_count].iter().map(|x|{let x=x.unwrap();json!([x.input_index,hx(&x.uuid),x.properties,x.known_kind,x.read_state as u8,x.read_reason,x.read_size])}).collect::<Vec<_>>(),"diagnostics":r.diagnostics[..r.diagnostic_count].iter().map(|x|{let x=x.unwrap();json!([x.code,x.known_kind,x.input_index])}).collect::<Vec<_>>()})
}
fn hash(x: &str) -> String {
    format!("{:x}", Sha256::digest(x.as_bytes()))
}
#[test]
fn capability_v1_exact_reports() {
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
    let mut cats = BTreeMap::new();
    let mut failures = Vec::new();
    for case in vectors["cases"].as_array().unwrap() {
        let id = case["id"].as_str().unwrap();
        assert!(ids.insert(id));
        *cats
            .entry(case["category"].as_str().unwrap())
            .or_insert(0usize) += 1;
        let input = expand(&case["input"], &vectors["snapshots"]);
        assert!(
            input.get("characteristics").is_some(),
            "bad expansion {id}: {input}"
        );
        let expected = expand(&case["expected"], &vectors["reports"]);
        let got = actual(&input);
        if got != expected {
            failures.push(format!("{id}: expected {expected}; got {got}"));
        }
    }
    eprintln!("FTMS Rust capability-v1: head={} dirty={} schemaSha256={} vectorsSha256={} contractSha256={} protocolSha256={}; cases={} categories={cats:?} passed={} failed={} unsupported=0 skipped=0",git("rev-parse HEAD"),!git("status --porcelain").is_empty(),hash(SCHEMA),hash(VECTORS),hash(CONTRACT),hash(PROTOCOL),ids.len(),ids.len()-failures.len(),failures.len());
    assert_eq!(ids.len(), 63);
    assert!(failures.is_empty(), "{}", failures.join("\n"));
}
fn git(args: &str) -> String {
    String::from_utf8(
        std::process::Command::new("git")
            .arg("-C")
            .arg(std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../.."))
            .args(args.split_whitespace())
            .output()
            .unwrap()
            .stdout,
    )
    .unwrap()
    .trim()
    .into()
}
