from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SOURCE_MANIFEST = ROOT / "scripts" / "supabase-cli.local-patch.source.json"
RUNTIME_MANIFEST = ROOT / "scripts" / "supabase-cli.local-patch.runtime.json"
PATCH_PATH = ROOT / "scripts" / "patches" / "supabase-cli-v2.109.1-db-loopback.patch"
BOOTSTRAP_PATH = ROOT / "scripts" / "bootstrap_patched_supabase.ps1"

EXPECTED_SOURCE = {
    "schema_version": 1,
    "upstream": {
        "repository": "https://github.com/supabase/cli.git",
        "tag": "v2.109.1",
        "tag_object_sha1": "9d25ff8b5b0fba3c6f0ef000e7dd658c8d710c38",
        "commit_sha1": "6d4c19870ed213ba7f682f117d0345c8a40bfa94",
    },
    "go": {
        "version": "1.25.11",
        "platform": "windows-amd64",
        "url": "https://dl.google.com/go/go1.25.11.windows-amd64.zip",
        "sha256": "b7401f1b41517428e537493316256fb7cf03c66a130a0103ab07f3a2152e2112",
    },
    "patch": {
        "relative_path": "scripts/patches/supabase-cli-v2.109.1-db-loopback.patch",
        "size_bytes": 1824,
        "sha256": "109c096480e8185d761e9ce8fba10e93efc55190c42eab978f769a6993833f7d",
        "allowed_files": [
            "apps/cli-go/internal/db/start/start_test.go",
            "apps/cli-go/internal/db/start/start.go",
        ],
    },
    "workspace": {
        "checkout_a": "s/a",
        "checkout_b": "s/b",
        "max_tracked_relative_file_path_length": 134,
        "max_absolute_file_path_length": 248,
    },
    "build": {
        "working_directory": "apps/cli-go",
        "version": "2.109.1",
        "goos": "windows",
        "goarch": "amd64",
        "cgo_enabled": "0",
        "goproxy": "https://proxy.golang.org",
        "gosumdb": "sum.golang.org",
        "goprivate": "",
        "gonoproxy": "",
        "gonosumdb": "",
        "goinsecure": "",
        "goenv": "off",
        "gowork": "off",
        "gotoolchain": "local",
        "goflags": "",
        "goamd64": "v1",
        "goexperiment": "",
        "flags": ["-trimpath", "-buildvcs=false"],
        "ldflags": "-s -w -X github.com/supabase/cli/internal/utils.Version=2.109.1",
    },
}


def powershell_executable() -> str:
    executable = shutil.which("powershell.exe") or shutil.which("powershell")
    if executable is None:
        raise AssertionError("Windows PowerShell 5.1+ is required")
    return executable


