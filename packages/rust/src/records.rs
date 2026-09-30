//! Bounded More-Data planning and caller-clocked record assembly.
use crate::{
    measurement::{
        decode_measurement, encode_measurement, selected_fields, MeasurementKind,
        MeasurementOptions, RawMeasurement,
    },
    Error,
};

pub const MEASUREMENT_PACKET_VALUE_MAX: usize = 64;
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct MeasurementPacket {
    pub value: [u8; MEASUREMENT_PACKET_VALUE_MAX],
    pub length: usize,
}
impl Default for MeasurementPacket {
    fn default() -> Self {
        Self {
            value: [0; MEASUREMENT_PACKET_VALUE_MAX],
            length: 0,
        }
    }
}

fn strict(
    kind: MeasurementKind,
    data: &[u8],
    options: MeasurementOptions,
) -> Result<RawMeasurement, Error> {
    let v = decode_measurement(kind, data, options)?;
    let mut canonical = [0; MEASUREMENT_PACKET_VALUE_MAX];
    let n = encode_measurement(&v, options, &mut canonical)?;
    if v.truncated
        || v.trailing_bytes
        || v.reserved_flags
        || n != data.len()
        || canonical[..n] != *data
    {
        return Err(Error::InvalidRange);
    }
    Ok(v)
}
fn layout(kind: MeasurementKind) -> (usize, &'static [u8]) {
    match kind {
        MeasurementKind::Treadmill | MeasurementKind::Rower | MeasurementKind::IndoorBike => {
            (2, &[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
        }
        MeasurementKind::CrossTrainer => (3, &[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]),
        MeasurementKind::StepClimber => (2, &[0, 1, 2, 3, 4, 5, 6, 7, 8]),
        MeasurementKind::StairClimber => (2, &[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
    }
}
fn fragment(source: &RawMeasurement, flags: u32) -> RawMeasurement {
    let mut x = *source;
    x.flags = flags;
    x.present = 0;
    x.unavailable = 0;
    // Encoding itself validates exact selected field masks; reconstruct from source selections.
    for i in 0..crate::measurement::MEASUREMENT_FIELD_COUNT {
        let bit = 1u32 << i;
        if source.present & bit != 0 {
            x.present |= bit;
            if source.unavailable & bit != 0 {
                x.unavailable |= bit;
            }
        }
    }
    x
}
/// Plans greedy wire-order More Data fragments. `packets` is not changed on error.
pub fn plan_measurement(
    snapshot: &RawMeasurement,
    options: MeasurementOptions,
    budget: usize,
    packets: &mut [MeasurementPacket],
) -> Result<usize, Error> {
    if snapshot.flags & 1 != 0 {
        return Err(Error::InvalidRange);
    }
    let mut whole = [0; MEASUREMENT_PACKET_VALUE_MAX];
    let complete = encode_measurement(snapshot, options, &mut whole)?;
    let (flag_bytes, bits) = layout(snapshot.kind);
    if budget < flag_bytes + 1 {
        return Err(Error::InsufficientStorage {
            required: flag_bytes + 1,
            available: budget,
        });
    }
    if complete <= budget {
        if packets.is_empty() {
            return Err(Error::InsufficientStorage {
                required: 1,
                available: 0,
            });
        }
        let mut staged = MeasurementPacket::default();
        staged.value[..complete].copy_from_slice(&whole[..complete]);
        staged.length = complete;
        packets[0] = staged;
        return Ok(1);
    }
    // Measure each group by canonical encoding a one-group non-final fragment.
    let fixed = snapshot.flags & !bits.iter().fold(0u32, |m, b| m | (1 << b));
    let mut result = [MeasurementPacket::default(); 32];
    let mut count = 0;
    let mut current = 0u32;
    for &bit in &bits[1..] {
        if snapshot.flags & (1 << bit) == 0 {
            continue;
        }
        let candidate = current | (1 << bit);
        let mut x = fragment(snapshot, fixed | candidate | 1);
        x.present &= selected_fields(snapshot.kind, x.flags, options);
        x.unavailable &= x.present;
        let mut buf = [0; MEASUREMENT_PACKET_VALUE_MAX];
        let n = encode_measurement(&x, options, &mut buf)?;
        if n > budget {
            if current == 0 {
                return Err(Error::InsufficientStorage {
                    required: n,
                    available: budget,
                });
            }
            let mut y = fragment(snapshot, fixed | current | 1);
            y.present &= selected_fields(snapshot.kind, y.flags, options);
            y.unavailable &= y.present;
            let n = encode_measurement(&y, options, &mut result[count].value)?;
            if n > budget {
                return Err(Error::InsufficientStorage {
                    required: n,
                    available: budget,
                });
            }
            result[count].length = n;
            count += 1;
            current = 1 << bit;
            let mut single = fragment(snapshot, fixed | current | 1);
            single.present &= selected_fields(snapshot.kind, single.flags, options);
            single.unavailable &= single.present;
            let n = encode_measurement(&single, options, &mut buf)?;
            if n > budget {
                return Err(Error::InsufficientStorage {
                    required: n,
                    available: budget,
                });
            }
        } else {
            current = candidate;
        }
    }
    if current != 0 {
        let mut y = fragment(snapshot, fixed | current | 1);
        y.present &= selected_fields(snapshot.kind, y.flags, options);
        y.unavailable &= y.present;
        let n = encode_measurement(&y, options, &mut result[count].value)?;
        if n > budget {
            return Err(Error::InsufficientStorage {
                required: n,
                available: budget,
            });
        }
        result[count].length = n;
        count += 1;
    }
    let mut final_fragment = fragment(snapshot, fixed);
    final_fragment.present &= selected_fields(snapshot.kind, final_fragment.flags, options);
    final_fragment.unavailable &= final_fragment.present;
    let n = encode_measurement(&final_fragment, options, &mut result[count].value)?;
    if n > budget {
        return Err(Error::InsufficientStorage {
            required: n,
            available: budget,
        });
    }
    result[count].length = n;
    count += 1;
    if packets.len() < count {
        return Err(Error::InsufficientStorage {
            required: count,
            available: packets.len(),
        });
    }
    packets[..count].copy_from_slice(&result[..count]);
    Ok(count)
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RecordStatus {
    Pending,
    Complete,
    Invalid,
    Expired,
    Generation,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RecordAssembler {
    kind: MeasurementKind,
    options: MeasurementOptions,
    generation: u32,
    max_age: u32,
    started: u32,
    active: bool,
    merged: RawMeasurement,
}
impl RecordAssembler {
    pub fn new(
        kind: MeasurementKind,
        options: MeasurementOptions,
        generation: u32,
        max_age: u32,
    ) -> Result<Self, Error> {
        if max_age == 0 || max_age >= 0x8000_0000 {
            return Err(Error::InvalidRange);
        };
        Ok(Self {
            kind,
            options,
            generation,
            max_age,
            started: 0,
            active: false,
            merged: RawMeasurement::new(kind),
        })
    }
    pub fn reset(&mut self) {
        self.active = false;
        self.started = 0;
    }
    pub fn feed(
        &mut self,
        data: &[u8],
        generation: u32,
        now: u32,
        out: &mut RawMeasurement,
    ) -> RecordStatus {
        if generation != self.generation {
            self.reset();
            return RecordStatus::Generation;
        }
        if self.active && now.wrapping_sub(self.started) >= self.max_age {
            self.reset();
            return RecordStatus::Expired;
        }
        let Ok(f) = strict(self.kind, data, self.options) else {
            self.reset();
            return RecordStatus::Invalid;
        };
        if !self.active {
            if !f.more_data {
                *out = f;
                return RecordStatus::Complete;
            };
            self.merged = f;
            self.merged.flags &= !1;
            self.merged.more_data = false;
            self.started = now;
            self.active = true;
            return RecordStatus::Pending;
        }
        if f.backward != self.merged.backward || f.present & self.merged.present != 0 {
            self.reset();
            return RecordStatus::Invalid;
        }
        if !f.more_data && f.flags & 1 != 0 {
            self.reset();
            return RecordStatus::Invalid;
        }
        self.merged.flags |= f.flags & !1;
        self.merged.present |= f.present;
        self.merged.unavailable |= f.unavailable;
        for i in 0..crate::measurement::MEASUREMENT_FIELD_COUNT {
            if f.present & (1 << i) != 0 {
                self.merged.values[i] = f.values[i]
            }
        }
        if f.more_data {
            return RecordStatus::Pending;
        }
        let mut complete = self.merged;
        complete.bytes_read = 0;
        *out = complete;
        self.reset();
        RecordStatus::Complete
    }
}
