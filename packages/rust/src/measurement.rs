//! Raw codecs for all six FTMS measurement characteristics.
//!
//! Fields use wire integers, not human-unit floating point values. `present`
//! distinguishes absent/incomplete fields from actual zero measurements;
//! `unavailable` marks only defined wire sentinels. No fragments are reassembled.
//! The kind, flags, masks and values are authoritative encoder input; derived
//! decode metadata (`bytes_read` and diagnostic booleans) is not encoded.
//!
//! ```
//! use ftms::measurement::*;
//! let mut value = RawMeasurement::new(MeasurementKind::IndoorBike);
//! value.flags = 1 << 2; // cadence selected, More Data clear: speed also required
//! value.present = MeasurementField::Speed.mask() | MeasurementField::Cadence.mask();
//! value.values[MeasurementField::Speed.index()] = 1000; // 10.00 km/h
//! value.values[MeasurementField::Cadence.index()] = 120; // 60 rpm
//! let mut wire = [0; 6];
//! let options = MeasurementOptions::default();
//! assert_eq!(encode_measurement(&value, options, &mut wire), Ok(6));
//! assert_eq!(wire, [4, 0, 232, 3, 120, 0]);
//! let decoded = decode_measurement(value.kind, &wire, options)?;
//! assert_eq!(decoded.values, value.values);
//! assert_eq!(decoded.present, value.present);
//! # Ok::<(), ftms::Error>(())
//! ```

use crate::Error;

/// The six characteristic layouts, in the shared raw contract's kind order.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum MeasurementKind {
    Treadmill,
    CrossTrainer,
    StepClimber,
    StairClimber,
    Rower,
    IndoorBike,
}

impl TryFrom<u8> for MeasurementKind {
    type Error = Error;
    fn try_from(value: u8) -> Result<Self, Error> {
        match value {
            0 => Ok(Self::Treadmill),
            1 => Ok(Self::CrossTrainer),
            2 => Ok(Self::StepClimber),
            3 => Ok(Self::StairClimber),
            4 => Ok(Self::Rower),
            5 => Ok(Self::IndoorBike),
            _ => Err(Error::InvalidKind),
        }
    }
}

/// Field indices and mask positions from the shared raw comparison contract.
/// Names do not imply identical scaling across equipment kinds; see the package
/// documentation for units. Unavailable values decode to zero with a mask bit.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum MeasurementField {
    Speed,
    AverageSpeed,
    Distance,
    Inclination,
    RampAngle,
    PositiveElevation,
    NegativeElevation,
    InstantaneousPace,
    AveragePace,
    Energy,
    EnergyPerHour,
    EnergyPerMinute,
    HeartRate,
    Met,
    Elapsed,
    Remaining,
    Force,
    Power,
    StepRate,
    AverageStepRate,
    StrideCount,
    Resistance,
    AveragePower,
    FloorCount,
    StepCount,
    StrokeRate,
    StrokeCount,
    AverageStrokeRate,
    Cadence,
    AverageCadence,
}

impl MeasurementField {
    pub const fn index(self) -> usize {
        self as usize
    }
    pub const fn mask(self) -> u32 {
        1 << (self as u8)
    }
}

pub const MEASUREMENT_FIELD_COUNT: usize = 30;

/// Raw decoded evidence or encoder input. Construct canonical encoder input with
/// [`RawMeasurement::new`], then set flags and exactly the selected field masks.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RawMeasurement {
    pub kind: MeasurementKind,
    pub flags: u32,
    pub present: u32,
    pub unavailable: u32,
    pub values: [i32; MEASUREMENT_FIELD_COUNT],
    pub more_data: bool,
    pub backward: bool,
    pub truncated: bool,
    pub trailing_bytes: bool,
    pub reserved_flags: bool,
    pub bytes_read: usize,
}

