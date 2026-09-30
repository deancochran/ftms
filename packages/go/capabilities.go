package ftms

// Static capability interpretation. This file deliberately consumes only a
// caller supplied snapshot; it performs no GATT I/O and makes no control claim.

import "encoding/binary"

// DiscoveryState describes caller-owned enumeration completeness.
type DiscoveryState uint8

const (
	DiscoveryNotAttempted DiscoveryState = iota
	DiscoveryPartial
	DiscoveryComplete
	DiscoveryFailed
)

// ServiceScope identifies whether one FTMS service instance is selected.
type ServiceScope uint8

const (
	ScopeUnknown ServiceScope = iota
	ScopePresent
	ScopeAbsent
	ScopeAmbiguous
)

// Presence distinguishes unknown, confirmed absent, unique and duplicate evidence.
type Presence uint8

const (
	PresenceUnknown Presence = iota
	PresenceAbsent
	PresenceUnique
	PresenceAmbiguous
)

// ReadState distinguishes an unattempted read from a successful or failed read.
type ReadState uint8

const (
	ReadNotAttempted ReadState = iota
	ReadSuccess
	ReadFailed
)

// ReadReason is a platform-independent explanation for a failed read.
type ReadReason uint8

const (
	ReasonNone ReadReason = iota
	ReasonGeneric
	ReasonSecurityRequired
	ReasonUnavailable
	ReasonTimeout
	ReasonDisconnected
)

// DecodeState describes interpretation of read evidence, independently of properties.
type DecodeState uint8

const (
	DecodeNotAttempted DecodeState = iota
	DecodeValid
	DecodeMalformed
	DecodeFailed
)

// Declaration reports protocol support, not current permission to execute.
type Declaration uint8

const (
	DeclarationUnknown Declaration = iota
	DeclarationNotSupported
	DeclarationSupported
)

// Prerequisite reports static evidence completeness and consistency only.
type Prerequisite uint8

const (
	PrerequisiteNotApplicable Prerequisite = iota
	PrerequisiteSatisfied
	PrerequisiteIncomplete
	PrerequisiteInconsistent
)

// Truth retains unknown separately from false for caller-owned C.7 evidence.
type Truth uint8

const (
	TruthUnknown Truth = iota
	TruthFalse
	TruthTrue
)

// CharacteristicKind indexes CapabilityReport.Presence. KindUnknown has no
// aggregate presence meaning; unknown UUIDs remain individual observations.
type CharacteristicKind uint8

const (
	KindUnknown CharacteristicKind = iota
	KindFeature
	KindTreadmillData
	KindCrossTrainerData
	KindStepClimberData
	KindStairClimberData
	KindRowerData
	KindIndoorBikeData
	KindTrainingStatus
	KindSpeedRange
	KindInclinationRange
	KindResistanceRange
	KindHeartRateRange
	KindPowerRange
	KindControlPoint
	KindMachineStatus
)

// UUID holds all 128 bits in canonical display/network order, not BLE wire order.
type UUID [16]byte

// CharacteristicObservation describes one characteristic in the selected service.
// Bytes must be empty except for ReadSuccess; Reason must be ReasonNone except
// for ReadFailed. Successful empty bytes are valid input but malformed read evidence.
type CharacteristicObservation struct {
	UUID       UUID
	Properties uint16
	ReadState  ReadState
	Reason     ReadReason
	Bytes      []byte
}

// C7Evidence controls Feature's conditional Indicate requirement. A zero value
// means unknown, not false. This says nothing about current connection security.
type C7Evidence struct{ BondingSupported, FeatureMayChangeOverLifetime Truth }

// CapabilitySnapshot covers exactly one service instance and discovery generation.
// Callers own freshness and must not merge observations from different instances.
type CapabilitySnapshot struct {
	Discovery       DiscoveryState
	Scope           ServiceScope
	Generation      uint32
	Characteristics []CharacteristicObservation
	C7              C7Evidence
}

