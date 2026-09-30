"""Pure FTMS protocol codecs; this alpha intentionally has partial API coverage."""

from ._errors import RawCodecError
from .features import (
    FeatureDecodeResult,
    FeatureDiagnostic,
    Features,
    FeaturesRaw,
    decode_features,
    decode_features_raw,
    encode_features_raw,
)
from .measurements import (
    MeasurementFormatOptions,
    MeasurementRaw,
    decode_measurement_raw,
    encode_measurement_raw,
    normalize_measurement,
)
from .statuses import (
    MachineStatusRaw,
    TrainingStatusRaw,
    decode_machine_status_raw,
    decode_training_status_raw,
    encode_machine_status_raw,
    encode_training_status_raw,
    normalize_machine_status,
    normalize_training_status,
)

__all__ = [
    "FeatureDecodeResult",
    "FeatureDiagnostic",
    "Features",
    "FeaturesRaw",
    "RawCodecError",
    "decode_features",
    "decode_features_raw",
    "encode_features_raw",
]
from .control import (
    ControlFormatOptions,
    ControlRequestRaw,
    ControlResponseRaw,
    decode_control_request_raw,
    decode_control_response_raw,
    encode_control_request_raw,
    encode_control_response_raw,
)
from .ranges import (
    RangeFormatOptions,
    SupportedRange,
    SupportedRangeRaw,
    decode_supported_range,
    decode_supported_range_raw,
    encode_supported_range_raw,
    inspect_supported_range_raw,
)

__all__ += [
    "RangeFormatOptions",
    "SupportedRange",
    "SupportedRangeRaw",
    "decode_supported_range",
    "decode_supported_range_raw",
    "encode_supported_range_raw",
    "inspect_supported_range_raw",
    "ControlFormatOptions",
    "ControlRequestRaw",
    "ControlResponseRaw",
    "decode_control_request_raw",
    "encode_control_request_raw",
    "decode_control_response_raw",
    "encode_control_response_raw",
]
__all__ += [
    "MeasurementFormatOptions",
    "MeasurementRaw",
    "decode_measurement_raw",
    "encode_measurement_raw",
    "normalize_measurement",
    "MachineStatusRaw",
    "TrainingStatusRaw",
    "decode_machine_status_raw",
    "encode_machine_status_raw",
    "decode_training_status_raw",
    "encode_training_status_raw",
    "normalize_machine_status",
    "normalize_training_status",
]
