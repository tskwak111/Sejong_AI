from __future__ import annotations

import ctypes
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import tomllib
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
PIN_PATH = ROOT / "scripts" / "supabase-cli.version.json"
BOOTSTRAP_PATH = ROOT / "scripts" / "bootstrap_supabase.ps1"
PATCHED_BOOTSTRAP_PATH = ROOT / "scripts" / "bootstrap_patched_supabase.ps1"
PATCHED_RUNTIME_RELATIVE = Path(
    ".tools/supabase/v2.109.1-sejong-loopback/supabase.exe"
)
CONFIG_PATH = ROOT / "supabase" / "config.toml"
SEED_PATH = ROOT / "supabase" / "seed.sql"
INITIAL_RELEASE_SEED_PATH = (
    ROOT / "data" / "official" / "releases" / "0.1.0-initial.1" / "seed.sql"
)
RELEASE_SEED_PATH = (
    ROOT / "data" / "official" / "releases" / "0.1.0-initial.2" / "seed.sql"
)
PROVISION_PATH = ROOT / "scripts" / "provision_local_database_login.py"
SQL_RUNNER_PATH = ROOT / "scripts" / "run_database_sql.py"
DATABASE_RUNNER_PATH = ROOT / "scripts" / "verify_database.ps1"
CAPABILITY_MIGRATION_PATH = (
    ROOT / "supabase" / "migrations" / "20260716000300_capabilities_and_functions.sql"
)
CAPABILITY_TEST_PATH = ROOT / "supabase" / "tests" / "database" / "003_capabilities_test.sql"
ADMIN_READ_MIGRATION_PATH = (
    ROOT
    / "supabase"
    / "migrations"
    / "20260722000650_local_admin_read_capabilities.sql"
)
ADMIN_READ_ROLLBACK_PATH = (
    ROOT
    / "database"
    / "rollbacks"
    / "20260722000650_local_admin_read_capabilities.rollback.sql"
)
ADMIN_READ_TEST_PATH = (
    ROOT / "supabase" / "tests" / "database" / "007_local_admin_read_capabilities_test.sql"
)
IDEMPOTENCY_MIGRATION_PATH = (
    ROOT / "supabase" / "migrations" / "20260722000660_chat_idempotency.sql"
)
IDEMPOTENCY_ROLLBACK_PATH = (
    ROOT / "database" / "rollbacks" / "20260722000660_chat_idempotency.rollback.sql"
)
IDEMPOTENCY_TEST_PATH = (
    ROOT / "supabase" / "tests" / "database" / "008_chat_idempotency_test.sql"
)
CANDIDATE_BINDING_MIGRATION_PATH = (
    ROOT / "supabase" / "migrations" / "20260722000670_candidate_public_id_binding.sql"
)
CANDIDATE_BINDING_ROLLBACK_PATH = (
    ROOT / "database" / "rollbacks" / "20260722000670_candidate_public_id_binding.rollback.sql"
)
CANDIDATE_BINDING_TEST_PATH = (
    ROOT / "supabase" / "tests" / "database" / "009_candidate_public_id_binding_test.sql"
)
CIVIC_SCOPE_GAP_MIGRATION_PATH = (
    ROOT / "supabase" / "migrations" / "20260727000680_civic_scope_gap_queue.sql"
)
CIVIC_SCOPE_GAP_ROLLBACK_PATH = (
    ROOT / "database" / "rollbacks" / "20260727000680_civic_scope_gap_queue.rollback.sql"
)
CIVIC_SCOPE_GAP_TEST_PATH = (
    ROOT / "supabase" / "tests" / "database" / "010_civic_scope_gap_queue_test.sql"
)
PRIVILEGED_SEARCH_PATH_MIGRATION_PATH = (
    ROOT
    / "supabase"
    / "migrations"
    / "20260727000700_privileged_function_search_path.sql"
)
PRIVILEGED_SEARCH_PATH_ROLLBACK_PATH = (
    ROOT
    / "database"
    / "rollbacks"
    / "20260727000700_privileged_function_search_path.rollback.sql"
)
PRIVILEGED_SEARCH_PATH_TEST_PATH = (
    ROOT
    / "supabase"
    / "tests"
    / "database"
    / "011_privileged_function_search_path_test.sql"
)
EXPECTED_PIN = {
    "version": "2.109.1",
    "release": "v2.109.1",
    "published_at": "2026-07-07T09:00:28Z",
    "asset": "supabase_2.109.1_windows_amd64.zip",
    "size_bytes": 75309565,
    "url": (
        "https://github.com/supabase/cli/releases/download/v2.109.1/"
        "supabase_2.109.1_windows_amd64.zip"
    ),
    "sha256": "d0d270692cf78b8aa56545461f02cdf929ce9bb94e95e5e66404fd0e7d2c0c16",
}
CHILD_OUTPUT_SENTINEL = "postgresql://synthetic.invalid/private-question-sentinel"


def _database_dsn(scheme: str, authority: str) -> str:
    return f"{scheme}://{authority}"


class MembershipGuardStructureTests(unittest.TestCase):
    def assert_independent_schema_owner_options(self, block: str) -> None:
        for option in ("admin_option", "inherit_option", "set_option"):
            self.assertEqual(1, block.count(f"memberships.{option}"), option)
        self.assertNotIn(
            "memberships.inherit_option\n      AND memberships.set_option",
            block,
        )

    def test_migration_and_pgtap_use_three_independent_option_checks(self) -> None:
        migration = CAPABILITY_MIGRATION_PATH.read_text(encoding="utf-8")
        migration_block = migration.split("IF NOT EXISTS (", maxsplit=1)[1].split(
            "OR NOT EXISTS (\n       SELECT 1 FROM pg_catalog.pg_auth_members AS memberships\n"
            "       WHERE memberships.roleid = v_backend_oid",
            maxsplit=1,
        )[0]
        self.assert_independent_schema_owner_options(migration_block)

        pgtap = CAPABILITY_TEST_PATH.read_text(encoding="utf-8")
        pgtap_block = pgtap.split("SELECT ok(", maxsplit=1)[1].split(
            "'migration user keeps ADMIN, INHERIT, and SET for schema owner'",
            maxsplit=1,
        )[0]
        self.assert_independent_schema_owner_options(pgtap_block)


class MvpDatabaseAdditionStructureTests(unittest.TestCase):
    def test_new_migrations_rollbacks_and_pgtap_files_are_transaction_bounded(self) -> None:
        for path in (
            ADMIN_READ_MIGRATION_PATH,
            ADMIN_READ_ROLLBACK_PATH,
            ADMIN_READ_TEST_PATH,
            IDEMPOTENCY_MIGRATION_PATH,
            IDEMPOTENCY_ROLLBACK_PATH,
            IDEMPOTENCY_TEST_PATH,
            CANDIDATE_BINDING_MIGRATION_PATH,
            CANDIDATE_BINDING_ROLLBACK_PATH,
            CANDIDATE_BINDING_TEST_PATH,
            CIVIC_SCOPE_GAP_MIGRATION_PATH,
            CIVIC_SCOPE_GAP_ROLLBACK_PATH,
            CIVIC_SCOPE_GAP_TEST_PATH,
            PRIVILEGED_SEARCH_PATH_MIGRATION_PATH,
            PRIVILEGED_SEARCH_PATH_ROLLBACK_PATH,
            PRIVILEGED_SEARCH_PATH_TEST_PATH,
        ):
            source = path.read_text(encoding="utf-8")
            self.assertTrue(source.startswith("BEGIN;\n"), path.name)
            self.assertRegex(source, r"(?m)^(?:COMMIT|ROLLBACK);\s*$", path.name)

    def test_public_hardening_is_exact_property_only_allowlist(self) -> None:
        migration = PRIVILEGED_SEARCH_PATH_MIGRATION_PATH.read_text(encoding="utf-8")
        rollback = PRIVILEGED_SEARCH_PATH_ROLLBACK_PATH.read_text(encoding="utf-8")
        pgtap = PRIVILEGED_SEARCH_PATH_TEST_PATH.read_text(encoding="utf-8")

        alter_pattern = re.compile(
            r"ALTER FUNCTION (app_(?:api|private)\.[^(]+\([^)]*\))\s+"
            r"SET search_path = pg_catalog(?:, pg_temp)?;"
        )
        forward = alter_pattern.findall(migration)
        reverse = alter_pattern.findall(rollback)

        self.assertEqual(len(forward), 22)
        self.assertEqual(len(set(forward)), 22)
        self.assertEqual(reverse, forward)
        self.assertEqual(migration.count("SET search_path = pg_catalog, pg_temp;"), 22)
        self.assertEqual(rollback.count("SET search_path = pg_catalog;"), 21)
        self.assertEqual(rollback.count("SET search_path = pg_catalog, pg_temp;"), 1)
        for forbidden in (
            "CREATE FUNCTION",
            "CREATE OR REPLACE FUNCTION",
            "DROP FUNCTION",
            "GRANT ",
            "REVOKE ",
            "ALTER TABLE",
            "UPDATE ",
            "INSERT ",
            "DELETE ",
            "EXECUTE ",
        ):
            self.assertNotIn(forbidden, migration)
        self.assertIn("SELECT plan(6);", pgtap)
        self.assertIn("search_path=pg_catalog, pg_temp", pgtap)
        self.assertIn("md5(functions.prosrc)", pgtap)
        self.assertIn("pg_catalog.aclexplode", pgtap)

    def test_admin_read_files_expose_and_compensate_only_four_capabilities(self) -> None:
        migration = ADMIN_READ_MIGRATION_PATH.read_text(encoding="utf-8")
        rollback = ADMIN_READ_ROLLBACK_PATH.read_text(encoding="utf-8")
        pgtap = ADMIN_READ_TEST_PATH.read_text(encoding="utf-8")
        names = (
            "list_failed_questions",
            "get_failed_question",
            "list_kb_candidates",
            "get_kb_candidate",
        )

        for name in names:
            self.assertIn(f"CREATE FUNCTION app_api.{name}", migration)
            self.assertIn(f"DROP FUNCTION app_api.{name}", rollback)
            self.assertIn(name, pgtap)
        self.assertNotIn("GRANT SELECT ON app_private", migration)

    def test_idempotency_files_keep_correlation_identity_out_and_bound_lease(self) -> None:
        migration = IDEMPOTENCY_MIGRATION_PATH.read_text(encoding="utf-8")
        rollback = IDEMPOTENCY_ROLLBACK_PATH.read_text(encoding="utf-8")
        pgtap = IDEMPOTENCY_TEST_PATH.read_text(encoding="utf-8")

        self.assertNotIn("claim_request_id", migration)
        self.assertIn("claim_token uuid", migration)
        self.assertIn("lease_expires_at timestamptz", migration)
        self.assertIn("interval '5 minutes'", migration)
        self.assertIn("interval '24 hours'", migration)
        self.assertIn("DROP TABLE app_private.chat_idempotency", rollback)
        self.assertIn("SELECT plan(23);", pgtap)
        self.assertIn("the old claim token cannot complete reacquired work", pgtap)

    def test_candidate_binding_is_one_backend_only_fixed_capability(self) -> None:
        migration = CANDIDATE_BINDING_MIGRATION_PATH.read_text(encoding="utf-8")
        rollback = CANDIDATE_BINDING_ROLLBACK_PATH.read_text(encoding="utf-8")
        pgtap = CANDIDATE_BINDING_TEST_PATH.read_text(encoding="utf-8")

        self.assertEqual(migration.count("CREATE FUNCTION app_api."), 1)
        self.assertIn(
            "CREATE FUNCTION app_api.approve_kb_candidate_with_public_id(", migration
        )
        self.assertIn(
            "DROP FUNCTION app_api.approve_kb_candidate_with_public_id"
            "(uuid, text, text, text, text)",
            rollback,
        )
        self.assertIn("SET search_path = pg_catalog, pg_temp", migration)
        self.assertIn("OWNER TO sejong_schema_owner", migration)
        self.assertIn("FROM PUBLIC, anon, authenticated, sejong_backend", migration)
        self.assertIn("TO sejong_backend", migration)
        self.assertIn("app_api.approve_kb_candidate(", migration)
        self.assertIn("KB-WASTE-03", pgtap)
        self.assertIn("SELECT plan(36);", pgtap)

    def test_civic_scope_gap_queue_is_bounded_backend_only_and_compensated(self) -> None:
        migration = CIVIC_SCOPE_GAP_MIGRATION_PATH.read_text(encoding="utf-8")
        rollback = CIVIC_SCOPE_GAP_ROLLBACK_PATH.read_text(encoding="utf-8")
        pgtap = CIVIC_SCOPE_GAP_TEST_PATH.read_text(encoding="utf-8")
        names = (
            "record_civic_scope_gap",
            "list_civic_scope_gaps",
            "review_civic_scope_gap",
            "purge_expired_civic_scope_gap_text",
        )

        self.assertIn("CREATE TABLE app_private.civic_scope_gaps", migration)
        self.assertIn("interval '30 days'", migration)
        self.assertIn("status IN ('NEW', 'PLANNED', 'DISMISSED')", migration)
        self.assertNotIn("failed_question_id", migration)
        self.assertNotIn("candidate_id", migration)
        self.assertNotIn("kb_document_id", migration)
        for forbidden in (
            "raw_question",
            "answer_snapshot",
            "source_snapshot",
            "context_token",
        ):
            self.assertNotIn(forbidden, migration)

        for name in names:
            self.assertIn(f"CREATE FUNCTION app_api.{name}", migration)
            self.assertIn(f"DROP FUNCTION app_api.{name}", rollback)
            self.assertIn(name, pgtap)

        self.assertEqual(migration.count("CREATE FUNCTION app_api."), 4)
        self.assertIn("SET search_path = pg_catalog, pg_temp", migration)
        self.assertIn("OWNER TO sejong_schema_owner", migration)
        self.assertIn("FROM PUBLIC, anon, authenticated, sejong_backend", migration)
        self.assertIn("TO sejong_backend", migration)
        self.assertIn("DROP TABLE app_private.civic_scope_gaps", rollback)
        self.assertIn("SELECT plan(22);", pgtap)
        self.assertIn("terminal scope-gap rows cannot be reviewed twice", pgtap)
        self.assertIn("purge nulls only expired masked text", pgtap)


