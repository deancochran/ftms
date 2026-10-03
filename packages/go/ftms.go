// Package ftms provides transport-independent codecs for Bluetooth Fitness
// Machine Service 1.0. It deliberately has no Bluetooth or lifecycle APIs.
package ftms

import (
	"encoding/binary"
	"errors"
	"fmt"
	"unicode/utf8"
)

var (
	ErrLength = errors.New("ftms: invalid length")
	ErrKind   = errors.New("ftms: invalid kind")
	ErrRange  = errors.New("ftms: value out of range")
	// ErrUnsupported identifies an otherwise well-formed UUID for which this
	// convenience measurement projection has no defined meaning.
	ErrUnsupported = errors.New("ftms: unsupported measurement characteristic")
)

type Diagnostics struct {
	Truncated, TrailingBytes, ReservedFlags bool
	Issues                                  []string
}

func (d *Diagnostics) add(s string) {
	for _, x := range d.Issues {
		if x == s {
			return
		}
	}
	d.Issues = append(d.Issues, s)
}
func u16(b []byte, p int) uint16 { return binary.LittleEndian.Uint16(b[p:]) }
func i16(b []byte, p int) int16  { return int16(u16(b, p)) }
func u24(b []byte, p int) uint32 { return uint32(b[p]) | uint32(b[p+1])<<8 | uint32(b[p+2])<<16 }
func put16(v uint16) []byte      { return []byte{byte(v), byte(v >> 8)} }
func put24(v uint32) []byte      { return []byte{byte(v), byte(v >> 8), byte(v >> 16)} }

type Features struct{ MachineRaw, TargetRaw, MachineUnknown, TargetUnknown uint32 }

func DecodeFeatures(b []byte) (Features, error) {
	if len(b) != 8 {
		return Features{}, ErrLength
	}
	f := Features{MachineRaw: uint32(u16(b, 0)) | uint32(u16(b, 2))<<16, TargetRaw: uint32(u16(b, 4)) | uint32(u16(b, 6))<<16}
	f.MachineUnknown = f.MachineRaw &^ 0x1ffff
	f.TargetUnknown = f.TargetRaw &^ 0x1ffff
	return f, nil
}
func EncodeFeatures(f Features) []byte {
	b := make([]byte, 0, 8)
	for _, v := range []uint32{f.MachineRaw, f.TargetRaw} {
		b = append(b, put16(uint16(v))...)
		b = append(b, put16(uint16(v>>16))...)
	}
	return b
}
func (f Features) Machine(bit uint) bool { return bit < 32 && f.MachineRaw&(1<<bit) != 0 }
func (f Features) Target(bit uint) bool  { return bit < 32 && f.TargetRaw&(1<<bit) != 0 }

type RangeKind int

const (
	SpeedRange RangeKind = iota
	InclinationRange
	ResistanceRange
	HeartRateRange
	PowerRange
)

type ResistanceFormat uint8

const (
	ResistanceUint8Whole ResistanceFormat = iota
	ResistanceSint16Tenths
)

type RangeOptions struct{ Resistance ResistanceFormat }
type SupportedRange struct {
	Kind                        RangeKind
	Minimum, Maximum, Increment int32
	Format                      RangeOptions
}

