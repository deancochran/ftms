using System.Text.Json;
using System.Text.Json.Nodes;
using DeanCochran.Ftms;

internal static partial class Program
{
    private static readonly string[] LegacyMachineFeatures =
    [
        "averageSpeedSupported", "cadenceSupported", "totalDistanceSupported", "inclinationSupported",
        "elevationGainSupported", "paceSupported", "stepCountSupported", "resistanceLevelSupported",
        "strideCountSupported", "expendedEnergySupported", "heartRateMeasurementSupported",
        "metabolicEquivalentSupported", "elapsedTimeSupported", "remainingTimeSupported",
        "powerMeasurementSupported", "forceOnBeltSupported", "userDataRetentionSupported"
    ];

    private static readonly string[] LegacyTargetFeatures =
    [
        "speedTargetSettingSupported", "inclinationTargetSettingSupported", "resistanceTargetSettingSupported",
        "powerTargetSettingSupported", "heartRateTargetSettingSupported", "targetedExpendedEnergySupported",
        "targetedStepNumberSupported", "targetedStrideNumberSupported", "targetedDistanceSupported",
        "targetedTrainingTimeSupported", "targetedTimeTwoHRZonesSupported", "targetedTimeThreeHRZonesSupported",
        "targetedTimeFiveHRZonesSupported", "indoorBikeSimulationSupported", "wheelCircumferenceSupported",
        "spinDownControlSupported", "targetedCadenceSupported"
    ];

    private static void RunLegacyConformance(string root)
    {
        using var document = Load(root, "shared/conformance/v1/vectors.json");
        if (document.RootElement.GetProperty("schemaVersion").GetInt32() != 1)
        {
            throw new InvalidDataException("codec-v1 schemaVersion must be 1");
        }

        var categories = new[] { "features", "ranges", "controls", "controlResponses", "measurements", "statuses", "diagnostics" };
        var ids = new HashSet<string>(StringComparer.Ordinal);
        var count = 0;
        foreach (var category in categories)
        {
            foreach (var fixture in document.RootElement.GetProperty(category).EnumerateArray())
            {
                var id = fixture.GetProperty("id").GetString()!;
                if (!ids.Add(id))
                {
                    throw new InvalidDataException($"Duplicate codec-v1 ID: {id}");
                }

                count++;
                RunLegacyCase(category, id, fixture);
            }
        }

        if (count == 0)
        {
            throw new InvalidDataException("codec-v1 must not be empty");
        }
    }

    private static void RunLegacyCase(string category, string id, JsonElement fixture)
    {
        try
        {
            switch (category)
            {
                case "features":
                    LegacyFeatures(category, id, fixture);
                    break;
                case "ranges":
                    LegacyRange(category, id, fixture);
                    break;
                case "controls":
                    Check(category, id, "encode", Bytes(fixture.GetProperty("expectedBytes")), LegacyRequest(fixture.GetProperty("request")));
                    break;
                case "controlResponses":
                    LegacyResponse(category, id, fixture);
                    break;
                case "measurements":
                case "statuses":
                case "diagnostics":
                    LegacyParsed(category, id, fixture);
                    break;
                default:
                    throw new InvalidDataException($"Unknown codec-v1 category {category}");
            }
        }
        catch (Exception exception)
        {
            Record(category, id, "decode", "failed", exception.ToString());
        }
    }

    private static void LegacyFeatures(string category, string id, JsonElement fixture)
    {
        var actual = LegacyFeatures(FeatureCodec.Decode(Bytes(fixture.GetProperty("bytes"))));
        if (fixture.TryGetProperty("expected", out var expected))
        {
            CheckObject(category, id, "decode", actual, expected);
            return;
        }

        var expectedTrue = fixture.GetProperty("expectedTrue").EnumerateArray()
            .Select(value => value.GetString()!).OrderBy(value => value, StringComparer.Ordinal).ToArray();
        var actualTrue = actual.Where(pair => pair.Value!.GetValue<bool>()).Select(pair => pair.Key)
            .OrderBy(value => value, StringComparer.Ordinal).ToArray();
        CheckObject(category, id, "decode", JsonSerializer.SerializeToNode(actualTrue)!, JsonSerializer.SerializeToNode(expectedTrue)!);
    }