// CapabilityOptions selects resistance-range decoding only. It does not select
// measurement or Control Point formats, nor infer a format from the observed bytes.
type CapabilityOptions struct{ Range RangeOptions }

// ObservationReport retains input identity and read metadata, not caller bytes.
type ObservationReport struct {
	InputIndex int
	UUID       UUID
	Properties uint16
	KnownKind  CharacteristicKind
	ReadState  ReadState
	Reason     ReadReason
	ReadSize   int
}

// FeatureReport preserves raw words even when characteristic properties are invalid.
// InputIndex is meaningful only when HasInputIndex is true; raw words only when
// Decode is DecodeValid. Duplicate observations are never selected for decoding.
type FeatureReport struct {
	Presence                                             Presence
	Decode                                               DecodeState
	InputIndex                                           int
	HasInputIndex                                        bool
	MachineRaw, TargetRaw, MachineUnknown, TargetUnknown uint32
}

// RangeValue retains exact integer numerators; divide by ScaleDivisor for physical
// values. Unit uses RangeKind's speed/km/h, inclination/percent, resistance/level,
// heart-rate/bpm and power/watts order.
type RangeValue struct {
	Kind                        RangeKind
	Minimum, Maximum, Increment int32
	ScaleDivisor                int32
	Unit                        RangeKind
}

// RangeReport separates presence, read/decode outcomes and an optional valid value.
// InputIndex is meaningful only when HasInputIndex is true.
type RangeReport struct {
	Presence      Presence
	Decode        DecodeState
	InputIndex    int
	HasInputIndex bool
	Value         *RangeValue
}

// OperationReport covers one wire opcode. TargetBit is 255 for base procedures.
// Reasons is a bitwise combination of CapabilityReason constants. Satisfied
// prerequisites are static protocol evidence, never authorization to send a command.
type OperationReport struct {
	Opcode          uint8
	TargetBit       uint8
	OptionalInTable bool
	Declaration     Declaration
	Prerequisite    Prerequisite
	Reasons         uint16
}

// DiagnosticCode is a stable capability-contract diagnostic, not a platform error.
type DiagnosticCode uint8

const (
	DiagnosticScopeUnavailable DiagnosticCode = iota
	DiagnosticDiscoveryIncomplete
	DiagnosticDiscoveryFailed
	DiagnosticDuplicateCharacteristic
	DiagnosticRequiredCharacteristicMissing
	DiagnosticRequiredPropertyMissing
	DiagnosticExcludedPropertyPresent
	DiagnosticReadFailed
	DiagnosticReadSecurityRequired
	DiagnosticMalformedBytes
	DiagnosticRequiredRangeMissing
	DiagnosticScopeContradiction
	DiagnosticInsufficientC7
)

// CapabilityDiagnostic links a stable reason to a known kind and optional input.
type CapabilityDiagnostic struct {
	Code          DiagnosticCode
	KnownKind     CharacteristicKind
	InputIndex    int
	HasInputIndex bool
}

// CapabilityReport owns its slices and range values. Ranges are in RangeKind
// order (heart rate before power); Operations are indexed by opcode 0 through 20.
// Observation indices refer back to the caller snapshot. No input bytes are retained.
type CapabilityReport struct {
	Generation       uint32
	Discovery        DiscoveryState
	Scope            ServiceScope
	ObservationCount int
	DiagnosticCount  int
	Presence         [16]Presence
	Feature          FeatureReport
	Ranges           [5]RangeReport
	Operations       [21]OperationReport
	Observations     []ObservationReport
	Diagnostics      []CapabilityDiagnostic
}

// CapabilityReason flags preserve both unavailable and contradictory evidence.
const (
	CapabilityReasonScopeUnavailable uint16 = 1 << iota
	CapabilityReasonDiscoveryIncomplete
	CapabilityReasonFeatureUnavailable
	CapabilityReasonFeatureInvalid
	CapabilityReasonControlUnavailable
	CapabilityReasonControlInvalid
	CapabilityReasonStatusUnavailable
	CapabilityReasonStatusInvalid
	CapabilityReasonRangeUnavailable
	CapabilityReasonRangeInvalid
	CapabilityReasonC7Insufficient
)

