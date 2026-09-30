mod support;

use ftms::{measurement::*, Error};
use serde::Deserialize;
use serde_json::json;
use std::collections::BTreeMap;
use support::{failure, git, sha256};

const TABLE: &str = include_str!("../../../shared/conformance/measurement-matrix/v1/layouts.json");
const CONTRACT: &str = include_str!("../../../shared/conformance/measurement-matrix/v1/README.md");

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct Layout {
    kind: u8,
    flag_bytes: usize,
    optional_groups: u32,
    full_length: usize,
    fields: Vec<[u32; 5]>,
}
#[derive(Deserialize)]
struct Table {
    contract: String,
    layouts: Vec<Layout>,
}

/// Independent test-only declarations loaded from the shared table, never from
/// production descriptor arrays. The builders implement the matrix contract.
fn fields(layout: &Layout, alternate: bool) -> Vec<[u32; 5]> {
    layout
        .fields
        .iter()
        .copied()
        .map(|mut f| {
            if alternate && layout.kind == 0 && matches!(f[2], 7 | 8) {
                f[1] = 1;
            }
            if alternate && matches!(layout.kind, 1 | 4 | 5) && f[2] == 21 {
                f[1] = 2;
                f[3] = 1;
            }
            f
        })
        .collect()
}
fn selected(flags: u32, f: &[u32; 5]) -> bool {
    if f[0] == 0 {
        flags & 1 == 0
    } else {
        flags & (1 << f[0]) != 0
    }
}
fn sentinel(f: &[u32; 5]) -> u32 {
    if f[3] != 0 {
        0x7fff
    } else {
        (1 << (8 * f[1])) - 1
    }
}
fn append(out: &mut Vec<u8>, width: usize, value: u32) {
    out.extend((0..width).map(|i| (value >> (8 * i)) as u8));
}
fn build(
    layout: &Layout,
    fields: &[[u32; 5]],
    flags: u32,
    unavailable: u32,
) -> (Vec<u8>, RawMeasurement) {
    let mut value = RawMeasurement::new(MeasurementKind::try_from(layout.kind).unwrap());
    value.flags = flags;
    value.more_data = flags & 1 != 0;
    value.backward = layout.kind == 1 && flags & 0x8000 != 0;
    let mut bytes = Vec::new();
    append(&mut bytes, layout.flag_bytes, flags);
    for f in fields.iter().filter(|f| selected(flags, f)) {
        let bit = 1 << f[2];
        let raw = if unavailable & bit != 0 {
            sentinel(f)
        } else {
            ((f[2] + 1) as i32 * if f[3] != 0 { -1 } else { 1 }) as u32
        };
        append(&mut bytes, f[1] as usize, raw);
        value.present |= bit;
        if unavailable & bit != 0 {
            value.unavailable |= bit;
        } else {
            value.values[f[2] as usize] = raw as i32;
        }
    }
    value.bytes_read = bytes.len();
    (bytes, value)
}
fn options(kind: u8, alternate: bool) -> MeasurementOptions {
    MeasurementOptions {
        resistance_format: if alternate && kind != 0 {
            MeasurementResistanceFormat::Signed16Tenths
        } else {
            MeasurementResistanceFormat::Uint8Whole
        },
        treadmill_pace_format: if alternate && kind == 0 {
            TreadmillPaceFormat::Uint8Legacy
        } else {
            TreadmillPaceFormat::Uint16
        },
    }
}

#[derive(Default)]
struct Counts {
    attempted: usize,
    failed: usize,
}
#[derive(Default)]
struct Stats {
    groups: BTreeMap<String, Counts>,
    failures: Vec<String>,
}
impl Stats {
    fn run(&mut self, group: &str, id: &str, direction: &str, f: impl FnOnce()) {
        let counts = self.groups.entry(group.into()).or_default();
        counts.attempted += 1;
        if let Some(error) = failure(f) {
            counts.failed += 1;
            self.failures.push(format!("{id}:{direction}: {error}"));
        }
    }
}
fn check_encoding(value: &RawMeasurement, options: MeasurementOptions, expected: &[u8]) {
    let mut out = [0xa5; 64];
    assert_eq!(
        encode_measurement(value, options, &mut out),
        Ok(expected.len())
    );
    assert_eq!(&out[..expected.len()], expected);
    assert!(out[expected.len()..].iter().all(|v| *v == 0xa5));
}