    private static JsonObject LegacyFeatures(Features features)
    {
        var output = new JsonObject();
        for (var bit = 0; bit < LegacyMachineFeatures.Length; bit++)
        {
            output[LegacyMachineFeatures[bit]] = features.Machine(bit);
        }

        for (var bit = 0; bit < LegacyTargetFeatures.Length; bit++)
        {
            output[LegacyTargetFeatures[bit]] = features.Target(bit);
        }

        output["supportsERG"] = features.Target(3);
        output["supportsSIM"] = features.Target(13);
        output["supportsResistance"] = features.Target(2);
        return output;
    }

    private static void LegacyRange(string category, string id, JsonElement fixture)
    {
        try
        {
            var range = RangeCodec.Decode(Kind(fixture.GetProperty("kind").GetString()!), Bytes(fixture.GetProperty("bytes")));
            if (fixture.TryGetProperty("expectedError", out var expectedError))
            {
                CheckSubset(category, id, "decode", Obj(("ok", true), ("value", LegacyRange(range))),
                    Obj(("ok", false), ("error", Obj(("code", expectedError.GetString()!)))));
            }
            else
            {
                var expected = JsonNode.Parse(fixture.GetProperty("expected").GetRawText())!.AsObject();
                expected["kind"] = fixture.GetProperty("kind").GetString();
                CheckObject(category, id, "decode", LegacyRange(range), expected);
            }
        }
        catch (FtmsException exception)
        {
            var actual = Obj(("ok", false), ("error", Obj(("code", exception.Code))));
            CheckSubset(category, id, "decode", actual,
                Obj(("ok", false), ("error", Obj(("code", fixture.GetProperty("expectedError").GetString()!)))));
        }
    }

    private static JsonObject LegacyRange(SupportedRange range)
    {
        var unit = range.Unit switch
        {
            RangeUnit.KilometresPerHour => "km/h",
            RangeUnit.Percent => "percent",
            RangeUnit.Level => "level",
            RangeUnit.BeatsPerMinute => "bpm",
            RangeUnit.Watts => "watts",
            _ => throw new InvalidDataException($"Unknown range unit {range.Unit}")
        };
        return Obj(("kind", KindName(range.Kind)), ("min", range.MinimumValue),
            ("max", range.MaximumValue), ("increment", range.IncrementValue), ("unit", unit));
    }

    private static byte[] LegacyRequest(JsonElement request)
    {
        var operation = request.GetProperty("op").GetString()!;
        var opcode = Array.IndexOf(new[]
        {
            "requestControl", "reset", "setTargetSpeed", "setTargetInclination", "setTargetResistance",
            "setTargetPower", "setTargetHeartRate", "startResume", "stopPause", "setTargetedExpendedEnergy",
            "setTargetedSteps", "setTargetedStrides", "setTargetedDistance", "setTargetedTrainingTime",
            "setTargetedTimeTwoHrZones", "setTargetedTimeThreeHrZones", "setTargetedTimeFiveHrZones",
            "setIndoorBikeSimulation", "setWheelCircumference", "spinDown", "setTargetedCadence"
        }, operation);
        if (opcode < 0)
        {
            throw new InvalidDataException($"Unknown control operation {operation}");
        }

        int Scaled(string name, int scale = 1) => checked((int)(request.GetProperty(name).GetDecimal() * scale));
        int[] operands = opcode switch
        {
            2 => [Scaled("speedKph", 100)],
            3 => [Scaled("inclinationPercent", 10)],
            4 => [Scaled("resistanceLevel", 10)],
            5 => [Scaled("powerWatts")],
            6 => [Scaled("heartRateBpm")],
            8 => [Action(request, "stop", "pause")],
            9 => [Scaled("energyKcal")],
            10 => [Scaled("steps")],
            11 => [Scaled("strides")],
            12 => [Scaled("distanceMeters")],
            13 => [Scaled("seconds")],
            14 or 15 or 16 => request.GetProperty("seconds").EnumerateArray().Select(value => value.GetInt32()).ToArray(),
            17 => [Scaled("windSpeedMps", 1000), Scaled("gradePercent", 100), Scaled("crr", 10000), Scaled("cwKgPerM", 100)],
            18 => [Scaled("circumferenceMm", 10)],
            19 => [Action(request, "start", "ignore")],
            20 => [Scaled("cadenceRpm", 2)],
            _ => []
        };
        return ControlCodec.EncodeRequest(new ControlRequest((byte)opcode, operands));
    }

