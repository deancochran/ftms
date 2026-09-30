package ftms

import (
	"bytes"
	"reflect"
	"testing"
)

func capObs(short uint16, p uint16, state ReadState, b []byte) CharacteristicObservation {
	return CharacteristicObservation{UUID: UUID16(short), Properties: p, ReadState: state, Bytes: b}
}

func completeCapabilitySnapshot() CapabilitySnapshot {
	return CapabilitySnapshot{Scope: ScopePresent, Discovery: DiscoveryComplete, Generation: 42,
		C7: C7Evidence{BondingSupported: TruthFalse}, Characteristics: []CharacteristicObservation{
			capObs(0x2acc, PropertyRead, ReadSuccess, make([]byte, 8)),
			capObs(0x2ad9, PropertyWrite|PropertyIndicate, ReadNotAttempted, nil),
			capObs(0x2ada, PropertyNotify, ReadNotAttempted, nil),
		}}
}

func TestCapabilityC7TruthTable(t *testing.T) {
	for bonding := TruthUnknown; bonding <= TruthTrue; bonding++ {
		for changes := TruthUnknown; changes <= TruthTrue; changes++ {
			for _, properties := range []uint16{PropertyRead, PropertyRead | PropertyIndicate} {
				s := completeCapabilitySnapshot()
				s.C7 = C7Evidence{bonding, changes}
				s.Characteristics[0].Properties = properties
				r, e := InterpretCapabilities(s, CapabilityOptions{})
				if e != nil {
					t.Fatal(e)
				}
				want := PrerequisiteSatisfied
				if bonding == TruthFalse || changes == TruthFalse {
					if properties != PropertyRead {
						want = PrerequisiteInconsistent
					}
				} else if bonding == TruthTrue && changes == TruthTrue {
					if properties != PropertyRead|PropertyIndicate {
						want = PrerequisiteInconsistent
					}
				} else {
					want = PrerequisiteIncomplete
				}
				if r.Operations[0].Prerequisite != want {
					t.Fatalf("bonding=%d lifetime=%d properties=%x got=%+v", bonding, changes, properties, r.Operations[0])
				}
			}
		}
	}
}

func TestCapabilityReadAndDuplicateEvidence(t *testing.T) {
	s := completeCapabilitySnapshot()
	s.C7 = C7Evidence{}
	s.Characteristics[0].ReadState = ReadFailed
	s.Characteristics[0].Reason = ReasonSecurityRequired
	s.Characteristics[0].Bytes = nil
	r, e := InterpretCapabilities(s, CapabilityOptions{})
	if e != nil {
		t.Fatal(e)
	}
	if len(r.Diagnostics) != 2 || r.Diagnostics[0].Code != DiagnosticInsufficientC7 || r.Diagnostics[1].Code != DiagnosticReadSecurityRequired {
		t.Fatal(r.Diagnostics)
	}
	if r.Operations[0].Reasons != CapabilityReasonC7Insufficient || r.Operations[2].Reasons != CapabilityReasonC7Insufficient|CapabilityReasonFeatureUnavailable {
		t.Fatal(r.Operations)
	}
	// Duplicate entries retain their individual property/read contradictions, but
	// no duplicate Feature is selected for decoding or a C.7 prerequisite decision.
	s.Characteristics = append(s.Characteristics, s.Characteristics[0])
	s.Characteristics[3].Properties = 0
	r, e = InterpretCapabilities(s, CapabilityOptions{})
	if e != nil {
		t.Fatal(e)
	}
	if r.Feature.Presence != PresenceAmbiguous || r.Feature.HasInputIndex || r.Feature.Decode != DecodeNotAttempted || r.Operations[0].Reasons != CapabilityReasonFeatureInvalid {
		t.Fatal(r.Feature, r.Operations[0])
	}
	if len(r.Diagnostics) != 6 || r.Diagnostics[0].Code != DiagnosticDuplicateCharacteristic {
		t.Fatal(r.Diagnostics)
	}
}