func DecodeRange(k RangeKind, b []byte, o RangeOptions) (SupportedRange, error) {
	if k < SpeedRange || k > PowerRange || o.Resistance > ResistanceSint16Tenths || k != ResistanceRange && o.Resistance != ResistanceUint8Whole {
		return SupportedRange{}, ErrKind
	}
	signed := k == InclinationRange || k == PowerRange || (k == ResistanceRange && o.Resistance == ResistanceSint16Tenths)
	w := 2
	if k == HeartRateRange || (k == ResistanceRange && !signed) {
		w = 1
	}
	if len(b) != w*3 {
		return SupportedRange{}, ErrLength
	}
	get := func(p int) int32 {
		if w == 1 {
			return int32(b[p])
		}
		if signed {
			return int32(i16(b, p))
		}
		return int32(u16(b, p))
	}
	inc := func(p int) int32 {
		if w == 1 {
			return int32(b[p])
		}
		return int32(u16(b, p))
	}
	r := SupportedRange{k, get(0), get(w), inc(2 * w), o}
	if r.Increment <= 0 || r.Minimum > r.Maximum {
		return SupportedRange{}, ErrRange
	}
	return r, nil
}
func EncodeRange(r SupportedRange, o RangeOptions) ([]byte, error) {
	if r.Kind < SpeedRange || r.Kind > PowerRange || o.Resistance > ResistanceSint16Tenths || r.Kind != ResistanceRange && o.Resistance != ResistanceUint8Whole {
		return nil, ErrKind
	}
	if r.Format != o {
		return nil, ErrKind
	}
	signed := r.Kind == InclinationRange || r.Kind == PowerRange || (r.Kind == ResistanceRange && o.Resistance == ResistanceSint16Tenths)
	w := 2
	if r.Kind == HeartRateRange || (r.Kind == ResistanceRange && !signed) {
		w = 1
	}
	if r.Increment <= 0 || r.Minimum > r.Maximum {
		return nil, ErrRange
	}
	enc := func(v int32, endpoint bool) ([]byte, error) {
		if w == 1 {
			if v < 0 || v > 255 {
				return nil, ErrRange
			}
			return []byte{byte(v)}, nil
		}
		if endpoint && signed {
			if v < -32768 || v > 32767 {
				return nil, ErrRange
			}
			return put16(uint16(int16(v))), nil
		}
		if v < 0 || v > 65535 {
			return nil, ErrRange
		}
		return put16(uint16(v)), nil
	}
	a, e := enc(r.Minimum, true)
	if e != nil {
		return nil, e
	}
	b, e := enc(r.Maximum, true)
	if e != nil {
		return nil, e
	}
	c, e := enc(r.Increment, false)
	return append(append(a, b...), c...), e
}

type NormalizedRange struct {
	Minimum, Maximum, Increment float64
	Unit                        string
}

func NormalizeRange(r SupportedRange) NormalizedRange {
	scale := 1.0
	unit := "level"
	switch r.Kind {
	case SpeedRange:
		scale = 100
		unit = "km/h"
	case InclinationRange:
		scale = 10
		unit = "percent"
	case HeartRateRange:
		unit = "bpm"
	case PowerRange:
		unit = "watts"
	case ResistanceRange:
		if r.Format.Resistance == ResistanceSint16Tenths {
			scale = 10
		}
	}
	return NormalizedRange{float64(r.Minimum) / scale, float64(r.Maximum) / scale, float64(r.Increment) / scale, unit}
}

type RangeInspection struct {
	Selected                     ResistanceFormat
	ActualLength, ExpectedLength int
	Err                          error
	Value                        *SupportedRange
	Candidates                   []RangeCandidate
}
type RangeCandidate struct {
	Format         ResistanceFormat
	ExpectedLength int
	Err            error
	Value          *SupportedRange
}

// InspectRange reports the selected decode and bounded alternatives. A candidate
// is not evidence of the intended format, physical units, or control permission.
// The returned error is for invalid arguments; packet errors are in the report.
func InspectRange(k RangeKind, b []byte, o RangeOptions) (RangeInspection, error) {
	if k < SpeedRange || k > PowerRange || o.Resistance > ResistanceSint16Tenths || k != ResistanceRange && o.Resistance != ResistanceUint8Whole {
		return RangeInspection{}, ErrKind
	}
	choices := []ResistanceFormat{o.Resistance}
	if k == ResistanceRange {
		choices = []ResistanceFormat{ResistanceUint8Whole, ResistanceSint16Tenths}
	}
	out := RangeInspection{Selected: o.Resistance, ActualLength: len(b)}
	for _, x := range choices {
		r, e := DecodeRange(k, b, RangeOptions{x})
		c := RangeCandidate{x, 6, e, nil}
		if k == HeartRateRange || k == ResistanceRange && x == ResistanceUint8Whole {
			c.ExpectedLength = 3
		}
		if e == nil {
			c.Value = &r
		}
		out.Candidates = append(out.Candidates, c)
		if x == o.Resistance {
			out.Err = e
			out.ExpectedLength = c.ExpectedLength
			out.Value = c.Value
		}
	}
	return out, nil
}

type ControlRequest struct {
	Opcode   byte
	Operands []int32
}