    private static int Action(JsonElement request, string first, string second) => request.GetProperty("action").GetString() switch
    {
        var action when action == first => 1,
        var action when action == second => 2,
        var action => throw new InvalidDataException($"Unknown action {action}")
    };

    private static void LegacyResponse(string category, string id, JsonElement fixture)
    {
        try
        {
            var response = ControlCodec.DecodeResponse(Bytes(fixture.GetProperty("bytes")));
            if (response.UnknownRequest || response.UnexpectedParameters)
            {
                throw new FtmsException(FtmsError.Kind);
            }
            CheckObject(category, id, "decode", LegacyResponse(response), fixture.GetProperty("expected"));
        }
        catch (FtmsException exception)
        {
            if (exception.Error is not (FtmsError.Length or FtmsError.Kind))
            {
                throw;
            }
            CheckSubset(category, id, "decode", Obj(("ok", false), ("error", Obj(("code", "malformed_response")))),
                Obj(("ok", false), ("error", Obj(("code", fixture.GetProperty("expectedError").GetString()!)))));
        }
    }

    private static JsonObject LegacyResponse(ControlResponse response)
    {
        var name = response.ResultCode switch
        {
            1 => "success",
            2 => "not_supported",
            3 => "invalid_parameter",
            4 => "operation_failed",
            5 => "control_not_permitted",
            _ => $"unknown_0x{response.ResultCode:x2}"
        };
        JsonObject parameter = response.SpinDownStartSpeed.HasValue
            ? Obj(("kind", "spin_down_speeds"), ("targetSpeedLowKph", response.SpinDownStartSpeed.Value / 100.0),
                ("targetSpeedHighKph", response.SpinDownEndSpeed!.Value / 100.0))
            : Obj(("kind", "none"));
        var issues = new JsonArray();
        if (response.UnknownResult) issues.Add("reserved_value");
        return Obj(("requestOpCode", response.RequestOpcode), ("resultCode", response.ResultCode),
            ("resultCodeName", name), ("success", response.ResultCode == 1), ("parameter", parameter),
            ("issues", issues));
    }

    private static void LegacyParsed(string category, string id, JsonElement fixture)
    {
        var parsed = LegacyParse(fixture.GetProperty("characteristicUuid").GetString()!, Bytes(fixture.GetProperty("bytes")));
        if (fixture.TryGetProperty("expectedMetrics", out var expectedMetrics))
        {
            CheckMetrics(category, id, parsed.Metrics, expectedMetrics);
        }
        if (fixture.TryGetProperty("expectedStatus", out var expectedStatus))
        {
            CheckSubset(category, id, "decode", parsed.Status, JsonNode.Parse(expectedStatus.GetRawText())!);
        }
        if (category == "diagnostics")
        {
            CheckObject(category, id, "diagnostics", JsonValue.Create(parsed.Truncated)!, fixture.GetProperty("expectedTruncated"));
            foreach (var issue in fixture.GetProperty("expectedIssues").EnumerateArray())
            {
                if (!parsed.Issues.Contains(issue.GetString()!))
                {
                    Record(category, id, "diagnostics", "failed", $"Missing diagnostic {issue.GetString()}");
                }
            }
            if (fixture.TryGetProperty("expectedStatusCode", out var code))
            {
                CheckObject(category, id, "diagnostics", parsed.Status["code"]!, code);
            }
        }
    }

    private sealed record LegacyParsedValue(JsonObject Metrics, JsonObject Status, bool Truncated, HashSet<string> Issues);

