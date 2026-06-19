; ============================================================================
;  FreeSystemDoctor — Inno Setup installer
;  Builds a clean, signed-friendly Windows installer for the portable .exe.
;  PUP-safe: NO bundled software, NO pre-checked partner offers. The only
;  outbound link is an opt-in "thank-you" page (UTM-tagged) on the finish page.
;
;  Build:  iscc /DSourceDir=..\dist installer\FreeSystemDoctor.iss
;          (see build_installer.ps1)
; ============================================================================

#define MyAppName       "FreeSystemDoctor"
#define MyAppVersion    "2.2.0"
#define MyAppPublisher  "CoopAI Solutions"
#define MyAppURL        "https://freesystemdoctor.com.pl"
#define MyAppExeName    "FreeSystemDoctor.exe"
#define MyAppId         "{{A7F3C2E1-9B4D-4E8A-B1C6-2F5D8E0A3C71}"

; Where the freshly-built portable exe lives (override with /DSourceDir=...)
#ifndef SourceDir
  #define SourceDir "..\dist_test"
#endif
#ifndef OutDir
  #define OutDir "..\dist_installer"
#endif

; UTM-tagged thank-you page opened (opt-in) at the end of setup.
#define ThanksURL "https://freesystemdoctor.com.pl/thanks?utm_source=installer&utm_medium=setup&utm_campaign=v" + MyAppVersion

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
OutputDir={#OutDir}
OutputBaseFilename=FreeSystemDoctor-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; The app itself requires admin; install per-machine into Program Files.
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
#if FileExists(SourcePath + "..\gui\icon.ico")
SetupIconFile=..\gui\icon.ico
#endif
LicenseFile=..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "polish";  MessagesFile: "compiler:Languages\Polish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; DestName: "README.md"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Launch the app (opt-out checkbox, checked) — standard.
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
; Open the thank-you page (opt-out checkbox, checked) — benign, no partner offer.
Filename: "{#ThanksURL}"; Description: "Open the thank-you page (free tips & supported partners)"; Flags: postinstall shellexec skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
