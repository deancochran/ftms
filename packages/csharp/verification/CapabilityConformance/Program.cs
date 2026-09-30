using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Nodes;
using DeanCochran.Ftms;

internal static class Program
{
    private static int Main(string[] args)
    {
        try
        {
            string root = FindRoot();
            string fixture = Path.Combine(root, "shared/conformance/capabilities/v1/vectors.json");
            JsonObject corpus = JsonNode.Parse(File.ReadAllText(fixture))!.AsObject();
            if (corpus["schemaVersion"]?.GetValue<int>() != 1)
                throw new InvalidDataException("Unsupported capability corpus schemaVersion.");

            int nativeTestCount = RunNativeImmutabilityChecks();
            JsonArray cases = corpus["cases"]!.AsArray();
            var ids = new HashSet<string>(); var outcomes = new JsonArray(); var categories = new Dictionary<string, int>();
            int passed = 0, failed = 0;
            foreach (JsonNode? item in cases)
            {
                JsonObject test = item!.AsObject(); string id = test["id"]!.GetValue<string>(); string category = test["category"]!.GetValue<string>();
                if (!ids.Add(id)) throw new InvalidDataException("Duplicate case ID: " + id);
                categories[category] = categories.TryGetValue(category, out int count) ? count + 1 : 1;
                try
                {
                    JsonObject input = Expand(corpus["snapshots"]!.AsObject(), test["input"]!.AsObject());
                    JsonNode expected = Expand(corpus["reports"]!.AsObject(), test["expected"]!.AsObject());
                    JsonNode actual = Normalize(CapabilityEvaluator.Evaluate(Snapshot(input)));
                    if (!JsonNode.DeepEquals(expected, actual)) throw new InvalidDataException("Exact report mismatch");
                    outcomes.Add(new JsonObject { ["id"] = id, ["outcome"] = "passed" }); passed++;
                }
                catch (Exception ex) { outcomes.Add(new JsonObject { ["id"] = id, ["outcome"] = "failed", ["reason"] = ex.Message }); failed++; }
            }
            JsonObject categoryObject = new(); foreach (var pair in categories) categoryObject[pair.Key] = pair.Value;
            var result = new JsonObject
            {
                ["schemaVersion"] = corpus["schemaVersion"]!.GetValue<int>(),
                ["sourceCommit"] = Git(root, "rev-parse HEAD"),
                ["dirty"] = Git(root, "status --porcelain").Length != 0,
                ["hashes"] = Hashes(root),
                ["total"] = cases.Count,
                ["passed"] = passed,
                ["failed"] = failed,
                ["unsupported"] = 0,
                ["skipped"] = 0,
                ["categoryCounts"] = categoryObject,
                ["outcomes"] = outcomes,
                ["nativeTestCount"] = nativeTestCount,
                ["complete"] = cases.Count > 0 && failed == 0
            };
            string output = args.Length == 1 ? args[0] : Path.Combine(Directory.GetCurrentDirectory(), "capability-conformance-report.json");
            File.WriteAllText(output, result.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
            Console.WriteLine(result.ToJsonString()); return failed == 0 ? 0 : 1;
        }
        catch (Exception ex) { Console.Error.WriteLine(ex); return 1; }
    }

    private static CapabilitySnapshot Snapshot(JsonObject node)
    {
        CapabilityC7? c7 = null;
        if (node["c7"] is JsonObject c) c7 = new CapabilityC7(Truth(c["bondingSupported"]), Truth(c["featureMayChangeOverLifetime"]));
        var values = new List<CapabilityCharacteristic>();
        foreach (JsonNode? item in node["characteristics"]!.AsArray()) { JsonObject x = item!.AsObject(); values.Add(new CapabilityCharacteristic(x["uuid"]!.GetValue<string>(), (ushort)x["properties"]!.GetValue<int>(), x["readState"]!.GetValue<int>(), x["reason"]!.GetValue<int>(), Convert.FromHexString(x["bytes"]!.GetValue<string>()))); }
        return new CapabilitySnapshot(node["discovery"]!.GetValue<int>(), node["scope"]!.GetValue<int>(), node["generation"]!.GetValue<uint>(), values, c7);
    }
    private static bool? Truth(JsonNode? n) { int value = n!.GetValue<int>(); return value == 0 ? null : value == 1 ? false : true; }

    private static int RunNativeImmutabilityChecks()
    {
        byte[] source = Convert.FromHexString("0000000000000000");
        var feature = new CapabilityCharacteristic("00002acc00001000800000805f9b34fb", 2, 1, 0, source);
        var snapshot = new CapabilitySnapshot(2, 1, 9, new[] { feature }, new CapabilityC7(false, false));
        source[0] = 0xff;
        CapabilityReport report = CapabilityEvaluator.Evaluate(snapshot);
        if (report.Feature.MachineRaw != 0) throw new InvalidDataException("Snapshot did not retain input bytes.");

        byte[] exposed = feature.Bytes;
        exposed[0] = 0xff;
        if (CapabilityEvaluator.Evaluate(snapshot).Feature.MachineRaw != 0)
            throw new InvalidDataException("Characteristic bytes getter exposed mutable backing storage.");

        byte[] observed = report.Observations[0].RawBytes;
        observed[0] = 0xff;
        if (report.Observations[0].RawBytes[0] != 0)
            throw new InvalidDataException("Observation raw bytes getter exposed mutable backing storage.");

        try { report.Presence[0] = 99; }
        catch (NotSupportedException) { return 4; }
        throw new InvalidDataException("Report collections must reject mutation.");
    }

    private static JsonObject Normalize(CapabilityReport r)
    {
        var ranges = new JsonArray(); foreach (var x in r.Ranges) ranges.Add(new JsonArray(x.Presence, x.Decode, N(x.InputIndex), x.Value == null ? null : new JsonArray(x.Value.Kind, x.Value.Minimum, x.Value.Maximum, x.Value.Increment, x.Value.ScaleDivisor, x.Value.Unit)));
        var operations = new JsonArray(); foreach (var x in r.Operations) operations.Add(new JsonArray(x.Opcode, x.TargetBit, x.OptionalInTable, x.Declaration, x.Prerequisite, x.Reasons));
        var observations = new JsonArray(); foreach (var x in r.Observations) observations.Add(new JsonArray(x.InputIndex, x.Uuid, x.Properties, x.KnownKind, x.ReadState, x.Reason, x.ReadSize));
        var diagnostics = new JsonArray(); foreach (var x in r.Diagnostics) diagnostics.Add(new JsonArray(x.Code, x.KnownKind, N(x.InputIndex)));
        var presence = new JsonArray(); foreach (int x in r.Presence) presence.Add(x);
        var feature = new JsonArray((int)r.Feature.Presence, (int)r.Feature.DecodeState, N(r.Feature.InputIndex),
            r.Feature.MachineRaw, r.Feature.TargetRaw, r.Feature.MachineUnknown, r.Feature.TargetUnknown);
        return new JsonObject { ["generation"] = r.Generation, ["discovery"] = r.Discovery, ["scope"] = r.Scope, ["observationCount"] = r.ObservationCount, ["diagnosticCount"] = r.DiagnosticCount, ["presence"] = presence, ["feature"] = feature, ["ranges"] = ranges, ["operations"] = operations, ["observations"] = observations, ["diagnostics"] = diagnostics };
    }
    private static JsonNode? N(long? value) => value.HasValue ? JsonValue.Create(value.Value) : null;
    private static JsonNode? N(int? value) => value.HasValue ? JsonValue.Create(value.Value) : null;

    private static JsonObject Expand(JsonObject templates, JsonObject specification)
    {
        string template = specification["template"]!.GetValue<string>(); if (templates[template] == null) throw new InvalidDataException("Unknown template: " + template);
        JsonNode root = templates[template]!.DeepClone();
        foreach (JsonNode? editNode in specification["edits"]!.AsArray()) Apply(ref root, editNode!.AsObject());
        return root.AsObject();
    }
    private static void Apply(ref JsonNode root, JsonObject edit)
    {
        var paths = new List<List<object>> { new() }; foreach (JsonNode? segment in edit["path"]!.AsArray()) { var next = new List<List<object>>(); foreach (var path in paths) { if (segment is JsonArray alternatives) foreach (var a in alternatives) { var copy = new List<object>(path); copy.Add(a!.GetValue<int>()); next.Add(copy); } else { var copy = new List<object>(path); copy.Add(Segment(segment!)); next.Add(copy); } } paths = next; }
        string op = edit["op"]?.GetValue<string>() ?? "replace"; if (paths.Count == 0) throw new InvalidDataException("Empty edit selection");
        foreach (var path in paths) EditAt(ref root, path, op, edit["value"]);
    }
    private static void EditAt(ref JsonNode root, List<object> path, string op, JsonNode? value)
    {
        if (path.Count == 0) { if (op != "replace") throw new InvalidDataException("Invalid root edit"); root = value!.DeepClone(); return; }
        if (op == "append") { foreach (var target in Resolve(root, path)) { if (target is not JsonArray array) throw new InvalidDataException("Append requires array"); array.Add(value!.DeepClone()); } return; }
        var parents = new List<JsonNode> { root }; for (int depth = 0; depth < path.Count - 1; depth++) { var next = new List<JsonNode>(); foreach (var parent in parents) { object segment = path[depth]; if (segment is string text && text == "*") { if (parent is not JsonArray array) throw new InvalidDataException("Wildcard requires array"); foreach (var child in array) next.Add(child!); } else next.Add(Child(parent, segment)); } parents = next; }
        object leaf = path[^1]; foreach (var parent in parents) { if (parent is JsonArray all && leaf is string wildcard && wildcard == "*") { if (op != "replace") throw new InvalidDataException("Wildcard only supports replacement"); for (int index = 0; index < all.Count; index++) all[index] = value!.DeepClone(); } else if (parent is JsonObject obj && leaf is string key) { if (!obj.ContainsKey(key)) throw new InvalidDataException("Missing key"); if (op == "remove") obj.Remove(key); else obj[key] = value!.DeepClone(); } else if (parent is JsonArray array && leaf is int index) { if (index < 0 || index >= array.Count) throw new InvalidDataException("Bad index"); if (op == "remove") array.RemoveAt(index); else array[index] = value!.DeepClone(); } else throw new InvalidDataException("Invalid edit target"); }
    }
    private static object Segment(JsonNode node) { JsonValue value = (JsonValue)node; if (value.TryGetValue<int>(out int number)) return number; return value.GetValue<string>(); }
    private static IEnumerable<JsonNode> Resolve(JsonNode root, List<object> path) { var nodes = new List<JsonNode> { root }; foreach (var segment in path) { var next = new List<JsonNode>(); foreach (var node in nodes) { if (segment is string text && text == "*") { if (node is not JsonArray a) throw new InvalidDataException("Wildcard requires array"); foreach (var child in a) next.Add(child!); } else next.Add(Child(node, segment)); } nodes = next; } return nodes; }
    private static JsonNode Child(JsonNode parent, object key) => parent is JsonObject o && key is string s && o[s] != null ? o[s]! : parent is JsonArray a && key is int i && i < a.Count && a[i] != null ? a[i]! : throw new InvalidDataException("Bad edit path");
    private static string FindRoot() { for (var d = new DirectoryInfo(Directory.GetCurrentDirectory()); d != null; d = d.Parent) if (Directory.Exists(Path.Combine(d.FullName, "shared"))) return d.FullName; throw new DirectoryNotFoundException("Repository root not found."); }
    private static string Git(string root, string arguments)
    {
        var start = new ProcessStartInfo("git", arguments)
        {
            WorkingDirectory = root,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false
        };
        using Process process = Process.Start(start) ?? throw new InvalidOperationException("Could not start Git.");
        string text = process.StandardOutput.ReadToEnd().Trim();
        string error = process.StandardError.ReadToEnd().Trim();
        process.WaitForExit();
        if (process.ExitCode != 0)
            throw new InvalidOperationException("Git identity command failed: " + error);
        return text;
    }
    private static JsonObject Hashes(string root) { var result = new JsonObject(); foreach (string relative in new[] { "shared/conformance/capabilities/v1/schema.json", "shared/conformance/capabilities/v1/vectors.json", "shared/conformance/capabilities/README.md", "shared/protocol/capability-discovery.md" }) using (var sha = SHA256.Create()) using (var file = File.OpenRead(Path.Combine(root, relative))) result[relative] = Convert.ToHexString(sha.ComputeHash(file)).ToLowerInvariant(); return result; }
}
