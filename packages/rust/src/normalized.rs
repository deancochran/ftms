//! Physical-unit projections of raw measurement evidence.
//!
//! A metric is omitted when its flag did not select it, and is `Unavailable`
//! when its selected wire representation used the FTMS unavailable sentinel.

use crate::{
    measurement::{
        MeasurementField as F, MeasurementKind, MeasurementOptions, RawMeasurement,
        TreadmillPaceFormat,
    },
    status::RawMachineStatus,
    ControlOptions, ControlRequest, ControlResponse, Error, RangeKind, RawFeatures, RawRange,
};

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum NormalizedValue {
    Number(f32),
    Unavailable,
    UnknownUnit,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NormalizedFeatures {
    pub machine_raw: u32,
    pub target_raw: u32,
    pub machine_unknown: u32,
    pub target_unknown: u32,
}
/// Known Fitness Machine Feature measurement-word bits (0--16).
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum MachineFeature {
    AverageSpeed,
    Cadence,
    TotalDistance,
    Inclination,
    ElevationGain,
    Pace,
    StepCount,
    ResistanceLevel,
    StrideCount,
    ExpendedEnergy,
    HeartRateMeasurement,
    MetabolicEquivalent,
    ElapsedTime,
    RemainingTime,
    PowerMeasurement,
    ForceOnBelt,
    UserDataRetention,
}
/// Known Fitness Machine Feature target-word bits (0--16).
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum TargetFeature {
    Speed,
    Inclination,
    Resistance,
    Power,
    HeartRate,
    ExpendedEnergy,
    StepNumber,
    StrideNumber,
    Distance,
    TrainingTime,
    TimeTwoHrZones,
    TimeThreeHrZones,
    TimeFiveHrZones,
    IndoorBikeSimulation,
    WheelCircumference,
    SpinDown,
    Cadence,
}
impl NormalizedFeatures {
    pub const fn supports_machine(self, feature: MachineFeature) -> bool {
        self.machine_raw & (1 << feature as u8) != 0
    }
    pub const fn supports_target(self, feature: TargetFeature) -> bool {
        self.target_raw & (1 << feature as u8) != 0
    }
    pub const fn supports_erg(self) -> bool {
        self.supports_target(TargetFeature::Power)
    }
    pub const fn supports_sim(self) -> bool {
        self.supports_target(TargetFeature::IndoorBikeSimulation)
    }
    pub const fn supports_resistance(self) -> bool {
        self.supports_target(TargetFeature::Resistance)
    }
}
pub fn normalize_features(raw: RawFeatures) -> NormalizedFeatures {
    NormalizedFeatures {
        machine_raw: raw.machine,
        target_raw: raw.target,
        machine_unknown: raw.machine & !0x1ffff,
        target_unknown: raw.target & !0x1ffff,
    }
}

/// A physical-unit view of a supported range. The raw range remains available for
/// callers that need its exact integer representation.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct NormalizedRange {
    pub kind: RangeKind,
    pub minimum: f32,
    pub maximum: f32,
    pub increment: f32,
}

/// Converts a decoded range using its explicit codec-selected scale.
pub fn normalize_range(raw: RawRange) -> NormalizedRange {
    let scale = 1.0 / raw.scale_divisor as f32;
    NormalizedRange {
        kind: raw.kind,
        minimum: raw.minimum as f32 * scale,
        maximum: raw.maximum as f32 * scale,
        increment: raw.increment as f32 * scale,
    }
}

/// Human-unit Control Point input. This is deliberately separate from
/// `ControlRequest`, whose operands are exact wire integers.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum NormalizedControlRequest {
    RequestControl,
    Reset,
    TargetSpeedKph(f32),
    TargetInclinationPercent(f32),
    TargetResistanceLevel(f32),
    TargetPowerWatts(i16),
    TargetHeartRateBpm(u8),
    StartResume,
    StopPause {
        action: u8,
    },
    TargetEnergyKcal(u16),
    TargetSteps(u16),
    TargetStrides(u16),
    TargetDistanceMetres(u32),
    TargetTrainingSeconds(u16),
    TargetTimeTwoHrZones([u16; 2]),
    TargetTimeThreeHrZones([u16; 3]),
    TargetTimeFiveHrZones([u16; 5]),
    IndoorBikeSimulation {
        wind_speed_mps: f32,
        grade_percent: f32,
        crr: f32,
        cw_kg_per_m: f32,
    },
    WheelCircumferenceMm(u16),
    SpinDown {
        action: u8,
    },
    TargetCadenceRpm(f32),
}

