use ftms::{capabilities::*, measurement::*, normalized::*, records::*, RangeOptions};

fn uuid(short: u16) -> [u8; 16] {
    [
        0,
        0,
        (short >> 8) as u8,
        short as u8,
        0,
        0,
        0x10,
        0,
        0x80,
        0,
        0,
        0x80,
        0x5f,
        0x9b,
        0x34,
        0xfb,
    ]
}
#[test]
fn capability_evidence_preserves_declaration_without_authority() {
    let feature = [1, 0, 0, 0, 1, 0, 0, 0];
    let chars = [
        Characteristic {
            uuid: uuid(0x2acc),
            properties: PROP_READ,
            read_state: ReadState::Success,
            read_reason: 0,
            bytes: &feature,
        },
        Characteristic {
            uuid: uuid(0x2ad4),
            properties: PROP_READ,
            read_state: ReadState::Success,
            read_reason: 0,
            bytes: &[0, 0, 100, 0, 1, 0],
        },
        Characteristic {
            uuid: uuid(0x2ad9),
            properties: PROP_WRITE | PROP_INDICATE,
            read_state: ReadState::NotAttempted,
            read_reason: 0,
            bytes: &[],
        },
        Characteristic {
            uuid: uuid(0x2ada),
            properties: PROP_NOTIFY,
            read_state: ReadState::NotAttempted,
            read_reason: 0,
            bytes: &[],
        },
    ];
    let report = evaluate_capabilities::<4, 16>(
        CapabilitySnapshot {
            discovery: Discovery::Complete,
            scope: ServiceScope::Present,
            generation: 7,
            characteristics: &chars,
            c7: C7Evidence {
                bonding_supported: Truth::False,
                feature_may_change_over_lifetime: Truth::Unknown,
            },
        },
        RangeOptions::default(),
    )
    .unwrap();
    assert_eq!(report.feature.decode, Decode::Valid);
    assert_eq!(report.operations[2].declaration, Declaration::Supported);
    assert_eq!(report.operations[2].prerequisite, Prerequisite::Satisfied);
}
#[test]
fn capability_c7_and_unread_evidence_are_incomplete_not_invalid() {
    let chars = [
        Characteristic {
            uuid: uuid(0x2acc),
            properties: PROP_READ | PROP_INDICATE,
            read_state: ReadState::NotAttempted,
            read_reason: 0,
            bytes: &[],
        },
        Characteristic {
            uuid: uuid(0x2ad9),
            properties: PROP_WRITE | PROP_INDICATE,
            read_state: ReadState::NotAttempted,
            read_reason: 0,
            bytes: &[],
        },
        Characteristic {
            uuid: uuid(0x2ada),
            properties: PROP_NOTIFY,
            read_state: ReadState::NotAttempted,
            read_reason: 0,
            bytes: &[],
        },
    ];
    let report = evaluate_capabilities::<3, 16>(
        CapabilitySnapshot {
            discovery: Discovery::Complete,
            scope: ServiceScope::Present,
            generation: 0,
            characteristics: &chars,
            c7: C7Evidence {
                bonding_supported: Truth::Unknown,
                feature_may_change_over_lifetime: Truth::Unknown,
            },
        },
        RangeOptions::default(),
    )
    .unwrap();
    assert_eq!(report.operations[2].prerequisite, Prerequisite::Incomplete);
    assert_ne!(report.operations[2].reasons & 0x400, 0);
    assert_ne!(report.operations[2].reasons & 4, 0);
}
#[test]
fn capability_rejects_invalid_read_evidence() {
    let c = Characteristic {
        uuid: uuid(0x2acc),
        properties: PROP_READ,
        read_state: ReadState::NotAttempted,
        read_reason: 1,
        bytes: &[],
    };
    assert_eq!(
        evaluate_capabilities::<1, 1>(
            CapabilitySnapshot {
                discovery: Discovery::Complete,
                scope: ServiceScope::Present,
                generation: 0,
                characteristics: &[c],
                c7: C7Evidence {
                    bonding_supported: Truth::False,
                    feature_may_change_over_lifetime: Truth::False
                }
            },
            RangeOptions::default()
        ),
        Err(ftms::Error::InvalidRange)
    );
    let c = Characteristic {
        read_state: ReadState::Failed,
        read_reason: 1,
        bytes: &[1],
        ..c
    };
    assert_eq!(
        evaluate_capabilities::<1, 1>(
            CapabilitySnapshot {
                discovery: Discovery::Complete,
                scope: ServiceScope::Present,
                generation: 0,
                characteristics: &[c],
                c7: C7Evidence {
                    bonding_supported: Truth::False,
                    feature_may_change_over_lifetime: Truth::False
                }
            },
            RangeOptions::default()
        ),
        Err(ftms::Error::InvalidRange)
    );
}
#[test]
fn normalized_preserves_absence_and_unavailable() {
    let mut m = RawMeasurement::new(MeasurementKind::IndoorBike);
    assert_eq!(
        normalized_measurement(&m, MeasurementOptions::default(), Metric::PowerWatts),
        None
    );
    m.present = MeasurementField::Power.mask();
    m.unavailable = m.present;
    assert_eq!(
        normalized_measurement(&m, MeasurementOptions::default(), Metric::PowerWatts),
        Some(NormalizedValue::Unavailable)
    );
}
#[test]
fn planner_and_assembler_use_caller_budget_and_clock() {
    let mut m = RawMeasurement::new(MeasurementKind::IndoorBike);
    m.flags = (1 << 2) | (1 << 6);
    m.present = selected_fields(m.kind, m.flags, MeasurementOptions::default());
    m.values[MeasurementField::Speed.index()] = 100;
    m.values[MeasurementField::Cadence.index()] = 120;
    m.values[MeasurementField::Power.index()] = 200;
    let mut packets = [MeasurementPacket::default(); 4];
    let n = plan_measurement(&m, MeasurementOptions::default(), 6, &mut packets).unwrap();
    assert!(n > 1);
    let mut a = RecordAssembler::new(m.kind, MeasurementOptions::default(), 3, 10).unwrap();
    let mut out = RawMeasurement::new(m.kind);
    for p in &packets[..n - 1] {
        assert_eq!(
            a.feed(&p.value[..p.length], 3, 1, &mut out),
            RecordStatus::Pending
        );
    }
    assert_eq!(
        a.feed(
            &packets[n - 1].value[..packets[n - 1].length],
            3,
            2,
            &mut out
        ),
        RecordStatus::Complete
    );
    assert_eq!(out.present, m.present);
}
#[test]
fn planner_and_assembler_boundaries_across_kinds() {
    for kind in [
        MeasurementKind::Treadmill,
        MeasurementKind::CrossTrainer,
        MeasurementKind::StepClimber,
        MeasurementKind::StairClimber,
        MeasurementKind::Rower,
        MeasurementKind::IndoorBike,
    ] {
        let mut m = RawMeasurement::new(kind);
        m.flags = 0;
        m.present = selected_fields(kind, 0, MeasurementOptions::default());
        m.values[0] = 1;
        let mut packets = [MeasurementPacket::default(); 1];
        let before = packets;
        assert!(plan_measurement(&m, MeasurementOptions::default(), 1, &mut packets).is_err());
        assert_eq!(packets, before);
        assert_eq!(
            plan_measurement(&m, MeasurementOptions::default(), 64, &mut packets).unwrap(),
            1
        );
        let mut a = RecordAssembler::new(kind, MeasurementOptions::default(), 9, 2).unwrap();
        let mut out = RawMeasurement::new(kind);
        assert_eq!(
            a.feed(&packets[0].value[..packets[0].length], 8, 0, &mut out),
            RecordStatus::Generation
        );
        assert_eq!(
            a.feed(&packets[0].value[..packets[0].length], 9, 0, &mut out),
            RecordStatus::Complete
        );
    }
}
#[test]
fn assembler_expiry_duplicate_and_cross_direction_reject() {
    let mut m = RawMeasurement::new(MeasurementKind::CrossTrainer);
    m.flags = 1 | (1 << 15);
    m.present = selected_fields(m.kind, m.flags, MeasurementOptions::default());
    m.values[MeasurementField::Speed.index()] = 1;
    let mut b = [0; 64];
    let n = encode_measurement(&m, MeasurementOptions::default(), &mut b).unwrap();
    let mut a = RecordAssembler::new(m.kind, MeasurementOptions::default(), 1, 1).unwrap();
    let mut out = RawMeasurement::new(m.kind);
    assert_eq!(a.feed(&b[..n], 1, 0, &mut out), RecordStatus::Pending);
    assert_eq!(a.feed(&b[..n], 1, 1, &mut out), RecordStatus::Expired);
}
#[test]
fn planner_rejects_late_oversized_group_atomically_and_preserves_split_sentinels() {
    let mut m = RawMeasurement::new(MeasurementKind::Treadmill);
    m.flags = (1 << 1) | (1 << 7);
    m.present = selected_fields(m.kind, m.flags, MeasurementOptions::default());
    m.values[MeasurementField::Speed.index()] = 1;
    m.values[MeasurementField::AverageSpeed.index()] = 1;
    let energy = MeasurementField::Energy.mask()
        | MeasurementField::EnergyPerHour.mask()
        | MeasurementField::EnergyPerMinute.mask();
    m.unavailable = energy;
    let mut packets = [MeasurementPacket::default(); 4];
    packets[0].value[0] = 0xaa;
    let before = packets;
    assert!(plan_measurement(&m, MeasurementOptions::default(), 4, &mut packets).is_err());
    assert_eq!(packets, before);
    let n = plan_measurement(&m, MeasurementOptions::default(), 7, &mut packets).unwrap();
    assert!(n >= 3);
    assert!(packets[..n].iter().all(|p| p.length <= 7));
    let decoded = decode_measurement(
        m.kind,
        &packets[1].value[..packets[1].length],
        MeasurementOptions::default(),
    )
    .unwrap();
    assert_ne!(decoded.unavailable & energy, 0);
}
