"""Bidirectional raw FTMS Features codec and normalized Feature view."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ._binary import Reader, Writer, immutable_bytes
from ._errors import RawCodecError


@dataclass(frozen=True, slots=True)
class FeaturesRaw:
    """Uninterpreted unsigned 32-bit Feature words, including reserved bits."""

    machine: int
    target: int


@dataclass(frozen=True, slots=True)
class FeatureDiagnostic:
    """Non-throwing normalized decode diagnostic."""

    code: Literal["length"]
    offset: int
    expected: int
    actual: int
    message: str


@dataclass(frozen=True, slots=True)
class FeatureDecodeResult:
    """Immutable normalized decode result; exactly one of value/diagnostic is set."""

    ok: bool
    value: Features | None
    diagnostic: FeatureDiagnostic | None


_MACHINE_BITS = (
    "average_speed_supported cadence_supported total_distance_supported inclination_supported "
    "elevation_gain_supported pace_supported step_count_supported resistance_level_supported "
    "stride_count_supported expended_energy_supported heart_rate_measurement_supported "
    "metabolic_equivalent_supported elapsed_time_supported remaining_time_supported "
    "power_measurement_supported force_on_belt_supported user_data_retention_supported"
).split()
_TARGET_BITS = (
    "speed_target_setting_supported inclination_target_setting_supported resistance_target_setting_supported "
    "power_target_setting_supported heart_rate_target_setting_supported targeted_expended_energy_supported "
    "targeted_step_number_supported targeted_stride_number_supported targeted_distance_supported "
    "targeted_training_time_supported targeted_time_two_hr_zones_supported "
    "targeted_time_three_hr_zones_supported targeted_time_five_hr_zones_supported "
    "indoor_bike_simulation_supported wheel_circumference_supported spin_down_control_supported "
    "targeted_cadence_supported"
).split()


@dataclass(frozen=True, slots=True)
class Features:
    """Canonical normalized Feature flags; unknown/reserved bits remain only in ``FeaturesRaw``."""

    average_speed_supported: bool
    cadence_supported: bool
    total_distance_supported: bool
    inclination_supported: bool
    elevation_gain_supported: bool
    pace_supported: bool
    step_count_supported: bool
    resistance_level_supported: bool
    stride_count_supported: bool
    expended_energy_supported: bool
    heart_rate_measurement_supported: bool
    metabolic_equivalent_supported: bool
    elapsed_time_supported: bool
    remaining_time_supported: bool
    power_measurement_supported: bool
    force_on_belt_supported: bool
    user_data_retention_supported: bool
    speed_target_setting_supported: bool
    inclination_target_setting_supported: bool
    resistance_target_setting_supported: bool
    power_target_setting_supported: bool
    heart_rate_target_setting_supported: bool
    targeted_expended_energy_supported: bool
    targeted_step_number_supported: bool
    targeted_stride_number_supported: bool
    targeted_distance_supported: bool
    targeted_training_time_supported: bool
    targeted_time_two_hr_zones_supported: bool
    targeted_time_three_hr_zones_supported: bool
    targeted_time_five_hr_zones_supported: bool
    indoor_bike_simulation_supported: bool
    wheel_circumference_supported: bool
    spin_down_control_supported: bool
    targeted_cadence_supported: bool

    @property
    def supports_erg(self) -> bool:
        return self.power_target_setting_supported

    @property
    def supports_sim(self) -> bool:
        return self.indoor_bike_simulation_supported

    @property
    def supports_resistance(self) -> bool:
        return self.resistance_target_setting_supported


def _validate_word(value: object, name: str) -> int:
    if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
        raise RawCodecError("range", f"{name} must be an integer from 0 through 4294967295")
    return value


def decode_features_raw(data: bytes | bytearray | memoryview) -> FeaturesRaw:
    """Decode exactly eight Feature bytes, preserving both raw words verbatim."""
    bytes_ = immutable_bytes(data)
    if len(bytes_) != 8:
        raise RawCodecError("length", "FTMS Features requires exactly 8 bytes")
    reader = Reader(bytes_)
    return FeaturesRaw(machine=reader.u32le(), target=reader.u32le())


def encode_features_raw(features: FeaturesRaw) -> bytes:
    """Encode both unsigned 32-bit Feature words, including unknown/reserved bits."""
    if not isinstance(features, FeaturesRaw):
        raise RawCodecError("kind", "FeaturesRaw value is required")
    writer = Writer()
    writer.u32le(_validate_word(features.machine, "machine"))
    writer.u32le(_validate_word(features.target, "target"))
    return writer.finish()


def _normalized(raw: FeaturesRaw) -> Features:
    values = {name: bool(raw.machine & (1 << bit)) for bit, name in enumerate(_MACHINE_BITS)}
    values.update({name: bool(raw.target & (1 << bit)) for bit, name in enumerate(_TARGET_BITS)})
    return Features(**values)


def decode_features(data: bytes | bytearray | memoryview) -> FeatureDecodeResult:
    """Decode a normalized view, returning a length diagnostic rather than throwing for length."""
    bytes_ = immutable_bytes(data)
    if len(bytes_) != 8:
        return FeatureDecodeResult(
            ok=False,
            value=None,
            diagnostic=FeatureDiagnostic(
                code="length",
                offset=0,
                expected=8,
                actual=len(bytes_),
                message=f"Expected exactly 8 bytes, received {len(bytes_)}",
            ),
        )
    return FeatureDecodeResult(
        ok=True, value=_normalized(decode_features_raw(bytes_)), diagnostic=None
    )