// ControlResistanceFormat selects the Control Point resistance operand only.
// Its zero value is the corrected signed 16-bit tenths layout.
type ControlResistanceFormat uint8

const (
	ControlResistanceSigned16Tenths ControlResistanceFormat = iota
	ControlResistanceUint8Tenths
)

type ControlOptions struct{ Resistance ControlResistanceFormat }

var controlLengths = [21]int{1, 1, 3, 3, 3, 3, 2, 1, 2, 3, 3, 3, 4, 3, 5, 7, 11, 7, 3, 2, 3}
var operandCounts = [21]int{0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 2, 3, 5, 4, 1, 1, 1}

func DecodeControlRequest(b []byte, o ControlOptions) (ControlRequest, error) {
	if o.Resistance > ControlResistanceUint8Tenths {
		return ControlRequest{}, ErrKind
	}
	if len(b) == 0 {
		return ControlRequest{}, ErrLength
	}
	op := int(b[0])
	if op > 20 {
		return ControlRequest{}, ErrKind
	}
	n := controlLengths[op]
	if op == 4 && o.Resistance == ControlResistanceUint8Tenths {
		n = 2
	}
	if len(b) != n {
		return ControlRequest{}, ErrLength
	}
	r := ControlRequest{Opcode: b[0]}
	oneU := func() { r.Operands = []int32{int32(u16(b, 1))} }
	switch op {
	case 2, 9, 10, 11, 13, 18, 20:
		oneU()
	case 3, 5:
		r.Operands = []int32{int32(i16(b, 1))}
	case 4:
		if o.Resistance == ControlResistanceUint8Tenths {
			r.Operands = []int32{int32(b[1])}
		} else {
			r.Operands = []int32{int32(i16(b, 1))}
		}
	case 6, 8, 19:
		r.Operands = []int32{int32(b[1])}
	case 12:
		r.Operands = []int32{int32(u24(b, 1))}
	case 14, 15, 16:
		for p := 1; p < n; p += 2 {
			r.Operands = append(r.Operands, int32(u16(b, p)))
		}
	case 17:
		r.Operands = []int32{int32(i16(b, 1)), int32(i16(b, 3)), int32(b[5]), int32(b[6])}
	}
	if (op == 8 || op == 19) && (r.Operands[0] < 1 || r.Operands[0] > 2) {
		return ControlRequest{}, ErrRange
	}
	return r, nil
}
func EncodeControlRequest(r ControlRequest, o ControlOptions) ([]byte, error) {
	if o.Resistance > ControlResistanceUint8Tenths {
		return nil, ErrKind
	}
	op := int(r.Opcode)
	if op > 20 {
		return nil, ErrKind
	}
	if len(r.Operands) != operandCounts[op] {
		return nil, ErrLength
	}
	n := controlLengths[op]
	if op == 4 && o.Resistance == ControlResistanceUint8Tenths {
		n = 2
	}
	b := []byte{r.Opcode}
	u := func(x int32, max int32) error {
		if x < 0 || x > max {
			return ErrRange
		}
		if max == 255 {
			b = append(b, byte(x))
		} else if max == 0xffffff {
			b = append(b, put24(uint32(x))...)
		} else {
			b = append(b, put16(uint16(x))...)
		}
		return nil
	}
	s := func(x int32) error {
		if x < -32768 || x > 32767 {
			return ErrRange
		}
		b = append(b, put16(uint16(int16(x)))...)
		return nil
	}
	var e error
	switch op {
	case 2, 9, 10, 11, 13, 18, 20:
		e = u(r.Operands[0], 65535)
	case 3, 5:
		e = s(r.Operands[0])
	case 4:
		if o.Resistance == ControlResistanceUint8Tenths {
			e = u(r.Operands[0], 255)
		} else {
			e = s(r.Operands[0])
		}
	case 6:
		e = u(r.Operands[0], 255)
	case 8, 19:
		if r.Operands[0] != 1 && r.Operands[0] != 2 {
			return nil, ErrRange
		}
		e = u(r.Operands[0], 255)
	case 12:
		e = u(r.Operands[0], 0xffffff)
	case 14, 15, 16:
		for _, x := range r.Operands {
			if e = u(x, 65535); e != nil {
				break
			}
		}
	case 17:
		e = s(r.Operands[0])
		if e == nil {
			e = s(r.Operands[1])
		}
		if e == nil {
			e = u(r.Operands[2], 255)
		}
		if e == nil {
			e = u(r.Operands[3], 255)
		}
	}
	if e != nil {
		return nil, e
	}
	if len(b) != n {
		return nil, fmt.Errorf("%w: internal control length", ErrLength)
	}
	return b, nil
}

