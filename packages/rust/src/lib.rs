#![no_std]
#![forbid(unsafe_code)]
//! Allocation-free, transport-independent raw FTMS codecs.
//!
//! This crate does not acquire Bluetooth permissions, manage a BLE lifecycle, or
//! authorize a control. All values are native raw wire integers.
//!
//! ```
//! use ftms::{decode_features, encode_features, RawFeatures};
//! let value = RawFeatures { machine: 1, target: 8 };
//! assert_eq!(encode_features(value), [1, 0, 0, 0, 8, 0, 0, 0]);
//! assert_eq!(decode_features(&encode_features(value)), Ok(value));
//! ```

use core::fmt;

pub mod capabilities;
pub mod measurement;
pub mod normalized;
pub mod records;
pub mod status;

pub const FEATURE_BYTES: usize = 8;

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct RawFeatures {
    pub machine: u32,
    pub target: u32,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Error {
    WrongLength { expected: usize, actual: usize },
    InsufficientStorage { required: usize, available: usize },
    InvalidKind,
    InvalidRange,
}
impl core::error::Error for Error {}
impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{self:?}")
    }
}

fn u16le(b: &[u8], o: usize) -> u16 {
    u16::from_le_bytes([b[o], b[o + 1]])
}
fn i16le(b: &[u8], o: usize) -> i16 {
    i16::from_le_bytes([b[o], b[o + 1]])
}
fn put16(b: &mut [u8], o: usize, v: i32) {
    b[o..o + 2].copy_from_slice(&(v as i16).to_le_bytes());
}
fn putu16(b: &mut [u8], o: usize, v: i32) {
    b[o..o + 2].copy_from_slice(&(v as u16).to_le_bytes());
}

