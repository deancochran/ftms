use ftms::*;

fn request(opcode: u8, operands: [i32; 5], count: usize) -> ControlRequest {
    ControlRequest {
        opcode,
        operands,
        operand_count: count,
    }
}

#[test]
fn feature_range_request_and_response_lengths_reject_every_improper_prefix() {
    for n in 0..8 {
        assert!(decode_features(&vec![0; n]).is_err());
    }
    assert!(decode_features(&[0; 9]).is_err());
    for (kind, bytes) in [
        (RangeKind::Speed, vec![0; 6]),
        (RangeKind::Resistance, vec![0; 3]),
    ] {
        for n in 0..bytes.len() {
            assert!(
                decode_range(kind, &bytes[..n], RangeOptions::default()).is_err(),
                "{kind:?} prefix {n}"
            );
        }
        assert!(decode_range(kind, &[0; 7], RangeOptions::default()).is_err());
    }
    for (bytes, options) in [
        (&[2, 1, 0][..], ControlOptions::default()),
        (
            &[4, 1][..],
            ControlOptions {
                resistance_format: ResistanceControlFormat::Uint8Tenths,
            },
        ),
        (&[17, 0, 0, 0, 0, 0, 0][..], ControlOptions::default()),
    ] {
        for n in 0..bytes.len() {
            assert!(
                decode_control_request(&bytes[..n], options).is_err(),
                "request prefix {n}"
            );
        }
    }
    for n in [0, 1, 2, 4, 5, 6] {
        assert!(decode_control_response(&[0x80, 19, 1, 0, 0, 0, 0][..n]).is_err());
    }
    assert!(
        decode_control_response(&[0x80, 2, 1, 7]).is_ok(),
        "generic response trailing evidence is diagnostic, not an error"
    );
}

#[test]
fn control_encode_validates_all_widths_and_never_writes_invalid_data() {
    let widths: &[(u8, usize, i32, i32, i32, i32)] = &[
        (2, 0, 0, 65535, -1, 65536),
        (3, 0, -32768, 32767, -32769, 32768),
        (4, 0, -32768, 32767, -32769, 32768),
        (5, 0, -32768, 32767, -32769, 32768),
        (6, 0, 0, 255, -1, 256),
        (9, 0, 0, 65535, -1, 65536),
        (10, 0, 0, 65535, -1, 65536),
        (11, 0, 0, 65535, -1, 65536),
        (12, 0, 0, 0x00ff_ffff, -1, 0x0100_0000),
        (13, 0, 0, 65535, -1, 65536),
        (14, 0, 0, 65535, -1, 65536),
        (14, 1, 0, 65535, -1, 65536),
        (15, 0, 0, 65535, -1, 65536),
        (15, 1, 0, 65535, -1, 65536),
        (15, 2, 0, 65535, -1, 65536),
        (16, 0, 0, 65535, -1, 65536),
        (16, 1, 0, 65535, -1, 65536),
        (16, 2, 0, 65535, -1, 65536),
        (16, 3, 0, 65535, -1, 65536),
        (16, 4, 0, 65535, -1, 65536),
        (17, 0, -32768, 32767, -32769, 32768),
        (17, 1, -32768, 32767, -32769, 32768),
        (17, 2, 0, 255, -1, 256),
        (17, 3, 0, 255, -1, 256),
        (18, 0, 0, 65535, -1, 65536),
        (20, 0, 0, 65535, -1, 65536),
    ];
    for &(opcode, position, min, max, below, above) in widths {
        let count = match opcode {
            14 => 2,
            15 => 3,
            16 => 5,
            17 => 4,
            _ => 1,
        };
        for (value, valid) in [(min, true), (max, true), (below, false), (above, false)] {
            let mut values = [0; 5];
            values[position] = value;
            let mut out = [0xa5; 11];
            let result = encode_control_request(
                request(opcode, values, count),
                ControlOptions::default(),
                &mut out,
            );
            if valid {
                assert!(result.is_ok(), "{opcode}/{position}/{value}");
            } else {
                assert_eq!(result, Err(Error::InvalidRange));
                assert_eq!(out, [0xa5; 11]);
            }
        }
    }
    for (value, valid) in [(0, true), (255, true), (-1, false), (256, false)] {
        let mut out = [0xa5; 11];
        let result = encode_control_request(
            request(4, [value, 0, 0, 0, 0], 1),
            ControlOptions {
                resistance_format: ResistanceControlFormat::Uint8Tenths,
            },
            &mut out,
        );
        if valid {
            assert!(result.is_ok());
        } else {
            assert_eq!(result, Err(Error::InvalidRange));
            assert_eq!(out, [0xa5; 11]);
        }
    }
    for (opcode, value) in [(8, 1), (8, 2), (19, 1), (19, 2)] {
        assert!(encode_control_request(
            request(opcode, [value, 0, 0, 0, 0], 1),
            ControlOptions::default(),
            &mut [0; 11]
        )
        .is_ok());
    }
    for opcode in [8, 19] {
        for value in [0, 3, -1, 256] {
            let mut out = [0xa5; 11];
            assert_eq!(
                encode_control_request(
                    request(opcode, [value, 0, 0, 0, 0], 1),
                    ControlOptions::default(),
                    &mut out
                ),
                Err(Error::InvalidRange)
            );
            assert_eq!(out, [0xa5; 11]);
        }
    }
}

