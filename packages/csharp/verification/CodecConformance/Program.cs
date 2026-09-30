using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Nodes;
using DeanCochran.Ftms;

// This executable is deliberately an adapter, not a second codec.  It only turns
// typed C# evidence into the language-neutral raw shapes used by shared fixtures.
internal static partial class Program
{
    private static readonly string[] FieldNames = ["speed", "averageSpeed", "distance", "inclination", "rampAngle", "positiveElevation", "negativeElevation", "instantaneousPace", "averagePace", "energy", "energyPerHour", "energyPerMinute", "heartRate", "met", "elapsed", "remaining", "force", "power", "stepRate", "averageStepRate", "strideCount", "resistance", "averagePower", "floorCount", "stepCount", "strokeRate", "strokeCount", "averageStrokeRate", "cadence", "averageCadence"];
    private static readonly List<JsonObject> Outcomes = [];
    private static int passed, failed, unsupported, skipped, assertions;
    private static readonly Dictionary<string, int> Categories = new();

    public static int Main(string[] args)
    {
        var root = FindRoot();
        var reportPath = args.Length == 0 ? Path.Combine(Environment.CurrentDirectory, "codec-conformance-report.json") : args[0];
        try
        {
            Discover(root);
            ComparatorSelfTests();
            foreach (var run in new Action<string>[] { RunValues, RunControls, RunMeasurements, RunStatuses, RunCompatibility, RunInspection, RunLegacyConformance })
            {
                try { run(root); }
                catch (Exception error) { Record("runner", run.Method.Name, "runner", "failed", error.ToString()); }
            }
        }
        catch (Exception error) { Record("runner", "fatal", "runner", "failed", error.ToString()); }
        var caseOutcomes = ReconcileCases();

        var report = new JsonObject
        {
            ["runner"] = "DeanCochran.Ftms CodecConformance",
            ["complete"] = DiscoveryComplete && ExpectedCases.Count > 0 && passed > 0 && failed == 0 && unsupported == 0 && skipped == 0,
            ["summary"] = new JsonObject { ["passed"] = passed, ["failed"] = failed, ["unsupported"] = unsupported, ["skipped"] = skipped, ["assertions"] = assertions },
            ["categories"] = JsonSerializer.SerializeToNode(Categories),
            ["discoveredCases"] = ExpectedCases.Count,
            ["discoveryComplete"] = DiscoveryComplete,
            ["comparisons"] = assertions,
            ["caseCategoryCounts"] = JsonSerializer.SerializeToNode(ExpectedCases.Values.GroupBy(value => value.Category).ToDictionary(group => group.Key, group => group.Count())),
            ["caseOutcomes"] = caseOutcomes,
            ["caseSummary"] = JsonSerializer.SerializeToNode(caseOutcomes.GroupBy(value => value!["outcome"]!.GetValue<string>()).ToDictionary(group => group.Key, group => group.Count())),
            ["outcomes"] = new JsonArray(Outcomes.Select(x => (JsonNode)x).ToArray()),
            ["identity"] = Identity(root)
        };
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(reportPath))!);
        File.WriteAllText(reportPath, report.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine($"Codec conformance: {passed} passed, {failed} failed, {unsupported} unsupported, {skipped} skipped. Report: {reportPath}");
        return DiscoveryComplete && ExpectedCases.Count > 0 && failed == 0 && unsupported == 0 && skipped == 0 ? 0 : 1;
    }

    private static void RunValues(string root)
    {
        var doc = Load(root, "shared/conformance/values/v1/vectors.json");
        RequireSchemaVersion(doc.RootElement, "values");
        EnsureUniqueIds(doc.RootElement.GetProperty("cases"), "values");
        foreach (var c in doc.RootElement.GetProperty("cases").EnumerateArray())
        {
            var id = c.GetProperty("id").GetString()!; var bytes = Bytes(c.GetProperty("expectedBytes"));
            if (c.GetProperty("operation").GetString() == "features")
            {
                var value = new Features(c.GetProperty("machine").GetUInt32(), c.GetProperty("target").GetUInt32());
                Check("values/features", id, "encode", bytes, FeatureCodec.Encode(value));
                var actual = FeatureCodec.Decode(bytes); CheckObject("values/features", id, "decode", Obj(("machine", actual.MachineRaw), ("target", actual.TargetRaw)), Obj(("machine", value.MachineRaw), ("target", value.TargetRaw)));
            }
            else
            {
                var range = Range(c); Check("values/ranges", id, "encode", bytes, RangeCodec.Encode(range));
                var actual = RangeCodec.Decode(range.Kind, bytes); CheckObject("values/ranges", id, "decode", RangeJson(actual), RangeJson(range));
            }
        }
    }

    private static void RunControls(string root)
    {
        var doc = Load(root, "shared/conformance/controls/v1/vectors.json");
        RequireSchemaVersion(doc.RootElement, "controls");
        EnsureUniqueIds("controls", doc.RootElement.GetProperty("requests"), doc.RootElement.GetProperty("responses"), doc.RootElement.GetProperty("invalid"));
        foreach (var c in doc.RootElement.GetProperty("requests").EnumerateArray())
        {
            var id = c.GetProperty("id").GetString()!; var expected = c.GetProperty("decoded"); var bytes = Bytes(c.GetProperty("bytes")); var request = new ControlRequest(expected.GetProperty("opcode").GetByte(), expected.GetProperty("operands").EnumerateArray().Select(x => x.GetInt32()).ToArray()); var format = ControlFormat(c);
            Check("controls/requests", id, "encode", bytes, ControlCodec.EncodeRequest(request, format));
            var actual = ControlCodec.DecodeRequest(bytes, format); CheckObject("controls/requests", id, "decode", RequestJson(actual), expected);
        }
        foreach (var c in doc.RootElement.GetProperty("responses").EnumerateArray())
        {
            var id = c.GetProperty("id").GetString()!; var bytes = Bytes(c.GetProperty("bytes")); var expected = c.GetProperty("decoded"); var result = ControlCodec.DecodeResponse(bytes); CheckObject("controls/responses", id, "decode", ResponseJson(result), expected);
            if (!c.TryGetProperty("encode", out var e) || e.GetBoolean()) Check("controls/responses", id, "encode", bytes, ControlCodec.EncodeResponse(Response(expected)));
        }
        foreach (var c in doc.RootElement.GetProperty("invalid").EnumerateArray())
        {
            var r = c.GetProperty("operation").GetString() == "response" ? ControlCodec.TryDecodeResponse(Bytes(c.GetProperty("bytes"))).Error : ControlCodec.TryDecodeRequest(Bytes(c.GetProperty("bytes")), ControlFormat(c)).Error;
            CheckObject("controls/invalid", c.GetProperty("id").GetString()!, "decode", JsonValue.Create(Code(r))!, c.GetProperty("error"));
        }
    }

    private static void RunMeasurements(string root)
    {
        var doc = Load(root, "shared/conformance/measurements/v1/vectors.json");
        RequireSchemaVersion(doc.RootElement, "measurements");
        EnsureUniqueIds(doc.RootElement.GetProperty("cases"), "measurements");
        foreach (var c in doc.RootElement.GetProperty("cases").EnumerateArray()) RunMeasurementCase("measurements", c);
    }
    private static void RunCompatibility(string root)
    {
        var doc = Load(root, "shared/conformance/compatibility/v1/vectors.json");
        RequireSchemaVersion(doc.RootElement, "compatibility");
        EnsureUniqueIds(doc.RootElement.GetProperty("cases"), "compatibility");
        foreach (var c in doc.RootElement.GetProperty("cases").EnumerateArray())
        {
            if (c.GetProperty("area").GetString() == "measurement") RunMeasurementCase("compatibility/measurements", c);
            else { var range = Range(c.GetProperty("expected")); var bytes = Bytes(c.GetProperty("bytes")); var f = RangeFormat(c); Check("compatibility/ranges", c.GetProperty("id").GetString()!, "encode", bytes, RangeCodec.Encode(range, f)); CheckObject("compatibility/ranges", c.GetProperty("id").GetString()!, "decode", RangeJson(RangeCodec.Decode(range.Kind, bytes, f)), c.GetProperty("expected")); }
        }
    }
    private static void RunMeasurementCase(string category, JsonElement c)
    {
        var id = c.GetProperty("id").GetString()!; var expected = c.TryGetProperty("decoded", out var decoded) ? decoded : c.GetProperty("expected"); var format = MeasurementFormatOf(c); var bytes = Bytes(c.GetProperty("bytes"));
        if (expected.TryGetProperty("error", out var error)) { CheckObject(category, id, "decode", JsonValue.Create(ErrorNumber(MeasurementCodec.TryDecode((MeasurementKind)c.GetProperty("kind").GetInt32(), bytes, format).Error)!)!, error); return; }
        var actual = MeasurementCodec.Decode((MeasurementKind)c.GetProperty("kind").GetInt32(), bytes, format); CheckObject(category, id, "decode", MeasurementJson(actual), expected);
        if (!c.TryGetProperty("encode", out var encode) || encode.GetBoolean()) Check(category, id, "encode", bytes, MeasurementCodec.Encode(MeasurementOf(expected, format)));
    }

    private static void RunStatuses(string root)
    {
        var doc = Load(root, "shared/conformance/statuses/v1/vectors.json");
        RequireSchemaVersion(doc.RootElement, "statuses");
        EnsureUniqueIds("statuses", doc.RootElement.GetProperty("machine"), doc.RootElement.GetProperty("training"));
        foreach (var c in doc.RootElement.GetProperty("machine").EnumerateArray()) { var id = c.GetProperty("id").GetString()!; var bytes = Bytes(c.GetProperty("bytes")); var expected = c.GetProperty("decoded"); CheckObject("statuses/machine", id, "decode", MachineJson(StatusCodec.DecodeMachine(bytes)), expected); if (c.GetProperty("encode").GetBoolean()) Check("statuses/machine", id, "encode", bytes, StatusCodec.EncodeMachine(MachineOf(expected))); }
        foreach (var c in doc.RootElement.GetProperty("training").EnumerateArray()) { var id = c.GetProperty("id").GetString()!; var bytes = Bytes(c.GetProperty("bytes")); var expected = c.GetProperty("decoded"); CheckObject("statuses/training", id, "decode", TrainingJson(StatusCodec.DecodeTraining(bytes)), expected); if (c.GetProperty("encode").GetBoolean()) Check("statuses/training", id, "encode", bytes, StatusCodec.EncodeTraining(TrainingOf(expected))); }
    }

    private static void RunInspection(string root)
    {
        var doc = Load(root, "shared/conformance/inspection/v1/fixtures.json"); RequireSchemaVersion(doc.RootElement, "inspection"); EnsureUniqueIds(doc.RootElement.GetProperty("cases"), "inspection"); foreach (var c in doc.RootElement.GetProperty("cases").EnumerateArray()) { var f = RangeFormat(c); var v = RangeCodec.Inspect(Kind(c.GetProperty("kind").GetString()!), Bytes(c.GetProperty("bytes")), f); CheckObject("inspection", c.GetProperty("id").GetString()!, "inspect", InspectionJson(v), c.GetProperty("expected")); }
    }

    private static JsonObject MeasurementJson(Measurement m) { long present = 0, unavailable = 0; var values = new JsonArray(); for (int i = 0; i < 30; i++) { var key = (MeasurementField)i; if (m.Fields.TryGetValue(key, out var raw)) { present |= 1L << i; if (!raw.HasValue) unavailable |= 1L << i; values.Add(raw ?? 0); } else values.Add(0); } return Obj(("kind", (int)m.Kind), ("flags", m.Flags), ("present", present), ("unavailable", unavailable), ("values", values), ("moreData", m.MoreData ? 1 : 0), ("backward", m.Backward ? 1 : 0), ("truncated", m.Diagnostics.Truncated ? 1 : 0), ("trailingBytes", m.Diagnostics.TrailingBytes ? 1 : 0), ("reservedFlags", m.Diagnostics.ReservedFlags ? 1 : 0), ("bytesRead", m.BytesRead)); }
    private static Measurement MeasurementOf(JsonElement e, MeasurementFormat f) { var d = new Dictionary<MeasurementField, int?>(); var values = e.GetProperty("values"); long present = e.GetProperty("present").GetInt64(), unavailable = e.GetProperty("unavailable").GetInt64(); for (int i = 0; i < 30; i++) if ((present & (1L << i)) != 0) d[(MeasurementField)i] = (unavailable & (1L << i)) != 0 ? null : values[i].GetInt32(); return new Measurement((MeasurementKind)e.GetProperty("kind").GetInt32(), e.GetProperty("flags").GetUInt32(), d, f); }
    private static JsonObject RequestJson(ControlRequest x) => Obj(("opcode", x.Opcode), ("operands", new JsonArray(x.Operands.Select(value => (JsonNode?)JsonValue.Create(value)).ToArray())));
    private static JsonObject ResponseJson(ControlResponse x) => Obj(("requestOpcode", x.RequestOpcode), ("resultCode", x.ResultCode), ("parameter", x.SpinDownStartSpeed.HasValue ? 1 : 0), ("low", x.SpinDownStartSpeed ?? 0), ("high", x.SpinDownEndSpeed ?? 0), ("unknownRequest", x.UnknownRequest ? 1 : 0), ("unknownResult", x.UnknownResult ? 1 : 0), ("unexpectedParameters", x.UnexpectedParameters ? 1 : 0));
    private static JsonObject RangeJson(SupportedRange x) => Obj(("kind", KindName(x.Kind)), ("minimum", x.Minimum), ("maximum", x.Maximum), ("increment", x.Increment), ("scaleDivisor", x.ScaleDivisor), ("unit", (int)x.Unit));
    private static JsonObject MachineJson(MachineStatus x) => Obj(("opcode", x.Opcode), ("action", x.Action), ("parameter", x.Parameter is null ? null : RequestJson(x.Parameter)), ("unknownOpcode", x.Diagnostics.Issues.Contains("unknown_opcode") ? 1 : 0), ("reservedValue", x.Diagnostics.Issues.Contains("reserved_value") ? 1 : 0), ("truncated", x.Diagnostics.Truncated ? 1 : 0), ("trailingBytes", x.Diagnostics.TrailingBytes ? 1 : 0));
    private static JsonObject TrainingJson(TrainingStatus x) => Obj(("flags", x.Flags), ("code", x.Code), ("textOffset", x.TextOffset), ("textSize", x.TextSize), ("textHex", Convert.ToHexString(x.TextBytes).ToLowerInvariant()), ("textPresent", !x.Diagnostics.Truncated && x.TextPresent ? 1 : 0), ("extendedString", x.ExtendedString ? 1 : 0), ("reservedValue", x.Diagnostics.Issues.Contains("reserved_value") ? 1 : 0), ("invalidFlags", x.Diagnostics.Issues.Contains("invalid_flags") ? 1 : 0), ("invalidUtf8", x.Diagnostics.Issues.Contains("invalid_utf8") ? 1 : 0), ("truncated", x.Diagnostics.Truncated ? 1 : 0), ("trailingBytes", x.Diagnostics.TrailingBytes ? 1 : 0), ("reservedFlags", x.ReservedFlags));
    private static JsonObject InspectionJson(RangeInspection x) => Obj(("selectedProfile", x.SelectedProfile), ("actualLength", x.ActualLength), ("expectedLength", x.ExpectedLength), ("status", x.Status.ToString().ToLowerInvariant()), ("value", x.Value is null ? null : RangeJson(x.Value)), ("candidates", new JsonArray(x.Candidates.Select(c => Obj(("profile", c.Profile), ("expectedLength", c.ExpectedLength), ("status", c.Status.ToString().ToLowerInvariant()), ("value", c.Value is null ? null : RangeJson(c.Value)))).ToArray())));

    private static SupportedRange Range(JsonElement e) => new(Kind(e.GetProperty("kind").ValueKind == JsonValueKind.String ? e.GetProperty("kind").GetString()! : KindName((RangeKind)e.GetProperty("kind").GetInt32())), e.GetProperty("minimum").GetInt32(), e.GetProperty("maximum").GetInt32(), e.GetProperty("increment").GetInt32(), e.GetProperty("scaleDivisor").GetInt32(), (RangeUnit)e.GetProperty("unit").GetInt32());
    private static ControlResponse Response(JsonElement e) => new(e.GetProperty("requestOpcode").GetByte(), e.GetProperty("resultCode").GetByte(), e.GetProperty("parameter").GetInt32() == 1 ? (ushort)e.GetProperty("low").GetInt32() : null, e.GetProperty("parameter").GetInt32() == 1 ? (ushort)e.GetProperty("high").GetInt32() : null);
    private static MachineStatus MachineOf(JsonElement e) => new(e.GetProperty("opcode").GetByte(), e.GetProperty("action").GetByte(), e.GetProperty("parameter").ValueKind == JsonValueKind.Null ? null : new ControlRequest(e.GetProperty("parameter").GetProperty("opcode").GetByte(), e.GetProperty("parameter").GetProperty("operands").EnumerateArray().Select(x => x.GetInt32()).ToArray()));
    private static TrainingStatus TrainingOf(JsonElement e) => new(e.GetProperty("flags").GetByte(), e.GetProperty("code").GetByte(), e.GetProperty("textPresent").GetInt32() == 0 ? null : System.Text.Encoding.UTF8.GetString(Convert.FromHexString(e.GetProperty("textHex").GetString()!)));
    private static MeasurementFormat MeasurementFormatOf(JsonElement c) { if (!c.TryGetProperty("options", out var o)) return new(); var resistance = !o.TryGetProperty("resistanceFormat", out var r) || r.GetString() == "uint8Whole" ? ResistanceFormat.UInt8Whole : r.GetString() == "signed16Tenths" ? ResistanceFormat.SInt16Tenths : throw new InvalidDataException("Unknown resistance format"); var pace = !o.TryGetProperty("treadmillPaceFormat", out var p) || p.GetString() == "uint16" ? TreadmillPaceFormat.UInt16 : p.GetString() == "uint8Legacy" ? TreadmillPaceFormat.UInt8Legacy : throw new InvalidDataException("Unknown treadmill pace format"); return new(resistance, pace); }
    private static ResistanceFormat RangeFormat(JsonElement c) { if (!c.TryGetProperty("options", out var o) || !o.TryGetProperty("resistanceFormat", out var r) || r.GetString() == "uint8Whole") return ResistanceFormat.UInt8Whole; return r.GetString() == "signed16Tenths" ? ResistanceFormat.SInt16Tenths : throw new InvalidDataException("Unknown resistance format"); }
    private static ControlResistanceFormat ControlFormat(JsonElement c) => !c.TryGetProperty("format", out var f) || f.GetString() == "signed16Tenths" ? ControlResistanceFormat.SInt16Tenths : f.GetString() == "uint8Tenths" ? ControlResistanceFormat.UInt8Tenths : throw new InvalidDataException("Unknown control format");
    private static RangeKind Kind(string s) => s switch { "speed" => RangeKind.Speed, "inclination" => RangeKind.Inclination, "resistance" => RangeKind.Resistance, "heartRate" => RangeKind.HeartRate, "power" => RangeKind.Power, _ => throw new InvalidDataException(s) };
    private static string KindName(RangeKind k) => k switch { RangeKind.Speed => "speed", RangeKind.Inclination => "inclination", RangeKind.Resistance => "resistance", RangeKind.HeartRate => "heartRate", _ => "power" };
    private static string Code(FtmsError? e) => e?.ToString().ToLowerInvariant() ?? "ok";
    private static int ErrorNumber(FtmsError? error) => error switch { FtmsError.Length => 2, FtmsError.Kind => 3, FtmsError.Range => 4, _ => 0 };
    private static byte[] Bytes(JsonElement x) => x.EnumerateArray().Select(v => v.GetByte()).ToArray();
    private static JsonDocument Load(string root, string relative) => JsonDocument.Parse(File.ReadAllText(Path.Combine(root, relative)));
    private static void RequireSchemaVersion(JsonElement document, string corpus) { if (!document.TryGetProperty("schemaVersion", out var version) || version.GetInt32() != 1) throw new InvalidDataException($"{corpus} schemaVersion must be 1"); }
    private static void EnsureUniqueIds(JsonElement cases, string corpus) => EnsureUniqueIds(corpus, cases);
    private static void EnsureUniqueIds(string corpus, params JsonElement[] groups) { var ids = new HashSet<string>(StringComparer.Ordinal); foreach (var group in groups) foreach (var item in group.EnumerateArray()) { var id = item.GetProperty("id").GetString()!; if (!ids.Add(id)) throw new InvalidDataException($"Duplicate {corpus} ID: {id}"); } }
    private static void Check(string cat, string id, string dir, byte[] expected, byte[] actual) => CheckObject(cat, id, dir, JsonSerializer.SerializeToNode(actual)!, JsonSerializer.SerializeToNode(expected)!);
    private static void CheckObject(string cat, string id, string dir, JsonNode actual, JsonElement expected) => CheckNode(cat, id, dir, actual, JsonNode.Parse(expected.GetRawText())!);
    private static void CheckObject(string cat, string id, string dir, JsonNode actual, JsonNode expected) => CheckNode(cat, id, dir, actual, expected);
    private static void CheckNode(string cat, string id, string dir, JsonNode actual, JsonNode expected) { assertions++; if (Exact(actual, expected, out var why)) Record(cat, id, dir, "passed", null); else Record(cat, id, dir, "failed", why + "; expected=" + expected.ToJsonString() + " actual=" + actual.ToJsonString()); }
    private static void RecordUnsupported(string cat, string id, string why) => Record(cat, id, "all", "unsupported", why);
    private static void Record(string cat, string id, string dir, string outcome, string? reason) { Categories[cat] = Categories.GetValueOrDefault(cat) + 1; if (outcome == "passed") passed++; else if (outcome == "failed") failed++; else if (outcome == "unsupported") unsupported++; else skipped++; Outcomes.Add(Obj(("category", cat), ("id", id), ("direction", dir), ("outcome", outcome), ("reason", reason))); }
    private static bool Exact(JsonNode? a, JsonNode? e, out string why) { if (a is null || e is null) { why = "null mismatch"; return a is null && e is null; } if (a is JsonObject ao && e is JsonObject eo) { if (ao.Count != eo.Count || ao.Any(p => !eo.ContainsKey(p.Key))) { why = "object keys mismatch"; return false; } foreach (var p in eo) if (!Exact(ao[p.Key], p.Value, out why)) { why = p.Key + "." + why; return false; } } else if (a is JsonArray aa && e is JsonArray ea) { if (aa.Count != ea.Count) { why = "array length mismatch"; return false; } for (var i = 0; i < aa.Count; i++) if (!Exact(aa[i], ea[i], out why)) { why = $"[{i}]." + why; return false; } } else if (a is JsonObject || a is JsonArray || e is JsonObject || e is JsonArray) { why = "JSON kind mismatch"; return false; } else if (a.ToJsonString() != e.ToJsonString()) { why = "scalar mismatch"; return false; } why = ""; return true; }
    private static void ComparatorSelfTests() { void Bad(JsonNode a, JsonNode e) { if (Exact(a, e, out _)) throw new InvalidOperationException("comparator accepted invalid negative test"); } Bad(JsonNode.Parse("{\"a\":1,\"b\":2}")!, JsonNode.Parse("{\"a\":1}")!); Bad(JsonNode.Parse("{}")!, JsonNode.Parse("{\"a\":null}")!); Bad(JsonNode.Parse("{\"a\":true}")!, JsonNode.Parse("{\"a\":\"true\"}")!); Bad(JsonNode.Parse("[2,1]")!, JsonNode.Parse("[1,2]")!); }
    private static string FindRoot() { for (var d = new DirectoryInfo(Environment.CurrentDirectory); d is not null; d = d.Parent) if (Directory.Exists(Path.Combine(d.FullName, "shared", "conformance"))) return d.FullName; throw new DirectoryNotFoundException("shared/conformance not found"); }
    private static JsonObject Identity(string root) => new() { ["sourceCommit"] = Git(root, "rev-parse HEAD"), ["dirty"] = Git(root, "status --porcelain").Length != 0, ["schemaVersion"] = 1, ["corpora"] = new JsonObject { { "codec-v1", Hashes(root, "shared/conformance/v1/schema.json", "shared/conformance/v1/vectors.json", "shared/conformance/README.md") }, { "values", Hashes(root, "shared/conformance/values/v1/schema.json", "shared/conformance/values/v1/vectors.json", "shared/conformance/values/README.md") }, { "controls", Hashes(root, "shared/conformance/controls/v1/schema.json", "shared/conformance/controls/v1/vectors.json", "shared/conformance/controls/README.md") }, { "measurements", Hashes(root, "shared/conformance/measurements/v1/schema.json", "shared/conformance/measurements/v1/vectors.json", "shared/conformance/measurements/README.md") }, { "statuses", Hashes(root, "shared/conformance/statuses/v1/schema.json", "shared/conformance/statuses/v1/vectors.json", "shared/conformance/statuses/README.md") }, { "compatibility", Hashes(root, "shared/conformance/compatibility/v1/schema.json", "shared/conformance/compatibility/v1/vectors.json", "shared/conformance/compatibility/README.md") }, { "inspection", Hashes(root, "shared/conformance/inspection/v1/fixtures.json", "shared/conformance/inspection/v1/README.md") } } };
    private static JsonObject Hashes(string root, params string[] files) { var o = new JsonObject(); foreach (var f in files) o[f] = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(Path.Combine(root, f)))).ToLowerInvariant(); return o; }
    private static string Git(string root, string args) { var p = Process.Start(new ProcessStartInfo("git", args) { WorkingDirectory = root, RedirectStandardOutput = true, RedirectStandardError = true })!; var output = p.StandardOutput.ReadToEnd(); var error = p.StandardError.ReadToEnd(); p.WaitForExit(); if (p.ExitCode != 0) throw new InvalidOperationException($"git {args} failed: {error}"); return output.Trim(); }
    private static JsonObject Obj(params (string Key, object? Value)[] values) { var o = new JsonObject(); foreach (var (k, v) in values) o[k] = v switch { null => null, JsonNode n => n, JsonElement e => JsonNode.Parse(e.GetRawText()), _ => JsonSerializer.SerializeToNode(v) }; return o; }
}
