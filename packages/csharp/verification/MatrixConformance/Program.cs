using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using DeanCochran.Ftms;

var root = new DirectoryInfo(Environment.CurrentDirectory);
while (root != null && !Directory.Exists(Path.Combine(root.FullName, "shared/conformance"))) root = root.Parent;
if (root == null) throw new DirectoryNotFoundException("Run inside the FTMS checkout.");
string[] identityFiles = { "shared/conformance/measurement-matrix/v1/layouts.json", "shared/conformance/measurement-matrix/v1/README.md" };
using var document = JsonDocument.Parse(File.ReadAllText(Path.Combine(root.FullName, identityFiles[0])));
if (document.RootElement.GetProperty("contract").GetString() != "ftms-measurement-matrix-v1") throw new InvalidDataException("Unknown matrix contract.");
int structures = 0, sentinels = 0, reserved = 0, prefixes = 0, configurations = 0;
int[] perKind = new int[6];
var failures = new List<object>();
int passed = 0, failed = 0;
void Check(string id, Action action)
{
    try { action(); passed++; }
    catch (Exception error) { failures.Add(new { id, reason = error.ToString() }); failed++; }
}
foreach (var layout in document.RootElement.GetProperty("layouts").EnumerateArray())
{
    int kind = layout.GetProperty("kind").GetInt32(), flagBytes = layout.GetProperty("flagBytes").GetInt32(), groups = layout.GetProperty("optionalGroups").GetInt32();
    for (int variant = 0; variant < (kind is 0 or 1 or 4 or 5 ? 2 : 1); variant++)
    {
        configurations++;
        var format = new MeasurementFormat(variant == 1 && kind != 0 ? ResistanceFormat.SInt16Tenths : ResistanceFormat.UInt8Whole,
            variant == 1 && kind == 0 ? TreadmillPaceFormat.UInt8Legacy : TreadmillPaceFormat.UInt16);
        var fields = layout.GetProperty("fields").EnumerateArray().Select(row =>
        {
            int index = row[2].GetInt32();
            int width = variant == 1 && index == 21 ? 2 : variant == 1 && kind == 0 && index is 7 or 8 ? 1 : row[1].GetInt32();
            return new Field(row[0].GetInt32(), width, index, row[3].GetInt32() == 1 || variant == 1 && index == 21, row[4].GetInt32() == 1);
        }).ToArray();

        Golden Build(uint flags, int sentinelField = -1, int prefix = int.MaxValue)
        {
            var bytes = new List<byte>();
            for (int i = 0; i < flagBytes; i++) bytes.Add((byte)(flags >> (i * 8)));
            var values = new Dictionary<MeasurementField, int?>();
            bool truncated = false;
            foreach (var field in fields)
            {
                if (field.Bit == 0 ? (flags & 1) != 0 : (flags & (1u << field.Bit)) == 0) continue;
                if (bytes.Count + field.Width > prefix) { truncated = true; break; }
                bool sentinel = field.Index == sentinelField;
                int value = sentinel ? field.Signed ? 32767 : (1 << (8 * field.Width)) - 1 : (field.Index + 1) * (field.Signed ? -1 : 1);
                values.Add((MeasurementField)field.Index, sentinel ? null : value);
                for (int i = 0; i < field.Width; i++) bytes.Add((byte)(value >> (i * 8)));
            }
            return new Golden(bytes.ToArray(), values, truncated);
        }

        void Decode(uint flags, byte[] bytes, Golden expected, bool rfu = false)
        {
            var actual = MeasurementCodec.Decode((MeasurementKind)kind, bytes, format);
            if (actual.Flags != flags || actual.Kind != (MeasurementKind)kind || actual.MoreData != ((flags & 1) != 0)
                || actual.Backward != (kind == 1 && (flags & 0x8000) != 0) || actual.Diagnostics.Truncated != expected.Truncated
                || actual.Diagnostics.TrailingBytes || actual.Diagnostics.ReservedFlags != rfu || actual.BytesRead != expected.Bytes.Length
                || actual.Fields.Count != expected.Fields.Count) throw new InvalidDataException("Decoded structure/diagnostics mismatch.");
            foreach (var pair in expected.Fields)
                if (!actual.Fields.TryGetValue(pair.Key, out var value) || value != pair.Value) throw new InvalidDataException($"Field {pair.Key} mismatch.");
        }

        void Both(uint flags, int sentinel = -1)
        {
            var expected = Build(flags, sentinel);
            Decode(flags, expected.Bytes, expected);
            var input = new Measurement((MeasurementKind)kind, flags, expected.Fields, format);
            if (!expected.Bytes.AsSpan().SequenceEqual(MeasurementCodec.Encode(input))) throw new InvalidDataException("Encoded bytes mismatch.");
        }

        for (int subset = 0; subset < (1 << groups); subset++)
        for (int more = 0; more < 2; more++)
        for (int backward = 0; backward < (kind == 1 ? 2 : 1); backward++)
        {
            uint flags = (uint)(subset << 1 | more | backward << 15);
            Check($"kind={kind}/variant={variant}/flags={flags}", () => Both(flags)); structures++; perKind[kind]++;
        }
        uint all = (uint)(((1 << groups) - 1) << 1);
        foreach (var field in fields.Where(f => f.Sentinel))
        { Check($"kind={kind}/variant={variant}/sentinel={field.Index}", () => Both(all, field.Index)); sentinels++; }
        var full = Build(all);
        int expectedLength = layout.GetProperty("fullLength").GetInt32() + (variant == 1 ? kind == 0 ? -2 : 1 : 0);
        if (full.Bytes.Length != expectedLength) throw new InvalidDataException("Fixture field widths do not match fullLength.");
        for (int length = 0; length < full.Bytes.Length; length++)
        {
            int size = length;
            Check($"kind={kind}/variant={variant}/prefix={size}", () =>
            {
                if (size < flagBytes)
                {
                    if (MeasurementCodec.TryDecode((MeasurementKind)kind, full.Bytes.AsSpan(0, size), format).Error != FtmsError.Length)
                        throw new InvalidDataException("Short flags must reject.");
                }
                else Decode(all, full.Bytes.AsSpan(0, size).ToArray(), Build(all, prefix: size));
            }); prefixes++;
        }
        for (int bit = kind == 1 ? 16 : groups + 1; bit < flagBytes * 8; bit++)
        {
            uint flags = all | (1u << bit);
            Check($"kind={kind}/variant={variant}/rfu={bit}", () =>
            {
                var golden = Build(flags);
                Decode(flags, golden.Bytes, golden, true);
                try { MeasurementCodec.Encode(new Measurement((MeasurementKind)kind, flags, golden.Fields, format)); }
                catch (FtmsException) { return; }
                throw new InvalidDataException("RFU encoder must reject even without diagnostics.");
            }); reserved++;
        }
    }
}
string Git(string command)
{
    using var process = Process.Start(new ProcessStartInfo("git", command) { WorkingDirectory = root.FullName, RedirectStandardOutput = true })!;
    string text = process.StandardOutput.ReadToEnd().Trim(); process.WaitForExit();
    if (process.ExitCode != 0) throw new InvalidOperationException("Git identity unavailable.");
    return text;
}
bool accounting = structures == 181760 && sentinels == 46 && reserved == 47 && prefixes == 315 && configurations == 10;
var report = new
{
    contract = "ftms-measurement-matrix-v1", sourceCommit = Git("rev-parse HEAD"), dirty = Git("status --porcelain").Length != 0,
    hashes = identityFiles.ToDictionary(f => f, f => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(Path.Combine(root.FullName, f)))).ToLowerInvariant()),
    structures, structuralDirections = structures * 2, perKind, sentinels, reserved, prefixes, configurations,
    passed, failed, unsupported = 0, skipped = 0, failures, accountingComplete = accounting, complete = accounting && failed == 0
};
string output = args.Length == 1 ? args[0] : "matrix-conformance.json";
File.WriteAllText(output, JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }) + "\n");
Console.WriteLine($"Matrix: {structures} structures, {sentinels} sentinels, {reserved} RFU, {prefixes} prefixes; failed={failed}.");
return report.complete ? 0 : 1;

internal sealed record Field(int Bit, int Width, int Index, bool Signed, bool Sentinel);
internal sealed record Golden(byte[] Bytes, Dictionary<MeasurementField, int?> Fields, bool Truncated);
