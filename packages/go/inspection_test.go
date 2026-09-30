//go:build conformance

package ftms

import (
	"crypto/sha256"
	"encoding/json"
	"os"
	"testing"
)

func TestRangeInspectionCorpus(t *testing.T) {
	root := "../../shared/conformance/inspection/v1/"
	b, e := os.ReadFile(root + "fixtures.json")
	if e != nil {
		t.Fatal(e)
	}
	contract, e := os.ReadFile(root + "README.md")
	if e != nil {
		t.Fatal(e)
	}
	var doc struct {
		SchemaVersion int
		Cases         []object
	}
	if e = json.Unmarshal(b, &doc); e != nil {
		t.Fatal(e)
	}
	if doc.SchemaVersion != 1 || len(doc.Cases) != 9 {
		t.Fatal("unexpected inspection corpus")
	}
	ids := map[string]bool{}
	for _, c := range doc.Cases {
		id := c["id"].(string)
		if ids[id] {
			t.Fatal("duplicate id", id)
		}
		ids[id] = true
		t.Run(id, func(t *testing.T) {
			k := rangeKind(c["kind"].(string))
			o := RangeOptions{}
			if opts, ok := c["options"].(object); ok && opts["resistanceFormat"] == "signed16Tenths" {
				o.Resistance = ResistanceSint16Tenths
			}
			r, e := InspectRange(k, wire(c, "bytes"), o)
			if e != nil {
				t.Fatal(e)
			}
			profile := func(f ResistanceFormat) string {
				if k == ResistanceRange {
					if f == ResistanceSint16Tenths {
						return "signed16Tenths"
					}
					return "uint8Whole"
				}
				return map[RangeKind]string{SpeedRange: "uint16Hundredths", InclinationRange: "signed16Tenths", HeartRateRange: "uint8Bpm", PowerRange: "signed16Watts"}[k]
			}
			status := func(e error) string {
				if e == nil {
					return "valid"
				}
				if e == ErrLength {
					return "length"
				}
				if e == ErrRange {
					return "range"
				}
				t.Fatal(e)
				return ""
			}
			value := func(v *SupportedRange) any {
				if v == nil {
					return nil
				}
				divisor := 1
				if k == SpeedRange {
					divisor = 100
				}
				if k == InclinationRange || k == ResistanceRange && v.Format.Resistance == ResistanceSint16Tenths {
					divisor = 10
				}
				unit := map[RangeKind]int{SpeedRange: 0, InclinationRange: 1, ResistanceRange: 2, HeartRateRange: 3, PowerRange: 4}[k]
				return object{"kind": c["kind"], "minimum": v.Minimum, "maximum": v.Maximum, "increment": v.Increment, "scaleDivisor": divisor, "unit": unit}
			}
			candidates := []object{}
			for _, candidate := range r.Candidates {
				candidates = append(candidates, object{"profile": profile(candidate.Format), "expectedLength": candidate.ExpectedLength, "status": status(candidate.Err), "value": value(candidate.Value)})
			}
			exact(t, object{"selectedProfile": profile(r.Selected), "actualLength": r.ActualLength, "expectedLength": r.ExpectedLength, "status": status(r.Err), "value": value(r.Value), "candidates": candidates}, c["expected"])
		})
	}
	t.Logf("inspection/v1 cases=9 complete-reports=9 fixturesSHA256=%x contractSHA256=%x", sha256.Sum256(b), sha256.Sum256(contract))
}
