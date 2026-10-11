<#
.SYNOPSIS
  M10-E4 (B6): rebuild QtCore 6.11.2 from the delivered source with one visible
  modification, place it in a COPY of a frozen bundle and verify the copy runs.

.DESCRIPTION
  Engineering experiment only. It never installs a toolchain, accepts a licence,
  downloads anything, edits the original bundle or publishes output. When a
  prerequisite is missing it stops with exit code 3 and names the owner action.

  Owner prerequisite (not performed by this script): Visual Studio 2022 Build
  Tools with the MSVC v143 14.44 toolset (cl 19.44, as recorded in the official
  Qt 6.11.2 build SBOM) and a Windows 11 SDK, installed and licence-accepted by
  the owner. CMake >= 3.30.5 and Ninja must be on PATH; run from a
  "x64 Native Tools" prompt so cl.exe and the SDK are on PATH.

.EXAMPLE
  powershell -File tools\m10\e4_modified_qt.ps1 -SourceArchive X:\src\qtbase-everywhere-src-6.11.2.tar.xz `
    -Bundle X:\sti-build\dist\sti-desktop -Work X:\e4 -BuildPython X:\venv\Scripts\python.exe
#>
param(
  [Parameter(Mandatory)] [string] $SourceArchive,
  [Parameter(Mandatory)] [string] $Bundle,
  [Parameter(Mandatory)] [string] $Work,
  [Parameter(Mandatory)] [string] $BuildPython,
  [switch] $CheckOnly
)
$ErrorActionPreference = 'Stop'
$QtBaseSha256 = '5b2e00eccaf5a4d8c14134ffa0ea8dfd0a35ae1ffc7f8d87fa4305a1ed23cf22'
$Original = '" build; by " COMPILER_STRING ")";'
$Modified = '" build, STI-E4-MODIFIED; by " COMPILER_STRING ")";'
$Marker = 'STI-E4-MODIFIED'

function Stop-Prerequisite([string] $Message) {
  Write-Output "E4 prerequisite missing: $Message"
  Write-Output 'Owner action: install Visual Studio 2022 Build Tools (MSVC v143 14.44, Windows 11 SDK) and accept its licence; this script never does so.'
  exit 3
}

# 1. Prerequisites — read-only checks, nothing is created before they pass.
$cl = Get-Command cl.exe -ErrorAction SilentlyContinue
if (-not $cl) { Stop-Prerequisite 'cl.exe (MSVC) is not on PATH.' }
$banner = (& cl.exe 2>&1 | Select-Object -First 1) -join ''
if ($banner -notmatch 'Version 19\.44\.') { Stop-Prerequisite "cl.exe is not MSVC 19.44 ($banner)." }
foreach ($tool in 'cmake.exe', 'ninja.exe', 'rc.exe') {
  if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { Stop-Prerequisite "$tool is not on PATH." }
}
$cmakeVersion = [version]((& cmake.exe --version | Select-Object -First 1) -replace '[^0-9.]', '')
if ($cmakeVersion -lt [version]'3.30.5') { Stop-Prerequisite "CMake $cmakeVersion is older than 3.30.5." }
if (-not (Test-Path -LiteralPath $SourceArchive -PathType Leaf) -or
    (Get-FileHash -LiteralPath $SourceArchive).Hash.ToLower() -ne $QtBaseSha256) {
  Stop-Prerequisite 'the pinned qtbase-everywhere-src-6.11.2.tar.xz was not found or its SHA-256 differs.'
}
if (-not (Test-Path -LiteralPath (Join-Path $Bundle '_internal\PySide6\Qt6Core.dll'))) {
  Stop-Prerequisite 'the frozen bundle does not contain _internal\PySide6\Qt6Core.dll.'
}
if (Test-Path -LiteralPath $Work) { Stop-Prerequisite 'the work directory already exists; use a new one.' }
if ($CheckOnly) { Write-Output 'E4 prerequisites present.'; exit 0 }

# 2. Source with exactly one modification.
New-Item -ItemType Directory -Path $Work | Out-Null
tar -xf $SourceArchive -C $Work
$source = Join-Path $Work 'qtbase-everywhere-src-6.11.2'
$file = Join-Path $source 'src\corelib\global\qlibraryinfo.cpp'
$text = [IO.File]::ReadAllText($file)
if (([regex]::Matches($text, [regex]::Escape($Original))).Count -ne 1) { throw 'Unexpected qlibraryinfo.cpp; refusing to patch.' }
[IO.File]::WriteAllText($file, $text.Replace($Original, $Modified))

# 3. Release build of QtCore with the SBOM-recorded configure options that affect the ABI.
$build = Join-Path $Work 'build'
New-Item -ItemType Directory -Path $build | Out-Null
Push-Location $build
try {
  & (Join-Path $source 'configure.bat') -release -force-debug-info -nomake examples -nomake tests -qt-zlib -- -DFEATURE_msvc_obj_debug_info=ON
  if ($LASTEXITCODE) { throw 'configure failed.' }
  & cmake.exe --build . --target Core
  if ($LASTEXITCODE) { throw 'QtCore build failed.' }
} finally { Pop-Location }
$rebuilt = Get-ChildItem -LiteralPath $build -Recurse -Filter Qt6Core.dll | Select-Object -First 1
if (-not $rebuilt) { throw 'Rebuilt Qt6Core.dll not found.' }
if (-not (Select-String -LiteralPath $rebuilt.FullName -Pattern $Marker -SimpleMatch -Quiet)) { throw 'Marker missing from rebuilt Qt6Core.dll.' }

# 4. Fresh copy of the bundle with only Qt6Core.dll replaced, then the validation criteria.
$copy = Join-Path $Work 'bundle'
robocopy $Bundle $copy /E /NFL /NDL /NJH /NJS /NP | Out-Null
$target = Join-Path $copy '_internal\PySide6\Qt6Core.dll'
$before = (Get-FileHash -LiteralPath $target).Hash.ToLower()
Copy-Item -LiteralPath $rebuilt.FullName -Destination $target -Force
$after = (Get-FileHash -LiteralPath $target).Hash.ToLower()
if ($before -eq $after) { throw 'The rebuilt library is identical to the shipped one.' }
$results = [ordered]@{ qt6core_before_sha256 = $before; qt6core_after_sha256 = $after }
& $BuildPython (Join-Path $PSScriptRoot 'e4_check.py') (Join-Path $copy '_internal') | Tee-Object -Variable gap | Out-Null
$results.unresolved_qt_imports = ($gap | ConvertFrom-Json).unresolved
$env:TEMP = Join-Path $Work 'tmp'; $env:TMP = $env:TEMP; New-Item -ItemType Directory $env:TEMP | Out-Null
foreach ($mode in '--license-info', '--verify-runtime', '--smoke') {
  $output = & (Join-Path $copy 'sti-check.exe') $mode
  $results[$mode] = [ordered]@{ exit = $LASTEXITCODE; output = ($output -join '') }
}
$results.distribution_permitted = $false
$results | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 (Join-Path $Work 'e4-receipt.json')
$passed = ($results.unresolved_qt_imports -eq 0) -and
  ($results['--license-info'].exit -eq 0) -and ($results['--verify-runtime'].exit -eq 0) -and ($results['--smoke'].exit -eq 0)
Write-Output ("E4 " + $(if ($passed) { 'PASS' } else { 'FAIL' }) + '; receipt: e4-receipt.json')
exit $(if ($passed) { 0 } else { 2 })
