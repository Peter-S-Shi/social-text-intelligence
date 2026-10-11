; Rendered only into ignored local build output by installer.py.
[Setup]
AppId={{DB272C58-19C3-48E1-A88B-040CD5D88E35}
AppName=Social Text Intelligence (internal engineering)
AppVersion=0.10.0
DefaultDirName={localappdata}\Programs\Social Text Intelligence
DisableDirPage=yes
DefaultGroupName=Social Text Intelligence
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0
OutputDir=@@OUTPUT@@
OutputBaseFilename=STI-0.10.0-internal-x64
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
Name: "{autoprograms}\Social Text Intelligence\Social Text Intelligence"; Filename: "{app}\sti-desktop.exe"; WorkingDir: "{app}"
Name: "{autoprograms}\Social Text Intelligence\Licenses and sources"; Filename: "{app}\legal"

[Code]
function GetFileAttributesW(Name: string): Cardinal;
  external 'GetFileAttributesW@kernel32.dll stdcall';

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