#[test]
fn capacities_and_response_encode_errors_preserve_output() {
    let range = RawRange {
        kind: RangeKind::Power,
        minimum: -1,
        maximum: 1,
        increment: 1,
        scale_divisor: 1,
        unit: RangeUnit::Watts,
    };
    let mut small = [0xa5; 5];
    assert_eq!(
        encode_range(range, RangeOptions::default(), &mut small),
        Err(Error::InsufficientStorage {
            required: 6,
            available: 5
        })
    );
    assert_eq!(small, [0xa5; 5]);
    let mut short = [0xa5; 1];
    assert_eq!(
        encode_control_request(
            request(2, [-1, 0, 0, 0, 0], 1),
            ControlOptions::default(),
            &mut short
        ),
        Err(Error::InvalidRange)
    );
    assert_eq!(short, [0xa5]);
    let base = ControlResponse {
        request_opcode: 2,
        result_code: 99,
        parameter: 0,
        low: 0,
        high: 0,
        unknown_request: 0,
        unknown_result: 0,
        unexpected_parameters: 0,
    };
    assert_eq!(
        encode_control_response(base, &mut [0; 7]),
        Err(Error::InvalidRange)
    );
    let unknown = ControlResponse {
        request_opcode: 250,
        result_code: 1,
        ..base
    };
    assert_eq!(
        encode_control_response(unknown, &mut [0; 7]),
        Err(Error::InvalidKind)
    );
}
#[test]
fn resistance_control_profile_does_not_change_other_opcodes() {
    let alternate = ControlOptions {
        resistance_format: ResistanceControlFormat::Uint8Tenths,
    };
    for opcode in 0..=20 {
        if opcode == 4 {
            continue;
        }
        let count = match opcode {
            0 | 1 | 7 => 0,
            14 => 2,
            15 => 3,
            16 => 5,
            17 => 4,
            _ => 1,
        };
        let mut operands = [1; 5];
        if matches!(opcode, 3 | 5 | 17) {
            operands[0] = -123;
        }
        let request = ControlRequest {
            opcode,
            operands,
            operand_count: count,
        };
        let mut normal = [0; 11];
        let mut other = [0; 11];
        let n = encode_control_request(request, ControlOptions::default(), &mut normal).unwrap();
        assert_eq!(
            encode_control_request(request, alternate, &mut other),
            Ok(n)
        );
        assert_eq!(normal, other);
        let expected = decode_control_request(&normal[..n], ControlOptions::default()).unwrap();
        assert_eq!(
            decode_control_request(&normal[..n], alternate),
            Ok(expected),
            "opcode {opcode}"
        );
        assert_eq!(&expected.operands[..count], &operands[..count]);
    }
}
