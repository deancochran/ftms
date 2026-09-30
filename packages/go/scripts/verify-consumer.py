"""Offline module-zip and isolated consumer gate. Never publishes anything."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

package = Path(__file__).resolve().parents[1]
go_root = subprocess.check_output(["go", "env", "GOROOT"], text=True).strip()
go_binary = str(Path(go_root) / "bin" / ("go.exe" if os.name == "nt" else "go"))
module = "github.com/deancochran/ftms/packages/go"
version = "v0.0.0-local"
preferred = "/tmp/opencode" if os.access("/tmp/opencode", os.W_OK) else tempfile.gettempdir()
base = Path(os.environ.get("TMPDIR", preferred))
base.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix="ftms-go-consumer-", dir=base) as temp:
    root = Path(temp)
    proxy = root / "proxy"
    versions = proxy / module / "@v"
    versions.mkdir(parents=True)
    (versions / "list").write_text(version + "\n")
    (versions / f"{version}.mod").write_bytes((package / "go.mod").read_bytes())
    (versions / f"{version}.info").write_text(json.dumps({"Version": version, "Time": "2000-01-01T00:00:00Z"}))
    with zipfile.ZipFile(versions / f"{version}.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(package.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(package)
            if any(part.startswith(".") or part in ("__pycache__", "reports") for part in relative.parts):
                continue
            archive.write(path, f"{module}@{version}/{relative.as_posix()}")
    env = dict(os.environ, GOPROXY=proxy.as_uri(), GOSUMDB="off", GOPRIVATE="", GONOPROXY="",
               GONOSUMDB="", GOWORK="off", GOFLAGS="", GOTOOLCHAIN="local", GOMODCACHE=str(root / "cache"))
    consumer = root / "consumer"
    consumer.mkdir()
    (consumer / "go.mod").write_text(f"module example.com/ftms-consumer\n\ngo 1.24\n\nrequire {module} {version}\n")
    (consumer / "main.go").write_text('''package main
import (
    "bytes"
    ftms "github.com/deancochran/ftms/packages/go"
)
func main() {
    measurement, err := ftms.DecodeMeasurement(ftms.IndoorBike, []byte{0, 0, 0x10, 0x0e}, ftms.MeasurementOptions{})
    if err != nil || measurement.Values[ftms.Speed] != 3600 { panic("telemetry") }
    packet, err := ftms.EncodeControlRequest(ftms.ControlRequest{Opcode: 5, Operands: []int32{250}}, ftms.ControlOptions{})
    if err != nil || !bytes.Equal(packet, []byte{5,250,0}) { panic("control") }
    if _, err := ftms.DecodeControlRequest(packet, ftms.ControlOptions{}); err != nil { panic(err) }
    report, err := ftms.InterpretCapabilities(ftms.CapabilitySnapshot{
        Scope: ftms.ScopePresent, Discovery: ftms.DiscoveryComplete, Generation: 7,
        C7: ftms.C7Evidence{BondingSupported: ftms.TruthFalse},
        Characteristics: []ftms.CharacteristicObservation{
            {UUID: ftms.UUID16(0x2acc), Properties: ftms.PropertyRead, ReadState: ftms.ReadSuccess, Bytes: make([]byte, 8)},
            {UUID: ftms.UUID16(0x2ad9), Properties: ftms.PropertyWrite | ftms.PropertyIndicate},
            {UUID: ftms.UUID16(0x2ada), Properties: ftms.PropertyNotify},
        },
    }, ftms.CapabilityOptions{})
    if err != nil || report.Generation != 7 || report.Operations[0].Declaration != ftms.DeclarationSupported ||
        report.Operations[0].Prerequisite != ftms.PrerequisiteSatisfied { panic("capability interpretation") }
}
''')
    def run(*args, cwd=consumer):
        if args[0] == "go":
            args = (go_binary, *args[1:])
        subprocess.run(args, cwd=cwd, env=env, check=True)
    run("go", "mod", "tidy")
    run("go", "mod", "verify")
    run("go", "run", ".")
    result = subprocess.run([go_binary, "mod", "download", "-json", f"{module}@{version}"],
                            cwd=consumer, env=env, check=True, capture_output=True, text=True)
    metadata = json.loads(result.stdout)
    # Test a writable copy of the downloaded zip, without a checkout or shared/.
    installed = root / "installed"
    shutil.copytree(metadata["Dir"], installed)
    run("go", "test", "./...", cwd=installed)
    run("go", "build", "./...", cwd=installed)
    print(json.dumps({"localOnly": True, "replaceDirectives": False,
                      "toolchain": subprocess.check_output([go_binary, "version"], env=env, text=True).strip(),
                      "module": module, "version": version,
                      "sum": metadata["Sum"], "goModSum": metadata["GoModSum"],
                      "consumerRun": "passed", "installedTests": "passed"}, indent=2))
