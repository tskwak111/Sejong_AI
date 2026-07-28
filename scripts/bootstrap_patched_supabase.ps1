$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

function Throw-PatchedBootstrapFailure {
    param(
        [string]$Step,
        [string]$Reason,
        [int]$Code
    )

    $failure = New-Object System.InvalidOperationException("controlled patched bootstrap failure")
    $failure.Data["PatchedBootstrapFailure"] = $true
    $failure.Data["Step"] = $Step
    $failure.Data["Reason"] = $Reason
    $failure.Data["Code"] = $Code
    throw $failure
}

function Write-PatchedStatus {
    param([string]$Message)

    [Console]::Out.WriteLine($Message)
}

function Resolve-SafeChildPath {
    param(
        [string]$Root,
        [string]$Candidate
    )

    if ([string]::IsNullOrWhiteSpace($Root) -or [string]::IsNullOrWhiteSpace($Candidate)) {
        Throw-PatchedBootstrapFailure "VALIDATE-PATCHED-SUPABASE-PATH" "invalid" 2
    }

    try {
        $rootPath = [System.IO.Path]::GetFullPath($Root)
        if ([System.IO.Path]::IsPathRooted($Candidate)) {
            $candidatePath = [System.IO.Path]::GetFullPath($Candidate)
        }
        else {
            $candidatePath = [System.IO.Path]::GetFullPath(
                [System.IO.Path]::Combine($rootPath, $Candidate)
            )
        }
    }
    catch {
        Throw-PatchedBootstrapFailure "VALIDATE-PATCHED-SUPABASE-PATH" "invalid" 2
    }

    $trimmedRoot = $rootPath.TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
    $rootPrefix = $trimmedRoot + [System.IO.Path]::DirectorySeparatorChar
    if (
        $candidatePath -ceq $trimmedRoot -or
        -not $candidatePath.StartsWith(
            $rootPrefix,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {
        Throw-PatchedBootstrapFailure "VALIDATE-PATCHED-SUPABASE-PATH" "invalid" 2
    }

    $pathsToCheck = New-Object System.Collections.Generic.List[string]
    $pathsToCheck.Add($trimmedRoot)
    $relative = $candidatePath.Substring($rootPrefix.Length)
    $current = $trimmedRoot
    foreach ($segment in @($relative -split "[\\/]")) {
        if ([string]::IsNullOrEmpty($segment)) {
            continue
        }
        $current = [System.IO.Path]::Combine($current, $segment)
        $pathsToCheck.Add($current)
    }
    foreach ($pathToCheck in $pathsToCheck) {
        if (Test-Path -LiteralPath $pathToCheck) {
            $item = Get-Item -LiteralPath $pathToCheck -Force
            if (
                ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0
            ) {
                Throw-PatchedBootstrapFailure "VALIDATE-PATCHED-SUPABASE-PATH" "invalid" 2
            }
        }
    }

    return $candidatePath
}

function Remove-OwnedPath {
    param(
        [string]$Root,
        [string]$Candidate
    )

    $ownedPath = Resolve-SafeChildPath $Root $Candidate
    if (Test-Path -LiteralPath $ownedPath) {
        Remove-Item -LiteralPath $ownedPath -Recurse -Force
    }
}

function Assert-PatchedCheckoutPathBudget {
    param(
        [string]$Destination,
        [int]$MaxTrackedRelativeFilePathLength,
        [int]$MaxAbsoluteFilePathLength
    )

    $checkout = Resolve-SafeChildPath $script:ToolRoot $Destination
    $projectedMaximum = $checkout.Length + 1 + $MaxTrackedRelativeFilePathLength
    if (
        $MaxTrackedRelativeFilePathLength -ne 134 -or
        $MaxAbsoluteFilePathLength -ne 248 -or
        $projectedMaximum -gt $MaxAbsoluteFilePathLength
    ) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "invalid" 2
    }
    return $checkout
}

function ConvertTo-PatchedProcessArgument {
    param([string]$Value)

    if ($null -eq $Value) {
        return '""'
    }
    if ($Value.Length -gt 0 -and $Value -notmatch '[\s"]') {
        return $Value
    }

    $builder = New-Object System.Text.StringBuilder
    $null = $builder.Append('"')
    $backslashes = 0
    foreach ($character in $Value.ToCharArray()) {
        if ($character -eq [char]92) {
            $backslashes += 1
            continue
        }
        if ($character -eq [char]34) {
            if ($backslashes -gt 0) {
                $null = $builder.Append((([string][char]92) * ($backslashes * 2)))
            }
            $null = $builder.Append([char]92)
            $null = $builder.Append([char]34)
            $backslashes = 0
            continue
        }
        if ($backslashes -gt 0) {
            $null = $builder.Append((([string][char]92) * $backslashes))
            $backslashes = 0
        }
        $null = $builder.Append($character)
    }
    if ($backslashes -gt 0) {
        $null = $builder.Append((([string][char]92) * ($backslashes * 2)))
    }
    $null = $builder.Append('"')
    return $builder.ToString()
}

function Initialize-PatchedJobSupport {
    if ($null -ne ("SejongPatchedBootstrap.NativeJob" -as [type])) {
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

namespace SejongPatchedBootstrap
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
        private const uint WAIT_OBJECT_0 = 0x00000000;
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

    public static class NativePath
    {
        private const uint FILE_SHARE_READ = 0x00000001;
        private const uint FILE_SHARE_WRITE = 0x00000002;
        private const uint FILE_SHARE_DELETE = 0x00000004;
        private const uint OPEN_EXISTING = 3;
        private const uint FILE_FLAG_BACKUP_SEMANTICS = 0x02000000;

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr CreateFile(
            string fileName,
            uint desiredAccess,
            uint shareMode,
            IntPtr securityAttributes,
            uint creationDisposition,
            uint flagsAndAttributes,
            IntPtr templateFile
        );

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern uint GetFinalPathNameByHandle(
            IntPtr file,
            StringBuilder filePath,
            uint filePathLength,
            uint flags
        );

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool CloseHandle(IntPtr handle);

        public static string GetFinalPath(string path)
        {
            IntPtr file = CreateFile(
                path,
                0,
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                IntPtr.Zero,
                OPEN_EXISTING,
                FILE_FLAG_BACKUP_SEMANTICS,
                IntPtr.Zero
            );
            if (file == new IntPtr(-1))
            {
                throw new Win32Exception(Marshal.GetLastWin32Error());
            }
            try
            {
                StringBuilder buffer = new StringBuilder(1024);
                uint length = GetFinalPathNameByHandle(
                    file,
                    buffer,
                    (uint)buffer.Capacity,
                    0
                );
                if (length == 0)
                {
                    throw new Win32Exception(Marshal.GetLastWin32Error());
                }
                if (length >= buffer.Capacity)
                {
                    buffer = new StringBuilder((int)length + 1);
                    length = GetFinalPathNameByHandle(
                        file,
                        buffer,
                        (uint)buffer.Capacity,
                        0
                    );
                    if (length == 0 || length >= buffer.Capacity)
                    {
                        throw new Win32Exception(Marshal.GetLastWin32Error());
                    }
                }
                string finalPath = buffer.ToString();
                if (finalPath.StartsWith(@"\\?\UNC\", StringComparison.Ordinal))
                {
                    return @"\\" + finalPath.Substring(8);
                }
                if (finalPath.StartsWith(@"\\?\", StringComparison.Ordinal))
                {
                    return finalPath.Substring(4);
                }
                return finalPath;
            }
            finally
            {
                CloseHandle(file);
            }
        }
    }
}
"@
    $null = Add-Type -TypeDefinition $jobSource -Language CSharp -PassThru
}

function Invoke-PatchedChild {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [int]$TimeoutMilliseconds
    )

    if ($TimeoutMilliseconds -le 0) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "operational" 2
    }

    try {
        Initialize-PatchedJobSupport
        $quotedArguments = New-Object System.Collections.Generic.List[string]
        foreach ($argument in @($Arguments)) {
            $quotedArguments.Add((ConvertTo-PatchedProcessArgument $argument))
        }
        $commandLine = ConvertTo-PatchedProcessArgument $FilePath
        if ($quotedArguments.Count -gt 0) {
            $commandLine += " " + ($quotedArguments -join " ")
        }
        return [SejongPatchedBootstrap.NativeJob]::Run(
            $FilePath,
            $commandLine,
            $WorkingDirectory,
            $TimeoutMilliseconds
        )
    }
    catch {
        Throw-PatchedBootstrapFailure $script:CurrentStep "operational" 2
    }
}

function Read-PatchedJson {
    param(
        [string]$Path,
        [string]$Step
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        Throw-PatchedBootstrapFailure $Step "missing" 2
    }

    $parsed = $null
    $readSucceeded = $false
    try {
        $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
        $parsed = $raw | ConvertFrom-Json
        $readSucceeded = $null -ne $parsed
    }
    catch {
        $readSucceeded = $false
    }
    if (-not $readSucceeded) {
        Throw-PatchedBootstrapFailure $Step "invalid" 2
    }
    $script:LastPatchedJsonRaw = $raw
    return $parsed
}

function Assert-ExactRawJsonPropertyNames {
    param(
        [string]$Raw,
        [string[]]$Expected,
        [string]$Step,
        [string]$Reason
    )

    if ([string]::IsNullOrWhiteSpace($Raw)) {
        Throw-PatchedBootstrapFailure $Step $Reason 2
    }
    $propertyPattern = '(?s)(?:\{|,)\s*"((?:\\["\\/bfnrt]|\\u[0-9a-fA-F]{4}|[^"\\])*)"\s*:'
    $propertyMatches = [System.Text.RegularExpressions.Regex]::Matches(
        $Raw,
        $propertyPattern
    )
    $expectedCounts = New-Object "System.Collections.Generic.Dictionary[string,int]" (
        [System.StringComparer]::Ordinal
    )
    $actualCounts = New-Object "System.Collections.Generic.Dictionary[string,int]" (
        [System.StringComparer]::Ordinal
    )
    foreach ($name in $Expected) {
        if ($expectedCounts.ContainsKey($name)) {
            $expectedCounts[$name] += 1
        }
        else {
            $expectedCounts.Add($name, 1)
        }
    }
    foreach ($propertyMatch in $propertyMatches) {
        $name = $propertyMatch.Groups[1].Value
        if ($actualCounts.ContainsKey($name)) {
            $actualCounts[$name] += 1
        }
        else {
            $actualCounts.Add($name, 1)
        }
    }
    if (
        $propertyMatches.Count -ne $Expected.Count -or
        $actualCounts.Count -ne $expectedCounts.Count
    ) {
        Throw-PatchedBootstrapFailure $Step $Reason 2
    }
    foreach ($name in $expectedCounts.Keys) {
        if (
            -not $actualCounts.ContainsKey($name) -or
            $actualCounts[$name] -ne $expectedCounts[$name]
        ) {
            Throw-PatchedBootstrapFailure $Step $Reason 2
        }
    }
}

function Assert-ExactPropertyNames {
    param(
        [object]$Value,
        [string[]]$Expected,
        [string]$Step,
        [string]$Reason = "unapproved-source"
    )

    if ($null -eq $Value) {
        Throw-PatchedBootstrapFailure $Step $Reason 2
    }
    $actual = @($Value.PSObject.Properties | ForEach-Object { $_.Name })
    $differences = @(
        Compare-Object -ReferenceObject @($Expected) -DifferenceObject $actual -CaseSensitive
    )
    if ($actual.Count -ne $Expected.Count -or $differences.Count -ne 0) {
        Throw-PatchedBootstrapFailure $Step $Reason 2
    }
}

function Assert-PatchedStringValues {
    param(
        [object[]]$Values,
        [string]$Step,
        [string]$Reason
    )

    foreach ($value in $Values) {
        if ($value -isnot [string]) {
            Throw-PatchedBootstrapFailure $Step $Reason 2
        }
    }
}

function Assert-ExactSourceManifest {
    param([object]$Manifest)

    $step = "VALIDATE-PATCHED-SUPABASE-SOURCE-MANIFEST"
    Assert-ExactRawJsonPropertyNames $script:LastPatchedJsonRaw @(
        "schema_version",
        "upstream",
        "repository",
        "tag",
        "tag_object_sha1",
        "commit_sha1",
        "go",
        "version",
        "platform",
        "url",
        "sha256",
        "patch",
        "relative_path",
        "size_bytes",
        "sha256",
        "allowed_files",
        "workspace",
        "checkout_a",
        "checkout_b",
        "max_tracked_relative_file_path_length",
        "max_absolute_file_path_length",
        "build",
        "working_directory",
        "version",
        "goos",
        "goarch",
        "cgo_enabled",
        "goproxy",
        "gosumdb",
        "goprivate",
        "gonoproxy",
        "gonosumdb",
        "goinsecure",
        "goenv",
        "gowork",
        "gotoolchain",
        "goflags",
        "goamd64",
        "goexperiment",
        "flags",
        "ldflags"
    ) $step "unapproved-source"
    Assert-ExactPropertyNames $Manifest @(
        "schema_version", "upstream", "go", "patch", "workspace", "build"
    ) $step
    Assert-ExactPropertyNames $Manifest.upstream @(
        "repository", "tag", "tag_object_sha1", "commit_sha1"
    ) $step
    Assert-ExactPropertyNames $Manifest.go @(
        "version", "platform", "url", "sha256"
    ) $step
    Assert-ExactPropertyNames $Manifest.patch @(
        "relative_path", "size_bytes", "sha256", "allowed_files"
    ) $step
    Assert-ExactPropertyNames $Manifest.workspace @(
        "checkout_a",
        "checkout_b",
        "max_tracked_relative_file_path_length",
        "max_absolute_file_path_length"
    ) $step
    Assert-ExactPropertyNames $Manifest.build @(
        "working_directory",
        "version",
        "goos",
        "goarch",
        "cgo_enabled",
        "goproxy",
        "gosumdb",
        "goprivate",
        "gonoproxy",
        "gonosumdb",
        "goinsecure",
        "goenv",
        "gowork",
        "gotoolchain",
        "goflags",
        "goamd64",
        "goexperiment",
        "flags",
        "ldflags"
    ) $step
    Assert-PatchedStringValues @(
        $Manifest.upstream.repository,
        $Manifest.upstream.tag,
        $Manifest.upstream.tag_object_sha1,
        $Manifest.upstream.commit_sha1,
        $Manifest.go.version,
        $Manifest.go.platform,
        $Manifest.go.url,
        $Manifest.go.sha256,
        $Manifest.patch.relative_path,
        $Manifest.patch.sha256,
        $Manifest.workspace.checkout_a,
        $Manifest.workspace.checkout_b,
        $Manifest.build.working_directory,
        $Manifest.build.version,
        $Manifest.build.goos,
        $Manifest.build.goarch,
        $Manifest.build.cgo_enabled,
        $Manifest.build.goproxy,
        $Manifest.build.gosumdb,
        $Manifest.build.goprivate,
        $Manifest.build.gonoproxy,
        $Manifest.build.gonosumdb,
        $Manifest.build.goinsecure,
        $Manifest.build.goenv,
        $Manifest.build.gowork,
        $Manifest.build.gotoolchain,
        $Manifest.build.goflags,
        $Manifest.build.goamd64,
        $Manifest.build.goexperiment,
        $Manifest.build.ldflags
    ) $step "unapproved-source"
    if (
        $Manifest.patch.allowed_files -isnot [System.Array] -or
        $Manifest.build.flags -isnot [System.Array]
    ) {
        Throw-PatchedBootstrapFailure $step "unapproved-source" 2
    }

    $approved = (
        $Manifest.schema_version -is [int] -and
        $Manifest.schema_version -eq 1 -and
        $Manifest.upstream.repository -ceq "https://github.com/supabase/cli.git" -and
        $Manifest.upstream.tag -ceq "v2.109.1" -and
        $Manifest.upstream.tag_object_sha1 -ceq "9d25ff8b5b0fba3c6f0ef000e7dd658c8d710c38" -and
        $Manifest.upstream.commit_sha1 -ceq "6d4c19870ed213ba7f682f117d0345c8a40bfa94" -and
        $Manifest.go.version -ceq "1.25.11" -and
        $Manifest.go.platform -ceq "windows-amd64" -and
        $Manifest.go.url -ceq "https://dl.google.com/go/go1.25.11.windows-amd64.zip" -and
        $Manifest.go.sha256 -ceq "b7401f1b41517428e537493316256fb7cf03c66a130a0103ab07f3a2152e2112" -and
        $Manifest.patch.relative_path -ceq "scripts/patches/supabase-cli-v2.109.1-db-loopback.patch" -and
        $Manifest.patch.size_bytes -is [int] -and
        $Manifest.patch.size_bytes -eq 1824 -and
        $Manifest.patch.sha256 -ceq "109c096480e8185d761e9ce8fba10e93efc55190c42eab978f769a6993833f7d" -and
        $Manifest.workspace.checkout_a -ceq "s/a" -and
        $Manifest.workspace.checkout_b -ceq "s/b" -and
        $Manifest.workspace.max_tracked_relative_file_path_length -is [int] -and
        $Manifest.workspace.max_tracked_relative_file_path_length -eq 134 -and
        $Manifest.workspace.max_absolute_file_path_length -is [int] -and
        $Manifest.workspace.max_absolute_file_path_length -eq 248 -and
        $Manifest.build.working_directory -ceq "apps/cli-go" -and
        $Manifest.build.version -ceq "2.109.1" -and
        $Manifest.build.goos -ceq "windows" -and
        $Manifest.build.goarch -ceq "amd64" -and
        $Manifest.build.cgo_enabled -ceq "0" -and
        $Manifest.build.goproxy -ceq "https://proxy.golang.org" -and
        $Manifest.build.gosumdb -ceq "sum.golang.org" -and
        $Manifest.build.goprivate -ceq "" -and
        $Manifest.build.gonoproxy -ceq "" -and
        $Manifest.build.gonosumdb -ceq "" -and
        $Manifest.build.goinsecure -ceq "" -and
        $Manifest.build.goenv -ceq "off" -and
        $Manifest.build.gowork -ceq "off" -and
        $Manifest.build.gotoolchain -ceq "local" -and
        $Manifest.build.goflags -ceq "" -and
        $Manifest.build.goamd64 -ceq "v1" -and
        $Manifest.build.goexperiment -ceq "" -and
        $Manifest.build.ldflags -ceq "-s -w -X github.com/supabase/cli/internal/utils.Version=2.109.1"
    )
    $allowedFiles = @($Manifest.patch.allowed_files)
    $flags = @($Manifest.build.flags)
    Assert-PatchedStringValues $allowedFiles $step "unapproved-source"
    Assert-PatchedStringValues $flags $step "unapproved-source"
    $approved = (
        $approved -and
        $allowedFiles.Count -eq 2 -and
        $allowedFiles[0] -ceq "apps/cli-go/internal/db/start/start_test.go" -and
        $allowedFiles[1] -ceq "apps/cli-go/internal/db/start/start.go" -and
        $flags.Count -eq 2 -and
        $flags[0] -ceq "-trimpath" -and
        $flags[1] -ceq "-buildvcs=false"
    )
    if (-not $approved) {
        Throw-PatchedBootstrapFailure $step "unapproved-source" 2
    }

    try {
        $repositoryUri = New-Object System.Uri($Manifest.upstream.repository)
        $goUri = New-Object System.Uri($Manifest.go.url)
    }
    catch {
        Throw-PatchedBootstrapFailure $step "unapproved-source" 2
    }
    if (
        $repositoryUri.Scheme -cne "https" -or
        $repositoryUri.Host -cne "github.com" -or
        $repositoryUri.Port -ne 443 -or
        $goUri.Scheme -cne "https" -or
        $goUri.Host -cne "dl.google.com" -or
        $goUri.Port -ne 443
    ) {
        Throw-PatchedBootstrapFailure $step "unapproved-source" 2
    }
}

function Assert-ExactRuntimeManifest {
    param(
        [object]$Manifest,
        [string]$SourceManifestHash
    )

    $step = "LOAD-PATCHED-SUPABASE-RUNTIME-MANIFEST"
    Assert-ExactRawJsonPropertyNames $script:LastPatchedJsonRaw @(
        "schema_version",
        "source_manifest_sha256",
        "version",
        "platform",
        "relative_path",
        "sha256"
    ) $step "invalid"
    Assert-ExactPropertyNames $Manifest @(
        "schema_version",
        "source_manifest_sha256",
        "version",
        "platform",
        "relative_path",
        "sha256"
    ) $step "invalid"
    Assert-PatchedStringValues @(
        $Manifest.source_manifest_sha256,
        $Manifest.version,
        $Manifest.platform,
        $Manifest.relative_path,
        $Manifest.sha256
    ) $step "invalid"
    if (
        $Manifest.schema_version -isnot [int] -or
        $Manifest.schema_version -ne 1 -or
        $Manifest.source_manifest_sha256 -cne $SourceManifestHash -or
        $Manifest.source_manifest_sha256 -cnotmatch "^[0-9a-f]{64}$" -or
        $Manifest.version -cne "2.109.1" -or
        $Manifest.platform -cne "windows-amd64" -or
        $Manifest.relative_path -cne ".tools/supabase/v2.109.1-sejong-loopback/supabase.exe" -or
        $Manifest.sha256 -cnotmatch "^[0-9a-f]{64}$"
    ) {
        Throw-PatchedBootstrapFailure $step "invalid" 2
    }
}

function Get-PatchedSha256 {
    param(
        [string]$Path,
        [string]$Step
    )

    try {
        return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    catch {
        Throw-PatchedBootstrapFailure $Step "operational" 2
    }
}

function Assert-PatchedChildSuccess {
    param(
        [object]$Result,
        [string]$Step
    )

    if ($Result.TimedOut -or $Result.ExitCode -ne 0) {
        Throw-PatchedBootstrapFailure $Step "child" 1
    }
}

function Test-PatchedSupabaseVersionStderr {
    param([string]$Value)

    if ([string]::IsNullOrEmpty($Value)) {
        return $true
    }
    $pattern = (
        "\AA new version of Supabase CLI is available: " +
        "v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*) " +
        "\(currently installed v2\.109\.1\)\r?\n" +
        "We recommend updating regularly for new features and bug fixes: " +
        "https://supabase\.com/docs/guides/cli/getting-started" +
        "#updating-the-supabase-cli(?:\r?\n)?\z"
    )
    return [System.Text.RegularExpressions.Regex]::IsMatch(
        $Value,
        $pattern,
        [System.Text.RegularExpressions.RegexOptions]::CultureInvariant
    )
}

function Test-PatchedSupabaseVersion {
    param([string]$BinaryPath)

    if (-not (Test-Path -LiteralPath $BinaryPath -PathType Leaf)) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "missing" 2
    }
    $result = Invoke-PatchedChild $BinaryPath @("--version") $script:RepositoryRoot 15000
    $versionOutput = $result.Stdout
    $platformNewLine = [System.Environment]::NewLine
    if ($versionOutput.EndsWith($platformNewLine)) {
        $versionOutput = $versionOutput.Substring(
            0,
            $versionOutput.Length - $platformNewLine.Length
        )
    }
    elseif ($versionOutput.EndsWith([string][char]10)) {
        $versionOutput = $versionOutput.Substring(0, $versionOutput.Length - 1)
    }
    if (
        $result.TimedOut -or
        $result.ExitCode -ne 0 -or
        -not (Test-PatchedSupabaseVersionStderr $result.Stderr) -or
        $versionOutput -cne "2.109.1"
    ) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "child" 1
    }
}

function Download-ApprovedGoArchive {
    param([string]$Destination)

    $downloadSucceeded = $false
    $handler = $null
    $client = $null
    $response = $null
    $networkStream = $null
    $fileStream = $null
    try {
        Add-Type -AssemblyName System.Net.Http
        $handler = New-Object System.Net.Http.HttpClientHandler
        $handler.AllowAutoRedirect = $false
        $client = New-Object System.Net.Http.HttpClient($handler)
        $client.Timeout = [TimeSpan]::FromMinutes(10)
        $response = $client.GetAsync(
            "https://dl.google.com/go/go1.25.11.windows-amd64.zip",
            [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead
        ).GetAwaiter().GetResult()
        if ($response.StatusCode -ne [System.Net.HttpStatusCode]::OK) {
            throw "approved source returned a non-success status"
        }
        $networkStream = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
        $fileStream = New-Object System.IO.FileStream(
            $Destination,
            [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write,
            [System.IO.FileShare]::None
        )
        $networkStream.CopyTo($fileStream)
        $fileStream.Flush($true)
        $downloadSucceeded = $true
    }
    catch {
        $downloadSucceeded = $false
    }
    finally {
        if ($null -ne $fileStream) {
            $fileStream.Dispose()
        }
        if ($null -ne $networkStream) {
            $networkStream.Dispose()
        }
        if ($null -ne $response) {
            $response.Dispose()
        }
        if ($null -ne $client) {
            $client.Dispose()
        }
        if ($null -ne $handler) {
            $handler.Dispose()
        }
    }
    if (-not $downloadSucceeded) {
        Throw-PatchedBootstrapFailure "VERIFY-GO-ARCHIVE" "operational" 2
    }
}

function Test-PatchedPathWithin {
    param(
        [string]$Root,
        [string]$Candidate
    )

    $rootPath = [System.IO.Path]::GetFullPath($Root).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
    $candidatePath = [System.IO.Path]::GetFullPath($Candidate)
    $rootPrefix = $rootPath + [System.IO.Path]::DirectorySeparatorChar
    return (
        $candidatePath -ceq $rootPath -or
        $candidatePath.StartsWith(
            $rootPrefix,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    )
}

function Resolve-PatchedCanonicalComparisonPath {
    param([string]$Path)

    try {
        Initialize-PatchedJobSupport
        $fullPath = [System.IO.Path]::GetFullPath($Path)
        $missingSegments = New-Object System.Collections.Generic.List[string]
        $existingPath = $fullPath
        while (-not (Test-Path -LiteralPath $existingPath)) {
            $leaf = [System.IO.Path]::GetFileName($existingPath)
            if ([string]::IsNullOrEmpty($leaf)) {
                Throw-PatchedBootstrapFailure $script:CurrentStep "invalid" 2
            }
            $missingSegments.Insert(0, $leaf)
            $parent = [System.IO.Path]::GetDirectoryName($existingPath)
            if ([string]::IsNullOrEmpty($parent) -or $parent -ceq $existingPath) {
                Throw-PatchedBootstrapFailure $script:CurrentStep "invalid" 2
            }
            $existingPath = $parent
        }
        $canonicalPath = [SejongPatchedBootstrap.NativePath]::GetFinalPath(
            $existingPath
        )
        foreach ($segment in $missingSegments) {
            $canonicalPath = [System.IO.Path]::Combine($canonicalPath, $segment)
        }
        return [System.IO.Path]::GetFullPath($canonicalPath)
    }
    catch {
        if (
            $_.Exception.Data.Contains("PatchedBootstrapFailure") -and
            [bool]$_.Exception.Data["PatchedBootstrapFailure"]
        ) {
            throw $_.Exception
        }
        Throw-PatchedBootstrapFailure $script:CurrentStep "invalid" 2
    }
}

function Get-VerifiedGoToolchain {
    param([string]$ArchiveOverride)

    $script:CurrentStep = "VERIFY-GO-ARCHIVE"
    Write-PatchedStatus "[START] step=VERIFY-GO-ARCHIVE"
    $archivePath = $null
    $ownedArchive = $false
    if (-not [string]::IsNullOrEmpty($ArchiveOverride)) {
        try {
            $archivePath = [System.IO.Path]::GetFullPath($ArchiveOverride)
        }
        catch {
            Throw-PatchedBootstrapFailure $script:CurrentStep "invalid" 2
        }
        if (-not (Test-Path -LiteralPath $archivePath -PathType Leaf)) {
            Throw-PatchedBootstrapFailure $script:CurrentStep "missing" 2
        }
        $canonicalArchivePath = Resolve-PatchedCanonicalComparisonPath $archivePath
        foreach ($mutableChild in @(
            "cache",
            "go",
            "s",
            "supabase-source",
            "supabase-build",
            "supabase"
        )) {
            $mutableRoot = Resolve-SafeChildPath $script:ToolRoot $mutableChild
            $canonicalMutableRoot = Resolve-PatchedCanonicalComparisonPath $mutableRoot
            if (Test-PatchedPathWithin $canonicalMutableRoot $canonicalArchivePath) {
                Throw-PatchedBootstrapFailure $script:CurrentStep "invalid" 2
            }
        }
    }
    else {
        $cacheDirectory = Resolve-SafeChildPath $script:ToolRoot "cache"
        $archivePath = Resolve-SafeChildPath $script:ToolRoot "cache/go1.25.11.windows-amd64.zip"
        $ownedArchive = $true
        if (-not (Test-Path -LiteralPath $archivePath -PathType Leaf)) {
            $null = [System.IO.Directory]::CreateDirectory($cacheDirectory)
            $temporaryArchive = Resolve-SafeChildPath $script:ToolRoot (
                "cache/.go1.25.11.windows-amd64-$PID.download"
            )
            Remove-OwnedPath $script:ToolRoot $temporaryArchive
            try {
                Download-ApprovedGoArchive $temporaryArchive
                $temporaryHash = Get-PatchedSha256 $temporaryArchive $script:CurrentStep
                if (
                    $temporaryHash -cne
                    "b7401f1b41517428e537493316256fb7cf03c66a130a0103ab07f3a2152e2112"
                ) {
                    Throw-PatchedBootstrapFailure $script:CurrentStep "integrity" 1
                }
                [System.IO.File]::Move($temporaryArchive, $archivePath)
            }
            finally {
                if (Test-Path -LiteralPath $temporaryArchive) {
                    Remove-OwnedPath $script:ToolRoot $temporaryArchive
                }
            }
        }
    }

    $archiveHash = Get-PatchedSha256 $archivePath $script:CurrentStep
    if (
        $archiveHash -cne
        "b7401f1b41517428e537493316256fb7cf03c66a130a0103ab07f3a2152e2112"
    ) {
        if ($ownedArchive) {
            Remove-OwnedPath $script:ToolRoot $archivePath
        }
        Throw-PatchedBootstrapFailure $script:CurrentStep "integrity" 1
    }
    Write-PatchedStatus "[PASS] step=VERIFY-GO-ARCHIVE"

    $script:CurrentStep = "VERIFY-GO-TOOLCHAIN"
    Write-PatchedStatus "[START] step=VERIFY-GO-TOOLCHAIN"
    $goParent = Resolve-SafeChildPath $script:ToolRoot "go/1.25.11"
    $goRoot = Resolve-SafeChildPath $script:ToolRoot "go/1.25.11/windows-amd64"
    $extractRoot = Resolve-SafeChildPath $script:ToolRoot (
        "go/1.25.11/.extract-$PID"
    )
    Remove-OwnedPath $script:ToolRoot $goRoot
    Remove-OwnedPath $script:ToolRoot $extractRoot
    $null = [System.IO.Directory]::CreateDirectory($goParent)
    $null = [System.IO.Directory]::CreateDirectory($extractRoot)
    try {
        Expand-Archive -LiteralPath $archivePath -DestinationPath $extractRoot
        $entries = @(Get-ChildItem -LiteralPath $extractRoot -Force)
        if (
            $entries.Count -ne 1 -or
            $entries[0].Name -cne "go" -or
            -not $entries[0].PSIsContainer
        ) {
            Throw-PatchedBootstrapFailure $script:CurrentStep "integrity" 1
        }
        Move-Item -LiteralPath $entries[0].FullName -Destination $goRoot
    }
    catch {
        if (
            $_.Exception.Data.Contains("PatchedBootstrapFailure") -and
            [bool]$_.Exception.Data["PatchedBootstrapFailure"]
        ) {
            throw $_.Exception
        }
        Throw-PatchedBootstrapFailure $script:CurrentStep "operational" 2
    }
    finally {
        if (Test-Path -LiteralPath $extractRoot) {
            Remove-OwnedPath $script:ToolRoot $extractRoot
        }
    }

    $goExecutable = Resolve-SafeChildPath $goRoot "bin/go.exe"
    if (-not (Test-Path -LiteralPath $goExecutable -PathType Leaf)) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "missing" 2
    }
    $versionResult = Invoke-PatchedChild $goExecutable @("version") $script:RepositoryRoot 15000
    if (
        $versionResult.TimedOut -or
        $versionResult.ExitCode -ne 0 -or
        $versionResult.Stdout -cnotmatch "go1\.25\.11 windows/amd64"
    ) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "child" 1
    }
    Write-PatchedStatus "[PASS] step=VERIFY-GO-TOOLCHAIN"
    return $goExecutable
}

function Get-PatchedGitExecutable {
    try {
        $gitApplications = @(
            Get-Command git.exe -CommandType Application -ErrorAction Stop
        )
    }
    catch {
        Throw-PatchedBootstrapFailure $script:CurrentStep "operational" 2
    }
    if ($gitApplications.Count -lt 1) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "operational" 2
    }

    $gitSource = $gitApplications[0].Source
    if (
        -not ($gitSource -is [string]) -or
        [string]::IsNullOrWhiteSpace($gitSource) -or
        -not [System.IO.Path]::IsPathRooted($gitSource)
    ) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "operational" 2
    }
    try {
        $gitPath = [System.IO.Path]::GetFullPath($gitSource)
    }
    catch {
        Throw-PatchedBootstrapFailure $script:CurrentStep "operational" 2
    }
    if (-not (Test-Path -LiteralPath $gitPath -PathType Leaf)) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "operational" 2
    }
    return [string]$gitPath
}

