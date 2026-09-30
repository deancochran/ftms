package ftms_test

import (
	"fmt"

	ftms "github.com/deancochran/ftms/packages/go"
)

func ExampleDecodeFeatures() {
	f, _ := ftms.DecodeFeatures([]byte{1, 0, 0, 0, 4, 0, 0, 0})
	fmt.Println(f.Machine(0), f.Target(2))
	// Output: true true
}

func ExampleDecodeMeasurement() {
	reading, err := ftms.DecodeMeasurement(ftms.IndoorBike,
		[]byte{0, 0, 0x10, 0x0e}, ftms.MeasurementOptions{})
	if err != nil {
		panic(err)
	}
	if reading.Diagnostics.Truncated {
		panic("incomplete measurement")
	}
	if raw, present := reading.Values[ftms.Speed]; present {
		fmt.Printf("%.1f km/h\n", float64(raw)/100)
	}
	// Output: 36.0 km/h
}

func ExampleEncodeControlRequest() {
	packet, err := ftms.EncodeControlRequest(
		ftms.ControlRequest{Opcode: 5, Operands: []int32{250}}, ftms.ControlOptions{})
	if err != nil {
		panic(err)
	}
	// Producing bytes does not authorize sending them to equipment.
	fmt.Printf("% x\n", packet)
	// Output: 05 fa 00
}

func ExampleInterpretCapabilities() {
	snapshot := ftms.CapabilitySnapshot{
		Scope: ftms.ScopePresent, Discovery: ftms.DiscoveryComplete, Generation: 7,
		C7: ftms.C7Evidence{BondingSupported: ftms.TruthFalse},
		Characteristics: []ftms.CharacteristicObservation{
			{UUID: ftms.UUID16(0x2acc), Properties: ftms.PropertyRead,
				ReadState: ftms.ReadSuccess, Bytes: make([]byte, 8)},
			{UUID: ftms.UUID16(0x2ad9), Properties: ftms.PropertyWrite | ftms.PropertyIndicate},
			{UUID: ftms.UUID16(0x2ada), Properties: ftms.PropertyNotify},
		},
	}
	report, err := ftms.InterpretCapabilities(snapshot, ftms.CapabilityOptions{})
	if err != nil {
		panic(err)
	}
	requestControl := report.Operations[0]
	fmt.Println(report.Generation, requestControl.Declaration == ftms.DeclarationSupported,
		requestControl.Prerequisite == ftms.PrerequisiteSatisfied)
	// These are static facts, not permission to issue a command.
	// Output: 7 true true
}