func TestCapabilityRangeOptionIsolation(t *testing.T) {
	s := completeCapabilitySnapshot()
	s.Characteristics[0].Bytes[4] = 0x1f
	for _, x := range []CharacteristicObservation{
		capObs(0x2ad4, 2, ReadSuccess, []byte{0, 0, 100, 0, 1, 0}),
		capObs(0x2ad5, 2, ReadSuccess, []byte{0, 0, 100, 0, 1, 0}),
		capObs(0x2ad6, 2, ReadSuccess, []byte{246, 255, 100, 0, 1, 0}),
		capObs(0x2ad7, 2, ReadSuccess, []byte{60, 200, 1}),
		capObs(0x2ad8, 2, ReadSuccess, []byte{0, 0, 100, 0, 1, 0}),
	} {
		s.Characteristics = append(s.Characteristics, x)
	}
	r, e := InterpretCapabilities(s, CapabilityOptions{Range: RangeOptions{Resistance: ResistanceSint16Tenths}})
	if e != nil {
		t.Fatal(e)
	}
	for _, rr := range r.Ranges {
		if rr.Decode != DecodeValid {
			t.Fatal(r.Ranges)
		}
	}
	for _, op := range r.Operations[:9] {
		if op.Prerequisite != PrerequisiteSatisfied {
			t.Fatal(op)
		}
	}
	if r.Ranges[ResistanceRange].Value.Minimum != -10 || r.Ranges[ResistanceRange].Value.ScaleDivisor != 10 {
		t.Fatal(r.Ranges[ResistanceRange])
	}
	defaultReport, e := InterpretCapabilities(s, CapabilityOptions{})
	if e != nil {
		t.Fatal(e)
	}
	if defaultReport.Ranges[ResistanceRange].Decode != DecodeMalformed || defaultReport.Operations[4].Prerequisite != PrerequisiteInconsistent || defaultReport.Operations[5].Prerequisite != PrerequisiteSatisfied {
		t.Fatal(defaultReport)
	}
	// Result storage is independent across calls and does not alias input.
	r.Observations[0].UUID[0] = 255
	r.Ranges[SpeedRange].Value.Minimum = 999
	if s.Characteristics[0].UUID[0] != 0 || defaultReport.Ranges[SpeedRange].Value.Minimum != 0 {
		t.Fatal("aliased report")
	}
}

func TestCapabilityArgumentValidation(t *testing.T) {
	changes := []func(*CapabilitySnapshot){
		func(s *CapabilitySnapshot) { s.Scope = 255 }, func(s *CapabilitySnapshot) { s.Discovery = 255 },
		func(s *CapabilitySnapshot) { s.C7.BondingSupported = 255 }, func(s *CapabilitySnapshot) { s.C7.FeatureMayChangeOverLifetime = 255 },
		func(s *CapabilitySnapshot) { s.Characteristics[0].ReadState = 255 }, func(s *CapabilitySnapshot) { s.Characteristics[0].Reason = 255 },
		func(s *CapabilitySnapshot) { s.Characteristics[0].ReadState = ReadNotAttempted },
		func(s *CapabilitySnapshot) { s.Characteristics[0].ReadState = ReadFailed },
	}
	for _, change := range changes {
		s := completeCapabilitySnapshot()
		change(&s)
		r, e := InterpretCapabilities(s, CapabilityOptions{})
		if e != ErrKind || !reflect.DeepEqual(r, CapabilityReport{}) {
			t.Fatal(r, e)
		}
	}
	// Empty successful reads are not API errors; unread/malformed/failed remain distinct.
	for state := ReadNotAttempted; state <= ReadFailed; state++ {
		s := completeCapabilitySnapshot()
		s.Characteristics[0].ReadState = state
		s.Characteristics[0].Bytes = nil
		r, e := InterpretCapabilities(s, CapabilityOptions{})
		if e != nil {
			t.Fatal(e)
		}
		want := map[ReadState]DecodeState{ReadNotAttempted: DecodeNotAttempted, ReadSuccess: DecodeMalformed, ReadFailed: DecodeFailed}[state]
		if r.Feature.Decode != want || r.Operations[0].Prerequisite != PrerequisiteSatisfied {
			t.Fatal(r.Feature, r.Operations[0])
		}
	}
}