function Invoke-VerifiedGit {
    param(
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [int]$TimeoutMilliseconds
    )

    $result = Invoke-PatchedChild $script:GitExecutable $Arguments $WorkingDirectory $TimeoutMilliseconds
    Assert-PatchedChildSuccess $result $script:CurrentStep
    return $result
}

function New-VerifiedSupabaseCheckout {
    param(
        [string]$Destination,
        [int]$MaxTrackedRelativeFilePathLength,
        [int]$MaxAbsoluteFilePathLength
    )

    $checkout = Assert-PatchedCheckoutPathBudget (
        $Destination
    ) $MaxTrackedRelativeFilePathLength $MaxAbsoluteFilePathLength
    Remove-OwnedPath $script:ToolRoot $checkout
    $null = [System.IO.Directory]::CreateDirectory($checkout)

    $null = Invoke-VerifiedGit @("-c", "core.autocrlf=false", "init", "--quiet", ".") $checkout 30000
    $null = Invoke-VerifiedGit @("config", "--local", "core.autocrlf", "false") $checkout 30000
    $null = Invoke-VerifiedGit @("config", "--local", "core.longpaths", "true") $checkout 30000
    $null = Invoke-VerifiedGit @(
        "remote", "add", "origin", "https://github.com/supabase/cli.git"
    ) $checkout 30000
    $remoteNames = Invoke-VerifiedGit @("remote") $checkout 30000
    $names = @($remoteNames.Stdout -split "\r?\n" | Where-Object { $_ -cne "" })
    if ($names.Count -ne 1 -or $names[0] -cne "origin") {
        Throw-PatchedBootstrapFailure $script:CurrentStep "integrity" 1
    }
    $remoteUrls = Invoke-VerifiedGit @("remote", "get-url", "--all", "origin") $checkout 30000
    $urls = @($remoteUrls.Stdout -split "\r?\n" | Where-Object { $_ -cne "" })
    if (
        $urls.Count -ne 1 -or
        $urls[0] -cne "https://github.com/supabase/cli.git"
    ) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "integrity" 1
    }

    $null = Invoke-VerifiedGit @(
        "fetch",
        "--quiet",
        "--depth=1",
        "--filter=blob:none",
        "origin",
        "refs/tags/v2.109.1:refs/tags/v2.109.1"
    ) $checkout 300000
    $tagType = Invoke-VerifiedGit @("cat-file", "-t", "refs/tags/v2.109.1") $checkout 30000
    $tagObject = Invoke-VerifiedGit @(
        "rev-parse", "--verify", "refs/tags/v2.109.1"
    ) $checkout 30000
    $peeledCommit = Invoke-VerifiedGit @(
        "rev-parse", "--verify", "refs/tags/v2.109.1^{}"
    ) $checkout 30000
    if (
        $tagType.Stdout.Trim() -cne "tag" -or
        $tagObject.Stdout.Trim() -cne "9d25ff8b5b0fba3c6f0ef000e7dd658c8d710c38" -or
        $peeledCommit.Stdout.Trim() -cne "6d4c19870ed213ba7f682f117d0345c8a40bfa94"
    ) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "integrity" 1
    }
    $null = Invoke-VerifiedGit @(
        "checkout",
        "--quiet",
        "--detach",
        "6d4c19870ed213ba7f682f117d0345c8a40bfa94"
    ) $checkout 120000
    $head = Invoke-VerifiedGit @("rev-parse", "--verify", "HEAD") $checkout 30000
    if (
        $head.Stdout.Trim() -cne
        "6d4c19870ed213ba7f682f117d0345c8a40bfa94"
    ) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "integrity" 1
    }
    return $checkout
}

