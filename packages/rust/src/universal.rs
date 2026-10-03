//! UUID-selected convenience decoding for FTMS measurements.
//!
//! UUIDs are canonical Bluetooth display/network-order bytes. Recognition is a
//! full 128-bit comparison, so a vendor UUID sharing a SIG low word is not
//! treated as FTMS data. This module selects an existing raw layout; it does not
//! infer equipment identity or a format from packet bytes.

use crate::{
    measurement::{decode_measurement, MeasurementKind, MeasurementOptions, RawMeasurement},
    normalized::{normalized_measurement, Metric, NormalizedValue},
    Error,
};

pub const TREADMILL_DATA_UUID: [u8; 16] = [
    0, 0, 0x2a, 0xcd, 0, 0, 0x10, 0, 0x80, 0, 0, 0x80, 0x5f, 0x9b, 0x34, 0xfb,
];
pub const CROSS_TRAINER_DATA_UUID: [u8; 16] = [
    0, 0, 0x2a, 0xce, 0, 0, 0x10, 0, 0x80, 0, 0, 0x80, 0x5f, 0x9b, 0x34, 0xfb,
];
pub const STEP_CLIMBER_DATA_UUID: [u8; 16] = [
    0, 0, 0x2a, 0xcf, 0, 0, 0x10, 0, 0x80, 0, 0, 0x80, 0x5f, 0x9b, 0x34, 0xfb,
];
pub const STAIR_CLIMBER_DATA_UUID: [u8; 16] = [
    0, 0, 0x2a, 0xd0, 0, 0, 0x10, 0, 0x80, 0, 0, 0x80, 0x5f, 0x9b, 0x34, 0xfb,
];
pub const ROWER_DATA_UUID: [u8; 16] = [
    0, 0, 0x2a, 0xd1, 0, 0, 0x10, 0, 0x80, 0, 0, 0x80, 0x5f, 0x9b, 0x34, 0xfb,
];
pub const INDOOR_BIKE_DATA_UUID: [u8; 16] = [
    0, 0, 0x2a, 0xd2, 0, 0, 0x10, 0, 0x80, 0, 0, 0x80, 0x5f, 0x9b, 0x34, 0xfb,
];

pub fn measurement_kind_for_uuid(uuid: [u8; 16]) -> Option<MeasurementKind> {
    if uuid == TREADMILL_DATA_UUID {
        Some(MeasurementKind::Treadmill)
    } else if uuid == CROSS_TRAINER_DATA_UUID {
        Some(MeasurementKind::CrossTrainer)
    } else if uuid == STEP_CLIMBER_DATA_UUID {
        Some(MeasurementKind::StepClimber)
    } else if uuid == STAIR_CLIMBER_DATA_UUID {
        Some(MeasurementKind::StairClimber)
    } else if uuid == ROWER_DATA_UUID {
        Some(MeasurementKind::Rower)
    } else if uuid == INDOOR_BIKE_DATA_UUID {
        Some(MeasurementKind::IndoorBike)
    } else {
        None
    }
}

/// A known measurement preserves both raw evidence and the explicit format
/// used to decode it, so callers can continue using raw or normalized access.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct UniversalMeasurement {
    pub raw: RawMeasurement,
    pub options: MeasurementOptions,
}

impl UniversalMeasurement {
    pub fn metric(&self, metric: Metric) -> Option<NormalizedValue> {
        normalized_measurement(&self.raw, self.options, metric)
    }
}

/// An unknown UUID is an honest non-error result: no FTMS layout was selected.
/// A recognized UUID with malformed bytes returns the raw decoder's error.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum UniversalMeasurementDecode {
    Known(UniversalMeasurement),
    Unsupported,
}

pub fn decode_measurement_uuid(
    uuid: [u8; 16],
    bytes: &[u8],
    options: MeasurementOptions,
) -> Result<UniversalMeasurementDecode, Error> {
    let Some(kind) = measurement_kind_for_uuid(uuid) else {
        return Ok(UniversalMeasurementDecode::Unsupported);
    };
    Ok(UniversalMeasurementDecode::Known(UniversalMeasurement {
        raw: decode_measurement(kind, bytes, options)?,
        options,
    }))
}