func FuzzInterpretCapabilities(f *testing.F) {
	f.Add([]byte{0, 0, 0, 0, 0, 0, 0, 0}, uint16(2), uint8(1), uint8(0))
	f.Fuzz(func(t *testing.T, b []byte, properties uint16, state, reason uint8) {
		s := completeCapabilitySnapshot()
		s.Characteristics[0].Bytes = b
		s.Characteristics[0].Properties = properties
		s.Characteristics[0].ReadState = ReadState(state)
		s.Characteristics[0].Reason = ReadReason(reason)
		before := bytes.Clone(b)
		r, e := InterpretCapabilities(s, CapabilityOptions{})
		if !bytes.Equal(b, before) {
			t.Fatal("input mutated")
		}
		if e != nil {
			if e != ErrKind || !reflect.DeepEqual(r, CapabilityReport{}) {
				t.Fatal("invalid failure result")
			}
			return
		}
		again, e := InterpretCapabilities(s, CapabilityOptions{})
		if e != nil || !reflect.DeepEqual(r, again) {
			t.Fatal("nondeterministic")
		}
		if r.ObservationCount != len(s.Characteristics) || r.DiagnosticCount != len(r.Diagnostics) || r.Generation != s.Generation {
			t.Fatal("bad report accounting")
		}
	})
}

func TestInterpretCapabilitiesFullUUIDAndOwnership(t *testing.T) {
	b := []byte{0, 0, 0, 0, 0, 0, 0, 0}
	s := CapabilitySnapshot{Discovery: DiscoveryComplete, Scope: ScopePresent, Generation: 99,
		Characteristics: []CharacteristicObservation{capObs(0x2acc, 2, ReadSuccess, b)}}
	r, err := InterpretCapabilities(s, CapabilityOptions{})
	if err != nil {
		t.Fatal(err)
	}
	if r.Generation != 99 || r.Feature.Decode != DecodeValid || r.Feature.InputIndex != 0 {
		t.Fatalf("unexpected feature: %#v", r.Feature)
	}
	b[0] = 0xff
	if r.Feature.MachineRaw != 0 {
		t.Fatal("report retained caller byte ownership")
	}
	lookalike := capObs(0x2acc, 2, ReadSuccess, make([]byte, 8))
	lookalike.UUID[0] = 0x12
	r, err = InterpretCapabilities(CapabilitySnapshot{Discovery: DiscoveryComplete, Scope: ScopePresent, Characteristics: []CharacteristicObservation{lookalike}}, CapabilityOptions{})
	if err != nil || r.Observations[0].KnownKind != KindUnknown {
		t.Fatalf("truncated UUID recognized: %#v %v", r, err)
	}
}

func TestInterpretCapabilitiesC7AndValidation(t *testing.T) {
	s := CapabilitySnapshot{Discovery: DiscoveryComplete, Scope: ScopePresent, Characteristics: []CharacteristicObservation{
		capObs(0x2acc, 34, ReadSuccess, make([]byte, 8)), capObs(0x2ad9, 40, ReadNotAttempted, nil), capObs(0x2ada, 16, ReadNotAttempted, nil),
	}, C7: C7Evidence{BondingSupported: TruthUnknown, FeatureMayChangeOverLifetime: TruthUnknown}}
	r, e := InterpretCapabilities(s, CapabilityOptions{})
	if e != nil {
		t.Fatal(e)
	}
	if len(r.Diagnostics) != 1 || r.Diagnostics[0].Code != DiagnosticInsufficientC7 || r.Operations[0].Reasons&CapabilityReasonC7Insufficient == 0 {
		t.Fatalf("C7 not preserved: %#v %#v", r.Diagnostics, r.Operations[0])
	}
	s.Characteristics[0].Reason = ReasonGeneric
	if _, e = InterpretCapabilities(s, CapabilityOptions{}); e != ErrKind {
		t.Fatalf("invalid successful-read reason: %v", e)
	}
	s.Characteristics[0].Reason = ReasonNone
	s.Characteristics[0].Bytes = nil
	s.Characteristics[0].ReadState = ReadNotAttempted
	if _, e = InterpretCapabilities(s, CapabilityOptions{Range: RangeOptions{Resistance: 99}}); e != ErrKind {
		t.Fatalf("invalid option: %v", e)
	}
}
