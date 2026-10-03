package ftms

import "testing"

func TestDecodeNormalizedMeasurementAllFamiliesAndDiagnostics(t *testing.T) {
	uuids := []UUID{UUID16(0x2acd), UUID16(0x2ace), UUID16(0x2acf), UUID16(0x2ad0), UUID16(0x2ad1), UUID16(0x2ad2)}
	packets := [][]byte{{0, 0, 0x10, 0x0e}, {0, 0, 0, 0x10, 0x0e}, {0, 0, 1, 0, 2, 0}, {0, 0, 1, 0}, {0, 0, 7, 1, 0, 2, 0}, {0, 0, 0x10, 0x0e}}
	for i, uuid := range uuids {
		got, err := DecodeNormalizedMeasurement(uuid, packets[i], MeasurementOptions{})
		if err != nil || got.Raw.Kind != MeasurementKind(i) {
			t.Fatalf("family %d: %#v %v", i, got, err)
		}
		if got.Raw.Diagnostics.Truncated || got.Raw.BytesRead == 0 {
			t.Fatalf("family %d lost raw diagnostics", i)
		}
		truncated, err := DecodeNormalizedMeasurement(uuid, packets[i][:map[bool]int{true: 3, false: 2}[i == 1]], MeasurementOptions{})
		if err != nil || !truncated.Raw.Diagnostics.Truncated {
			t.Fatalf("family %d truncated: %#v %v", i, truncated.Raw.Diagnostics, err)
		}
	}
	reading, err := DecodeNormalizedMeasurement(UUID16(0x2acd), []byte{8, 0, 0, 0, 0xff, 0x7f, 0xff, 0x7f}, MeasurementOptions{})
	if err != nil || reading.InclinationPercent != nil || !reading.Raw.Unavailable[Inclination] {
		t.Fatalf("unavailable: %#v %v", reading, err)
	}
	reserved, err := DecodeNormalizedMeasurement(UUID16(0x2acd), []byte{0, 0x20, 0, 0}, MeasurementOptions{})
	if err != nil || !reserved.Raw.Diagnostics.ReservedFlags {
		t.Fatalf("reserved: %#v %v", reserved, err)
	}
}

func TestDecodeNormalizedMeasurementFormatsAndUUIDs(t *testing.T) {
	unsigned, err := DecodeNormalizedMeasurement(UUID16(0x2ace), []byte{0x80, 0, 0, 0, 0, 9}, MeasurementOptions{})
	if err != nil || unsigned.ResistanceLevel == nil || *unsigned.ResistanceLevel != 9 {
		t.Fatalf("unsigned resistance: %#v %v", unsigned, err)
	}
	cross, err := DecodeNormalizedMeasurement(UUID16(0x2ace), []byte{0x80, 0, 0, 0, 0, 0xfb, 0xff}, MeasurementOptions{Resistance: MeasurementResistanceSigned16Tenths})
	if err != nil || cross.ResistanceLevel == nil || *cross.ResistanceLevel != -0.5 || cross.Format().Resistance != MeasurementResistanceSigned16Tenths {
		t.Fatalf("signed resistance: %#v %v", cross, err)
	}
	legacy, err := DecodeNormalizedMeasurement(UUID16(0x2acd), []byte{0x20, 0, 0, 0, 12}, MeasurementOptions{TreadmillPaceUint8: true})
	if err != nil || legacy.InstantaneousPaceSecondsPer500M != nil || legacy.Raw.Values[InstantaneousPace] != 12 {
		t.Fatalf("legacy pace: %#v %v", legacy, err)
	}
	if _, err := DecodeNormalizedMeasurement(UUID{0x12}, []byte{0, 0}, MeasurementOptions{}); err != ErrUnsupported {
		t.Fatalf("vendor UUID: %v", err)
	}
	if _, err := DecodeNormalizedMeasurement(UUID16(0x2ad3), []byte{0, 0}, MeasurementOptions{}); err != ErrUnsupported {
		t.Fatalf("nonmeasurement UUID: %v", err)
	}
}

