Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$TimeoutSeconds = 3600
$PollSeconds = 1
$ResultRelativePath = ".superpowers\sdd\2026-07-29-deepseek-classifier-provider\a074-offline-gate-result.json"
$LockRelativePath = ".superpowers\sdd\2026-07-29-deepseek-classifier-provider\a074-offline-gate-result.json.run.lock"
$StdoutRelativePath = ".superpowers\sdd\2026-07-29-deepseek-classifier-provider\a074-offline-gate.stdout.log"
$StderrRelativePath = ".superpowers\sdd\2026-07-29-deepseek-classifier-provider\a074-offline-gate.stderr.log"
$LeaseText = "A-074-OFFLINE-GATE one-shot lease`n"

function Write-NewFsyncedFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LiteralPath,
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    $encoding = New-Object System.Text.UTF8Encoding($false)
    $bytes = $encoding.GetBytes($Text)
    $stream = New-Object System.IO.FileStream(
        $LiteralPath,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    try {
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
    }
    finally {
        $stream.Dispose()
    }
}

function New-EmptyFsyncedFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LiteralPath
    )

    $stream = New-Object System.IO.FileStream(
        $LiteralPath,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    try {
        $stream.Flush($true)
    }
    finally {
        $stream.Dispose()
    }
}

function Get-Sha256Lower {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LiteralPath
    )

    return (Get-FileHash -LiteralPath $LiteralPath -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Stop-ProcessTreeAndWait {
    param(
        [Parameter(Mandatory = $true)]
        [System.Diagnostics.Process]$Process
    )

    $taskkill = Join-Path $env:SystemRoot "System32\taskkill.exe"
    if (-not (Test-Path -LiteralPath $taskkill -PathType Leaf)) {
        throw "PROCESS_TREE_KILLER_UNAVAILABLE"
    }
    $killArguments = @(
        "/PID",
        $Process.Id.ToString([System.Globalization.CultureInfo]::InvariantCulture),
        "/T",
        "/F"
    )
    $killer = Start-Process `
        -FilePath $taskkill `
        -ArgumentList $killArguments `
        -PassThru `
        -Wait `
        -WindowStyle Hidden
    if ($killer.ExitCode -ne 0) {
        throw "PROCESS_TREE_KILL_FAILED"
    }
    $Process.WaitForExit()
    if (-not $Process.HasExited) {
        throw "PROCESS_TREE_TERMINATION_UNCONFIRMED"
    }
}

function Assert-OriginalSourceIdentityAndClean {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepositoryRoot,
        [Parameter(Mandatory = $true)]
        [string]$OriginalSourceSha
    )

    $currentShaOutput = @(
        & git -C $RepositoryRoot rev-parse HEAD 2>$null
    )
    if (
        $LASTEXITCODE -ne 0 -or
        $currentShaOutput.Count -ne 1 -or
        $currentShaOutput[0].Trim() -cne $OriginalSourceSha
    ) {
        throw "SOURCE_SHA_DRIFTED"
    }
    $currentStatusOutput = @(
        & git -C $RepositoryRoot status --porcelain=v1 --untracked-files=all 2>$null
    )
    if ($LASTEXITCODE -ne 0 -or $currentStatusOutput.Count -ne 0) {
        throw "SOURCE_NOT_CLEAN"
    }
}

try {
    if (
        $PSVersionTable.PSVersion.Major -ne 5 -or
        $PSVersionTable.PSVersion.Minor -lt 1
    ) {
        throw "POWERSHELL_VERSION_INVALID"
    }

    $repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
    $verifyScript = Join-Path $repoRoot "scripts\verify.ps1"
    $resultPath = Join-Path $repoRoot $ResultRelativePath
    $lockPath = Join-Path $repoRoot $LockRelativePath
    $stdoutPath = Join-Path $repoRoot $StdoutRelativePath
    $stderrPath = Join-Path $repoRoot $StderrRelativePath
    $artifactPaths = @($resultPath, $lockPath, $stdoutPath, $stderrPath)

    if (-not (Test-Path -LiteralPath $verifyScript -PathType Leaf)) {
        throw "VERIFY_SCRIPT_MISSING"
    }
    foreach ($artifactPath in $artifactPaths) {
        if (Test-Path -LiteralPath $artifactPath) {
            throw "OFFLINE_ARTIFACT_ALREADY_EXISTS"
        }
    }

    $sourceShaOutput = @(
        & git -C $repoRoot rev-parse HEAD 2>$null
    )
    if ($LASTEXITCODE -ne 0 -or $sourceShaOutput.Count -ne 1) {
        throw "SOURCE_SHA_UNAVAILABLE"
    }
    $sourceSha = $sourceShaOutput[0].Trim()
    if ($sourceSha -cnotmatch "^[0-9a-f]{40}$") {
        throw "SOURCE_SHA_INVALID"
    }

    $statusOutput = @(
        & git -C $repoRoot status --porcelain=v1 --untracked-files=all 2>$null
    )
    if ($LASTEXITCODE -ne 0 -or $statusOutput.Count -ne 0) {
        throw "SOURCE_NOT_CLEAN"
    }
}
catch {
    [Console]::Error.WriteLine("A074_OFFLINE_GATE_PREFLIGHT_FAILED")
    exit 2
}

$exitCode = 125
$timedOut = $false
$outcome = "FAIL"
$postLeaseFailure = $false
$leaseAcquired = $false
$process = $null
$processTerminationConfirmed = $true
$processTerminationAttempted = $false

try {
    $artifactDirectory = Split-Path -Parent $resultPath
    [System.IO.Directory]::CreateDirectory($artifactDirectory) | Out-Null
    Write-NewFsyncedFile -LiteralPath $lockPath -Text $LeaseText
    $leaseAcquired = $true
    New-EmptyFsyncedFile -LiteralPath $stdoutPath
    New-EmptyFsyncedFile -LiteralPath $stderrPath

    $quotedVerifyScript = '"' + $verifyScript.Replace('"', '\"') + '"'
    $verifyArguments = @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $quotedVerifyScript,
        "-Offline"
    )
    $processTerminationConfirmed = $false
    $process = Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList $verifyArguments `
        -WorkingDirectory $repoRoot `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath `
        -PassThru `
        -WindowStyle Hidden
    # Windows PowerShell 5.1 must cache the process handle before a fast child exits,
    # otherwise ExitCode can become unavailable after polling.
    $processHandle = $process.Handle

    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    $finished = $false
    while (-not $finished) {
        if ($stopwatch.Elapsed.TotalSeconds -ge $TimeoutSeconds) {
            $timedOut = $true
            break
        }
        $finished = $process.WaitForExit([int]($PollSeconds * 1000))
    }
    if ($timedOut) {
        $processTerminationAttempted = $true
        Stop-ProcessTreeAndWait -Process $process
        if (-not $process.HasExited) {
            throw "PROCESS_TREE_TERMINATION_UNCONFIRMED"
        }
        $processTerminationConfirmed = $true
        $exitCode = 124
    }
    else {
        $process.WaitForExit()
        if (-not $process.HasExited) {
            throw "PROCESS_EXIT_UNCONFIRMED"
        }
        $processTerminationConfirmed = $true
        $exitCode = [int]$process.ExitCode
    }
    Assert-OriginalSourceIdentityAndClean `
        -RepositoryRoot $repoRoot `
        -OriginalSourceSha $sourceSha
    if (-not $timedOut -and $exitCode -eq 0) {
        $outcome = "PASS"
    }
}
catch {
    $postLeaseFailure = $true
    $exitCode = 125
    $outcome = "FAIL"
    if (-not $leaseAcquired) {
        [Console]::Error.WriteLine("A074_OFFLINE_GATE_LEASE_FAILED")
        exit 125
    }
    if (-not $processTerminationConfirmed -and $null -ne $process) {
        try {
            if (-not $processTerminationAttempted -and $process.HasExited) {
                $process.WaitForExit()
                $processTerminationConfirmed = $true
            }
            elseif (-not $processTerminationAttempted) {
                $processTerminationAttempted = $true
                Stop-ProcessTreeAndWait -Process $process
                if ($process.HasExited) {
                    $processTerminationConfirmed = $true
                }
            }
        }
        catch {
            $processTerminationConfirmed = $false
        }
    }
    if (-not $processTerminationConfirmed) {
        [Console]::Error.WriteLine(
            "A074_OFFLINE_GATE_PROCESS_TERMINATION_UNCONFIRMED"
        )
        exit 125
    }
}

try {
    if (-not (Test-Path -LiteralPath $lockPath -PathType Leaf)) {
        throw "PERMANENT_LEASE_MISSING"
    }
    if (-not (Test-Path -LiteralPath $stdoutPath -PathType Leaf)) {
        New-EmptyFsyncedFile -LiteralPath $stdoutPath
    }
    if (-not (Test-Path -LiteralPath $stderrPath -PathType Leaf)) {
        New-EmptyFsyncedFile -LiteralPath $stderrPath
    }
    try {
        Assert-OriginalSourceIdentityAndClean `
            -RepositoryRoot $repoRoot `
            -OriginalSourceSha $sourceSha
    }
    catch {
        $postLeaseFailure = $true
        $exitCode = 125
        $outcome = "FAIL"
    }

    $stdoutItem = Get-Item -LiteralPath $stdoutPath
    $stderrItem = Get-Item -LiteralPath $stderrPath
    $result = [ordered]@{
        schema_version = 1
        gate = "A-074-OFFLINE"
        source_sha = $sourceSha
        outcome = $outcome
        exit_code = [int]$exitCode
        timed_out = [bool]$timedOut
        invocation_count = 1
        rerun_count = 0
        stdout_sha256 = Get-Sha256Lower -LiteralPath $stdoutPath
        stdout_bytes = [long]$stdoutItem.Length
        stderr_sha256 = Get-Sha256Lower -LiteralPath $stderrPath
        stderr_bytes = [long]$stderrItem.Length
    }
    $resultJson = ($result | ConvertTo-Json -Compress) + "`n"
    Write-NewFsyncedFile -LiteralPath $resultPath -Text $resultJson
}
catch {
    [Console]::Error.WriteLine("A074_OFFLINE_GATE_EVIDENCE_WRITE_FAILED")
    exit 125
}

if ($outcome -eq "PASS") {
    [Console]::Out.WriteLine("A074_OFFLINE_GATE_PASS")
    exit 0
}

[Console]::Out.WriteLine("A074_OFFLINE_GATE_FAIL")
if ($postLeaseFailure -and $exitCode -eq 0) {
    exit 125
}
exit $exitCode