    private static LegacyParsedValue LegacyParse(string uuid, byte[] bytes)
    {
        var measurementUuids = new[] { "2acd", "2ace", "2acf", "2ad0", "2ad1", "2ad2" }
            .Select(value => $"0000{value}-0000-1000-8000-00805f9b34fb").ToArray();
        var index = Array.IndexOf(measurementUuids, uuid);
        if (index >= 0)
        {
            var measurement = MeasurementCodec.Decode((MeasurementKind)index, bytes);
            var issues = new HashSet<string>();
            Add(issues, measurement.MoreData, "more_data"); Add(issues, measurement.Diagnostics.Truncated, "truncated");
            Add(issues, measurement.Diagnostics.TrailingBytes, "trailing_bytes"); Add(issues, measurement.Diagnostics.ReservedFlags, "reserved_flags");
            Add(issues, measurement.Fields.Any(pair => !pair.Value.HasValue), "unavailable");
            return new LegacyParsedValue(LegacyMetrics(measurement), new JsonObject(), measurement.Diagnostics.Truncated, issues);
        }
        if (uuid == "00002ad3-0000-1000-8000-00805f9b34fb")
        {
            var status = StatusCodec.DecodeTraining(bytes); var issues = new HashSet<string>(status.Diagnostics.Issues);
            var report = Obj(("code", status.Diagnostics.Truncated ? null : status.Code),
                ("label", status.Code == 13 ? "manual_mode" : $"unmapped_{status.Code}"),
                ("details", Obj(("kind", "training_status"), ("flags", status.Flags), ("stringPresent", status.TextPresent),
                    ("extendedStringPresent", status.ExtendedString), ("trainingStatusString", status.TextPresent ? status.Text : null))));
            return new LegacyParsedValue(new JsonObject(), report, status.Diagnostics.Truncated, issues);
        }
        if (uuid != "00002ada-0000-1000-8000-00805f9b34fb") throw new InvalidDataException($"Unsupported UUID {uuid}");
        var machine = StatusCodec.DecodeMachine(bytes); var machineIssues = new HashSet<string>(machine.Diagnostics.Issues);
        var (label, details) = machine.Opcode == 5 && machine.Parameter?.Opcode == 2
            ? ("target_speed_changed", Obj(("kind", "speed"), ("speedKph", machine.Parameter.Operands[0] / 100.0)))
            : machine.Opcode == 18 && machine.Parameter?.Opcode == 17
                ? ("indoor_bike_simulation_parameters_changed", Obj(("kind", "simulation"), ("windSpeedMps", machine.Parameter.Operands[0] / 1000.0), ("gradePercent", machine.Parameter.Operands[1] / 100.0), ("crr", machine.Parameter.Operands[2] / 10000.0), ("cwKgPerM", machine.Parameter.Operands[3] / 100.0)))
                : machine.Opcode == 255 && machine.Parameter is null ? ("control_permission_lost", Obj(("kind", "none"))) : ($"unmapped_{machine.Opcode}", Obj(("kind", "unmapped")));
        var machineReport = Obj(("code", machine.Diagnostics.Truncated && machine.Diagnostics.Issues.Contains("unknown_opcode") && machine.Opcode == 0 ? null : machine.Opcode), ("label", label), ("details", details));
        return new LegacyParsedValue(new JsonObject(), machineReport, machine.Diagnostics.Truncated, machineIssues);
    }

    private static JsonObject LegacyMetrics(Measurement measurement)
    {
        var names = new[] { "speedMps", "averageSpeedMps", "distanceMeters", "inclinationPercent", "rampAngleDegrees", "positiveElevationGainMeters", "negativeElevationGainMeters", "instantaneousPaceSecondsPer500m", "averagePaceSecondsPer500m", "energyKcal", "energyPerHourKcal", "energyPerMinuteKcal", "hrBpm", "metabolicEquivalent", "elapsedTimeSeconds", "remainingTimeSeconds", "forceOnBeltNewtons", "powerWatts", "stepRateSpm", "averageStepRateSpm", "strideCount", "resistanceLevel", "averagePowerWatts", "floorCount", "stepCount", "strokeRateSpm", "strokeCount", "averageStrokeRateSpm", "cadenceRpm", "averageCadenceRpm" };
        var metrics = new JsonObject();
        for (var field = 0; field < names.Length; field++)
        {
            if (!measurement.Fields.TryGetValue((MeasurementField)field, out var raw)) continue;
            var divisor = field is 0 or 1 ? 360 : field is 3 or 4 or 13 ? 10 :
                field is 5 or 6 && measurement.Kind == MeasurementKind.Treadmill ? 10 :
                field == 20 && measurement.Kind == MeasurementKind.CrossTrainer ? 10 : field is 25 or 27 or 28 or 29 ? 2 : 1;
            metrics[names[field]] = raw.HasValue ? raw.Value / (double)divisor : null;
        }
        if (measurement.Diagnostics.Truncated)
        {
            foreach (var field in SelectedUnreadFields(measurement)) metrics[names[field]] = null;
        }
        if (measurement.Kind == MeasurementKind.CrossTrainer) metrics["movementDirection"] = measurement.Backward ? "backward" : "forward";
        return metrics;
    }