type ControlResponse struct {
	RequestOpcode, ResultCode                                        byte
	SpinDownLow, SpinDownHigh                                        uint16
	HasSpinDown, UnknownRequest, UnknownResult, UnexpectedParameters bool
}

func DecodeControlResponse(b []byte, allowTrailing bool) (ControlResponse, error) {
	if len(b) < 3 {
		return ControlResponse{}, ErrLength
	}
	if b[0] != 0x80 {
		return ControlResponse{}, ErrKind
	}
	spin := b[1] == 19 && b[2] == 1 && len(b) == 7
	if b[1] == 19 && b[2] == 1 && len(b) != 3 && !spin {
		return ControlResponse{}, ErrLength
	}
	if len(b) != 3 && !spin && !allowTrailing {
		return ControlResponse{}, ErrLength
	}
	r := ControlResponse{RequestOpcode: b[1], ResultCode: b[2], HasSpinDown: spin, UnknownRequest: b[1] > 20, UnknownResult: b[2] < 1 || b[2] > 5, UnexpectedParameters: len(b) != 3 && !spin}
	if spin {
		r.SpinDownLow = u16(b, 3)
		r.SpinDownHigh = u16(b, 5)
	}
	return r, nil
}
func EncodeControlResponse(r ControlResponse) ([]byte, error) {
	if !r.HasSpinDown && (r.SpinDownLow != 0 || r.SpinDownHigh != 0) {
		return nil, ErrRange
	}
	if r.UnknownResult || r.UnexpectedParameters || r.ResultCode < 1 || r.ResultCode > 5 || r.UnknownRequest != (r.RequestOpcode > 20) {
		return nil, ErrRange
	}
	if r.RequestOpcode > 20 && r.ResultCode != 2 {
		return nil, ErrRange
	}
	b := []byte{0x80, r.RequestOpcode, r.ResultCode}
	if r.HasSpinDown {
		if r.RequestOpcode != 19 || r.ResultCode != 1 {
			return nil, ErrRange
		}
		b = append(b, put16(r.SpinDownLow)...)
		b = append(b, put16(r.SpinDownHigh)...)
	}
	return b, nil
}

type MachineStatus struct {
	Opcode      byte
	Operands    []int32
	Diagnostics Diagnostics
}

