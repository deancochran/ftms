//! Pure, allocation-free interpretation of caller-supplied FTMS discovery evidence.
//! It does not perform GATT I/O and deliberately has no execution-permission result.
use crate::{decode_features, decode_range, Error, RangeKind, RangeOptions, RawRange};

pub const PROP_READ: u16 = 2;
pub const PROP_WRITE: u16 = 8;
pub const PROP_NOTIFY: u16 = 16;
pub const PROP_INDICATE: u16 = 32;
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum Discovery {
    NotAttempted,
    Partial,
    Complete,
    Failed,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum ServiceScope {
    Unknown,
    Present,
    Absent,
    Ambiguous,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum ReadState {
    NotAttempted,
    Success,
    Failed,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum Truth {
    Unknown,
    False,
    True,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum Presence {
    Unknown,
    Absent,
    Unique,
    Ambiguous,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum Decode {
    NotAttempted,
    Valid,
    Malformed,
    Failed,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum Declaration {
    Unknown,
    NotSupported,
    Supported,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum Prerequisite {
    NotApplicable,
    Satisfied,
    Incomplete,
    Inconsistent,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct C7Evidence {
    pub bonding_supported: Truth,
    pub feature_may_change_over_lifetime: Truth,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Characteristic<'a> {
    pub uuid: [u8; 16],
    pub properties: u16,
    pub read_state: ReadState,
    pub read_reason: u8,
    pub bytes: &'a [u8],
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CapabilitySnapshot<'a> {
    pub discovery: Discovery,
    pub scope: ServiceScope,
    pub generation: u32,
    pub characteristics: &'a [Characteristic<'a>],
    pub c7: C7Evidence,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Diagnostic {
    pub code: u8,
    pub known_kind: u8,
    pub input_index: Option<usize>,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Observation {
    pub input_index: usize,
    pub uuid: [u8; 16],
    pub properties: u16,
    pub known_kind: u8,
    pub read_state: ReadState,
    pub read_reason: u8,
    pub read_size: usize,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct FeatureEvidence {
    pub presence: Presence,
    pub decode: Decode,
    pub input_index: Option<usize>,
    pub machine_raw: u32,
    pub target_raw: u32,
    pub machine_unknown: u32,
    pub target_unknown: u32,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RangeEvidence {
    pub presence: Presence,
    pub decode: Decode,
    pub input_index: Option<usize>,
    pub value: Option<RawRange>,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Operation {
    pub opcode: u8,
    pub target_bit: u8,
    pub optional_in_table: bool,
    pub declaration: Declaration,
    pub prerequisite: Prerequisite,
    pub reasons: u32,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CapabilityReport<const O: usize, const D: usize> {
    pub generation: u32,
    pub discovery: Discovery,
    pub scope: ServiceScope,
    pub presence: [Presence; 16],
    pub feature: FeatureEvidence,
    pub ranges: [RangeEvidence; 5],
    pub operations: [Operation; 21],
    pub observation_count: usize,
    pub observations: [Option<Observation>; O],
    pub diagnostics: [Option<Diagnostic>; D],
    pub diagnostic_count: usize,
}

const BASE: [u8; 12] = [0, 0, 0x10, 0, 0x80, 0, 0, 0x80, 0x5f, 0x9b, 0x34, 0xfb];
fn kind(uuid: [u8; 16]) -> u8 {
    if uuid[0] == 0 && uuid[1] == 0 && uuid[4..] == BASE {
        let v = u16::from_be_bytes([uuid[2], uuid[3]]);
        if (0x2acc..=0x2ada).contains(&v) {
            return (v - 0x2acc + 1) as u8;
        }
    }
    0
}
fn expected(k: u8, c7: C7Evidence) -> u16 {
    match k {
        1 => {
            PROP_READ
                | if c7.bonding_supported == Truth::True
                    && c7.feature_may_change_over_lifetime == Truth::True
                {
                    PROP_INDICATE
                } else {
                    0
                }
        }
        2..=7 | 15 => PROP_NOTIFY,
        8 => PROP_READ | PROP_NOTIFY,
        9..=13 => PROP_READ,
        14 => PROP_WRITE | PROP_INDICATE,
        _ => 0,
    }
}
fn c7_unknown(c: C7Evidence) -> bool {
    !(c.bonding_supported == Truth::False
        || c.feature_may_change_over_lifetime == Truth::False
        || (c.bonding_supported == Truth::True
            && c.feature_may_change_over_lifetime == Truth::True))
}
fn push<const O: usize, const D: usize>(
    r: &mut CapabilityReport<O, D>,
    d: Diagnostic,
) -> Result<(), Error> {
    if r.diagnostic_count == D {
        return Err(Error::InsufficientStorage {
            required: r.diagnostic_count + 1,
            available: D,
        });
    };
    r.diagnostics[r.diagnostic_count] = Some(d);
    r.diagnostic_count += 1;
    Ok(())
}
fn range_kind(i: usize) -> RangeKind {
    [
        RangeKind::Speed,
        RangeKind::Inclination,
        RangeKind::Resistance,
        RangeKind::HeartRate,
        RangeKind::Power,
    ][i]
}
/// Evaluates a single caller-selected service snapshot. Diagnostics use fixed
/// caller-chosen capacity `D`; insufficient capacity returns without a report.
pub fn evaluate_capabilities<const O: usize, const D: usize>(
    s: CapabilitySnapshot<'_>,
    options: RangeOptions,
) -> Result<CapabilityReport<O, D>, Error> {
    if s.characteristics.len() > O {
        return Err(Error::InsufficientStorage {
            required: s.characteristics.len(),
            available: O,
        });
    }
    for c in s.characteristics {
        if c.read_reason > 5
            || (c.read_state != ReadState::Failed && c.read_reason != 0)
            || (c.read_state != ReadState::Success && !c.bytes.is_empty())
        {
            return Err(Error::InvalidRange);
        }
    }
    let mut r = CapabilityReport {
        generation: s.generation,
        discovery: s.discovery,
        scope: s.scope,
        presence: [Presence::Unknown; 16],
        feature: FeatureEvidence {
            presence: Presence::Unknown,
            decode: Decode::NotAttempted,
            input_index: None,
            machine_raw: 0,
            target_raw: 0,
            machine_unknown: 0,
            target_unknown: 0,
        },
        ranges: [RangeEvidence {
            presence: Presence::Unknown,
            decode: Decode::NotAttempted,
            input_index: None,
            value: None,
        }; 5],
        operations: [Operation {
            opcode: 0,
            target_bit: 255,
            optional_in_table: false,
            declaration: Declaration::Unknown,
            prerequisite: Prerequisite::Incomplete,
            reasons: 0,
        }; 21],
        observation_count: s.characteristics.len(),
        observations: [None; O],
        diagnostics: [None; D],
        diagnostic_count: 0,
    };
    let mut first = [None; 16];
    let mut count = [0u8; 16];
    for (i, c) in s.characteristics.iter().enumerate() {
        let k = kind(c.uuid) as usize;
        r.observations[i] = Some(Observation {
            input_index: i,
            uuid: c.uuid,
            properties: c.properties,
            known_kind: k as u8,
            read_state: c.read_state,
            read_reason: c.read_reason,
            read_size: c.bytes.len(),
        });
        if k > 0 {
            if first[k].is_none() {
                first[k] = Some(i)
            };
            count[k] = count[k].saturating_add(1)
        }
    }
    for k in 1..16 {
        r.presence[k] = if count[k] > 1 {
            push(
                &mut r,
                Diagnostic {
                    code: 3,
                    known_kind: k as u8,
                    input_index: first[k],
                },
            )?;
            Presence::Ambiguous
        } else if count[k] == 1 {
            Presence::Unique
        } else if s.discovery == Discovery::Complete && s.scope == ServiceScope::Present {
            Presence::Absent
        } else {
            Presence::Unknown
        };
    }
    if s.scope != ServiceScope::Present {
        push(
            &mut r,
            Diagnostic {
                code: 0,
                known_kind: 0,
                input_index: None,
            },
        )?;
        if s.scope == ServiceScope::Absent
            && !(s.discovery == Discovery::Complete && s.characteristics.is_empty())
        {
            push(
                &mut r,
                Diagnostic {
                    code: 11,
                    known_kind: 0,
                    input_index: None,
                },
            )?
        }
    };
    if s.discovery != Discovery::Complete {
        push(
            &mut r,
            Diagnostic {
                code: if s.discovery == Discovery::Failed {
                    2
                } else {
                    1
                },
                known_kind: 0,
                input_index: None,
            },
        )?
    }
    if s.scope == ServiceScope::Present {
        for (i, c) in s.characteristics.iter().enumerate() {
            let k = kind(c.uuid);
            if k == 0 {
                continue;
            }
            let e = expected(k, s.c7);
            let unknown = k == 1 && c7_unknown(s.c7);
            if c.properties & e != e {
                push(
                    &mut r,
                    Diagnostic {
                        code: 5,
                        known_kind: k,
                        input_index: Some(i),
                    },
                )?
            }
            if c.properties & !(e | if unknown { PROP_INDICATE } else { 0 }) != 0 {
                push(
                    &mut r,
                    Diagnostic {
                        code: 6,
                        known_kind: k,
                        input_index: Some(i),
                    },
                )?
            }
            if unknown {
                push(
                    &mut r,
                    Diagnostic {
                        code: 12,
                        known_kind: k,
                        input_index: Some(i),
                    },
                )?
            }
            if c.read_state == ReadState::Failed {
                push(
                    &mut r,
                    Diagnostic {
                        code: if c.read_reason == 2 { 8 } else { 7 },
                        known_kind: k,
                        input_index: Some(i),
                    },
                )?
            }
        }
    }
    let presence = r.presence;
    let decode_one = |k: usize| -> (Decode, Option<&Characteristic>) {
        if s.scope != ServiceScope::Present || presence[k] != Presence::Unique {
            return (Decode::NotAttempted, None);
        }
        let c = &s.characteristics[first[k].unwrap()];
        if c.read_state == ReadState::Failed {
            (Decode::Failed, Some(c))
        } else if c.read_state == ReadState::Success {
            (Decode::Valid, Some(c))
        } else {
            (Decode::NotAttempted, Some(c))
        }
    };
    let (fd, fc) = decode_one(1);
    r.feature.presence = r.presence[1];
    r.feature.input_index = if s.scope == ServiceScope::Present && r.presence[1] == Presence::Unique
    {
        first[1]
    } else {
        None
    };
    r.feature.decode = fd;
    if let Some(c) = fc {
        if fd == Decode::Valid {
            match decode_features(c.bytes) {
                Ok(x) => {
                    r.feature.machine_raw = x.machine;
                    r.feature.target_raw = x.target;
                    r.feature.machine_unknown = x.machine & !0x1ffff;
                    r.feature.target_unknown = x.target & !0x1ffff
                }
                Err(_) => {
                    r.feature.decode = Decode::Malformed;
                    push(
                        &mut r,
                        Diagnostic {
                            code: 9,
                            known_kind: 1,
                            input_index: first[1],
                        },
                    )?
                }
            }
        }
    }
    for i in 0..5 {
        let k = 9 + i;
        let (d, c) = decode_one(k);
        r.ranges[i].presence = r.presence[k];
        r.ranges[i].input_index =
            if s.scope == ServiceScope::Present && r.presence[k] == Presence::Unique {
                first[k]
            } else {
                None
            };
        r.ranges[i].decode = d;
        if let Some(c) = c {
            if d == Decode::Valid {
                match decode_range(
                    range_kind(i),
                    c.bytes,
                    if i == 2 {
                        options
                    } else {
                        RangeOptions::default()
                    },
                ) {
                    Ok(v) => r.ranges[i].value = Some(v),
                    Err(_) => {
                        r.ranges[i].decode = Decode::Malformed;
                        push(
                            &mut r,
                            Diagnostic {
                                code: 9,
                                known_kind: k as u8,
                                input_index: first[k],
                            },
                        )?
                    }
                }
            }
        }
    }
    if s.scope == ServiceScope::Present {
        if r.feature.presence == Presence::Absent {
            push(
                &mut r,
                Diagnostic {
                    code: 4,
                    known_kind: 1,
                    input_index: None,
                },
            )?;
        }
        if matches!(r.presence[14], Presence::Unique | Presence::Ambiguous)
            && r.presence[15] == Presence::Absent
        {
            push(
                &mut r,
                Diagnostic {
                    code: 4,
                    known_kind: 15,
                    input_index: None,
                },
            )?;
        }
        if r.feature.decode == Decode::Valid {
            if r.feature.target_raw & 0x1ffff != 0 && r.presence[14] == Presence::Absent {
                push(
                    &mut r,
                    Diagnostic {
                        code: 4,
                        known_kind: 14,
                        input_index: None,
                    },
                )?;
            }
            for (bit, range) in [0usize, 1, 2, 4, 3].iter().enumerate() {
                if r.feature.target_raw & (1 << bit) != 0
                    && r.ranges[*range].presence == Presence::Absent
                {
                    push(
                        &mut r,
                        Diagnostic {
                            code: 10,
                            known_kind: (9 + range) as u8,
                            input_index: None,
                        },
                    )?;
                }
            }
        }
    }
    let targets = [
        255, 255, 0, 1, 2, 3, 4, 255, 255, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
    ];
    let range_for = [0, 1, 2, 4, 3];
    for (op, &bit) in targets.iter().enumerate() {
        let mut decl = Declaration::Unknown;
        let mut why = 0;
        if s.scope != ServiceScope::Present {
            why = 1;
            if s.scope == ServiceScope::Absent
                && s.discovery == Discovery::Complete
                && s.characteristics.is_empty()
            {
                decl = Declaration::NotSupported
            }
            r.operations[op] = Operation {
                opcode: op as u8,
                target_bit: bit,
                optional_in_table: op == 18 || op == 19,
                declaration: decl,
                prerequisite: if decl == Declaration::NotSupported {
                    Prerequisite::NotApplicable
                } else if s.scope == ServiceScope::Absent {
                    Prerequisite::Inconsistent
                } else {
                    Prerequisite::Incomplete
                },
                reasons: why,
            };
            continue;
        }
        if bit == 255 {
            decl = match r.presence[14] {
                Presence::Unique => Declaration::Supported,
                Presence::Absent => Declaration::NotSupported,
                _ => Declaration::Unknown,
            }
        } else if r.feature.decode == Decode::Valid {
            decl = if r.feature.target_raw & (1 << bit) != 0 {
                Declaration::Supported
            } else {
                Declaration::NotSupported
            }
        }
        if decl == Declaration::NotSupported {
            r.operations[op] = Operation {
                opcode: op as u8,
                target_bit: bit,
                optional_in_table: op == 18 || op == 19,
                declaration: decl,
                prerequisite: Prerequisite::NotApplicable,
                reasons: 0,
            };
            continue;
        }
        if s.discovery != Discovery::Complete {
            why |= 2
        }
        for (k, u, iv) in [(1, 4, 8), (14, 16, 32), (15, 64, 128)] {
            why |= match r.presence[k] {
                Presence::Unknown => u,
                Presence::Unique => {
                    let p = s.characteristics[first[k].unwrap()].properties;
                    if k == 1 && c7_unknown(s.c7) {
                        0x400
                            | if p & PROP_READ == 0 || p & !(PROP_READ | PROP_INDICATE) != 0 {
                                iv
                            } else {
                                0
                            }
                    } else if p == expected(k as u8, s.c7) {
                        0
                    } else {
                        iv
                    }
                }
                _ => iv,
            }
        }
        if bit != 255 && r.feature.presence == Presence::Unique {
            why |= match r.feature.decode {
                Decode::Valid => 0,
                Decode::Malformed => 8,
                _ => 4,
            };
        }
        if bit < 5 && decl == Declaration::Supported {
            let ri = range_for[bit as usize];
            why |= match r.ranges[ri].presence {
                Presence::Unknown => 256,
                Presence::Unique => {
                    let c = &s.characteristics[first[9 + ri].unwrap()];
                    let property = if c.properties == PROP_READ { 0 } else { 512 };
                    property
                        | match r.ranges[ri].decode {
                            Decode::Valid => 0,
                            Decode::Malformed => 512,
                            _ => 256,
                        }
                }
                _ => 512,
            }
        }
        r.operations[op] = Operation {
            opcode: op as u8,
            target_bit: bit,
            optional_in_table: op == 18 || op == 19,
            declaration: decl,
            prerequisite: if why & (8 | 32 | 128 | 512) != 0 {
                Prerequisite::Inconsistent
            } else if why == 0 {
                Prerequisite::Satisfied
            } else {
                Prerequisite::Incomplete
            },
            reasons: why,
        };
    }
    Ok(r)
}
