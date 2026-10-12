# Run only against a new application/profile namespace. No recursive cleanup.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Installer,
    [Parameter(Mandatory=$true)][string]$Receipt,
    [Parameter(Mandatory=$true)][string]$Output,
    [ValidateSet('DevelopmentHost','DisposableVM')][string]$EnvironmentKind = 'DevelopmentHost',
    # Missing: prove the installer refuses without VC++ 14.44+ and leaves nothing.
    # Present: the full lifecycle on a machine that has the runtime (R1).
    [Parameter(Mandatory=$true)][ValidateSet('Missing','Present')][string]$RuntimeExpectation
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'validate_installer_lib.ps1')

function Hash([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Assert([bool]$Condition, [string]$Message) { if (-not $Condition) { throw $Message } }
function RunProcess([string]$Path, [string[]]$Arguments) {
    $process = Start-Process -FilePath $Path -ArgumentList $Arguments -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(120000)) { throw 'Owned validation process timed out; inspect locally.' }
    return $process.ExitCode
}
function CheckPayload {
    foreach ($entry in $manifest.payload) {
        $path = [IO.Path]::GetFullPath((Join-Path $install $entry.path))
        Assert ($path.StartsWith($install + '\', [StringComparison]::OrdinalIgnoreCase)) 'Receipt path escapes install directory.'
        Assert ((Hash $path) -eq $entry.sha256) 'Installed payload differs from receipt.'
    }
}
function CheckSentinels {
    foreach ($entry in $sentinels) { Assert ((Hash $entry.Path) -eq $entry.Hash) 'Synthetic preservation sentinel changed.' }
}
function Install {
    $code = RunProcess $Installer @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',('/LOG="' + $Output + '\install-private.log"'))
    Assert ($code -eq 0) 'Installation failed; inspect private log.'
    CheckPayload
}
function Uninstall {
    Assert ((Get-Content -LiteralPath (Join-Path $install 'installer\managed.txt') -Raw) -eq 'STI M10-C managed application files v1') 'Managed marker changed.'
    Assert ((Hash (Join-Path $install 'unins000.exe')) -eq $uninstallerHash) 'Uninstaller bytes changed.'
    $code = RunProcess (Join-Path $install 'unins000.exe') @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/LOG="' + $Output + '\uninstall-private.log"'))
    return $code
}

Assert ([Environment]::Is64BitOperatingSystem -and $env:OS -eq 'Windows_NT') 'Windows x64 is required.'
if ($EnvironmentKind -eq 'DisposableVM') {
    Assert (Test-Path -LiteralPath 'C:\STI-M10C-VM.txt' -PathType Leaf) 'Disposable VM marker is required.'
    Assert ((Get-Content -LiteralPath 'C:\STI-M10C-VM.txt' -Raw).Trim() -eq 'STI M10-C disposable Windows validation v1') 'VM marker does not match.'
}
Assert (-not (Test-Path -LiteralPath $Output)) 'Validation output must be new.'
Assert (-not ($Output -match '["\r\n]')) 'Invalid output path.'
$manifest = Get-Content -LiteralPath $Receipt -Raw | ConvertFrom-Json
$facts = Test-StiReceipt $manifest
Assert ((Hash $Installer) -eq $manifest.installer_sha256) 'Installer checksum differs from receipt.'
$runtime = Get-StiVCRuntimeState
Assert-StiRuntimeExpectation $runtime $RuntimeExpectation
$local = [Environment]::GetFolderPath('LocalApplicationData')
$install = [IO.Path]::GetFullPath((Join-Path $local 'Programs\Social Text Intelligence'))
$appData = Join-Path $local 'SocialTextIntelligence'
$menu = Join-Path ([Environment]::GetFolderPath('Programs')) 'Social Text Intelligence'
Assert (-not (Test-Path -LiteralPath $install)) 'Existing installation/data is preserved; use a fresh Windows profile.'
Assert (-not (Test-Path -LiteralPath $appData)) 'Existing project/model data is preserved; use a fresh Windows profile.'
Assert (-not (Test-Path -LiteralPath $menu)) 'Existing Start Menu folder is preserved; use a fresh profile.'
$uninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{DB272C58-19C3-48E1-A88B-040CD5D88E35}_is1'
Assert (-not (Test-Path -LiteralPath $uninstallKey)) 'Existing uninstall registration is preserved; use a fresh profile.'
New-Item -ItemType Directory -Path $Output | Out-Null
$Output = [IO.Path]::GetFullPath($Output)
$savedEnvironment = @{}
foreach ($name in @('PATH','TEMP','TMP','HF_HOME','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','QT_PLUGIN_PATH','QML2_IMPORT_PATH','QT_QPA_PLATFORM')) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
try {
    $env:PATH = $env:SystemRoot + '\System32;' + $env:SystemRoot
    $env:TEMP = Join-Path $Output 'temp'; $env:TMP = $env:TEMP
    New-Item -ItemType Directory -Path $env:TEMP | Out-Null
    $env:HF_HOME = Join-Path $Output 'empty-hub-cache'
    $env:HF_HUB_OFFLINE = '1'; $env:TRANSFORMERS_OFFLINE = '1'
    Remove-Item Env:QT_PLUGIN_PATH,Env:QML2_IMPORT_PATH,Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
    if ($RuntimeExpectation -eq 'Missing') {
        $code = RunProcess $Installer @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',('/LOG="' + $Output + '\install-private.log"'))
        Assert ($code -ne 0) 'Installation was not refused without the required VC++ runtime.'
        foreach ($path in @($install, $appData, $menu, $uninstallKey)) {
            Assert (-not (Test-Path -LiteralPath $path)) 'A refused installation left files, shortcuts or registration behind.'
        }
        New-StiObservations $manifest $facts $runtime $EnvironmentKind $RuntimeExpectation ([ordered]@{
            install_refused_without_runtime='PASS'; no_residue_after_refusal='PASS'
            lifecycle='NOT RUN in RuntimeExpectation Missing mode'
        }) | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Output 'observations.json') -Encoding utf8
        return
    }
    Install
    $uninstallerHash = Hash (Join-Path $install 'unins000.exe')
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut((Join-Path $menu 'Social Text Intelligence.lnk'))
    Assert ($shortcut.TargetPath -eq (Join-Path $install 'sti-desktop.exe')) 'Start Menu target is wrong.'
    Assert ($shortcut.WorkingDirectory -eq $install) 'Start Menu working directory is wrong.'
    Assert (Test-Path -LiteralPath (Join-Path $menu 'Licenses and sources.lnk')) 'License shortcut is missing.'

    # Launch exactly the Start Menu target; only this newly started process tree is observed.
    $started = Start-Process -FilePath $shortcut.TargetPath -WorkingDirectory $install -WindowStyle Hidden -PassThru
    $window = $null
    for ($attempt = 0; $attempt -lt 100; $attempt++) {
        $candidates = @(Get-Process -Id $started.Id -ErrorAction SilentlyContinue)
        $children = Get-CimInstance Win32_Process -Filter ('ParentProcessId = ' + $started.Id)
        foreach ($child in $children) { $candidates += @(Get-Process -Id $child.ProcessId -ErrorAction SilentlyContinue) }
        $window = $candidates | Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like '*Social Text Intelligence*' } | Select-Object -First 1
        if ($null -ne $window) { break }
        Start-Sleep -Milliseconds 200
    }
    Assert ($null -ne $window) 'First launch did not expose the native application window.'
    Assert ($window.CloseMainWindow()) 'Native window did not accept close.'
    Assert ($started.WaitForExit(15000)) 'First-launch process did not close safely.'

    $appRuntime = (& (Join-Path $install 'sti-check.exe') --verify-runtime) | ConvertFrom-Json
    Assert ($LASTEXITCODE -eq 0 -and $appRuntime.ready -and -not $appRuntime.models_loaded) 'Installed runtime readiness failed.'
    $license = (& (Join-Path $install 'sti-check.exe') --license-info) | ConvertFrom-Json
    Assert ($LASTEXITCODE -eq 0 -and $license.materials_present -and -not $license.distribution_permitted) 'Installed license packet is missing.'
    $smoke = (& (Join-Path $install 'sti-check.exe') --smoke) | ConvertFrom-Json
    Assert ($LASTEXITCODE -eq 0 -and $smoke.window -and $smoke.models_unbundled -and $smoke.reopened) 'Installed synthetic native/missing-model smoke failed.'

    $sentinels = @()
    foreach ($path in @((Join-Path $install 'unrelated\nested\preserve.txt'), (Join-Path $appData 'projects\m10c-preservation.synthetic'), (Join-Path $appData 'models\m10c-external-model.synthetic'), (Join-Path $Output 'unrelated\preserve.txt'))) {
        New-Item -ItemType Directory -Path (Split-Path $path) -Force | Out-Null
        Assert (-not (Test-Path -LiteralPath $path)) 'Sentinel path already exists.'
        'Synthetic M10-C byte-preservation sentinel; not model weights or actual user data.' | Set-Content -LiteralPath $path -Encoding ascii
        $sentinels += [pscustomobject]@{Path=$path; Hash=(Hash $path)}
    }

    # Temporarily redirect an owned material directory to a fresh synthetic external target.
    $legal = Join-Path $install 'legal'; $held = Join-Path $install 'legal-m10c-held'
    Assert (-not (Test-Path -LiteralPath $held)) 'Reserved backup path exists.'
    Assert (((Get-Item -LiteralPath $legal).Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'Legal path is already redirected.'
    $external = Join-Path $Output 'external-legal'
    New-Item -ItemType Directory -Path $external | Out-Null
    $externalFile = Join-Path $external 'GNU-LGPL-3.0.txt'
    'Synthetic external data: must never be removed by uninstall.' | Set-Content -LiteralPath $externalFile -Encoding ascii
    $externalHash = Hash $externalFile
    Move-Item -LiteralPath $legal -Destination $held
    try {
        New-Item -ItemType Junction -Path $legal -Target $external | Out-Null
        Assert ((Uninstall) -ne 0) 'Uninstaller accepted a redirected material directory.'
        Assert ((Hash $externalFile) -eq $externalHash) 'External sentinel changed.'
        Assert (Test-Path -LiteralPath (Join-Path $install 'sti-desktop.exe')) 'Refused uninstall removed application files.'
    } finally {
        $junction = Get-Item -LiteralPath $legal
        Assert ($junction.LinkType -eq 'Junction' -and $junction.Target -eq $external) 'Unexpected link: stop and inspect manually.'
        # Removing this verified junction without recursion removes the link only.
        Remove-Item -LiteralPath $legal -Force
        Assert ((Hash $externalFile) -eq $externalHash) 'External sentinel changed while removing link.'
        Move-Item -LiteralPath $held -Destination $legal
    }
    Assert ((Uninstall) -eq 0) 'Normal uninstall failed.'
    CheckSentinels
    Assert (-not (Test-Path -LiteralPath (Join-Path $menu 'Social Text Intelligence.lnk'))) 'Application shortcut was not removed.'
    Assert (-not (Test-Path -LiteralPath (Join-Path $menu 'Licenses and sources.lnk'))) 'License shortcut was not removed.'
    foreach ($entry in $manifest.payload) {
        Assert (-not (Test-Path -LiteralPath (Join-Path $install $entry.path))) 'A logged payload file was not removed.'
    }
    Install
    CheckSentinels
    $uninstallerHash = Hash (Join-Path $install 'unins000.exe')
    Assert ((Uninstall) -eq 0) 'Second uninstall failed.'
    CheckSentinels
    Assert (-not (Test-Path -LiteralPath $uninstallKey)) 'Uninstall registration was not removed.'
    New-StiObservations $manifest $facts $runtime $EnvironmentKind $RuntimeExpectation ([ordered]@{
        installed_payload_matches=$true; start_menu_target='PASS'; first_native_launch='PASS'
        app_runtime=$appRuntime; license=$license; synthetic_native_smoke=$smoke
        missing_model_analysis_interaction='NOT RUN'; download_authorization_interaction='NOT RUN'
        reparse_uninstall_refusal='PASS'; external_sentinel_preserved=$true
        uninstall_owned_files_and_license_removal='PASS'; shortcuts_removed='PASS'
        uninstall_registration_removed='PASS'; reinstall='PASS'; preservation_sentinels='PASS'
    }) | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Output 'observations.json') -Encoding utf8
} finally {
    foreach ($name in $savedEnvironment.Keys) { [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process') }
}
