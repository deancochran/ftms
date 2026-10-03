use ftms::{
    measurement::{MeasurementKind, MeasurementOptions, TreadmillPaceFormat},
    normalized::{Metric, NormalizedValue},
    universal::*,
};

#[test]
fn all_six_uuid_layouts_and_prefixes_use_existing_raw_decoder() {
    let cases = [
        (
            TREADMILL_DATA_UUID,
            MeasurementKind::Treadmill,
            &[0, 0, 1, 0][..],
        ),
        (
            CROSS_TRAINER_DATA_UUID,
            MeasurementKind::CrossTrainer,
            &[0, 0, 0, 1, 0][..],
        ),
        (
            STEP_CLIMBER_DATA_UUID,
            MeasurementKind::StepClimber,
            &[0, 0, 1, 0, 1, 0][..],
        ),
        (
            STAIR_CLIMBER_DATA_UUID,
            MeasurementKind::StairClimber,
            &[0, 0, 1, 0][..],
        ),
        (
            ROWER_DATA_UUID,
            MeasurementKind::Rower,
            &[0, 0, 1, 1, 0][..],
        ),
        (
            INDOOR_BIKE_DATA_UUID,
            MeasurementKind::IndoorBike,
            &[0, 0, 1, 0][..],
        ),
    ];
    for (uuid, kind, bytes) in cases {
        let UniversalMeasurementDecode::Known(value) =
            decode_measurement_uuid(uuid, bytes, MeasurementOptions::default()).unwrap()
        else {
            panic!("known UUID");
        };
        assert_eq!(value.raw.kind, kind);
        let prefix_len = if kind == MeasurementKind::CrossTrainer {
            3
        } else {
            2
        };
        let UniversalMeasurementDecode::Known(prefix) =
            decode_measurement_uuid(uuid, &bytes[..prefix_len], MeasurementOptions::default())
                .unwrap()
        else {
            panic!("known UUID");
        };
        assert!(prefix.raw.truncated);
    }
}

#[test]
fn format_and_sentinel_states_are_retained_for_normalized_access() {
    let legacy = MeasurementOptions {
        treadmill_pace_format: TreadmillPaceFormat::Uint8Legacy,
        ..MeasurementOptions::default()
    };
    let UniversalMeasurementDecode::Known(legacy_value) =
        decode_measurement_uuid(TREADMILL_DATA_UUID, &[0x20, 0, 1, 0, 7], legacy).unwrap()
    else {
        panic!();
    };
    assert_eq!(
        legacy_value.metric(Metric::InstantaneousPaceSecondsPer500Metres),
        Some(NormalizedValue::UnknownUnit)
    );
    let UniversalMeasurementDecode::Known(sentinel) = decode_measurement_uuid(
        TREADMILL_DATA_UUID,
        &[0x80, 0, 1, 0, 255, 255, 255],
        MeasurementOptions::default(),
    )
    .unwrap() else {
        panic!();
    };
    assert_eq!(
        sentinel.metric(Metric::EnergyKcal),
        Some(NormalizedValue::Unavailable)
    );
}

#[test]
fn vendor_low_word_is_not_a_sig_uuid() {
    let mut vendor = INDOOR_BIKE_DATA_UUID;
    vendor[0] = 1;
    assert_eq!(measurement_kind_for_uuid(vendor), None);
    assert_eq!(
        decode_measurement_uuid(vendor, &[0, 0], MeasurementOptions::default()).unwrap(),
        UniversalMeasurementDecode::Unsupported
    );
}
