//go:build conformance

package ftms

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"os"
	"reflect"
	"testing"
)

// The oracle uses the canonical test-only layout declaration, never fields().
type matrixLayout struct {
	Kind                                  MeasurementKind
	FlagBytes, OptionalGroups, FullLength int
	Fields                                [][5]int
}

func TestMeasurementMatrix(t *testing.T) {
	path := "../../shared/conformance/measurement-matrix/v1/"
	b, err := os.ReadFile(path + "layouts.json")
	if err != nil {
		t.Fatal(err)
	}
	contract, err := os.ReadFile(path + "README.md")
	if err != nil {
		t.Fatal(err)
	}
	var doc struct {
		Contract string
		Layouts  []matrixLayout
	}
	if err = json.Unmarshal(b, &doc); err != nil {
		t.Fatal(err)
	}
	if doc.Contract != "ftms-measurement-matrix-v1" || len(doc.Layouts) != 6 {
		t.Fatal("unexpected matrix identity")
	}
	cases, sentinels, rfus, prefixes := 0, 0, 0, 0
	for _, base := range doc.Layouts {
		options := []MeasurementOptions{{}}
		switch base.Kind {
		case Treadmill:
			options = append(options, MeasurementOptions{TreadmillPaceUint8: true})
		case CrossTrainer, Rower, IndoorBike:
			options = append(options, MeasurementOptions{Resistance: MeasurementResistanceSigned16Tenths})
		}
		for _, o := range options {
			layout := base
			layout.Fields = append([][5]int{}, base.Fields...)
			for i, f := range layout.Fields {
				if o.TreadmillPaceUint8 && (f[2] == int(InstantaneousPace) || f[2] == int(AveragePace)) {
					layout.Fields[i][1] = 1
				}
				if o.Resistance == MeasurementResistanceSigned16Tenths && f[2] == int(Resistance) {
					layout.Fields[i][1] = 2
					layout.Fields[i][3] = 1
				}
			}
			backwards := 1
			if base.Kind == CrossTrainer {
				backwards = 2
			}
			for subset := 0; subset < 1<<base.OptionalGroups; subset++ {
				for more := 0; more < 2; more++ {
					for backward := 0; backward < backwards; backward++ {
						flags := uint32(subset<<1 | more | backward<<15)
						want, raw := matrixPacket(layout, o, flags, -1)
						checkMatrix(t, want, raw, true)
						cases++
					}
				}
			}
			fullFlags := uint32(((1 << base.OptionalGroups) - 1) << 1)
			full, raw := matrixPacket(layout, o, fullFlags, -1)
			for _, f := range layout.Fields {
				if f[4] != 0 {
					want, raw := matrixPacket(layout, o, fullFlags, f[2])
					checkMatrix(t, want, raw, true)
					sentinels++
				}
			}
			valid := uint32((1 << (base.OptionalGroups + 1)) - 1)
			if base.Kind == CrossTrainer {
				valid |= 1 << 15
			}
			for bit := 0; bit < 8*base.FlagBytes; bit++ {
				if valid&(1<<bit) == 0 {
					want, raw := matrixPacket(layout, o, fullFlags|1<<bit, -1)
					want.Diagnostics.ReservedFlags = true
					want.Diagnostics.Issues = []string{"reserved_flags"}
					checkMatrix(t, want, raw, false)
					if _, err := EncodeMeasurement(want, o); err == nil {
						t.Fatal("encoded RFU flag")
					}
					rfus++
				}
			}
			for length := 0; length < len(raw); length++ {
				got, e := DecodeMeasurement(base.Kind, raw[:length], o)
				if length < base.FlagBytes {
					if e != ErrLength {
						t.Fatal("short flag error", e)
					}
					prefixes++
					continue
				}
				want := Measurement{Kind: base.Kind, Flags: fullFlags, Format: o, Values: map[MeasurementField]int32{}, Unavailable: map[MeasurementField]bool{}, BytesRead: base.FlagBytes, Diagnostics: Diagnostics{Truncated: true, Issues: []string{"truncated"}}}
				for _, f := range layout.Fields {
					if want.BytesRead+f[1] > length {
						break
					}
					want.BytesRead += f[1]
					id := MeasurementField(f[2])
					want.Values[id] = full.Values[id]
				}
				if e != nil || !reflect.DeepEqual(got, want) {
					t.Fatalf("prefix kind=%d options=%+v length=%d got=%+v want=%+v err=%v", base.Kind, o, length, got, want, e)
				}
				prefixes++
			}
		}
	}
	if cases != 181760 || sentinels != 46 || rfus != 47 || prefixes != 315 {
		t.Fatalf("unexpected totals: %d %d %d %d", cases, sentinels, rfus, prefixes)
	}
	t.Logf("contract=%s layoutsSHA256=%x contractSHA256=%x structural=%d directional=%d sentinels=%d RFU=%d incompletePrefixes=%d; planner budgets NOT implemented", doc.Contract, sha256.Sum256(b), sha256.Sum256(contract), cases, cases*2, sentinels, rfus, prefixes)
}

func matrixPacket(l matrixLayout, o MeasurementOptions, flags uint32, sentinel int) (Measurement, []byte) {
	m := Measurement{Kind: l.Kind, Flags: flags, Format: o, Values: map[MeasurementField]int32{}, Unavailable: map[MeasurementField]bool{}}
	b := make([]byte, l.FlagBytes)
	for i := range b {
		b[i] = byte(flags >> uint(8*i))
	}
	for _, f := range l.Fields {
		selected := flags&(1<<f[0]) != 0
		if f[0] == 0 {
			selected = flags&1 == 0
		}
		if !selected {
			continue
		}
		id := MeasurementField(f[2])
		v := int32(f[2]+1) * 3
		if f[3] != 0 {
			v = -v
		}
		if f[2] == sentinel {
			m.Unavailable[id] = true
			m.Diagnostics.Issues = []string{"unavailable"}
			if f[3] != 0 {
				v = 0x7fff
			} else {
				v = (1 << uint(8*f[1])) - 1
			}
		} else {
			m.Values[id] = v
		}
		for i := 0; i < f[1]; i++ {
			b = append(b, byte(uint32(v)>>uint(8*i)))
		}
	}
	m.BytesRead = len(b)
	return m, b
}

func checkMatrix(t *testing.T, want Measurement, raw []byte, encode bool) {
	t.Helper()
	got, e := DecodeMeasurement(want.Kind, raw, want.Format)
	if e != nil || !reflect.DeepEqual(got, want) {
		t.Fatalf("kind=%d flags=%x format=%+v decode=%+v want=%+v err=%v", want.Kind, want.Flags, want.Format, got, want, e)
	}
	if encode {
		b, e := EncodeMeasurement(want, want.Format)
		if e != nil || !bytes.Equal(b, raw) {
			t.Fatalf("matrix encode kind=%d flags=%x format=%+v bytes=%v want=%v err=%v", want.Kind, want.Flags, want.Format, b, raw, e)
		}
	}
}
