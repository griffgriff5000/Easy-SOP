; Build using scripts/package_installer.py. Keep uninstall records outside App:
; the bundled updater transactionally replaces App and retains its previous version.
#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef PayloadDir
  #error PayloadDir is required
#endif
#ifndef OutputDir
  #error OutputDir is required
#endif
#ifndef ApplicationId
  #define ApplicationId "{93E18DAC-6E7B-48EB-A9A5-15AB24D690EE}"
#endif
#ifndef ShortcutName
  #define ShortcutName "SOP Capture Studio"
#endif

[Setup]
AppId={{#ApplicationId}
AppName=SOP Capture Studio
AppVersion={#AppVersion}
AppPublisher=SOP Capture Studio
AppPublisherURL=https://github.com/griffgriff5000/Easy-SOP
AppSupportURL=https://github.com/griffgriff5000/Easy-SOP/issues
AppUpdatesURL=https://github.com/griffgriff5000/Easy-SOP/releases/latest
DefaultDirName={localappdata}\Programs\SOPCaptureStudio
DisableDirPage=yes
DefaultGroupName={#ShortcutName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
UninstallFilesDir={app}
UninstallDisplayIcon={app}\App\SOPCaptureStudio.exe
SetupIconFile={#PayloadDir}\_internal\sop_capture\assets\app.ico
OutputDir={#OutputDir}
OutputBaseFilename=SOPCaptureStudio-{#AppVersion}-Windows-x64-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
LicenseFile={#PayloadDir}\LICENSE.txt

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}\App"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userdesktop}\{#ShortcutName}"; Filename: "{app}\App\SOPCaptureStudio.exe"; WorkingDir: "{app}\App"; IconFilename: "{app}\App\SOPCaptureStudio.exe"; IconIndex: 0; AppUserModelID: "SOPCaptureStudio.Desktop"; Tasks: desktopicon
Name: "{userprograms}\{#ShortcutName}\{#ShortcutName}"; Filename: "{app}\App\SOPCaptureStudio.exe"; WorkingDir: "{app}\App"; IconFilename: "{app}\App\SOPCaptureStudio.exe"; IconIndex: 0; AppUserModelID: "SOPCaptureStudio.Desktop"

[Run]
Filename: "{app}\App\SOPCaptureStudio.exe"; Description: "Launch SOP Capture Studio"; Flags: nowait postinstall skipifsilent
