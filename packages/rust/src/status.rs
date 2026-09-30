//! Raw Machine Status and Training Status evidence, independent of transport.
//! Malformed/unknown notifications are retained with diagnostics. Encoders reject
//! diagnostic states rather than turning them into apparently canonical packets.
//!
//! ```
//! use ftms::status::*;
//! let value = RawTrainingStatus {
//!     flags: 1, code: 1, text: b"Ready", ..RawTrainingStatus::default()
//! };
//! let mut wire = [0; 7];
//! assert_eq!(encode_training_status(&value, &mut wire), Ok(7));
//! assert_eq!(&wire, b"\x01\x01Ready");
//! let decoded = decode_training_status(&wire);
//! assert_eq!(decoded.text, b"Ready"); // borrowed from wire, not allocated
//! assert!(!decoded.invalid_utf8);
//! ```

use crate::{
    decode_control_request, encode_control_request, ControlOptions, ControlRequest, Error,
};

/// Raw Machine Status. A missing or incomplete parameter is `None`, not zero.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct RawMachineStatus {
    pub opcode: u8,
    pub action: u8,
    pub parameter: Option<ControlRequest>,
    pub unknown_opcode: bool,
    pub reserved_value: bool,
    pub truncated: bool,
    pub trailing_bytes: bool,
}

fn parameter_opcode(opcode: u8) -> Option<u8> {
    match opcode {
        0x05..=0x09 => Some(opcode - 3),
        0x0a..=0x13 | 0x15 => Some(opcode - 1),
        _ => None,
    }
}
fn length(opcode: u8) -> Option<usize> {
    match opcode {
        1 | 3 | 4 | 0xff => Some(1),
        2 | 0x14 => Some(2),
        _ => parameter_opcode(opcode)
            .and_then(|op| crate::req_len(op, crate::ResistanceControlFormat::Signed16Tenths).ok()),
    }
}
fn valid_action(opcode: u8, action: u8) -> bool {
    match opcode {
        2 => (1..=2).contains(&action),
        0x14 => (1..=4).contains(&action),
        _ => true,
    }
}

/// Every byte slice is interpretable evidence, including empty/unknown input.
/// Resistance status always uses signed 16-bit tenths; request-format options
/// never change this layout. Spin-down *status* permits actions 1 through 4.
pub fn decode_machine_status(bytes: &[u8]) -> RawMachineStatus {
    let Some(&opcode) = bytes.first() else {
        return RawMachineStatus {
            unknown_opcode: true,
            truncated: true,
            ..RawMachineStatus::default()
        };
    };
    let mut status = RawMachineStatus {
        opcode,
        ..RawMachineStatus::default()
    };
    let Some(n) = length(opcode) else {
        status.unknown_opcode = true;
        return status;
    };
    if bytes.len() < n {
        status.truncated = true;
        return status;
    }
    if opcode == 2 || opcode == 0x14 {
        status.action = bytes[1];
        status.reserved_value = !valid_action(opcode, status.action);
    } else if let Some(request) = parameter_opcode(opcode) {
        let mut payload = [0; 11];
        payload[..n].copy_from_slice(&bytes[..n]);
        payload[0] = request;
        // Mapped parameters are numeric-only requests, already length checked.
        status.parameter = decode_control_request(&payload[..n], ControlOptions::default()).ok();
    }
    status.trailing_bytes = bytes.len() > n;
    status
}