function Assert-ExactPatchedDiff {
    param([string]$Checkout)

    $diffNames = Invoke-VerifiedGit @("diff", "--name-only") $Checkout 30000
    $actualNames = @(
        $diffNames.Stdout -split "\r?\n" |
            Where-Object { $_ -cne "" } |
            Sort-Object
    )
    $expectedNames = @(
        "apps/cli-go/internal/db/start/start.go",
        "apps/cli-go/internal/db/start/start_test.go"
    )
    if (
        $actualNames.Count -ne 2 -or
        $actualNames[0] -cne $expectedNames[0] -or
        $actualNames[1] -cne $expectedNames[1]
    ) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "integrity" 1
    }
    $null = Invoke-VerifiedGit @("diff", "--check") $Checkout 30000
}

function Apply-And-TestSupabasePatch {
    param(
        [string]$Checkout,
        [bool]$RequireRed
    )

    $testFile = "apps/cli-go/internal/db/start/start_test.go"
    $productionFile = "apps/cli-go/internal/db/start/start.go"
    if ($RequireRed) {
        $script:CurrentStep = "TEST-PATCHED-SUPABASE-RED"
        Write-PatchedStatus "[START] step=TEST-PATCHED-SUPABASE-RED"
        $null = Invoke-VerifiedGit @(
            "apply", "--check", "--include=$testFile", $script:PatchPath
        ) $Checkout 30000
        $null = Invoke-VerifiedGit @(
            "apply", "--include=$testFile", $script:PatchPath
        ) $Checkout 30000
        $goWorkingDirectory = Resolve-SafeChildPath $Checkout "apps/cli-go"
        $redResult = Invoke-PatchedChild $script:GoExecutable @(
            "test",
            "-json",
            "./internal/db/start",
            "-run",
            "^TestNewHostConfigBindsDatabaseToIPv4Loopback$",
            "-count=1"
        ) $goWorkingDirectory 900000
        $sawExpectedFailure = $false
        foreach ($line in @($redResult.Stdout -split "\r?\n")) {
            if ([string]::IsNullOrWhiteSpace($line)) {
                continue
            }
            try {
                $event = $line | ConvertFrom-Json
                if (
                    $event.Action -ceq "fail" -and
                    $event.Test -ceq
                    "TestNewHostConfigBindsDatabaseToIPv4Loopback"
                ) {
                    $sawExpectedFailure = $true
                }
            }
            catch {
            }
        }
        if (
            $redResult.TimedOut -or
            $redResult.ExitCode -eq 0 -or
            -not $sawExpectedFailure
        ) {
            Throw-PatchedBootstrapFailure $script:CurrentStep "child" 1
        }
        Write-PatchedStatus "[PASS] step=TEST-PATCHED-SUPABASE-RED"

        $script:CurrentStep = "TEST-PATCHED-SUPABASE-GREEN"
        Write-PatchedStatus "[START] step=TEST-PATCHED-SUPABASE-GREEN"
        $null = Invoke-VerifiedGit @(
            "apply", "--check", "--include=$productionFile", $script:PatchPath
        ) $Checkout 30000
        $null = Invoke-VerifiedGit @(
            "apply", "--include=$productionFile", $script:PatchPath
        ) $Checkout 30000
        Assert-ExactPatchedDiff $Checkout
        $focusedGreen = Invoke-PatchedChild $script:GoExecutable @(
            "test",
            "./internal/db/start",
            "-run",
            "^TestNewHostConfigBindsDatabaseToIPv4Loopback$",
            "-count=1"
        ) $goWorkingDirectory 900000
        Assert-PatchedChildSuccess $focusedGreen $script:CurrentStep
        $fullGreen = Invoke-PatchedChild $script:GoExecutable @(
            "test", "./internal/db/start", "-count=1"
        ) $goWorkingDirectory 900000
        Assert-PatchedChildSuccess $fullGreen $script:CurrentStep
        Write-PatchedStatus "[PASS] step=TEST-PATCHED-SUPABASE-GREEN"
    }
    else {
        $null = Invoke-VerifiedGit @(
            "apply",
            "--check",
            "--include=$testFile",
            "--include=$productionFile",
            $script:PatchPath
        ) $Checkout 30000
        $null = Invoke-VerifiedGit @(
            "apply",
            "--include=$testFile",
            "--include=$productionFile",
            $script:PatchPath
        ) $Checkout 30000
        Assert-ExactPatchedDiff $Checkout
    }
}

