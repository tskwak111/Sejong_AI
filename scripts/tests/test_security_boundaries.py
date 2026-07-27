from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SECRET_SCANNER = ROOT / "scripts" / "check_secret_patterns.ps1"
BUNDLE_SCANNER = ROOT / "scripts" / "check_web_bundle_secrets.mjs"


def assignments(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator:
            raise AssertionError(f"invalid environment line in {path.name}")
        result[key.strip()] = value.strip()
    return result


def run_secret_scanner(
    *paths: Path,
    repository_root: Path | None = None,
    scanner: Path = SECRET_SCANNER,
    environment: dict[str, str] | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("powershell.exe") or shutil.which("powershell")
    if executable is None:
        raise AssertionError("Windows PowerShell is required")
    command = [executable, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(scanner)]
    if paths:
        command.extend(["-Path", *(str(path) for path in paths)])
    if repository_root is not None:
        command.extend(["-RepositoryRoot", str(repository_root)])
    return subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        env=environment,
        timeout=timeout,
    )


def scanner_with_mock_git(directory: Path, mode: str) -> tuple[Path, dict[str, str]]:
    helper = directory / "mock_git.py"
    helper.write_text(
        """\
import os
import sys
import time

mode = sys.argv[1]
arguments = sys.argv[2:]
if "rev-parse" in arguments:
    sys.stdout.write(os.environ["SEJONG_MOCK_GIT_ROOT"] + "\\n")
    raise SystemExit(0)
if "ls-files" not in arguments:
    raise SystemExit(3)
if mode == "oversized-stderr":
    marker = b"mock-git-stderr-secret-value"
    target = (4 * 1024 * 1024) + 1
    while target > 0:
        chunk = marker[:target]
        sys.stderr.buffer.write(chunk)
        target -= len(chunk)
    sys.stderr.buffer.flush()
    sys.stdout.buffer.write(b"clean.txt\\0")
    sys.stdout.buffer.flush()
elif mode == "stalled-stdout":
    sys.stdout.buffer.write(b"stalled-stdout-secret-value")
    sys.stdout.buffer.flush()
    time.sleep(12)
elif mode == "stalled-stderr":
    sys.stderr.buffer.write(b"stalled-stderr-secret-value")
    sys.stderr.buffer.flush()
    time.sleep(12)
elif mode == "stalled-process":
    os.close(sys.stdout.fileno())
    os.close(sys.stderr.fileno())
    time.sleep(12)
else:
    raise SystemExit(4)
""",
        encoding="utf-8",
    )

    source = SECRET_SCANNER.read_text(encoding="utf-8")
    executable_literal = str(Path(os.sys.executable)).replace("'", "''")
    helper_arguments = subprocess.list2cmdline([str(helper), mode]).replace("'", "''")
    file_name_line = "$startInfo.FileName = 'git'"
    arguments_line = "$startInfo.Arguments = $Arguments"
    deadline_line = "$script:GitDeadlineMilliseconds = 60000"
    if (
        source.count(file_name_line) != 1
        or source.count(arguments_line) != 1
        or source.count(deadline_line) != 1
    ):
        raise AssertionError("secret scanner Git process seam changed")
    source = source.replace(file_name_line, f"$startInfo.FileName = '{executable_literal}'")
    source = source.replace(
        arguments_line,
        f"$startInfo.Arguments = '{helper_arguments} ' + $Arguments",
    )
    source = source.replace(deadline_line, "$script:GitDeadlineMilliseconds = 300")
    scanner = directory / "check_secret_patterns.mock-git.ps1"
    scanner.write_text(source, encoding="utf-8")
    (directory / "clean.txt").write_text("public content\n", encoding="utf-8")
    environment = os.environ.copy()
    environment["SEJONG_MOCK_GIT_ROOT"] = str(directory)
    return scanner, environment


def run_bundle_scanner(build: Path, sentinel: str | None = None) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    if sentinel is None:
        environment.pop("SEJONG_WEB_SECRET_SENTINEL", None)
    else:
        environment["SEJONG_WEB_SECRET_SENTINEL"] = sentinel
    return subprocess.run(
        ["node", str(BUNDLE_SCANNER), str(build)],
        cwd=ROOT,
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        env=environment,
    )


def result_diagnostic(result: subprocess.CompletedProcess[str]) -> str:
    return (
        f"exit={result.returncode} "
        f"stdout_lines={len(result.stdout.splitlines())} "
        f"stderr_lines={len(result.stderr.splitlines())}"
    )


def assert_exit(test: unittest.TestCase, result: subprocess.CompletedProcess[str], code: int) -> None:
    test.assertEqual(result.returncode, code, result_diagnostic(result))


def assert_no_disclosure(
    test: unittest.TestCase, result: subprocess.CompletedProcess[str], values: list[str]
) -> None:
    combined = result.stdout + result.stderr
    test.assertFalse(
        any(value in combined for value in values),
        "scanner output disclosed a synthetic value",
    )


class EnvironmentBoundaryTest(unittest.TestCase):
    def test_root_template_is_comment_only_and_points_to_service_templates(self) -> None:
        path = ROOT / ".env.example"
        parsed = assignments(path)
        if parsed:
            raise AssertionError(f"root template has {len(parsed)} assignments")
        text = path.read_text(encoding="utf-8")
        self.assertIn("apps/web/.env.example -> apps/web/.env.local", text)
        self.assertIn("apps/api/.env.example -> apps/api/.env", text)

    def test_web_template_has_only_the_approved_server_assignment(self) -> None:
        path = ROOT / "apps" / "web" / ".env.example"
        self.assertTrue(path.is_file())
        parsed = assignments(path)
        self.assertEqual(
            set(parsed),
            {
                "API_INTERNAL_BASE_URL",
                "CHAT_UI_MODE",
                "ADMIN_UI_ENABLED",
                "ADMIN_UI_MODE",
            },
        )
        if parsed.get("API_INTERNAL_BASE_URL") != "http://127.0.0.1:8000":
            raise AssertionError("web API base URL does not match the approved local default")
        self.assertEqual(parsed.get("CHAT_UI_MODE"), "actual")
        self.assertEqual(parsed.get("ADMIN_UI_ENABLED"), "false")
        self.assertEqual(parsed.get("ADMIN_UI_MODE"), "actual")
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("NEXT_PUBLIC_", text)
        for name in (
            "DATABASE_URL",
            "SUPABASE_SERVICE_ROLE_KEY",
            "LLM_API_KEY",
            "CONTEXT_TOKEN_SECRET",
            "DEEPSEEK_API_KEY",
        ):
            with self.subTest(name=name):
                self.assertNotIn(name, text)

    def test_api_template_has_exact_defaults_and_blank_sensitive_values(self) -> None:
        path = ROOT / "apps" / "api" / ".env.example"
        self.assertTrue(path.is_file())
        expected = {
            "APP_ENV": "development",
            "LOG_LEVEL": "INFO",
            "CORS_ORIGINS": "http://127.0.0.1:3000",
            "DATABASE_URL": "",
            "SUPABASE_URL": "",
            "SUPABASE_ANON_KEY": "",
            "SUPABASE_SERVICE_ROLE_KEY": "",
            "LLM_PROVIDER": "disabled",
            "LLM_MODEL": "solar-pro3",
            "LLM_API_KEY": "",
            "LLM_BASE_URL": "https://api.upstage.ai/v1",
            "LLM_TIMEOUT_SECONDS": "8",
            "LLM_MAX_RETRIES": "0",
            "LLM_MAX_CONCURRENCY": "1",
            "LLM_MAX_INPUT_TOKENS": "4096",
            "LLM_MAX_OUTPUT_TOKENS": "1024",
            "LLM_RUN_ATTEMPT_CAP": "30",
            "LLM_CLASSIFIER_TIMEOUT_SECONDS": "3",
            "LLM_CLASSIFIER_MAX_RETRIES": "0",
            "LLM_CLASSIFIER_MAX_INPUT_CHARS": "1024",
            "LLM_CLASSIFIER_MAX_OUTPUT_TOKENS": "128",
            "LLM_CLASSIFIER_ATTEMPT_CAP": "20",
            "LLM_GENERATOR_ATTEMPT_CAP": "30",
            "LLM_COMBINED_ATTEMPT_CAP": "40",
            "UPSTAGE_SYNTHETIC_EVALUATION_MODE": "false",
            "UPSTAGE_CLASSIFIER_MODE": "false",
            "UPSTAGE_GROUNDED_CHAT_MODE": "false",
            "CONTEXT_TOKEN_SECRET": "",
            "CONTEXT_TOKEN_TTL_SECONDS": "900",
            "PII_RETENTION_DAYS": "30",
            "DEMO_OPERATOR_ID": "OPERATOR-LOCAL-001",
            "DEMO_APPROVER_ID": "PM-LOCAL-001",
            "ENABLE_EMBEDDINGS": "false",
            "ENABLE_DEMO_ROLE_SWITCH": "true",
            "ENABLE_LOAD_TEST_ENDPOINT": "false",
        }
        actual = assignments(path)
        if actual != expected:
            changed_keys = sorted(
                key for key in set(actual) | set(expected) if actual.get(key) != expected.get(key)
            )
            raise AssertionError(f"API environment contract differs at keys={changed_keys}")
        template = path.read_text(encoding="utf-8")
        self.assertFalse(any(key.startswith("NEXT_PUBLIC_") for key in expected))
        self.assertNotIn("STORE_SUCCESS_TEXT", template)
        self.assertNotIn("STORE_OUT_OF_SCOPE_TEXT", template)


class SecretPatternScannerTest(unittest.TestCase):
    def test_scanner_source_escapes_control_paths_and_workflow_command_prefixes(self) -> None:
        source = SECRET_SCANNER.read_text(encoding="utf-8")
        self.assertIn("$code -lt 32", source)
        self.assertIn("$code -eq 0x2028", source)
        self.assertIn("$safe.StartsWith('::'", source)
        self.assertIn("'\\u003A\\u003A'", source)

    def test_repository_mode_scans_active_git_files_and_excludes_inactive_trees(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sejong candidate repository ") as directory:
            repository = Path(directory)
            subprocess.run(["git", "init", "--quiet"], cwd=repository, check=True)
            active = repository / "active.env"
            legacy = repository / "legacy" / "old.env"
            metadata = repository / ".git" / "scanner-sentinel.env"
            legacy.parent.mkdir(parents=True, exist_ok=True)
            active.write_text("LLM_API_KEY=active-synthetic-value\n", encoding="utf-8")
            legacy.write_text("LLM_API_KEY=legacy-synthetic-value\n", encoding="utf-8")
            metadata.write_text("LLM_API_KEY=git-synthetic-value\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "--", "active.env", "legacy/old.env"],
                cwd=repository,
                check=True,
            )

            result = run_secret_scanner(repository_root=repository)

        assert_exit(self, result, 1)
        self.assertIn("active.env rule=NONEMPTY_SECRET_ASSIGNMENT count=1", result.stdout)
        self.assertNotIn("legacy", result.stdout)
        self.assertNotIn(".git", result.stdout)
        assert_no_disclosure(
            self,
            result,
            ["active-synthetic-value", "legacy-synthetic-value", "git-synthetic-value"],
        )

    def test_repository_mode_rejects_non_repository_without_raw_path_disclosure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sejong non repository sentinel ") as directory:
            result = run_secret_scanner(repository_root=Path(directory))

        assert_exit(self, result, 2)
        self.assertIn("rule=GIT_DISCOVERY_ERROR count=1", result.stdout)
        self.assertNotIn("non repository sentinel", result.stdout + result.stderr)

    def test_repository_mode_rejects_oversized_active_file_before_content_allocation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sejong oversized candidate ") as directory:
            repository = Path(directory)
            subprocess.run(["git", "init", "--quiet"], cwd=repository, check=True)
            active = repository / "oversized-active.bin"
            secret_value = b"sk-" + (b"q" * 32)
            active.write_bytes(secret_value + (b"\0" * ((4 * 1024 * 1024) + 1)))
            subprocess.run(["git", "add", "--", active.name], cwd=repository, check=True)

            result = run_secret_scanner(repository_root=repository)

        assert_exit(self, result, 2)
        self.assertEqual(
            result.stdout.splitlines(),
            ["oversized-active.bin rule=FILE_SIZE_LIMIT count=1"],
        )
        self.assertFalse(result.stderr)
        assert_no_disclosure(self, result, [secret_value.decode("ascii")])

    def test_repository_mode_rejects_aggregate_active_bytes_before_next_allocation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sejong aggregate candidate ") as directory:
            repository = Path(directory)
            subprocess.run(["git", "init", "--quiet"], cwd=repository, check=True)
            for index in range(5):
                active = repository / f"aggregate-{index}.bin"
                active.write_bytes(b"\0" * (4 * 1024 * 1024))
            subprocess.run(["git", "add", "--", "."], cwd=repository, check=True)

            result = run_secret_scanner(repository_root=repository)

        assert_exit(self, result, 2)
        self.assertEqual(
            result.stdout.splitlines(),
            [". rule=AGGREGATE_SCAN_LIMIT count=1"],
        )
        self.assertFalse(result.stderr)

    def test_repository_mode_bounds_git_stderr_without_disclosure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sejong mock git stderr ") as directory:
            repository = Path(directory)
            subprocess.run(["git", "init", "--quiet"], cwd=repository, check=True)
            scanner, environment = scanner_with_mock_git(repository, "oversized-stderr")

            result = run_secret_scanner(
                repository_root=repository,
                scanner=scanner,
                environment=environment,
                timeout=8,
            )

        assert_exit(self, result, 2)
        self.assertEqual(result.stdout.splitlines(), [". rule=GIT_DISCOVERY_ERROR count=1"])
        self.assertFalse(result.stderr)
        assert_no_disclosure(self, result, ["mock-git-stderr-secret-value"])

    def test_repository_mode_deadline_covers_stalled_git_streams_and_process(self) -> None:
        values = {
            "stalled-stdout": "stalled-stdout-secret-value",
            "stalled-stderr": "stalled-stderr-secret-value",
            "stalled-process": "stalled-process-secret-value",
        }
        for mode, secret_value in values.items():
            with self.subTest(mode=mode):
                with tempfile.TemporaryDirectory(prefix="sejong mock git stall ") as directory:
                    repository = Path(directory)
                    subprocess.run(["git", "init", "--quiet"], cwd=repository, check=True)
                    scanner, environment = scanner_with_mock_git(repository, mode)

                    try:
                        result = run_secret_scanner(
                            repository_root=repository,
                            scanner=scanner,
                            environment=environment,
                            timeout=8,
                        )
                    except subprocess.TimeoutExpired:
                        self.fail(f"scanner missed its Git deadline for mode={mode}")

                assert_exit(self, result, 2)
                self.assertEqual(
                    result.stdout.splitlines(),
                    [". rule=GIT_DISCOVERY_ERROR count=1"],
                )
                self.assertFalse(result.stderr)
                assert_no_disclosure(self, result, [secret_value])

    def test_runtime_shell_assignment_prefixes_are_detected_without_value_disclosure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="sejong scanner runtime ") as directory:
            fixture = Path(directory) / "runtime-fragments.txt"
            powershell_value = "synthetic-powershell-runtime-fragment"
            command_value = "synthetic-command-runtime-fragment"
            fixture.write_text(
                "\n".join(
                    (
                        "$EnV:"
                        + "CONTEXT_TOKEN_"
                        + "SECRET = '"
                        + powershell_value
                        + "'",
                        "SeT "
                        + "SUPABASE_"
                        + "SERVICE_ROLE_KEY="
                        + command_value,
                    )
                ),
                encoding="utf-8",
            )
            result = run_secret_scanner(fixture)

        assert_exit(self, result, 1)
        self.assertIn("rule=NONEMPTY_SECRET_ASSIGNMENT count=2", result.stdout)
        assert_no_disclosure(self, result, [powershell_value, command_value])

    def test_unicode_path_reports_sorted_rules_without_echoing_values(self) -> None:
        with tempfile.TemporaryDirectory(prefix="세종 scanner ") as directory:
            fixture = Path(directory) / "비밀 후보.txt"
            values = {
                "provider": "sk-" + ("a" * 32),
                "github": "gh" + "p_" + ("b" * 36),
                "aws": "AK" + "IA" + ("C" * 16),
                "aws_temporary": "AS" + "IA" + ("D" * 16),
                "database": "postgresql://scan-user:" + "db-pass@db.invalid/demo",
                "service_role": "synthetic-service-role-value",
                "llm": "synthetic-llm-value",
                "context": "synthetic-context-value",
                "https_url": "https://demo-user:" + "demo-pass@example.invalid/path",
            }
            fixture.write_text(
                "\ufeff" + "\n".join(
                    (
                        "-----BEGIN " + "PRIVATE KEY-----",
                        "-----BEGIN " + "ENCRYPTED PRIVATE KEY-----",
                        values["provider"],
                        values["github"],
                        values["aws"],
                        values["aws_temporary"],
                        "export " + "DATABASE_" + "URL=" + values["database"],
                        "SUPABASE_" + "SERVICE_ROLE_KEY = " + values["service_role"],
                        "LLM_" + "API_KEY=" + values["llm"],
                        "CONTEXT_TOKEN_" + "SECRET=" + values["context"],
                        values["https_url"],
                    )
                ),
                encoding="utf-8",
            )
            result = run_secret_scanner(fixture)

        assert_exit(self, result, 1)
        lines = result.stdout.splitlines()
        self.assertTrue(lines == sorted(lines), "scanner output is not sorted")
        expected_counts = {
            "PRIVATE_KEY_HEADER": 2,
            "PROVIDER_KEY": 1,
            "GITHUB_TOKEN": 1,
            "AWS_ACCESS_KEY": 2,
            "NONEMPTY_SECRET_ASSIGNMENT": 4,
            "CREDENTIAL_URL": 2,
        }
        for rule, count in expected_counts.items():
            expected = f"rule={rule} count={count}"
            self.assertTrue(any(expected in line for line in lines), f"missing rule={rule}")
        self.assertTrue(all("비밀 후보.txt rule=" in line for line in lines))
        assert_no_disclosure(self, result, list(values.values()))

    def test_blank_assignments_are_clean_and_missing_input_is_operational_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sejong scanner clean ") as directory:
            fixture = Path(directory) / "clean.env"
            fixture.write_text(
                "DATABASE_" + "URL=\nLLM_" + "API_KEY=\nCONTEXT_TOKEN_" + "SECRET=\n",
                encoding="utf-8",
            )
            clean = run_secret_scanner(fixture)
            missing = run_secret_scanner(Path(directory) / "missing-sentinel-value.txt")
        assert_exit(self, clean, 0)
        self.assertFalse(clean.stdout or clean.stderr, "clean scan emitted output")
        self.assertGreaterEqual(missing.returncode, 2, result_diagnostic(missing))
        self.assertTrue(
            "rule=INPUT_MISSING count=1" in missing.stdout,
            "missing input rule not reported",
        )
        self.assertFalse(
            "missing-sentinel-value" in missing.stderr,
            "operational stderr disclosed the input path",
        )

    def test_empty_file_is_clean(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sejong scanner empty ") as directory:
            fixture = Path(directory) / "empty.txt"
            fixture.touch()
            result = run_secret_scanner(fixture)

        assert_exit(self, result, 0)
        self.assertFalse(result.stdout or result.stderr, "empty file scan emitted output")

    def test_multiple_explicit_unicode_paths_are_scanned_in_one_ps51_invocation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="세종 scanner paths ") as directory:
            clean_path = Path(directory) / "깨끗한 파일.env"
            leak_path = Path(directory) / "탐지 파일.txt"
            value = "sk-" + ("m" * 32)
            clean_path.write_text("LLM_" + "API_KEY=\n", encoding="utf-8")
            leak_path.write_text(value, encoding="utf-8")

            result = run_secret_scanner(clean_path, leak_path)

        assert_exit(self, result, 1)
        self.assertFalse(result.stderr, "multi-path scan wrote to stderr")
        self.assertTrue(leak_path.name in result.stdout, "second explicit path was not scanned")
        self.assertFalse(clean_path.name in result.stdout, "clean explicit path was reported")
        assert_no_disclosure(self, result, [value])

    def test_default_scan_self_scans_and_honors_active_file_boundaries(self) -> None:
        active = ROOT / "scanner 한글 active.txt"
        excluded = [
            ROOT / "legacy" / "scanner ignored.txt",
            ROOT / "cache" / "scanner ignored.txt",
            ROOT / "quarantine" / "scanner ignored.txt",
            ROOT / "build" / "scanner ignored.txt",
        ]
        created_directories: list[Path] = []
        value = "sk-" + ("x" * 32)
        try:
            self_scan = run_secret_scanner()
            assert_exit(self, self_scan, 0)

            active.write_text(value, encoding="utf-8")
            found = run_secret_scanner()
            assert_exit(self, found, 1)
            expected = f"{active.name} rule=PROVIDER_KEY count=1"
            self.assertTrue(expected in found.stdout, "untracked active file was not scanned")
            assert_no_disclosure(self, found, [value])
            active.unlink()

            for path in excluded:
                if not path.parent.exists():
                    path.parent.mkdir()
                    created_directories.append(path.parent)
                path.write_text(value, encoding="utf-8")
            ignored = run_secret_scanner()
            assert_exit(self, ignored, 0)
        finally:
            active.unlink(missing_ok=True)
            for path in excluded:
                path.unlink(missing_ok=True)
            for directory in reversed(created_directories):
                directory.rmdir()


class BrowserBundleScannerTest(unittest.TestCase):
    def test_missing_or_empty_browser_artifact_scope_is_operational_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sejong bundle missing ") as directory:
            base = Path(directory)
            missing = run_bundle_scanner(base / "missing")
            empty_build = base / ".next"
            empty_build.mkdir()
            empty = run_bundle_scanner(empty_build)
        assert_exit(self, missing, 2)
        self.assertTrue(
            "rule=BUILD_DIRECTORY_MISSING count=1" in missing.stdout,
            "missing build rule not reported",
        )
        assert_exit(self, empty, 2)
        self.assertTrue(
            "rule=NO_BROWSER_ARTIFACTS count=1" in empty.stdout,
            "empty browser scope rule not reported",
        )

    def test_clean_static_html_and_rsc_artifacts_return_zero(self) -> None:
        with tempfile.TemporaryDirectory(prefix="세종 bundle clean ") as directory:
            build = Path(directory) / ".next"
            files = (
                build / "static" / "chunks" / "clean.js",
                build / "server" / "app" / "index.html",
                build / "server" / "app" / "index.segment.rsc",
                build / "server" / "pages" / "index.html",
            )
            for path in files:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"public-browser-content")
            result = run_bundle_scanner(build)
        assert_exit(self, result, 0)
        self.assertFalse(result.stdout or result.stderr, "clean bundle scan emitted output")

    def test_only_browser_transmitted_scope_reports_sorted_rules_without_values(self) -> None:
        with tempfile.TemporaryDirectory(prefix="세종 bundle leak ") as directory:
            build = Path(directory) / ".next"
            static_file = build / "static" / "chunks" / "marker.bin"
            rsc_file = build / "server" / "app" / "page.segment.rsc"
            html_file = build / "server" / "pages" / "index.html"
            server_only_file = build / "server" / "app" / "page.js"
            for path in (static_file, rsc_file, html_file, server_only_file):
                path.parent.mkdir(parents=True, exist_ok=True)

            markers = (
                "SUPABASE_" + "SERVICE_ROLE_KEY",
                "LLM_" + "API_KEY",
                "CONTEXT_TOKEN_" + "SECRET",
                "DATABASE_" + "URL",
            )
            sentinel = "sentinel-" + ("z" * 24)
            static_file.write_bytes(" ".join(markers).encode("utf-8"))
            rsc_file.write_bytes(sentinel.encode("utf-8"))
            html_file.write_bytes(markers[0].encode("utf-8"))
            server_only_file.write_bytes((" ".join(markers) + sentinel).encode("utf-8"))

            result = run_bundle_scanner(build, sentinel)

        assert_exit(self, result, 1)
        lines = result.stdout.splitlines()
        self.assertTrue(lines == sorted(lines), "bundle scanner output is not sorted")
        for expected in (
            "static/chunks/marker.bin rule=SERVER_SECRET_NAME count=4",
            "server/app/page.segment.rsc rule=SECRET_SENTINEL count=1",
            "server/pages/index.html rule=SERVER_SECRET_NAME count=1",
        ):
            self.assertTrue(expected in lines, "expected browser artifact rule is missing")
        self.assertFalse(
            any("server/app/page.js" in line for line in lines),
            "server-only JavaScript was scanned",
        )
        assert_no_disclosure(self, result, [*markers, sentinel])

    def test_bundle_scanner_does_not_follow_symbolic_links(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sejong bundle link ") as directory:
            base = Path(directory)
            build = base / ".next"
            static = build / "static"
            static.mkdir(parents=True)
            (static / "clean.js").write_bytes(b"public")
            outside = base / "outside.txt"
            outside.write_bytes(("LLM_" + "API_KEY").encode("utf-8"))
            link = static / "linked.js"
            try:
                link.symlink_to(outside)
            except OSError as error:
                self.skipTest(f"symbolic links unavailable: {error.__class__.__name__}")
            result = run_bundle_scanner(build)
        assert_exit(self, result, 0)


if __name__ == "__main__":
    unittest.main()
