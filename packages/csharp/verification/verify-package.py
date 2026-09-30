"""Local-only NuGet payload, identity, Source Link and isolated consumer checks."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import zipfile

PACKAGE = Path(__file__).resolve().parents[1]
PACKAGE_ID = "DeanCochran.Ftms"
TFMS = ("netstandard2.1", "net10.0")


def validate_version(value):
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9a-z-]+(?:\.[0-9a-z-]+)*))?", value):
        raise ValueError("VERSION must be canonical NuGet SemVer without build metadata")
    release, _, prerelease = value.partition("-")
    if any(int(part) > 2147483647 for part in release.split(".")):
        raise ValueError("VERSION release component exceeds Int32")
    if any(part.isdigit() and len(part) > 1 and part[0] == "0" for part in prerelease.split(".")):
        raise ValueError("VERSION numeric prerelease component has a leading zero")
    return value


def payload_manifest(path, allow_repository_signature=False):
    """No blanket exclusions: only NuGet's exact root signature entry may differ."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate ZIP entry")
        if any(name.startswith("/") or "\\" in name or ".." in name.split("/") for name in names):
            raise ValueError("Unsafe ZIP path")
        if ".signature.p7s" in names and not allow_repository_signature:
            raise ValueError("Unexpected signature in local unsigned candidate")
        return {name: hashlib.sha256(archive.read(name)).hexdigest() for name in sorted(names)
                if not (allow_repository_signature and name == ".signature.p7s")}


def audit_archive(path, version, symbols=False):
    manifest = payload_manifest(path)
    common = {"_rels/.rels", f"{PACKAGE_ID}.nuspec", "[Content_Types].xml"}
    expected = common | ({f"lib/{tfm}/{PACKAGE_ID}.pdb" for tfm in TFMS} if symbols else
                         {"README.md"} | {f"lib/{tfm}/{PACKAGE_ID}.{ext}" for tfm in TFMS for ext in ("dll", "xml")})
    metadata = {name for name in manifest if re.fullmatch(r"package/services/metadata/core-properties/[0-9a-f]{32}\.psmdcp", name)}
    if len(metadata) != 1 or set(manifest) != expected | metadata:
        raise ValueError("Package allowlist mismatch: " + repr(set(manifest) ^ (expected | metadata)))
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read(f"{PACKAGE_ID}.nuspec"))
        metadata_xml = root.find("{*}metadata")
        if metadata_xml is None:
            raise ValueError("Missing nuspec metadata")
        expected_metadata = [("id", PACKAGE_ID), ("version", version)]
        # SDK symbol nuspecs deliberately omit author/license; the main package owns them.
        if not symbols:
            expected_metadata.extend((("license", "MIT"), ("authors", "Dean Cochran")))
        for key, expected_value in expected_metadata:
            if metadata_xml.findtext("{*}" + key) != expected_value:
                raise ValueError(f"Nuspec {key} mismatch")
        repository = metadata_xml.find("{*}repository")
        if repository is None or repository.get("url") != "https://github.com/deancochran/ftms" or not repository.get("commit"):
            raise ValueError("Missing repository/source identity")
        if metadata_xml.findall(".//{*}dependency"):
            raise ValueError("Unexpected runtime dependency")
        if not symbols and archive.read("README.md") != (PACKAGE / "README.md").read_bytes():
            raise ValueError("Packaged README differs from its source")
    return manifest


def run(*args, cwd=PACKAGE, env=None):
    subprocess.run(args, cwd=cwd, env=env, check=True)


def project(tfm, executable, body=""):
    output = "<OutputType>Exe</OutputType>" if executable else ""
    return (f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>{tfm}</TargetFramework>'
            f'{output}<LangVersion>14.0</LangVersion><RestorePackagesWithLockFile>false</RestorePackagesWithLockFile>'
            '<TreatWarningsAsErrors>true</TreatWarningsAsErrors></PropertyGroup>' + body + '</Project>')