    private static IEnumerable<int> SelectedUnreadFields(Measurement measurement)
    {
        var groups = new[]
        {
            new[] { new[]{0},new[]{1},new[]{2},new[]{3,4},new[]{5,6},new[]{7},new[]{8},new[]{9,10,11},new[]{12},new[]{13},new[]{14},new[]{15},new[]{16,17} },
            new[] { new[]{0},new[]{1},new[]{2},new[]{18,19},new[]{20},new[]{5,6},new[]{3,4},new[]{21},new[]{17},new[]{22},new[]{9,10,11},new[]{12},new[]{13},new[]{14},new[]{15} },
            new[] { new[]{23,24},new[]{18},new[]{19},new[]{5},new[]{9,10,11},new[]{12},new[]{13},new[]{14},new[]{15} },
            new[] { new[]{23},new[]{18},new[]{19},new[]{5},new[]{20},new[]{9,10,11},new[]{12},new[]{13},new[]{14},new[]{15} },
            new[] { new[]{25,26},new[]{27},new[]{2},new[]{7},new[]{8},new[]{17},new[]{22},new[]{21},new[]{9,10,11},new[]{12},new[]{13},new[]{14},new[]{15} },
            new[] { new[]{0},new[]{1},new[]{28},new[]{29},new[]{2},new[]{21},new[]{17},new[]{22},new[]{9,10,11},new[]{12},new[]{13},new[]{14},new[]{15} }
        };
        foreach (var (group, bit) in groups[(int)measurement.Kind].Select((group, bit) => (group, bit)))
        {
            var selected = bit == 0 ? (measurement.Flags & 1) == 0 : (measurement.Flags & (1u << bit)) != 0;
            if (selected) foreach (var field in group) if (!measurement.Fields.ContainsKey((MeasurementField)field)) yield return field;
        }
    }

    private static void CheckSubset(string category, string id, string direction, JsonNode actual, JsonNode expected)
    {
        assertions++;
        if (Subset(actual, expected, out var reason)) Record(category, id, direction, "passed", null);
        else Record(category, id, direction, "failed", reason);
    }

    private static void CheckMetrics(string category, string id, JsonObject actual, JsonElement expected)
    {
        assertions++;
        foreach (var expectedMetric in expected.EnumerateObject())
        {
            if (!actual.TryGetPropertyValue(expectedMetric.Name, out var actualValue)) { Record(category, id, "decode", "failed", $"Missing metric {expectedMetric.Name}"); return; }
            if (expectedMetric.Value.ValueKind == JsonValueKind.Number)
            {
                if (actualValue is not JsonValue number || !number.TryGetValue<double>(out var value) || !double.IsFinite(value) || Math.Abs(value - expectedMetric.Value.GetDouble()) >= 0.005) { Record(category, id, "decode", "failed", $"Metric {expectedMetric.Name} outside strict tolerance"); return; }
            }
            else if (!Exact(actualValue, JsonNode.Parse(expectedMetric.Value.GetRawText()), out var reason)) { Record(category, id, "decode", "failed", $"Metric {expectedMetric.Name}: {reason}"); return; }
        }
        Record(category, id, "decode", "passed", null);
    }

    private static bool Subset(JsonNode? actual, JsonNode? expected, out string reason)
    {
        if (actual is null || expected is null) { reason = "null mismatch"; return actual is null && expected is null; }
        if (expected is JsonObject expectedObject)
        {
            if (actual is not JsonObject actualObject) { reason = "expected object"; return false; }
            foreach (var property in expectedObject)
            {
                if (!actualObject.ContainsKey(property.Key)) { reason = property.Key + ".missing"; return false; }
                if (!Subset(actualObject[property.Key], property.Value, out reason)) { reason = property.Key + "." + reason; return false; }
            }
            reason = ""; return true;
        }
        if (expected is JsonArray expectedArray)
        {
            if (actual is not JsonArray actualArray || actualArray.Count != expectedArray.Count) { reason = "array mismatch"; return false; }
            for (var index = 0; index < expectedArray.Count; index++) if (!Subset(actualArray[index], expectedArray[index], out reason)) { reason = $"[{index}].{reason}"; return false; }
            reason = ""; return true;
        }
        return Exact(actual, expected, out reason);
    }

    private static void Add(ISet<string> issues, bool condition, string issue) { if (condition) issues.Add(issue); }
}