/// Encode canonical status into caller storage. No writes occur on errors.
/// Diagnostic states/unknown opcodes are rejected, as are missing or mismatched
/// parameters. Unused `action` for non-action statuses is not encoded.
pub fn encode_machine_status(status: &RawMachineStatus, out: &mut [u8]) -> Result<usize, Error> {
    let n = length(status.opcode).ok_or(Error::InvalidKind)?;
    if status.unknown_opcode || status.reserved_value || status.truncated || status.trailing_bytes {
        return Err(Error::InvalidKind);
    }
    if !valid_action(status.opcode, status.action) {
        return Err(Error::InvalidRange);
    }
    let mut buffer = [0; 11];
    match (parameter_opcode(status.opcode), status.parameter) {
        (Some(expected), Some(parameter)) => {
            if parameter.opcode != expected {
                return Err(Error::InvalidKind);
            }
            encode_control_request(parameter, ControlOptions::default(), &mut buffer)?;
        }
        (Some(_), None) => return Err(Error::InvalidRange),
        (None, Some(_)) => return Err(Error::InvalidKind),
        (None, None) => {
            if n == 2 {
                buffer[1] = status.action;
            }
        }
    }
    buffer[0] = status.opcode;
    if out.len() < n {
        return Err(Error::InsufficientStorage {
            required: n,
            available: out.len(),
        });
    }
    out[..n].copy_from_slice(&buffer[..n]);
    Ok(n)
}

/// Training Status with a borrowed raw text span. Invalid UTF-8 remains bytes;
/// no allocation, replacement characters, or arbitrary string-size limit.
/// Encoding uses `flags`, `code` and `text`, not `text_offset`, `text_present` or
/// `extended_string`. Error diagnostics must still be clear for encoding.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct RawTrainingStatus<'a> {
    pub flags: u8,
    pub code: u8,
    pub text: &'a [u8],
    pub text_offset: usize,
    pub text_present: bool,
    pub extended_string: bool,
    pub reserved_value: bool,
    pub invalid_flags: bool,
    pub invalid_utf8: bool,
    pub truncated: bool,
    pub trailing_bytes: bool,
    pub reserved_flags: u8,
}

/// Decode diagnostics even if the two-byte header is incomplete. In that case
/// `code` is zero-initialized evidence, not a received training state.
pub fn decode_training_status(bytes: &[u8]) -> RawTrainingStatus<'_> {
    let flags = bytes.first().copied().unwrap_or(0);
    if bytes.len() < 2 {
        return RawTrainingStatus {
            flags,
            truncated: true,
            ..RawTrainingStatus::default()
        };
    }
    let code = bytes[1];
    let present = flags & 1 != 0;
    let text = if present { &bytes[2..] } else { &[] };
    RawTrainingStatus {
        flags,
        code,
        text,
        text_offset: if present { 2 } else { 0 },
        text_present: present,
        extended_string: flags & 2 != 0,
        reserved_value: code > 15,
        invalid_flags: flags & 3 == 2,
        invalid_utf8: core::str::from_utf8(text).is_err(),
        truncated: false,
        trailing_bytes: !present && bytes.len() > 2,
        reserved_flags: flags & 0xfc,
    }
}

/// Encode a canonical training state. Set `flags`, `code` and `text` on a default
/// report for new encoder input. RFU flags/codes, malformed UTF-8, diagnostic
/// states and text supplied without the present flag are errors. The entire
/// output remains unchanged on error, including insufficient capacity.
pub fn encode_training_status(
    status: &RawTrainingStatus<'_>,
    out: &mut [u8],
) -> Result<usize, Error> {
    if status.code > 15
        || status.flags & 0xfc != 0
        || status.flags & 3 == 2
        || status.truncated
        || status.reserved_flags != 0
        || status.reserved_value
        || status.invalid_flags
        || status.invalid_utf8
        || status.trailing_bytes
        || (status.flags & 1 == 0 && !status.text.is_empty())
        || core::str::from_utf8(status.text).is_err()
    {
        return Err(Error::InvalidRange);
    }
    let n = status
        .text
        .len()
        .checked_add(2)
        .ok_or(Error::InvalidRange)?;
    if out.len() < n {
        return Err(Error::InsufficientStorage {
            required: n,
            available: out.len(),
        });
    }
    out[0] = status.flags;
    out[1] = status.code;
    out[2..n].copy_from_slice(status.text);
    Ok(n)
}