// Characteristic property masks retain the standard GATT bit positions. Unknown
// bits remain in the supplied uint16 and are diagnosed for known characteristics.
const (
	PropertyRead     uint16 = 0x02
	PropertyWrite    uint16 = 0x08
	PropertyNotify   uint16 = 0x10
	PropertyIndicate uint16 = 0x20
)

const baseUUID = "\x00\x00\x10\x00\x80\x00\x00\x80\x5f\x9b\x34\xfb"

// UUID16 expands a 16-bit assigned number into the full Bluetooth base UUID.
func UUID16(short uint16) UUID {
	var u UUID
	binary.BigEndian.PutUint16(u[2:4], short)
	copy(u[4:], baseUUID)
	return u
}
func kindOf(u UUID) CharacteristicKind {
	if u[0] != 0 || u[1] != 0 {
		return KindUnknown
	}
	for i := 0; i < 12; i++ {
		if u[i+4] != baseUUID[i] {
			return KindUnknown
		}
	}
	switch binary.BigEndian.Uint16(u[2:4]) {
	case 0x2acc:
		return KindFeature
	case 0x2acd:
		return KindTreadmillData
	case 0x2ace:
		return KindCrossTrainerData
	case 0x2acf:
		return KindStepClimberData
	case 0x2ad0:
		return KindStairClimberData
	case 0x2ad1:
		return KindRowerData
	case 0x2ad2:
		return KindIndoorBikeData
	case 0x2ad3:
		return KindTrainingStatus
	case 0x2ad4:
		return KindSpeedRange
	case 0x2ad5:
		return KindInclinationRange
	case 0x2ad6:
		return KindResistanceRange
	case 0x2ad7:
		return KindHeartRateRange
	case 0x2ad8:
		return KindPowerRange
	case 0x2ad9:
		return KindControlPoint
	case 0x2ada:
		return KindMachineStatus
	}
	return KindUnknown
}
func (r *CapabilityReport) diag(c DiagnosticCode, k CharacteristicKind, i int, has bool) {
	r.Diagnostics = append(r.Diagnostics, CapabilityDiagnostic{c, k, i, has})
}
func requiredProperties(k CharacteristicKind) uint16 {
	switch k {
	case KindFeature, KindSpeedRange, KindInclinationRange, KindResistanceRange, KindHeartRateRange, KindPowerRange:
		return 2
	case KindTreadmillData, KindCrossTrainerData, KindStepClimberData, KindStairClimberData, KindRowerData, KindIndoorBikeData, KindMachineStatus:
		return 16
	case KindTrainingStatus:
		return 18
	case KindControlPoint:
		return 40
	}
	return 0
}

// Target bits 3 and 4 are power and heart rate, unlike the range report order.
func rangeForTarget(bit uint8) RangeKind {
	if bit == 3 {
		return PowerRange
	}
	if bit == 4 {
		return HeartRateRange
	}
	return RangeKind(bit)
}

func c7Unknown(e C7Evidence) bool {
	return e.BondingSupported != TruthFalse && e.FeatureMayChangeOverLifetime != TruthFalse &&
		(e.BondingSupported == TruthUnknown || e.FeatureMayChangeOverLifetime == TruthUnknown)
}

func propertyRequirements(k CharacteristicKind, e C7Evidence) (required, allowed uint16) {
	required = requiredProperties(k)
	if k == KindFeature && e.BondingSupported == TruthTrue && e.FeatureMayChangeOverLifetime == TruthTrue {
		required |= 32
	}
	allowed = required
	if k == KindFeature && c7Unknown(e) {
		allowed |= 32
	}
	return
}

func characteristicReasons(p Presence, properties, required, allowed, unavailable, invalid uint16) uint16 {
	if p == PresenceUnknown {
		return unavailable
	}
	if p != PresenceUnique {
		return invalid
	}
	if properties&required != required || properties&^allowed != 0 {
		return invalid
	}
	return 0
}