impl RawMeasurement {
    pub const fn new(kind: MeasurementKind) -> Self {
        Self {
            kind,
            flags: 0,
            present: 0,
            unavailable: 0,
            values: [0; MEASUREMENT_FIELD_COUNT],
            more_data: false,
            backward: false,
            truncated: false,
            trailing_bytes: false,
            reserved_flags: false,
            bytes_read: 0,
        }
    }
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum MeasurementResistanceFormat {
    #[default]
    Uint8Whole,
    Signed16Tenths,
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum TreadmillPaceFormat {
    #[default]
    Uint16,
    Uint8Legacy,
}

/// Independent caller choices, never inferred from a packet or a range profile.
/// Options have no effect on equipment/fields to which they do not apply.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct MeasurementOptions {
    pub resistance_format: MeasurementResistanceFormat,
    pub treadmill_pace_format: TreadmillPaceFormat,
}

#[derive(Clone, Copy)]
struct Field {
    bit: u8,
    width: usize,
    id: MeasurementField,
    signed: bool,
    sentinel: bool,
}
const fn f(bit: u8, width: usize, id: MeasurementField, signed: bool, sentinel: bool) -> Field {
    Field {
        bit,
        width,
        id,
        signed,
        sentinel,
    }
}
use MeasurementField::*;

// Characteristic wire order. Repeated bits intentionally select whole groups.
const TREADMILL: &[Field] = &[
    f(0, 2, Speed, false, false),
    f(1, 2, AverageSpeed, false, false),
    f(2, 3, Distance, false, false),
    f(3, 2, Inclination, true, true),
    f(3, 2, RampAngle, true, true),
    f(4, 2, PositiveElevation, false, false),
    f(4, 2, NegativeElevation, false, false),
    f(5, 2, InstantaneousPace, false, false),
    f(6, 2, AveragePace, false, false),
    f(7, 2, Energy, false, true),
    f(7, 2, EnergyPerHour, false, true),
    f(7, 1, EnergyPerMinute, false, true),
    f(8, 1, HeartRate, false, false),
    f(9, 1, Met, false, false),
    f(10, 2, Elapsed, false, false),
    f(11, 2, Remaining, false, false),
    f(12, 2, Force, true, true),
    f(12, 2, Power, true, true),
];
const CROSS: &[Field] = &[
    f(0, 2, Speed, false, false),
    f(1, 2, AverageSpeed, false, false),
    f(2, 3, Distance, false, false),
    f(3, 2, StepRate, false, true),
    f(3, 2, AverageStepRate, false, true),
    f(4, 2, StrideCount, false, false),
    f(5, 2, PositiveElevation, false, false),
    f(5, 2, NegativeElevation, false, false),
    f(6, 2, Inclination, true, true),
    f(6, 2, RampAngle, true, true),
    f(7, 1, Resistance, false, false),
    f(8, 2, Power, true, false),
    f(9, 2, AveragePower, true, false),
    f(10, 2, Energy, false, true),
    f(10, 2, EnergyPerHour, false, true),
    f(10, 1, EnergyPerMinute, false, true),
    f(11, 1, HeartRate, false, false),
    f(12, 1, Met, false, false),
    f(13, 2, Elapsed, false, false),
    f(14, 2, Remaining, false, false),
];
const STEP: &[Field] = &[
    f(0, 2, FloorCount, false, false),
    f(0, 2, StepCount, false, false),
    f(1, 2, StepRate, false, false),
    f(2, 2, AverageStepRate, false, false),
    f(3, 2, PositiveElevation, false, false),
    f(4, 2, Energy, false, true),
    f(4, 2, EnergyPerHour, false, true),
    f(4, 1, EnergyPerMinute, false, true),
    f(5, 1, HeartRate, false, false),
    f(6, 1, Met, false, false),
    f(7, 2, Elapsed, false, false),
    f(8, 2, Remaining, false, false),
];
const STAIR: &[Field] = &[
    f(0, 2, FloorCount, false, false),
    f(1, 2, StepRate, false, false),
    f(2, 2, AverageStepRate, false, false),
    f(3, 2, PositiveElevation, false, false),
    f(4, 2, StrideCount, false, false),
    f(5, 2, Energy, false, true),
    f(5, 2, EnergyPerHour, false, true),
    f(5, 1, EnergyPerMinute, false, true),
    f(6, 1, HeartRate, false, false),
    f(7, 1, Met, false, false),
    f(8, 2, Elapsed, false, false),
    f(9, 2, Remaining, false, false),
];
const ROWER: &[Field] = &[
    f(0, 1, StrokeRate, false, false),
    f(0, 2, StrokeCount, false, false),
    f(1, 1, AverageStrokeRate, false, false),
    f(2, 3, Distance, false, false),
    f(3, 2, InstantaneousPace, false, false),
    f(4, 2, AveragePace, false, false),
    f(5, 2, Power, true, false),
    f(6, 2, AveragePower, true, false),
    f(7, 1, Resistance, false, false),
    f(8, 2, Energy, false, true),
    f(8, 2, EnergyPerHour, false, true),
    f(8, 1, EnergyPerMinute, false, true),
    f(9, 1, HeartRate, false, false),
    f(10, 1, Met, false, false),
    f(11, 2, Elapsed, false, false),
    f(12, 2, Remaining, false, false),
];
const BIKE: &[Field] = &[
    f(0, 2, Speed, false, false),
    f(1, 2, AverageSpeed, false, false),
    f(2, 2, Cadence, false, false),
    f(3, 2, AverageCadence, false, false),
    f(4, 3, Distance, false, false),
    f(5, 1, Resistance, false, false),
    f(6, 2, Power, true, false),
    f(7, 2, AveragePower, true, false),
    f(8, 2, Energy, false, true),
    f(8, 2, EnergyPerHour, false, true),
    f(8, 1, EnergyPerMinute, false, true),
    f(9, 1, HeartRate, false, false),
    f(10, 1, Met, false, false),
    f(11, 2, Elapsed, false, false),
    f(12, 2, Remaining, false, false),
];

fn layout(kind: MeasurementKind) -> (usize, u32, &'static [Field]) {
    match kind {
        MeasurementKind::Treadmill => (2, 0x1fff, TREADMILL),
        MeasurementKind::CrossTrainer => (3, 0xffff, CROSS),
        MeasurementKind::StepClimber => (2, 0x01ff, STEP),
        MeasurementKind::StairClimber => (2, 0x03ff, STAIR),
        MeasurementKind::Rower => (2, 0x1fff, ROWER),
        MeasurementKind::IndoorBike => (2, 0x1fff, BIKE),
    }
}
fn formatted(mut field: Field, kind: MeasurementKind, options: MeasurementOptions) -> Field {
    if field.id == Resistance
        && options.resistance_format == MeasurementResistanceFormat::Signed16Tenths
    {
        field.width = 2;
        field.signed = true;
    }
    if kind == MeasurementKind::Treadmill
        && matches!(field.id, InstantaneousPace | AveragePace)
        && options.treadmill_pace_format == TreadmillPaceFormat::Uint8Legacy
    {
        field.width = 1;
    }
    field
}
fn selected(flags: u32, field: Field) -> bool {
    if field.bit == 0 {
        flags & 1 == 0
    } else {
        flags & (1 << field.bit) != 0
    }
}
/// Returns the raw-field mask selected by a measurement flag word.  This is
/// useful to bounded planners; it does not inspect packet bytes.
pub fn selected_fields(kind: MeasurementKind, flags: u32, options: MeasurementOptions) -> u32 {
    let (_, _, fields) = layout(kind);
    fields
        .iter()
        .copied()
        .map(|f| formatted(f, kind, options))
        .filter(|f| selected(flags, *f))
        .fold(0, |mask, f| mask | f.id.mask())
}
fn sentinel(field: Field) -> u32 {
    if field.signed {
        0x7fff
    } else {
        (1 << (field.width * 8)) - 1
    }
}
fn read(bytes: &[u8]) -> u32 {
    bytes
        .iter()
        .enumerate()
        .fold(0, |n, (i, byte)| n | (u32::from(*byte) << (8 * i)))
}
fn write(bytes: &mut [u8], value: u32) {
    for (i, byte) in bytes.iter_mut().enumerate() {
        *byte = (value >> (8 * i)) as u8;
    }
}

/// Decode complete fields and retain diagnostics for partial/trailing/RFU data.
/// Only a missing flag word is a length error. `bytes_read` never includes an
/// incomplete field. Invalid kinds are excluded by the enum (or `TryFrom`).
pub fn decode_measurement(
    kind: MeasurementKind,
    bytes: &[u8],
    options: MeasurementOptions,
) -> Result<RawMeasurement, Error> {
    let (flag_bytes, valid_flags, fields) = layout(kind);
    if bytes.len() < flag_bytes {
        return Err(Error::WrongLength {
            expected: flag_bytes,
            actual: bytes.len(),
        });
    }
    let mut value = RawMeasurement::new(kind);
    value.flags = read(&bytes[..flag_bytes]);
    value.more_data = value.flags & 1 != 0;
    value.backward = kind == MeasurementKind::CrossTrainer && value.flags & 0x8000 != 0;
    value.reserved_flags = value.flags & !valid_flags != 0;
    value.bytes_read = flag_bytes;
    for field in fields.iter().copied().map(|f| formatted(f, kind, options)) {
        if !selected(value.flags, field) {
            continue;
        }
        let end = value.bytes_read + field.width; // bounded by the known layout, at most 41
        let Some(span) = bytes.get(value.bytes_read..end) else {
            value.truncated = true;
            return Ok(value);
        };
        let raw = read(span);
        value.bytes_read = end;
        value.present |= field.id.mask();
        if field.sentinel && raw == sentinel(field) {
            value.unavailable |= field.id.mask();
        } else {
            value.values[field.id.index()] = if field.signed {
                i32::from(raw as u16 as i16)
            } else {
                raw as i32
            };
        }
    }
    value.trailing_bytes = value.bytes_read < bytes.len();
    Ok(value)
}

/// Encode the fields selected by flags, with no output modification on error.
/// Rejects RFU flags, missing/extra presence bits, invalid sentinel masks and
/// out-of-width raw values. The largest current complete format is 41 bytes;
/// that is an implementation layout bound, not a BLE notification size limit.
pub fn encode_measurement(
    value: &RawMeasurement,
    options: MeasurementOptions,
    out: &mut [u8],
) -> Result<usize, Error> {
    let (flag_bytes, valid_flags, fields) = layout(value.kind);
    let required = fields
        .iter()
        .filter(|f| selected(value.flags, **f))
        .fold(0, |mask, f| mask | f.id.mask());
    if value.flags & !valid_flags != 0
        || value.present != required
        || value.unavailable & !required != 0
    {
        return Err(Error::InvalidRange);
    }
    let mut buffer = [0; 41];
    write(&mut buffer[..flag_bytes], value.flags);
    let mut offset = flag_bytes;
    for field in fields
        .iter()
        .copied()
        .map(|f| formatted(f, value.kind, options))
    {
        if !selected(value.flags, field) {
            continue;
        }
        let raw = if value.unavailable & field.id.mask() != 0 {
            if !field.sentinel {
                return Err(Error::InvalidRange);
            }
            sentinel(field)
        } else {
            let v = value.values[field.id.index()];
            let valid = if field.signed {
                (-32768..=32767).contains(&v)
            } else {
                v >= 0 && (v as u32) < (1 << (field.width * 8))
            };
            if !valid || (field.sentinel && v as u32 == sentinel(field)) {
                return Err(Error::InvalidRange);
            }
            v as u32
        };
        write(&mut buffer[offset..offset + field.width], raw);
        offset += field.width;
    }
    if out.len() < offset {
        return Err(Error::InsufficientStorage {
            required: offset,
            available: out.len(),
        });
    }
    out[..offset].copy_from_slice(&buffer[..offset]);
    Ok(offset)
}
