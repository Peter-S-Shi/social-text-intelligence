# Checks shared by validate_installer.ps1 and its tests (M10 S5-A). Dot-source only.
# Windows PowerShell 5.1 and PowerShell 7 compatible; ASCII only.

$StiVCRuntimeKey = 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64'
# The installer requires Visual C++ 2015-2022 x64 runtime 14.44 or later (R1).
$StiVCRuntimeMinimum = @{ Major = 14; Minor = 44 }
# The per-user uninstall registration Inno Setup creates for installer.iss AppId.
$StiUninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{DB272C58-19C3-48E1-A88B-040CD5D88E35}_is1'
# The line installer.iss InitializeSetup logs when it refuses for a missing runtime.
$StiRuntimeRefusalLog = 'Microsoft Visual C++ 2015-2022 x64 runtime 14.44 or later is not installed.'
$StiAcceptanceNotDetermined = 'NOT DETERMINED BY THIS HARNESS'

function Test-StiInteger($Value) { return ($Value -is [int] -or $Value -is [long]) }

function Get-StiField($Object, [string]$Name) {
    <# A required receipt field; a missing one refuses the receipt. #>
    if ($null -eq $Object -or -not ($Object.PSObject.Properties.Name -contains $Name)) {
        throw "Receipt field '$Name' is missing; the receipt is refused."
    }
    # The comma keeps a list (even an empty or single-item one) from unrolling.
    return ,$Object.$Name
}

function Get-StiReceiptFacts($Manifest) {
    <# The receipt's own blocker facts, after a fail-closed structural check (H1). #>
    if ($null -eq $Manifest -or $Manifest -is [array]) { throw 'The receipt must be one JSON object.' }
    $schema = Get-StiField $Manifest 'schema_version'
    if (-not (Test-StiInteger $schema) -or $schema -ne 1) { throw 'Only receipt schema version 1 is accepted.' }
    if ((Get-StiField $Manifest 'compiled') -isnot [bool] -or -not $Manifest.compiled) {
        throw 'Compiled installer receipt is required.'
    }
    if ((Get-StiField $Manifest 'distribution_permitted') -isnot [bool] -or $Manifest.distribution_permitted) {
        throw 'The receipt must record distribution as not permitted.'
    }
    if ((Get-StiField $Manifest 'models_bundled') -isnot [bool] -or $Manifest.models_bundled) {
        throw 'The receipt must record that no models are bundled.'
    }
    if ((Get-StiField $Manifest 'installer_sha256') -cnotmatch '^[0-9a-f]{64}$') {
        throw 'The receipt must record the installer SHA-256.'
    }
    if ((Get-StiField $Manifest 'frozen_application_sha') -cnotmatch '^[0-9a-f]{40}$') {
        throw 'The receipt must record the frozen application revision.'
    }
    $payload = Get-StiField $Manifest 'payload'
    if ($payload -isnot [array] -or $payload.Count -eq 0) { throw 'The receipt must list the installed payload.' }
    foreach ($entry in $payload) {
        if ($entry -isnot [System.Management.Automation.PSCustomObject] -or
            ($entry.PSObject.Properties.Name -cnotcontains 'path') -or $entry.path -isnot [string] -or
            ($entry.PSObject.Properties.Name -cnotcontains 'sha256') -or $entry.sha256 -cnotmatch '^[0-9a-f]{64}$') {
            throw 'A receipt payload entry is malformed.'
        }
    }

    $legal = Get-StiField $Manifest 'legal_blockers'
    if ($legal -isnot [array]) { throw 'legal_blockers must be a list.' }
    $codes = @($legal)
    if ($codes.Count -eq 0) { throw 'Distribution is not permitted, so the receipt must name its blockers.' }
    foreach ($code in $codes) {
        if ($code -isnot [string] -or $code -cnotmatch '^B[1-6]$') { throw 'A legal blocker code is malformed.' }
    }
    if (@($codes | Select-Object -Unique).Count -ne $codes.Count) { throw 'A legal blocker code is repeated.' }
    if ($codes -cnotcontains 'B1') {
        # As in installer.py: no reviewed record closes B1, so a receipt without it is refused.
        throw 'The receipt omits B1, which no reviewed record closes.'
    }

    $other = Get-StiField $Manifest 'other_packet_blockers'
    if ($other -isnot [array]) { throw 'other_packet_blockers must be a list.' }
    foreach ($item in @($other)) {
        if ($item -isnot [string] -or $item.Trim().Length -eq 0) { throw 'An uncoded packet blocker is malformed.' }
    }

    $conditions = Get-StiField $Manifest 'release_conditions'
    if ($conditions -isnot [System.Management.Automation.PSCustomObject]) { throw 'release_conditions must be an object.' }
    $names = @($conditions.PSObject.Properties.Name)
    foreach ($required in @('B6', 'clean_machine_validation', 'public_source_hosting')) {
        if ($names -cnotcontains $required) { throw "release_conditions.$required is missing." }
    }
    foreach ($name in $names) {
        if ($conditions.$name -isnot [string]) { throw "release_conditions.$name must be text." }
    }
    if ($conditions.clean_machine_validation -cne 'NOT RUN' -or (Get-StiField $Manifest 'clean_machine_validation') -cne 'NOT RUN') {
        # A receipt is produced before any clean-machine run; it cannot carry an acceptance.
        throw 'The receipt claims a clean-machine result it cannot hold.'
    }
    if ((Get-StiField $Manifest 'owner_30_minute_smoke') -cne 'NOT RUN') {
        throw 'The receipt claims an owner smoke result it cannot hold.'
    }
    if ($codes -ccontains 'B6') {
        # B6 is reported as a release condition (closed on its narrow criterion), never both.
        throw 'The receipt reports B6 both as a packet blocker and as a release condition.'
    }
    return [ordered]@{
        legal_blockers = $codes
        other_packet_blockers = @($other)
        release_conditions = $conditions
    }
}

