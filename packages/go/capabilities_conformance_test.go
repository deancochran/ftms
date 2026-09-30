//go:build conformance

package ftms

import (
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

type portableSnapshot struct {
	Generation      uint32
	Discovery       DiscoveryState
	Scope           ServiceScope
	C7              C7Evidence
	Characteristics []struct {
		UUID       string
		Properties uint16
		ReadState  ReadState
		Reason     ReadReason
		Bytes      string
	}
}

func (p portableSnapshot) native() (CapabilitySnapshot, error) {
	s := CapabilitySnapshot{Generation: p.Generation, Discovery: p.Discovery, Scope: p.Scope, C7: p.C7}
	for _, x := range p.Characteristics {
		u, e := hex.DecodeString(x.UUID)
		if e != nil || len(u) != 16 {
			return s, fmt.Errorf("invalid UUID %q", x.UUID)
		}
		b, e := hex.DecodeString(x.Bytes)
		if e != nil {
			return s, e
		}
		var id UUID
		copy(id[:], u)
		s.Characteristics = append(s.Characteristics, CharacteristicObservation{UUID: id, Properties: x.Properties, ReadState: x.ReadState, Reason: x.Reason, Bytes: b})
	}
	return s, nil
}

func normalizedCapabilities(r CapabilityReport) object {
	index := func(i int, has bool) any {
		if has {
			return i
		}
		return nil
	}
	f := r.Feature
	feature := []any{f.Presence, f.Decode, index(f.InputIndex, f.HasInputIndex), f.MachineRaw, f.TargetRaw, f.MachineUnknown, f.TargetUnknown}
	ranges := [][]any{}
	for _, rr := range r.Ranges {
		var value any
		if v := rr.Value; v != nil {
			value = []any{v.Kind, v.Minimum, v.Maximum, v.Increment, v.ScaleDivisor, v.Unit}
		}
		ranges = append(ranges, []any{rr.Presence, rr.Decode, index(rr.InputIndex, rr.HasInputIndex), value})
	}
	operations := [][]any{}
	for _, o := range r.Operations {
		operations = append(operations, []any{o.Opcode, o.TargetBit, flag(o.OptionalInTable), o.Declaration, o.Prerequisite, o.Reasons})
	}
	observations := [][]any{}
	for _, o := range r.Observations {
		observations = append(observations, []any{o.InputIndex, hex.EncodeToString(o.UUID[:]), o.Properties, o.KnownKind, o.ReadState, o.Reason, o.ReadSize})
	}
	diagnostics := [][]any{}
	for _, d := range r.Diagnostics {
		diagnostics = append(diagnostics, []any{d.Code, d.KnownKind, index(d.InputIndex, d.HasInputIndex)})
	}
	return object{"generation": r.Generation, "discovery": r.Discovery, "scope": r.Scope, "observationCount": r.ObservationCount, "diagnosticCount": r.DiagnosticCount, "presence": r.Presence, "feature": feature, "ranges": ranges, "operations": operations, "observations": observations, "diagnostics": diagnostics}
}

func TestCapabilityConformance(t *testing.T) {
	report := object{"complete": false, "runnerErrors": []string{"fixture validation, expansion, or runner failed before completion"}}
	defer func() {
		if path := os.Getenv("FTMS_GO_REPORT"); path != "" {
			b, e := json.MarshalIndent(report, "", "  ")
			if e != nil {
				t.Error(e)
				return
			}
			if e = os.WriteFile(filepath.Join(filepath.Dir(path), "capabilities.json"), b, 0600); e != nil {
				t.Error(e)
			}
		}
	}()
	cmd := exec.Command("python3", "scripts/capability_fixtures.py")
	b, err := cmd.Output()
	if err != nil {
		if e, ok := err.(*exec.ExitError); ok {
			t.Fatalf("fixture validation/expansion failed: %s", e.Stderr)
		}
		t.Fatal(err)
	}
	var input struct {
		SchemaVersion                                  int
		SchemaID, SchemaValidation, SpecificationBasis string
		Hashes                                         map[string]string
		Cases                                          []struct {
			ID, Category string
			Snapshot     portableSnapshot
			Expected     object
		}
	}
	if err = json.Unmarshal(b, &input); err != nil {
		t.Fatal(err)
	}
	if len(input.Cases) == 0 || input.SchemaVersion != 1 || input.SchemaValidation != "passed" || len(input.Hashes) != 4 {
		t.Fatal("invalid fixture envelope")
	}
	git := func(args ...string) string {
		b, e := exec.Command("git", args...).Output()
		if e != nil {
			t.Fatal(e)
		}
		return strings.TrimSpace(string(b))
	}
	toolchain, e := exec.Command("go", "version").Output()
	if e != nil {
		t.Fatal(e)
	}
	metadata := object{"schemaVersion": input.SchemaVersion, "schemaID": input.SchemaID, "schemaValidation": input.SchemaValidation, "specificationBasis": input.SpecificationBasis, "hashes": input.Hashes, "sourceCommit": git("rev-parse", "HEAD"), "dirty": git("status", "--porcelain") != "", "toolchain": strings.TrimSpace(string(toolchain)), "unsupported": 0, "skipped": 0}
	for key, value := range metadata {
		report[key] = value
	}
	categories := map[string]int{}
	results := []object{}
	passed := 0
	for _, c := range input.Cases {
		categories[c.Category]++
		result := object{"id": c.ID, "category": c.Category, "status": "passed"}
		ok := t.Run(c.ID, func(t *testing.T) {
			s, e := c.Snapshot.native()
			if e != nil {
				result["reason"] = e.Error()
				t.Fatal(e)
			}
			r, e := InterpretCapabilities(s, CapabilityOptions{})
			if e != nil {
				result["reason"] = e.Error()
				t.Fatal(e)
			}
			actual := normalizedCapabilities(r)
			b, e := json.Marshal(actual)
			if e != nil {
				t.Fatal(e)
			}
			var normalized object
			if e = json.Unmarshal(b, &normalized); e != nil {
				t.Fatal(e)
			}
			if !reflect.DeepEqual(normalized, c.Expected) {
				t.Error("exact report mismatch")
				result["reason"] = "exact report mismatch"
				result["actual"] = actual
				result["expected"] = c.Expected
				for key, want := range c.Expected {
					if !reflect.DeepEqual(normalized[key], want) {
						t.Errorf("%s: actual=%v expected=%v", key, normalized[key], want)
					}
				}
				if len(normalized) != len(c.Expected) {
					t.Error("report key set mismatch")
				}
			}
		})
		if ok {
			passed++
		} else {
			result["status"] = "failed"
		}
		results = append(results, result)
	}
	report["cases"] = results
	report["categories"] = categories
	report["total"] = len(results)
	report["passed"] = passed
	report["failed"] = len(results) - passed
	report["complete"] = passed == len(results) && passed > 0
	report["runnerErrors"] = []string{}
	t.Logf("capabilities/v1 total=%d passed=%d failed=%d unsupported=0 skipped=0 categories=%v hashes=%v", len(results), passed, len(results)-passed, categories, input.Hashes)
}