function Build-PatchedSupabase {
    param(
        [string]$Checkout,
        [string]$Output
    )

    $outputPath = Resolve-SafeChildPath $script:ToolRoot $Output
    $outputDirectory = Split-Path -Parent $outputPath
    $null = [System.IO.Directory]::CreateDirectory($outputDirectory)
    if (Test-Path -LiteralPath $outputPath) {
        Remove-OwnedPath $script:ToolRoot $outputPath
    }
    $goWorkingDirectory = Resolve-SafeChildPath $Checkout "apps/cli-go"
    $buildResult = Invoke-PatchedChild $script:GoExecutable @(
        "build",
        "-trimpath",
        "-buildvcs=false",
        "-ldflags",
        "-s -w -X github.com/supabase/cli/internal/utils.Version=2.109.1",
        "-o",
        $outputPath,
        "main.go"
    ) $goWorkingDirectory 900000
    Assert-PatchedChildSuccess $buildResult $script:CurrentStep
    Test-PatchedSupabaseVersion $outputPath
    return $outputPath
}

function Assert-InstalledPatchedBinary {
    param([object]$RuntimeManifest)

    $binaryPath = Resolve-SafeChildPath $script:RepositoryRoot $RuntimeManifest.relative_path
    if (-not (Test-Path -LiteralPath $binaryPath -PathType Leaf)) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "missing" 2
    }
    $binaryHash = Get-PatchedSha256 $binaryPath $script:CurrentStep
    if ($binaryHash -cne $RuntimeManifest.sha256) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "integrity" 1
    }
    Test-PatchedSupabaseVersion $binaryPath
}

