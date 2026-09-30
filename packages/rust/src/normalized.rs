//! Physical-unit projections of raw measurement evidence.
//!
//! A metric is omitted when its flag did not select it, and is `Unavailable`
//! when its selected wire representation used the FTMS unavailable sentinel.

use crate::{
    measurement::{
        MeasurementField as F, MeasurementKind, MeasurementOptions, RawMeasurement,
        TreadmillPaceFormat,
    },
    RawFeatures,
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
