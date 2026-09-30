package ftms

type MeasurementKind int

const (
	Treadmill MeasurementKind = iota
	CrossTrainer
	StepClimber
	StairClimber
	Rower
	IndoorBike
)

type MeasurementField uint8

const (
	Speed MeasurementField = iota
	AverageSpeed
	Distance
	Inclination
	RampAngle
	PositiveElevation
	NegativeElevation
	InstantaneousPace
	AveragePace
	TotalEnergy
	EnergyPerHour
	EnergyPerMinute
	HeartRate
	MetabolicEquivalent
	ElapsedTime
	RemainingTime
	ForceOnBelt
	Power
	StepRate
	AverageStepRate
	StrideCount
	Resistance
	AveragePower
	FloorCount
	StepCount
	StrokeRate
	StrokeCount
	AverageStrokeRate
	Cadence
	AverageCadence
)

// MeasurementResistanceFormat is independent of range and Control Point formats.
// Its zero value preserves the raw corpus's legacy unsigned byte layout.
type MeasurementResistanceFormat uint8

const (
	MeasurementResistanceUint8 MeasurementResistanceFormat = iota
	MeasurementResistanceSigned16Tenths
)

type MeasurementOptions struct {
	Resistance         MeasurementResistanceFormat
	TreadmillPaceUint8 bool
}
type Measurement struct {
	Kind        MeasurementKind
	Flags       uint32
	Values      map[MeasurementField]int32
	Unavailable map[MeasurementField]bool
	Diagnostics Diagnostics
	BytesRead   int
	Format      MeasurementOptions
}
type field struct {
	bit, width          int
	id                  MeasurementField
	signed, unavailable bool
}

func fields(k MeasurementKind, o MeasurementOptions) (int, uint32, []field) {
	e := func(bit, w int, id MeasurementField, s, u bool) field { return field{bit, w, id, s, u} }
	energy := func(bit int) []field {
		return []field{e(bit, 2, TotalEnergy, false, true), e(bit, 2, EnergyPerHour, false, true), e(bit, 1, EnergyPerMinute, false, true)}
	}
	switch k {
	case Treadmill:
		f := []field{e(0, 2, Speed, false, false), e(1, 2, AverageSpeed, false, false), e(2, 3, Distance, false, false), e(3, 2, Inclination, true, true), e(3, 2, RampAngle, true, true), e(4, 2, PositiveElevation, false, false), e(4, 2, NegativeElevation, false, false)}
		w := 2
		if o.TreadmillPaceUint8 {
			w = 1
		}
		f = append(f, e(5, w, InstantaneousPace, false, false), e(6, w, AveragePace, false, false))
		f = append(f, energy(7)...)
		f = append(f, e(8, 1, HeartRate, false, false), e(9, 1, MetabolicEquivalent, false, false), e(10, 2, ElapsedTime, false, false), e(11, 2, RemainingTime, false, false), e(12, 2, ForceOnBelt, true, true), e(12, 2, Power, true, true))
		return 2, 0x1fff, f
	case CrossTrainer:
		f := []field{e(0, 2, Speed, false, false), e(1, 2, AverageSpeed, false, false), e(2, 3, Distance, false, false), e(3, 2, StepRate, false, true), e(3, 2, AverageStepRate, false, true), e(4, 2, StrideCount, false, false), e(5, 2, PositiveElevation, false, false), e(5, 2, NegativeElevation, false, false), e(6, 2, Inclination, true, true), e(6, 2, RampAngle, true, true)}
		w := 1
		s := false
		if o.Resistance == MeasurementResistanceSigned16Tenths {
			w = 2
			s = true
		}
		f = append(f, e(7, w, Resistance, s, false), e(8, 2, Power, true, false), e(9, 2, AveragePower, true, false))
		f = append(f, energy(10)...)
		f = append(f, e(11, 1, HeartRate, false, false), e(12, 1, MetabolicEquivalent, false, false), e(13, 2, ElapsedTime, false, false), e(14, 2, RemainingTime, false, false))
		return 3, 0xffff, f
	case StepClimber:
		return 2, 0x1ff, append([]field{e(0, 2, FloorCount, false, false), e(0, 2, StepCount, false, false), e(1, 2, StepRate, false, false), e(2, 2, AverageStepRate, false, false), e(3, 2, PositiveElevation, false, false)}, append(energy(4), e(5, 1, HeartRate, false, false), e(6, 1, MetabolicEquivalent, false, false), e(7, 2, ElapsedTime, false, false), e(8, 2, RemainingTime, false, false))...)
	case StairClimber:
		return 2, 0x3ff, []field{e(0, 2, FloorCount, false, false), e(1, 2, StepRate, false, false), e(2, 2, AverageStepRate, false, false), e(3, 2, PositiveElevation, false, false), e(4, 2, StrideCount, false, false), e(5, 2, TotalEnergy, false, true), e(5, 2, EnergyPerHour, false, true), e(5, 1, EnergyPerMinute, false, true), e(6, 1, HeartRate, false, false), e(7, 1, MetabolicEquivalent, false, false), e(8, 2, ElapsedTime, false, false), e(9, 2, RemainingTime, false, false)}
	case Rower, IndoorBike: /* shared tail differs only first fields */
	}
	var f []field
	if k == Rower {
		f = []field{e(0, 1, StrokeRate, false, false), e(0, 2, StrokeCount, false, false), e(1, 1, AverageStrokeRate, false, false), e(2, 3, Distance, false, false), e(3, 2, InstantaneousPace, false, false), e(4, 2, AveragePace, false, false), e(5, 2, Power, true, false), e(6, 2, AveragePower, true, false)}
	} else {
		f = []field{e(0, 2, Speed, false, false), e(1, 2, AverageSpeed, false, false), e(2, 2, Cadence, false, false), e(3, 2, AverageCadence, false, false), e(4, 3, Distance, false, false)}
	}
	w := 1
	s := false
	if o.Resistance == MeasurementResistanceSigned16Tenths {
		w = 2
		s = true
	}
	bit := 7
	if k == IndoorBike {
		bit = 5
	}
	f = append(f, e(bit, w, Resistance, s, false))
	if k == IndoorBike {
		f = append(f, e(6, 2, Power, true, false), e(7, 2, AveragePower, true, false))
	}
	f = append(f, energy(8)...)
	f = append(f, e(9, 1, HeartRate, false, false), e(10, 1, MetabolicEquivalent, false, false), e(11, 2, ElapsedTime, false, false), e(12, 2, RemainingTime, false, false))
	return 2, 0x1fff, f
}
func DecodeMeasurement(k MeasurementKind, b []byte, o MeasurementOptions) (Measurement, error) {
	if k < Treadmill || k > IndoorBike || o.Resistance > MeasurementResistanceSigned16Tenths {
		return Measurement{}, ErrKind
	}
	n, valid, fs := fields(k, o)
	if len(b) < n {
		return Measurement{}, ErrLength
	}
	flags := uint32(0)
	for i := 0; i < n; i++ {
		flags |= uint32(b[i]) << uint(i*8)
	}
	m := Measurement{Kind: k, Flags: flags, Values: map[MeasurementField]int32{}, Unavailable: map[MeasurementField]bool{}, BytesRead: n, Format: o}
	if flags&^valid != 0 {
		m.Diagnostics.ReservedFlags = true
		m.Diagnostics.add("reserved_flags")
	}
	p := n
	for _, f := range fs {
		present := flags&(1<<uint(f.bit)) != 0
		if f.bit == 0 {
			present = flags&1 == 0
		}
		if !present {
			continue
		}
		if p+f.width > len(b) {
			m.BytesRead = p
			m.Diagnostics.Truncated = true
			m.Diagnostics.add("truncated")
			return m, nil
		}
		raw := uint32(b[p])
		if f.width == 2 {
			raw = uint32(u16(b, p))
		} else if f.width == 3 {
			raw = u24(b, p)
		}
		p += f.width
		sent := uint32(0xffff)
		if f.signed {
			sent = 0x7fff
		} else if f.width == 1 {
			sent = 0xff
		}
		if f.unavailable && raw == sent {
			m.Unavailable[f.id] = true
			m.Diagnostics.add("unavailable")
		} else if f.signed {
			m.Values[f.id] = int32(int16(raw))
		} else {
			m.Values[f.id] = int32(raw)
		}
	}
	m.BytesRead = p
	if p < len(b) {
		m.Diagnostics.TrailingBytes = true
		m.Diagnostics.add("trailing_bytes")
	}
	return m, nil
}