def powershell_executable() -> str:
    executable = shutil.which("powershell.exe") or shutil.which("powershell")
    if executable is None:
        raise AssertionError("Windows PowerShell 5.1+ is required")
    return executable


def windows_process_is_alive(process_id: int) -> bool:
    if process_id <= 0:
        raise AssertionError("synthetic process id must be positive")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [ctypes.c_uint, ctypes.c_bool, ctypes.c_uint]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.GetExitCodeProcess.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint),
    ]
    kernel32.GetExitCodeProcess.restype = ctypes.c_bool
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_bool
    handle = kernel32.OpenProcess(0x1000, False, process_id)
    if not handle:
        return False
    try:
        exit_code = ctypes.c_uint()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            raise AssertionError("cannot inspect synthetic descendant process")
        return exit_code.value == 259
    finally:
        kernel32.CloseHandle(handle)


def terminate_synthetic_process_tree(process_id: int) -> None:
    taskkill = shutil.which("taskkill.exe") or shutil.which("taskkill")
    if taskkill is None:
        raise AssertionError("taskkill is required for synthetic process cleanup")
    subprocess.run(
        [taskkill, "/PID", str(process_id), "/T", "/F"],
        capture_output=True,
        check=False,
        timeout=10,
    )
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not windows_process_is_alive(process_id):
            return
        time.sleep(0.05)
    raise AssertionError("synthetic descendant cleanup did not terminate the process tree")


def observe_and_cleanup_synthetic_descendant(pid_path: Path) -> list[str]:
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline and not pid_path.is_file():
        time.sleep(0.05)
    if not pid_path.is_file():
        return ["descendant", "pid-missing"]
    process_id = int(pid_path.read_text(encoding="utf-8").strip())
    was_alive = windows_process_is_alive(process_id)
    observation = [
        "descendant",
        (
            "alive-before-harness-cleanup"
            if was_alive
            else "dead-before-harness-cleanup"
        ),
    ]
    if was_alive:
        terminate_synthetic_process_tree(process_id)
    if windows_process_is_alive(process_id):
        raise AssertionError("synthetic descendant survived harness cleanup")
    return observation


