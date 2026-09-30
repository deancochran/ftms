using System.Reflection.Metadata;
using System.Text;
using System.Text.Json;

// Audit the actual portable PDBs from the .snupkg, not build settings alone.
if (args.Length != 1) throw new ArgumentException("Supply the extracted symbol package directory.");
var sourceLinkId = new Guid("CC110556-A091-4D38-9FEC-25AB9A351A6A");
var reports = new List<object>();
foreach (var tfm in new[] { "netstandard2.1", "net10.0" })
{
    var path = Path.Combine(args[0], "lib", tfm, "DeanCochran.Ftms.pdb");
    using var stream = File.OpenRead(path);
    using var provider = MetadataReaderProvider.FromPortablePdbStream(stream);
    var reader = provider.GetMetadataReader();
    string? sourceLink = null;
    foreach (var handle in reader.CustomDebugInformation)
    {
        var record = reader.GetCustomDebugInformation(handle);
        if (reader.GetGuid(record.Kind) == sourceLinkId) sourceLink = Encoding.UTF8.GetString(reader.GetBlobBytes(record.Value));
    }
    if (sourceLink == null) throw new InvalidDataException($"Missing Source Link: {tfm}");
    using var document = JsonDocument.Parse(sourceLink);
    if (!document.RootElement.GetProperty("documents").EnumerateObject().Any()) throw new InvalidDataException("Empty Source Link documents.");
    reports.Add(new { target = tfm, sourceLink = document.RootElement.Clone(), documents = reader.Documents.Count });
}
Console.WriteLine(JsonSerializer.Serialize(reports));
