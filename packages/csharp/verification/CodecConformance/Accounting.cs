using System.Text.Json;
using System.Text.Json.Nodes;

internal static partial class Program
{
    private sealed record ExpectedCase(string Category, string Id, HashSet<string> Directions);
    private static readonly Dictionary<string, ExpectedCase> ExpectedCases = new(StringComparer.Ordinal);
    private static bool DiscoveryComplete;
    private static string CaseKey(string category, string id) => category + "\u001f" + id;

    // Discovery precedes all codec execution, so an adapter exception cannot erase
    // later fixture IDs from the denominator or turn a partial run into success.
    private static void Discover(string root)
    {
        foreach (var suite in new[] { "values", "controls", "measurements", "statuses", "compatibility", "inspection", "v1" })
        {
            string relative = suite == "v1" ? "shared/conformance/v1/vectors.json"
                : suite == "inspection" ? "shared/conformance/inspection/v1/fixtures.json"
                : $"shared/conformance/{suite}/v1/vectors.json";
            using var document = Load(root, relative);
            RequireSchemaVersion(document.RootElement, suite);
            string[] categories = suite switch
            {
                "v1" => new[] { "features", "ranges", "controls", "controlResponses", "measurements", "statuses", "diagnostics" },
                "controls" => new[] { "requests", "responses", "invalid" },
                "statuses" => new[] { "machine", "training" },
                _ => new[] { "cases" }
            };
            var ids = new HashSet<string>(StringComparer.Ordinal);
            foreach (string category in categories)
            foreach (var fixture in document.RootElement.GetProperty(category).EnumerateArray())
            {
                string id = fixture.GetProperty("id").GetString()!;
                if (string.IsNullOrWhiteSpace(id) || !ids.Add(id)) throw new InvalidDataException($"Duplicate/empty {suite} ID: {id}");
                string reportCategory = suite switch
                {
                    "v1" => category,
                    "values" => fixture.GetProperty("operation").GetString() switch { "features" => "values/features", "range" => "values/ranges", _ => throw new InvalidDataException("Unknown value operation") },
                    "compatibility" => fixture.GetProperty("area").GetString() switch { "measurement" => "compatibility/measurements", "range" => "compatibility/ranges", _ => throw new InvalidDataException("Unknown compatibility area") },
                    "controls" or "statuses" => suite + "/" + category,
                    _ => suite
                };
                var directions = new HashSet<string>(StringComparer.Ordinal);
                if (suite == "v1")
                {
                    if (category == "controls") directions.Add("encode");
                    else if (category == "diagnostics")
                    {
                        directions.Add("diagnostics");
                        if (fixture.TryGetProperty("expectedMetrics", out _) || fixture.TryGetProperty("expectedStatus", out _)) directions.Add("decode");
                    }
                    else directions.Add("decode");
                }
                else if (suite == "inspection") directions.Add("inspect");
                else
                {
                    directions.Add("decode");
                    if (category != "invalid" && (!fixture.TryGetProperty("encode", out var encode) || encode.GetBoolean())) directions.Add("encode");
                }
                ExpectedCases.Add(CaseKey(reportCategory, id), new ExpectedCase(reportCategory, id, directions));
            }
        }
        DiscoveryComplete = true;
    }

    private static JsonArray ReconcileCases()
    {
        var cases = new JsonArray();
        foreach (var expected in ExpectedCases.Values)
        {
            var actual = Outcomes.Where(value => value["category"]!.GetValue<string>() == expected.Category
                && value["id"]!.GetValue<string>() == expected.Id).ToList();
            foreach (string direction in expected.Directions)
            {
                if (actual.Any(value => value["direction"]!.GetValue<string>() == direction)) continue;
                Record(expected.Category, expected.Id, direction, "skipped", "Registered fixture direction was not executed; inspect runner failures.");
                actual.Add(Outcomes[^1]);
            }
            string result = actual.Any(v => v["outcome"]!.GetValue<string>() == "failed") ? "failed"
                : actual.Any(v => v["outcome"]!.GetValue<string>() == "unsupported") ? "unsupported"
                : actual.Any(v => v["outcome"]!.GetValue<string>() == "skipped") ? "skipped" : "passed";
            cases.Add(Obj(("category", expected.Category), ("id", expected.Id), ("outcome", result),
                ("requiredDirections", JsonSerializer.SerializeToNode(expected.Directions.OrderBy(v => v, StringComparer.Ordinal))),
                ("nonPassReasons", JsonSerializer.SerializeToNode(actual.Where(v => v["outcome"]!.GetValue<string>() != "passed").Select(v => v["reason"]?.GetValue<string>())))));
        }
        return cases;
    }
}
