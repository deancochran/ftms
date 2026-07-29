import { spawn } from "node:child_process";
import { mkdir, mkdtemp, readdir, readFile, rm, writeFile } from "node:fs/promises";
import { builtinModules } from "node:module";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const executable = (name) => (process.platform === "win32" ? `${name}.cmd` : name);
const sourceManifest = JSON.parse(await readFile(path.join(packageRoot, "package.json"), "utf8"));
const packagePathSegments = sourceManifest.name.split("/");
const sourceModules = ["binary", "constants", "control", "features", "index", "parsers", "types"];
const expectedPackageFiles = new Set([
  "CHANGELOG.md",
  "LICENSE",
  "README.md",
  "SECURITY.md",
  "conformance/v1/schema.json",
  "conformance/v1/vectors.json",
  "package.json",
  ...sourceModules.map((module) => `src/${module}.ts`),
  ...sourceModules.flatMap((module) => [
    `dist/${module}.d.ts`,
    `dist/${module}.d.ts.map`,
    `dist/${module}.js`,
    `dist/${module}.js.map`,
  ]),
]);

async function listFiles(directory, relativeDirectory = "") {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const relativePath = path.posix.join(relativeDirectory, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await listFiles(path.join(directory, entry.name), relativePath)));
    } else if (entry.isFile()) {
      files.push(relativePath);
    } else {
      throw new Error(`Packed package contains unsupported entry ${relativePath}`);
    }
  }
  return files.sort();
}

function assertExactPackageFiles(actualFiles) {
  const unexpected = actualFiles.filter((file) => !expectedPackageFiles.has(file));
  const missing = [...expectedPackageFiles].filter((file) => !actualFiles.includes(file));
  if (unexpected.length > 0 || missing.length > 0) {
    throw new Error(
      `Packed file allowlist mismatch; unexpected: ${unexpected.join(", ") || "none"}; missing: ${missing.join(", ") || "none"}`,
    );
  }
}

async function verifySourceMaps(packageDirectory) {
  for (const module of sourceModules) {
    for (const targetExtension of ["js", "d.ts"]) {
      const target = `dist/${module}.${targetExtension}`;
      const mapPath = `${target}.map`;
      const sourceMap = JSON.parse(await readFile(path.join(packageDirectory, mapPath), "utf8"));
      if (
        sourceMap.version !== 3 ||
        sourceMap.file !== path.posix.basename(target) ||
        sourceMap.sourceRoot !== "" ||
        sourceMap.sources?.length !== 1 ||
        sourceMap.sources[0] !== `../src/${module}.ts` ||
        typeof sourceMap.mappings !== "string"
      ) {
        throw new Error(`${mapPath} does not map ${target} to its packaged TypeScript source`);
      }
    }
  }
}

