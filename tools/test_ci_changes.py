import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("ci_changes", Path(__file__).with_name("ci-changes.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SelectionTests(unittest.TestCase):
    def test_each_port_and_docs(self):
        for port in module.PORTS:
            with self.subTest(port=port):
                selected = module.select([f"packages/{port}/source"])
                self.assertEqual({k for k, v in selected.items() if v}, {port, "docs"})

    def test_global_dependencies(self):
        for path in ("shared/conformance/README.md", "shared/protocol/contract.json", "shared/conformance/v1/vectors.json", "pnpm-lock.yaml", "biome.json", ".github/workflows/ci.yml", "tools/check-docs.mjs", "unknown/path"):
            with self.subTest(path=path):
                self.assertTrue(all(module.select([path]).values()))

    def test_docs_only(self):
        for path in ("docs/api.md", "README.md", "site/astro.config.mjs"):
            self.assertEqual({k for k, v in module.select([path]).items() if v}, {"docs"})

    def test_android_example_selects_kotlin_gate(self):
        for suffix in ("app/src/main/AndroidManifest.xml", "ci/run-emulator.sh", "ci/check_instrumentation.py", "README.md"):
            with self.subTest(suffix=suffix):
                selected = module.select([f"packages/kotlin/examples/android-telemetry/{suffix}"])
                self.assertEqual({k for k, v in selected.items() if v}, {"kotlin", "docs"})

    def test_swift_root_and_force(self):
        self.assertTrue(module.select(["Package.swift"])["swift"])
        self.assertTrue(all(module.select([], force=True).values()))
        self.assertFalse(any(module.select([]).values()))
