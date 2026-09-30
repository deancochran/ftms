#!/usr/bin/env bash
# Credential-free local verification; no tag, registry upload or equipment I/O.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
python="${PYTHON:-python3}"
"$python" -c 'import jsonschema' # See verification/requirements.txt.
rm -rf artifacts
mkdir -p artifacts/packages
"$python" -m unittest discover -s verification -p 'test_*.py' -v
"$python" verification/validate-schemas.py
for project in src/DeanCochran.Ftms tests/DeanCochran.Ftms.Tests verification/CodecConformance verification/CapabilityConformance verification/MatrixConformance verification/PackageAudit; do
  dotnet restore "$project" --locked-mode
done
dotnet build src/DeanCochran.Ftms -c Release --no-restore
dotnet test tests/DeanCochran.Ftms.Tests -c Release --no-restore --logger 'trx;LogFileName=unit-tests.trx' --results-directory artifacts/tests
dotnet run --project verification/CodecConformance -c Release --no-restore -- artifacts/codec-conformance.json
dotnet run --project verification/CapabilityConformance -c Release --no-restore -- artifacts/capability-conformance.json
dotnet run --project verification/MatrixConformance -c Release --no-restore -- artifacts/matrix-conformance.json
dotnet pack src/DeanCochran.Ftms -c Release --no-build --no-restore -o artifacts/packages
"$python" verification/verify-package.py
if [[ "${FTMS_VERIFY_AOT:-0}" == 1 ]]; then
  "$python" verification/verify-aot.py "${FTMS_AOT_RID:-linux-x64}"
fi
echo 'C# local verification passed. Artifacts and JSON reports: packages/csharp/artifacts/'
