/// Transport-independent Bluetooth Fitness Machine Service protocol tools.
///
/// Codecs operate synchronously on caller-provided bytes. Capability reports
/// describe static evidence, never permission to transmit or operate equipment.
/// Bluetooth, subscriptions, security, ownership and physical safety stay with
/// the application. Raw wire values remain available alongside normalized views.
library;

export 'src/capabilities.dart'
    show
        CapabilityDiscovery,
        CapabilityServiceScope,
        CapabilityReadState,
        CapabilityReadReason,
        CapabilityTruth,
        CapabilityPresence,
        CapabilityDecode,
        CapabilityDeclaration,
        CapabilityPrerequisite,
        CapabilityKnownKind,
        CapabilityDiagnosticCode,
        CapabilityResistanceRangeFormat,
        CapabilityCharacteristic,
        CapabilityC7Evidence,
        CapabilitySnapshot,
        CapabilityRangeValue,
        CapabilityRangeEvidence,
        CapabilityOperation,
        CapabilityObservation,
        CapabilityDiagnostic,
        CapabilityFeatureEvidence,
        CapabilityReport,
        evaluateCapabilities;
export 'src/control_point.dart'
    show
        ResistanceControlFormat,
        ControlErrorCode,
        ControlCodecException,
        ControlRequest,
        ControlResponse,
        decodeControlRequest,
        encodeControlRequest,
        decodeControlResponse,
        encodeControlResponse;
export 'src/measurements.dart'
    show
        MeasurementKind,
        MeasurementResistanceFormat,
        MeasurementTreadmillPaceFormat,
        MeasurementFormatOptions,
        MeasurementField,
        MeasurementCodecErrorCode,
        MeasurementCodecException,
        MeasurementRaw,
        decodeMeasurement,
        encodeMeasurement;
export 'src/normalized.dart'
    show MeasurementDirection, MeasurementNormalized, normalizeMeasurement;
export 'src/statuses.dart'
    show
        MachineStatusParameter,
        MachineStatus,
        TrainingStatus,
        decodeMachineStatus,
        encodeMachineStatus,
        decodeTrainingStatus,
        encodeTrainingStatus;
export 'src/values.dart'
    show
        RangeKind,
        RangeUnit,
        ResistanceRangeFormat,
        RangeProfile,
        RangeStatus,
        Features,
        SupportedRange,
        RangeCandidate,
        RangeInspection,
        decodeFeatures,
        encodeFeatures,
        decodeSupportedRange,
        encodeSupportedRange,
        inspectSupportedRange;
