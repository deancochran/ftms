mod support;

use ftms::{status::*, ControlRequest, Error};
use serde_json::Value;

const VECTORS: &str = include_str!("../../../shared/conformance/statuses/v1/vectors.json");

fn reject_machine(value: &RawMachineStatus) {
    let mut out = [0xa5; 16];
    assert!(encode_machine_status(value, &mut out).is_err());
    assert_eq!(out, [0xa5; 16]);
}

fn reject_training(value: &RawTrainingStatus<'_>) {
    let mut out = [0xa5; 16];
    assert_eq!(
        encode_training_status(value, &mut out),
        Err(Error::InvalidRange)
    );
    assert_eq!(out, [0xa5; 16]);
}

#[test]
fn every_machine_opcode_prefix_parameter_and_capacity() {
    let corpus: Value = serde_json::from_str(VECTORS).unwrap();
    let mut seen = std::collections::BTreeSet::new();
    for case in corpus["machine"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|c| c["encode"] == true)
    {
        let wire = support::bytes(&case["bytes"]);
        let value = decode_machine_status(&wire);
        seen.insert(value.opcode);
        for size in 0..wire.len() {
            let partial = decode_machine_status(&wire[..size]);
            assert_eq!(
                partial,
                RawMachineStatus {
                    opcode: if size == 0 { 0 } else { value.opcode },
                    unknown_opcode: size == 0,
                    truncated: true,
                    ..RawMachineStatus::default()
                }
            );
            reject_machine(&partial);
        }
        for capacity in 0..wire.len() {
            let mut out = vec![0xa5; capacity];
            assert_eq!(
                encode_machine_status(&value, &mut out),
                Err(Error::InsufficientStorage {
                    required: wire.len(),
                    available: capacity,
                })
            );
            assert!(out.iter().all(|b| *b == 0xa5));
        }
        let mut out = [0xa5; 16];
        assert_eq!(encode_machine_status(&value, &mut out), Ok(wire.len()));
        assert_eq!(&out[..wire.len()], wire);
        assert!(out[wire.len()..].iter().all(|b| *b == 0xa5));

        let mut extra = wire.clone();
        extra.push(0x5a);
        assert_eq!(
            decode_machine_status(&extra),
            RawMachineStatus {
                trailing_bytes: true,
                ..value
            }
        );
        reject_machine(&decode_machine_status(&extra));
        for index in 0..4 {
            let mut invalid = value;
            match index {
                0 => invalid.unknown_opcode = true,
                1 => invalid.reserved_value = true,
                2 => invalid.truncated = true,
                _ => invalid.trailing_bytes = true,
            }
            reject_machine(&invalid);
        }
        if let Some(parameter) = value.parameter {
            reject_machine(&RawMachineStatus {
                parameter: None,
                ..value
            });
            reject_machine(&RawMachineStatus {
                parameter: Some(ControlRequest {
                    opcode: 0xff,
                    ..parameter
                }),
                ..value
            });
            for count in [0, parameter.operand_count + 1, usize::MAX] {
                reject_machine(&RawMachineStatus {
                    parameter: Some(ControlRequest {
                        operand_count: count,
                        ..parameter
                    }),
                    ..value
                });
            }
            for operand in 0..parameter.operand_count {
                for invalid in [i32::MIN, i32::MAX] {
                    let mut mutated = parameter;
                    mutated.operands[operand] = invalid;
                    reject_machine(&RawMachineStatus {
                        parameter: Some(mutated),
                        ..value
                    });
                }
            }
        } else {
            reject_machine(&RawMachineStatus {
                parameter: Some(ControlRequest {
                    opcode: 0,
                    operand_count: 0,
                    operands: [0; 5],
                }),
                ..value
            });
        }
    }
    assert_eq!(seen, (1..=0x15).chain([0xff]).collect());

    for opcode in 0..=255 {
        if seen.contains(&opcode) {
            continue;
        }
        for wire in [vec![opcode], vec![opcode, 1, 2, 3]] {
            let value = decode_machine_status(&wire);
            assert_eq!(
                value,
                RawMachineStatus {
                    opcode,
                    unknown_opcode: true,
                    ..RawMachineStatus::default()
                }
            );
            reject_machine(&value);
        }
    }
}

#[test]
fn every_stop_pause_and_spin_down_status_action() {
    for (opcode, maximum) in [(2, 2), (0x14, 4)] {
        for action in 0..=255 {
            let valid = (1..=maximum).contains(&action);
            let value = decode_machine_status(&[opcode, action]);
            assert_eq!(
                value,
                RawMachineStatus {
                    opcode,
                    action,
                    reserved_value: !valid,
                    ..RawMachineStatus::default()
                }
            );
            let input = RawMachineStatus {
                opcode,
                action,
                ..RawMachineStatus::default()
            };
            if valid {
                let mut out = [0xa5; 3];
                assert_eq!(encode_machine_status(&input, &mut out), Ok(2));
                assert_eq!(out, [opcode, action, 0xa5]);
            } else {
                reject_machine(&value);
                reject_machine(&input);
            }
        }
    }
    // Status 0x07 does not share the explicitly selectable UINT8 command format.
    let value = decode_machine_status(&[7, 0xff, 0x7f]);
    assert_eq!(value.parameter.unwrap().operands[0], 32767);
    assert_eq!(decode_machine_status(&[7, 0]).parameter, None);
    assert!(decode_machine_status(&[7, 0]).truncated);
    assert_eq!(
        decode_machine_status(&[7, 0, 0x80])
            .parameter
            .unwrap()
            .operands[0],
        -32768
    );
}