@contextmanager
def run_patched_fixture(
    *arguments: str,
    include_runtime: bool,
    mutate_source: Callable[[dict[str, object]], None] | None = None,
) -> Iterator[tuple[subprocess.CompletedProcess[str], Path]]:
    with tempfile.TemporaryDirectory(prefix="sejong patched supabase ") as directory:
        root = Path(directory)
        scripts = root / "scripts"
        patches = scripts / "patches"
        patches.mkdir(parents=True)
        shutil.copy2(BOOTSTRAP_PATH, scripts / BOOTSTRAP_PATH.name)
        shutil.copy2(PATCH_PATH, patches / PATCH_PATH.name)
        source = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
        if mutate_source is not None:
            mutate_source(source)
        (scripts / SOURCE_MANIFEST.name).write_text(
            json.dumps(source, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if include_runtime:
            shutil.copy2(RUNTIME_MANIFEST, scripts / RUNTIME_MANIFEST.name)
        environment = {
            key: os.environ[key]
            for key in ("COMSPEC", "PATHEXT", "SystemRoot", "TEMP", "TMP", "WINDIR")
            if key in os.environ
        }
        result = subprocess.run(
            [
                powershell_executable(),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(scripts / BOOTSTRAP_PATH.name),
                *arguments,
            ],
            cwd=root,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            env=environment,
            timeout=30,
        )
        yield result, root


class PatchedSourceLockTests(unittest.TestCase):
    def test_source_manifest_is_exact(self) -> None:
        self.assertTrue(SOURCE_MANIFEST.is_file())
        self.assertEqual(
            json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8")),
            EXPECTED_SOURCE,
        )

    def test_patch_bytes_hash_and_scope_are_exact(self) -> None:
        payload = PATCH_PATH.read_bytes()
        self.assertEqual(len(payload), EXPECTED_SOURCE["patch"]["size_bytes"])
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            EXPECTED_SOURCE["patch"]["sha256"],
        )
        self.assertNotIn(b"\r\n", payload)
        text = payload.decode("utf-8")
        changed = re.findall(r"^diff --git a/(\S+) b/(\S+)$", text, re.MULTILINE)
        self.assertEqual(
            changed,
            [(path, path) for path in EXPECTED_SOURCE["patch"]["allowed_files"]],
        )
        self.assertEqual(text.count('HostIP: "127.0.0.1"'), 1)
        self.assertNotIn("internal/db/diff", text)


class PatchedBootstrapContractTests(unittest.TestCase):
    def test_multiple_git_applications_select_first_path_without_array_coercion(
        self,
    ) -> None:
        source_git = shutil.which("git.exe")
        self.assertIsNotNone(source_git, "git.exe is required for this regression test")
        with tempfile.TemporaryDirectory(prefix="sejong multiple git ") as directory:
            root = Path(directory)
            first_directory = root / "first"
            second_directory = root / "second"
            first_directory.mkdir()
            second_directory.mkdir()
            first_git = first_directory / "git.exe"
            second_git = second_directory / "git.exe"
            shutil.copy2(source_git, first_git)
            shutil.copy2(source_git, second_git)
            harness = root / "git_discovery_harness.ps1"
            harness.write_text(
                r"""
param(
    [string]$Bootstrap,
    [string]$ExpectedFirst,
    [string]$UnexpectedSecond
)
$ErrorActionPreference = "Stop"
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $Bootstrap,
    [ref]$tokens,
    [ref]$errors
)
if ($errors.Count -ne 0) {
    exit 1
}
$functionAsts = @($ast.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $node.Name -ceq "Get-PatchedGitExecutable"
    },
    $true
))
if ($functionAsts.Count -ne 1) {
    [Console]::Error.WriteLine(
        "expected-one-production-git-discovery-function actual=" +
        $functionAsts.Count
    )
    exit 1
}
. ([ScriptBlock]::Create($functionAsts[0].Extent.Text))
$applications = @(Get-Command git.exe -CommandType Application -ErrorAction Stop)
if ($applications.Count -ne 2) {
    [Console]::Error.WriteLine(
        "expected-two-git-applications actual=" + $applications.Count
    )
    exit 1
}
$result = @(Get-PatchedGitExecutable)
$expected = [System.IO.Path]::GetFullPath($ExpectedFirst)
$unexpected = [System.IO.Path]::GetFullPath($UnexpectedSecond)
if (
    $result.Count -ne 1 -or
    $result[0] -is [array] -or
    -not ($result[0] -is [string]) -or
    [string]::IsNullOrWhiteSpace([string]$result[0]) -or
    -not [System.IO.Path]::IsPathRooted([string]$result[0]) -or
    -not (Test-Path -LiteralPath ([string]$result[0]) -PathType Leaf) -or
    ([string]$result[0]) -cne $expected -or
    ([string]$result[0]).Contains($unexpected)
) {
    [Console]::Error.WriteLine(
        "unexpected-git-selection=" + ($result | ConvertTo-Json -Compress)
    )
    exit 1
}
[Console]::Out.WriteLine("GIT-DISCOVERY-OK")
""".lstrip(),
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["PATH"] = os.pathsep.join(
                (str(first_directory), str(second_directory))
            )
            result = subprocess.run(
                [
                    powershell_executable(),
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(harness),
                    str(BOOTSTRAP_PATH),
                    str(first_git),
                    str(second_git),
                ],
                cwd=root,
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                env=environment,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.strip(), "GIT-DISCOVERY-OK")
            self.assertFalse(result.stderr)

    def test_script_has_only_approved_modes_sources_and_operations(self) -> None:
        script = BOOTSTRAP_PATH.read_text(encoding="utf-8")
        lowered = script.lower()
        for token in (
            '"-BuildCandidate"',
            '"-Install"',
            '"-VerifyOnly"',
            '"-GoArchivePath"',
            "Get-FileHash",
            "git.exe",
            "go.exe",
            '@("mod", "verify")',
            "-trimpath",
            "-buildvcs=false",
            "GOPROXY",
            "GOSUMDB",
            "GOPRIVATE",
            "GONOPROXY",
            "GONOSUMDB",
            "GOINSECURE",
            "GOENV",
            "GOWORK",
            "GOTOOLCHAIN",
            "GOFLAGS",
            "GOAMD64",
            "GOEXPERIMENT",
            "$sourceManifest.workspace.checkout_a",
            "$sourceManifest.workspace.checkout_b",
            "VALIDATE-PATCHED-SUPABASE-CHECKOUT-WORKSPACE",
            '"supabase-build/supabase-v2.109.1-sejong-loopback-a.exe"',
            '"supabase-build/supabase-v2.109.1-sejong-loopback-b.exe"',
        ):
            self.assertIn(token, script)
        for forbidden in (
            "npm install",
            "bun build",
            "winget",
            "supabase login",
            "supabase link",
            "supabase db push",
            "volume prune",
            "system prune",
        ):
            self.assertNotIn(forbidden, lowered)

    def test_remove_owned_path_cleans_inclusive_248_character_tree(self) -> None:
        """Existing PS5.1 cleanup must remove an owned non-reparse tree at the inclusive cap."""
        with tempfile.TemporaryDirectory(prefix="sejong remove 248 ") as directory:
            root = Path(directory)
            tool_root = root / ".tools"
            checkout = tool_root / "s" / "a"
            checkout.mkdir(parents=True)
            leaf_name_length = 248 - len(str(checkout)) - 1
            self.assertGreater(leaf_name_length, 0)
            leaf = checkout / ("x" * leaf_name_length)
            leaf.write_bytes(b"inclusive-path-budget")
            self.assertEqual(len(str(leaf)), 248)

            harness = root / "remove_248_harness.ps1"
            harness.write_text(
                r"""
param([string]$Bootstrap, [string]$ToolRoot, [string]$Checkout)
$ErrorActionPreference = "Stop"
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $Bootstrap,
    [ref]$tokens,
    [ref]$errors
)
if ($errors.Count -ne 0) {
    exit 1
}
$wanted = @(
    "Throw-PatchedBootstrapFailure",
    "Resolve-SafeChildPath",
    "Remove-OwnedPath"
)
foreach ($functionAst in @($ast.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $wanted -contains $node.Name
    },
    $true
))) {
    . ([ScriptBlock]::Create($functionAst.Extent.Text))
}
Remove-OwnedPath $ToolRoot $Checkout
if (Test-Path -LiteralPath $Checkout) {
    [Console]::Error.WriteLine("inclusive-tree-remains")
    exit 1
}
[Console]::Out.WriteLine("REMOVE-248-OK")
""".lstrip(),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    powershell_executable(),
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(harness),
                    str(BOOTSTRAP_PATH),
                    str(tool_root),
                    str(checkout),
                ],
                cwd=root,
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.strip(), "REMOVE-248-OK")
            self.assertFalse(result.stderr)
            self.assertFalse(checkout.exists())

    def test_short_checkout_reparse_is_rejected_and_external_sentinel_untouched(
        self,
    ) -> None:
        """A `.tools/s` or `.tools/s/a` junction must fail controlled before external deletion."""
        for junction_relative in (Path("s"), Path("s") / "a"):
            with self.subTest(junction_relative=junction_relative.as_posix()), tempfile.TemporaryDirectory(
                prefix="sejong short checkout reparse "
            ) as directory:
                root = Path(directory)
                tool_root = root / ".tools"
                junction = tool_root / junction_relative
                junction.parent.mkdir(parents=True)
                external = root / "external-checkout"
                external.mkdir()
                sentinel = external / "sentinel.txt"
                payload = b"external-sentinel"
                sentinel.write_bytes(payload)

                junction_environment = os.environ.copy()
                junction_environment["SEJONG_TEST_JUNCTION_ALIAS"] = str(junction)
                junction_environment["SEJONG_TEST_JUNCTION_TARGET"] = str(external)
                junction_result = subprocess.run(
                    [
                        powershell_executable(),
                        "-NoProfile",
                        "-Command",
                        "New-Item -ItemType Junction "
                        "-Path $env:SEJONG_TEST_JUNCTION_ALIAS "
                        "-Target $env:SEJONG_TEST_JUNCTION_TARGET | Out-Null",
                    ],
                    capture_output=True,
                    check=False,
                    encoding="utf-8",
                    errors="replace",
                    env=junction_environment,
                    timeout=30,
                )
                self.assertEqual(junction_result.returncode, 0, junction_result.stderr)

                harness = root / "short_checkout_reparse_harness.ps1"
                harness.write_text(
                    r"""
param([string]$Bootstrap, [string]$ToolRoot)
$ErrorActionPreference = "Stop"
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $Bootstrap,
    [ref]$tokens,
    [ref]$errors
)
if ($errors.Count -ne 0) {
    exit 1
}
$wanted = @(
    "Throw-PatchedBootstrapFailure",
    "Resolve-SafeChildPath",
    "Remove-OwnedPath",
    "Assert-PatchedCheckoutPathBudget",
    "New-VerifiedSupabaseCheckout"
)
foreach ($functionAst in @($ast.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $wanted -contains $node.Name
    },
    $true
))) {
    . ([ScriptBlock]::Create($functionAst.Extent.Text))
}
$script:ToolRoot = [System.IO.Path]::GetFullPath($ToolRoot)
$script:CurrentStep = "TEST-SHORT-CHECKOUT-REPARSE"
try {
    $null = New-VerifiedSupabaseCheckout "s/a" 134 248
    [Console]::Error.WriteLine("reparse-checkout-unexpectedly-succeeded")
    exit 1
}
catch {
    $failure = $_.Exception
    if (
        -not $failure.Data.Contains("PatchedBootstrapFailure") -or
        -not [bool]$failure.Data["PatchedBootstrapFailure"] -or
        [string]$failure.Data["Step"] -cne "VALIDATE-PATCHED-SUPABASE-PATH" -or
        [string]$failure.Data["Reason"] -cne "invalid" -or
        [int]$failure.Data["Code"] -ne 2
    ) {
        [Console]::Error.WriteLine("unexpected-reparse-failure")
        exit 1
    }
}
[Console]::Out.WriteLine("SHORT-CHECKOUT-REPARSE-OK")
""".lstrip(),
                    encoding="utf-8",
                )
                try:
                    result = subprocess.run(
                        [
                            powershell_executable(),
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            str(harness),
                            str(BOOTSTRAP_PATH),
                            str(tool_root),
                        ],
                        cwd=root,
                        capture_output=True,
                        check=False,
                        encoding="utf-8",
                        errors="replace",
                        timeout=30,
                    )
                    self.assertEqual(
                        result.returncode,
                        0,
                        result.stdout + result.stderr,
                    )
                    self.assertEqual(
                        result.stdout.strip(),
                        "SHORT-CHECKOUT-REPARSE-OK",
                    )
                    self.assertFalse(result.stderr)
                    self.assertTrue(junction.exists())
                    self.assertEqual(sentinel.read_bytes(), payload)
                finally:
                    if junction.exists():
                        os.rmdir(junction)

    def test_checkout_workspace_preflight_validates_both_roots_before_toolchain_or_mutation(
        self,
    ) -> None:
        """Both manifest-derived checkout budgets must fail closed before mutable work."""
        with tempfile.TemporaryDirectory(prefix="sj-preflight-ast-") as ast_directory:
            ast_root = Path(ast_directory)
            harness = ast_root / "preflight_ast_harness.ps1"
            harness.write_text(
                r"""
param([string]$Bootstrap)
$ErrorActionPreference = "Stop"
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $Bootstrap,
    [ref]$tokens,
    [ref]$errors
)
if ($errors.Count -ne 0) {
    [Console]::Error.WriteLine("parse-failed")
    exit 1
}
$mainTries = @($ast.EndBlock.Statements | Where-Object {
    $_ -is [System.Management.Automation.Language.TryStatementAst]
})
if ($mainTries.Count -ne 1) {
    [Console]::Error.WriteLine("expected-one-main-try")
    exit 1
}
$main = $mainTries[0]
$commands = @($main.Body.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.CommandAst]
    },
    $true
))
$budgetCommands = @($commands | Where-Object {
    $_.GetCommandName() -ceq "Assert-PatchedCheckoutPathBudget"
} | Sort-Object { $_.Extent.StartOffset })
if ($budgetCommands.Count -ne 2) {
    [Console]::Error.WriteLine("expected-two-budget-commands")
    exit 1
}
$budgetA = @($budgetCommands | Where-Object {
    $_.Extent.Text -cmatch '\$sourceManifest\.workspace\.checkout_a'
})
$budgetB = @($budgetCommands | Where-Object {
    $_.Extent.Text -cmatch '\$sourceManifest\.workspace\.checkout_b'
})
foreach ($budget in $budgetCommands) {
    if (
        $budget.Extent.Text -cnotmatch
            '\$sourceManifest\.workspace\.max_tracked_relative_file_path_length' -or
        $budget.Extent.Text -cnotmatch
            '\$sourceManifest\.workspace\.max_absolute_file_path_length'
    ) {
        [Console]::Error.WriteLine("budget-command-not-manifest-derived")
        exit 1
    }
}
if ($budgetA.Count -ne 1 -or $budgetB.Count -ne 1) {
    [Console]::Error.WriteLine("checkout-budget-roots-not-exact")
    exit 1
}
$preflightEnd = 0
foreach ($budget in $budgetCommands) {
    if ($budget.Extent.EndOffset -gt $preflightEnd) {
        $preflightEnd = $budget.Extent.EndOffset
    }
}
$dangerousCommands = @(
    "Get-VerifiedGoToolchain",
    "Get-PatchedGitExecutable",
    "New-VerifiedSupabaseCheckout",
    "Apply-And-TestSupabasePatch",
    "Build-PatchedSupabase",
    "Install-PatchedSupabaseBinary",
    "Download-ApprovedGoArchive",
    "Expand-Archive",
    "Invoke-PatchedChild",
    "Invoke-VerifiedGit",
    "Invoke-WebRequest",
    "Invoke-RestMethod",
    "New-Item",
    "Remove-Item",
    "Remove-OwnedPath",
    "Move-Item",
    "Copy-Item",
    "Start-Process"
)
foreach ($command in $commands) {
    $name = $command.GetCommandName()
    if (
        $dangerousCommands -ccontains $name -and
        $command.Extent.StartOffset -lt $preflightEnd
    ) {
        [Console]::Error.WriteLine("dangerous-operation-before-preflight")
        exit 1
    }
}
$dangerousMembers = @(
    "CreateDirectory",
    "Delete",
    "DownloadFile",
    "GetAsync",
    "Move",
    "Replace",
    "SetEnvironmentVariable"
)
$memberCalls = @($main.Body.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.InvokeMemberExpressionAst]
    },
    $true
))
foreach ($memberCall in $memberCalls) {
    $memberName = [string]$memberCall.Member.Value
    if (
        $dangerousMembers -ccontains $memberName -and
        $memberCall.Extent.StartOffset -lt $preflightEnd
    ) {
        [Console]::Error.WriteLine("dangerous-member-before-preflight")
        exit 1
    }
}
[Console]::Out.WriteLine("PREFLIGHT-AST-OK")
""".lstrip(),
                encoding="utf-8",
            )

            def run_ast_audit(bootstrap: Path) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [
                        powershell_executable(),
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(harness),
                        str(bootstrap),
                    ],
                    cwd=ast_root,
                    capture_output=True,
                    check=False,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                )

            production_result = run_ast_audit(BOOTSTRAP_PATH)
            self.assertEqual(
                production_result.returncode,
                0,
                production_result.stdout + production_result.stderr,
            )
            self.assertEqual(production_result.stdout.strip(), "PREFLIGHT-AST-OK")
            self.assertFalse(production_result.stderr)

            script = BOOTSTRAP_PATH.read_text(encoding="utf-8")
            marker = (
                '$script:ToolRoot = Resolve-SafeChildPath '
                '$script:RepositoryRoot ".tools"'
            )
            self.assertEqual(script.count(marker), 1)
            mutated = script.replace(
                marker,
                '$null = Invoke-PatchedChild "bad.exe" @() '
                '$script:RepositoryRoot 1000\n    ' + marker,
                1,
            )
            mutated_path = ast_root / "preflight_regression.ps1"
            mutated_path.write_text(mutated, encoding="utf-8")
            mutation_result = run_ast_audit(mutated_path)
            self.assertNotEqual(mutation_result.returncode, 0)
            self.assertIn(
                "dangerous-operation-before-preflight",
                mutation_result.stderr,
            )

        with tempfile.TemporaryDirectory(prefix="sj-preflight-") as directory:
            base = Path(directory)
            root_length = 103
            padding_length = root_length - len(str(base)) - 1
            self.assertGreater(padding_length, 0)
            fixture_root = base / ("r" * padding_length)
            fixture_root.mkdir()
            checkout = fixture_root / ".tools" / "s" / "a"
            self.assertEqual(len(str(checkout)) + 1 + 134, 249)

            @contextmanager
            def fixed_directory(*_args: object, **_kwargs: object) -> Iterator[str]:
                yield str(fixture_root)

            with patch.object(tempfile, "TemporaryDirectory", fixed_directory):
                with run_patched_fixture(
                    "-BuildCandidate",
                    include_runtime=False,
                ) as (result, root):
                    self.assertEqual(root, fixture_root)
                    self.assertEqual(result.returncode, 2)
                    self.assertTrue(
                        result.stdout.strip().endswith(
                            "[START] step=VALIDATE-PATCHED-SUPABASE-CHECKOUT-WORKSPACE\n"
                            "[FAIL] step=VALIDATE-PATCHED-SUPABASE-CHECKOUT-WORKSPACE "
                            "reason=invalid code=2"
                        ),
                        result.stdout,
                    )
                    self.assertFalse(result.stderr)
                    self.assertFalse((root / ".tools").exists())

    def test_checkout_budget_accepts_244_and_248_rejects_249_before_cleanup(
        self,
    ) -> None:
        """The inclusive budget accepts 248 and rejects 249 before cleanup."""
        with tempfile.TemporaryDirectory(prefix="sj-budget-") as directory:
            base = Path(directory)

            def tool_root_for_projection(projected: int) -> Path:
                checkout_length = projected - 1 - 134
                tool_root_length = checkout_length - len(str(Path("s") / "a")) - 1
                padding_length = tool_root_length - len(str(base)) - 1
                self.assertGreater(padding_length, 0)
                tool_root = base / (str(projected)[-1] * padding_length)
                self.assertEqual(
                    len(str(tool_root / "s" / "a")) + 1 + 134,
                    projected,
                )
                return tool_root

            tool_roots = {
                projected: tool_root_for_projection(projected)
                for projected in (244, 248, 249)
            }
            harness = base / "checkout_budget_harness.ps1"
            harness.write_text(
                r"""
param(
    [string]$Bootstrap,
    [string]$ToolRoot244,
    [string]$ToolRoot248,
    [string]$ToolRoot249
)
$ErrorActionPreference = "Stop"
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $Bootstrap,
    [ref]$tokens,
    [ref]$errors
)
if ($errors.Count -ne 0) { exit 1 }
$wanted = @(
    "Throw-PatchedBootstrapFailure",
    "Resolve-SafeChildPath",
    "Assert-PatchedCheckoutPathBudget",
    "New-VerifiedSupabaseCheckout"
)
foreach ($functionAst in @($ast.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $wanted -contains $node.Name
    },
    $true
))) {
    . ([ScriptBlock]::Create($functionAst.Extent.Text))
}
$script:CurrentStep = "VALIDATE-PATCHED-SUPABASE-CHECKOUT-WORKSPACE"
foreach ($case in @(
    [pscustomobject]@{ Root = $ToolRoot244; Projected = 244 },
    [pscustomobject]@{ Root = $ToolRoot248; Projected = 248 }
)) {
    $script:ToolRoot = [System.IO.Path]::GetFullPath($case.Root)
    $actual = Assert-PatchedCheckoutPathBudget "s/a" 134 248
    $expected = [System.IO.Path]::GetFullPath((Join-Path $script:ToolRoot "s/a"))
    if ($actual -cne $expected -or ($actual.Length + 1 + 134) -ne $case.Projected) {
        [Console]::Error.WriteLine("unexpected-accepted-projection")
        exit 1
    }
}
$script:ToolRoot = [System.IO.Path]::GetFullPath($ToolRoot249)
$script:RemoveCount = 0
function Remove-OwnedPath {
    param([string]$Root, [string]$Candidate)
    $script:RemoveCount += 1
}
try {
    $null = New-VerifiedSupabaseCheckout "s/a" 134 248
    [Console]::Error.WriteLine("projection-249-unexpectedly-succeeded")
    exit 1
}
catch {
    $failure = $_.Exception
    if (
        -not $failure.Data.Contains("PatchedBootstrapFailure") -or
        -not [bool]$failure.Data["PatchedBootstrapFailure"] -or
        [string]$failure.Data["Step"] -cne
            "VALIDATE-PATCHED-SUPABASE-CHECKOUT-WORKSPACE" -or
        [string]$failure.Data["Reason"] -cne "invalid" -or
        [int]$failure.Data["Code"] -ne 2
    ) {
        [Console]::Error.WriteLine("unexpected-budget-failure")
        exit 1
    }
}
if ($script:RemoveCount -ne 0) {
    [Console]::Error.WriteLine("cleanup-ran-before-budget-rejection")
    exit 1
}
[Console]::Out.WriteLine(
    "VALIDATE-PATCHED-SUPABASE-CHECKOUT-WORKSPACE:invalid:2"
)
""".lstrip(),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    powershell_executable(),
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(harness),
                    str(BOOTSTRAP_PATH),
                    str(tool_roots[244]),
                    str(tool_roots[248]),
                    str(tool_roots[249]),
                ],
                cwd=base,
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(
                result.stdout.strip(),
                "VALIDATE-PATCHED-SUPABASE-CHECKOUT-WORKSPACE:invalid:2",
            )
            self.assertFalse(result.stderr)

    def test_legacy_source_root_is_deny_only_never_checkout_build_or_delete(
        self,
    ) -> None:
        """The quarantined long root remains one exact archive deny literal only."""
        with tempfile.TemporaryDirectory(prefix="sj-legacy-ast-") as directory:
            root = Path(directory)
            harness = root / "legacy_ast_harness.ps1"
            harness.write_text(
                r"""
param([string]$Bootstrap)
$ErrorActionPreference = "Stop"
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $Bootstrap,
    [ref]$tokens,
    [ref]$errors
)
if ($errors.Count -ne 0) {
    [Console]::Error.WriteLine("parse-failed")
    exit 1
}
$legacyStrings = @($ast.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.StringConstantExpressionAst] -and
            $node.Value.StartsWith(
                "supabase-source",
                [System.StringComparison]::OrdinalIgnoreCase
            )
    },
    $true
))
if (
    $legacyStrings.Count -ne 1 -or
    $legacyStrings[0].Value -cne "supabase-source"
) {
    [Console]::Error.WriteLine("legacy-string-boundary-not-exact")
    exit 1
}
$legacy = $legacyStrings[0]
$enclosingForEach = $legacy
while (
    $null -ne $enclosingForEach -and
    $enclosingForEach -isnot [System.Management.Automation.Language.ForEachStatementAst]
) {
    $enclosingForEach = $enclosingForEach.Parent
}
$enclosingFunction = $legacy
while (
    $null -ne $enclosingFunction -and
    $enclosingFunction -isnot [System.Management.Automation.Language.FunctionDefinitionAst]
) {
    $enclosingFunction = $enclosingFunction.Parent
}
if (
    $null -eq $enclosingForEach -or
    $enclosingForEach.Variable.VariablePath.UserPath -cne "mutableChild" -or
    $null -eq $enclosingFunction -or
    $enclosingFunction.Name -cne "Get-VerifiedGoToolchain"
) {
    [Console]::Error.WriteLine("legacy-string-not-in-archive-deny-context")
    exit 1
}
$bodyCommands = @($enclosingForEach.Body.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.CommandAst]
    },
    $true
))
$actualCommands = @($bodyCommands | ForEach-Object {
    $_.GetCommandName()
} | Sort-Object)
$expectedCommands = @(
    "Resolve-PatchedCanonicalComparisonPath",
    "Resolve-SafeChildPath",
    "Test-PatchedPathWithin",
    "Throw-PatchedBootstrapFailure"
) | Sort-Object
if (
    $actualCommands.Count -ne $expectedCommands.Count -or
    @(Compare-Object -ReferenceObject $expectedCommands `
        -DifferenceObject $actualCommands -CaseSensitive).Count -ne 0
) {
    [Console]::Error.WriteLine("legacy-deny-body-has-active-operation")
    exit 1
}
$bodyStatements = @($enclosingForEach.Body.Statements)
if (
    $bodyStatements.Count -ne 3 -or
    $bodyStatements[0] -isnot
        [System.Management.Automation.Language.AssignmentStatementAst] -or
    $bodyStatements[1] -isnot
        [System.Management.Automation.Language.AssignmentStatementAst] -or
    $bodyStatements[2] -isnot
        [System.Management.Automation.Language.IfStatementAst] -or
    $bodyStatements[0].Left.VariablePath.UserPath -cne "mutableRoot" -or
    $bodyStatements[1].Left.VariablePath.UserPath -cne "canonicalMutableRoot" -or
    $bodyStatements[2].Clauses.Count -ne 1 -or
    $null -ne $bodyStatements[2].ElseClause
) {
    [Console]::Error.WriteLine("legacy-deny-body-shape-changed")
    exit 1
}
$allAssignments = @($enclosingForEach.Body.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.AssignmentStatementAst]
    },
    $true
) | Sort-Object { $_.Extent.StartOffset })
$allIfStatements = @($enclosingForEach.Body.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.IfStatementAst]
    },
    $true
))
$controlFlowEscapes = @($enclosingForEach.Body.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.ReturnStatementAst] -or
            $node -is [System.Management.Automation.Language.BreakStatementAst] -or
            $node -is [System.Management.Automation.Language.ContinueStatementAst] -or
            $node -is [System.Management.Automation.Language.ExitStatementAst] -or
            $node -is [System.Management.Automation.Language.TrapStatementAst]
    },
    $true
))
$conditionText = [System.Text.RegularExpressions.Regex]::Replace(
    $bodyStatements[2].Clauses[0].Item1.Extent.Text,
    '\s+',
    ' '
).Trim()
$ifBodyStatements = @($bodyStatements[2].Clauses[0].Item2.Statements)
$firstRightText = [System.Text.RegularExpressions.Regex]::Replace(
    $allAssignments[0].Right.Extent.Text,
    '\s+',
    ' '
).Trim()
$secondRightText = [System.Text.RegularExpressions.Regex]::Replace(
    $allAssignments[1].Right.Extent.Text,
    '\s+',
    ' '
).Trim()
if (
    $allAssignments.Count -ne 2 -or
    $allIfStatements.Count -ne 1 -or
    $controlFlowEscapes.Count -ne 0 -or
    $allAssignments[0].Operator -ne
        [System.Management.Automation.Language.TokenKind]::Equals -or
    $allAssignments[1].Operator -ne
        [System.Management.Automation.Language.TokenKind]::Equals -or
    $firstRightText -cne
        'Resolve-SafeChildPath $script:ToolRoot $mutableChild' -or
    $secondRightText -cne
        'Resolve-PatchedCanonicalComparisonPath $mutableRoot' -or
    $conditionText -cne
        'Test-PatchedPathWithin $canonicalMutableRoot $canonicalArchivePath' -or
    $ifBodyStatements.Count -ne 1 -or
    $ifBodyStatements[0] -isnot [System.Management.Automation.Language.PipelineAst] -or
    ([System.Text.RegularExpressions.Regex]::Replace(
        $ifBodyStatements[0].Extent.Text,
        '\s+',
        ' '
    ).Trim()) -cne
        'Throw-PatchedBootstrapFailure $script:CurrentStep "invalid" 2'
) {
    [Console]::Error.WriteLine("legacy-deny-descendant-shape-changed")
    exit 1
}
$memberCalls = @($enclosingForEach.Body.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.InvokeMemberExpressionAst]
    },
    $true
))
if ($memberCalls.Count -ne 0) {
    [Console]::Error.WriteLine("legacy-deny-body-has-active-member-operation")
    exit 1
}
$trackedVariables = @("mutableChild", "mutableRoot", "canonicalMutableRoot")
$functionVariables = @($enclosingFunction.Body.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.VariableExpressionAst]
    },
    $true
))
foreach ($variable in $functionVariables) {
    if (
        $trackedVariables -ccontains $variable.VariablePath.UserPath -and
        (
            $variable.Extent.StartOffset -lt $enclosingForEach.Extent.StartOffset -or
            $variable.Extent.EndOffset -gt $enclosingForEach.Extent.EndOffset
        )
    ) {
        [Console]::Error.WriteLine("legacy-deny-variable-escapes-loop")
        exit 1
    }
}
$dangerousCommands = @(
    "Build-PatchedSupabase",
    "New-VerifiedSupabaseCheckout",
    "Remove-OwnedPath",
    "Remove-Item",
    "New-Item",
    "Move-Item",
    "Copy-Item"
)
foreach ($command in @($ast.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.CommandAst]
    },
    $true
))) {
    if ($dangerousCommands -ccontains $command.GetCommandName()) {
        $legacyArguments = @($command.FindAll(
            {
                param($node)
                $node -is [System.Management.Automation.Language.StringConstantExpressionAst] -and
                    $node.Value.StartsWith(
                        "supabase-source",
                        [System.StringComparison]::OrdinalIgnoreCase
                    )
            },
            $true
        ))
        if ($legacyArguments.Count -ne 0) {
            [Console]::Error.WriteLine("legacy-string-used-by-active-command")
            exit 1
        }
    }
}
[Console]::Out.WriteLine("LEGACY-DENY-AST-OK")
""".lstrip(),
                encoding="utf-8",
            )

            def run_ast_audit(bootstrap: Path) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [
                        powershell_executable(),
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(harness),
                        str(bootstrap),
                    ],
                    cwd=root,
                    capture_output=True,
                    check=False,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                )

            production_result = run_ast_audit(BOOTSTRAP_PATH)
            self.assertEqual(
                production_result.returncode,
                0,
                production_result.stdout + production_result.stderr,
            )
            self.assertEqual(production_result.stdout.strip(), "LEGACY-DENY-AST-OK")
            self.assertFalse(production_result.stderr)

            script = BOOTSTRAP_PATH.read_text(encoding="utf-8")
            marker = (
                "$canonicalMutableRoot = "
                "Resolve-PatchedCanonicalComparisonPath $mutableRoot"
            )
            self.assertEqual(script.count(marker), 1)
            mutated = script.replace(
                marker,
                "Remove-OwnedPath $script:ToolRoot $mutableRoot\n            " + marker,
                1,
            )
            mutated_path = root / "legacy_delete_regression.ps1"
            mutated_path.write_text(mutated, encoding="utf-8")
            mutation_result = run_ast_audit(mutated_path)
            self.assertNotEqual(mutation_result.returncode, 0)
            self.assertIn(
                "legacy-deny-body-has-active-operation",
                mutation_result.stderr,
            )

            alias_marker = (
                "$canonicalMutableRoot = "
                "Resolve-PatchedCanonicalComparisonPath $mutableRoot"
            )
            loop_end_marker = (
                "        }\n"
                "    }\n"
                "    else {\n"
                '        $cacheDirectory = Resolve-SafeChildPath '
                '$script:ToolRoot "cache"'
            )
            self.assertEqual(script.count(alias_marker), 1)
            self.assertEqual(script.count(loop_end_marker), 1)
            alias_mutated = script.replace(
                alias_marker,
                "$escapedLegacyRoot = $mutableRoot\n            " + alias_marker,
                1,
            ).replace(
                loop_end_marker,
                "        }\n"
                "        Remove-OwnedPath $script:ToolRoot $escapedLegacyRoot\n"
                "    }\n"
                "    else {\n"
                '        $cacheDirectory = Resolve-SafeChildPath '
                '$script:ToolRoot "cache"',
                1,
            )
            alias_mutated_path = root / "legacy_alias_delete_regression.ps1"
            alias_mutated_path.write_text(alias_mutated, encoding="utf-8")
            alias_mutation_result = run_ast_audit(alias_mutated_path)
            self.assertNotEqual(alias_mutation_result.returncode, 0)
            self.assertIn(
                "legacy-deny-body-shape-changed",
                alias_mutation_result.stderr,
            )

            nested_if_marker = (
                "if (Test-PatchedPathWithin $canonicalMutableRoot "
                "$canonicalArchivePath) {\n"
                "                Throw-PatchedBootstrapFailure "
                '$script:CurrentStep "invalid" 2\n'
                "            }"
            )
            self.assertEqual(script.count(nested_if_marker), 1)
            nested_alias_mutated = script.replace(
                nested_if_marker,
                "if (Test-PatchedPathWithin $canonicalMutableRoot "
                "$canonicalArchivePath) {\n"
                "                $escapedLegacyRoot = $mutableRoot\n"
                "                continue\n"
                "                Throw-PatchedBootstrapFailure "
                '$script:CurrentStep "invalid" 2\n'
                "            }",
                1,
            ).replace(
                loop_end_marker,
                "        }\n"
                "        Remove-OwnedPath $script:ToolRoot $escapedLegacyRoot\n"
                "    }\n"
                "    else {\n"
                '        $cacheDirectory = Resolve-SafeChildPath '
                '$script:ToolRoot "cache"',
                1,
            )
            nested_alias_path = root / "legacy_nested_alias_regression.ps1"
            nested_alias_path.write_text(nested_alias_mutated, encoding="utf-8")
            nested_alias_result = run_ast_audit(nested_alias_path)
            self.assertNotEqual(nested_alias_result.returncode, 0)
            self.assertIn(
                "legacy-deny-descendant-shape-changed",
                nested_alias_result.stderr,
            )

    def test_verify_only_without_runtime_manifest_is_non_mutating(self) -> None:
        with run_patched_fixture("-VerifyOnly", include_runtime=False) as (result, root):
            self.assertEqual(result.returncode, 2)
            self.assertEqual(
                result.stdout.strip(),
                "[FAIL] step=LOAD-PATCHED-SUPABASE-RUNTIME-MANIFEST reason=missing code=2",
            )
            self.assertFalse(result.stderr)
            self.assertFalse((root / ".tools").exists())

    def test_duplicate_or_unknown_arguments_fail_before_work(self) -> None:
        for arguments in (
            ("-VerifyOnly", "-VerifyOnly"),
            ("-VerifyOnly", "-Unknown"),
            ("-GoArchivePath",),
        ):
            with self.subTest(arguments=arguments):
                with run_patched_fixture(*arguments, include_runtime=False) as (result, root):
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(
                        result.stdout.strip(),
                        "[FAIL] step=VALIDATE-PATCHED-SUPABASE-ARGUMENTS reason=invalid code=2",
                    )
                    self.assertFalse(result.stderr)
                    self.assertFalse((root / ".tools").exists())

    def test_unapproved_source_manifest_fails_before_network(self) -> None:
        with run_patched_fixture(
            "-BuildCandidate",
            mutate_source=lambda value: value["upstream"].update(
                {"repository": "https://example.invalid/supabase/cli.git"}
            ),
            include_runtime=False,
        ) as (result, root):
            self.assertEqual(result.returncode, 2)
            self.assertEqual(
                result.stdout.strip(),
                "[FAIL] step=VALIDATE-PATCHED-SUPABASE-SOURCE-MANIFEST reason=unapproved-source code=2",
            )
            self.assertFalse(result.stderr)
            self.assertFalse((root / ".tools").exists())

    def test_duplicate_source_property_fails_before_runtime_or_network(self) -> None:
        duplicate_source = SOURCE_MANIFEST.read_text(encoding="utf-8").replace(
            '    "repository": "https://github.com/supabase/cli.git",',
            '    "repository": "https://github.com/supabase/cli.git",\n'
            '    "repository": "https://github.com/supabase/cli.git",',
            1,
        )
        with patch.object(json, "dumps", return_value=duplicate_source.rstrip("\n")):
            with run_patched_fixture("-VerifyOnly", include_runtime=False) as (result, root):
                self.assertEqual(result.returncode, 2)
                self.assertEqual(
                    result.stdout.strip(),
                    "[FAIL] step=VALIDATE-PATCHED-SUPABASE-SOURCE-MANIFEST "
                    "reason=unapproved-source code=2",
                )
                self.assertFalse(result.stderr)
                self.assertFalse((root / ".tools").exists())

    def test_non_scalar_source_values_fail_before_runtime_or_network(self) -> None:
        scalar_paths = (
            ("schema_version",),
            ("upstream", "repository"),
            ("upstream", "tag"),
            ("upstream", "tag_object_sha1"),
            ("upstream", "commit_sha1"),
            ("go", "version"),
            ("go", "platform"),
            ("go", "url"),
            ("go", "sha256"),
            ("patch", "relative_path"),
            ("patch", "size_bytes"),
            ("patch", "sha256"),
            ("workspace", "checkout_a"),
            ("workspace", "checkout_b"),
            ("workspace", "max_tracked_relative_file_path_length"),
            ("workspace", "max_absolute_file_path_length"),
            ("build", "working_directory"),
            ("build", "version"),
            ("build", "goos"),
            ("build", "goarch"),
            ("build", "cgo_enabled"),
            ("build", "goproxy"),
            ("build", "gosumdb"),
            ("build", "goprivate"),
            ("build", "gonoproxy"),
            ("build", "gonosumdb"),
            ("build", "goinsecure"),
            ("build", "goenv"),
            ("build", "gowork"),
            ("build", "gotoolchain"),
            ("build", "goflags"),
            ("build", "goamd64"),
            ("build", "goexperiment"),
            ("build", "ldflags"),
        )

        def poison_scalar(source: dict[str, object], path: tuple[str, ...]) -> None:
            node = source
            for segment in path[:-1]:
                node = node[segment]  # type: ignore[assignment]
            value = node[path[-1]]
            node[path[-1]] = str(value) if isinstance(value, int) else [value]

        cases = tuple((path, None) for path in scalar_paths) + (
            (("patch", "allowed_files", "0"), "nested"),
            (("build", "flags", "0"), "nested"),
        )
        for path, kind in cases:
            with self.subTest(path=".".join(path)):
                def mutate(
                    source: dict[str, object],
                    path: tuple[str, ...] = path,
                    kind: str | None = kind,
                ) -> None:
                    if kind == "nested":
                        values = source[path[0]][path[1]]  # type: ignore[index]
                        values[int(path[2])] = [values[int(path[2])]]
                    else:
                        poison_scalar(source, path)

                with run_patched_fixture(
                    "-VerifyOnly",
                    mutate_source=mutate,
                    include_runtime=False,
                ) as (result, root):
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(
                        result.stdout.strip(),
                        "[FAIL] step=VALIDATE-PATCHED-SUPABASE-SOURCE-MANIFEST "
                        "reason=unapproved-source code=2",
                    )
                    self.assertFalse(result.stderr)
                    self.assertFalse((root / ".tools").exists())

    def test_non_scalar_runtime_values_fail_before_binary_work(self) -> None:
        source_hash = hashlib.sha256(SOURCE_MANIFEST.read_bytes()).hexdigest()
        runtime_template: dict[str, object] = {
            "schema_version": 1,
            "source_manifest_sha256": source_hash,
            "version": "2.109.1",
            "platform": "windows-amd64",
            "relative_path": ".tools/supabase/v2.109.1-sejong-loopback/supabase.exe",
            "sha256": "0" * 64,
        }
        real_copy2 = shutil.copy2
        for key in runtime_template:
            with self.subTest(key=key):
                runtime = dict(runtime_template)
                value = runtime[key]
                runtime[key] = str(value) if isinstance(value, int) else [value]

                def copy_with_runtime(
                    source: str | os.PathLike[str],
                    destination: str | os.PathLike[str],
                    *args: object,
                    runtime: dict[str, object] = runtime,
                    **kwargs: object,
                ) -> str:
                    if Path(source) == RUNTIME_MANIFEST:
                        Path(destination).write_text(
                            json.dumps(runtime, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8",
                        )
                        return str(destination)
                    return str(real_copy2(source, destination, *args, **kwargs))

                with patch.object(shutil, "copy2", side_effect=copy_with_runtime):
                    with run_patched_fixture(
                        "-VerifyOnly",
                        include_runtime=True,
                    ) as (result, root):
                        self.assertEqual(result.returncode, 2)
                        self.assertEqual(
                            result.stdout.strip(),
                            "[FAIL] step=LOAD-PATCHED-SUPABASE-RUNTIME-MANIFEST "
                            "reason=invalid code=2",
                        )
                        self.assertFalse(result.stderr)
                        self.assertFalse((root / ".tools").exists())

    def test_override_inside_owned_cleanup_tree_is_rejected_without_mutation(
        self,
    ) -> None:
        for mutable_child in (
            "cache",
            "go",
            "s",
            "supabase-source",
            "supabase-build",
            "supabase",
        ):
            with self.subTest(mutable_child=mutable_child), tempfile.TemporaryDirectory(
                prefix="sejong unsafe go override "
            ) as directory:
                root = Path(directory)
                override = root / ".tools" / mutable_child / "owned" / "override.zip"
                override.parent.mkdir(parents=True)
                payload = b"read-only-invalid-override"
                override.write_bytes(payload)
                before = {
                    path.relative_to(root).as_posix() for path in root.rglob("*")
                }

                @contextmanager
                def fixed_directory(*_args: object, **_kwargs: object) -> Iterator[str]:
                    yield str(root)

                with patch.object(tempfile, "TemporaryDirectory", fixed_directory):
                    with run_patched_fixture(
                        "-BuildCandidate",
                        "-GoArchivePath",
                        str(override),
                        include_runtime=False,
                    ) as (result, fixture_root):
                        self.assertEqual(fixture_root, root)
                        self.assertEqual(result.returncode, 2)
                        self.assertEqual(
                            result.stdout.strip(),
                            "[START] step=VALIDATE-PATCHED-SUPABASE-CHECKOUT-WORKSPACE\n"
                            "[PASS] step=VALIDATE-PATCHED-SUPABASE-CHECKOUT-WORKSPACE\n"
                            "[START] step=VERIFY-GO-ARCHIVE\n"
                            "[FAIL] step=VERIFY-GO-ARCHIVE reason=invalid code=2",
                        )
                        self.assertFalse(result.stderr)
                        self.assertEqual(override.read_bytes(), payload)
                        after = {
                            path.relative_to(root).as_posix() for path in root.rglob("*")
                        }
                        self.assertEqual(
                            after - before,
                            {
                                "scripts",
                                "scripts/bootstrap_patched_supabase.ps1",
                                "scripts/patches",
                                "scripts/patches/supabase-cli-v2.109.1-db-loopback.patch",
                                "scripts/supabase-cli.local-patch.source.json",
                            },
                        )

    def test_reparse_override_targeting_owned_tree_is_rejected(self) -> None:
        for owned_child in ("go", "s"):
            with self.subTest(owned_child=owned_child), tempfile.TemporaryDirectory(
                prefix="sejong reparse go override "
            ) as directory:
                root = Path(directory)
                owned = root / ".tools" / owned_child / "owned"
                owned.mkdir(parents=True)
                target = owned / "override.zip"
                payload = b"read-only-reparse-override"
                target.write_bytes(payload)
                alias = root / "external-override-alias"
                junction_environment = os.environ.copy()
                junction_environment["SEJONG_TEST_JUNCTION_ALIAS"] = str(alias)
                junction_environment["SEJONG_TEST_JUNCTION_TARGET"] = str(owned)
                junction = subprocess.run(
                    [
                        powershell_executable(),
                        "-NoProfile",
                        "-Command",
                        "New-Item -ItemType Junction "
                        "-Path $env:SEJONG_TEST_JUNCTION_ALIAS "
                        "-Target $env:SEJONG_TEST_JUNCTION_TARGET | Out-Null",
                    ],
                    capture_output=True,
                    check=False,
                    encoding="utf-8",
                    env=junction_environment,
                    errors="replace",
                    timeout=30,
                )
                self.assertEqual(junction.returncode, 0, junction.stderr)

                @contextmanager
                def fixed_directory(*_args: object, **_kwargs: object) -> Iterator[str]:
                    yield str(root)

                try:
                    with patch.object(tempfile, "TemporaryDirectory", fixed_directory):
                        with run_patched_fixture(
                            "-BuildCandidate",
                            "-GoArchivePath",
                            str(alias / "override.zip"),
                            include_runtime=False,
                        ) as (result, _fixture_root):
                            self.assertEqual(result.returncode, 2)
                            self.assertEqual(
                                result.stdout.strip(),
                                "[START] step=VALIDATE-PATCHED-SUPABASE-CHECKOUT-WORKSPACE\n"
                                "[PASS] step=VALIDATE-PATCHED-SUPABASE-CHECKOUT-WORKSPACE\n"
                                "[START] step=VERIFY-GO-ARCHIVE\n"
                                "[FAIL] step=VERIFY-GO-ARCHIVE reason=invalid code=2",
                            )
                            self.assertFalse(result.stderr)
                            self.assertEqual(target.read_bytes(), payload)
                finally:
                    os.rmdir(alias)

    def test_checkout_sets_local_longpaths_before_fetch_and_checkout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sejong checkout argv ") as directory:
            root = Path(directory)
            harness = root / "checkout_argv_harness.ps1"
            harness.write_text(
                r"""
param([string]$Bootstrap, [string]$Root)
$ErrorActionPreference = "Stop"
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $Bootstrap,
    [ref]$tokens,
    [ref]$errors
)
if ($errors.Count -ne 0) {
    exit 1
}
$checkoutFunction = @($ast.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $node.Name -ceq "New-VerifiedSupabaseCheckout"
    },
    $true
))
if ($checkoutFunction.Count -ne 1) {
    [Console]::Error.WriteLine("missing-production-checkout-function")
    exit 1
}
$parameterNames = @(
    $checkoutFunction[0].Body.ParamBlock.Parameters |
        ForEach-Object { $_.Name.VariablePath.UserPath }
)
if (
    $parameterNames.Count -ne 3 -or
    $parameterNames[0] -cne "Destination" -or
    $parameterNames[1] -cne "MaxTrackedRelativeFilePathLength" -or
    $parameterNames[2] -cne "MaxAbsoluteFilePathLength"
) {
    [Console]::Error.WriteLine("unexpected-production-checkout-signature")
    exit 1
}
. ([ScriptBlock]::Create($checkoutFunction[0].Extent.Text))

$script:ToolRoot = [System.IO.Path]::GetFullPath((Join-Path $Root ".tools"))
$script:ExpectedDestination = "s/a"
$script:ExpectedCheckout = [System.IO.Path]::GetFullPath(
    (Join-Path $script:ToolRoot $script:ExpectedDestination)
)
$script:CurrentStep = "TEST-CHECKOUT-ARGV"
$script:CapturedGitCalls = @()
$script:RemovedOwnedPath = $false
$script:BudgetCallCount = 0
$null = [System.IO.Directory]::CreateDirectory($script:ToolRoot)

function Resolve-SafeChildPath {
    param([string]$Parent, [string]$Child)
    if (
        $Parent -cne $script:ToolRoot -or
        $Child -cne $script:ExpectedDestination
    ) {
        throw "unexpected-checkout-path"
    }
    return $script:ExpectedCheckout
}

function Remove-OwnedPath {
    param([string]$Parent, [string]$Target)
    if (
        $Parent -cne $script:ToolRoot -or
        $Target -cne $script:ExpectedCheckout -or
        $script:BudgetCallCount -ne 1
    ) {
        throw "unexpected-owned-path-removal"
    }
    $script:RemovedOwnedPath = $true
}

function Assert-PatchedCheckoutPathBudget {
    param(
        [string]$Destination,
        [int]$MaxTrackedRelativeFilePathLength,
        [int]$MaxAbsoluteFilePathLength
    )
    if (
        $script:RemovedOwnedPath -or
        $Destination -cne $script:ExpectedDestination -or
        $MaxTrackedRelativeFilePathLength -ne 134 -or
        $MaxAbsoluteFilePathLength -ne 248
    ) {
        throw "unexpected-checkout-budget-call"
    }
    $script:BudgetCallCount += 1
    return $script:ExpectedCheckout
}

function Throw-PatchedBootstrapFailure {
    param([string]$Step, [string]$Reason, [int]$Code)
    throw "unexpected-bootstrap-failure:${Step}:${Reason}:${Code}"
}

function Test-ExactArguments {
    param([string[]]$Actual, [string[]]$Expected)
    if ($Actual.Count -ne $Expected.Count) {
        return $false
    }
    for ($index = 0; $index -lt $Expected.Count; $index += 1) {
        if ($Actual[$index] -cne $Expected[$index]) {
            return $false
        }
    }
    return $true
}

function Invoke-VerifiedGit {
    param(
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [int]$TimeoutMilliseconds
    )
    $script:CapturedGitCalls += ,([pscustomobject]@{
        Arguments = @($Arguments)
        WorkingDirectory = $WorkingDirectory
        TimeoutMilliseconds = $TimeoutMilliseconds
    })
    $stdout = ""
    if (Test-ExactArguments $Arguments @("remote")) {
        $stdout = "origin`n"
    }
    elseif (
        Test-ExactArguments $Arguments @(
            "remote", "get-url", "--all", "origin"
        )
    ) {
        $stdout = "https://github.com/supabase/cli.git`n"
    }
    elseif (
        Test-ExactArguments $Arguments @(
            "cat-file", "-t", "refs/tags/v2.109.1"
        )
    ) {
        $stdout = "tag`n"
    }
    elseif (
        Test-ExactArguments $Arguments @(
            "rev-parse", "--verify", "refs/tags/v2.109.1"
        )
    ) {
        $stdout = "9d25ff8b5b0fba3c6f0ef000e7dd658c8d710c38`n"
    }
    elseif (
        Test-ExactArguments $Arguments @(
            "rev-parse", "--verify", "refs/tags/v2.109.1^{}"
        )
    ) {
        $stdout = "6d4c19870ed213ba7f682f117d0345c8a40bfa94`n"
    }
    elseif (
        Test-ExactArguments $Arguments @(
            "rev-parse", "--verify", "HEAD"
        )
    ) {
        $stdout = "6d4c19870ed213ba7f682f117d0345c8a40bfa94`n"
    }
    return [pscustomobject]@{
        ExitCode = 0
        Stdout = $stdout
        Stderr = ""
        TimedOut = $false
    }
}

$actualCheckout = New-VerifiedSupabaseCheckout $script:ExpectedDestination 134 248
$expectedCalls = @(
    [pscustomobject]@{
        Arguments = @("-c", "core.autocrlf=false", "init", "--quiet", ".")
        TimeoutMilliseconds = 30000
    },
    [pscustomobject]@{
        Arguments = @("config", "--local", "core.autocrlf", "false")
        TimeoutMilliseconds = 30000
    },
    [pscustomobject]@{
        Arguments = @("config", "--local", "core.longpaths", "true")
        TimeoutMilliseconds = 30000
    },
    [pscustomobject]@{
        Arguments = @(
            "remote", "add", "origin", "https://github.com/supabase/cli.git"
        )
        TimeoutMilliseconds = 30000
    },
    [pscustomobject]@{
        Arguments = @("remote")
        TimeoutMilliseconds = 30000
    },
    [pscustomobject]@{
        Arguments = @("remote", "get-url", "--all", "origin")
        TimeoutMilliseconds = 30000
    },
    [pscustomobject]@{
        Arguments = @(
            "fetch",
            "--quiet",
            "--depth=1",
            "--filter=blob:none",
            "origin",
            "refs/tags/v2.109.1:refs/tags/v2.109.1"
        )
        TimeoutMilliseconds = 300000
    },
    [pscustomobject]@{
        Arguments = @("cat-file", "-t", "refs/tags/v2.109.1")
        TimeoutMilliseconds = 30000
    },
    [pscustomobject]@{
        Arguments = @("rev-parse", "--verify", "refs/tags/v2.109.1")
        TimeoutMilliseconds = 30000
    },
    [pscustomobject]@{
        Arguments = @("rev-parse", "--verify", "refs/tags/v2.109.1^{}")
        TimeoutMilliseconds = 30000
    },
    [pscustomobject]@{
        Arguments = @(
            "checkout",
            "--quiet",
            "--detach",
            "6d4c19870ed213ba7f682f117d0345c8a40bfa94"
        )
        TimeoutMilliseconds = 120000
    },
    [pscustomobject]@{
        Arguments = @("rev-parse", "--verify", "HEAD")
        TimeoutMilliseconds = 30000
    }
)
$longPathCalls = @($script:CapturedGitCalls | Where-Object {
    Test-ExactArguments $_.Arguments @(
        "config", "--local", "core.longpaths", "true"
    )
})
if ($longPathCalls.Count -ne 1) {
    [Console]::Error.WriteLine(
        "expected-one-local-core.longpaths-before-fetch-and-checkout"
    )
    exit 1
}
if ($script:CapturedGitCalls.Count -ne $expectedCalls.Count) {
    [Console]::Error.WriteLine("unexpected-git-call-count")
    exit 1
}
for ($index = 0; $index -lt $expectedCalls.Count; $index += 1) {
    $actual = $script:CapturedGitCalls[$index]
    $expected = $expectedCalls[$index]
    if (
        -not (Test-ExactArguments $actual.Arguments $expected.Arguments) -or
        $actual.WorkingDirectory -cne $script:ExpectedCheckout -or
        $actual.TimeoutMilliseconds -ne $expected.TimeoutMilliseconds
    ) {
        [Console]::Error.WriteLine("unexpected-git-call-order-or-argv")
        exit 1
    }
    foreach ($argument in @($actual.Arguments)) {
        if (
            $argument -ceq "--global" -or
            $argument -ceq "--system" -or
            $argument -match "sparse-checkout|pathspec-from-file|:\(exclude\)"
        ) {
            [Console]::Error.WriteLine("forbidden-git-scope-or-path-exclusion")
            exit 1
        }
    }
}
if (
    -not $script:RemovedOwnedPath -or
    $script:BudgetCallCount -ne 1 -or
    $actualCheckout -cne $script:ExpectedCheckout -or
    -not (Test-Path -LiteralPath $script:ExpectedCheckout -PathType Container)
) {
    [Console]::Error.WriteLine("unexpected-checkout-path-state")
    exit 1
}
[Console]::Out.WriteLine("CHECKOUT-ARGV-OK")
""".lstrip(),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    powershell_executable(),
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(harness),
                    str(BOOTSTRAP_PATH),
                    str(root),
                ],
                cwd=root,
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.strip(), "CHECKOUT-ARGV-OK")
            self.assertFalse(result.stderr)

    def test_build_uses_exact_official_main_go_argv(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sejong build argv ") as directory:
            root = Path(directory)
            harness = root / "build_argv_harness.ps1"
            harness.write_text(
                r"""
param([string]$Bootstrap, [string]$Root)
$ErrorActionPreference = "Stop"
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $Bootstrap,
    [ref]$tokens,
    [ref]$errors
)
if ($errors.Count -ne 0) {
    exit 1
}
$wanted = @(
    "Throw-PatchedBootstrapFailure",
    "Resolve-SafeChildPath",
    "Remove-OwnedPath",
    "Build-PatchedSupabase"
)
foreach ($functionAst in @($ast.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $wanted -contains $node.Name
    },
    $true
))) {
    . ([ScriptBlock]::Create($functionAst.Extent.Text))
}
$script:ToolRoot = Join-Path $Root ".tools"
$script:GoExecutable = "approved-go.exe"
$script:CurrentStep = "TEST-BUILD-ARGV"
$checkout = Join-Path $Root "checkout"
$workingDirectory = Join-Path $checkout "apps/cli-go"
$null = New-Item -ItemType Directory -Path $workingDirectory -Force
$null = New-Item -ItemType Directory -Path $script:ToolRoot -Force
$script:CapturedFilePath = $null
$script:CapturedArguments = $null
$script:CapturedWorkingDirectory = $null
$script:CapturedTimeout = $null
function Invoke-PatchedChild {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [int]$TimeoutMilliseconds
    )
    $script:CapturedFilePath = $FilePath
    $script:CapturedArguments = @($Arguments)
    $script:CapturedWorkingDirectory = $WorkingDirectory
    $script:CapturedTimeout = $TimeoutMilliseconds
    return [pscustomobject]@{
        ExitCode = 0
        Stdout = ""
        Stderr = ""
        TimedOut = $false
    }
}
function Assert-PatchedChildSuccess {
    param([object]$Result, [string]$Step)
}
function Test-PatchedSupabaseVersion {
    param([string]$BinaryPath)
}
$relativeOutput = "supabase-build/candidate.exe"
$expectedOutput = [System.IO.Path]::GetFullPath(
    (Join-Path $script:ToolRoot $relativeOutput)
)
$null = Build-PatchedSupabase $checkout $relativeOutput
$expectedArguments = @(
    "build",
    "-trimpath",
    "-buildvcs=false",
    "-ldflags",
    "-s -w -X github.com/supabase/cli/internal/utils.Version=2.109.1",
    "-o",
    $expectedOutput,
    "main.go"
)
$matches = $script:CapturedArguments.Count -eq $expectedArguments.Count
if ($matches) {
    for ($index = 0; $index -lt $expectedArguments.Count; $index += 1) {
        if ($script:CapturedArguments[$index] -cne $expectedArguments[$index]) {
            $matches = $false
            break
        }
    }
}
if (
    -not $matches -or
    $script:CapturedFilePath -cne "approved-go.exe" -or
    $script:CapturedWorkingDirectory -cne $workingDirectory -or
    $script:CapturedTimeout -ne 900000
) {
    [Console]::Error.WriteLine(
        "unexpected-build-argv=" +
        ($script:CapturedArguments | ConvertTo-Json -Compress)
    )
    exit 1
}
[Console]::Out.WriteLine("BUILD-ARGV-OK")
""".lstrip(),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    powershell_executable(),
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(harness),
                    str(BOOTSTRAP_PATH),
                    str(root),
                ],
                cwd=root,
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.strip(), "BUILD-ARGV-OK")
            self.assertFalse(result.stderr)

    def test_version_probe_accepts_only_the_official_upgrade_advisory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sejong version advisory ") as directory:
            root = Path(directory)
            harness = root / "version_advisory_harness.ps1"
            harness.write_text(
                r"""
param([string]$Bootstrap, [string]$ProbeStderr)
$ErrorActionPreference = "Stop"
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $Bootstrap,
    [ref]$tokens,
    [ref]$errors
)
if ($errors.Count -ne 0) {
    exit 1
}
$wanted = @(
    "Throw-PatchedBootstrapFailure",
    "Test-PatchedSupabaseVersionStderr",
    "Test-PatchedSupabaseVersion"
)
foreach ($functionAst in @($ast.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $wanted -contains $node.Name
    },
    $true
))) {
    . ([ScriptBlock]::Create($functionAst.Extent.Text))
}
function Invoke-PatchedChild {
    return [pscustomobject]@{
        ExitCode = 0
        Stdout = "2.109.1`n"
        Stderr = $ProbeStderr
        TimedOut = $false
    }
}
$script:CurrentStep = "VERIFY-PATCHED-SUPABASE-BINARY"
$script:RepositoryRoot = (Get-Location).Path
$binary = Join-Path $script:RepositoryRoot "synthetic-supabase.exe"
[System.IO.File]::WriteAllBytes($binary, [byte[]]@(77, 90))
Test-PatchedSupabaseVersion $binary
[Console]::Out.WriteLine("VERSION-ADVISORY-OK")
""".lstrip(),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    powershell_executable(),
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(harness),
                    str(BOOTSTRAP_PATH),
                    (
                        "A new version of Supabase CLI is available: v2.110.0 "
                        "(currently installed v2.109.1)\n"
                        "We recommend updating regularly for new features and bug fixes: "
                        "https://supabase.com/docs/guides/cli/getting-started"
                        "#updating-the-supabase-cli\n"
                    ),
                ],
                cwd=root,
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.strip(), "VERSION-ADVISORY-OK")
            self.assertFalse(result.stderr)
            rejected = subprocess.run(
                [
                    powershell_executable(),
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(harness),
                    str(BOOTSTRAP_PATH),
                    "unexpected child diagnostic",
                ],
                cwd=root,
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertNotIn("VERSION-ADVISORY-OK", rejected.stdout)

    def test_install_rollback_preserves_backup_on_restore_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sejong rollback recovery ") as directory:
            root = Path(directory)
            harness = root / "rollback_recovery_harness.ps1"
            harness.write_text(
                r"""
param([string]$Bootstrap, [string]$Root)
$ErrorActionPreference = "Stop"
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $Bootstrap,
    [ref]$tokens,
    [ref]$errors
)
if ($errors.Count -ne 0) {
    exit 1
}
$wanted = @(
    "Throw-PatchedBootstrapFailure",
    "Resolve-SafeChildPath",
    "Remove-OwnedPath",
    "Get-PatchedSha256",
    "Install-PatchedSupabaseBinary"
)
foreach ($functionAst in @($ast.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $wanted -contains $node.Name
    },
    $true
))) {
    . ([ScriptBlock]::Create($functionAst.Extent.Text))
}
$script:RepositoryRoot = [System.IO.Path]::GetFullPath($Root)
$script:ToolRoot = Join-Path $script:RepositoryRoot ".tools"
$script:CurrentStep = "INSTALL-PATCHED-SUPABASE"
$candidate = Join-Path $script:ToolRoot "supabase-build/candidate.exe"
$relativeFinal = ".tools/supabase/v2.109.1-sejong-loopback/supabase.exe"
$final = Join-Path $script:RepositoryRoot $relativeFinal
$null = New-Item -ItemType Directory -Path (Split-Path -Parent $candidate) -Force
$null = New-Item -ItemType Directory -Path (Split-Path -Parent $final) -Force
$knownGood = [System.Text.Encoding]::UTF8.GetBytes("known-good-stock-binary")
$candidateBytes = [System.Text.Encoding]::UTF8.GetBytes("invalid-new-candidate")
[System.IO.File]::WriteAllBytes($final, $knownGood)
[System.IO.File]::WriteAllBytes($candidate, $candidateBytes)
$runtimeManifest = [pscustomobject]@{
    relative_path = $relativeFinal
    sha256 = (Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash.ToLowerInvariant()
}
$script:ReplaceCalls = 0
$script:RestoreCalls = 0
function Replace-PatchedFileWithBackup {
    param(
        [string]$Source,
        [string]$Destination,
        [string]$Backup
    )
    $script:ReplaceCalls += 1
    [System.IO.File]::Replace($Source, $Destination, $Backup, $true)
}
function Restore-PatchedFileFromBackup {
    param([string]$Backup, [string]$Destination)
    $script:RestoreCalls += 1
    throw (New-Object System.InvalidOperationException("forced restore failure"))
}
function Assert-InstalledPatchedBinary {
    param([object]$RuntimeManifest)
    Throw-PatchedBootstrapFailure "VERIFY-POST-REPLACEMENT" "integrity" 1
}
$failureLine = $null
try {
    Install-PatchedSupabaseBinary $candidate $runtimeManifest
    [Console]::Error.WriteLine("install-unexpectedly-succeeded")
    exit 1
}
catch {
    $failure = $_.Exception
    if (
        -not $failure.Data.Contains("PatchedBootstrapFailure") -or
        -not [bool]$failure.Data["PatchedBootstrapFailure"]
    ) {
        [Console]::Error.WriteLine("uncontrolled-install-failure")
        exit 1
    }
    $failureLine = "[FAIL] step=$($failure.Data['Step']) " +
        "reason=$($failure.Data['Reason']) code=$($failure.Data['Code'])"
}
$backup = Join-Path $script:ToolRoot (
    "supabase/.v2.109.1-sejong-loopback-$PID.backup"
)
if ($failureLine -cne "[FAIL] step=INSTALL-PATCHED-SUPABASE reason=operational code=2") {
    [Console]::Error.WriteLine("unexpected-failure-line=$failureLine")
    exit 1
}
if ($script:ReplaceCalls -ne 1 -or $script:RestoreCalls -ne 1) {
    [Console]::Error.WriteLine(
        "unexpected-call-count replace=$($script:ReplaceCalls) " +
        "restore=$($script:RestoreCalls)"
    )
    exit 1
}
if (-not (Test-Path -LiteralPath $backup -PathType Leaf)) {
    [Console]::Error.WriteLine("known-good-backup-missing")
    exit 1
}
if (
    [System.Text.Encoding]::UTF8.GetString(
        [System.IO.File]::ReadAllBytes($backup)
    ) -cne "known-good-stock-binary"
) {
    [Console]::Error.WriteLine("known-good-backup-corrupt")
    exit 1
}
if (
    [System.Text.Encoding]::UTF8.GetString(
        [System.IO.File]::ReadAllBytes($final)
    ) -cne "invalid-new-candidate"
) {
    [Console]::Error.WriteLine("post-replacement-state-not-observed")
    exit 1
}
[Console]::Out.WriteLine($failureLine)
[Console]::Out.WriteLine("KNOWN-GOOD-BACKUP-RETAINED")
""".lstrip(),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    powershell_executable(),
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(harness),
                    str(BOOTSTRAP_PATH),
                    str(root),
                ],
                cwd=root,
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(
                result.stdout.strip(),
                "[FAIL] step=INSTALL-PATCHED-SUPABASE reason=operational code=2\n"
                "KNOWN-GOOD-BACKUP-RETAINED",
            )
            self.assertFalse(result.stderr)

    def test_child_timeout_starts_suspended_before_job_assignment(self) -> None:
        script = BOOTSTRAP_PATH.read_text(encoding="utf-8")
        for token in (
            "CreateJobObject",
            "SetInformationJobObject",
            "CreateProcess",
            "CREATE_SUSPENDED",
            "AssignProcessToJobObject",
            "ResumeThread",
            "TerminateJobObject",
            "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE",
            "Task.WaitAll",
        ):
            self.assertIn(token, script)
        self.assertLess(
            script.index("AssignProcessToJobObject(job, processInformation.Process)"),
            script.index("ResumeThread(processInformation.Thread)"),
        )

    def test_child_timeout_terminates_spawned_descendant(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sejong child tree ") as directory:
            root = Path(directory)
            harness = root / "job_harness.ps1"
            parent_script = root / "spawn_parent.ps1"
            pid_file = root / "descendant.pid"
            parent_script.write_text(
                r"""
param([string]$PidFile)
$ErrorActionPreference = "Stop"
$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $env:ComSpec
$startInfo.Arguments = "/d /c ping -n 31 127.0.0.1 >NUL"
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $true
$child = [System.Diagnostics.Process]::Start($startInfo)
$child.Id | Set-Content -LiteralPath $PidFile
Start-Sleep -Seconds 30
""".lstrip(),
                encoding="utf-8",
            )
            harness.write_text(
                r"""
param(
    [string]$Bootstrap,
    [string]$PowerShell,
    [string]$ParentScript,
    [string]$PidFile
)
$ErrorActionPreference = "Stop"
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $Bootstrap,
    [ref]$tokens,
    [ref]$errors
)
if ($errors.Count -ne 0) {
    exit 1
}
$wanted = @(
    "Throw-PatchedBootstrapFailure",
    "ConvertTo-PatchedProcessArgument",
    "Initialize-PatchedJobSupport",
    "Invoke-PatchedChild"
)
foreach ($functionAst in @($ast.FindAll(
    {
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $wanted -contains $node.Name
    },
    $true
))) {
    . ([ScriptBlock]::Create($functionAst.Extent.Text))
}
$script:CurrentStep = "TEST-CHILD-TREE"
$probe = Invoke-PatchedChild $PowerShell @(
    "-NoProfile",
    "-Command",
    "[Console]::Out.WriteLine('child-probe-ok')"
) (Get-Location).Path 5000
if (
    $probe.TimedOut -or
    $probe.ExitCode -ne 0 -or
    $probe.Stdout.Trim() -cne "child-probe-ok"
) {
    [Console]::Error.WriteLine(
        "probe-failed timed_out=$($probe.TimedOut) exit_code=$($probe.ExitCode) " +
        "stdout=$($probe.Stdout) stderr=$($probe.Stderr)"
    )
    exit 1
}
$result = Invoke-PatchedChild $PowerShell @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $ParentScript,
    $PidFile
) (Get-Location).Path 10000
if (-not $result.TimedOut -or $result.ExitCode -ne -1) {
    [Console]::Error.WriteLine(
        "unexpected-result timed_out=$($result.TimedOut) exit_code=$($result.ExitCode)"
    )
    exit 1
}
if (-not (Test-Path -LiteralPath $PidFile -PathType Leaf)) {
    [Console]::Error.WriteLine(
        "descendant-pid-missing stdout=$($result.Stdout) stderr=$($result.Stderr)"
    )
    exit 1
}
$descendantPid = [int](Get-Content -LiteralPath $PidFile -Raw)
for ($attempt = 0; $attempt -lt 20; $attempt += 1) {
    if ($null -eq (Get-Process -Id $descendantPid -ErrorAction SilentlyContinue)) {
        [Console]::Out.WriteLine("DESCENDANT-TIMEOUT-OK")
        exit 0
    }
    Start-Sleep -Milliseconds 100
}
[Console]::Error.WriteLine("descendant-still-running pid=$descendantPid")
exit 1
""".lstrip(),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    powershell_executable(),
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(harness),
                    str(BOOTSTRAP_PATH),
                    powershell_executable(),
                    str(parent_script),
                    str(pid_file),
                ],
                cwd=root,
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                timeout=45,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.strip(), "DESCENDANT-TIMEOUT-OK")
            self.assertFalse(result.stderr)

    def test_unapproved_go_build_environment_fails_before_network(self) -> None:
        poisoned = {
            "gonoproxy": "example.invalid",
            "goinsecure": "example.invalid",
            "goenv": "C:/unapproved/go.env",
            "gowork": "C:/unapproved/go.work",
            "gotoolchain": "auto",
            "goflags": "-mod=mod",
            "goamd64": "v3",
            "goexperiment": "arenas",
        }
        for key, value in poisoned.items():
            with self.subTest(key=key):
                with run_patched_fixture(
                    "-BuildCandidate",
                    mutate_source=lambda source, key=key, value=value: source[
                        "build"
                    ].update({key: value}),
                    include_runtime=False,
                ) as (result, root):
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(
                        result.stdout.strip(),
                        "[FAIL] step=VALIDATE-PATCHED-SUPABASE-SOURCE-MANIFEST reason=unapproved-source code=2",
                    )
                    self.assertFalse(result.stderr)
                    self.assertFalse((root / ".tools").exists())


class PatchedRuntimeLockTests(unittest.TestCase):
    def test_runtime_manifest_and_installed_binary_are_exact(self) -> None:
        runtime = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
        source_hash = hashlib.sha256(SOURCE_MANIFEST.read_bytes()).hexdigest()
        self.assertEqual(
            set(runtime),
            {
                "schema_version",
                "source_manifest_sha256",
                "version",
                "platform",
                "relative_path",
                "sha256",
            },
        )
        self.assertEqual(runtime["schema_version"], 1)
        self.assertEqual(runtime["source_manifest_sha256"], source_hash)
        self.assertEqual(runtime["version"], "2.109.1")
        self.assertEqual(runtime["platform"], "windows-amd64")
        self.assertEqual(
            runtime["relative_path"],
            ".tools/supabase/v2.109.1-sejong-loopback/supabase.exe",
        )
        self.assertRegex(runtime["sha256"], r"^[0-9a-f]{64}$")
        binary = ROOT / Path(runtime["relative_path"])
        self.assertTrue(binary.is_file())
        self.assertEqual(hashlib.sha256(binary.read_bytes()).hexdigest(), runtime["sha256"])


if __name__ == "__main__":
    unittest.main()