#[test]
fn complete_structural_matrix_sentinels_rfu_and_prefixes() {
    let table: Table = serde_json::from_str(TABLE).unwrap();
    assert_eq!(table.contract, "ftms-measurement-matrix-v1");
    assert_eq!(
        table.layouts.iter().map(|l| l.kind).collect::<Vec<_>>(),
        [0, 1, 2, 3, 4, 5]
    );
    let mut stats = Stats::default();
    let (mut structural, mut sentinels, mut rfu, mut prefixes) = (0, 0, 0, 0);
    let mut per_layout = BTreeMap::new();
    for layout in &table.layouts {
        let kind = MeasurementKind::try_from(layout.kind).unwrap();
        let variants = if matches!(layout.kind, 0 | 1 | 4 | 5) {
            2
        } else {
            1
        };
        for variant in 0..variants {
            let name = format!("kind-{}-format-{variant}", layout.kind);
            let fields = fields(layout, variant != 0);
            let opts = options(layout.kind, variant != 0);
            let subsets = 1u32 << layout.optional_groups;
            let directions = if layout.kind == 1 { 2 } else { 1 };
            let mut count = 0;
            for subset in 0..subsets {
                for more in 0..2 {
                    for backward in 0..directions {
                        let flags = (subset << 1) | more | (backward << 15);
                        let (bytes, expected) = build(layout, &fields, flags, 0);
                        let id = format!("{name}-flags-{flags:06x}");
                        stats.run("structural", &id, "decode", || {
                            assert_eq!(decode_measurement(kind, &bytes, opts), Ok(expected))
                        });
                        stats.run("structural", &id, "encode", || {
                            check_encoding(&expected, opts, &bytes)
                        });
                        structural += 1;
                        count += 1;
                    }
                }
            }
            per_layout.insert(name.clone(), count);
            let full_flags = (subsets - 1) << 1;
            let (bytes, expected) = build(layout, &fields, full_flags, 0);
            if variant == 0 {
                assert_eq!(bytes.len(), layout.full_length);
            }
            for f in fields.iter().filter(|f| f[4] != 0) {
                let (wire, value) = build(layout, &fields, full_flags, 1 << f[2]);
                let id = format!("{name}-sentinel-{}", f[2]);
                stats.run("sentinels", &id, "decode", || {
                    assert_eq!(decode_measurement(kind, &wire, opts), Ok(value))
                });
                stats.run("sentinels", &id, "encode", || {
                    check_encoding(&value, opts, &wire)
                });
                sentinels += 1;
            }
            let valid = full_flags | 1 | if layout.kind == 1 { 0x8000 } else { 0 };
            for bit in 0..(layout.flag_bytes * 8) {
                if valid & (1 << bit) != 0 {
                    continue;
                }
                let mut wire = bytes.clone();
                wire[bit / 8] |= 1 << (bit % 8);
                let mut value = expected;
                value.flags |= 1 << bit;
                value.reserved_flags = true;
                let id = format!("{name}-rfu-{bit}");
                stats.run("rfu", &id, "decode", || {
                    assert_eq!(decode_measurement(kind, &wire, opts), Ok(value))
                });
                stats.run("rfu", &id, "encode-reject", || {
                    let mut out = [0xa5; 64];
                    assert_eq!(
                        encode_measurement(&value, opts, &mut out),
                        Err(Error::InvalidRange)
                    );
                    assert_eq!(out, [0xa5; 64]);
                });
                rfu += 1;
            }
            // Calculate each partial expected record without invoking a decoder.
            for size in 0..bytes.len() {
                let id = format!("{name}-prefix-{size}");
                stats.run("prefixes", &id, "decode", || {
                    if size < layout.flag_bytes {
                        assert_eq!(
                            decode_measurement(kind, &bytes[..size], opts),
                            Err(Error::WrongLength {
                                expected: layout.flag_bytes,
                                actual: size
                            })
                        );
                    } else {
                        let mut partial = RawMeasurement::new(kind);
                        partial.flags = full_flags;
                        partial.truncated = true;
                        partial.bytes_read = layout.flag_bytes;
                        for f in &fields {
                            if partial.bytes_read + f[1] as usize > size {
                                break;
                            }
                            partial.bytes_read += f[1] as usize;
                            partial.present |= 1 << f[2];
                            partial.values[f[2] as usize] = expected.values[f[2] as usize];
                        }
                        assert_eq!(decode_measurement(kind, &bytes[..size], opts), Ok(partial));
                    }
                });
                prefixes += 1;
            }
        }
    }
    eprintln!(
        "{}",
        json!({"contract":table.contract,"head":git(&["rev-parse","HEAD"]),"dirty":!git(&["status","--porcelain"]).is_empty(),
        "layoutsSha256":sha256(TABLE),"contractSha256":sha256(CONTRACT),"structuralCases":structural,
        "sentinelCases":sentinels,"rfuCases":rfu,"prefixCases":prefixes,"perLayoutStructuralCases":per_layout,
        "assertions":stats.groups.iter().map(|(k,v)|(k,json!({"executed":v.attempted,"passed":v.attempted-v.failed,"failed":v.failed}))).collect::<BTreeMap<_,_>>(),
        "unsupported":0,"skipped":0,"runnerErrors":[],"failures":stats.failures})
    );
    assert_eq!(
        (structural, sentinels, rfu, prefixes),
        (181760, 46, 47, 315)
    );
    assert!(stats.failures.is_empty(), "see matrix failure IDs");
}

