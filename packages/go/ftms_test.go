package ftms

import (
	"bytes"
	"testing"
)

func TestWireRoundTrips(t *testing.T) {
	f := Features{MachineRaw: 1, TargetRaw: 0x10000}
	x, e := DecodeFeatures(EncodeFeatures(f))
	if e != nil || x.MachineRaw != f.MachineRaw || x.TargetRaw != f.TargetRaw {
		t.Fatal(x, e)
	}
	r := SupportedRange{SpeedRange, 1, 100, 1, RangeOptions{}}
	b, e := EncodeRange(r, RangeOptions{})
	if e != nil {
		t.Fatal(e)
	}
	if _, e = DecodeRange(SpeedRange, b, RangeOptions{}); e != nil {
		t.Fatal(e)
	}
	q := ControlRequest{2, []int32{250}}
	b, e = EncodeControlRequest(q, ControlOptions{})
	if e != nil {
		t.Fatal(e)
	}
	if x, e := DecodeControlRequest(b, ControlOptions{}); e != nil || x.Operands[0] != 250 {
		t.Fatal(x, e)
	}
}
func TestRejectsInvalidKindsAndUTF8(t *testing.T) {
	if _, e := DecodeRange(RangeKind(99), nil, RangeOptions{}); e != ErrKind {
		t.Fatalf("range kind: %v", e)
	}
	if _, e := DecodeMeasurement(MeasurementKind(99), nil, MeasurementOptions{}); e != ErrKind {
		t.Fatalf("measurement kind: %v", e)
	}
	s := DecodeTrainingStatus([]byte{1, 1, 0xff})
	if len(s.Diagnostics.Issues) == 0 || s.Diagnostics.Issues[0] != "invalid_utf8" {
		t.Fatalf("utf8 diagnostics: %#v", s.Diagnostics)
	}
}
func FuzzDecodeWire(f *testing.F) {
	f.Add([]byte{0, 0})
	f.Add([]byte{0x80, 19, 1, 100, 0, 200, 0})
	f.Add([]byte{0xff, 0xff, 0xff, 0xff, 0xff})
	f.Fuzz(func(t *testing.T, b []byte) {
		original := bytes.Clone(b)
		_, _ = DecodeFeatures(b)
		for k := SpeedRange; k <= PowerRange; k++ {
			for _, format := range []ResistanceFormat{ResistanceUint8Whole, ResistanceSint16Tenths} {
				_, _ = DecodeRange(k, b, RangeOptions{format})
				_, _ = InspectRange(k, b, RangeOptions{format})
			}
		}
		for _, format := range []ControlResistanceFormat{ControlResistanceSigned16Tenths, ControlResistanceUint8Tenths} {
			_, _ = DecodeControlRequest(b, ControlOptions{format})
			_ = DecodeMachineStatus(b, ControlOptions{format})
		}
		_, _ = DecodeControlResponse(b, true)
		_, _ = DecodeControlResponse(b, false)
		for k := Treadmill; k <= IndoorBike; k++ {
			for _, o := range []MeasurementOptions{{}, {Resistance: MeasurementResistanceSigned16Tenths}, {TreadmillPaceUint8: true}} {
				m, e := DecodeMeasurement(k, b, o)
				if e == nil && (m.BytesRead > len(b) || m.BytesRead < 2) {
					t.Fatal("invalid consumed offset")
				}
				if e == nil {
					_, _ = EncodeMeasurement(m, o)
				}
			}
		}
		_ = DecodeTrainingStatus(b)
		if !bytes.Equal(b, original) {
			t.Fatal("decoder mutated input")
		}
	})
}