function Replace-PatchedFileWithBackup {
    param(
        [string]$Source,
        [string]$Destination,
        [string]$Backup
    )

    [System.IO.File]::Replace($Source, $Destination, $Backup, $true)
}

function Restore-PatchedFileFromBackup {
    param(
        [string]$Backup,
        [string]$Destination
    )

    [System.IO.File]::Replace($Backup, $Destination, $null, $true)
}

function Install-PatchedSupabaseBinary {
    param(
        [string]$Candidate,
        [object]$RuntimeManifest
    )

    $candidateHash = Get-PatchedSha256 $Candidate $script:CurrentStep
    if ($candidateHash -cne $RuntimeManifest.sha256) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "integrity" 1
    }
    $finalPath = Resolve-SafeChildPath $script:RepositoryRoot $RuntimeManifest.relative_path
    $finalDirectory = Split-Path -Parent $finalPath
    if (
        (Test-Path -LiteralPath $finalPath) -and
        -not (Test-Path -LiteralPath $finalPath -PathType Leaf)
    ) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "invalid" 2
    }
    $null = [System.IO.Directory]::CreateDirectory($finalDirectory)
    $backupPath = Resolve-SafeChildPath $script:ToolRoot (
        "supabase/.v2.109.1-sejong-loopback-$PID.backup"
    )
    if (Test-Path -LiteralPath $backupPath) {
        Remove-OwnedPath $script:ToolRoot $backupPath
    }
    $hadExisting = Test-Path -LiteralPath $finalPath -PathType Leaf
    $replacementCompleted = $false
    $preserveBackup = $false
    try {
        if ($hadExisting) {
            Replace-PatchedFileWithBackup $Candidate $finalPath $backupPath
        }
        else {
            [System.IO.File]::Move($Candidate, $finalPath)
        }
        $replacementCompleted = $true
        Assert-InstalledPatchedBinary $RuntimeManifest
    }
    catch {
        $installFailure = $_.Exception
        if (-not $replacementCompleted) {
            if (Test-Path -LiteralPath $backupPath -PathType Leaf) {
                $preserveBackup = $true
            }
            throw $installFailure
        }

        $rollbackRestored = $false
        if ($hadExisting) {
            if (Test-Path -LiteralPath $backupPath -PathType Leaf) {
                try {
                    Restore-PatchedFileFromBackup $backupPath $finalPath
                    $rollbackRestored = $true
                }
                catch {
                    $preserveBackup = $true
                }
            }
        }
        else {
            try {
                if (Test-Path -LiteralPath $finalPath) {
                    Remove-OwnedPath $script:ToolRoot $finalPath
                }
                $rollbackRestored = -not (Test-Path -LiteralPath $finalPath)
            }
            catch {
                $rollbackRestored = $false
            }
        }
        if (-not $rollbackRestored) {
            Throw-PatchedBootstrapFailure "INSTALL-PATCHED-SUPABASE" "operational" 2
        }
        throw $installFailure
    }
    finally {
        if (-not $preserveBackup -and (Test-Path -LiteralPath $backupPath)) {
            Remove-OwnedPath $script:ToolRoot $backupPath
        }
    }
}