func machineLen(op byte) int {
	switch op {
	case 1, 3, 4, 255:
		return 1
	case 2, 9, 20:
		return 2
	case 13:
		return 4
	case 15:
		return 5
	case 16, 18:
		return 7
	case 17:
		return 11
	case 5, 6, 7, 8, 10, 11, 12, 14, 19, 21:
		return 3
	}
	return 0
}
func machineControl(op byte) (byte, bool) {
	if op >= 5 && op <= 9 {
		return op - 3, true
	}
	if op >= 10 && op <= 19 {
		return op - 1, true
	}
	if op == 21 {
		return 20, true
	}
	return 0, false
}
func DecodeMachineStatus(b []byte, o ControlOptions) MachineStatus {
	if len(b) == 0 {
		return MachineStatus{Diagnostics: Diagnostics{Truncated: true, Issues: []string{"unknown_opcode", "truncated"}}}
	}
	n := machineLen(b[0])
	if n == 0 {
		return MachineStatus{Opcode: b[0], Diagnostics: Diagnostics{Issues: []string{"unknown_opcode"}}}
	}
	if len(b) < n {
		return MachineStatus{Opcode: b[0], Diagnostics: Diagnostics{Truncated: true, Issues: []string{"truncated"}}}
	}
	d := Diagnostics{}
	if len(b) > n {
		d.TrailingBytes = true
		d.add("trailing_bytes")
	}
	r := MachineStatus{Opcode: b[0], Diagnostics: d}
	if b[0] == 2 || b[0] == 20 {
		r.Operands = []int32{int32(b[1])}
		if (b[0] == 2 && (b[1] < 1 || b[1] > 2)) || (b[0] == 20 && (b[1] < 1 || b[1] > 4)) {
			r.Diagnostics.add("reserved_value")
		}
		return r
	}
	if b[0] == 7 {
		r.Operands = []int32{int32(i16(b, 1))}
		return r
	}
	if op, ok := machineControl(b[0]); ok {
		x, e := DecodeControlRequest(append([]byte{op}, b[1:n]...), o)
		if e != nil {
			r.Diagnostics.Truncated = true
			r.Diagnostics.add("truncated")
		} else {
			r.Operands = x.Operands
		}
	}
	return r
}
func EncodeMachineStatus(s MachineStatus, o ControlOptions) ([]byte, error) {
	n := machineLen(s.Opcode)
	if n == 0 || s.Diagnostics.Truncated || s.Diagnostics.TrailingBytes || s.Diagnostics.ReservedFlags || len(s.Diagnostics.Issues) != 0 {
		return nil, ErrKind
	}
	if s.Opcode == 2 || s.Opcode == 20 {
		if len(s.Operands) != 1 || s.Operands[0] < 1 || s.Operands[0] > map[byte]int32{2: 2, 20: 4}[s.Opcode] {
			return nil, ErrRange
		}
		return []byte{s.Opcode, byte(s.Operands[0])}, nil
	}
	if s.Opcode == 7 {
		if len(s.Operands) != 1 {
			return nil, ErrRange
		}
		b, e := EncodeControlRequest(ControlRequest{4, s.Operands}, ControlOptions{})
		if e != nil {
			return nil, e
		}
		return append([]byte{7}, b[1:]...), nil
	}
	if op, ok := machineControl(s.Opcode); ok {
		b, e := EncodeControlRequest(ControlRequest{op, s.Operands}, o)
		if e != nil {
			return nil, e
		}
		if len(b) != n {
			return nil, ErrLength
		}
		return append([]byte{s.Opcode}, b[1:]...), nil
	}
	if len(s.Operands) != 0 {
		return nil, ErrRange
	}
	return []byte{s.Opcode}, nil
}

type TrainingStatus struct {
	Flags, Code byte
	Text        string
	Diagnostics Diagnostics
}

func DecodeTrainingStatus(b []byte) TrainingStatus {
	if len(b) < 2 {
		r := TrainingStatus{Diagnostics: Diagnostics{Truncated: true, Issues: []string{"truncated"}}}
		if len(b) == 1 {
			r.Flags = b[0]
		}
		return r
	}
	r := TrainingStatus{Flags: b[0], Code: b[1]}
	if r.Flags&^byte(3) != 0 {
		r.Diagnostics.ReservedFlags = true
		r.Diagnostics.add("reserved_flags")
	}
	if r.Flags&2 != 0 && r.Flags&1 == 0 {
		r.Diagnostics.add("invalid_flags")
	}
	if r.Code > 15 {
		r.Diagnostics.add("reserved_value")
	}
	if r.Flags&1 != 0 {
		r.Text = string(b[2:]) // Preserve raw bytes even when UTF-8 is invalid.
		if !utf8.Valid(b[2:]) {
			r.Diagnostics.add("invalid_utf8")
		}
	} else if len(b) > 2 {
		r.Diagnostics.TrailingBytes = true
		r.Diagnostics.add("trailing_bytes")
	}
	return r
}
func EncodeTrainingStatus(s TrainingStatus) ([]byte, error) {
	if s.Diagnostics.Truncated || s.Diagnostics.TrailingBytes || s.Diagnostics.ReservedFlags || s.Flags&^byte(3) != 0 || s.Flags&2 != 0 && s.Flags&1 == 0 || s.Code > 15 || len(s.Diagnostics.Issues) > 0 || s.Flags&1 == 0 && s.Text != "" || !utf8.ValidString(s.Text) {
		return nil, ErrRange
	}
	b := []byte{s.Flags, s.Code}
	if s.Flags&1 != 0 {
		b = append(b, []byte(s.Text)...)
	}
	return b, nil
}
