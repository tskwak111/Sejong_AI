Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Throw-DatabaseGateFailure {
    param(
        [string]$Step,
        [string]$Reason,
        [int]$Code
    )

    $failure = New-Object System.Exception("controlled database gate failure")
    $failure.Data["step"] = $Step
    $failure.Data["reason"] = $Reason
    $failure.Data["code"] = $Code
    throw $failure
}

function ConvertTo-NativeArgument {
    param([string]$Value)

    if ($Value.Length -gt 0 -and $Value -notmatch '[\s"]') {
        return $Value
    }

    $builder = New-Object System.Text.StringBuilder
    $null = $builder.Append('"')
    $backslashCount = 0
    foreach ($character in $Value.ToCharArray()) {
        if ($character -eq '\') {
            $backslashCount += 1
            continue
        }
        if ($character -eq '"') {
            $null = $builder.Append(('\' * (($backslashCount * 2) + 1)))
            $null = $builder.Append('"')
            $backslashCount = 0
            continue
        }
        if ($backslashCount -gt 0) {
            $null = $builder.Append(('\' * $backslashCount))
            $backslashCount = 0
        }
        $null = $builder.Append($character)
    }
    if ($backslashCount -gt 0) {
        $null = $builder.Append(('\' * ($backslashCount * 2)))
    }
    $null = $builder.Append('"')
    return $builder.ToString()
}

function Initialize-DatabaseJobSupport {
    if ($null -ne ("SejongDatabaseRunner.NativeJob" -as [type])) {
        return
    }

    $jobSource = @"
using System;
using System.ComponentModel;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;
using Microsoft.Win32.SafeHandles;

namespace SejongDatabaseRunner
{
    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_BASIC_LIMIT_INFORMATION
    {
        public long PerProcessUserTimeLimit;
        public long PerJobUserTimeLimit;
        public uint LimitFlags;
        public UIntPtr MinimumWorkingSetSize;
        public UIntPtr MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint PriorityClass;
        public uint SchedulingClass;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct IO_COUNTERS
    {
        public ulong ReadOperationCount;
        public ulong WriteOperationCount;
        public ulong OtherOperationCount;
        public ulong ReadTransferCount;
        public ulong WriteTransferCount;
        public ulong OtherTransferCount;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION
    {
        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
        public IO_COUNTERS IoInfo;
        public UIntPtr ProcessMemoryLimit;
        public UIntPtr JobMemoryLimit;
        public UIntPtr PeakProcessMemoryUsed;
        public UIntPtr PeakJobMemoryUsed;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct SECURITY_ATTRIBUTES
    {
        public int Length;
        public IntPtr SecurityDescriptor;
        [MarshalAs(UnmanagedType.Bool)]
        public bool InheritHandle;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct STARTUPINFO
    {
        public int Cb;
        public string Reserved;
        public string Desktop;
        public string Title;
        public uint X;
        public uint Y;
        public uint XSize;
        public uint YSize;
        public uint XCountChars;
        public uint YCountChars;
        public uint FillAttribute;
        public uint Flags;
        public ushort ShowWindow;
        public ushort Reserved2Length;
        public IntPtr Reserved2;
        public IntPtr StdInput;
        public IntPtr StdOutput;
        public IntPtr StdError;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct PROCESS_INFORMATION
    {
        public IntPtr Process;
        public IntPtr Thread;
        public uint ProcessId;
        public uint ThreadId;
    }

    public sealed class ChildResult
    {
        public int ExitCode { get; set; }
        public string Stdout { get; set; }
        public string Stderr { get; set; }
        public bool TimedOut { get; set; }
    }

    public static class NativeJob
    {
        public const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;
        private const int JobObjectExtendedLimitInformation = 9;
        private const uint CREATE_SUSPENDED = 0x00000004;
        private const uint CREATE_NO_WINDOW = 0x08000000;
        private const uint STARTF_USESTDHANDLES = 0x00000100;
        private const uint HANDLE_FLAG_INHERIT = 0x00000001;
        private const uint WAIT_TIMEOUT = 0x00000102;
        private const uint WAIT_FAILED = 0xFFFFFFFF;
        private const int STD_INPUT_HANDLE = -10;

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr CreateJobObject(IntPtr securityAttributes, string name);

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool SetInformationJobObject(
            IntPtr job,
            int informationClass,
            ref JOBOBJECT_EXTENDED_LIMIT_INFORMATION information,
            uint informationLength
        );

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool TerminateJobObject(IntPtr job, uint exitCode);

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool CreatePipe(
            out IntPtr readPipe,
            out IntPtr writePipe,
            ref SECURITY_ATTRIBUTES pipeAttributes,
            uint size
        );

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool SetHandleInformation(
            IntPtr handle,
            uint mask,
            uint flags
        );

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool CreateProcess(
            string applicationName,
            StringBuilder commandLine,
            IntPtr processAttributes,
            IntPtr threadAttributes,
            [MarshalAs(UnmanagedType.Bool)] bool inheritHandles,
            uint creationFlags,
            IntPtr environment,
            string currentDirectory,
            ref STARTUPINFO startupInfo,
            out PROCESS_INFORMATION processInformation
        );

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern uint ResumeThread(IntPtr thread);

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool TerminateProcess(IntPtr process, uint exitCode);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool GetExitCodeProcess(IntPtr process, out uint exitCode);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern IntPtr GetStdHandle(int standardHandle);

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool CloseHandle(IntPtr handle);

        private static IntPtr CreateKillOnCloseJob()
        {
            IntPtr job = CreateJobObject(IntPtr.Zero, null);
            if (job == IntPtr.Zero)
            {
                throw new Win32Exception(Marshal.GetLastWin32Error());
            }
            JOBOBJECT_EXTENDED_LIMIT_INFORMATION information =
                new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
            information.BasicLimitInformation.LimitFlags =
                JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            uint length = (uint)Marshal.SizeOf(
                typeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION)
            );
            if (!SetInformationJobObject(
                job,
                JobObjectExtendedLimitInformation,
                ref information,
                length
            ))
            {
                int error = Marshal.GetLastWin32Error();
                CloseHandle(job);
                throw new Win32Exception(error);
            }
            return job;
        }

        private static bool WaitForOutput(Task[] tasks, int milliseconds)
        {
            try
            {
                return Task.WaitAll(tasks, milliseconds);
            }
            catch
            {
                return false;
            }
        }

        public static ChildResult Run(
            string applicationName,
            string commandLine,
            string workingDirectory,
            int timeoutMilliseconds
        )
        {
            IntPtr job = IntPtr.Zero;
            IntPtr stdoutRead = IntPtr.Zero;
            IntPtr stdoutWrite = IntPtr.Zero;
            IntPtr stderrRead = IntPtr.Zero;
            IntPtr stderrWrite = IntPtr.Zero;
            PROCESS_INFORMATION processInformation = new PROCESS_INFORMATION();
            StreamReader stdoutReader = null;
            StreamReader stderrReader = null;
            try
            {
                job = CreateKillOnCloseJob();
                SECURITY_ATTRIBUTES pipeAttributes = new SECURITY_ATTRIBUTES();
                pipeAttributes.Length = Marshal.SizeOf(typeof(SECURITY_ATTRIBUTES));
                pipeAttributes.InheritHandle = true;
                if (!CreatePipe(
                    out stdoutRead,
                    out stdoutWrite,
                    ref pipeAttributes,
                    0
                ) || !SetHandleInformation(stdoutRead, HANDLE_FLAG_INHERIT, 0))
                {
                    throw new Win32Exception(Marshal.GetLastWin32Error());
                }
                if (!CreatePipe(
                    out stderrRead,
                    out stderrWrite,
                    ref pipeAttributes,
                    0
                ) || !SetHandleInformation(stderrRead, HANDLE_FLAG_INHERIT, 0))
                {
                    throw new Win32Exception(Marshal.GetLastWin32Error());
                }

                STARTUPINFO startupInfo = new STARTUPINFO();
                startupInfo.Cb = Marshal.SizeOf(typeof(STARTUPINFO));
                startupInfo.Flags = STARTF_USESTDHANDLES;
                startupInfo.StdInput = GetStdHandle(STD_INPUT_HANDLE);
                startupInfo.StdOutput = stdoutWrite;
                startupInfo.StdError = stderrWrite;
                StringBuilder mutableCommandLine = new StringBuilder(commandLine);
                if (!CreateProcess(
                    applicationName,
                    mutableCommandLine,
                    IntPtr.Zero,
                    IntPtr.Zero,
                    true,
                    CREATE_SUSPENDED | CREATE_NO_WINDOW,
                    IntPtr.Zero,
                    workingDirectory,
                    ref startupInfo,
                    out processInformation
                ))
                {
                    throw new Win32Exception(Marshal.GetLastWin32Error());
                }

                if (!AssignProcessToJobObject(job, processInformation.Process))
                {
                    int error = Marshal.GetLastWin32Error();
                    TerminateProcess(processInformation.Process, 1);
                    throw new Win32Exception(error);
                }
                if (ResumeThread(processInformation.Thread) == WAIT_FAILED)
                {
                    int error = Marshal.GetLastWin32Error();
                    TerminateJobObject(job, 1);
                    throw new Win32Exception(error);
                }
                CloseHandle(processInformation.Thread);
                processInformation.Thread = IntPtr.Zero;
                CloseHandle(stdoutWrite);
                stdoutWrite = IntPtr.Zero;
                CloseHandle(stderrWrite);
                stderrWrite = IntPtr.Zero;

                SafeFileHandle stdoutHandle = new SafeFileHandle(stdoutRead, true);
                stdoutRead = IntPtr.Zero;
                SafeFileHandle stderrHandle = new SafeFileHandle(stderrRead, true);
                stderrRead = IntPtr.Zero;
                FileStream stdoutStream = new FileStream(
                    stdoutHandle,
                    FileAccess.Read,
                    4096,
                    false
                );
                FileStream stderrStream = new FileStream(
                    stderrHandle,
                    FileAccess.Read,
                    4096,
                    false
                );
                stdoutReader = new StreamReader(
                    stdoutStream,
                    new UTF8Encoding(false, false),
                    true,
                    4096
                );
                stderrReader = new StreamReader(
                    stderrStream,
                    new UTF8Encoding(false, false),
                    true,
                    4096
                );
                Task<string> stdoutTask = stdoutReader.ReadToEndAsync();
                Task<string> stderrTask = stderrReader.ReadToEndAsync();
                Task[] outputTasks = new Task[] { stdoutTask, stderrTask };

                uint waitResult = WaitForSingleObject(
                    processInformation.Process,
                    (uint)timeoutMilliseconds
                );
                bool timedOut = waitResult == WAIT_TIMEOUT;
                if (waitResult == WAIT_FAILED)
                {
                    throw new Win32Exception(Marshal.GetLastWin32Error());
                }
                if (timedOut)
                {
                    if (!TerminateJobObject(job, 1))
                    {
                        throw new Win32Exception(Marshal.GetLastWin32Error());
                    }
                    WaitForSingleObject(processInformation.Process, 5000);
                }

                bool outputDrained = WaitForOutput(outputTasks, 5000);
                if (!outputDrained)
                {
                    TerminateJobObject(job, 1);
                    WaitForSingleObject(processInformation.Process, 5000);
                    outputDrained = WaitForOutput(outputTasks, 5000);
                    timedOut = true;
                }
                if (!outputDrained)
                {
                    return new ChildResult {
                        ExitCode = -1,
                        Stdout = "",
                        Stderr = "",
                        TimedOut = true
                    };
                }

                if (timedOut)
                {
                    return new ChildResult {
                        ExitCode = -1,
                        Stdout = stdoutTask.Result,
                        Stderr = stderrTask.Result,
                        TimedOut = true
                    };
                }
                uint exitCode;
                if (!GetExitCodeProcess(processInformation.Process, out exitCode))
                {
                    throw new Win32Exception(Marshal.GetLastWin32Error());
                }
                return new ChildResult {
                    ExitCode = unchecked((int)exitCode),
                    Stdout = stdoutTask.Result,
                    Stderr = stderrTask.Result,
                    TimedOut = false
                };
            }
            finally
            {
                if (stdoutReader != null) stdoutReader.Dispose();
                if (stderrReader != null) stderrReader.Dispose();
                if (stdoutRead != IntPtr.Zero) CloseHandle(stdoutRead);
                if (stdoutWrite != IntPtr.Zero) CloseHandle(stdoutWrite);
                if (stderrRead != IntPtr.Zero) CloseHandle(stderrRead);
                if (stderrWrite != IntPtr.Zero) CloseHandle(stderrWrite);
                if (processInformation.Thread != IntPtr.Zero)
                    CloseHandle(processInformation.Thread);
                if (processInformation.Process != IntPtr.Zero)
                    CloseHandle(processInformation.Process);
                if (job != IntPtr.Zero) CloseHandle(job);
            }
        }
    }
}
"@
    $null = Add-Type -TypeDefinition $jobSource -Language CSharp -PassThru
}

function Invoke-DatabaseChild {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [int]$TimeoutMilliseconds = 900000
    )

    if ($TimeoutMilliseconds -le 0) {
        Throw-DatabaseGateFailure -Step "DATABASE-CHILD" -Reason "operational" -Code 2
    }

    Initialize-DatabaseJobSupport
    $quotedArguments = New-Object System.Collections.Generic.List[string]
    foreach ($argument in @($Arguments)) {
        $quotedArguments.Add((ConvertTo-NativeArgument -Value ([string]$argument)))
    }
    $commandLine = ConvertTo-NativeArgument -Value $FilePath
    if ($quotedArguments.Count -gt 0) {
        $commandLine += " " + ($quotedArguments -join " ")
    }
    $result = [SejongDatabaseRunner.NativeJob]::Run(
        $FilePath,
        $commandLine,
        $WorkingDirectory,
        $TimeoutMilliseconds
    )
    if ($result.TimedOut) {
        Throw-DatabaseGateFailure -Step "DATABASE-CHILD" -Reason "timeout" -Code 2
    }
    return [pscustomobject]@{
        ExitCode = [int]$result.ExitCode
        Output = [string]$result.Stdout
    }
}

function Invoke-DatabaseStep {
    param(
        [string]$Step,
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [int]$TimeoutMilliseconds = 900000
    )

    [Console]::Out.WriteLine("[START] step=" + $Step)
    try {
        $result = Invoke-DatabaseChild `
            -FilePath $FilePath `
            -Arguments $Arguments `
            -WorkingDirectory $WorkingDirectory `
            -TimeoutMilliseconds $TimeoutMilliseconds
    }
    catch {
        if ($_.Exception.Data.Contains("step")) {
            throw
        }
        Throw-DatabaseGateFailure -Step $Step -Reason "operational" -Code 2
    }
    if ($result.ExitCode -ne 0) {
        Throw-DatabaseGateFailure -Step $Step -Reason "child" -Code $result.ExitCode
    }
    [Console]::Out.WriteLine("[PASS] step=" + $Step)
    return $result
}

function Read-DatabaseUrlFromStatus {
    param([string]$StatusOutput)

    foreach ($line in ($StatusOutput -split "`r?`n")) {
        if ($line.StartsWith("DB_URL=", [System.StringComparison]::Ordinal)) {
            $value = $line.Substring(7).Trim()
            if (
                $value.Length -ge 2 -and
                $value.StartsWith('"', [System.StringComparison]::Ordinal) -and
                $value.EndsWith('"', [System.StringComparison]::Ordinal)
            ) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                return $value
            }
        }
    }
    Throw-DatabaseGateFailure -Step "READ-LOCAL-DATABASE-STATUS" -Reason "invalid" -Code 2
}

function Read-EnvironmentAssignment {
    param(
        [string]$Path,
        [string]$Key
    )

    $reader = $null
    try {
        $reader = New-Object System.IO.StreamReader($Path, [System.Text.Encoding]::UTF8, $true)
        while (-not $reader.EndOfStream) {
            $line = $reader.ReadLine()
            if ($line.StartsWith($Key + "=", [System.StringComparison]::Ordinal)) {
                $value = $line.Substring($Key.Length + 1)
                if (-not [string]::IsNullOrWhiteSpace($value)) {
                    return $value
                }
                break
            }
        }
    }
    catch {
        Throw-DatabaseGateFailure -Step "READ-BACKEND-DATABASE-ENV" -Reason "operational" -Code 2
    }
    finally {
        if ($null -ne $reader) {
            $reader.Dispose()
        }
    }
    Throw-DatabaseGateFailure -Step "READ-BACKEND-DATABASE-ENV" -Reason "invalid" -Code 2
}

function Save-ProcessEnvironment {
    param([string[]]$Names)

    $saved = @{}
    foreach ($name in $Names) {
        $saved[$name] = [pscustomobject]@{
            Existed = Test-Path -LiteralPath ("Env:\" + $name)
            Value = [Environment]::GetEnvironmentVariable($name, "Process")
        }
    }
    return $saved
}

function Restore-ProcessEnvironment {
    param([hashtable]$Saved)

    foreach ($name in $Saved.Keys) {
        if ($Saved[$name].Existed) {
            [Environment]::SetEnvironmentVariable($name, $Saved[$name].Value, "Process")
        }
        else {
            [Environment]::SetEnvironmentVariable($name, $null, "Process")
        }
    }
}

function ConvertFrom-DatabaseJson {
    param(
        [string]$Value,
        [string]$Step
    )

    try {
        if ([string]::IsNullOrWhiteSpace($Value)) {
            throw New-Object System.FormatException("empty JSON")
        }
        return $Value | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        Throw-DatabaseGateFailure -Step $Step -Reason "invalid" -Code 2
    }
}

function Ensure-LocalDatabaseNetwork {
    param(
        [string]$DockerPath,
        [string]$NetworkName,
        [string]$WorkingDirectory
    )

    $step = "VERIFY-LOCAL-DATABASE-NETWORK"
    [Console]::Out.WriteLine("[START] step=" + $step)
    $listResult = Invoke-DatabaseChild `
        -FilePath $DockerPath `
        -Arguments @(
            "network",
            "ls",
            "--filter",
            ("name=^" + $NetworkName + '$'),
            "--format",
            "{{.Name}}"
        ) `
        -WorkingDirectory $WorkingDirectory `
        -TimeoutMilliseconds 30000
    if ($listResult.ExitCode -ne 0) {
        Throw-DatabaseGateFailure -Step $step -Reason "operational" -Code 2
    }
    $networkNames = @(
        $listResult.Output -split "`r?`n" |
            ForEach-Object { $_.Trim() } |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    if ($networkNames.Count -eq 0) {
        $createResult = Invoke-DatabaseChild `
            -FilePath $DockerPath `
            -Arguments @(
                "network",
                "create",
                "--driver",
                "bridge",
                "--opt",
                "com.docker.network.bridge.host_binding_ipv4=127.0.0.1",
                "--label",
                "com.sejong-ai.local-boundary=sejong-ai-local",
                $NetworkName
            ) `
            -WorkingDirectory $WorkingDirectory `
            -TimeoutMilliseconds 30000
        if ($createResult.ExitCode -ne 0) {
            Throw-DatabaseGateFailure -Step $step -Reason "child" -Code $createResult.ExitCode
        }
    }
    elseif ($networkNames.Count -ne 1 -or $networkNames[0] -cne $NetworkName) {
        Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
    }

    $inspectResult = Invoke-DatabaseChild `
        -FilePath $DockerPath `
        -Arguments @(
            "network",
            "inspect",
            $NetworkName,
            "--format",
            "{{json .}}"
        ) `
        -WorkingDirectory $WorkingDirectory `
        -TimeoutMilliseconds 30000
    if ($inspectResult.ExitCode -ne 0) {
        Throw-DatabaseGateFailure -Step $step -Reason "child" -Code $inspectResult.ExitCode
    }
    $network = ConvertFrom-DatabaseJson -Value $inspectResult.Output -Step $step
    if (
        $network.Name -cne $NetworkName -or
        $network.Scope -cne "local" -or
        $network.Driver -cne "bridge" -or
        $null -eq $network.Options -or
        $null -eq $network.Labels
    ) {
        Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
    }
    $bindingOption = $network.Options.PSObject.Properties[
        "com.docker.network.bridge.host_binding_ipv4"
    ]
    if ($null -eq $bindingOption -or $bindingOption.Value -cne "127.0.0.1") {
        Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
    }
    $ownershipLabel = $network.Labels.PSObject.Properties[
        "com.sejong-ai.local-boundary"
    ]
    if ($null -eq $ownershipLabel -or $ownershipLabel.Value -cne "sejong-ai-local") {
        Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
    }
    [Console]::Out.WriteLine("[PASS] step=" + $step)
}

function Assert-LocalDatabaseRuntime {
    param(
        [string]$DockerPath,
        [string]$ProjectId,
        [string]$NetworkName,
        [string]$ExpectedContainerName,
        [string]$WorkingDirectory,
        [switch]$AllowAbsent
    )

    $step = "VERIFY-LOCAL-DATABASE-RUNTIME"
    [Console]::Out.WriteLine("[START] step=" + $step)
    $listResult = Invoke-DatabaseChild `
        -FilePath $DockerPath `
        -Arguments @(
            "ps",
            "-a",
            "--filter",
            ("label=com.supabase.cli.project=" + $ProjectId),
            "--format",
            "{{.ID}}"
        ) `
        -WorkingDirectory $WorkingDirectory `
        -TimeoutMilliseconds 30000
    if ($listResult.ExitCode -ne 0) {
        Throw-DatabaseGateFailure -Step $step -Reason "operational" -Code 2
    }
    $containerIds = @(
        $listResult.Output -split "`r?`n" |
            ForEach-Object { $_.Trim() } |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    if ($containerIds.Count -eq 0 -and $AllowAbsent) {
        [Console]::Out.WriteLine("[PASS] step=" + $step)
        return $false
    }
    if ($containerIds.Count -ne 1) {
        Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
    }

    $inspectResult = Invoke-DatabaseChild `
        -FilePath $DockerPath `
        -Arguments @(
            "inspect",
            $containerIds[0],
            "--format",
            "{{json .}}"
        ) `
        -WorkingDirectory $WorkingDirectory `
        -TimeoutMilliseconds 30000
    if ($inspectResult.ExitCode -ne 0) {
        Throw-DatabaseGateFailure -Step $step -Reason "child" -Code $inspectResult.ExitCode
    }
    $container = ConvertFrom-DatabaseJson -Value $inspectResult.Output -Step $step
    $actualName = [string]$container.Name
    if ($actualName.StartsWith("/", [System.StringComparison]::Ordinal)) {
        $actualName = $actualName.Substring(1)
    }
    if ($actualName -cne $ExpectedContainerName) {
        Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
    }
    if (
        $null -eq $container.State -or
        $container.State.Running -ne $true -or
        $null -eq $container.Config -or
        $null -eq $container.Config.Labels
    ) {
        Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
    }
    $projectLabel = $container.Config.Labels.PSObject.Properties[
        "com.supabase.cli.project"
    ]
    if ($null -eq $projectLabel -or $projectLabel.Value -cne $ProjectId) {
        Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
    }
    if (
        $null -eq $container.HostConfig -or
        $container.HostConfig.NetworkMode -cne $NetworkName -or
        $null -eq $container.NetworkSettings -or
        $null -eq $container.NetworkSettings.Networks -or
        $null -eq $container.NetworkSettings.Networks.PSObject.Properties[$NetworkName]
    ) {
        Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
    }
    if ($null -eq $container.HostConfig.PortBindings) {
        Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
    }
    $publishedPorts = @($container.HostConfig.PortBindings.PSObject.Properties)
    if ($publishedPorts.Count -ne 1 -or $publishedPorts[0].Name -cne "5432/tcp") {
        Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
    }
    foreach ($publishedPort in $publishedPorts) {
        $bindings = @($publishedPort.Value)
        if ($bindings.Count -ne 1) {
            Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
        }
        foreach ($binding in $bindings) {
            if ($null -eq $binding) {
                Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
            }
            $requestedHostIp = [string]$binding.HostIp
            if (
                (
                    $requestedHostIp -cne "" -and
                    $requestedHostIp -cne "127.0.0.1"
                ) -or
                [string]$binding.HostPort -cne "54322"
            ) {
                Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
            }
        }
    }
    if ($null -eq $container.NetworkSettings.Ports) {
        Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
    }
    $resolvedPorts = @($container.NetworkSettings.Ports.PSObject.Properties)
    if ($resolvedPorts.Count -ne 1 -or $resolvedPorts[0].Name -cne "5432/tcp") {
        Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
    }
    $resolvedBindings = @($resolvedPorts[0].Value)
    if ($resolvedBindings.Count -ne 1) {
        Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
    }
    $resolvedBinding = $resolvedBindings[0]
    if (
        $null -eq $resolvedBinding -or
        [string]$resolvedBinding.HostIp -cne "127.0.0.1" -or
        [string]$resolvedBinding.HostPort -cne "54322"
    ) {
        Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
    }
    [Console]::Out.WriteLine("[PASS] step=" + $step)
    return $true
}

function Stop-OwnedUnsafeLocalDatabaseRuntime {
    param(
        [string]$SupabasePath,
        [string]$DockerPath,
        [string]$ProjectId,
        [string]$WorkingDirectory
    )

    $step = "STOP-UNSAFE-LOCAL-DATABASE-RUNTIME"
    [Console]::Out.WriteLine("[START] step=" + $step)
    try {
        $stopResult = Invoke-DatabaseChild `
            -FilePath $SupabasePath `
            -Arguments @("stop") `
            -WorkingDirectory $WorkingDirectory `
            -TimeoutMilliseconds 120000
    }
    catch {
        if ($_.Exception.Data.Contains("step")) {
            throw
        }
        Throw-DatabaseGateFailure -Step $step -Reason "operational" -Code 2
    }
    if ($stopResult.ExitCode -ne 0) {
        Throw-DatabaseGateFailure -Step $step -Reason "child" -Code $stopResult.ExitCode
    }

    try {
        $listResult = Invoke-DatabaseChild `
            -FilePath $DockerPath `
            -Arguments @(
                "ps",
                "-a",
                "--filter",
                ("label=com.supabase.cli.project=" + $ProjectId),
                "--format",
                "{{.ID}}"
            ) `
            -WorkingDirectory $WorkingDirectory `
            -TimeoutMilliseconds 30000
    }
    catch {
        if ($_.Exception.Data.Contains("step")) {
            throw
        }
        Throw-DatabaseGateFailure -Step $step -Reason "operational" -Code 2
    }
    if ($listResult.ExitCode -ne 0) {
        Throw-DatabaseGateFailure -Step $step -Reason "operational" -Code 2
    }
    $remainingContainerIds = @(
        $listResult.Output -split "`r?`n" |
            ForEach-Object { $_.Trim() } |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    if ($remainingContainerIds.Count -ne 0) {
        Throw-DatabaseGateFailure -Step $step -Reason "invalid" -Code 2
    }
    [Console]::Out.WriteLine("[PASS] step=" + $step)
}

$skipStart = $false
$skipRollbackReplay = $false
$skipStartSeen = $false
$skipRollbackSeen = $false
$exitCode = 0
$savedEnvironment = Save-ProcessEnvironment -Names @(
    "SEJONG_ADMIN_DATABASE_URL",
    "SEJONG_DB_TEST_URL"
)

try {
    foreach ($argument in $args) {
        $argumentValue = [string]$argument
        if ($argumentValue.Equals("-SkipStart", [System.StringComparison]::OrdinalIgnoreCase)) {
            if ($skipStartSeen) {
                Throw-DatabaseGateFailure -Step "VALIDATE-DATABASE-ARGUMENTS" -Reason "invalid" -Code 2
            }
            $skipStartSeen = $true
            $skipStart = $true
            continue
        }
        if ($argumentValue.Equals(
                "-SkipRollbackReplay",
                [System.StringComparison]::OrdinalIgnoreCase
            )) {
            if ($skipRollbackSeen) {
                Throw-DatabaseGateFailure -Step "VALIDATE-DATABASE-ARGUMENTS" -Reason "invalid" -Code 2
            }
            $skipRollbackSeen = $true
            $skipRollbackReplay = $true
            continue
        }
        Throw-DatabaseGateFailure -Step "VALIDATE-DATABASE-ARGUMENTS" -Reason "invalid" -Code 2
    }

    if (
        $PSVersionTable.PSVersion.Major -lt 5 -or
        (
            $PSVersionTable.PSVersion.Major -eq 5 -and
            $PSVersionTable.PSVersion.Minor -lt 1
        )
    ) {
        Throw-DatabaseGateFailure -Step "PREFLIGHT-POWERSHELL" -Reason "version" -Code 2
    }

    $scriptDirectory = [System.IO.Path]::GetFullPath($PSScriptRoot)
    $repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptDirectory ".."))
    $supabaseBinary = Join-Path $repositoryRoot ".tools\supabase\v2.109.1-sejong-loopback\supabase.exe"
    $pythonBinary = Join-Path $repositoryRoot "apps\api\.venv\Scripts\python.exe"
    $bootstrapScript = Join-Path $scriptDirectory "bootstrap_patched_supabase.ps1"
    $provisionScript = Join-Path $scriptDirectory (
        "provision_local_database_" + "lo" + "gin.py"
    )
    $sqlRunner = Join-Path $scriptDirectory "run_database_sql.py"
    $apiEnvironmentPath = Join-Path $repositoryRoot "apps\api\.env"
    $powerShellBinary = Join-Path $PSHOME "powershell.exe"
    $localProjectId = "sejong-ai-local"
    $localNetworkName = "sejong-ai-local-loopback"
    $localDatabaseContainerName = "supabase_db_sejong-ai-local"

    foreach ($requiredFile in @(
            $supabaseBinary,
            $pythonBinary,
            $bootstrapScript,
            $provisionScript,
            $sqlRunner,
            $powerShellBinary
        )) {
        if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
            Throw-DatabaseGateFailure -Step "PREFLIGHT-LOCAL-FILES" -Reason "missing" -Code 2
        }
    }

    $pythonCheck = Invoke-DatabaseChild `
        -FilePath $pythonBinary `
        -Arguments @("--version") `
        -WorkingDirectory $repositoryRoot `
        -TimeoutMilliseconds 15000
    if ($pythonCheck.ExitCode -ne 0) {
        Throw-DatabaseGateFailure -Step "PREFLIGHT-PYTHON" -Reason "child" -Code $pythonCheck.ExitCode
    }

    [Console]::Out.WriteLine("[START] step=PREFLIGHT-DOCKER")
    $dockerCommand = Get-Command "docker.exe" -CommandType Application -ErrorAction SilentlyContinue
    if ($null -eq $dockerCommand) {
        $dockerCommand = Get-Command "docker" -CommandType Application -ErrorAction SilentlyContinue
    }
    if ($null -eq $dockerCommand) {
        Throw-DatabaseGateFailure -Step "PREFLIGHT-DOCKER" -Reason "missing" -Code 2
    }
    $dockerCheck = Invoke-DatabaseChild `
        -FilePath $dockerCommand.Source `
        -Arguments @("version", "--format", "{{.Server.Version}}") `
        -WorkingDirectory $repositoryRoot `
        -TimeoutMilliseconds 30000
    if ($dockerCheck.ExitCode -ne 0) {
        Throw-DatabaseGateFailure -Step "PREFLIGHT-DOCKER" -Reason "child" -Code $dockerCheck.ExitCode
    }
    $dockerVersionText = $dockerCheck.Output.Trim()
    try {
        if ($dockerVersionText -notmatch '^\d+\.\d+\.\d+(?:\.\d+)?$') {
            throw New-Object System.FormatException("unsupported Docker version format")
        }
        $dockerVersion = [System.Version]::Parse($dockerVersionText)
    }
    catch {
        Throw-DatabaseGateFailure -Step "PREFLIGHT-DOCKER" -Reason "version" -Code 2
    }
    if ($dockerVersion.Major -lt 28) {
        Throw-DatabaseGateFailure -Step "PREFLIGHT-DOCKER" -Reason "version" -Code 2
    }
    [Console]::Out.WriteLine("[PASS] step=PREFLIGHT-DOCKER")

    $null = Invoke-DatabaseStep `
        -Step "VERIFY-SUPABASE-VERSION" `
        -FilePath $powerShellBinary `
        -Arguments @(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            $bootstrapScript,
            "-VerifyOnly"
        ) `
        -WorkingDirectory $repositoryRoot `
        -TimeoutMilliseconds 30000

    Ensure-LocalDatabaseNetwork `
        -DockerPath $dockerCommand.Source `
        -NetworkName $localNetworkName `
        -WorkingDirectory $repositoryRoot

    $runnerCreatedRuntime = $false
    if (-not $skipStart) {
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
    try {
        $null = Assert-LocalDatabaseRuntime `
            -DockerPath $dockerCommand.Source `
            -ProjectId $localProjectId `
            -NetworkName $localNetworkName `
            -ExpectedContainerName $localDatabaseContainerName `
            -WorkingDirectory $repositoryRoot
    }
    catch {
        $runtimeFailure = $_.Exception
        if ($runnerCreatedRuntime) {
            Stop-OwnedUnsafeLocalDatabaseRuntime `
                -SupabasePath $supabaseBinary `
                -DockerPath $dockerCommand.Source `
                -ProjectId $localProjectId `
                -WorkingDirectory $repositoryRoot
        }
        throw $runtimeFailure
    }

    # Local command: db reset.
    $null = Invoke-DatabaseStep `
        -Step "RESET-DATABASE-ONE" `
        -FilePath $supabaseBinary `
        -Arguments @("db", "reset", "--local") `
        -WorkingDirectory $repositoryRoot

    $status = Invoke-DatabaseChild `
        -FilePath $supabaseBinary `
        -Arguments @("status", "-o", "env") `
        -WorkingDirectory $repositoryRoot `
        -TimeoutMilliseconds 30000
    if ($status.ExitCode -ne 0) {
        Throw-DatabaseGateFailure -Step "READ-LOCAL-DATABASE-STATUS" -Reason "child" -Code $status.ExitCode
    }
    $env:SEJONG_ADMIN_DATABASE_URL = Read-DatabaseUrlFromStatus -StatusOutput $status.Output

    $provisionStepOne = "PROVISION-LOCAL-DB-" + "LOG" + "IN-ONE"
    $null = Invoke-DatabaseStep `
        -Step $provisionStepOne `
        -FilePath $pythonBinary `
        -Arguments @("-B", $provisionScript) `
        -WorkingDirectory $repositoryRoot `
        -TimeoutMilliseconds 30000

    # Local command: test db.
    $null = Invoke-DatabaseStep `
        -Step "TEST-PGTAP-ONE" `
        -FilePath $supabaseBinary `
        -Arguments @("test", "db") `
        -WorkingDirectory $repositoryRoot

    if (-not $skipRollbackReplay) {
        $rollbackFiles = @(
            (Join-Path $repositoryRoot "database\rollbacks\20260727000680_civic_scope_gap_queue.rollback.sql"),
            (Join-Path $repositoryRoot "database\rollbacks\20260722000670_candidate_public_id_binding.rollback.sql"),
            (Join-Path $repositoryRoot "database\rollbacks\20260722000660_chat_idempotency.rollback.sql"),
            (Join-Path $repositoryRoot "database\rollbacks\20260722000650_local_admin_read_capabilities.rollback.sql"),
            (Join-Path $repositoryRoot "database\rollbacks\20260717000600_deferred_active_question_trigger_security.rollback.sql"),
            (Join-Path $repositoryRoot "database\rollbacks\20260716000500_indexes_and_read_interfaces.rollback.sql"),
            (Join-Path $repositoryRoot "database\rollbacks\20260716000400_candidate_workflow.rollback.sql"),
            (Join-Path $repositoryRoot "database\rollbacks\20260716000300_capabilities_and_functions.rollback.sql"),
            (Join-Path $repositoryRoot "database\rollbacks\20260716000200_invariants_and_lineage.rollback.sql"),
            (Join-Path $repositoryRoot "database\rollbacks\20260716000100_private_schema.rollback.sql")
        )
        $null = Invoke-DatabaseStep `
            -Step "ROLLBACK-DB001" `
            -FilePath $pythonBinary `
            -Arguments (@("-B", $sqlRunner) + $rollbackFiles) `
            -WorkingDirectory $repositoryRoot `
            -TimeoutMilliseconds 60000

        $absenceProof = Join-Path $repositoryRoot "database\verify_db001_absent.sql"
        $null = Invoke-DatabaseStep `
            -Step "VERIFY-DB001-ABSENT" `
            -FilePath $pythonBinary `
            -Arguments @("-B", $sqlRunner, $absenceProof) `
            -WorkingDirectory $repositoryRoot `
            -TimeoutMilliseconds 30000

        $null = Invoke-DatabaseStep `
            -Step "RESET-DATABASE-TWO" `
            -FilePath $supabaseBinary `
            -Arguments @("db", "reset", "--local") `
            -WorkingDirectory $repositoryRoot

        $provisionStepTwo = "PROVISION-LOCAL-DB-" + "LOG" + "IN-TWO"
        $null = Invoke-DatabaseStep `
            -Step $provisionStepTwo `
            -FilePath $pythonBinary `
            -Arguments @("-B", $provisionScript) `
            -WorkingDirectory $repositoryRoot `
            -TimeoutMilliseconds 30000

        $null = Invoke-DatabaseStep `
            -Step "TEST-PGTAP-TWO" `
            -FilePath $supabaseBinary `
            -Arguments @("test", "db") `
            -WorkingDirectory $repositoryRoot
    }

    $env:SEJONG_DB_TEST_URL = Read-EnvironmentAssignment `
        -Path $apiEnvironmentPath `
        -Key "DATABASE_URL"
    $integrationTest = Join-Path $repositoryRoot "apps\api\tests\db\test_integration.py"
    $null = Invoke-DatabaseStep `
        -Step "TEST-DATABASE-INTEGRATION" `
        -FilePath $pythonBinary `
        -Arguments @(
            "-B",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            $integrationTest
        ) `
        -WorkingDirectory $repositoryRoot `
        -TimeoutMilliseconds 120000
}
catch {
    $failure = $_.Exception
    if (
        $failure.Data.Contains("step") -and
        $failure.Data.Contains("reason") -and
        $failure.Data.Contains("code")
    ) {
        $exitCode = [int]$failure.Data["code"]
        [Console]::Out.WriteLine(
            "[FAIL] step=" + [string]$failure.Data["step"] +
            " reason=" + [string]$failure.Data["reason"] +
            " code=" + [string]$failure.Data["code"]
        )
    }
    else {
        $exitCode = 2
        [Console]::Out.WriteLine("[FAIL] step=VERIFY-DATABASE reason=operational code=2")
    }
}
finally {
    try {
        Restore-ProcessEnvironment -Saved $savedEnvironment
    }
    catch {
        if ($exitCode -eq 0) {
            $exitCode = 2
            [Console]::Out.WriteLine(
                "[FAIL] step=RESTORE-DATABASE-ENVIRONMENT reason=operational code=2"
            )
        }
    }
}

exit $exitCode