def copy_tooling_fixture(root: Path, *, url: str | None = None) -> Path:
    if not BOOTSTRAP_PATH.is_file():
        raise AssertionError(f"missing required tooling file: {BOOTSTRAP_PATH.name}")
    if not PIN_PATH.is_file():
        raise AssertionError(f"missing required tooling file: {PIN_PATH.name}")
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(BOOTSTRAP_PATH, scripts / BOOTSTRAP_PATH.name)
    pin = json.loads(PIN_PATH.read_text(encoding="utf-8"))
    if url is not None:
        pin["url"] = url
    (scripts / PIN_PATH.name).write_text(
        json.dumps(pin, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return scripts / BOOTSTRAP_PATH.name


def run_bootstrap(
    script: Path, *arguments: str, cwd: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            powershell_executable(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            *arguments,
        ],
        cwd=cwd,
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    )


def load_module(path: Path, name: str) -> ModuleType:
    if not path.is_file():
        raise AssertionError(f"missing required tooling file: {path.name}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load tooling module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_database_runner_with_supabase_capture(
    source: str,
    *,
    full_path: bool = False,
    failure_phase: str | None = None,
    include_docker_invocations: bool = False,
    network_state: str = "absent",
    runtime_state: str = "none",
    started_runtime_state: str = "safe",
    docker_server_version: str = "29.2.1",
    stop_failure: bool = False,
    stop_leaves_runtime: bool = False,
    runner_arguments: tuple[str, ...] = (),
    capture_patched_bootstrap: bool = False,
    patched_bootstrap_exit_code: int = 0,
    include_patched_runtime: bool = True,
    include_fallback_decoys: bool = False,
    bootstrap_spawns_inheriting_descendant: bool = False,
) -> tuple[subprocess.CompletedProcess[str], list[list[str]]]:
    if patched_bootstrap_exit_code not in {0, 1, 2}:
        raise AssertionError("patched bootstrap exit code must be 0, 1, or 2")
    runtime_executable = ROOT / "apps" / "api" / ".venv" / "Scripts" / "python.exe"
    if not runtime_executable.is_file():
        raise AssertionError("API venv Python is required for the synthetic runner fixture")

    with tempfile.TemporaryDirectory(prefix="sejong database runner ") as directory:
        root = Path(directory)
        scripts = root / "scripts"
        fake_bin = root / "fake-bin"
        supabase_dir = root / PATCHED_RUNTIME_RELATIVE.parent
        python_dir = root / "apps" / "api" / ".venv" / "Scripts"
        for path in (scripts, fake_bin, supabase_dir, python_dir):
            path.mkdir(parents=True, exist_ok=True)

        capture_path = root / "supabase-invocations.jsonl"
        runtime_path = root / "synthetic-docker-runtime.json"
        descendant_pid_path = root / "synthetic-descendant.pid"
        runtime_path.write_text(
            json.dumps(
                {
                    "network": network_state,
                    "runtime": runtime_state,
                }
            ),
            encoding="utf-8",
        )
        if full_path:
            restoration_line = "        Restore-ProcessEnvironment -Saved $savedEnvironment"
            if source.count(restoration_line) != 1:
                raise AssertionError("runner restoration point must be unique")
            instrumentation = restoration_line + '''
        $adminState = if (
            [Environment]::GetEnvironmentVariable(
                "SEJONG_ADMIN_DATABASE_URL", "Process"
            ) -ceq $env:SEJONG_SYNTHETIC_INITIAL_ADMIN
        ) { "restored" } else { "changed" }
        $backendState = if (
            [Environment]::GetEnvironmentVariable(
                "SEJONG_DB_TEST_URL", "Process"
            ) -ceq $env:SEJONG_SYNTHETIC_INITIAL_BACKEND
        ) { "restored" } else { "changed" }
        $environmentLine = '["environment","' + $adminState + '","' + $backendState + '"]'
        [System.IO.File]::AppendAllText(
            $env:SEJONG_SYNTHETIC_SUPABASE_CAPTURE,
            $environmentLine + [Environment]::NewLine,
            [System.Text.Encoding]::UTF8
        )
'''
            source = source.replace(restoration_line, instrumentation)

        runner = scripts / DATABASE_RUNNER_PATH.name
        runner.write_text(source, encoding="utf-8")
        bootstrap_capture_source = r'''
$bootstrapEvent = @(
    "bootstrap",
    [System.IO.Path]::GetFileName($MyInvocation.MyCommand.Path)
) + @($args)
$bootstrapLine = ConvertTo-Json -InputObject $bootstrapEvent -Compress
[System.IO.File]::AppendAllText(
    $env:SEJONG_SYNTHETIC_SUPABASE_CAPTURE,
    $bootstrapLine + [Environment]::NewLine,
    [System.Text.Encoding]::UTF8
)
'''
        bootstrap_source = ""
        if capture_patched_bootstrap:
            bootstrap_source += bootstrap_capture_source
        provision_source = "# synthetic fixture\n"
        sql_runner_source = "# synthetic fixture\n"
        if full_path:
            bootstrap_source += (
                f'[Console]::Out.WriteLine("{CHILD_OUTPUT_SENTINEL}")\n'
                f'[Console]::Error.WriteLine("{CHILD_OUTPUT_SENTINEL}")\n'
            )
            provision_source = f'''
import json
import os
import sys
from pathlib import Path

capture = Path(os.environ["SEJONG_SYNTHETIC_SUPABASE_CAPTURE"])
with capture.open("a", encoding="utf-8") as stream:
    stream.write(json.dumps(["provision"]) + "\\n")
environment_path = Path.cwd() / "apps" / "api" / ".env"
environment_path.parent.mkdir(parents=True, exist_ok=True)
environment_path.write_text(
    "DATABASE_URL=postgresql://synthetic.invalid/backend\\n", encoding="utf-8"
)
print({CHILD_OUTPUT_SENTINEL!r})
print({CHILD_OUTPUT_SENTINEL!r}, file=sys.stderr)
raise SystemExit(0)
'''
            sql_runner_source = f'''
import json
import os
import sys
from pathlib import Path

event = ["sql", *(Path(value).name for value in sys.argv[1:])]
with open(os.environ["SEJONG_SYNTHETIC_SUPABASE_CAPTURE"], "a", encoding="utf-8") as stream:
    stream.write(json.dumps(event) + "\\n")
print({CHILD_OUTPUT_SENTINEL!r})
print({CHILD_OUTPUT_SENTINEL!r}, file=sys.stderr)
raise SystemExit(0)
'''
        if bootstrap_spawns_inheriting_descendant:
            bootstrap_source += r'''
$descendantStartInfo = New-Object System.Diagnostics.ProcessStartInfo
$descendantStartInfo.FileName = Join-Path $env:SystemRoot "System32\PING.EXE"
$descendantStartInfo.Arguments = "-n 31 127.0.0.1"
$descendantStartInfo.UseShellExecute = $false
$descendantStartInfo.CreateNoWindow = $true
$descendant = [System.Diagnostics.Process]::Start($descendantStartInfo)
[System.IO.File]::WriteAllText(
    $env:SEJONG_SYNTHETIC_DESCENDANT_PID,
    [string]$descendant.Id,
    (New-Object System.Text.UTF8Encoding($false))
)
Start-Sleep -Seconds 30
'''
        bootstrap_source += f"exit {patched_bootstrap_exit_code}\n"
        (scripts / PATCHED_BOOTSTRAP_PATH.name).write_text(
            bootstrap_source,
            encoding="utf-8",
        )
        if include_fallback_decoys:
            (scripts / BOOTSTRAP_PATH.name).write_text(
                bootstrap_capture_source + "exit 0\n",
                encoding="utf-8",
            )
        (scripts / PROVISION_PATH.name).write_text(provision_source, encoding="utf-8")
        (scripts / SQL_RUNNER_PATH.name).write_text(sql_runner_source, encoding="utf-8")

        runtime_destinations = [
            fake_bin / "docker.exe",
            python_dir / "python.exe",
        ]
        if include_patched_runtime:
            runtime_destinations.append(root / PATCHED_RUNTIME_RELATIVE)
        if include_fallback_decoys:
            stock_decoy = root / ".tools" / "supabase" / "v2.109.1" / "supabase.exe"
            stock_decoy.parent.mkdir(parents=True, exist_ok=True)
            runtime_destinations.extend((stock_decoy, fake_bin / "supabase.exe"))
        for destination in runtime_destinations:
            shutil.copy2(runtime_executable, destination)

        version_source = "raise SystemExit(0)\n"
        if full_path:
            version_source = f'''
import sys
print({CHILD_OUTPUT_SENTINEL!r})
print({CHILD_OUTPUT_SENTINEL!r}, file=sys.stderr)
raise SystemExit(0)
'''
        docker_version_source = f'''
import json
import os

with open(os.environ["SEJONG_SYNTHETIC_SUPABASE_CAPTURE"], "a", encoding="utf-8") as stream:
    stream.write(json.dumps(["docker", "version"]) + "\\n")
print(os.environ["SEJONG_SYNTHETIC_DOCKER_SERVER_VERSION"])
raise SystemExit(0)
'''
        (root / "version").write_text(docker_version_source, encoding="utf-8")
        docker_network_source = '''
import json
import os
import sys
from pathlib import Path

capture = Path(os.environ["SEJONG_SYNTHETIC_SUPABASE_CAPTURE"])
state_path = Path(os.environ["SEJONG_SYNTHETIC_DOCKER_RUNTIME"])
state = json.loads(state_path.read_text(encoding="utf-8"))
event = ["docker", "network", *sys.argv[1:]]
with capture.open("a", encoding="utf-8") as stream:
    stream.write(json.dumps(event) + "\\n")
if sys.argv[1] == "ls":
    if state["network"] != "absent":
        print("sejong-ai-local-loopback")
    raise SystemExit(0)
if sys.argv[1] == "inspect":
    if state["network"] == "absent":
        raise SystemExit(1)
    driver = "overlay" if state["network"] == "driver-drift" else "bridge"
    host_ip = (
        "0.0.0.0" if state["network"] == "option-drift" else "127.0.0.1"
    )
    print(json.dumps({
        "Name": (
            "unexpected-loopback-network"
            if state["network"] == "name-drift"
            else "sejong-ai-local-loopback"
        ),
        "Driver": driver,
        "Scope": "swarm" if state["network"] == "scope-drift" else "local",
        "Options": {
            "com.docker.network.bridge.host_binding_ipv4": host_ip,
        },
        "Labels": {
            "com.sejong-ai.local-boundary": (
                "unexpected-owner"
                if state["network"] == "label-drift"
                else "sejong-ai-local"
            ),
        },
    }))
    raise SystemExit(0)
if sys.argv[1] == "create":
    state["network"] = "safe"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    raise SystemExit(0)
raise SystemExit(9)
'''
        (root / "network").write_text(docker_network_source, encoding="utf-8")
        docker_ps_source = '''
import json
import os
import sys
from pathlib import Path

capture = Path(os.environ["SEJONG_SYNTHETIC_SUPABASE_CAPTURE"])
state_path = Path(os.environ["SEJONG_SYNTHETIC_DOCKER_RUNTIME"])
state = json.loads(state_path.read_text(encoding="utf-8"))
with capture.open("a", encoding="utf-8") as stream:
    stream.write(json.dumps(["docker", "ps", *sys.argv[1:]]) + "\\n")
if state["runtime"] == "stopped" and "-a" not in sys.argv[1:]:
    raise SystemExit(0)
if state["runtime"] == "multiple":
    print("container-one")
    print("container-two")
elif state["runtime"] != "none":
    print("container-one")
raise SystemExit(0)
'''
        (root / "ps").write_text(docker_ps_source, encoding="utf-8")
        docker_inspect_source = '''
import json
import os
import sys
from pathlib import Path

capture = Path(os.environ["SEJONG_SYNTHETIC_SUPABASE_CAPTURE"])
state_path = Path(os.environ["SEJONG_SYNTHETIC_DOCKER_RUNTIME"])
state = json.loads(state_path.read_text(encoding="utf-8"))
container_id = sys.argv[1]
with capture.open("a", encoding="utf-8") as stream:
    stream.write(json.dumps(["docker", "inspect", container_id]) + "\\n")
runtime = state["runtime"]
requested_host_ip = (
    "0.0.0.0"
    if runtime in ("unsafe-ip", "unsafe-requested")
    else "127.0.0.1" if runtime == "unsafe-resolved" else ""
)
resolved_host_ip = (
    "0.0.0.0" if runtime in ("unsafe-ip", "unsafe-resolved") else "127.0.0.1"
)
bindings = None if runtime == "unpublished" else {
    "5432/tcp": [{
        "HostIp": requested_host_ip,
        "HostPort": "54323" if runtime == "wrong-host-port" else "54322",
    }],
}
if runtime == "mixed-bindings":
    bindings["5432/tcp"].append({"HostIp": "0.0.0.0", "HostPort": "54322"})
if runtime == "null-binding":
    bindings["5432/tcp"] = [None]
networks = {} if runtime == "wrong-network" else {
    "sejong-ai-local-loopback": {"NetworkID": "synthetic"},
}
name = (
    "/supabase_db_sejong-ai-local"
    if container_id == "container-one" and runtime != "name-drift"
    else "/unexpected_project_container"
)
print(json.dumps({
    "Name": name,
    "State": {"Running": runtime != "stopped"},
    "Config": {"Labels": {
        "com.supabase.cli.project": (
            "unexpected-project" if runtime == "label-drift" else "sejong-ai-local"
        ),
    }},
    "HostConfig": {
        "NetworkMode": (
            "bridge" if runtime == "networkmode-drift" else "sejong-ai-local-loopback"
        ),
        "PortBindings": bindings,
    },
    "NetworkSettings": {
        "Networks": networks,
        "Ports": None if runtime == "unpublished" else {
            "5432/tcp": [{
                "HostIp": resolved_host_ip,
                "HostPort": "54323" if runtime == "wrong-host-port" else "54322",
            }],
        },
    },
}))
raise SystemExit(0)
'''
        (root / "inspect").write_text(docker_inspect_source, encoding="utf-8")
        capture_program = f'''
import json
import os
import sys
from pathlib import Path

invocation = [Path(sys.argv[0]).name, *sys.argv[1:]]
with open(os.environ["SEJONG_SYNTHETIC_SUPABASE_CAPTURE"], "a", encoding="utf-8") as stream:
    stream.write(json.dumps(invocation) + "\\n")
if os.environ.get("SEJONG_SYNTHETIC_FULL_PATH") == "1":
    print({CHILD_OUTPUT_SENTINEL!r})
    print({CHILD_OUTPUT_SENTINEL!r}, file=sys.stderr)
if invocation in (
    ["db", "start"],
    ["start"],
    ["db", "start", "--network-id", "sejong-ai-local-loopback"],
):
    state_path = Path(os.environ["SEJONG_SYNTHETIC_DOCKER_RUNTIME"])
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["runtime"] = os.environ["SEJONG_SYNTHETIC_STARTED_RUNTIME"]
    state_path.write_text(json.dumps(state), encoding="utf-8")
    if os.environ.get("SEJONG_SYNTHETIC_FAILURE_PHASE") == "start":
        raise SystemExit(23)
    raise SystemExit(0)
if invocation == ["stop"]:
    if os.environ.get("SEJONG_SYNTHETIC_STOP_FAILURE") == "1":
        raise SystemExit(23)
    state_path = Path(os.environ["SEJONG_SYNTHETIC_DOCKER_RUNTIME"])
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if os.environ.get("SEJONG_SYNTHETIC_STOP_LEAVES_RUNTIME") != "1":
        state["runtime"] = "none"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    with open(os.environ["SEJONG_SYNTHETIC_SUPABASE_CAPTURE"], "a", encoding="utf-8") as stream:
        stream.write(json.dumps(["runtime", state["runtime"]]) + "\\n")
    raise SystemExit(0)
if invocation == ["db", "reset", "--local"]:
    raise SystemExit(0 if os.environ.get("SEJONG_SYNTHETIC_FULL_PATH") == "1" else 7)
if invocation == ["status", "-o", "env"]:
    print('DB_URL="postgresql://synthetic.invalid/admin"')
    raise SystemExit(0)
if invocation == ["test", "db"]:
    if os.environ.get("SEJONG_SYNTHETIC_FAILURE_PHASE") == "pgtap-one":
        raise SystemExit(17)
    raise SystemExit(0)
raise SystemExit(9)
'''
        commands = (
            ("db", "start", "stop", "status", "test")
            if full_path
            else ("db", "start", "stop")
        )
        for command in commands:
            (root / command).write_text(capture_program, encoding="utf-8")

        if full_path:
            pytest_package = root / "pytest"
            pytest_package.mkdir()
            (pytest_package / "__init__.py").write_text("", encoding="utf-8")
            (pytest_package / "__main__.py").write_text(
                f'''
import json
import os
import sys
from pathlib import Path

event = ["pytest", Path(sys.argv[-1]).name]
with open(os.environ["SEJONG_SYNTHETIC_SUPABASE_CAPTURE"], "a", encoding="utf-8") as stream:
    stream.write(json.dumps(event) + "\\n")
print({CHILD_OUTPUT_SENTINEL!r})
print({CHILD_OUTPUT_SENTINEL!r}, file=sys.stderr)
if os.environ.get("SEJONG_SYNTHETIC_FAILURE_PHASE") == "integration":
    raise SystemExit(19)
raise SystemExit(0)
''',
                encoding="utf-8",
            )

        environment = {
            key: os.environ[key]
            for key in ("COMSPEC", "PATHEXT", "SystemRoot", "TEMP", "TMP", "WINDIR")
            if key in os.environ
        }
        environment["PATH"] = str(fake_bin)
        environment["SEJONG_SYNTHETIC_SUPABASE_CAPTURE"] = str(capture_path)
        environment["SEJONG_SYNTHETIC_DOCKER_RUNTIME"] = str(runtime_path)
        environment["SEJONG_SYNTHETIC_STARTED_RUNTIME"] = started_runtime_state
        environment["SEJONG_SYNTHETIC_DOCKER_SERVER_VERSION"] = docker_server_version
        environment["SEJONG_SYNTHETIC_STOP_FAILURE"] = "1" if stop_failure else "0"
        environment["SEJONG_SYNTHETIC_STOP_LEAVES_RUNTIME"] = (
            "1" if stop_leaves_runtime else "0"
        )
        if bootstrap_spawns_inheriting_descendant:
            environment["SEJONG_SYNTHETIC_DESCENDANT_PID"] = str(
                descendant_pid_path
            )
        if full_path:
            environment["SEJONG_SYNTHETIC_FULL_PATH"] = "1"
            environment["SEJONG_SYNTHETIC_FAILURE_PHASE"] = failure_phase or ""
            environment["SEJONG_SYNTHETIC_INITIAL_ADMIN"] = "initial-admin-sentinel"
            environment["SEJONG_SYNTHETIC_INITIAL_BACKEND"] = "initial-backend-sentinel"
            environment["SEJONG_ADMIN_DATABASE_URL"] = environment[
                "SEJONG_SYNTHETIC_INITIAL_ADMIN"
            ]
            environment["SEJONG_DB_TEST_URL"] = environment[
                "SEJONG_SYNTHETIC_INITIAL_BACKEND"
            ]
        runner_command = [
            powershell_executable(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(runner),
            *runner_arguments,
        ]
        descendant_observation: list[str] | None = None
        harness_timed_out = False
        if bootstrap_spawns_inheriting_descendant:
            process = subprocess.Popen(
                runner_command,
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                errors="replace",
                env=environment,
            )
            try:
                stdout, stderr = process.communicate(timeout=25)
            except subprocess.TimeoutExpired:
                harness_timed_out = True
                descendant_observation = observe_and_cleanup_synthetic_descendant(
                    descendant_pid_path
                )
                if process.poll() is None:
                    process.kill()
                stdout, stderr = process.communicate(timeout=5)
            finally:
                if descendant_observation is None:
                    descendant_observation = observe_and_cleanup_synthetic_descendant(
                        descendant_pid_path
                    )
            result = subprocess.CompletedProcess(
                runner_command,
                process.returncode,
                stdout,
                stderr,
            )
        else:
            result = subprocess.run(
                runner_command,
                cwd=root,
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                env=environment,
                timeout=30,
            )
        invocations = []
        if capture_path.is_file():
            invocations = [
                json.loads(line)
                for line in capture_path.read_text(encoding="utf-8-sig").splitlines()
            ]
        if not include_docker_invocations:
            invocations = [
                invocation
                for invocation in invocations
                if not invocation or invocation[0] != "docker"
            ]
        if descendant_observation is not None:
            invocations.append(descendant_observation)
        if harness_timed_out:
            invocations.append(["runner", "test-harness-timeout"])
        return result, invocations


def assert_database_runner_discovery_surface_is_locked(script: str) -> None:
    binary_assignment = (
        r'$supabaseBinary = Join-Path $repositoryRoot '
        r'".tools\supabase\v2.109.1-sejong-loopback\supabase.exe"'
    )
    bootstrap_assignment = (
        '$bootstrapScript = Join-Path $scriptDirectory '
        '"bootstrap_patched_supabase.ps1"'
    )

    if script.count(binary_assignment) != 1:
        raise AssertionError("patched Supabase binary assignment must be unique")
    if script.count(bootstrap_assignment) != 1:
        raise AssertionError("patched Supabase bootstrap assignment must be unique")
    if script.count('"-VerifyOnly"') != 1:
        raise AssertionError("patched Supabase verify literal must be unique")
    expected_get_command_lines = [
        '    $dockerCommand = Get-Command "docker.exe" '
        "-CommandType Application -ErrorAction SilentlyContinue",
        '        $dockerCommand = Get-Command "docker" '
        "-CommandType Application -ErrorAction SilentlyContinue",
    ]
    get_command_lines = [
        line
        for line in script.splitlines()
        if re.search(r"(?i)(?<![\w-])Get-Command(?![\w-])", line)
    ]
    if get_command_lines != expected_get_command_lines:
        raise AssertionError("only the exact Docker Get-Command lookups are allowed")
    where_command_token = re.compile(
        r"(?im)(?:^|[;|{}()])\s*"
        r"(?:\$[A-Za-z_][\w:]*\s*=\s*)?"
        r"(?:where(?:\.exe)?|&\s*[\"']?where(?:\.exe)?[\"']?)"
        r"(?=\s|$)"
    )
    if where_command_token.search(script):
        raise AssertionError("PowerShell where command discovery is forbidden")
    if "$env:path" in script.lower():
        raise AssertionError("PATH-based Supabase discovery is forbidden")


class PatchedDatabaseRunnerSelectionTests(unittest.TestCase):
    def test_runner_uses_only_runtime_pinned_patched_cli(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        self.assertIn(
            r'".tools\supabase\v2.109.1-sejong-loopback\supabase.exe"',
            script,
        )
        self.assertIn('"bootstrap_patched_supabase.ps1"', script)
        self.assertNotIn(r'".tools\supabase\v2.109.1\supabase.exe"', script)
        self.assertNotIn('"bootstrap_supabase.ps1"', script)
        self.assertIn('"-VerifyOnly"', script)

    def test_runner_still_checks_actual_binding_before_reset(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        start = script.index('-Step "START-LOCAL-DATABASE"')
        inspect = script.index("Assert-LocalDatabaseRuntime", start)
        reset = script.index('-Step "RESET-DATABASE-ONE"', inspect)

        self.assertLess(start, inspect)
        self.assertLess(inspect, reset)

    def test_patched_verify_occurs_after_docker_version_and_before_every_db_phase(
        self,
    ) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        result, invocations = run_database_runner_with_supabase_capture(
            script,
            full_path=True,
            include_docker_invocations=True,
            capture_patched_bootstrap=True,
        )

        bootstrap_event = [
            "bootstrap",
            "bootstrap_patched_supabase.ps1",
            "-VerifyOnly",
        ]
        self.assertEqual(result.returncode, 0)
        self.assertFalse(result.stderr)
        self.assertEqual(invocations.count(bootstrap_event), 1)
        bootstrap_index = invocations.index(bootstrap_event)
        self.assertLess(invocations.index(["docker", "version"]), bootstrap_index)

        later_phases = {
            "network": lambda event: event[:2] == ["docker", "network"],
            "container-list": lambda event: event[:2] == ["docker", "ps"],
            "actual-binding": lambda event: event[:2] == ["docker", "inspect"],
            "start": lambda event: event
            == ["db", "start", "--network-id", "sejong-ai-local-loopback"],
            "reset": lambda event: event == ["db", "reset", "--local"],
            "status": lambda event: event == ["status", "-o", "env"],
            "credentials": lambda event: event == ["provision"],
            "sql": lambda event: bool(event) and event[0] == "sql",
            "pgtap": lambda event: event == ["test", "db"],
            "integration": lambda event: bool(event) and event[0] == "pytest",
        }
        for phase, predicate in later_phases.items():
            with self.subTest(phase=phase):
                indexes = [
                    index
                    for index, invocation in enumerate(invocations)
                    if predicate(invocation)
                ]
                self.assertTrue(indexes, f"missing synthetic phase: {phase}")
                self.assertLess(bootstrap_index, min(indexes))

    def test_patched_verify_failure_stops_before_network_and_database_work(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        result, invocations = run_database_runner_with_supabase_capture(
            script,
            include_docker_invocations=True,
            capture_patched_bootstrap=True,
            patched_bootstrap_exit_code=1,
        )

        self.assertEqual(result.returncode, 1)
        self.assertFalse(result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "[START] step=PREFLIGHT-DOCKER",
                "[PASS] step=PREFLIGHT-DOCKER",
                "[START] step=VERIFY-SUPABASE-VERSION",
                "[FAIL] step=VERIFY-SUPABASE-VERSION reason=child code=1",
            ],
        )
        self.assertEqual(
            invocations,
            [
                ["docker", "version"],
                ["bootstrap", "bootstrap_patched_supabase.ps1", "-VerifyOnly"],
            ],
        )

    def test_database_child_timeout_terminates_inheriting_descendant_and_restores_environment(
        self,
    ) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")
        verify_timeout_boundary = '''        -TimeoutMilliseconds 30000

    Ensure-LocalDatabaseNetwork `'''
        self.assertEqual(script.count(verify_timeout_boundary), 1)
        short_timeout_source = script.replace(
            verify_timeout_boundary,
            '''        -TimeoutMilliseconds 10000

    Ensure-LocalDatabaseNetwork `''',
        )

        started = time.monotonic()
        result, invocations = run_database_runner_with_supabase_capture(
            short_timeout_source,
            full_path=True,
            include_docker_invocations=True,
            capture_patched_bootstrap=True,
            bootstrap_spawns_inheriting_descendant=True,
        )
        elapsed = time.monotonic() - started

        self.assertEqual(result.returncode, 2)
        self.assertFalse(result.stderr)
        self.assertNotIn(CHILD_OUTPUT_SENTINEL, result.stdout)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "[START] step=PREFLIGHT-DOCKER",
                "[PASS] step=PREFLIGHT-DOCKER",
                "[START] step=VERIFY-SUPABASE-VERSION",
                "[FAIL] step=DATABASE-CHILD reason=timeout code=2",
            ],
        )
        self.assertEqual(
            invocations,
            [
                ["docker", "version"],
                ["bootstrap", "bootstrap_patched_supabase.ps1", "-VerifyOnly"],
                ["environment", "restored", "restored"],
                ["descendant", "dead-before-harness-cleanup"],
            ],
        )
        self.assertLess(elapsed, 25)

    def test_missing_patched_runtime_never_uses_stock_or_path_decoys(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        result, invocations = run_database_runner_with_supabase_capture(
            script,
            include_docker_invocations=True,
            include_patched_runtime=False,
            include_fallback_decoys=True,
            capture_patched_bootstrap=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertFalse(result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            "[FAIL] step=PREFLIGHT-LOCAL-FILES reason=missing code=2",
        )
        self.assertEqual(invocations, [])

    def test_runner_has_unique_patched_assignments_and_no_supabase_discovery(
        self,
    ) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        assert_database_runner_discovery_surface_is_locked(script)

    def test_discovery_guard_rejects_get_command_name_option_mutation(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")
        mutant = script + '\nGet-Command -Name "supabase.exe"\n'

        with self.assertRaises(AssertionError):
            assert_database_runner_discovery_surface_is_locked(mutant)

    def test_discovery_guard_rejects_get_command_parenthesized_mutation(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")
        mutant = script + '\nGet-Command ("supabase.exe")\n'

        with self.assertRaises(AssertionError):
            assert_database_runner_discovery_surface_is_locked(mutant)

    def test_discovery_guard_rejects_where_option_mutation(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")
        mutant = script + "\nwhere.exe /Q supabase.exe\n"

        with self.assertRaises(AssertionError):
            assert_database_runner_discovery_surface_is_locked(mutant)


def run_python_tool(path: Path, *arguments: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    if env is not None:
        environment.update(env)
    return subprocess.run(
        [str(ROOT / "apps" / "api" / ".venv" / "Scripts" / "python.exe"), "-B", str(path), *arguments],
        cwd=ROOT,
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        env=environment,
        timeout=20,
    )


class SupabaseToolPinTests(unittest.TestCase):
    def read_required_text(self, path: Path) -> str:
        self.assertTrue(path.is_file(), f"missing required tooling file: {path.name}")
        return path.read_text(encoding="utf-8")

    def test_exact_official_windows_pin(self) -> None:
        pin = json.loads(self.read_required_text(PIN_PATH))

        self.assertEqual(pin, EXPECTED_PIN)
        parsed_url = urlparse(pin["url"])
        self.assertEqual(parsed_url.scheme, "https")
        self.assertEqual(parsed_url.hostname, "github.com")

    def test_bootstrap_is_local_checksum_gated_and_non_secret(self) -> None:
        script = self.read_required_text(BOOTSTRAP_PATH)
        lowered = script.lower()

        self.assertIn("Get-FileHash", script)
        self.assertIn("Expand-Archive", script)
        self.assertIn(".tools\\supabase", script)
        self.assertIn("$PSScriptRoot", script)
        self.assertIn("--version", script)
        self.assertIn("[PASS] step=VERIFY-SUPABASE-ARCHIVE", script)
        self.assertIn("[PASS] step=VERIFY-SUPABASE-VERSION", script)
        self.assertIsNone(
            re.match(r"\A\s*param\(", script),
            "typed top-level binding can disclose argument errors before controlled handling",
        )
        self.assertIn('"-VerifyOnly"', script)
        self.assertIn('"-ArchivePath"', script)
        self.assertNotIn("Get-Location", script)
        for forbidden_operation in (
            "npm install",
            "winget",
            "supabase login",
            "supabase link",
            "supabase db push",
        ):
            self.assertNotIn(forbidden_operation, lowered)


class LocalDatabaseToolingContractTests(unittest.TestCase):
    def test_local_config_runs_database_only_and_exposes_no_app_schema(self) -> None:
        config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))

        self.assertEqual(config["project_id"], "sejong-ai-local")
        self.assertEqual(config["db"]["port"], 54322)
        self.assertEqual(config["db"]["major_version"], 17)
        self.assertFalse(config["api"]["enabled"])
        self.assertEqual(config["api"]["schemas"], ["public", "graphql_public"])
        self.assertEqual(config["api"]["extra_search_path"], ["public", "extensions"])
        self.assertFalse(config["auth"]["enabled"])
        self.assertFalse(config["realtime"]["enabled"])
        self.assertFalse(config["storage"]["enabled"])
        self.assertFalse(config["studio"]["enabled"])
        self.assertFalse(config["local_smtp"]["enabled"])
        self.assertNotIn("inbucket", config)
        self.assertFalse(config["analytics"]["enabled"])
        self.assertFalse(config["edge_runtime"]["enabled"])
        self.assertFalse(config["db"]["pooler"]["enabled"])
        self.assertFalse(config["db"]["seed"]["enabled"])
        self.assertEqual(config["db"]["seed"]["sql_paths"], ["./seed.sql"])
        exposed = config["api"]["schemas"] + config["api"]["extra_search_path"]
        self.assertNotIn("app_private", exposed)
        self.assertNotIn("app_api", exposed)

    def test_seed_dispatcher_matches_active_release_and_stays_db_disabled(self) -> None:
        config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))

        self.assertEqual(
            ROOT
            / "data"
            / "official"
            / "releases"
            / "0.1.0-initial.2"
            / "seed.sql",
            RELEASE_SEED_PATH,
        )
        if RELEASE_SEED_PATH.is_file():
            self.assertEqual(RELEASE_SEED_PATH.read_bytes(), SEED_PATH.read_bytes())
        else:
            self.assertEqual(
                INITIAL_RELEASE_SEED_PATH.read_bytes(),
                SEED_PATH.read_bytes(),
                "pre-publication dispatcher must remain byte-exact predecessor",
            )
        self.assertFalse(config["db"]["seed"]["enabled"])
        self.assertEqual(["./seed.sql"], config["db"]["seed"]["sql_paths"])

    def test_env_update_preserves_every_non_target_byte(self) -> None:
        module = load_module(PROVISION_PATH, "provision_local_database_login_test")
        self.assertEqual(module.ROLE_NAME, "sejong_local_login")
        self.assertEqual(module.TARGET_ENV_KEY, "DATABASE_URL")
        original = (
            b"# synthetic local configuration\r\n"
            b"APP_ENV=development\r\n"
            b"DATABASE_URL=old-local-value\r\n"
            b"\r\n"
            b"LLM_API_KEY=synthetic-deepseek-sentinel\r\n"
            b"LOG_LEVEL=INFO\r\n"
        )
        expected = original.replace(
            b"DATABASE_URL=old-local-value",
            b"DATABASE_URL=postgresql://local.invalid/new-value",
        )
        with tempfile.TemporaryDirectory(prefix="sejong env update ") as directory:
            env_path = Path(directory) / ".env"
            env_path.write_bytes(original)

            module.update_env_assignment(
                env_path,
                "DATABASE_URL",
                "postgresql://local.invalid/new-value",
            )

            self.assertEqual(env_path.read_bytes(), expected)

    def test_env_update_appends_target_without_rewriting_existing_bytes(self) -> None:
        module = load_module(PROVISION_PATH, "provision_local_database_login_append_test")
        original = b"# keep\nLLM_API_KEY=synthetic-deepseek-sentinel"
        with tempfile.TemporaryDirectory(prefix="sejong env append ") as directory:
            env_path = Path(directory) / ".env"
            env_path.write_bytes(original)

            module.update_env_assignment(env_path, "DATABASE_URL", "postgresql://local.invalid/new")

            self.assertEqual(
                env_path.read_bytes(),
                original + b"\nDATABASE_URL=postgresql://local.invalid/new\n",
            )

    def test_env_update_replace_failure_keeps_original_and_cleans_temp(self) -> None:
        module = load_module(PROVISION_PATH, "provision_local_database_login_atomic_test")
        original = (
            b"# synthetic local configuration\r\n"
            b"DATABASE_URL=old-local-value\r\n"
            b"LLM_API_KEY=synthetic-deepseek-sentinel\r\n"
        )
        expected_staged = original.replace(
            b"DATABASE_URL=old-local-value",
            b"DATABASE_URL=postgresql://local.invalid/rotated",
        )
        with tempfile.TemporaryDirectory(prefix="sejong env atomic ") as directory:
            root = Path(directory)
            env_path = root / ".env"
            env_path.write_bytes(original)

            def fail_after_complete_write(source: str | Path, destination: str | Path) -> None:
                staged_path = Path(source)
                self.assertEqual(Path(destination), env_path)
                self.assertEqual(staged_path.parent, env_path.parent)
                self.assertTrue(staged_path.name.startswith(".env."))
                self.assertEqual(staged_path.read_bytes(), expected_staged)
                raise OSError("synthetic replace failure")

            with patch.object(module.os, "replace", side_effect=fail_after_complete_write):
                with self.assertRaises(OSError):
                    module.update_env_assignment(
                        env_path,
                        "DATABASE_URL",
                        "postgresql://local.invalid/rotated",
                    )

            self.assertEqual(env_path.read_bytes(), original)
            self.assertEqual(list(root.glob(".env.*")), [])

    def test_provisioner_writes_canonical_percent_encoded_local_database_uri(
        self,
    ) -> None:
        module = load_module(PROVISION_PATH, "provision_local_database_login_uri_test")
        admin_password = "synthetic-admin-secret"
        admin_dsn = _database_dsn(
            "postgresql", "postgres:synthetic-admin-secret@127.0.0.1:54322/postgres"
        )
        generated_password = "synthetic:/@% password"
        expected_url = _database_dsn(
            "postgresql",
            "sejong_local_login:synthetic%3A%2F%40%25%20password@127.0.0.1:54322/postgres",
        )

        with tempfile.TemporaryDirectory(prefix="sejong provision uri ") as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("CONTEXT_TOKEN_SECRET=synthetic-context\n", encoding="utf-8")
            with (
                patch.dict(module.os.environ, {}, clear=True),
                patch.object(module.psycopg, "connect") as connect,
                patch.object(module.secrets, "token_urlsafe", return_value=generated_password),
                patch("builtins.print") as output,
            ):
                connection = connect.return_value.__enter__.return_value
                cursor = connection.cursor.return_value.__enter__.return_value
                cursor.fetchone.side_effect = [
                    None,
                    module.EXPECTED_EXISTING_ROLE_STATE,
                    (True, True, False, True, True),
                    module.EXPECTED_LOGIN_ADMIN_STATE,
                    module.EXPECTED_CAPABILITY_ROLE_STATE,
                    module.EXPECTED_CAPABILITY_MEMBER_STATE,
                ]

                module.provision(admin_dsn, env_path)

            self.assertEqual(
                env_path.read_text(encoding="utf-8"),
                f"CONTEXT_TOKEN_SECRET=synthetic-context\nDATABASE_URL={expected_url}\n",
            )
            self.assertNotIn(admin_password, env_path.read_text(encoding="utf-8"))
            connect.assert_called_once_with(
                admin_dsn,
                hostaddr="127.0.0.1",
                autocommit=False,
            )
            output.assert_not_called()

    def test_provisioner_rejects_unsafe_capability_role_before_commit_or_env_write(
        self,
    ) -> None:
        module = load_module(
            PROVISION_PATH,
            "provision_local_database_login_unsafe_capability_test",
        )
        admin_dsn = _database_dsn(
            "postgresql", "postgres:synthetic-admin-secret@127.0.0.1:54322/postgres"
        )
        unsafe_capability = (
            False,
            True,
            False,
            False,
            False,
            False,
            False,
            -1,
            True,
            True,
            False,
        )

        with tempfile.TemporaryDirectory(
            prefix="sejong provision unsafe capability "
        ) as directory:
            env_path = Path(directory) / ".env"
            with (
                patch.dict(module.os.environ, {}, clear=True),
                patch.object(module.psycopg, "connect") as connect,
                patch.object(
                    module.secrets,
                    "token_urlsafe",
                    return_value="rotated-synthetic-password",
                ),
            ):
                connection = connect.return_value.__enter__.return_value
                cursor = connection.cursor.return_value.__enter__.return_value
                cursor.fetchone.side_effect = [
                    module.EXPECTED_EXISTING_ROLE_STATE,
                    module.EXPECTED_EXISTING_ROLE_STATE,
                    (True, True, False, True, True),
                    module.EXPECTED_LOGIN_ADMIN_STATE,
                    unsafe_capability,
                ]

                with self.assertRaisesRegex(
                    ValueError,
                    "^BACKEND_CAPABILITY_STATE_INVALID$",
                ):
                    module.provision(admin_dsn, env_path)

            connection.commit.assert_not_called()
            self.assertFalse(env_path.exists())

    def test_provisioner_rejects_extra_capability_member_before_commit_or_env_write(
        self,
    ) -> None:
        module = load_module(
            PROVISION_PATH,
            "provision_local_database_login_extra_capability_member_test",
        )
        admin_dsn = _database_dsn(
            "postgresql", "postgres:synthetic-admin-secret@127.0.0.1:54322/postgres"
        )

        with tempfile.TemporaryDirectory(
            prefix="sejong provision extra capability member "
        ) as directory:
            env_path = Path(directory) / ".env"
            with (
                patch.dict(module.os.environ, {}, clear=True),
                patch.object(module.psycopg, "connect") as connect,
                patch.object(
                    module.secrets,
                    "token_urlsafe",
                    return_value="rotated-synthetic-password",
                ),
            ):
                connection = connect.return_value.__enter__.return_value
                cursor = connection.cursor.return_value.__enter__.return_value
                cursor.fetchone.side_effect = [
                    module.EXPECTED_EXISTING_ROLE_STATE,
                    module.EXPECTED_EXISTING_ROLE_STATE,
                    module.EXPECTED_MEMBERSHIP_STATE,
                    module.EXPECTED_LOGIN_ADMIN_STATE,
                    module.EXPECTED_CAPABILITY_ROLE_STATE,
                    (False, True, True),
                ]

                with self.assertRaisesRegex(
                    ValueError,
                    "^BACKEND_CAPABILITY_MEMBER_STATE_INVALID$",
                ):
                    module.provision(admin_dsn, env_path)

            connection.commit.assert_not_called()
            self.assertFalse(env_path.exists())

    def test_provisioner_rejects_unsafe_existing_login_before_mutation_or_env_write(
        self,
    ) -> None:
        module = load_module(
            PROVISION_PATH,
            "provision_local_database_login_unsafe_existing_role_test",
        )
        admin_dsn = _database_dsn(
            "postgresql", "postgres:synthetic-admin-secret@127.0.0.1:54322/postgres"
        )

        with tempfile.TemporaryDirectory(prefix="sejong provision unsafe existing ") as directory:
            env_path = Path(directory) / ".env"
            with (
                patch.dict(module.os.environ, {}, clear=True),
                patch.object(module.psycopg, "connect") as connect,
                patch.object(module.secrets, "token_urlsafe") as token_urlsafe,
            ):
                connection = connect.return_value.__enter__.return_value
                cursor = connection.cursor.return_value.__enter__.return_value
                cursor.fetchone.return_value = (
                    True,
                    True,
                    True,
                    False,
                    False,
                    False,
                    False,
                    -1,
                    True,
                    True,
                )

                with self.assertRaisesRegex(
                    ValueError,
                    "^BACKEND_ROLE_STATE_INVALID$",
                ):
                    module.provision(admin_dsn, env_path)

            token_urlsafe.assert_called_once_with(32)
            self.assertEqual(cursor.execute.call_count, 1)
            self.assertFalse(env_path.exists())

    def test_provisioner_rejects_unsafe_membership_postcondition_before_commit_or_env_write(
        self,
    ) -> None:
        module = load_module(
            PROVISION_PATH,
            "provision_local_database_login_unsafe_membership_test",
        )
        admin_dsn = _database_dsn(
            "postgresql", "postgres:synthetic-admin-secret@127.0.0.1:54322/postgres"
        )

        with tempfile.TemporaryDirectory(prefix="sejong provision unsafe membership ") as directory:
            env_path = Path(directory) / ".env"
            with (
                patch.dict(module.os.environ, {}, clear=True),
                patch.object(module.psycopg, "connect") as connect,
                patch.object(
                    module.secrets,
                    "token_urlsafe",
                    return_value="rotated-synthetic-password",
                ),
            ):
                connection = connect.return_value.__enter__.return_value
                cursor = connection.cursor.return_value.__enter__.return_value
                cursor.fetchone.side_effect = [
                    module.EXPECTED_EXISTING_ROLE_STATE,
                    module.EXPECTED_EXISTING_ROLE_STATE,
                    (False, True, False, True, True),
                ]

                with self.assertRaisesRegex(
                    ValueError,
                    "^BACKEND_MEMBERSHIP_STATE_INVALID$",
                ):
                    module.provision(admin_dsn, env_path)

            connection.commit.assert_not_called()
            self.assertFalse(env_path.exists())

    def test_provisioner_rejects_extra_login_admin_member_before_commit_or_env_write(
        self,
    ) -> None:
        module = load_module(
            PROVISION_PATH,
            "provision_local_database_login_extra_admin_member_test",
        )
        admin_dsn = _database_dsn(
            "postgresql", "postgres:synthetic-admin-secret@127.0.0.1:54322/postgres"
        )

        with tempfile.TemporaryDirectory(
            prefix="sejong provision extra admin member "
        ) as directory:
            env_path = Path(directory) / ".env"
            with (
                patch.dict(module.os.environ, {}, clear=True),
                patch.object(module.psycopg, "connect") as connect,
                patch.object(
                    module.secrets,
                    "token_urlsafe",
                    return_value="rotated-synthetic-password",
                ),
            ):
                connection = connect.return_value.__enter__.return_value
                cursor = connection.cursor.return_value.__enter__.return_value
                cursor.fetchone.side_effect = [
                    module.EXPECTED_EXISTING_ROLE_STATE,
                    module.EXPECTED_EXISTING_ROLE_STATE,
                    (True, True, False, True, True),
                    (False, True, True, False, False),
                ]

                with self.assertRaisesRegex(
                    ValueError,
                    "^BACKEND_LOGIN_ADMIN_STATE_INVALID$",
                ):
                    module.provision(admin_dsn, env_path)

            connection.commit.assert_not_called()
            self.assertFalse(env_path.exists())

    def test_provisioner_rejects_unsafe_role_postcondition_before_grant_or_env_write(
        self,
    ) -> None:
        module = load_module(
            PROVISION_PATH,
            "provision_local_database_login_unsafe_role_postcondition_test",
        )
        admin_dsn = _database_dsn(
            "postgresql", "postgres:synthetic-admin-secret@127.0.0.1:54322/postgres"
        )
        unsafe_postcondition = (
            True,
            True,
            False,
            False,
            False,
            False,
            False,
            1,
            True,
            True,
        )

        with tempfile.TemporaryDirectory(
            prefix="sejong provision unsafe role postcondition "
        ) as directory:
            env_path = Path(directory) / ".env"
            with (
                patch.dict(module.os.environ, {}, clear=True),
                patch.object(module.psycopg, "connect") as connect,
                patch.object(
                    module.secrets,
                    "token_urlsafe",
                    return_value="rotated-synthetic-password",
                ),
            ):
                connection = connect.return_value.__enter__.return_value
                cursor = connection.cursor.return_value.__enter__.return_value
                cursor.fetchone.side_effect = [
                    module.EXPECTED_EXISTING_ROLE_STATE,
                    unsafe_postcondition,
                ]

                with self.assertRaisesRegex(
                    ValueError,
                    "^BACKEND_ROLE_STATE_INVALID$",
                ):
                    module.provision(admin_dsn, env_path)

            self.assertFalse(
                any("GRANT" in repr(call.args[0]) for call in cursor.execute.call_args_list)
            )
            connection.commit.assert_not_called()
            self.assertFalse(env_path.exists())

    def test_provisioner_rotates_existing_safe_login_without_reasserting_superuser_flag(
        self,
    ) -> None:
        module = load_module(
            PROVISION_PATH,
            "provision_local_database_login_existing_role_test",
        )
        admin_dsn = _database_dsn(
            "postgresql", "postgres:synthetic-admin-secret@127.0.0.1:54322/postgres"
        )

        with tempfile.TemporaryDirectory(prefix="sejong provision existing ") as directory:
            env_path = Path(directory) / ".env"
            with (
                patch.dict(module.os.environ, {}, clear=True),
                patch.object(module.psycopg, "connect") as connect,
                patch.object(
                    module.secrets,
                    "token_urlsafe",
                    return_value="rotated-synthetic-password",
                ),
            ):
                connection = connect.return_value.__enter__.return_value
                cursor = connection.cursor.return_value.__enter__.return_value
                cursor.fetchone.side_effect = [
                    module.EXPECTED_EXISTING_ROLE_STATE,
                    module.EXPECTED_EXISTING_ROLE_STATE,
                    (True, True, False, True, True),
                    module.EXPECTED_LOGIN_ADMIN_STATE,
                    module.EXPECTED_CAPABILITY_ROLE_STATE,
                    module.EXPECTED_CAPABILITY_MEMBER_STATE,
                ]

                module.provision(admin_dsn, env_path)

            alter_statements = [
                call.args[0]
                for call in cursor.execute.call_args_list
                if "ALTER ROLE" in repr(call.args[0])
            ]
            self.assertEqual(len(alter_statements), 1)
            self.assertNotIn("NOSUPERUSER", repr(alter_statements[0]))
            self.assertNotIn("NOREPLICATION", repr(alter_statements[0]))
            self.assertNotIn("NOBYPASSRLS", repr(alter_statements[0]))
            self.assertIn("PASSWORD", repr(alter_statements[0]))
            self.assertIn("DATABASE_URL=", env_path.read_text(encoding="utf-8"))

    def test_provisioner_rejects_non_exact_admin_identity_before_connect_or_write(
        self,
    ) -> None:
        module = load_module(
            PROVISION_PATH, "provision_local_database_login_identity_test"
        )
        admin_secret = "synthetic-admin-secret"
        valid = _database_dsn(
            "postgresql", f"postgres:{admin_secret}@127.0.0.1:54322/postgres"
        )
        invalid = (
            valid.replace("postgres:", "other:", 1),
            valid.replace("127.0.0.1", "localhost", 1),
            valid.replace("127.0.0.1", "db.example.invalid", 1),
            valid.replace("54322", "54321", 1),
            valid.removesuffix("/postgres") + "/template1",
            valid + "?sslmode=disable",
            valid.replace(
                "@127.0.0.1",
                "@remote.example.invalid@127.0.0.1",
                1,
            ),
            valid.replace(admin_secret, "malformed%ZZsecret", 1),
            "user=postgres password=synthetic-admin-secret "
            "host=127.0.0.1 port=54322 dbname=postgres application_name=untrusted",
        )

        with tempfile.TemporaryDirectory(
            prefix="sejong provision identity "
        ) as directory:
            env_path = Path(directory) / ".env"
            for admin_dsn in invalid:
                with self.subTest(
                    admin_dsn_shape=admin_dsn.replace(admin_secret, "[SECRET]")
                ):
                    with (
                        patch.dict(module.os.environ, {}, clear=True),
                        patch.object(module.psycopg, "connect") as connect,
                    ):
                        with self.assertRaisesRegex(
                            ValueError,
                            "^ADMIN_DSN_IDENTITY_INVALID$",
                        ) as caught:
                            module.provision(admin_dsn, env_path)

                    connect.assert_not_called()
                    self.assertFalse(env_path.exists())
                    self.assertNotIn(admin_secret, repr(caught.exception))

    def test_provisioner_rejects_ambient_libpq_environment_before_connect_or_write(
        self,
    ) -> None:
        module = load_module(
            PROVISION_PATH, "provision_local_database_login_ambient_test"
        )
        admin_secret = "synthetic-admin-secret"
        admin_dsn = _database_dsn(
            "postgresql", f"postgres:{admin_secret}@127.0.0.1:54322/postgres"
        )

        with tempfile.TemporaryDirectory(
            prefix="sejong provision ambient "
        ) as directory:
            env_path = Path(directory) / ".env"
            for variable in (
                "PGHOSTADDR",
                "PGSERVICE",
                "PGSERVICEFILE",
                "PGOPTIONS",
                "pgpassword",
            ):
                with self.subTest(variable=variable):
                    with (
                        patch.dict(
                            module.os.environ,
                            {variable: "synthetic-ambient-value"},
                            clear=True,
                        ),
                        patch.object(module.psycopg, "connect") as connect,
                        patch("builtins.print") as output,
                    ):
                        with self.assertRaisesRegex(
                            ValueError,
                            "^AMBIENT_LIBPQ_ENVIRONMENT_INVALID$",
                        ) as caught:
                            module.provision(admin_dsn, env_path)

                    connect.assert_not_called()
                    output.assert_not_called()
                    self.assertFalse(env_path.exists())
                    self.assertNotIn(admin_secret, repr(caught.exception))

    def test_provisioner_missing_admin_dsn_is_stable(self) -> None:
        environment = os.environ.copy()
        environment.pop("SEJONG_ADMIN_DATABASE_URL", None)
        result = subprocess.run(
            [
                str(ROOT / "apps" / "api" / ".venv" / "Scripts" / "python.exe"),
                "-B",
                str(PROVISION_PATH),
            ],
            cwd=ROOT,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            env=environment,
            timeout=20,
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            result.stdout.strip(),
            "[FAIL] step=PROVISION-LOCAL-DB-LOGIN reason=missing-admin-dsn code=2",
        )
        self.assertFalse(result.stderr)

    def test_database_sql_runner_rejects_empty_and_outside_paths(self) -> None:
        missing_environment = {"SEJONG_ADMIN_DATABASE_URL": ""}
        empty = run_python_tool(SQL_RUNNER_PATH, env=missing_environment)
        outside = run_python_tool(
            SQL_RUNNER_PATH,
            str(ROOT / "README.md"),
            env=missing_environment,
        )

        self.assertEqual(empty.returncode, 2)
        self.assertEqual(
            empty.stdout.strip(),
            "[FAIL] step=RUN-DATABASE-SQL reason=invalid-files code=2",
        )
        self.assertEqual(outside.returncode, 2)
        self.assertEqual(
            outside.stdout.strip(),
            "[FAIL] step=RUN-DATABASE-SQL reason=invalid-files code=2",
        )
        self.assertFalse(empty.stderr or outside.stderr)

    def test_database_runner_has_no_remote_or_destructive_host_commands(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8").lower()
        for forbidden in ("db push", "link", "login", "projects", "volume prune", "system prune"):
            self.assertNotIn(forbidden, script)
        self.assertIn("db reset", script)
        self.assertIn("test db", script)
        self.assertIn('"-skipstart"', script)
        self.assertIn('"-skiprollbackreplay"', script)

    def test_database_runner_rejects_docker_engine_before_28(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        result, invocations = run_database_runner_with_supabase_capture(
            script,
            include_docker_invocations=True,
            docker_server_version="27.5.1",
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            result.stdout.splitlines()[-1],
            "[FAIL] step=PREFLIGHT-DOCKER reason=version code=2",
        )
        self.assertFalse(
            any(invocation[:2] == ["db", "start"] for invocation in invocations)
        )
        self.assertNotIn(["db", "reset", "--local"], invocations)

    def test_database_runner_creates_and_uses_loopback_network_before_reset(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        result, invocations = run_database_runner_with_supabase_capture(
            script,
            include_docker_invocations=True,
        )

        self.assertEqual(result.returncode, 7)
        self.assertFalse(result.stderr)
        self.assertIn(
            [
                "docker",
                "network",
                "create",
                "--driver",
                "bridge",
                "--opt",
                "com.docker.network.bridge.host_binding_ipv4=127.0.0.1",
                "--label",
                "com.sejong-ai.local-boundary=sejong-ai-local",
                "sejong-ai-local-loopback",
            ],
            invocations,
        )
        start = ["db", "start", "--network-id", "sejong-ai-local-loopback"]
        reset = ["db", "reset", "--local"]
        self.assertIn(start, invocations)
        self.assertIn(reset, invocations)
        self.assertLess(invocations.index(start), invocations.index(reset))
        self.assertLess(
            max(
                index
                for index, invocation in enumerate(invocations)
                if invocation[:2] == ["docker", "inspect"]
            ),
            invocations.index(reset),
        )

    def test_database_runner_rejects_network_driver_or_option_drift(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        for network_state in (
            "driver-drift",
            "option-drift",
            "name-drift",
            "scope-drift",
            "label-drift",
        ):
            with self.subTest(network_state=network_state):
                result, invocations = run_database_runner_with_supabase_capture(
                    script,
                    include_docker_invocations=True,
                    network_state=network_state,
                )

                self.assertEqual(result.returncode, 2)
                self.assertEqual(
                    result.stdout.splitlines()[-1],
                    "[FAIL] step=VERIFY-LOCAL-DATABASE-NETWORK "
                    "reason=invalid code=2",
                )
                self.assertFalse(
                    any(invocation[:2] == ["db", "start"] for invocation in invocations)
                )
                self.assertNotIn(["db", "reset", "--local"], invocations)

    def test_database_runner_rejects_unsafe_existing_runtime_before_mutation(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        result, invocations = run_database_runner_with_supabase_capture(
            script,
            include_docker_invocations=True,
            network_state="safe",
            runtime_state="unsafe-ip",
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            result.stdout.splitlines()[-1],
            "[FAIL] step=VERIFY-LOCAL-DATABASE-RUNTIME reason=invalid code=2",
        )
        self.assertNotIn(
            ["db", "start", "--network-id", "sejong-ai-local-loopback"],
            invocations,
        )
        self.assertNotIn(["db", "reset", "--local"], invocations)

    def test_database_runner_rejects_unsafe_resolved_binding_despite_safe_request(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        result, invocations = run_database_runner_with_supabase_capture(
            script,
            include_docker_invocations=True,
            network_state="safe",
            runtime_state="unsafe-resolved",
            runner_arguments=("-SkipStart",),
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            result.stdout.splitlines()[-1],
            "[FAIL] step=VERIFY-LOCAL-DATABASE-RUNTIME reason=invalid code=2",
        )
        self.assertNotIn(["db", "reset", "--local"], invocations)

    def test_database_runner_stops_only_new_unsafe_runtime_before_returning_original_failure(
        self,
    ) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        result, invocations = run_database_runner_with_supabase_capture(
            script,
            include_docker_invocations=True,
            network_state="safe",
            runtime_state="none",
            started_runtime_state="unsafe-resolved",
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            result.stdout.splitlines()[-1],
            "[FAIL] step=VERIFY-LOCAL-DATABASE-RUNTIME reason=invalid code=2",
        )
        self.assertIn(
            ["db", "start", "--network-id", "sejong-ai-local-loopback"],
            invocations,
        )
        self.assertIn(["stop"], invocations)
        self.assertIn(["runtime", "none"], invocations)
        self.assertNotIn(["db", "reset", "--local"], invocations)
        self.assertLess(invocations.index(["stop"]), invocations.index(["runtime", "none"]))

    def test_database_runner_stops_partial_runtime_when_start_command_fails(
        self,
    ) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        result, invocations = run_database_runner_with_supabase_capture(
            script,
            full_path=True,
            failure_phase="start",
            include_docker_invocations=True,
            network_state="safe",
            runtime_state="none",
            started_runtime_state="unsafe-resolved",
        )

        self.assertEqual(result.returncode, 23)
        self.assertFalse(result.stderr)
        self.assertEqual(
            result.stdout.splitlines()[-1],
            "[FAIL] step=START-LOCAL-DATABASE reason=child code=23",
        )
        self.assertIn(["stop"], invocations)
        self.assertIn(["runtime", "none"], invocations)
        self.assertNotIn(["db", "reset", "--local"], invocations)
        self.assertLess(invocations.index(["stop"]), invocations.index(["runtime", "none"]))

    def test_database_runner_reports_owned_runtime_stop_failure_without_reset(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        result, invocations = run_database_runner_with_supabase_capture(
            script,
            include_docker_invocations=True,
            network_state="safe",
            runtime_state="none",
            started_runtime_state="unsafe-resolved",
            stop_failure=True,
        )

        self.assertEqual(result.returncode, 23)
        self.assertEqual(
            result.stdout.splitlines()[-1],
            "[FAIL] step=STOP-UNSAFE-LOCAL-DATABASE-RUNTIME reason=child code=23",
        )
        self.assertIn(["stop"], invocations)
        self.assertNotIn(["runtime", "none"], invocations)
        self.assertNotIn(["db", "reset", "--local"], invocations)

    def test_database_runner_rejects_stop_success_when_owned_runtime_remains(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        result, invocations = run_database_runner_with_supabase_capture(
            script,
            include_docker_invocations=True,
            network_state="safe",
            runtime_state="none",
            started_runtime_state="unsafe-resolved",
            stop_leaves_runtime=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            result.stdout.splitlines()[-1],
            "[FAIL] step=STOP-UNSAFE-LOCAL-DATABASE-RUNTIME reason=invalid code=2",
        )
        self.assertIn(["stop"], invocations)
        self.assertIn(["runtime", "unsafe-resolved"], invocations)
        self.assertNotIn(["db", "reset", "--local"], invocations)

    def test_database_runner_never_stops_preexisting_or_skip_start_runtime(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")
        cases = (
            ((), "normal-preexisting"),
            (("-SkipStart",), "skip-start"),
        )

        for runner_arguments, label in cases:
            with self.subTest(label=label):
                result, invocations = run_database_runner_with_supabase_capture(
                    script,
                    include_docker_invocations=True,
                    network_state="safe",
                    runtime_state="safe",
                    runner_arguments=runner_arguments,
                )

                self.assertEqual(result.returncode, 7)
                self.assertNotIn(["stop"], invocations)
                self.assertIn(["db", "reset", "--local"], invocations)

    def test_database_runner_rejects_runtime_identity_or_state_drift(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        for runtime_state in (
            "stopped",
            "label-drift",
            "name-drift",
            "networkmode-drift",
            "wrong-network",
        ):
            with self.subTest(runtime_state=runtime_state):
                result, invocations = run_database_runner_with_supabase_capture(
                    script,
                    include_docker_invocations=True,
                    network_state="safe",
                    runtime_state=runtime_state,
                )

                self.assertEqual(result.returncode, 2)
                self.assertEqual(
                    result.stdout.splitlines()[-1],
                    "[FAIL] step=VERIFY-LOCAL-DATABASE-RUNTIME "
                    "reason=invalid code=2",
                )
                self.assertFalse(
                    any(invocation[:2] == ["db", "start"] for invocation in invocations)
                )
                self.assertNotIn(["db", "reset", "--local"], invocations)

    def test_database_runner_rejects_stopped_project_container_before_start(
        self,
    ) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        result, invocations = run_database_runner_with_supabase_capture(
            script,
            include_docker_invocations=True,
            network_state="safe",
            runtime_state="stopped",
            started_runtime_state="safe",
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            result.stdout.splitlines()[-1],
            "[FAIL] step=VERIFY-LOCAL-DATABASE-RUNTIME reason=invalid code=2",
        )
        self.assertFalse(
            any(invocation[:2] == ["db", "start"] for invocation in invocations)
        )
        self.assertNotIn(["db", "reset", "--local"], invocations)

    def test_database_runner_rejects_non_exact_database_port_binding(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        for runtime_state in (
            "mixed-bindings",
            "wrong-host-port",
            "unsafe-requested",
            "null-binding",
        ):
            with self.subTest(runtime_state=runtime_state):
                result, invocations = run_database_runner_with_supabase_capture(
                    script,
                    include_docker_invocations=True,
                    network_state="safe",
                    runtime_state=runtime_state,
                    runner_arguments=("-SkipStart",),
                )

                self.assertEqual(result.returncode, 2)
                self.assertEqual(
                    result.stdout.splitlines()[-1],
                    "[FAIL] step=VERIFY-LOCAL-DATABASE-RUNTIME "
                    "reason=invalid code=2",
                )
                self.assertNotIn(["db", "reset", "--local"], invocations)

    def test_database_runner_skip_start_accepts_only_safe_existing_runtime(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        result, invocations = run_database_runner_with_supabase_capture(
            script,
            include_docker_invocations=True,
            network_state="safe",
            runtime_state="safe",
            runner_arguments=("-SkipStart",),
        )

        self.assertEqual(result.returncode, 7)
        self.assertNotIn(
            ["db", "start", "--network-id", "sejong-ai-local-loopback"],
            invocations,
        )
        self.assertIn(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                "label=com.supabase.cli.project=sejong-ai-local",
                "--format",
                "{{.ID}}",
            ],
            invocations,
        )
        self.assertIn(["docker", "inspect", "container-one"], invocations)
        self.assertLess(
            invocations.index(["docker", "inspect", "container-one"]),
            invocations.index(["db", "reset", "--local"]),
        )

    def test_database_runner_rejects_missing_multiple_or_unpublished_runtime(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        for runtime_state in ("none", "multiple", "unpublished"):
            with self.subTest(runtime_state=runtime_state):
                result, invocations = run_database_runner_with_supabase_capture(
                    script,
                    include_docker_invocations=True,
                    network_state="safe",
                    runtime_state=runtime_state,
                    runner_arguments=("-SkipStart",),
                )

                self.assertEqual(result.returncode, 2)
                self.assertEqual(
                    result.stdout.splitlines()[-1],
                    "[FAIL] step=VERIFY-LOCAL-DATABASE-RUNTIME "
                    "reason=invalid code=2",
                )
                self.assertNotIn(["db", "reset", "--local"], invocations)

    def test_database_runner_starts_only_postgres_with_exact_cli_arguments(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        result, invocations = run_database_runner_with_supabase_capture(script)

        self.assertEqual(result.returncode, 7)
        self.assertFalse(result.stderr)
        self.assertEqual(
            invocations,
            [
                ["db", "start", "--network-id", "sejong-ai-local-loopback"],
                ["db", "reset", "--local"],
            ],
        )
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "[START] step=PREFLIGHT-DOCKER",
                "[PASS] step=PREFLIGHT-DOCKER",
                "[START] step=VERIFY-SUPABASE-VERSION",
                "[PASS] step=VERIFY-SUPABASE-VERSION",
                "[START] step=VERIFY-LOCAL-DATABASE-NETWORK",
                "[PASS] step=VERIFY-LOCAL-DATABASE-NETWORK",
                "[START] step=VERIFY-LOCAL-DATABASE-RUNTIME",
                "[PASS] step=VERIFY-LOCAL-DATABASE-RUNTIME",
                "[START] step=START-LOCAL-DATABASE",
                "[PASS] step=START-LOCAL-DATABASE",
                "[START] step=VERIFY-LOCAL-DATABASE-RUNTIME",
                "[PASS] step=VERIFY-LOCAL-DATABASE-RUNTIME",
                "[START] step=RESET-DATABASE-ONE",
                "[FAIL] step=RESET-DATABASE-ONE reason=child code=7",
            ],
        )

    def test_database_start_capture_rejects_dead_exact_block_and_live_bare_call(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")
        exact_block = '''    if (-not $skipStart) {
        $runtimeAlreadyPresent = Assert-LocalDatabaseRuntime `
            -DockerPath $dockerCommand.Source `
            -ProjectId $localProjectId `
            -NetworkName $localNetworkName `
            -ExpectedContainerName $localDatabaseContainerName `
            -WorkingDirectory $repositoryRoot `
            -AllowAbsent
        if (-not $runtimeAlreadyPresent) {
            $runnerCreatedRuntime = $true
        }
        try {
            $null = Invoke-DatabaseStep `
                -Step "START-LOCAL-DATABASE" `
                -FilePath $supabaseBinary `
                -Arguments @("db", "start", "--network-id", $localNetworkName) `
                -WorkingDirectory $repositoryRoot
        }
        catch {
            $startFailure = $_.Exception
            if ($runnerCreatedRuntime) {
                Stop-OwnedUnsafeLocalDatabaseRuntime `
                    -SupabasePath $supabaseBinary `
                    -DockerPath $dockerCommand.Source `
                    -ProjectId $localProjectId `
                    -WorkingDirectory $repositoryRoot
            }
            throw $startFailure
        }
    }
'''
        mutant_block = '''    if (-not $skipStart) {
        $runtimeAlreadyPresent = Assert-LocalDatabaseRuntime `
            -DockerPath $dockerCommand.Source `
            -ProjectId $localProjectId `
            -NetworkName $localNetworkName `
            -ExpectedContainerName $localDatabaseContainerName `
            -WorkingDirectory $repositoryRoot `
            -AllowAbsent
        if ($false) {
            $null = Invoke-DatabaseStep `
                -Step "START-LOCAL-DATABASE" `
                -FilePath $supabaseBinary `
                -Arguments @("db", "start", "--network-id", $localNetworkName) `
                -WorkingDirectory $repositoryRoot
        }
        $null = & $supabaseBinary start
        if ($LASTEXITCODE -ne 0) {
            Throw-DatabaseGateFailure `
                -Step "START-LOCAL-DATABASE" `
                -Reason "child" `
                -Code $LASTEXITCODE
        }
    }
'''
        self.assertEqual(script.count(exact_block), 1)
        mutant = script.replace(exact_block, mutant_block)

        result, invocations = run_database_runner_with_supabase_capture(mutant)

        self.assertEqual(result.returncode, 7)
        self.assertFalse(result.stderr)
        self.assertEqual(invocations, [["start"], ["db", "reset", "--local"]])
        self.assertNotEqual(
            invocations,
            [
                ["db", "start", "--network-id", "sejong-ai-local-loopback"],
                ["db", "reset", "--local"],
            ],
        )

    def test_database_start_capture_rejects_extra_live_bare_call(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")
        exact_block = '''    if (-not $skipStart) {
        $runtimeAlreadyPresent = Assert-LocalDatabaseRuntime `
            -DockerPath $dockerCommand.Source `
            -ProjectId $localProjectId `
            -NetworkName $localNetworkName `
            -ExpectedContainerName $localDatabaseContainerName `
            -WorkingDirectory $repositoryRoot `
            -AllowAbsent
        if (-not $runtimeAlreadyPresent) {
            $runnerCreatedRuntime = $true
        }
        try {
            $null = Invoke-DatabaseStep `
                -Step "START-LOCAL-DATABASE" `
                -FilePath $supabaseBinary `
                -Arguments @("db", "start", "--network-id", $localNetworkName) `
                -WorkingDirectory $repositoryRoot
        }
        catch {
            $startFailure = $_.Exception
            if ($runnerCreatedRuntime) {
                Stop-OwnedUnsafeLocalDatabaseRuntime `
                    -SupabasePath $supabaseBinary `
                    -DockerPath $dockerCommand.Source `
                    -ProjectId $localProjectId `
                    -WorkingDirectory $repositoryRoot
            }
            throw $startFailure
        }
    }
'''
        self.assertTrue(exact_block.endswith("    }\n"))
        mutant_block = (
            exact_block[:-6]
            + "        $null = & $supabaseBinary start\n    }\n"
        )
        self.assertEqual(script.count(exact_block), 1)
        mutant = script.replace(exact_block, mutant_block)

        result, invocations = run_database_runner_with_supabase_capture(mutant)

        self.assertEqual(result.returncode, 7)
        self.assertFalse(result.stderr)
        self.assertEqual(
            invocations,
            [
                ["db", "start", "--network-id", "sejong-ai-local-loopback"],
                ["start"],
                ["db", "reset", "--local"],
            ],
        )
        self.assertNotEqual(
            invocations,
            [
                ["db", "start", "--network-id", "sejong-ai-local-loopback"],
                ["db", "reset", "--local"],
            ],
        )

    def test_database_runner_uses_exact_newest_first_compensation_order(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")
        rollback_paths = re.findall(
            r'database\\rollbacks\\([^"\r\n]+\.rollback\.sql)',
            script,
        )

        self.assertEqual(
            rollback_paths,
            [
                "20260727000700_privileged_function_search_path.rollback.sql",
                "20260727000680_civic_scope_gap_queue.rollback.sql",
                "20260722000670_candidate_public_id_binding.rollback.sql",
                "20260722000660_chat_idempotency.rollback.sql",
                "20260722000650_local_admin_read_capabilities.rollback.sql",
                "20260717000600_deferred_active_question_trigger_security.rollback.sql",
                "20260716000500_indexes_and_read_interfaces.rollback.sql",
                "20260716000400_candidate_workflow.rollback.sql",
                "20260716000300_capabilities_and_functions.rollback.sql",
                "20260716000200_invariants_and_lineage.rollback.sql",
                "20260716000100_private_schema.rollback.sql",
            ],
        )

    def test_database_runner_full_path_orders_replay_and_restores_environment(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        result, invocations = run_database_runner_with_supabase_capture(
            script,
            full_path=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertFalse(result.stderr)
        self.assertFalse(CHILD_OUTPUT_SENTINEL in result.stdout)
        self.assertEqual(
            invocations,
            [
                ["db", "start", "--network-id", "sejong-ai-local-loopback"],
                ["db", "reset", "--local"],
                ["status", "-o", "env"],
                ["provision"],
                ["test", "db"],
                [
                    "sql",
                    "20260727000700_privileged_function_search_path.rollback.sql",
                    "20260727000680_civic_scope_gap_queue.rollback.sql",
                    "20260722000670_candidate_public_id_binding.rollback.sql",
                    "20260722000660_chat_idempotency.rollback.sql",
                    "20260722000650_local_admin_read_capabilities.rollback.sql",
                    "20260717000600_deferred_active_question_trigger_security.rollback.sql",
                    "20260716000500_indexes_and_read_interfaces.rollback.sql",
                    "20260716000400_candidate_workflow.rollback.sql",
                    "20260716000300_capabilities_and_functions.rollback.sql",
                    "20260716000200_invariants_and_lineage.rollback.sql",
                    "20260716000100_private_schema.rollback.sql",
                ],
                ["sql", "verify_db001_absent.sql"],
                ["db", "reset", "--local"],
                ["provision"],
                ["test", "db"],
                ["pytest", "test_integration.py"],
                ["environment", "restored", "restored"],
            ],
        )
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "[START] step=PREFLIGHT-DOCKER",
                "[PASS] step=PREFLIGHT-DOCKER",
                "[START] step=VERIFY-SUPABASE-VERSION",
                "[PASS] step=VERIFY-SUPABASE-VERSION",
                "[START] step=VERIFY-LOCAL-DATABASE-NETWORK",
                "[PASS] step=VERIFY-LOCAL-DATABASE-NETWORK",
                "[START] step=VERIFY-LOCAL-DATABASE-RUNTIME",
                "[PASS] step=VERIFY-LOCAL-DATABASE-RUNTIME",
                "[START] step=START-LOCAL-DATABASE",
                "[PASS] step=START-LOCAL-DATABASE",
                "[START] step=VERIFY-LOCAL-DATABASE-RUNTIME",
                "[PASS] step=VERIFY-LOCAL-DATABASE-RUNTIME",
                "[START] step=RESET-DATABASE-ONE",
                "[PASS] step=RESET-DATABASE-ONE",
                "[START] step=PROVISION-LOCAL-DB-LOGIN-ONE",
                "[PASS] step=PROVISION-LOCAL-DB-LOGIN-ONE",
                "[START] step=TEST-PGTAP-ONE",
                "[PASS] step=TEST-PGTAP-ONE",
                "[START] step=ROLLBACK-DB001",
                "[PASS] step=ROLLBACK-DB001",
                "[START] step=VERIFY-DB001-ABSENT",
                "[PASS] step=VERIFY-DB001-ABSENT",
                "[START] step=RESET-DATABASE-TWO",
                "[PASS] step=RESET-DATABASE-TWO",
                "[START] step=PROVISION-LOCAL-DB-LOGIN-TWO",
                "[PASS] step=PROVISION-LOCAL-DB-LOGIN-TWO",
                "[START] step=TEST-PGTAP-TWO",
                "[PASS] step=TEST-PGTAP-TWO",
                "[START] step=TEST-DATABASE-INTEGRATION",
                "[PASS] step=TEST-DATABASE-INTEGRATION",
            ],
        )

    def test_database_runner_propagates_pgtap_failure_and_restores_environment(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        result, invocations = run_database_runner_with_supabase_capture(
            script,
            full_path=True,
            failure_phase="pgtap-one",
        )

        self.assertEqual(result.returncode, 17)
        self.assertFalse(result.stderr)
        self.assertFalse(CHILD_OUTPUT_SENTINEL in result.stdout)
        self.assertEqual(invocations[-1], ["environment", "restored", "restored"])
        self.assertEqual(
            result.stdout.splitlines()[-1],
            "[FAIL] step=TEST-PGTAP-ONE reason=child code=17",
        )

    def test_database_runner_propagates_integration_failure_without_child_output(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")

        result, invocations = run_database_runner_with_supabase_capture(
            script,
            full_path=True,
            failure_phase="integration",
        )

        self.assertEqual(result.returncode, 19)
        self.assertFalse(result.stderr)
        self.assertFalse(CHILD_OUTPUT_SENTINEL in result.stdout)
        self.assertEqual(invocations[-2], ["pytest", "test_integration.py"])
        self.assertEqual(invocations[-1], ["environment", "restored", "restored"])
        self.assertEqual(
            result.stdout.splitlines()[-1],
            "[FAIL] step=TEST-DATABASE-INTEGRATION reason=child code=19",
        )

    def test_database_runner_source_never_names_external_llm_key(self) -> None:
        script = DATABASE_RUNNER_PATH.read_text(encoding="utf-8")
        forbidden_name = "LLM" + "_" + "API" + "_" + "KEY"

        self.assertNotIn(forbidden_name, script)


class SupabaseBootstrapBehaviorTests(unittest.TestCase):
    def assert_stable_output(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertFalse(result.stderr, "bootstrap wrote to stderr")
        for line in result.stdout.splitlines():
            self.assertRegex(
                line,
                r"^\[(?:START|PASS|FAIL)\] step=[A-Z0-9-]+"
                r"(?: reason=[a-z-]+ code=[012])?$",
            )

    def test_verify_only_missing_is_stable_and_never_downloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sejong supabase verify ") as directory:
            root = Path(directory)
            script = copy_tooling_fixture(root)
            unrelated_cwd = root / "unrelated-current-directory"
            unrelated_cwd.mkdir()

            result = run_bootstrap(script, "-VerifyOnly", cwd=unrelated_cwd)

            self.assertEqual(result.returncode, 2)
            self.assertEqual(
                result.stdout.strip(),
                "[FAIL] step=VERIFY-SUPABASE-BINARY reason=missing code=2",
            )
            self.assertFalse((root / ".tools").exists(), "verify-only created local tooling")
            self.assert_stable_output(result)

    def test_archive_path_without_value_is_controlled_before_typed_binding(self) -> None:
        result = run_bootstrap(BOOTSTRAP_PATH, "-ArchivePath", cwd=ROOT)

        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            result.stdout.strip(),
            "[FAIL] step=VALIDATE-SUPABASE-ARGUMENTS reason=invalid code=2",
        )
        self.assertFalse(result.stderr, "missing value wrote localized binding details")
        combined = result.stdout + result.stderr
        self.assertNotIn(str(ROOT), combined)
        self.assertNotIn(str(BOOTSTRAP_PATH), combined)
        self.assert_stable_output(result)

    def test_duplicate_approved_arguments_are_controlled(self) -> None:
        cases = (
            ("-VerifyOnly", "-VerifyOnly"),
            (
                "-ArchivePath",
                "synthetic-first-archive.zip",
                "-ArchivePath",
                "synthetic-second-archive.zip",
            ),
        )
        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = run_bootstrap(BOOTSTRAP_PATH, *arguments, cwd=ROOT)

                self.assertEqual(result.returncode, 2)
                self.assertEqual(
                    result.stdout.strip(),
                    "[FAIL] step=VALIDATE-SUPABASE-ARGUMENTS reason=invalid code=2",
                )
                self.assertFalse(result.stderr, "duplicate argument wrote binding details")
                for value in arguments:
                    self.assertNotIn(value, result.stdout + result.stderr)
                self.assert_stable_output(result)

    def test_unapproved_argument_is_rejected_before_other_work(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sejong supabase arguments ") as directory:
            root = Path(directory)
            script = copy_tooling_fixture(root)

            result = run_bootstrap(
                script,
                "-VerifyOnly",
                "-UnapprovedArgument",
                cwd=root,
            )

            self.assertEqual(result.returncode, 2)
            self.assertEqual(
                result.stdout.strip(),
                "[FAIL] step=VALIDATE-SUPABASE-ARGUMENTS reason=invalid code=2",
            )
            self.assertFalse((root / ".tools").exists(), "invalid arguments started work")
            self.assert_stable_output(result)

    def test_verify_only_uses_release_directory_and_rejects_wrong_child_version(self) -> None:
        harmless_executable = shutil.which("whoami.exe") or shutil.which("whoami")
        if harmless_executable is None:
            self.fail("a harmless synthetic child executable is required")

        with tempfile.TemporaryDirectory(prefix="sejong supabase child ") as directory:
            root = Path(directory)
            script = copy_tooling_fixture(root)
            binary = root / ".tools" / "supabase" / "v2.109.1" / "supabase.exe"
            binary.parent.mkdir(parents=True)
            shutil.copy2(harmless_executable, binary)

            result = run_bootstrap(script, "-VerifyOnly", cwd=root)

            self.assertEqual(result.returncode, 1)
            self.assertEqual(
                result.stdout.splitlines(),
                [
                    "[START] step=VERIFY-SUPABASE-VERSION",
                    "[FAIL] step=VERIFY-SUPABASE-VERSION reason=child code=1",
                ],
            )
            self.assertNotIn(binary.name, result.stdout + result.stderr)
            self.assert_stable_output(result)

    def test_same_size_invalid_checksum_fails_without_disclosure_or_extraction(self) -> None:
        marker = b"synthetic-invalid-supabase-archive-value"
        with tempfile.TemporaryDirectory(prefix="sejong supabase checksum ") as directory:
            root = Path(directory)
            script = copy_tooling_fixture(root)
            archive = root / "synthetic-invalid-archive-path.zip"
            with archive.open("wb") as stream:
                stream.write(marker)
                stream.truncate(EXPECTED_PIN["size_bytes"])
            with archive.open("rb") as stream:
                synthetic_digest = hashlib.file_digest(stream, "sha256").hexdigest()

            result = run_bootstrap(script, "-ArchivePath", str(archive), cwd=root)

            self.assertEqual(result.returncode, 1)
            self.assertEqual(
                result.stdout.splitlines(),
                [
                    "[START] step=VERIFY-SUPABASE-ARCHIVE",
                    "[FAIL] step=VERIFY-SUPABASE-ARCHIVE reason=integrity code=1",
                ],
            )
            combined = result.stdout + result.stderr
            for sensitive_value in (marker.decode("ascii"), archive.name, synthetic_digest):
                self.assertNotIn(sensitive_value, combined)
            self.assertFalse((root / ".tools").exists(), "invalid archive was extracted")
            self.assert_stable_output(result)

    def test_unapproved_url_or_host_is_rejected_without_network(self) -> None:
        urls = (
            "http://github.com/supabase/cli/releases/download/v2.109.1/"
            "supabase_2.109.1_windows_amd64.zip",
            "https://example.com/supabase_2.109.1_windows_amd64.zip",
        )
        for url in urls:
            with self.subTest(url=url), tempfile.TemporaryDirectory(
                prefix="sejong supabase source "
            ) as directory:
                root = Path(directory)
                script = copy_tooling_fixture(root, url=url)
                local_archive = root / "local-source-rejection-fixture.zip"
                local_archive.write_bytes(b"offline-only")

                result = run_bootstrap(
                    script,
                    "-ArchivePath",
                    str(local_archive),
                    cwd=root,
                )

                self.assertEqual(result.returncode, 2)
                self.assertEqual(
                    result.stdout.strip(),
                    "[FAIL] step=VALIDATE-SUPABASE-MANIFEST "
                    "reason=unapproved-source code=2",
                )
                self.assertFalse((root / ".tools").exists(), "rejected source was downloaded")
                self.assertNotIn(url, result.stdout + result.stderr)
                self.assert_stable_output(result)


if __name__ == "__main__":
    unittest.main()
