; Rendered only into ignored local build output by installer.py.
[Setup]
AppId={{DB272C58-19C3-48E1-A88B-040CD5D88E35}
AppName=@@APPNAME@@
AppVersion=@@VERSION@@
DefaultDirName={localappdata}\Programs\Social Text Intelligence
DisableDirPage=yes
DefaultGroupName=Social Text Intelligence
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0
OutputDir=@@OUTPUT@@
OutputBaseFilename=@@OUTBASE@@
Compression=none
UninstallDisplayIcon={app}\sti-desktop.exe
InfoBeforeFile=@@WARNING@@
CloseApplications=no
RestartApplications=no
SetupLogging=yes
WizardStyle=modern

[Files]
@@FILES@@

[Icons]
Name: "{autoprograms}\Social Text Intelligence\Social Text Intelligence"; Filename: "{app}\sti-desktop.exe"; WorkingDir: "{app}"; IconFilename: "{app}\sti-desktop.exe"
Name: "{autoprograms}\Social Text Intelligence\Licenses and sources"; Filename: "{app}\legal"

[Code]
function GetFileAttributesW(Name: string): Cardinal;
  external 'GetFileAttributesW@kernel32.dll stdcall';

const
  VCRuntimeKey = 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64';
  VCRuntimePage = 'https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist';

{ STI does not redistribute Microsoft Visual C++ runtime files (M10-E2, B3). It
  needs the system Visual C++ 2015-2022 x64 runtime 14.44 or later, which only
  its official Microsoft installer provides. This per-user setup never elevates. }
function VCRuntimeInstalled(): Boolean;
var Installed, Major, Minor: Cardinal;
begin
  Result := RegQueryDWordValue(HKLM64, VCRuntimeKey, 'Installed', Installed)
    and (Installed = 1)
    and RegQueryDWordValue(HKLM64, VCRuntimeKey, 'Major', Major)
    and RegQueryDWordValue(HKLM64, VCRuntimeKey, 'Minor', Minor)
    and ((Major > 14) or ((Major = 14) and (Minor >= 44)));
end;

function InitializeSetup(): Boolean;
var ErrorCode: Integer;
begin
  Result := VCRuntimeInstalled();
  if not Result then begin
    Log('Microsoft Visual C++ 2015-2022 x64 runtime 14.44 or later is not installed.');
    if SuppressibleMsgBox('Social Text Intelligence needs the Microsoft Visual C++ '
      + '2015-2022 Redistributable (x64), version 14.44 or later. It is not '
      + 'installed on this computer, and this setup does not install it.' + #13#10#13#10
      + 'Install it from Microsoft (administrator rights may be required), then run '
      + 'this setup again. Open the Microsoft download page now?',
      mbError, MB_YESNO, IDNO) = IDYES then
      ShellExecAsOriginalUser('open', VCRuntimePage, '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
  end;
end;

function HasReparse(Path: string): Boolean;
var Attributes: Cardinal; Parent: string;
begin
  Result := False;
  while Length(Path) > 0 do begin
    Attributes := GetFileAttributesW(Path);
    if (Attributes <> $FFFFFFFF) and ((Attributes and $400) <> 0) then begin
      Result := True; Exit;
    end;
    Parent := ExtractFileDir(Path);
    if Parent = Path then Exit;
    Path := Parent;
  end;
end;

function Collides(Path: string; Owned: Boolean): Boolean;
var Parent: string;
begin
  Result := HasReparse(Path) or DirExists(Path) or (FileExists(Path) and not Owned);
  Parent := ExtractFileDir(Path);
  while Length(Parent) > 0 do begin
    if FileExists(Parent) then begin Result := True; Exit; end;
    Path := ExtractFileDir(Parent);
    if Path = Parent then Exit;
    Parent := Path;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): string;
var Target, Registered: string; Marker: AnsiString; Owned: Boolean;
begin
  Result := '';
  Target := RemoveBackslashUnlessRoot(ExpandConstant('{app}'));
  if CompareText(Target, ExpandConstant('{localappdata}\Programs\Social Text Intelligence')) <> 0 then begin
    Result := 'Only the fixed per-user application location is supported.'; Exit;
  end;
  if HasReparse(Target) then begin
    Result := 'Installation through links or reparse points is not supported.'; Exit;
  end;
  Registered := '';
  RegQueryStringValue(HKCU64, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{DB272C58-19C3-48E1-A88B-040CD5D88E35}_is1', 'InstallLocation', Registered);
  Owned := (CompareText(RemoveBackslashUnlessRoot(Registered), Target) = 0)
    and FileExists(Target + '\unins000.exe')
    and LoadStringFromFile(Target + '\installer\managed.txt', Marker)
    and (Marker = 'STI M10-C managed application files v1');
  if Collides(ExpandConstant('{autoprograms}\Social Text Intelligence\Social Text Intelligence.lnk'), Owned)
    or Collides(ExpandConstant('{autoprograms}\Social Text Intelligence\Licenses and sources.lnk'), Owned) then begin
    Result := 'Existing Start Menu entries are not owned by this installer.'; Exit;
  end;
@@COLLISIONS@@
end;

function InitializeUninstall(): Boolean;
begin
  Result := False;
  if HasReparse(ExpandConstant('{app}')) then Exit;
  if HasReparse(ExpandConstant('{autoprograms}\Social Text Intelligence\Social Text Intelligence.lnk')) then Exit;
  if HasReparse(ExpandConstant('{autoprograms}\Social Text Intelligence\Licenses and sources.lnk')) then Exit;
@@UNINSTALL_CHECKS@@
  Result := True;
end;