pub fn decode_features(bytes: &[u8]) -> Result<RawFeatures, Error> {
    if bytes.len() != 8 {
        return Err(Error::WrongLength {
            expected: 8,
            actual: bytes.len(),
        });
    }
    Ok(RawFeatures {
        machine: u32::from_le_bytes(bytes[0..4].try_into().map_err(|_| Error::InvalidKind)?),
        target: u32::from_le_bytes(bytes[4..8].try_into().map_err(|_| Error::InvalidKind)?),
    })
}
pub fn encode_features(v: RawFeatures) -> [u8; 8] {
    let mut b = [0; 8];
    b[..4].copy_from_slice(&v.machine.to_le_bytes());
    b[4..].copy_from_slice(&v.target.to_le_bytes());
    b
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RangeKind {
    Speed,
    Inclination,
    Resistance,
    HeartRate,
    Power,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RangeUnit {
    KilometresPerHour,
    Percent,
    Level,
    BeatsPerMinute,
    Watts,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RawRange {
    pub kind: RangeKind,
    pub minimum: i32,
    pub maximum: i32,
    pub increment: i32,
    pub scale_divisor: u16,
    pub unit: RangeUnit,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ResistanceRangeFormat {
    Uint8Whole,
    Signed16Tenths,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RangeOptions {
    pub resistance_format: ResistanceRangeFormat,
}
impl Default for RangeOptions {
    fn default() -> Self {
        Self {
            resistance_format: ResistanceRangeFormat::Uint8Whole,
        }
    }
}
fn range_metadata(k: RangeKind, f: ResistanceRangeFormat) -> (usize, bool, u16, RangeUnit) {
    match k {
        RangeKind::Speed => (6, false, 100, RangeUnit::KilometresPerHour),
        RangeKind::Inclination => (6, true, 10, RangeUnit::Percent),
        RangeKind::Resistance if f == ResistanceRangeFormat::Signed16Tenths => {
            (6, true, 10, RangeUnit::Level)
        }
        RangeKind::Resistance => (3, false, 1, RangeUnit::Level),
        RangeKind::HeartRate => (3, false, 1, RangeUnit::BeatsPerMinute),
        RangeKind::Power => (6, true, 1, RangeUnit::Watts),
    }
}
pub fn decode_range(
    kind: RangeKind,
    bytes: &[u8],
    options: RangeOptions,
) -> Result<RawRange, Error> {
    if options.resistance_format == ResistanceRangeFormat::Signed16Tenths
        && kind != RangeKind::Resistance
    {
        return Err(Error::InvalidKind);
    }
    let (n, signed, div, unit) = range_metadata(kind, options.resistance_format);
    if bytes.len() != n {
        return Err(Error::WrongLength {
            expected: n,
            actual: bytes.len(),
        });
    }
    let (min, max, inc) = if n == 3 {
        (bytes[0] as i32, bytes[1] as i32, bytes[2] as i32)
    } else if signed {
        (
            i16le(bytes, 0) as i32,
            i16le(bytes, 2) as i32,
            u16le(bytes, 4) as i32,
        )
    } else {
        (
            u16le(bytes, 0) as i32,
            u16le(bytes, 2) as i32,
            u16le(bytes, 4) as i32,
        )
    };
    if min > max || inc == 0 {
        return Err(Error::InvalidRange);
    }
    Ok(RawRange {
        kind,
        minimum: min,
        maximum: max,
        increment: inc,
        scale_divisor: div,
        unit,
    })
}
pub fn encode_range(
    value: RawRange,
    options: RangeOptions,
    out: &mut [u8],
) -> Result<usize, Error> {
    if options.resistance_format == ResistanceRangeFormat::Signed16Tenths
        && value.kind != RangeKind::Resistance
    {
        return Err(Error::InvalidKind);
    }
    let (n, signed, div, unit) = range_metadata(value.kind, options.resistance_format);
    if value.scale_divisor != div
        || value.unit != unit
        || value.minimum > value.maximum
        || value.increment <= 0
    {
        return Err(Error::InvalidRange);
    }
    let max = if n == 3 { 255 } else { 65535 };
    if (signed && (value.minimum < -32768 || value.maximum > 32767))
        || (!signed && (value.minimum < 0 || value.maximum > max))
        || value.increment > max
    {
        return Err(Error::InvalidRange);
    }
    if out.len() < n {
        return Err(Error::InsufficientStorage {
            required: n,
            available: out.len(),
        });
    }
    if n == 3 {
        out[..3].copy_from_slice(&[
            value.minimum as u8,
            value.maximum as u8,
            value.increment as u8,
        ]);
    } else if signed {
        put16(out, 0, value.minimum);
        put16(out, 2, value.maximum);
        putu16(out, 4, value.increment);
    } else {
        putu16(out, 0, value.minimum);
        putu16(out, 2, value.maximum);
        putu16(out, 4, value.increment);
    }
    Ok(n)
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RangeProfile {
    Uint16Hundredths,
    Signed16Tenths,
    Uint8Whole,
    Uint8Bpm,
    Signed16Watts,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum InspectionStatus {
    Valid,
    Length,
    Range,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RangeCandidate {
    pub profile: RangeProfile,
    pub expected_length: usize,
    pub status: InspectionStatus,
    pub value: Option<RawRange>,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RangeInspection {
    pub selected_profile: RangeProfile,
    pub actual_length: usize,
    pub expected_length: usize,
    pub status: InspectionStatus,
    pub value: Option<RawRange>,
    pub candidates: [Option<RangeCandidate>; 2],
    pub candidate_count: usize,
}
fn profile(k: RangeKind, f: ResistanceRangeFormat) -> RangeProfile {
    match k {
        RangeKind::Speed => RangeProfile::Uint16Hundredths,
        RangeKind::Inclination => RangeProfile::Signed16Tenths,
        RangeKind::Resistance if f == ResistanceRangeFormat::Signed16Tenths => {
            RangeProfile::Signed16Tenths
        }
        RangeKind::Resistance => RangeProfile::Uint8Whole,
        RangeKind::HeartRate => RangeProfile::Uint8Bpm,
        RangeKind::Power => RangeProfile::Signed16Watts,
    }
}
fn candidate(k: RangeKind, b: &[u8], f: ResistanceRangeFormat) -> RangeCandidate {
    let (_, _, _, _) = range_metadata(k, f);
    let expected = range_metadata(k, f).0;
    match decode_range(
        k,
        b,
        RangeOptions {
            resistance_format: f,
        },
    ) {
        Ok(v) => RangeCandidate {
            profile: profile(k, f),
            expected_length: expected,
            status: InspectionStatus::Valid,
            value: Some(v),
        },
        Err(Error::InvalidRange) => RangeCandidate {
            profile: profile(k, f),
            expected_length: expected,
            status: InspectionStatus::Range,
            value: None,
        },
        _ => RangeCandidate {
            profile: profile(k, f),
            expected_length: expected,
            status: InspectionStatus::Length,
            value: None,
        },
    }
}
pub fn inspect_range(
    k: RangeKind,
    b: &[u8],
    options: RangeOptions,
) -> Result<RangeInspection, Error> {
    if options.resistance_format == ResistanceRangeFormat::Signed16Tenths
        && k != RangeKind::Resistance
    {
        return Err(Error::InvalidKind);
    };
    let first = candidate(k, b, ResistanceRangeFormat::Uint8Whole);
    let second = if k == RangeKind::Resistance {
        Some(candidate(k, b, ResistanceRangeFormat::Signed16Tenths))
    } else {
        None
    };
    let selected = if options.resistance_format == ResistanceRangeFormat::Signed16Tenths {
        second.unwrap()
    } else {
        first
    };
    Ok(RangeInspection {
        selected_profile: selected.profile,
        actual_length: b.len(),
        expected_length: selected.expected_length,
        status: selected.status,
        value: selected.value,
        candidates: [Some(first), second],
        candidate_count: if second.is_some() { 2 } else { 1 },
    })
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ResistanceControlFormat {
    Signed16Tenths,
    Uint8Tenths,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ControlOptions {
    pub resistance_format: ResistanceControlFormat,
}
impl Default for ControlOptions {
    fn default() -> Self {
        Self {
            resistance_format: ResistanceControlFormat::Signed16Tenths,
        }
    }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ControlRequest {
    pub opcode: u8,
    pub operands: [i32; 5],
    pub operand_count: usize,
}
fn req_len(op: u8, f: ResistanceControlFormat) -> Result<usize, Error> {
    Ok(match op {
        0 | 1 | 7 => 1,
        4 if f == ResistanceControlFormat::Uint8Tenths => 2,
        6 | 8 | 19 => 2,
        12 => 4,
        14 => 5,
        15 | 17 => 7,
        16 => 11,
        2..=5 | 9..=11 | 13 | 18 | 20 => 3,
        _ => return Err(Error::InvalidKind),
    })
}
fn valid_action(v: i32) -> bool {
    v == 1 || v == 2
}
fn operand_count(op: u8) -> usize {
    match op {
        0 | 1 | 7 => 0,
        14 => 2,
        15 => 3,
        16 => 5,
        17 => 4,
        _ => 1,
    }
}
fn fits_u8(value: i32) -> bool {
    (0..=u8::MAX as i32).contains(&value)
}
fn fits_u16(value: i32) -> bool {
    (0..=u16::MAX as i32).contains(&value)
}
fn fits_i16(value: i32) -> bool {
    (i16::MIN as i32..=i16::MAX as i32).contains(&value)
}
fn request_operands_valid(r: ControlRequest, format: ResistanceControlFormat) -> bool {
    match r.opcode {
        0 | 1 | 7 => true,
        2 | 9..=11 | 13 | 18 | 20 => fits_u16(r.operands[0]),
        3 | 5 => fits_i16(r.operands[0]),
        4 => {
            if format == ResistanceControlFormat::Uint8Tenths {
                fits_u8(r.operands[0])
            } else {
                fits_i16(r.operands[0])
            }
        }
        6 => fits_u8(r.operands[0]),
        8 | 19 => valid_action(r.operands[0]),
        12 => (0..=0x00ff_ffff).contains(&r.operands[0]),
        14..=16 => r.operands[..r.operand_count].iter().copied().all(fits_u16),
        17 => {
            fits_i16(r.operands[0])
                && fits_i16(r.operands[1])
                && fits_u8(r.operands[2])
                && fits_u8(r.operands[3])
        }
        _ => false,
    }
}
pub fn decode_control_request(b: &[u8], o: ControlOptions) -> Result<ControlRequest, Error> {
    if b.is_empty() {
        return Err(Error::WrongLength {
            expected: 1,
            actual: 0,
        });
    }
    let n = req_len(b[0], o.resistance_format)?;
    if b.len() != n {
        return Err(Error::WrongLength {
            expected: n,
            actual: b.len(),
        });
    }
    let mut r = ControlRequest {
        opcode: b[0],
        operands: [0; 5],
        operand_count: (n - 1) / 2,
    };
    match b[0] {
        0 | 1 | 7 => r.operand_count = 0,
        2 => r.operands[0] = u16le(b, 1) as i32,
        3 => r.operands[0] = i16le(b, 1) as i32,
        4 if o.resistance_format == ResistanceControlFormat::Signed16Tenths => {
            r.operands[0] = i16le(b, 1) as i32
        }
        4 | 6 | 8 | 19 => {
            r.operand_count = 1;
            r.operands[0] = b[1] as i32
        }
        5 => r.operands[0] = i16le(b, 1) as i32,
        9..=11 | 13 | 18 | 20 => r.operands[0] = u16le(b, 1) as i32,
        12 => r.operands[0] = (b[1] as i32) | ((b[2] as i32) << 8) | ((b[3] as i32) << 16),
        14..=16 => {
            for i in 0..r.operand_count {
                r.operands[i] = u16le(b, 1 + i * 2) as i32
            }
        }
        17 => {
            r.operands = [
                i16le(b, 1) as i32,
                i16le(b, 3) as i32,
                b[5] as i32,
                b[6] as i32,
                0,
            ];
            r.operand_count = 4
        }
        _ => {}
    }
    if matches!(b[0], 8 | 19) && !valid_action(r.operands[0]) {
        return Err(Error::InvalidRange);
    }
    Ok(r)
}
pub fn encode_control_request(
    r: ControlRequest,
    o: ControlOptions,
    out: &mut [u8],
) -> Result<usize, Error> {
    let n = req_len(r.opcode, o.resistance_format)?;
    if r.operand_count != operand_count(r.opcode) {
        return Err(Error::InvalidRange);
    }
    if !request_operands_valid(r, o.resistance_format) {
        return Err(Error::InvalidRange);
    }
    if out.len() < n {
        return Err(Error::InsufficientStorage {
            required: n,
            available: out.len(),
        });
    }
    let mut x = [0u8; 11];
    x[0] = r.opcode;
    match r.opcode {
        2 | 9..=11 | 13 | 18 | 20 => putu16(&mut x, 1, r.operands[0]),
        3 | 5 => put16(&mut x, 1, r.operands[0]),
        4 => {
            if o.resistance_format == ResistanceControlFormat::Uint8Tenths {
                x[1] = r.operands[0] as u8
            } else {
                put16(&mut x, 1, r.operands[0])
            }
        }
        6 | 8 | 19 => x[1] = r.operands[0] as u8,
        12 => {
            x[1] = r.operands[0] as u8;
            x[2] = (r.operands[0] >> 8) as u8;
            x[3] = (r.operands[0] >> 16) as u8
        }
        14..=16 => {
            for i in 0..r.operand_count {
                putu16(&mut x, 1 + i * 2, r.operands[i])
            }
        }
        17 => {
            put16(&mut x, 1, r.operands[0]);
            put16(&mut x, 3, r.operands[1]);
            x[5] = r.operands[2] as u8;
            x[6] = r.operands[3] as u8
        }
        _ => {}
    }
    out[..n].copy_from_slice(&x[..n]);
    Ok(n)
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ControlResponse {
    pub request_opcode: u8,
    pub result_code: u8,
    pub parameter: u8,
    pub low: u16,
    pub high: u16,
    pub unknown_request: u8,
    pub unknown_result: u8,
    pub unexpected_parameters: u8,
}
fn known(op: u8) -> bool {
    op <= 20
}
fn known_result(x: u8) -> bool {
    (1..=5).contains(&x)
}
pub fn decode_control_response(b: &[u8]) -> Result<ControlResponse, Error> {
    if b.len() < 3 {
        return Err(Error::WrongLength {
            expected: 3,
            actual: b.len(),
        });
    }
    if b[0] != 0x80 {
        return Err(Error::InvalidKind);
    }
    let mut r = ControlResponse {
        request_opcode: b[1],
        result_code: b[2],
        parameter: 0,
        low: 0,
        high: 0,
        unknown_request: (!known(b[1])) as u8,
        unknown_result: (!known_result(b[2])) as u8,
        unexpected_parameters: 0,
    };
    if b.len() == 3 {
        return Ok(r);
    }
    if b[1] == 19 && b[2] == 1 {
        if b.len() != 7 {
            return Err(Error::WrongLength {
                expected: 7,
                actual: b.len(),
            });
        }
        r.parameter = 1;
        r.low = u16le(b, 3);
        r.high = u16le(b, 5)
    } else {
        r.unexpected_parameters = 1
    }
    Ok(r)
}
pub fn encode_control_response(r: ControlResponse, out: &mut [u8]) -> Result<usize, Error> {
    if !known_result(r.result_code) {
        return Err(Error::InvalidRange);
    }
    if !known(r.request_opcode) && r.result_code != 2 {
        return Err(Error::InvalidKind);
    }
    let n = if r.parameter == 0 {
        3
    } else if r.parameter == 1 && r.request_opcode == 19 && r.result_code == 1 {
        7
    } else {
        return Err(Error::InvalidRange);
    };
    if out.len() < n {
        return Err(Error::InsufficientStorage {
            required: n,
            available: out.len(),
        });
    }
    out[0] = 0x80;
    out[1] = r.request_opcode;
    out[2] = r.result_code;
    if n == 7 {
        out[3..5].copy_from_slice(&r.low.to_le_bytes());
        out[5..7].copy_from_slice(&r.high.to_le_bytes())
    }
    Ok(n)
}