func TestDecodeNormalizedMeasurementAllFieldPhysicalGoldens(t *testing.T) {
	uuids := []UUID{UUID16(0x2acd), UUID16(0x2ace), UUID16(0x2acf), UUID16(0x2ad0), UUID16(0x2ad1), UUID16(0x2ad2)}
	for kind, uuid := range uuids {
		o := MeasurementOptions{}
		_, valid, fs := fields(MeasurementKind(kind), o)
		flags := valid &^ 1 // Bit zero selects the mandatory first field when clear.
		values := map[MeasurementField]int32{}
		present := map[MeasurementField]bool{}
		for _, f := range fs {
			values[f.id] = int32(100 + f.id)
			present[f.id] = true
		}
		m := Measurement{Kind: MeasurementKind(kind), Flags: flags, Values: values, Unavailable: map[MeasurementField]bool{}, Format: o}
		bytes, err := EncodeMeasurement(m, o)
		if err != nil {
			t.Fatalf("golden %d encode: %v", kind, err)
		}
		got, err := DecodeNormalizedMeasurement(uuid, bytes, o)
		if err != nil {
			t.Fatalf("golden %d decode: %v", kind, err)
		}
		want := func(id MeasurementField, divisor float64) *float64 {
			if !present[id] {
				return nil
			}
			v := float64(values[id]) / divisor
			return &v
		}
		check := func(name string, actual, expected *float64) {
			if actual == nil || expected == nil {
				if actual != expected {
					t.Errorf("kind %d %s: got %v want %v", kind, name, actual, expected)
				}
				return
			}
			if *actual != *expected {
				t.Errorf("kind %d %s: got %v want %v", kind, name, *actual, *expected)
			}
		}
		check("speed", got.SpeedMPS, want(Speed, 360))
		check("averageSpeed", got.AverageSpeedMPS, want(AverageSpeed, 360))
		check("distance", got.DistanceMeters, want(Distance, 1))
		check("inclination", got.InclinationPercent, want(Inclination, 10))
		check("ramp", got.RampAngleDegrees, want(RampAngle, 10))
		elevation := 1.0
		if kind == int(Treadmill) {
			elevation = 10
		}
		check("positiveElevation", got.PositiveElevationGainMeters, want(PositiveElevation, elevation))
		check("negativeElevation", got.NegativeElevationGainMeters, want(NegativeElevation, elevation))
		check("instantaneousPace", got.InstantaneousPaceSecondsPer500M, want(InstantaneousPace, 1))
		check("averagePace", got.AveragePaceSecondsPer500M, want(AveragePace, 1))
		check("energy", got.EnergyKcal, want(TotalEnergy, 1))
		check("energyPerHour", got.EnergyPerHourKcal, want(EnergyPerHour, 1))
		check("energyPerMinute", got.EnergyPerMinuteKcal, want(EnergyPerMinute, 1))
		check("heartRate", got.HeartRateBPM, want(HeartRate, 1))
		check("met", got.MetabolicEquivalent, want(MetabolicEquivalent, 10))
		check("elapsed", got.ElapsedTimeSeconds, want(ElapsedTime, 1))
		check("remaining", got.RemainingTimeSeconds, want(RemainingTime, 1))
		check("force", got.ForceOnBeltNewtons, want(ForceOnBelt, 1))
		check("power", got.PowerWatts, want(Power, 1))
		check("stepRate", got.StepRateSPM, want(StepRate, 1))
		check("averageStepRate", got.AverageStepRateSPM, want(AverageStepRate, 1))
		stride := 1.0
		if kind == int(CrossTrainer) {
			stride = 10
		}
		check("stride", got.StrideCount, want(StrideCount, stride))
		check("resistance", got.ResistanceLevel, want(Resistance, 1))
		check("averagePower", got.AveragePowerWatts, want(AveragePower, 1))
		check("floor", got.FloorCount, want(FloorCount, 1))
		check("stepCount", got.StepCount, want(StepCount, 1))
		check("strokeRate", got.StrokeRateSPM, want(StrokeRate, 2))
		check("strokeCount", got.StrokeCount, want(StrokeCount, 1))
		check("averageStrokeRate", got.AverageStrokeRateSPM, want(AverageStrokeRate, 2))
		check("cadence", got.CadenceRPM, want(Cadence, 2))
		check("averageCadence", got.AverageCadenceRPM, want(AverageCadence, 2))
		if kind == int(CrossTrainer) {
			if got.MovementDirection == nil || *got.MovementDirection != MovementBackward {
				t.Errorf("kind %d direction: %v", kind, got.MovementDirection)
			}
		} else if got.MovementDirection != nil {
			t.Errorf("kind %d unexpected direction", kind)
		}
	}
}