// EncodeMeasurement serializes a complete measurement. Its selected format must
// match the provenance retained by DecodeMeasurement; formats are never inferred.
func EncodeMeasurement(m Measurement, o MeasurementOptions) ([]byte, error) {
	if m.Kind < Treadmill || m.Kind > IndoorBike || o.Resistance > MeasurementResistanceSigned16Tenths {
		return nil, ErrKind
	}
	if m.Format != o {
		return nil, ErrKind
	}
	n, valid, fs := fields(m.Kind, o)
	if m.Flags&^valid != 0 {
		return nil, ErrRange
	}
	b := make([]byte, n)
	for i := 0; i < n; i++ {
		b[i] = byte(m.Flags >> uint(8*i))
	}
	selected := map[MeasurementField]bool{}
	for _, f := range fs {
		p := m.Flags&(1<<uint(f.bit)) != 0
		if f.bit == 0 {
			p = m.Flags&1 == 0
		}
		if p {
			selected[f.id] = true
		}
	}
	if len(selected) != len(m.Values)+len(m.Unavailable) {
		return nil, ErrRange
	}
	for id := range m.Values {
		if !selected[id] || m.Unavailable[id] {
			return nil, ErrRange
		}
	}
	for id := range m.Unavailable {
		if !selected[id] || !m.Unavailable[id] {
			return nil, ErrRange
		}
	}
	for _, f := range fs {
		p := m.Flags&(1<<uint(f.bit)) != 0
		if f.bit == 0 {
			p = m.Flags&1 == 0
		}
		if !p {
			continue
		}
		v, ok := m.Values[f.id]
		if m.Unavailable[f.id] {
			if !f.unavailable {
				return nil, ErrRange
			}
			if f.width == 1 {
				b = append(b, 0xff)
			} else if f.signed {
				b = append(b, put16(0x7fff)...)
			} else {
				b = append(b, put16(0xffff)...)
			}
			continue
		}
		if !ok {
			return nil, ErrRange
		}
		if f.signed {
			if v < -32768 || v > 32767 || f.unavailable && v == 32767 {
				return nil, ErrRange
			}
			b = append(b, put16(uint16(int16(v)))...)
		} else {
			max := int32(255)
			if f.width == 2 {
				max = 65535
			}
			if f.width == 3 {
				max = 0xffffff
			}
			if v < 0 || v > max || f.unavailable && v == max {
				return nil, ErrRange
			}
			if f.width == 1 {
				b = append(b, byte(v))
			} else if f.width == 2 {
				b = append(b, put16(uint16(v))...)
			} else {
				b = append(b, put24(uint32(v))...)
			}
		}
	}
	return b, nil
}