function Read-StiVCRuntimeRegistry {
    <# The four runtime values from the 64-bit registry view, or $null when absent. #>
    $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey(
        [Microsoft.Win32.RegistryHive]::LocalMachine, [Microsoft.Win32.RegistryView]::Registry64)
    try {
        $key = $base.OpenSubKey($StiVCRuntimeKey)
        if ($null -eq $key) { return $null }
        try {
            $values = @{}
            foreach ($name in @('Installed', 'Major', 'Minor', 'Bld')) { $values[$name] = $key.GetValue($name) }
            return $values
        } finally { $key.Close() }
    } finally { $base.Close() }
}

function Get-StiVCRuntimeState([scriptblock]$Reader = { Read-StiVCRuntimeRegistry }) {
    <# The installed runtime, judged exactly as installer.iss does (H2). #>
    $values = & $Reader
    $state = [ordered]@{ present = $false; installed = $null; major = $null; minor = $null; build = $null; meets_requirement = $false }
    if ($null -eq $values) { return $state }
    $state.present = $true
    $state.installed = $values['Installed']; $state.major = $values['Major']
    $state.minor = $values['Minor']; $state.build = $values['Bld']
    $numeric = $true
    foreach ($value in @($state.installed, $state.major, $state.minor)) {
        if ($value -isnot [int]) { $numeric = $false }
    }
    $state.meets_requirement = $numeric -and $state.installed -eq 1 -and (
        $state.major -gt $StiVCRuntimeMinimum.Major -or
        ($state.major -eq $StiVCRuntimeMinimum.Major -and $state.minor -ge $StiVCRuntimeMinimum.Minor))
    return $state
}

function Assert-StiRuntimeExpectation($State, [string]$Expectation) {
    <# Refuses a run whose selected mode does not match the machine's actual runtime. #>
    if ($Expectation -cnotin @('Missing', 'Present')) { throw 'Unknown runtime expectation.' }
    if ($Expectation -ceq 'Missing' -and $State.meets_requirement) {
        throw 'RuntimeExpectation Missing was selected, but a qualifying VC++ runtime is installed.'
    }
    if ($Expectation -ceq 'Present' -and -not $State.meets_requirement) {
        throw 'RuntimeExpectation Present was selected, but no VC++ runtime 14.44 or later is installed.'
    }
}

function New-StiObservations($Receipt, $Facts, $Runtime, [string]$EnvironmentKind, [string]$Expectation, $Automated) {
    <# Automated results only (H3): never a clean-baseline proof or an acceptance. #>
    return [ordered]@{
        schema_version = 2
        environment = $EnvironmentKind
        environment_marker = $(if ($EnvironmentKind -eq 'DisposableVM') {
            'present: operator intent only, not proof of a clean baseline' } else { 'not used' })
        runtime_expectation = $Expectation
        vc_runtime = $Runtime
        installer_sha256 = $Receipt.installer_sha256
        frozen_application_sha = $Receipt.frozen_application_sha
        automated_checks = $Automated
        clean_baseline_proof = 'NOT PROVIDED BY THIS HARNESS: record the snapshot/baseline evidence separately'
        owner_witness = 'NOT RECORDED BY THIS HARNESS: the owner records independent observations separately'
        clean_machine_acceptance = $StiAcceptanceNotDetermined
        formal_windows_uat = 'NOT RUN'
        owner_30_minute_smoke = 'NOT RUN'
        distribution_permitted = $false
        legal_blockers = $Facts.legal_blockers
        other_packet_blockers = $Facts.other_packet_blockers
        release_conditions = $Facts.release_conditions
    }
}
