"""Publish and execute the packed .NET 10 assembly as a NativeAOT host consumer."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from xml.sax.saxutils import escape

package = Path(__file__).resolve().parents[1]
version = (package / "VERSION").read_text().strip()
rid = sys.argv[1] if len(sys.argv) == 2 else "linux-x64"
artifacts = package / "artifacts"
with tempfile.TemporaryDirectory(prefix="aot-", dir=artifacts) as temporary:
    directory = Path(temporary)
    config = directory / "NuGet.Config"
    config.write_text('<configuration><packageSources><clear/><add key="candidate" value="'
                      + escape(str(artifacts / "packages"), {'"': '&quot;'}) + '"/>'
                      '<add key="framework" value="https://api.nuget.org/v3/index.json"/></packageSources>'
                      '<packageSourceMapping><packageSource key="candidate"><package pattern="DeanCochran.Ftms"/></packageSource>'
                      '<packageSource key="framework"><package pattern="*"/></packageSource></packageSourceMapping></configuration>')
    env = dict(os.environ, NUGET_PACKAGES=str(directory / "cache"), NUGET_HTTP_CACHE_PATH=str(directory / "http-cache"))
    subprocess.run(["dotnet", "publish", "verification/AotConsumer/AotConsumer.csproj", "-c", "Release", "-r", rid,
                    f"-p:FtmsVersion={version}", f"-p:RestoreConfigFile={config}", "-p:RestorePackagesWithLockFile=false",
                    "-o", str(directory / "output")], cwd=package, env=env, check=True)
    executable = directory / "output" / ("AotConsumer.exe" if os.name == "nt" else "AotConsumer")
    subprocess.run([str(executable)], cwd=directory, check=True)
(artifacts / "aot-verification.json").write_text(json.dumps({"complete": True, "rid": rid, "packageVersion": version,
                                                            "publishedArtifactConsumer": False, "localPackedArtifactConsumer": True,
                                                            "allLibraryMembersRootedForAnalysis": True}, indent=2) + "\n")
print(f"NativeAOT local-package consumer passed: {rid}")