func TestResistanceFormatsAreIndependent(t *testing.T) {
	b, err := EncodeControlRequest(ControlRequest{4, []int32{-10}}, ControlOptions{})
	if err != nil || !bytes.Equal(b, []byte{4, 246, 255}) {
		t.Fatal(b, err)
	}
	if _, err := DecodeControlRequest([]byte{4, 10}, ControlOptions{}); err != ErrLength {
		t.Fatal(err)
	}
	if _, err := DecodeControlRequest([]byte{4, 10}, ControlOptions{ControlResistanceUint8Tenths}); err != nil {
		t.Fatal(err)
	}
	if _, err := DecodeControlRequest([]byte{0}, ControlOptions{255}); err != ErrKind {
		t.Fatal(err)
	}
	if _, err := EncodeControlRequest(ControlRequest{Opcode: 0}, ControlOptions{255}); err != ErrKind {
		t.Fatal(err)
	}
	for _, k := range []MeasurementKind{-1, 6, 256} {
		if _, err := DecodeMeasurement(k, []byte{0, 0}, MeasurementOptions{}); err != ErrKind {
			t.Fatal(err)
		}
		if _, err := EncodeMeasurement(Measurement{Kind: k}, MeasurementOptions{}); err != ErrKind {
			t.Fatal(err)
		}
	}
	for _, k := range []RangeKind{-1, 5, 256} {
		if _, err := DecodeRange(k, []byte{0, 0, 1, 0, 1, 0}, RangeOptions{}); err != ErrKind {
			t.Fatal(err)
		}
		if _, err := InspectRange(k, nil, RangeOptions{}); err != ErrKind {
			t.Fatal(err)
		}
	}
}

func TestMeasurementRejectsInvalidRepresentation(t *testing.T) {
	m := Measurement{Kind: IndoorBike, Values: map[MeasurementField]int32{Speed: 100}}
	if _, err := EncodeMeasurement(m, MeasurementOptions{}); err != nil {
		t.Fatal(err)
	}
	m.Unavailable = map[MeasurementField]bool{Power: false}
	if _, err := EncodeMeasurement(m, MeasurementOptions{}); err == nil {
		t.Fatal("accepted false/unselected unavailable entry")
	}
	m.Unavailable = nil
	m.Values[Speed] = 65536
	if _, err := EncodeMeasurement(m, MeasurementOptions{}); err != ErrRange {
		t.Fatal(err)
	}
	m.Values[Speed] = 100
	m.Format.Resistance = MeasurementResistanceSigned16Tenths
	if _, err := EncodeMeasurement(m, MeasurementOptions{}); err != ErrKind {
		t.Fatal(err)
	}
}

func TestTrainingRetainsMalformedEvidence(t *testing.T) {
	s := DecodeTrainingStatus([]byte{1, 1, 0xc3})
	if s.Text != string([]byte{0xc3}) {
		t.Fatal("lost malformed text")
	}
	if _, err := EncodeTrainingStatus(s); err != ErrRange {
		t.Fatal(err)
	}
	if _, err := EncodeTrainingStatus(DecodeTrainingStatus(nil)); err != ErrRange {
		t.Fatal(err)
	}
	if _, err := EncodeMachineStatus(DecodeMachineStatus([]byte{2, 3}, ControlOptions{}), ControlOptions{}); err != ErrKind {
		t.Fatal(err)
	}
}

func TestCanonicalResponseAndStatusValidation(t *testing.T) {
	for _, opcode := range []byte{2, 19} {
		for _, speeds := range [][2]uint16{{1, 0}, {0, 1}, {65535, 65535}} {
			r := ControlResponse{RequestOpcode: opcode, ResultCode: 1, SpinDownLow: speeds[0], SpinDownHigh: speeds[1]}
			if b, err := EncodeControlResponse(r); err != ErrRange || b != nil {
				t.Fatal("discarded unused speeds", b, err)
			}
		}
		if _, err := EncodeControlResponse(ControlResponse{RequestOpcode: opcode, ResultCode: 1}); err != nil {
			t.Fatal(err)
		}
	}
	if _, err := EncodeMachineStatus(MachineStatus{Opcode: 1, Diagnostics: Diagnostics{ReservedFlags: true}}, ControlOptions{}); err != ErrKind {
		t.Fatal(err)
	}
}
