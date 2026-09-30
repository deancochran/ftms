//go:build conformance

package ftms

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"slices"
	"strings"
	"testing"
)

type object = map[string]any

func number(o object, k string) int64 { return int64(o[k].(float64)) }
func flag(b bool) int {
	if b {
		return 1
	}
	return 0
}
func issue(d Diagnostics, s string) int { return flag(slices.Contains(d.Issues, s)) }
func wire(o object, k string) []byte {
	b := []byte{}
	for _, v := range o[k].([]any) {
		b = append(b, byte(v.(float64)))
	}
	return b
}
func ints(v any) []int32 {
	r := []int32{}
	for _, n := range v.([]any) {
		r = append(r, int32(n.(float64)))
	}
	return r
}
func rangeKind(s string) RangeKind {
	return map[string]RangeKind{"speed": SpeedRange, "inclination": InclinationRange, "resistance": ResistanceRange, "heartRate": HeartRateRange, "power": PowerRange}[s]
}
func exact(t *testing.T, actual any, expected any) {
	t.Helper()
	b, err := json.Marshal(actual)
	if err != nil {
		t.Fatal(err)
	}
	var normalized any
	if err = json.Unmarshal(b, &normalized); err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(normalized, expected) {
		t.Errorf("actual=%s\nexpected=%v", b, expected)
	}
}
func exactBytes(t *testing.T, got []byte, err error, want []byte) {
	t.Helper()
	if err != nil || !bytes.Equal(got, want) {
		t.Errorf("bytes=%v err=%v; want=%v", got, err, want)
	}
}

type caseResult struct{ ID, Direction, Status string }
type corpusReport struct {
	Corpus                                                  string
	SchemaVersion                                           int
	SchemaValidation                                        string
	Hashes                                                  map[string]string
	Cases, Assertions, Passed, Failed, Unsupported, Skipped int
	Results                                                 []caseResult
}
type runReport struct {
	Commit    string
	Dirty     bool
	Toolchain string
	Corpora   []*corpusReport
}

// TestRawConformance executes complete directional assertions for the five named
// additive corpora. It does not claim the original normalized codec-v1 contract.
// Schema validation is a separate mandatory step in scripts/verify.sh.
func TestRawConformance(t *testing.T) {
	git := func(args ...string) string {
		b, e := exec.Command("git", args...).Output()
		if e != nil {
			t.Fatal(e)
		}
		return strings.TrimSpace(string(b))
	}
	v, e := exec.Command("go", "version").Output()
	if e != nil {
		t.Fatal(e)
	}
	report := runReport{Commit: git("rev-parse", "HEAD"), Dirty: git("status", "--porcelain") != "", Toolchain: strings.TrimSpace(string(v))}
	for _, name := range []string{"values", "controls", "measurements", "statuses", "compatibility"} {
		r := &corpusReport{Corpus: name + "/v1", SchemaVersion: 1, SchemaValidation: "separate verify.sh gate required", Hashes: map[string]string{}, Results: []caseResult{}}
		report.Corpora = append(report.Corpora, r)
		root := filepath.Join("..", "..", "shared", "conformance", name)
		var doc object
		for _, path := range []string{"v1/schema.json", "v1/vectors.json", "README.md"} {
			b, err := os.ReadFile(filepath.Join(root, path))
			if err != nil {
				t.Fatal(err)
			}
			r.Hashes[path] = fmt.Sprintf("%x", sha256.Sum256(b))
			if path == "v1/vectors.json" {
				if err = json.Unmarshal(b, &doc); err != nil {
					t.Fatal(err)
				}
			}
		}
		if number(doc, "schemaVersion") != 1 {
			t.Fatal("unsupported schema version")
		}
		categories := map[string][]string{"values": {"cases"}, "controls": {"requests", "responses", "invalid"}, "measurements": {"cases"}, "statuses": {"machine", "training"}, "compatibility": {"cases"}}[name]
		ids := map[string]bool{}
		for _, category := range categories {
			for _, raw := range doc[category].([]any) {
				c := raw.(object)
				id := c["id"].(string)
				if ids[id] {
					t.Fatalf("duplicate id %s/%s", name, id)
				}
				ids[id] = true
				r.Cases++
				directions := []string{"decode"}
				encode := name == "values" || name == "controls" && category != "invalid"
				if v, ok := c["encode"].(bool); ok {
					encode = v
				}
				if encode {
					directions = append(directions, "encode")
				}
				for _, direction := range directions {
					r.Assertions++
					ok := t.Run(name+"/"+id+"/"+direction, func(t *testing.T) { runRawCase(t, name, category, c, direction) })
					status := "passed"
					if ok {
						r.Passed++
					} else {
						status = "failed"
						r.Failed++
					}
					r.Results = append(r.Results, caseResult{id, direction, status})
				}
			}
		}
		expected := map[string][2]int{"values": {8, 16}, "controls": {41, 72}, "measurements": {26, 47}, "statuses": {38, 63}, "compatibility": {9, 18}}[name]
		if r.Cases != expected[0] || r.Assertions != expected[1] {
			t.Errorf("%s unexpected accounting %d/%d", name, r.Cases, r.Assertions)
		}
	}
	b, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if path := os.Getenv("FTMS_GO_REPORT"); path != "" {
		if err = os.WriteFile(path, b, 0600); err != nil {
			t.Fatal(err)
		}
	}
	for _, r := range report.Corpora {
		t.Logf("%s: cases=%d assertions=%d passed=%d failed=%d unsupported=%d skipped=%d", r.Corpus, r.Cases, r.Assertions, r.Passed, r.Failed, r.Unsupported, r.Skipped)
	}
}