$script:CurrentStep = "VALIDATE-PATCHED-SUPABASE-ARGUMENTS"
$script:RepositoryRoot = $null
$script:ToolRoot = $null
$script:PatchPath = $null
$script:GoExecutable = $null
$script:GitExecutable = $null
$script:LastPatchedJsonRaw = $null

try {
    $mode = $null
    $goArchivePath = $null
    $sawGoArchivePath = $false
    for ($index = 0; $index -lt $args.Count; $index += 1) {
        $argument = [string]$args[$index]
        switch -CaseSensitive ($argument) {
            "-BuildCandidate" {
                if ($null -ne $mode) {
                    Throw-PatchedBootstrapFailure $script:CurrentStep "invalid" 2
                }
                $mode = "BuildCandidate"
            }
            "-Install" {
                if ($null -ne $mode) {
                    Throw-PatchedBootstrapFailure $script:CurrentStep "invalid" 2
                }
                $mode = "Install"
            }
            "-VerifyOnly" {
                if ($null -ne $mode) {
                    Throw-PatchedBootstrapFailure $script:CurrentStep "invalid" 2
                }
                $mode = "VerifyOnly"
            }
            "-GoArchivePath" {
                if ($sawGoArchivePath -or $index + 1 -ge $args.Count) {
                    Throw-PatchedBootstrapFailure $script:CurrentStep "invalid" 2
                }
                $candidateValue = [string]$args[$index + 1]
                if (
                    [string]::IsNullOrWhiteSpace($candidateValue) -or
                    $candidateValue.StartsWith("-")
                ) {
                    Throw-PatchedBootstrapFailure $script:CurrentStep "invalid" 2
                }
                $sawGoArchivePath = $true
                $goArchivePath = $candidateValue
                $index += 1
            }
            default {
                Throw-PatchedBootstrapFailure $script:CurrentStep "invalid" 2
            }
        }
    }
    if ($null -eq $mode -or ($mode -ceq "VerifyOnly" -and $sawGoArchivePath)) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "invalid" 2
    }

    $script:RepositoryRoot = [System.IO.Path]::GetFullPath(
        (Split-Path -Parent $PSScriptRoot)
    )
    $sourceManifestPath = Join-Path $PSScriptRoot "supabase-cli.local-patch.source.json"
    $script:CurrentStep = "LOAD-PATCHED-SUPABASE-SOURCE-MANIFEST"
    $sourceManifest = Read-PatchedJson $sourceManifestPath $script:CurrentStep
    $script:CurrentStep = "VALIDATE-PATCHED-SUPABASE-SOURCE-MANIFEST"
    Assert-ExactSourceManifest $sourceManifest
    $sourceManifestHash = Get-PatchedSha256 $sourceManifestPath $script:CurrentStep

    $script:CurrentStep = "VERIFY-PATCHED-SUPABASE-PATCH"
    $script:PatchPath = Resolve-SafeChildPath (
        $script:RepositoryRoot
    ) $sourceManifest.patch.relative_path
    if (-not (Test-Path -LiteralPath $script:PatchPath -PathType Leaf)) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "missing" 2
    }
    $patchItem = Get-Item -LiteralPath $script:PatchPath -Force
    $patchHash = Get-PatchedSha256 $script:PatchPath $script:CurrentStep
    if (
        $patchItem.Length -ne 1824 -or
        $patchHash -cne
        "109c096480e8185d761e9ce8fba10e93efc55190c42eab978f769a6993833f7d"
    ) {
        Throw-PatchedBootstrapFailure $script:CurrentStep "integrity" 1
    }

    $runtimeManifest = $null
    if ($mode -ceq "VerifyOnly" -or $mode -ceq "Install") {
        $script:CurrentStep = "LOAD-PATCHED-SUPABASE-RUNTIME-MANIFEST"
        $runtimeManifestPath = Join-Path (
            $PSScriptRoot
        ) "supabase-cli.local-patch.runtime.json"
        $runtimeManifest = Read-PatchedJson $runtimeManifestPath $script:CurrentStep
        Assert-ExactRuntimeManifest $runtimeManifest $sourceManifestHash
    }

    if ($mode -ceq "VerifyOnly") {
        $script:CurrentStep = "VERIFY-PATCHED-SUPABASE-BINARY"
        Write-PatchedStatus "[START] step=VERIFY-PATCHED-SUPABASE-BINARY"
        Assert-InstalledPatchedBinary $runtimeManifest
        Write-PatchedStatus "[PASS] step=VERIFY-PATCHED-SUPABASE-BINARY"
        exit 0
    }

    $script:ToolRoot = Resolve-SafeChildPath $script:RepositoryRoot ".tools"
    $script:CurrentStep = "VALIDATE-PATCHED-SUPABASE-CHECKOUT-WORKSPACE"
    Write-PatchedStatus (
        "[START] step=VALIDATE-PATCHED-SUPABASE-CHECKOUT-WORKSPACE"
    )
    $null = Assert-PatchedCheckoutPathBudget (
        $sourceManifest.workspace.checkout_a
    ) $sourceManifest.workspace.max_tracked_relative_file_path_length (
        $sourceManifest.workspace.max_absolute_file_path_length
    )
    $null = Assert-PatchedCheckoutPathBudget (
        $sourceManifest.workspace.checkout_b
    ) $sourceManifest.workspace.max_tracked_relative_file_path_length (
        $sourceManifest.workspace.max_absolute_file_path_length
    )
    Write-PatchedStatus (
        "[PASS] step=VALIDATE-PATCHED-SUPABASE-CHECKOUT-WORKSPACE"
    )
    $goEnvironmentNames = @(
        "GOOS",
        "GOARCH",
        "GOAMD64",
        "CGO_ENABLED",
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
        "GOEXPERIMENT"
    )
    $savedGoEnvironment = @{}
    foreach ($name in $goEnvironmentNames) {
        $savedGoEnvironment[$name] = [System.Environment]::GetEnvironmentVariable(
            $name,
            [System.EnvironmentVariableTarget]::Process
        )
    }
    try {
        $pinnedGoEnvironment = @{
            GOOS = "windows"
            GOARCH = "amd64"
            GOAMD64 = "v1"
            CGO_ENABLED = "0"
            GOPROXY = "https://proxy.golang.org"
            GOSUMDB = "sum.golang.org"
            GOPRIVATE = ""
            GONOPROXY = ""
            GONOSUMDB = ""
            GOINSECURE = ""
            GOENV = "off"
            GOWORK = "off"
            GOTOOLCHAIN = "local"
            GOFLAGS = ""
            GOEXPERIMENT = ""
        }
        foreach ($name in $goEnvironmentNames) {
            [System.Environment]::SetEnvironmentVariable(
                $name,
                [string]$pinnedGoEnvironment[$name],
                [System.EnvironmentVariableTarget]::Process
            )
        }

        $script:GoExecutable = Get-VerifiedGoToolchain $goArchivePath
        $script:CurrentStep = "VERIFY-SUPABASE-SOURCE-A"
        Write-PatchedStatus "[START] step=VERIFY-SUPABASE-SOURCE-A"
        $script:GitExecutable = Get-PatchedGitExecutable
        $checkoutA = New-VerifiedSupabaseCheckout (
            $sourceManifest.workspace.checkout_a
        ) $sourceManifest.workspace.max_tracked_relative_file_path_length (
            $sourceManifest.workspace.max_absolute_file_path_length
        )
        Write-PatchedStatus "[PASS] step=VERIFY-SUPABASE-SOURCE-A"

        $script:CurrentStep = "VERIFY-SUPABASE-SOURCE-B"
        Write-PatchedStatus "[START] step=VERIFY-SUPABASE-SOURCE-B"
        $checkoutB = New-VerifiedSupabaseCheckout (
            $sourceManifest.workspace.checkout_b
        ) $sourceManifest.workspace.max_tracked_relative_file_path_length (
            $sourceManifest.workspace.max_absolute_file_path_length
        )
        Write-PatchedStatus "[PASS] step=VERIFY-SUPABASE-SOURCE-B"

        Apply-And-TestSupabasePatch $checkoutA $true
        Apply-And-TestSupabasePatch $checkoutB $false

        $script:CurrentStep = "VERIFY-PATCHED-SUPABASE-MODULES"
        Write-PatchedStatus "[START] step=VERIFY-PATCHED-SUPABASE-MODULES"
        foreach ($checkout in @($checkoutA, $checkoutB)) {
            $workingDirectory = Resolve-SafeChildPath $checkout "apps/cli-go"
            $moduleResult = Invoke-PatchedChild $script:GoExecutable @("mod", "verify") (
                $workingDirectory
            ) 900000
            Assert-PatchedChildSuccess $moduleResult $script:CurrentStep
        }
        Write-PatchedStatus "[PASS] step=VERIFY-PATCHED-SUPABASE-MODULES"

        $script:CurrentStep = "BUILD-PATCHED-SUPABASE-A"
        Write-PatchedStatus "[START] step=BUILD-PATCHED-SUPABASE-A"
        $outputA = Build-PatchedSupabase (
            $checkoutA
        ) "supabase-build/supabase-v2.109.1-sejong-loopback-a.exe"
        Write-PatchedStatus "[PASS] step=BUILD-PATCHED-SUPABASE-A"

        $script:CurrentStep = "BUILD-PATCHED-SUPABASE-B"
        Write-PatchedStatus "[START] step=BUILD-PATCHED-SUPABASE-B"
        $outputB = Build-PatchedSupabase (
            $checkoutB
        ) "supabase-build/supabase-v2.109.1-sejong-loopback-b.exe"
        Write-PatchedStatus "[PASS] step=BUILD-PATCHED-SUPABASE-B"

        $script:CurrentStep = "VERIFY-PATCHED-SUPABASE-REPRODUCIBILITY"
        Write-PatchedStatus "[START] step=VERIFY-PATCHED-SUPABASE-REPRODUCIBILITY"
        $hashA = Get-PatchedSha256 $outputA $script:CurrentStep
        $hashB = Get-PatchedSha256 $outputB $script:CurrentStep
        if ($hashA -cne $hashB -or $hashA -cnotmatch "^[0-9a-f]{64}$") {
            Throw-PatchedBootstrapFailure $script:CurrentStep "integrity" 1
        }
        Write-PatchedStatus "[PASS] step=VERIFY-PATCHED-SUPABASE-REPRODUCIBILITY"

        if ($mode -ceq "BuildCandidate") {
            $script:CurrentStep = "BUILD-PATCHED-SUPABASE-CANDIDATE"
            Write-PatchedStatus (
                "[PASS] step=BUILD-PATCHED-SUPABASE-CANDIDATE sha256=$hashA"
            )
        }
        else {
            $script:CurrentStep = "INSTALL-PATCHED-SUPABASE"
            Write-PatchedStatus "[START] step=INSTALL-PATCHED-SUPABASE"
            Install-PatchedSupabaseBinary $outputA $runtimeManifest
            Write-PatchedStatus "[PASS] step=INSTALL-PATCHED-SUPABASE"

            $script:CurrentStep = "VERIFY-PATCHED-SUPABASE-BINARY"
            Write-PatchedStatus "[START] step=VERIFY-PATCHED-SUPABASE-BINARY"
            Assert-InstalledPatchedBinary $runtimeManifest
            Write-PatchedStatus "[PASS] step=VERIFY-PATCHED-SUPABASE-BINARY"
        }
    }
    finally {
        foreach ($name in $goEnvironmentNames) {
            [System.Environment]::SetEnvironmentVariable(
                $name,
                $savedGoEnvironment[$name],
                [System.EnvironmentVariableTarget]::Process
            )
        }
    }
    exit 0
}
catch {
    $failure = $_.Exception
    if (
        $failure.Data.Contains("PatchedBootstrapFailure") -and
        [bool]$failure.Data["PatchedBootstrapFailure"]
    ) {
        $step = [string]$failure.Data["Step"]
        $reason = [string]$failure.Data["Reason"]
        $code = [int]$failure.Data["Code"]
    }
    else {
        $step = $script:CurrentStep
        $reason = "operational"
        $code = 2
    }
    Write-PatchedStatus "[FAIL] step=$step reason=$reason code=$code"
    exit $code
}
