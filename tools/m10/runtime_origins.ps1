# Launch sti-desktop.exe from one application directory and report where each loaded
# Microsoft Visual C++ runtime module came from (M10-E3). Starts and closes only
# the process it launches; changes no files and needs no administrator rights.
# The working directory is a neutral folder, so a copy that is reachable only
# through the current directory cannot pass as correctly placed.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Application,
    [ValidateSet('R1','R2')][string]$Route = 'R2'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Application = [IO.Path]::GetFullPath($Application)
$exe = Join-Path $Application 'sti-desktop.exe'
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw 'sti-desktop.exe is absent.' }
$appLocal = Join-Path $Application '_internal'
$system = Join-Path $env:SystemRoot 'System32'
$required = @('msvcp140.dll','msvcp140_1.dll','msvcp140_2.dll','msvcp140_atomic_wait.dll','vcruntime140.dll','vcruntime140_1.dll')
$pattern = '^(msvcp140|vcruntime140|concrt140|vccorlib140)([_-][0-9a-z_]+)?\.dll$'
$started = Start-Process -FilePath $exe -WorkingDirectory $env:TEMP -WindowStyle Hidden -PassThru
try {
    $window = $null
    for ($attempt = 0; $attempt -lt 150 -and $null -eq $window; $attempt++) {
        Start-Sleep -Milliseconds 200
        $process = Get-Process -Id $started.Id -ErrorAction SilentlyContinue
        if ($null -eq $process) { throw 'sti-desktop.exe exited before showing its window.' }
        if ($process.MainWindowHandle -ne 0 -and $process.MainWindowTitle -like '*Social Text Intelligence*') { $window = $process }
    }
    if ($null -eq $window) { throw 'sti-desktop.exe did not show its window.' }
    $modules = @($window.Modules | Where-Object { $_.ModuleName -match $pattern } | ForEach-Object {
        $folder = [IO.Path]::GetDirectoryName($_.FileName)
        [ordered]@{
            module = $_.ModuleName.ToLowerInvariant()
            location = if ($folder -ieq $appLocal) { 'app-local' } elseif ($folder -ieq $system) { 'system' } else { 'other' }
        }
    })
    $expected = if ($Route -eq 'R2') { 'app-local' } else { 'system' }
    $names = @($modules | ForEach-Object { $_.module } | Sort-Object -Unique)
    $complete = ($null -eq (Compare-Object $names $required))
    $ok = $complete -and -not ($modules | Where-Object { $_.location -ne $expected })
    [ordered]@{
        schema_version = 1; route = $Route; window = $true; working_directory = 'neutral'
        runtime_modules = $modules; required_set_loaded = $complete
        expected_location = $expected; origins_ok = [bool]$ok
    } | ConvertTo-Json -Depth 4
    if (-not $ok) { exit 1 }
} finally {
    $process = Get-Process -Id $started.Id -ErrorAction SilentlyContinue
    if ($null -ne $process) {
        # A close request sent while the window is still initialising can be lost,
        # so it is repeated for up to 15 seconds.
        $closed = $false
        for ($attempt = 0; $attempt -lt 15 -and -not $closed; $attempt++) {
            [void]$process.CloseMainWindow()
            $closed = $process.WaitForExit(1000)
        }
        if (-not $closed) {
            # Only the process this script started is stopped.
            Stop-Process -Id $started.Id -Force
            throw 'sti-desktop.exe did not close and was stopped; inspect it manually.'
        }
    }
}
exit 0