func runRawCase(t *testing.T, name, category string, c object, direction string) {
	enc := direction == "encode"
	if name == "values" {
		b := wire(c, "expectedBytes")
		if c["operation"] == "features" {
			f := Features{MachineRaw: uint32(number(c, "machine")), TargetRaw: uint32(number(c, "target"))}
			if enc {
				exactBytes(t, EncodeFeatures(f), nil, b)
				return
			}
			got, e := DecodeFeatures(b)
			if e != nil {
				t.Fatal(e)
			}
			f.MachineUnknown = f.MachineRaw &^ 0x1ffff
			f.TargetUnknown = f.TargetRaw &^ 0x1ffff
			if got != f {
				t.Errorf("got=%+v want=%+v", got, f)
			}
		} else {
			runRangeCase(t, c, c, b, RangeOptions{}, enc)
		}
		return
	}
	if name == "controls" {
		b := wire(c, "bytes")
		o := ControlOptions{}
		if c["format"] == "uint8Tenths" {
			o.Resistance = ControlResistanceUint8Tenths
		}
		if category == "invalid" {
			var e error
			if c["operation"] == "request" {
				_, e = DecodeControlRequest(b, o)
			} else {
				_, e = DecodeControlResponse(b, true)
			}
			want := map[string]error{"length": ErrLength, "kind": ErrKind, "range": ErrRange}[c["error"].(string)]
			if !errors.Is(e, want) {
				t.Errorf("error=%v want=%v", e, want)
			}
			return
		}
		d := c["decoded"].(object)
		if category == "requests" {
			want := ControlRequest{Opcode: byte(number(d, "opcode")), Operands: ints(d["operands"])}
			if enc {
				got, e := EncodeControlRequest(want, o)
				exactBytes(t, got, e, b)
				return
			}
			got, e := DecodeControlRequest(b, o)
			if e != nil {
				t.Fatal(e)
			}
			operands := append([]int32{}, got.Operands...)
			exact(t, object{"opcode": got.Opcode, "operands": operands}, d)
		} else {
			if enc {
				got, e := EncodeControlResponse(ControlResponse{RequestOpcode: byte(number(d, "requestOpcode")), ResultCode: byte(number(d, "resultCode")), HasSpinDown: number(d, "parameter") == 1, SpinDownLow: uint16(number(d, "low")), SpinDownHigh: uint16(number(d, "high")), UnknownRequest: number(d, "unknownRequest") == 1, UnknownResult: number(d, "unknownResult") == 1, UnexpectedParameters: number(d, "unexpectedParameters") == 1})
				exactBytes(t, got, e, b)
				return
			}
			got, e := DecodeControlResponse(b, true)
			if e != nil {
				t.Fatal(e)
			}
			exact(t, object{"requestOpcode": got.RequestOpcode, "resultCode": got.ResultCode, "parameter": flag(got.HasSpinDown), "low": got.SpinDownLow, "high": got.SpinDownHigh, "unknownRequest": flag(got.UnknownRequest), "unknownResult": flag(got.UnknownResult), "unexpectedParameters": flag(got.UnexpectedParameters)}, d)
		}
		return
	}
	if name == "measurements" || name == "compatibility" {
		dkey := "decoded"
		if name == "compatibility" {
			dkey = "expected"
		}
		d := c[dkey].(object)
		b := wire(c, "bytes")
		o := MeasurementOptions{}
		if opts, ok := c["options"].(object); ok {
			if opts["resistanceFormat"] == "signed16Tenths" {
				o.Resistance = MeasurementResistanceSigned16Tenths
			}
			o.TreadmillPaceUint8 = opts["treadmillPaceFormat"] == "uint8Legacy"
		}
		if c["area"] == "range" {
			rangeOptions := RangeOptions{}
			if o.Resistance == MeasurementResistanceSigned16Tenths {
				rangeOptions.Resistance = ResistanceSint16Tenths
			}
			runRangeCase(t, c, d, b, rangeOptions, enc)
			return
		}
		k := MeasurementKind(number(c, "kind"))
		if enc {
			m := Measurement{Kind: k, Flags: uint32(number(d, "flags")), Values: map[MeasurementField]int32{}, Unavailable: map[MeasurementField]bool{}, Format: o}
			for i, v := range ints(d["values"]) {
				if number(d, "present")&(1<<i) != 0 {
					if number(d, "unavailable")&(1<<i) != 0 {
						m.Unavailable[MeasurementField(i)] = true
					} else {
						m.Values[MeasurementField(i)] = v
					}
				}
			}
			got, e := EncodeMeasurement(m, o)
			exactBytes(t, got, e, b)
			return
		}
		m, e := DecodeMeasurement(k, b, o)
		if n, ok := d["error"].(float64); ok {
			want := map[int]error{2: ErrLength, 3: ErrKind}[int(n)]
			if !errors.Is(e, want) {
				t.Errorf("error=%v want=%v", e, want)
			}
			return
		}
		if e != nil {
			t.Fatal(e)
		}
		values := make([]int32, 30)
		present, unavailable := uint32(0), uint32(0)
		for i, v := range m.Values {
			values[i] = v
			present |= 1 << i
		}
		for i, v := range m.Unavailable {
			if v {
				present |= 1 << i
				unavailable |= 1 << i
			}
		}
		exact(t, object{"kind": m.Kind, "flags": m.Flags, "present": present, "unavailable": unavailable, "values": values, "moreData": flag(m.Flags&1 != 0), "backward": flag(m.Kind == CrossTrainer && m.Flags&(1<<15) != 0), "truncated": flag(m.Diagnostics.Truncated), "trailingBytes": flag(m.Diagnostics.TrailingBytes), "reservedFlags": flag(m.Diagnostics.ReservedFlags), "bytesRead": m.BytesRead}, d)
		return
	}
	if name == "statuses" {
		d := c["decoded"].(object)
		b := wire(c, "bytes")
		if category == "machine" {
			o := ControlOptions{}
			if enc {
				m := MachineStatus{Opcode: byte(number(d, "opcode"))}
				if p, ok := d["parameter"].(object); ok {
					m.Operands = ints(p["operands"])
				} else if m.Opcode == 2 || m.Opcode == 20 {
					m.Operands = []int32{int32(number(d, "action"))}
				}
				got, e := EncodeMachineStatus(m, o)
				exactBytes(t, got, e, b)
				return
			}
			m := DecodeMachineStatus(b, o)
			action := int32(0)
			var parameter any
			if m.Opcode == 2 || m.Opcode == 20 {
				if len(m.Operands) > 0 {
					action = m.Operands[0]
				}
			} else if op, ok := machineControl(m.Opcode); ok && !m.Diagnostics.Truncated {
				parameter = object{"opcode": op, "operands": append([]int32{}, m.Operands...)}
			}
			exact(t, object{"opcode": m.Opcode, "action": action, "parameter": parameter, "unknownOpcode": issue(m.Diagnostics, "unknown_opcode"), "reservedValue": issue(m.Diagnostics, "reserved_value"), "truncated": flag(m.Diagnostics.Truncated), "trailingBytes": flag(m.Diagnostics.TrailingBytes)}, d)
		} else {
			if enc {
				text, e := hex.DecodeString(d["textHex"].(string))
				if e != nil {
					t.Fatal(e)
				}
				got, e := EncodeTrainingStatus(TrainingStatus{Flags: byte(number(d, "flags")), Code: byte(number(d, "code")), Text: string(text)})
				exactBytes(t, got, e, b)
				return
			}
			m := DecodeTrainingStatus(b)
			present := !m.Diagnostics.Truncated && m.Flags&1 != 0
			offset := 0
			if present {
				offset = 2
			}
			extended := !m.Diagnostics.Truncated && m.Flags&2 != 0
			reserved := byte(0)
			if !m.Diagnostics.Truncated {
				reserved = m.Flags &^ 3
			}
			exact(t, object{"flags": m.Flags, "code": m.Code, "textOffset": offset, "textSize": len(m.Text), "textPresent": flag(present), "extendedString": flag(extended), "reservedFlags": reserved, "reservedValue": issue(m.Diagnostics, "reserved_value"), "invalidFlags": issue(m.Diagnostics, "invalid_flags"), "invalidUtf8": issue(m.Diagnostics, "invalid_utf8"), "truncated": flag(m.Diagnostics.Truncated), "trailingBytes": flag(m.Diagnostics.TrailingBytes), "textHex": hex.EncodeToString([]byte(m.Text))}, d)
		}
		return
	}
	t.Fatal("unhandled corpus")
}

func runRangeCase(t *testing.T, c, d object, b []byte, o RangeOptions, enc bool) {
	k := rangeKind(c["kind"].(string))
	want := SupportedRange{Kind: k, Minimum: int32(number(d, "minimum")), Maximum: int32(number(d, "maximum")), Increment: int32(number(d, "increment")), Format: o}
	if enc {
		got, e := EncodeRange(want, o)
		exactBytes(t, got, e, b)
		return
	}
	got, e := DecodeRange(k, b, o)
	if e != nil {
		t.Fatal(e)
	}
	if got != want {
		t.Errorf("got=%+v want=%+v", got, want)
	}
	n := NormalizeRange(got)
	divisor := float64(number(d, "scaleDivisor"))
	if n.Minimum != float64(want.Minimum)/divisor || n.Maximum != float64(want.Maximum)/divisor || n.Increment != float64(want.Increment)/divisor {
		t.Error("range normalization mismatch")
	}
	units := map[string]int{"km/h": 0, "percent": 1, "level": 2, "bpm": 3, "watts": 4}
	if units[n.Unit] != int(number(d, "unit")) {
		t.Errorf("unit %s", n.Unit)
	}
}