fn scaled(value: f32, scale: f32) -> Result<i32, Error> {
    let raw = f64::from(value) * f64::from(scale);
    if !raw.is_finite() || raw < f64::from(i32::MIN) || raw > f64::from(i32::MAX) {
        return Err(Error::InvalidRange);
    }
    let rounded = if raw >= 0.0 {
        (raw + 0.5) as i32
    } else {
        (raw - 0.5) as i32
    };
    // Allow only the input f32's representation error, not arbitrary rounding
    // to a different wire value. f64 prevents a second f32 multiplication error.
    let tolerance = f64::from(f32::EPSILON) * raw.abs().max(1.0);
    if (raw - f64::from(rounded)).abs() > tolerance {
        return Err(Error::InvalidRange);
    }
    Ok(rounded)
}

/// Converts human-unit command input into the raw request consumed by the codec.
/// Values must lie on the wire grid, allowing f32 representation error only.
/// Resistance uses signed-16-bit tenths (`ControlOptions::default()`); callers
/// must use that same profile when encoding the returned request.
/// The caller still owns authorization and transmission of the encoded bytes.
pub fn normalize_control_request(value: NormalizedControlRequest) -> Result<ControlRequest, Error> {
    let (opcode, operands, operand_count) = match value {
        NormalizedControlRequest::RequestControl => (0, [0; 5], 0),
        NormalizedControlRequest::Reset => (1, [0; 5], 0),
        NormalizedControlRequest::TargetSpeedKph(v) => (2, [scaled(v, 100.0)?, 0, 0, 0, 0], 1),
        NormalizedControlRequest::TargetInclinationPercent(v) => {
            (3, [scaled(v, 10.0)?, 0, 0, 0, 0], 1)
        }
        NormalizedControlRequest::TargetResistanceLevel(v) => {
            (4, [scaled(v, 10.0)?, 0, 0, 0, 0], 1)
        }
        NormalizedControlRequest::TargetPowerWatts(v) => (5, [v as i32, 0, 0, 0, 0], 1),
        NormalizedControlRequest::TargetHeartRateBpm(v) => (6, [v as i32, 0, 0, 0, 0], 1),
        NormalizedControlRequest::StartResume => (7, [0; 5], 0),
        NormalizedControlRequest::StopPause { action } => (8, [action as i32, 0, 0, 0, 0], 1),
        NormalizedControlRequest::TargetEnergyKcal(v) => (9, [v as i32, 0, 0, 0, 0], 1),
        NormalizedControlRequest::TargetSteps(v) => (10, [v as i32, 0, 0, 0, 0], 1),
        NormalizedControlRequest::TargetStrides(v) => (11, [v as i32, 0, 0, 0, 0], 1),
        NormalizedControlRequest::TargetDistanceMetres(v) => (12, [v as i32, 0, 0, 0, 0], 1),
        NormalizedControlRequest::TargetTrainingSeconds(v) => (13, [v as i32, 0, 0, 0, 0], 1),
        NormalizedControlRequest::TargetTimeTwoHrZones(v) => {
            (14, [v[0] as i32, v[1] as i32, 0, 0, 0], 2)
        }
        NormalizedControlRequest::TargetTimeThreeHrZones(v) => {
            (15, [v[0] as i32, v[1] as i32, v[2] as i32, 0, 0], 3)
        }
        NormalizedControlRequest::TargetTimeFiveHrZones(v) => (
            16,
            [
                v[0] as i32,
                v[1] as i32,
                v[2] as i32,
                v[3] as i32,
                v[4] as i32,
            ],
            5,
        ),
        NormalizedControlRequest::IndoorBikeSimulation {
            wind_speed_mps,
            grade_percent,
            crr,
            cw_kg_per_m,
        } => (
            17,
            [
                scaled(wind_speed_mps, 1000.0)?,
                scaled(grade_percent, 100.0)?,
                scaled(crr, 10000.0)?,
                scaled(cw_kg_per_m, 100.0)?,
                0,
            ],
            4,
        ),
        // Codec-v1's public millimetre input maps to the FTMS 0.1 mm wire unit.
        NormalizedControlRequest::WheelCircumferenceMm(v) => (18, [v as i32 * 10, 0, 0, 0, 0], 1),
        NormalizedControlRequest::SpinDown { action } => (19, [action as i32, 0, 0, 0, 0], 1),
        NormalizedControlRequest::TargetCadenceRpm(v) => (20, [scaled(v, 2.0)?, 0, 0, 0, 0], 1),
    };
    let raw = ControlRequest {
        opcode,
        operands,
        operand_count,
    };
    // This normalized API has one explicit resistance profile: signed 16-bit
    // tenths, matching FTMS 1.0/EC23224. Reuse the raw encoder's width and action
    // validation so successful construction always yields encodable raw input.
    let mut scratch = [0; 11];
    crate::encode_control_request(raw, ControlOptions::default(), &mut scratch)?;
    Ok(raw)
}

