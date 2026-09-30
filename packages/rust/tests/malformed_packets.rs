use ftms::{measurement::*, status::*, Error};

fn next(seed: &mut u32) -> u32 {
    *seed ^= *seed << 13;
    *seed ^= *seed >> 17;
    *seed ^= *seed << 5;
    *seed
}

/// Deterministic malformed-input regression, not coverage-guided fuzzing or
/// exhaustive values coverage. Includes lengths beyond the largest wire layout.
#[test]
fn ten_thousand_bounded_arbitrary_packets() {
    let mut seed = 0x4654_4d53;
    for _ in 0..10_000 {
        let len = (next(&mut seed) % 80) as usize;
        let mut wire = vec![0; len];
        for b in &mut wire {
            *b = next(&mut seed) as u8;
        }
        for kind in 0..6 {
            let kind = MeasurementKind::try_from(kind).unwrap();
            for resistance_format in [
                MeasurementResistanceFormat::Uint8Whole,
                MeasurementResistanceFormat::Signed16Tenths,
            ] {
                for treadmill_pace_format in [
                    TreadmillPaceFormat::Uint16,
                    TreadmillPaceFormat::Uint8Legacy,
                ] {
                    let options = MeasurementOptions {
                        resistance_format,
                        treadmill_pace_format,
                    };
                    match decode_measurement(kind, &wire, options) {
                        Ok(value) => {
                            assert!(value.bytes_read <= wire.len());
                            assert_eq!(value.unavailable & !value.present, 0);
                            assert!(!(value.truncated && value.trailing_bytes));
                            let mut out = [0xa5; 80];
                            if value.truncated || value.reserved_flags {
                                assert_eq!(
                                    encode_measurement(&value, options, &mut out),
                                    Err(Error::InvalidRange)
                                );
                                assert_eq!(out, [0xa5; 80]);
                            } else {
                                // Complete known fields re-encode, deliberately excluding
                                // trailing bytes (diagnostics are not encoder inputs).
                                assert_eq!(
                                    encode_measurement(&value, options, &mut out),
                                    Ok(value.bytes_read)
                                );
                                assert_eq!(&out[..value.bytes_read], &wire[..value.bytes_read]);
                                assert!(out[value.bytes_read..].iter().all(|b| *b == 0xa5));
                            }
                        }
                        Err(Error::WrongLength { expected, actual }) => {
                            assert_eq!(actual, len);
                            assert!(len < expected);
                            assert_eq!(
                                expected,
                                if kind == MeasurementKind::CrossTrainer {
                                    3
                                } else {
                                    2
                                }
                            );
                        }
                        Err(error) => panic!("unexpected measurement decode error {error:?}"),
                    }
                }
            }
        }
        let machine = decode_machine_status(&wire);
        let mut out = [0xa5; 80];
        if machine.unknown_opcode
            || machine.reserved_value
            || machine.truncated
            || machine.trailing_bytes
        {
            assert!(encode_machine_status(&machine, &mut out).is_err());
            assert_eq!(out, [0xa5; 80]);
        } else {
            assert_eq!(encode_machine_status(&machine, &mut out), Ok(wire.len()));
            assert_eq!(&out[..wire.len()], wire);
            assert!(out[wire.len()..].iter().all(|b| *b == 0xa5));
        }
        let training = decode_training_status(&wire);
        let mut out = [0xa5; 80];
        if training.reserved_value
            || training.invalid_flags
            || training.invalid_utf8
            || training.truncated
            || training.trailing_bytes
            || training.reserved_flags != 0
        {
            assert!(encode_training_status(&training, &mut out).is_err());
            assert_eq!(out, [0xa5; 80]);
        } else {
            assert_eq!(encode_training_status(&training, &mut out), Ok(wire.len()));
            assert_eq!(&out[..wire.len()], wire);
            assert!(out[wire.len()..].iter().all(|b| *b == 0xa5));
        }
    }
}