async function verifyBuiltJavaScript(packageDirectory) {
  const nodeBuiltins = new Set(
    builtinModules.flatMap((module) => [module, module.replace(/^node:/, "")]),
  );
  const forbiddenGlobals =
    /\b(?:Buffer|setTimeout|clearTimeout|setInterval|clearInterval|setImmediate|clearImmediate|console)\b/;
  const importPattern =
    /(?:\b(?:import|export)\s+(?:[^"'();]*?\s+from\s*)?|\b(?:import|require)\s*\(\s*)["']([^"']+)["']/g;

  for (const module of sourceModules) {
    const relativePath = `dist/${module}.js`;
    const javascript = await readFile(path.join(packageDirectory, relativePath), "utf8");
    const forbiddenGlobal = javascript.match(forbiddenGlobals)?.[0];
    if (forbiddenGlobal !== undefined) {
      throw new Error(`${relativePath} references forbidden runtime global ${forbiddenGlobal}`);
    }

    for (const match of javascript.matchAll(importPattern)) {
      const specifier = match[1];
      if (specifier === undefined) continue;
      const bareSpecifier = specifier.replace(/^node:/, "").split("/")[0];
      if (
        specifier.startsWith("node:") ||
        nodeBuiltins.has(specifier) ||
        nodeBuiltins.has(bareSpecifier)
      ) {
        throw new Error(`${relativePath} imports Node built-in ${specifier}`);
      }
      if (/(?:^|[/@_-])(?:react-native|bluetooth|ble|noble)(?:$|[/_-])/i.test(specifier)) {
        throw new Error(`${relativePath} imports runtime-specific module ${specifier}`);
      }
    }
  }
}

function run(command, args, cwd, env = process.env) {
  return new Promise((resolve, reject) => {
    const child = spawn(executable(command), args, {
      cwd,
      env,
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

  const packEnvironment = { ...process.env };
  delete packEnvironment.npm_config_dry_run;
  await run("pnpm", ["pack", "--pack-destination", packDirectory], packageRoot, packEnvironment);
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
    packEnvironment,
  );

  const installedManifest = JSON.parse(
    await readFile(
      path.join(consumerDirectory, "node_modules", ...packagePathSegments, "package.json"),
      "utf8",
    ),
  );
  const installedPackageDirectory = path.join(
    consumerDirectory,
    "node_modules",
    ...packagePathSegments,
  );
  assertExactPackageFiles(await listFiles(installedPackageDirectory));
  await verifySourceMaps(installedPackageDirectory);
  await verifyBuiltJavaScript(installedPackageDirectory);
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
    installedManifest.exports?.["."]?.["react-native"] !== "./dist/index.js" ||
    installedManifest.exports?.["./application"] !== undefined ||
    installedManifest.exports?.["./conformance/schema"] !== "./conformance/v1/schema.json" ||
    installedManifest.exports?.["./conformance/v1/schema"] !== "./conformance/v1/schema.json"
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

const root = await import("${sourceManifest.name}");
if ("reduceFtmsControl" in root || "detectFtmsMachineType" in root) {
  throw new Error("Application policy leaked into the root protocol API");
}
`,
  );
  await run("node", ["runtime.mjs"], consumerDirectory);
  await run("node", ["--conditions=development", "runtime.mjs"], consumerDirectory);
  await run("node", ["--conditions=react-native", "runtime.mjs"], consumerDirectory);

  await writeFile(
    path.join(consumerDirectory, "conformance.mjs"),
    `const { default: vectors } = await import("${sourceManifest.name}/conformance/v1", {
  with: { type: "json" },
});
const { default: schema } = await import("${sourceManifest.name}/conformance/schema", {
  with: { type: "json" },
});
const { default: versionedSchema } = await import(
  "${sourceManifest.name}/conformance/v1/schema",
  { with: { type: "json" } },
);
if (
  vectors.schemaVersion !== 1 ||
  !schema["$id"].includes("/v0.2.0/conformance/v1/schema.json") ||
  !versionedSchema["$id"].includes("/v0.2.0/conformance/v1/schema.json")
) {
  throw new Error("ESM conformance exports are not usable");
}
`,
  );
  await run("node", ["conformance.mjs"], consumerDirectory);

  await writeFile(
    path.join(consumerDirectory, "conformance.cjs"),
    `const vectors = require("${sourceManifest.name}/conformance/v1");
const schema = require("${sourceManifest.name}/conformance/schema");
const versionedSchema = require("${sourceManifest.name}/conformance/v1/schema");
if (
  vectors.schemaVersion !== 1 ||
  !schema["$id"].includes("/v0.2.0/conformance/v1/schema.json") ||
  !versionedSchema["$id"].includes("/v0.2.0/conformance/v1/schema.json")
) {
  throw new Error("Conformance exports are not usable");
}
`,
  );
  await run("node", ["conformance.cjs"], consumerDirectory);

  await writeFile(
    path.join(consumerDirectory, "index.html"),
    '<script type="module" src="/browser.mjs"></script>\n',
  );
  await writeFile(
    path.join(consumerDirectory, "browser.mjs"),
    `import { decodeFtmsFeatures, parseFtmsIndoorBikeMeasurement } from "${sourceManifest.name}";
const features = decodeFtmsFeatures(new Uint8Array(8).buffer);
const measurement = parseFtmsIndoorBikeMeasurement(Uint8Array.of(0, 0, 0, 0));
if (!features.ok || measurement.kind !== "measurement") {
  throw new Error("Browser bundle runtime mismatch");
}
`,
  );
  await run(
    "pnpm",
    [
      "exec",
      "vite",
      "build",
      consumerDirectory,
      "--outDir",
      path.join(temporaryRoot, "browser-dist"),
      "--emptyOutDir",
    ],
    packageRoot,
  );

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
    `Verified packed ${sourceManifest.name} allowlist, maps, runtime neutrality, exports, browser resolution, and declarations.`,
  );
} finally {
  if (process.env.FTMS_KEEP_VERIFY_TEMP === "1") {
    console.log(`Retained package verification files at ${temporaryRoot}`);
  } else {
    await rm(temporaryRoot, { force: true, recursive: true });
  }
}
