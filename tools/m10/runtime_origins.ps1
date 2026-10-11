# Launch sti-desktop.exe from one application directory and report where each loaded
# Microsoft Visual C++ runtime module came from (M10-E3). Starts and closes only
# the process it launches; changes no files and needs no administrator rights.
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
$pattern = '^(msvcp140|vcruntime140|concrt140|vccorlib140)([_-][0-9a-z_]+)?\.dll$'
$started = Start-Process -FilePath $exe -WorkingDirectory $Application -WindowStyle Hidden -PassThru
try {
    $window = $null
    for ($attempt = 0; $attempt -lt 150 -and $null -eq $window; $attempt++) {
        Start-Sleep -Milliseconds 200
        $process = Get-Process -Id $started.Id -ErrorAction SilentlyContinue
        if ($null -eq $process) { throw 'sti-desktop.exe exited before showing its window.' }
        if ($process.MainWindowHandle -ne 0) { $window = $process }
    }
    if ($null -eq $window) { throw 'sti-desktop.exe did not show its window.' }
    $modules = @($window.Modules | Where-Object { $_.ModuleName -match $pattern } | ForEach-Object {
        [ordered]@{
            module = $_.ModuleName.ToLowerInvariant()
            from_application = ([IO.Path]::GetDirectoryName($_.FileName) -ieq $Application)
            location = if ([IO.Path]::GetDirectoryName($_.FileName) -ieq $Application) { 'application' }
                       elseif ($_.FileName -like ($env:SystemRoot + '\*')) { 'windows' } else { 'other' }
        }
    })
    $expected = if ($Route -eq 'R2') { 'application' } else { 'windows' }
    $ok = $modules.Count -gt 0 -and -not ($modules | Where-Object { $_.location -ne $expected })
    [ordered]@{
        schema_version = 1; route = $Route; window = $true
        runtime_modules = $modules; expected_location = $expected; origins_ok = [bool]$ok
    } | ConvertTo-Json -Depth 4
    if (-not $ok) { exit 1 }
} finally {
    $process = Get-Process -Id $started.Id -ErrorAction SilentlyContinue
    if ($null -ne $process) {
        [void]$process.CloseMainWindow()
        if (-not $process.WaitForExit(15000)) { throw 'sti-desktop.exe did not close; inspect it manually.' }
    }
}