/// A normalized Control Point response without packet-format diagnostics.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct NormalizedControlResponse {
    pub request_opcode: u8,
    pub result_code: u8,
    pub spin_down_speeds_kph: Option<(f32, f32)>,
    pub unknown_result: bool,
}

/// Rejects raw response evidence with unexpected parameters; preserves an unknown
/// result code as an explicit normalized diagnostic rather than inventing a name.
pub fn normalize_control_response(
    raw: ControlResponse,
) -> Result<NormalizedControlResponse, Error> {
    if raw.request_opcode > 20
        || raw.unexpected_parameters != 0
        || raw.unknown_request != 0
        || raw.parameter > 1
        || (raw.parameter == 1 && (raw.request_opcode != 19 || raw.result_code != 1))
    {
        return Err(Error::InvalidKind);
    }
    Ok(NormalizedControlResponse {
        request_opcode: raw.request_opcode,
        result_code: raw.result_code,
        spin_down_speeds_kph: (raw.parameter == 1)
            .then(|| (raw.low as f32 / 100.0, raw.high as f32 / 100.0)),
        unknown_result: !(1..=5).contains(&raw.result_code),
    })
}

/// Defined Fitness Machine Status projection. `parameter` retains the decoded
/// raw request-shaped operands in wire units; it does not authorize sending a
/// command. `action` preserves Stop/Pause and Spin Down status action values.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct NormalizedMachineStatus {
    pub code: u8,
    pub label: &'static str,
    pub parameter: Option<ControlRequest>,
    pub action: Option<u8>,
}

