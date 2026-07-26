from __future__ import annotations

import ast
import json
import re
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RepositoryScaffoldContractTests(unittest.TestCase):
    def read_required_text(self, relative_path: str) -> str:
        path = ROOT / relative_path
        self.assertTrue(path.is_file(), f"missing required root contract: {relative_path}")
        return path.read_text(encoding="utf-8")

    def test_should_pin_exact_node_and_python_versions(self) -> None:
        self.assertEqual(self.read_required_text(".node-version").strip(), "24.12.0")
        self.assertEqual(self.read_required_text(".python-version").strip(), "3.12.13")

    def test_should_define_private_dependency_free_root_package(self) -> None:
        package = json.loads(self.read_required_text("package.json"))

        self.assertIs(package.get("private"), True)
        self.assertEqual(package.get("packageManager"), "pnpm@11.13.0")
        self.assertEqual(package.get("engines", {}).get("node"), ">=24.0.0 <25.0.0")
        self.assertEqual(package.get("dependencies", {}), {})
        self.assertEqual(package.get("devDependencies", {}), {})

    def test_should_include_active_app_and_package_workspaces(self) -> None:
        workspace = self.read_required_text("pnpm-workspace.yaml")
        entries = {
            match.group(1)
            for line in workspace.splitlines()
            if (match := re.fullmatch(r"\s*-\s+['\"]?([^'\"]+)['\"]?\s*", line))
        }

        self.assertIn("apps/*", entries)
        self.assertIn("packages/*", entries)

    def test_should_pin_exact_uv_without_index_or_credentials(self) -> None:
        uv_toml = self.read_required_text("uv.toml")

        self.assertEqual(uv_toml.strip(), 'required-version = "==0.11.28"')
        self.assertEqual(tomllib.loads(uv_toml), {"required-version": "==0.11.28"})
        lowered = uv_toml.lower()
        for forbidden_setting in (
            "index-url",
            "extra-index-url",
            "default-index",
            "username",
            "password",
            "credential",
            "token",
        ):
            self.assertNotIn(forbidden_setting, lowered)

    def test_should_enforce_exact_saves_and_engine_checks_without_credentials(self) -> None:
        npmrc = self.read_required_text(".npmrc")
        settings = {
            key.strip().lower(): value.strip().lower()
            for line in npmrc.splitlines()
            if line.strip() and not line.lstrip().startswith(("#", ";")) and "=" in line
            for key, value in [line.split("=", 1)]
        }

        self.assertEqual(settings.get("save-exact"), "true")
        self.assertEqual(settings.get("engine-strict"), "true")
        lowered = npmrc.lower()
        for credential_marker in ("_auth", "authtoken", "username=", "password=", "npm_token"):
            self.assertNotIn(credential_marker, lowered)

    def test_should_ignore_repository_transient_paths(self) -> None:
        ignored = {
            line.strip()
            for line in self.read_required_text(".gitignore").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

        required = {
            "node_modules/",
            ".pnpm-store/",
            ".next/",
            ".venv/",
            "__pycache__/",
            ".worktrees/",
            ".superpowers/",
            ".tools/",
            "supabase/.temp/",
            "supabase/.branches/",
        }
        self.assertEqual(required - ignored, set())

    def test_should_align_active_api_version_artifacts_with_manifest(self) -> None:
        manifest = json.loads(self.read_required_text("versions/manifest.json"))
        expected_api_version = manifest["versions"]["api"]

        def required_version_match(relative_path: str, pattern: str) -> str:
            matches = re.findall(pattern, self.read_required_text(relative_path), re.MULTILINE)
            self.assertEqual(
                len(matches),
                1,
                f"expected one active API version marker in {relative_path}",
            )
            return matches[0]

        main_module = ast.parse(
            self.read_required_text("apps/api/src/sejong_ai_api/main.py"),
            filename="apps/api/src/sejong_ai_api/main.py",
        )
        fastapi_versions = [
            keyword.value.value
            for node in ast.walk(main_module)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "FastAPI"
            for keyword in node.keywords
            if keyword.arg == "version"
            and isinstance(keyword.value, ast.Constant)
            and isinstance(keyword.value.value, str)
        ]
        self.assertEqual(
            len(fastapi_versions),
            1,
            "expected one literal FastAPI version metadata value",
        )

        actual_versions = {
            "README shared-contract state": required_version_match(
                "README.md",
                r"공유 계약 package는 OpenAPI ([^,\s]+),",
            ),
            "README active contract revision": required_version_match(
                "README.md",
                r"`contracts/`의 API spec revision은 ([^\s]+?)다\.",
            ),
            "CODEX contract index": required_version_match(
                "CODEX_FILE_INDEX.md",
                r"^\| `contracts/` \| OpenAPI ([^\s]+)와 동기화 JSON Schema \|$",
            ),
            "tracked OpenAPI metadata": required_version_match(
                "contracts/openapi-v1.yaml",
                r"^  version:\s*([^\s]+)\s*$",
            ),
            "FastAPI metadata": fastapi_versions[0],
            "generated TypeScript banner": required_version_match(
                "packages/shared-contracts/src/generated/api.ts",
                r"^\s*\* OpenAPI: ([^;]+); generator:",
            ),
        }

        drift = {
            artifact: actual
            for artifact, actual in actual_versions.items()
            if actual != expected_api_version
        }
        self.assertEqual(
            drift,
            {},
            f"active API versions must match manifest value {expected_api_version}",
        )


if __name__ == "__main__":
    unittest.main()