#[test]
fn every_field_width_sentinel_and_buffer_boundary() {
    let table: Table = serde_json::from_str(TABLE).unwrap();
    for layout in &table.layouts {
        for alternate in [false, true] {
            let fields = fields(layout, alternate);
            let opt = options(layout.kind, alternate);
            let flags = ((1 << layout.optional_groups) - 1) << 1;
            let (bytes, expected) = build(layout, &fields, flags, 0);
            for field in &fields {
                let max = if field[3] != 0 {
                    32767
                } else {
                    (1i32 << (8 * field[1])) - 1
                };
                let min = if field[3] != 0 { -32768 } else { 0 };
                for value in [min - 1, min, max, max + 1] {
                    let mut input = expected;
                    input.values[field[2] as usize] = value;
                    let valid = (min..=max).contains(&value)
                        && !(field[4] != 0 && value as u32 == sentinel(field));
                    let mut out = [0xa5; 64];
                    if valid {
                        // Build literal changed wire span from the test declaration.
                        let mut wire = bytes.clone();
                        let offset = layout.flag_bytes
                            + fields
                                .iter()
                                .take_while(|f| f[2] != field[2])
                                .map(|f| f[1] as usize)
                                .sum::<usize>();
                        for j in 0..field[1] as usize {
                            wire[offset + j] = ((value as u32) >> (8 * j)) as u8;
                        }
                        check_encoding(&input, opt, &wire);
                        assert_eq!(
                            decode_measurement(input.kind, &wire, opt).unwrap().values
                                [field[2] as usize],
                            value
                        );
                    } else {
                        assert_eq!(
                            encode_measurement(&input, opt, &mut out),
                            Err(Error::InvalidRange)
                        );
                        assert_eq!(out, [0xa5; 64]);
                    }
                }
                let mut input = expected;
                input.unavailable |= 1 << field[2];
                input.values[field[2] as usize] = i32::MIN; // ignored only for a defined sentinel
                let mut out = [0xa5; 64];
                if field[4] != 0 {
                    let (wire, _) = build(layout, &fields, flags, 1 << field[2]);
                    check_encoding(&input, opt, &wire);
                } else {
                    assert_eq!(
                        encode_measurement(&input, opt, &mut out),
                        Err(Error::InvalidRange)
                    );
                    assert_eq!(out, [0xa5; 64]);
                }
            }
            for capacity in 0..bytes.len() {
                let mut out = vec![0xa5; capacity];
                assert_eq!(
                    encode_measurement(&expected, opt, &mut out),
                    Err(Error::InsufficientStorage {
                        required: bytes.len(),
                        available: capacity
                    })
                );
                assert!(out.iter().all(|v| *v == 0xa5));
            }
            for (present, unavailable) in [
                (expected.present ^ 1, 0),
                (expected.present | (1 << 31), 0),
                (expected.present, 1 << 31),
            ] {
                let input = RawMeasurement {
                    present,
                    unavailable,
                    ..expected
                };
                let mut out = [0xa5; 64];
                assert_eq!(
                    encode_measurement(&input, opt, &mut out),
                    Err(Error::InvalidRange)
                );
                assert_eq!(out, [0xa5; 64]);
            }
        }
    }
}

#[test]
fn measurement_options_are_independent_and_never_inferred() {
    let table: Table = serde_json::from_str(TABLE).unwrap();
    for layout in &table.layouts {
        for alternate in [false, true] {
            let fields = fields(layout, alternate);
            let flags = ((1 << layout.optional_groups) - 1) << 1;
            let (wire, expected) = build(layout, &fields, flags, 0);
            let mut opt = options(layout.kind, alternate);
            if layout.kind == 0 {
                opt.resistance_format = MeasurementResistanceFormat::Signed16Tenths;
            } else {
                opt.treadmill_pace_format = TreadmillPaceFormat::Uint8Legacy;
            }
            assert_eq!(decode_measurement(expected.kind, &wire, opt), Ok(expected));
            check_encoding(&expected, opt, &wire);
        }
    }
    let wire = [33, 0, 246, 255];
    let default = decode_measurement(
        MeasurementKind::IndoorBike,
        &wire,
        MeasurementOptions::default(),
    )
    .unwrap();
    assert_eq!(default.values[MeasurementField::Resistance.index()], 246);
    assert!(default.trailing_bytes); // does not auto-select signed16 to consume more bytes
    let selected =
        decode_measurement(MeasurementKind::IndoorBike, &wire, options(5, true)).unwrap();
    assert_eq!(selected.values[MeasurementField::Resistance.index()], -10);
    assert!(!selected.trailing_bytes);
    let wire = [33, 0, 30];
    assert!(
        decode_measurement(
            MeasurementKind::Treadmill,
            &wire,
            MeasurementOptions::default()
        )
        .unwrap()
        .truncated
    );
    let selected = decode_measurement(MeasurementKind::Treadmill, &wire, options(0, true)).unwrap();
    assert_eq!(
        selected.values[MeasurementField::InstantaneousPace.index()],
        30
    );
    assert!(!selected.truncated);
}
