import { spawn } from "node:child_process";
import { mkdir, mkdtemp, readdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const executable = (name) => (process.platform === "win32" ? `${name}.cmd` : name);
const sourceManifest = JSON.parse(await readFile(path.join(packageRoot, "package.json"), "utf8"));
const packagePathSegments = sourceManifest.name.split("/");

function run(command, args, cwd) {
  return new Promise((resolve, reject) => {
    const child = spawn(executable(command), args, {
      cwd,
      env: process.env,
      stdio: "inherit",
    });
    child.once("error", reject);
    child.once("exit", (code, signal) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(
        new Error(
          `${command} ${args.join(" ")} failed${signal ? ` with signal ${signal}` : ` with code ${code}`}`,
        ),
      );
    });
  });
}

const temporaryRoot = await mkdtemp(path.join(tmpdir(), "ftms-package-"));
const packDirectory = path.join(temporaryRoot, "pack");
const consumerDirectory = path.join(temporaryRoot, "consumer");

try {
  await mkdir(packDirectory);
  await mkdir(consumerDirectory);

  await run("pnpm", ["pack", "--pack-destination", packDirectory], packageRoot);
  const tarballs = (await readdir(packDirectory)).filter((entry) => entry.endsWith(".tgz"));
  if (tarballs.length !== 1) {
    throw new Error(`Expected one package tarball, found ${tarballs.length}`);
  }

  const tarball = path.join(packDirectory, tarballs[0]);
  await writeFile(
    path.join(consumerDirectory, "package.json"),
    `${JSON.stringify({ name: "ftms-package-consumer", private: true, type: "module" }, null, 2)}\n`,
  );
  await run(
    "npm",
    ["install", "--ignore-scripts", "--no-audit", "--no-fund", tarball],
    consumerDirectory,
  );

  const installedManifest = JSON.parse(
    await readFile(
      path.join(consumerDirectory, "node_modules", ...packagePathSegments, "package.json"),
      "utf8",
    ),
  );
  if (
    installedManifest.name !== sourceManifest.name ||
    installedManifest.version !== sourceManifest.version
  ) {
    throw new Error(
      `Installed package identity does not match ${sourceManifest.name}@${sourceManifest.version}`,
    );
  }
  if (installedManifest.license !== "MIT") {
    throw new Error("Installed package must declare the MIT license");
  }
  if (
    installedManifest.exports?.["."]?.types !== "./dist/index.d.ts" ||
    installedManifest.exports?.["."]?.import !== "./dist/index.js" ||
    installedManifest.exports?.["."]?.["react-native"] !== "./dist/index.js"
  ) {
    throw new Error("Installed package exports do not target built artifacts");
  }

  await writeFile(
    path.join(consumerDirectory, "runtime.mjs"),
    `import {
  decodeFtmsFeatures,
  encodeFtmsControlRequest,
  parseFtmsIndoorBikeMeasurement,
} from "${sourceManifest.name}";

const features = decodeFtmsFeatures(Uint8Array.of(0, 0, 0, 0, 0, 0, 0, 0));
if (!features.ok) throw new Error("Feature decoder was not available");

const request = encodeFtmsControlRequest({ op: "setTargetPower", powerWatts: 250 });
if (request.length !== 3 || request[0] !== 0x05) throw new Error("Control encoder mismatch");

const measurement = parseFtmsIndoorBikeMeasurement(Uint8Array.of(0, 0, 0, 0));
if (measurement.kind !== "measurement") throw new Error("Measurement parser mismatch");
`,
  );
  await run("node", ["runtime.mjs"], consumerDirectory);
  await run("node", ["--conditions=development", "runtime.mjs"], consumerDirectory);
  await run("node", ["--conditions=react-native", "runtime.mjs"], consumerDirectory);

  await writeFile(
    path.join(consumerDirectory, "conformance.cjs"),
    `const vectors = require("${sourceManifest.name}/conformance/v1");
const schema = require("${sourceManifest.name}/conformance/schema");
if (vectors.schemaVersion !== 1 || schema.properties.schemaVersion.const !== 1) {
  throw new Error("Conformance exports are not usable");
}
`,
  );
  await run("node", ["conformance.cjs"], consumerDirectory);

  await writeFile(
    path.join(consumerDirectory, "consumer.ts"),
    `import {
  type FtmsControlRequest,
  type ParsedFtmsPayload,
  parseFtmsTreadmillData,
  tryEncodeFtmsControlRequest,
} from "${sourceManifest.name}";

const request: FtmsControlRequest = { op: "requestControl" };
const encoded = tryEncodeFtmsControlRequest(request);
const parsed: ParsedFtmsPayload = parseFtmsTreadmillData(Uint8Array.of(0, 0, 0, 0));
void encoded;
void parsed;
`,
  );
  await writeFile(
    path.join(consumerDirectory, "tsconfig.json"),
    `${JSON.stringify(
      {
        compilerOptions: {
          exactOptionalPropertyTypes: true,
          module: "NodeNext",
          moduleResolution: "NodeNext",
          noEmit: true,
          strict: true,
          target: "ES2022",
        },
        include: ["consumer.ts"],
      },
      null,
      2,
    )}\n`,
  );
  await run(
    "pnpm",
    ["exec", "tsc", "--project", path.join(consumerDirectory, "tsconfig.json")],
    packageRoot,
  );

  console.log(
    `Verified packed ${sourceManifest.name} artifact, exports, runtime, and declarations.`,
  );
} finally {
  if (process.env.FTMS_KEEP_VERIFY_TEMP === "1") {
    console.log(`Retained package verification files at ${temporaryRoot}`);
  } else {
    await rm(temporaryRoot, { force: true, recursive: true });
  }
}