def consumers(feed, version, temporary):
    results = []
    for tfm in TFMS:
        directory = temporary / tfm
        directory.mkdir()
        cache = directory / "cache"
        env = dict(os.environ, NUGET_PACKAGES=str(cache), NUGET_HTTP_CACHE_PATH=str(directory / "http-cache"),
                   DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1")
        (directory / "NuGet.Config").write_text('<configuration><packageSources><clear/><add key="candidate" value="'
                                               + escape(str(feed), {'"': '&quot;'}) + '"/>'
                                               '<add key="framework" value="https://api.nuget.org/v3/index.json"/></packageSources>'
                                               '<packageSourceMapping><packageSource key="candidate"><package pattern="DeanCochran.Ftms"/></packageSource>'
                                               '<packageSource key="framework"><package pattern="NETStandard.Library.Ref"/></packageSource>'
                                               '</packageSourceMapping></configuration>')
        (directory / "Program.cs").write_bytes((PACKAGE / "verification/PackageConsumer/Program.cs").read_bytes())
        body = f'<ItemGroup><PackageReference Include="{PACKAGE_ID}" Version="[{version}]" /></ItemGroup>'
        (directory / "Consumer.csproj").write_text(project(tfm, tfm == "net10.0", body))
        run("dotnet", "restore", "Consumer.csproj", "--configfile", "NuGet.Config", "--force", cwd=directory, env=env)
        assets = json.loads((directory / "obj/project.assets.json").read_text())
        target = next(iter(assets["targets"].values()))[f"{PACKAGE_ID}/{version}"]
        expected_asset = f"lib/{tfm}/{PACKAGE_ID}.dll"
        if set(target["compile"]) != {expected_asset} or set(target["runtime"]) != {expected_asset}:
            raise ValueError("Unexpected NuGet target selection")
        run("dotnet", "build", "Consumer.csproj", "-c", "Release", "--no-restore", cwd=directory, env=env)
        if tfm == "net10.0":
            run("dotnet", "run", "--project", "Consumer.csproj", "-c", "Release", "--no-build", cwd=directory, env=env)
        else:
            # Execute the very same Standard assembly, not a net10.0 package asset
            # silently re-selected by a transitive project/package reference.
            host = directory / "host"
            host.mkdir()
            library = cache / PACKAGE_ID.lower() / version / "lib/netstandard2.1" / f"{PACKAGE_ID}.dll"
            standard_consumer = directory / "bin/Release/netstandard2.1/Consumer.dll"
            references = ('<ItemGroup><Reference Include="Consumer"><HintPath>' + escape(str(standard_consumer)) + '</HintPath></Reference>'
                          '<Reference Include="DeanCochran.Ftms"><HintPath>' + escape(str(library)) + '</HintPath></Reference></ItemGroup>')
            (host / "Host.csproj").write_text(project("net10.0", True, references))
            (host / "Program.cs").write_text("public static class Host { public static void Main() => Consumer.Verify(); }")
            run("dotnet", "run", "--project", "Host.csproj", "-c", "Release", cwd=host, env=env)
            # Reuse the independent fixture runners against the installed Standard
            # DLL. No source ProjectReference or modern FTMS asset participates.
            for suite, report_name in (("CodecConformance", "codec"), ("CapabilityConformance", "capability"), ("MatrixConformance", "matrix")):
                runner = directory / "conformance" / suite
                runner.mkdir(parents=True)
                body = ('<PropertyGroup><EnableDefaultCompileItems>false</EnableDefaultCompileItems>'
                        '<ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup>'
                        '<ItemGroup><Compile Include="' + escape(str(PACKAGE / "verification" / suite / "*.cs"), {'"': '&quot;'}) + '"/>'
                        '<Reference Include="DeanCochran.Ftms"><HintPath>' + escape(str(library)) + '</HintPath></Reference></ItemGroup>')
                (runner / "Runner.csproj").write_text(project("net10.0", True, body))
                report = PACKAGE / "artifacts" / f"{report_name}-conformance-netstandard.json"
                run("dotnet", "run", "--project", "Runner.csproj", "-c", "Release", "--", str(report), cwd=runner, env=env)
        results.append({"target": tfm, "asset": expected_asset, "compiled": True, "executed": True, "source": "isolated local NuGet feed"})
    return results


def main():
    version = validate_version((PACKAGE / "VERSION").read_text().strip())
    artifacts = PACKAGE / "artifacts"
    feed = artifacts / "packages"
    paths = [feed / f"{PACKAGE_ID}.{version}.{ext}" for ext in ("nupkg", "snupkg")]
    if set(feed.iterdir()) != set(paths):
        raise ValueError("Candidate feed must contain exactly one nupkg and one snupkg")
    manifests = {path.name: audit_archive(path, version, path.suffix == ".snupkg") for path in paths}
    with tempfile.TemporaryDirectory(prefix="installed-", dir=artifacts) as temporary:
        temp = Path(temporary)
        results = consumers(feed, version, temp)
        symbols = temp / "symbols"
        with zipfile.ZipFile(paths[1]) as archive:
            for tfm in TFMS:
                name = f"lib/{tfm}/{PACKAGE_ID}.pdb"
                target = symbols / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
        run("dotnet", "run", "--project", "verification/PackageAudit", "-c", "Release", "--", str(symbols))
    report = {"packageId": PACKAGE_ID, "version": version, "complete": True, "published": False,
              "sourceCommit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PACKAGE, text=True).strip(),
              "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=PACKAGE, text=True).strip()),
              "artifactSha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
              "payloads": manifests, "consumers": results, "sourceLinkMetadataVerified": True}
    (artifacts / "package-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print("NuGet allowlist, metadata, symbols, Source Link metadata and both isolated consumers passed.")


if __name__ == "__main__":
    main()
