use ftms::{measurement::*, normalized::*, status::*, *};
use ftms::universal::*;

fn main() {
    let raw = RawFeatures {
        machine: 0x8000_0000,
        target: 0x4000_0000,
    };
    assert_eq!(decode_features(&encode_features(raw)), Ok(raw));
    assert!(!normalize_features(raw).supports_erg());
    assert_eq!(
        normalize_control_request(NormalizedControlRequest::TargetSpeedKph(12.34))
            .unwrap()
            .opcode,
        2
    );
    let range = RawRange {
        kind: RangeKind::Power,
        minimum: -100,
        maximum: 4000,
        increment: 5,
        scale_divisor: 1,
        unit: RangeUnit::Watts,
    };
    let mut range_bytes = [0; 6];
    assert_eq!(
        encode_range(range, RangeOptions::default(), &mut range_bytes),
        Ok(6)
    );
    assert_eq!(range_bytes, [156, 255, 160, 15, 5, 0]);
    assert_eq!(
        decode_range(RangeKind::Power, &range_bytes, RangeOptions::default()),
        Ok(range)
    );
    assert_eq!(normalize_range(range).maximum, 4000.0);
    let request = ControlRequest {
        opcode: 4,
        operands: [-10, 0, 0, 0, 0],
        operand_count: 1,
    };
    let mut request_bytes = [0; 11];
    assert_eq!(
        encode_control_request(request, ControlOptions::default(), &mut request_bytes),
        Ok(3)
    );
    assert_eq!(&request_bytes[..3], &[4, 246, 255]);
    assert_eq!(
        decode_control_request(&request_bytes[..3], ControlOptions::default()),
        Ok(request)
    );

    for (kind, wire, present) in [
        (
            MeasurementKind::Treadmill,
            &[0, 0, 100, 0][..],
            MeasurementField::Speed.mask(),
        ),
        (
            MeasurementKind::CrossTrainer,
            &[0, 0, 0, 100, 0][..],
            MeasurementField::Speed.mask(),
        ),
        (
            MeasurementKind::StepClimber,
            &[0, 0, 1, 0, 2, 0][..],
            MeasurementField::FloorCount.mask() | MeasurementField::StepCount.mask(),
        ),
        (
            MeasurementKind::StairClimber,
            &[0, 0, 1, 0][..],
            MeasurementField::FloorCount.mask(),
        ),
        (
            MeasurementKind::Rower,
            &[0, 0, 60, 2, 0][..],
            MeasurementField::StrokeRate.mask() | MeasurementField::StrokeCount.mask(),
        ),
        (
            MeasurementKind::IndoorBike,
            &[0, 0, 100, 0][..],
            MeasurementField::Speed.mask(),
        ),
    ] {
        let value = decode_measurement(kind, wire, MeasurementOptions::default()).unwrap();
        assert_eq!(value.present, present);
        assert!(!value.truncated);
        assert!(!value.trailing_bytes);
        let mut out = [0; 64];
        let n = encode_measurement(&value, MeasurementOptions::default(), &mut out).unwrap();
        assert_eq!(&out[..n], wire);
    }
    let options = MeasurementOptions {
        resistance_format: MeasurementResistanceFormat::Signed16Tenths,
        ..MeasurementOptions::default()
    };
    let bike =
        decode_measurement(MeasurementKind::IndoorBike, &[33, 0, 246, 255], options).unwrap();
    assert_eq!(bike.values[MeasurementField::Resistance.index()], -10);
    let mut out = [0; 4];
    assert_eq!(encode_measurement(&bike, options, &mut out), Ok(4));
    assert_eq!(out, [33, 0, 246, 255]);

    let UniversalMeasurementDecode::Known(universal) = decode_measurement_uuid(
        TREADMILL_DATA_UUID,
        &[0, 0, 104, 1],
        MeasurementOptions::default(),
    )
    .unwrap() else {
        panic!("known treadmill UUID")
    };
    assert_eq!(universal.raw.kind, MeasurementKind::Treadmill);
    assert_eq!(
        universal.metric(Metric::SpeedMetresPerSecond),
        Some(NormalizedValue::Number(1.0))
    );
    let legacy = MeasurementOptions {
        treadmill_pace_format: TreadmillPaceFormat::Uint8Legacy,
        ..MeasurementOptions::default()
    };
    let UniversalMeasurementDecode::Known(legacy_value) =
        decode_measurement_uuid(TREADMILL_DATA_UUID, &[0x20, 0, 1, 0, 7], legacy).unwrap()
    else {
        panic!("known treadmill UUID")
    };
    assert_eq!(
        legacy_value.metric(Metric::InstantaneousPaceSecondsPer500Metres),
        Some(NormalizedValue::UnknownUnit)
    );
    let mut vendor = INDOOR_BIKE_DATA_UUID;
    vendor[0] = 1;
    assert_eq!(
        decode_measurement_uuid(vendor, &[0, 0], MeasurementOptions::default()).unwrap(),
        UniversalMeasurementDecode::Unsupported
    );

    let machine = RawMachineStatus {
        opcode: 0x14,
        action: 4,
        ..RawMachineStatus::default()
    };
    let mut out = [0; 2];
    assert_eq!(encode_machine_status(&machine, &mut out), Ok(2));
    assert_eq!(out, [0x14, 4]);
    assert_eq!(decode_machine_status(&out), machine);
    assert_eq!(
        normalize_machine_status(machine).unwrap().label,
        "spin_down_status"
    );
    assert_eq!(normalize_machine_status(machine).unwrap().action, Some(4));
    let training = RawTrainingStatus {
        flags: 3,
        code: 2,
        text: b"Ready",
        ..RawTrainingStatus::default()
    };
    let mut out = [0; 7];
    assert_eq!(encode_training_status(&training, &mut out), Ok(7));
    assert_eq!(&out, b"\x03\x02Ready");
    assert_eq!(decode_training_status(&out).text, b"Ready");
}
