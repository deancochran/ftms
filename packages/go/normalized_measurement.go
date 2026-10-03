package ftms

// NormalizedMeasurement is the physical-unit projection of one complete or
// diagnostic measurement notification. Nil means the field was not selected,
// was unavailable, or was not completely present; Raw distinguishes those
// states without making masks or wire scaling ordinary adopter work.
// Treadmill legacy uint8 pace deliberately remains nil because its physical
// unit is not known by this package.
type NormalizedMeasurement struct {
	Raw    Measurement
	format MeasurementOptions
	// MovementDirection is set only for Cross Trainer Data. Other measurement
	// families do not encode a direction and leave it nil.
	MovementDirection                                                               *MovementDirection
	SpeedMPS, AverageSpeedMPS, DistanceMeters                                       *float64
	InclinationPercent, RampAngleDegrees                                            *float64
	PositiveElevationGainMeters, NegativeElevationGainMeters                        *float64
	InstantaneousPaceSecondsPer500M, AveragePaceSecondsPer500M                      *float64
	EnergyKcal, EnergyPerHourKcal, EnergyPerMinuteKcal, HeartRateBPM                *float64
	MetabolicEquivalent, ElapsedTimeSeconds, RemainingTimeSeconds                   *float64
	ForceOnBeltNewtons, PowerWatts, StepRateSPM, AverageStepRateSPM                 *float64
	StrideCount, ResistanceLevel, AveragePowerWatts, FloorCount, StepCount          *float64
	StrokeRateSPM, StrokeCount, AverageStrokeRateSPM, CadenceRPM, AverageCadenceRPM *float64
}

// Format returns the layout selection captured when these physical values were
// decoded. Changing the returned copy or Raw does not rewrite that provenance.
func (measurement NormalizedMeasurement) Format() MeasurementOptions { return measurement.format }

// MovementDirection is Cross Trainer Data's direction flag in named form.
type MovementDirection uint8

const (
	MovementForward MovementDirection = iota
	MovementBackward
)

// DecodeNormalizedMeasurement is the single UUID-selected measurement entry
// point. UUID is the native 128-bit display/network-order representation used
// by this package; only exact Bluetooth-base measurement UUIDs are accepted.
// It retains the selected wire format and raw diagnostic evidence in the result.
func DecodeNormalizedMeasurement(uuid UUID, bytes []byte, options MeasurementOptions) (NormalizedMeasurement, error) {
	k, ok := measurementKindForUUID(uuid)
	if !ok {
		return NormalizedMeasurement{}, ErrUnsupported
	}
	raw, err := DecodeMeasurement(k, bytes, options)
	if err != nil {
		return NormalizedMeasurement{}, err
	}
	out := NormalizedMeasurement{Raw: raw, format: options}
	value := func(id MeasurementField, divisor float64) *float64 {
		v, ok := raw.Values[id]
		if !ok || raw.Unavailable[id] {
			return nil
		}
		x := float64(v) / divisor
		return &x
	}
	out.SpeedMPS = value(Speed, 360)
	out.AverageSpeedMPS = value(AverageSpeed, 360)
	out.DistanceMeters = value(Distance, 1)
	out.InclinationPercent = value(Inclination, 10)
	out.RampAngleDegrees = value(RampAngle, 10)
	elevation := 1.0
	if k == Treadmill {
		elevation = 10
	}
	out.PositiveElevationGainMeters = value(PositiveElevation, elevation)
	out.NegativeElevationGainMeters = value(NegativeElevation, elevation)
	if k == CrossTrainer {
		direction := MovementForward
		if raw.Flags&0x8000 != 0 {
			direction = MovementBackward
		}
		out.MovementDirection = &direction
	}
	if !(k == Treadmill && options.TreadmillPaceUint8) {
		out.InstantaneousPaceSecondsPer500M = value(InstantaneousPace, 1)
		out.AveragePaceSecondsPer500M = value(AveragePace, 1)
	}
	out.EnergyKcal = value(TotalEnergy, 1)
	out.EnergyPerHourKcal = value(EnergyPerHour, 1)
	out.EnergyPerMinuteKcal = value(EnergyPerMinute, 1)
	out.HeartRateBPM = value(HeartRate, 1)
	out.MetabolicEquivalent = value(MetabolicEquivalent, 10)
	out.ElapsedTimeSeconds = value(ElapsedTime, 1)
	out.RemainingTimeSeconds = value(RemainingTime, 1)
	out.ForceOnBeltNewtons = value(ForceOnBelt, 1)
	out.PowerWatts = value(Power, 1)
	out.StepRateSPM = value(StepRate, 1)
	out.AverageStepRateSPM = value(AverageStepRate, 1)
	if k == CrossTrainer {
		out.StrideCount = value(StrideCount, 10)
	} else {
		out.StrideCount = value(StrideCount, 1)
	}
	out.ResistanceLevel = value(Resistance, 1)
	if options.Resistance == MeasurementResistanceSigned16Tenths {
		out.ResistanceLevel = value(Resistance, 10)
	}
	out.AveragePowerWatts = value(AveragePower, 1)
	out.FloorCount = value(FloorCount, 1)
	out.StepCount = value(StepCount, 1)
	out.StrokeRateSPM = value(StrokeRate, 2)
	out.StrokeCount = value(StrokeCount, 1)
	out.AverageStrokeRateSPM = value(AverageStrokeRate, 2)
	out.CadenceRPM = value(Cadence, 2)
	out.AverageCadenceRPM = value(AverageCadence, 2)
	return out, nil
}

func measurementKindForUUID(uuid UUID) (MeasurementKind, bool) {
	switch kindOf(uuid) {
	case KindTreadmillData:
		return Treadmill, true
	case KindCrossTrainerData:
		return CrossTrainer, true
	case KindStepClimberData:
		return StepClimber, true
	case KindStairClimberData:
		return StairClimber, true
	case KindRowerData:
		return Rower, true
	case KindIndoorBikeData:
		return IndoorBike, true
	default:
		return 0, false
	}
}