#[test]
fn every_training_flag_code_and_partial_header() {
    assert_eq!(
        decode_training_status(&[]),
        RawTrainingStatus {
            truncated: true,
            ..RawTrainingStatus::default()
        }
    );
    for flags in 0..=255 {
        let partial = decode_training_status(std::slice::from_ref(&flags));
        assert_eq!(
            partial,
            RawTrainingStatus {
                flags,
                truncated: true,
                ..RawTrainingStatus::default()
            }
        );
        reject_training(&partial);
        for code in 0..=255 {
            let bytes = [flags, code, b'a'];
            let value = decode_training_status(&bytes);
            let present = flags & 1 != 0;
            assert_eq!(
                value,
                RawTrainingStatus {
                    flags,
                    code,
                    text: if present { b"a" } else { b"" },
                    text_offset: if present { 2 } else { 0 },
                    text_present: present,
                    extended_string: flags & 2 != 0,
                    reserved_value: code > 15,
                    invalid_flags: flags & 3 == 2,
                    trailing_bytes: !present,
                    reserved_flags: flags & 0xfc,
                    ..RawTrainingStatus::default()
                }
            );
            let valid = code <= 15 && flags <= 3 && flags != 2;
            let input = RawTrainingStatus {
                flags,
                code,
                text: if present { b"a" } else { b"" },
                ..RawTrainingStatus::default()
            };
            if valid {
                let mut out = [0xa5; 4];
                let n = if present { 3 } else { 2 };
                assert_eq!(encode_training_status(&input, &mut out), Ok(n));
                assert_eq!(&out[..n], &bytes[..n]);
                assert!(out[n..].iter().all(|b| *b == 0xa5));
                if !present {
                    reject_training(&value);
                }
            } else {
                reject_training(&value);
                reject_training(&input);
            }
        }
    }
}

#[test]
fn training_utf8_borrowing_diagnostics_and_capacity() {
    let valid: &[&[u8]] = &[
        b"",
        b"a\0b",
        b"\x7f",
        b"\xc2\x80",
        b"\xdf\xbf",
        b"\xe0\xa0\x80",
        b"\xed\x9f\xbf",
        b"\xee\x80\x80",
        b"\xef\xbf\xbf",
        b"\xf0\x90\x80\x80",
        b"\xf4\x8f\xbf\xbf",
        "Ready ✓ 🚲".as_bytes(),
    ];
    let invalid: &[&[u8]] = &[
        b"\x80",
        b"\xbf",
        b"\xc0\x80",
        b"\xc1\xbf",
        b"\xc2",
        b"\xc2\x20",
        b"\xe0\x9f\xbf",
        b"\xed\xa0\x80",
        b"\xef\xbf",
        b"\xf0\x8f\xbf\xbf",
        b"\xf4\x90\x80\x80",
        b"\xf5\x80\x80\x80",
        b"\xff",
        b"a\xf0\x90\x80",
    ];
    for (texts, invalid_utf8) in [(valid, false), (invalid, true)] {
        for text in texts {
            let mut bytes = vec![3, 15];
            bytes.extend_from_slice(text);
            let value = decode_training_status(&bytes);
            assert_eq!(value.text, *text);
            assert_eq!(value.text.as_ptr(), bytes[2..].as_ptr());
            assert_eq!(value.invalid_utf8, invalid_utf8);
            if invalid_utf8 {
                reject_training(&value);
                reject_training(&RawTrainingStatus {
                    flags: 1,
                    text,
                    ..RawTrainingStatus::default()
                });
            } else {
                for capacity in 0..bytes.len() {
                    let mut out = vec![0xa5; capacity];
                    assert_eq!(
                        encode_training_status(&value, &mut out),
                        Err(Error::InsufficientStorage {
                            required: bytes.len(),
                            available: capacity
                        })
                    );
                    assert!(out.iter().all(|b| *b == 0xa5));
                }
                let mut out = vec![0xa5; bytes.len() + 2];
                assert_eq!(encode_training_status(&value, &mut out), Ok(bytes.len()));
                assert_eq!(&out[..bytes.len()], bytes);
                assert_eq!(&out[bytes.len()..], &[0xa5; 2]);
            }
        }
    }
    let value = RawTrainingStatus {
        flags: 3,
        code: 1,
        text: b"ok",
        ..RawTrainingStatus::default()
    };
    for index in 0..7 {
        let mut invalid = value;
        match index {
            0 => invalid.reserved_value = true,
            1 => invalid.invalid_flags = true,
            2 => invalid.invalid_utf8 = true,
            3 => invalid.truncated = true,
            4 => invalid.trailing_bytes = true,
            5 => invalid.reserved_flags = 4,
            _ => invalid.flags = 0, // text supplied without presence
        }
        reject_training(&invalid);
    }
    // Offsets and descriptive booleans do not override authoritative flags/text.
    let input = RawTrainingStatus {
        text_offset: usize::MAX,
        ..value
    };
    let mut out = [0xa5; 5];
    assert_eq!(encode_training_status(&input, &mut out), Ok(4));
    assert_eq!(out, [3, 1, b'o', b'k', 0xa5]);

    // Caller-bounded text, not a protocol-library fixed-size scratch buffer.
    let text = vec![b'x'; 8192];
    let input = RawTrainingStatus {
        flags: 1,
        text: &text,
        ..RawTrainingStatus::default()
    };
    let mut out = vec![0; text.len() + 2];
    assert_eq!(encode_training_status(&input, &mut out), Ok(text.len() + 2));
    assert_eq!(decode_training_status(&out).text, text);
}