func decodeReasons(state DecodeState, unavailable, invalid uint16) uint16 {
	if state == DecodeValid {
		return 0
	}
	if state == DecodeMalformed {
		return invalid
	}
	return unavailable
}

// InterpretCapabilities evaluates a caller-supplied snapshot without I/O, hidden
// state, or execution permission. Invalid enums/read combinations/options return
// ErrKind and a zero report. Malformed successful reads are diagnostic evidence,
// not API errors. Inputs are not mutated or retained; do not mutate them during
// the call. All returned mutable storage belongs to the caller.
func InterpretCapabilities(s CapabilitySnapshot, o CapabilityOptions) (CapabilityReport, error) {
	if s.Discovery > DiscoveryFailed || s.Scope > ScopeAmbiguous || s.C7.BondingSupported > TruthTrue || s.C7.FeatureMayChangeOverLifetime > TruthTrue || o.Range.Resistance > ResistanceSint16Tenths {
		return CapabilityReport{}, ErrKind
	}
	r := CapabilityReport{Generation: s.Generation, Discovery: s.Discovery, Scope: s.Scope, ObservationCount: len(s.Characteristics)}
	first := [16]int{}
	counts := [16]int{}
	for i := range first {
		first[i] = -1
	}
	for i, x := range s.Characteristics {
		if x.ReadState > ReadFailed || x.Reason > ReasonDisconnected || (x.ReadState != ReadFailed && x.Reason != ReasonNone) || (x.ReadState != ReadSuccess && len(x.Bytes) != 0) {
			return CapabilityReport{}, ErrKind
		}
		k := kindOf(x.UUID)
		r.Observations = append(r.Observations, ObservationReport{i, x.UUID, x.Properties, k, x.ReadState, x.Reason, len(x.Bytes)})
		if k != KindUnknown {
			counts[k]++
			if first[k] < 0 {
				first[k] = i
			}
		}
	}
	for k := CharacteristicKind(1); k <= KindMachineStatus; k++ {
		if counts[k] > 1 {
			r.Presence[k] = PresenceAmbiguous
		} else if counts[k] == 1 {
			r.Presence[k] = PresenceUnique
		} else if s.Scope == ScopePresent && s.Discovery == DiscoveryComplete {
			r.Presence[k] = PresenceAbsent
		} else {
			r.Presence[k] = PresenceUnknown
		}
	}
	// duplicates always lead the diagnostic sequence.
	for k := CharacteristicKind(1); k <= KindMachineStatus; k++ {
		if counts[k] > 1 {
			r.diag(DiagnosticDuplicateCharacteristic, k, first[k], true)
		}
	}
	derived := s.Scope == ScopePresent
	if !derived {
		r.diag(DiagnosticScopeUnavailable, KindUnknown, 0, false)
		if s.Scope == ScopeAbsent && (len(s.Characteristics) > 0 || s.Discovery != DiscoveryComplete) {
			r.diag(DiagnosticScopeContradiction, KindUnknown, 0, false)
		}
	}
	if s.Discovery == DiscoveryPartial || s.Discovery == DiscoveryNotAttempted {
		r.diag(DiagnosticDiscoveryIncomplete, KindUnknown, 0, false)
	} else if s.Discovery == DiscoveryFailed {
		r.diag(DiagnosticDiscoveryFailed, KindUnknown, 0, false)
	}
	r.Feature.Presence = r.Presence[KindFeature]
	for j := range r.Ranges {
		r.Ranges[j].Presence = r.Presence[KindSpeedRange+CharacteristicKind(j)]
	}
	if derived {
		for _, x := range r.Observations {
			k := x.KnownKind
			if k == KindUnknown {
				continue
			}
			required, allowed := propertyRequirements(k, s.C7)
			if x.Properties&required != required {
				r.diag(DiagnosticRequiredPropertyMissing, k, x.InputIndex, true)
			}
			if x.Properties&^allowed != 0 {
				r.diag(DiagnosticExcludedPropertyPresent, k, x.InputIndex, true)
			}
			if k == KindFeature && c7Unknown(s.C7) {
				r.diag(DiagnosticInsufficientC7, k, x.InputIndex, true)
			}
			if x.ReadState == ReadFailed {
				c := DiagnosticReadFailed
				if x.Reason == ReasonSecurityRequired {
					c = DiagnosticReadSecurityRequired
				}
				r.diag(c, k, x.InputIndex, true)
			}
		}
		// feature/range decoding after property/read diagnostics
		if r.Presence[KindFeature] == PresenceUnique {
			x := r.Observations[first[KindFeature]]
			r.Feature = FeatureReport{PresenceUnique, DecodeNotAttempted, x.InputIndex, true, 0, 0, 0, 0}
			if x.ReadState == ReadFailed {
				r.Feature.Decode = DecodeFailed
			} else if x.ReadState == ReadSuccess {
				f, e := DecodeFeatures(s.Characteristics[first[KindFeature]].Bytes)
				if e != nil {
					r.Feature.Decode = DecodeMalformed
					r.diag(DiagnosticMalformedBytes, KindFeature, x.InputIndex, true)
				} else {
					r.Feature.Decode = DecodeValid
					r.Feature.MachineRaw, r.Feature.TargetRaw, r.Feature.MachineUnknown, r.Feature.TargetUnknown = f.MachineRaw, f.TargetRaw, f.MachineUnknown, f.TargetUnknown
				}
			}
		} else {
			r.Feature.Presence = r.Presence[KindFeature]
		}
		for j := 0; j < 5; j++ {
			k := KindSpeedRange + CharacteristicKind(j)
			rr := RangeReport{Presence: r.Presence[k]}
			if rr.Presence == PresenceUnique {
				x := r.Observations[first[k]]
				rr.InputIndex, rr.HasInputIndex = x.InputIndex, true
				if x.ReadState == ReadFailed {
					rr.Decode = DecodeFailed
				} else if x.ReadState == ReadSuccess {
					options := RangeOptions{}
					if j == int(ResistanceRange) {
						options = o.Range
					}
					v, e := DecodeRange(RangeKind(j), s.Characteristics[first[k]].Bytes, options)
					if e != nil {
						rr.Decode = DecodeMalformed
						r.diag(DiagnosticMalformedBytes, k, x.InputIndex, true)
					} else {
						div := int32(1)
						if j == 0 {
							div = 100
						}
						if j == 1 || j == 2 && o.Range.Resistance == ResistanceSint16Tenths {
							div = 10
						}
						rr.Decode = DecodeValid
						rr.Value = &RangeValue{RangeKind(j), v.Minimum, v.Maximum, v.Increment, div, RangeKind(j)}
					}
				}
			}
			r.Ranges[j] = rr
		}
		if r.Presence[KindFeature] == PresenceAbsent {
			r.diag(DiagnosticRequiredCharacteristicMissing, KindFeature, 0, false)
		}
		if (r.Presence[KindControlPoint] == PresenceUnique || r.Presence[KindControlPoint] == PresenceAmbiguous) && r.Presence[KindMachineStatus] == PresenceAbsent {
			r.diag(DiagnosticRequiredCharacteristicMissing, KindMachineStatus, 0, false)
		}
		if r.Feature.Decode == DecodeValid {
			if r.Feature.TargetRaw&0x1ffff != 0 && r.Presence[KindControlPoint] == PresenceAbsent {
				r.diag(DiagnosticRequiredCharacteristicMissing, KindControlPoint, 0, false)
			}
			for bit := uint8(0); bit < 5; bit++ {
				kind := KindSpeedRange + CharacteristicKind(rangeForTarget(bit))
				if r.Feature.TargetRaw&(1<<bit) != 0 && r.Presence[kind] == PresenceAbsent {
					r.diag(DiagnosticRequiredRangeMissing, kind, 0, false)
				}
			}
		}
	}
	prerequisiteReasons := func(k CharacteristicKind, unavailable, invalid uint16) uint16 {
		required, allowed := propertyRequirements(k, s.C7)
		var properties uint16
		if first[k] >= 0 {
			properties = r.Observations[first[k]].Properties
		}
		reasons := characteristicReasons(r.Presence[k], properties, required, allowed, unavailable, invalid)
		if k == KindFeature && r.Presence[k] == PresenceUnique && c7Unknown(s.C7) {
			reasons |= CapabilityReasonC7Insufficient
		}
		return reasons
	}
	bits := [21]uint8{255, 255, 0, 1, 2, 3, 4, 255, 255, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}
	for op, b := range bits {
		q := OperationReport{Opcode: uint8(op), TargetBit: b, OptionalInTable: op == 18 || op == 19, Declaration: DeclarationUnknown}
		if !derived {
			q.Prerequisite = PrerequisiteIncomplete
			q.Reasons = CapabilityReasonScopeUnavailable
			if s.Scope == ScopeAbsent && s.Discovery == DiscoveryComplete && len(s.Characteristics) == 0 {
				q.Declaration = DeclarationNotSupported
				q.Prerequisite = PrerequisiteNotApplicable
			} else if s.Scope == ScopeAbsent {
				// An absent scope combined with observations or incomplete discovery
				// is contradictory evidence, which takes precedence over unavailable.
				q.Prerequisite = PrerequisiteInconsistent
			}
			r.Operations[op] = q
			continue
		}
		if b == 255 {
			if r.Presence[KindControlPoint] == PresenceUnique {
				q.Declaration = DeclarationSupported
			} else if r.Presence[KindControlPoint] == PresenceAbsent {
				q.Declaration = DeclarationNotSupported
			} else {
				q.Declaration = DeclarationUnknown
			}
		} else if r.Feature.Decode == DecodeValid {
			if r.Feature.TargetRaw&(1<<b) != 0 {
				q.Declaration = DeclarationSupported
			} else {
				q.Declaration = DeclarationNotSupported
			}
		}
		if q.Declaration == DeclarationNotSupported {
			q.Prerequisite = PrerequisiteNotApplicable
			r.Operations[op] = q
			continue
		}
		reasons := uint16(0)
		if s.Discovery != DiscoveryComplete {
			reasons |= CapabilityReasonDiscoveryIncomplete
		}
		reasons |= prerequisiteReasons(KindFeature, CapabilityReasonFeatureUnavailable, CapabilityReasonFeatureInvalid)
		if b != 255 && r.Feature.Presence == PresenceUnique {
			reasons |= decodeReasons(r.Feature.Decode, CapabilityReasonFeatureUnavailable, CapabilityReasonFeatureInvalid)
		}
		reasons |= prerequisiteReasons(KindControlPoint, CapabilityReasonControlUnavailable, CapabilityReasonControlInvalid)
		reasons |= prerequisiteReasons(KindMachineStatus, CapabilityReasonStatusUnavailable, CapabilityReasonStatusInvalid)
		if q.Declaration == DeclarationSupported && b < 5 {
			j := rangeForTarget(b)
			rr := r.Ranges[j]
			reasons |= prerequisiteReasons(KindSpeedRange+CharacteristicKind(j), CapabilityReasonRangeUnavailable, CapabilityReasonRangeInvalid)
			if rr.Presence == PresenceUnique {
				reasons |= decodeReasons(rr.Decode, CapabilityReasonRangeUnavailable, CapabilityReasonRangeInvalid)
			}
		}
		q.Reasons = reasons
		if reasons == 0 {
			q.Prerequisite = PrerequisiteSatisfied
		} else if reasons&(CapabilityReasonFeatureInvalid|CapabilityReasonControlInvalid|CapabilityReasonStatusInvalid|CapabilityReasonRangeInvalid) != 0 {
			q.Prerequisite = PrerequisiteInconsistent
		} else {
			q.Prerequisite = PrerequisiteIncomplete
		}
		r.Operations[op] = q
	}
	r.DiagnosticCount = len(r.Diagnostics)
	return r, nil
}