/// Projects every defined, non-diagnostic Machine Status opcode. Unknown,
/// incomplete, reserved, and trailing raw evidence is intentionally rejected.
pub fn normalize_machine_status(raw: RawMachineStatus) -> Result<NormalizedMachineStatus, Error> {
    if raw.unknown_opcode || raw.reserved_value || raw.truncated || raw.trailing_bytes {
        return Err(Error::InvalidKind);
    }
    let label = match raw.opcode {
        1 => "reset",
        2 => "stopped_or_paused",
        3 => "stopped_by_safety_key",
        4 => "started_or_resumed",
        5 => "target_speed_changed",
        6 => "target_inclination_changed",
        7 => "target_resistance_changed",
        8 => "target_power_changed",
        9 => "target_heart_rate_changed",
        10 => "targeted_expended_energy_changed",
        11 => "targeted_step_number_changed",
        12 => "targeted_stride_number_changed",
        13 => "targeted_distance_changed",
        14 => "targeted_training_time_changed",
        15 => "targeted_time_two_hr_zones_changed",
        16 => "targeted_time_three_hr_zones_changed",
        17 => "targeted_time_five_hr_zones_changed",
        18 => "indoor_bike_simulation_parameters_changed",
        19 => "wheel_circumference_changed",
        20 => "spin_down_status",
        21 => "targeted_cadence_changed",
        255 => "control_permission_lost",
        _ => return Err(Error::InvalidKind),
    };
    Ok(NormalizedMachineStatus {
        code: raw.opcode,
        label,
        parameter: raw.parameter,
        action: matches!(raw.opcode, 2 | 20).then_some(raw.action),
    })
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Metric {
    SpeedMetresPerSecond,
    AverageSpeedMetresPerSecond,
    DistanceMetres,
    InclinationPercent,
    RampAngleDegrees,
    PositiveElevationMetres,
    NegativeElevationMetres,
    InstantaneousPaceSecondsPer500Metres,
    AveragePaceSecondsPer500Metres,
    EnergyKcal,
    EnergyPerHourKcal,
    EnergyPerMinuteKcal,
    HeartRateBpm,
    MetabolicEquivalent,
    ElapsedSeconds,
    RemainingSeconds,
    ForceNewtons,
    PowerWatts,
    AveragePowerWatts,
    StepRatePerMinute,
    AverageStepRatePerMinute,
    StrideCount,
    ResistanceLevel,
    FloorCount,
    StepCount,
    StrokeRatePerMinute,
    StrokeCount,
    AverageStrokeRatePerMinute,
    CadenceRpm,
    AverageCadenceRpm,
}

fn field(metric: Metric) -> F {
    match metric {
        Metric::SpeedMetresPerSecond => F::Speed,
        Metric::AverageSpeedMetresPerSecond => F::AverageSpeed,
        Metric::DistanceMetres => F::Distance,
        Metric::InclinationPercent => F::Inclination,
        Metric::RampAngleDegrees => F::RampAngle,
        Metric::PositiveElevationMetres => F::PositiveElevation,
        Metric::NegativeElevationMetres => F::NegativeElevation,
        Metric::InstantaneousPaceSecondsPer500Metres => F::InstantaneousPace,
        Metric::AveragePaceSecondsPer500Metres => F::AveragePace,
        Metric::EnergyKcal => F::Energy,
        Metric::EnergyPerHourKcal => F::EnergyPerHour,
        Metric::EnergyPerMinuteKcal => F::EnergyPerMinute,
        Metric::HeartRateBpm => F::HeartRate,
        Metric::MetabolicEquivalent => F::Met,
        Metric::ElapsedSeconds => F::Elapsed,
        Metric::RemainingSeconds => F::Remaining,
        Metric::ForceNewtons => F::Force,
        Metric::PowerWatts => F::Power,
        Metric::AveragePowerWatts => F::AveragePower,
        Metric::StepRatePerMinute => F::StepRate,
        Metric::AverageStepRatePerMinute => F::AverageStepRate,
        Metric::StrideCount => F::StrideCount,
        Metric::ResistanceLevel => F::Resistance,
        Metric::FloorCount => F::FloorCount,
        Metric::StepCount => F::StepCount,
        Metric::StrokeRatePerMinute => F::StrokeRate,
        Metric::StrokeCount => F::StrokeCount,
        Metric::AverageStrokeRatePerMinute => F::AverageStrokeRate,
        Metric::CadenceRpm => F::Cadence,
        Metric::AverageCadenceRpm => F::AverageCadence,
    }
}

/// Returns `None` for a flag-absent (including not-yet-received truncated) field.
pub fn normalized_measurement(
    m: &RawMeasurement,
    options: MeasurementOptions,
    metric: Metric,
) -> Option<NormalizedValue> {
    let f = field(metric);
    if m.present & f.mask() == 0 {
        return None;
    }
    if m.unavailable & f.mask() != 0 {
        return Some(NormalizedValue::Unavailable);
    }
    let mut scale = match metric {
        Metric::SpeedMetresPerSecond | Metric::AverageSpeedMetresPerSecond => 1.0 / 360.0,
        Metric::InclinationPercent | Metric::RampAngleDegrees | Metric::MetabolicEquivalent => 0.1,
        Metric::StrokeRatePerMinute
        | Metric::AverageStrokeRatePerMinute
        | Metric::CadenceRpm
        | Metric::AverageCadenceRpm => 0.5,
        _ => 1.0,
    };
    if matches!(
        metric,
        Metric::PositiveElevationMetres | Metric::NegativeElevationMetres
    ) && m.kind == MeasurementKind::Treadmill
    {
        scale = 0.1;
    }
    if metric == Metric::StrideCount && m.kind == MeasurementKind::CrossTrainer {
        scale = 0.1;
    }
    if metric == Metric::ResistanceLevel
        && options.resistance_format
            == crate::measurement::MeasurementResistanceFormat::Signed16Tenths
    {
        scale = 0.1;
    }
    if matches!(
        metric,
        Metric::InstantaneousPaceSecondsPer500Metres | Metric::AveragePaceSecondsPer500Metres
    ) && m.kind == MeasurementKind::Treadmill
        && options.treadmill_pace_format == TreadmillPaceFormat::Uint8Legacy
    {
        return Some(NormalizedValue::UnknownUnit);
    }
    Some(NormalizedValue::Number(m.values[f.index()] as f32 * scale))
}
