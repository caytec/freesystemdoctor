; ============================================================================
;  FreeSystemDoctor — Inno Setup installer
;  Builds a clean, signed-friendly Windows installer for the portable .exe.
;
;  MONETIZATION (anti-PUP, opt-in): a dedicated "Recommended free tools" wizard
;  page lists hand-picked partner apps. EVERY box is UNCHECKED by default. We
;  NEVER bundle or silently install anything — a ticked offer only opens the
;  partner's own site in the user's browser AFTER setup finishes. Links route
;  through our /partners?ref=<id> page so the real affiliate URLs can be swapped
;  server-side without rebuilding the installer.
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

; Single place that all affiliate clicks route through (ref + UTM appended).
#define PartnersURL "https://freesystemdoctor.com.pl/partners"

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

[CustomMessages]
english.PartnerPageCaption=Recommended free tools (optional)
english.PartnerPageDesc=Hand-picked partner apps. Tick any you'd like to try — nothing is installed; ticked links simply open in your browser after setup.
english.PartnerIntro=All boxes are unchecked by default. These are affiliate links: if you sign up we may earn a small commission at no extra cost to you, which keeps FreeSystemDoctor free. You can skip this page entirely.
polish.PartnerPageCaption=Polecane darmowe narzędzia (opcjonalnie)
polish.PartnerPageDesc=Ręcznie wybrane aplikacje partnerów. Zaznacz te, które chcesz wypróbować — nic nie jest instalowane; zaznaczone linki otworzą się w przeglądarce po instalacji.
polish.PartnerIntro=Wszystkie pola są domyślnie odznaczone. To linki afiliacyjne: jeśli się zarejestrujesz, możemy otrzymać niewielką prowizję bez dodatkowych kosztów dla Ciebie, co utrzymuje FreeSystemDoctor za darmo. Tę stronę możesz pominąć.

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
; Open the thank-you page (opt-out checkbox, checked) — benign, free tips only.
Filename: "{#ThanksURL}"; Description: "Open the thank-you page (free tips)"; Flags: postinstall shellexec skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

; ============================================================================
;  Opt-in partner offer page (Pascal Script)
;  - One checkbox per curated partner, ALL unchecked by default.
;  - The offer ids below MUST match the LINKS map in website/partners.html.
;  - Nothing installs; ticked links open de-elevated in the user's browser
;    only after the user clicks Finish (ssDone).
; ============================================================================
[Code]
const
  PARTNER_COUNT = 6;

var
  PartnerPage:  TWizardPage;
  PartnerCheck: array[0..5] of TNewCheckBox;
  PartnerId:    array[0..5] of String;

procedure InitializeWizard();
var
  I, Y: Integer;
  Intro: TNewStaticText;
  Desc:  TNewStaticText;
  Titles: array[0..5] of String;
  Descs:  array[0..5] of String;
begin
  // offer id  (-> /partners?ref=<id>)        title (checkbox caption)            one-line benefit
  // All six have active, easy-to-join affiliate programs with real commission.
  PartnerId[0] := 'nordvpn';     Titles[0] := 'NordVPN';              Descs[0] := 'Encrypt your connection — 5500+ servers, 6 devices. Free trial available.';
  PartnerId[1] := 'protonvpn';   Titles[1] := 'Proton (VPN + Mail)';  Descs[1] := 'Swiss no-logs VPN & encrypted email. Free tier forever.';
  PartnerId[2] := 'surfshark';   Titles[2] := 'Surfshark VPN';        Descs[2] := 'Unlimited devices + built-in CleanWeb ad blocker.';
  PartnerId[3] := 'bitdefender'; Titles[3] := 'Bitdefender';          Descs[3] := 'Top-rated antivirus 2026 — runs alongside Defender, zero slowdown.';
  PartnerId[4] := 'malwarebytes';Titles[4] := 'Malwarebytes';         Descs[4] := '#1 anti-malware — pairs with Windows Defender, no conflicts.';
  PartnerId[5] := 'pcloud';      Titles[5] := 'pCloud';               Descs[5] := 'Lifetime cloud storage — pay once, no subscription.';

  PartnerPage := CreateCustomPage(
    wpSelectTasks,
    ExpandConstant('{cm:PartnerPageCaption}'),
    ExpandConstant('{cm:PartnerPageDesc}'));

  Intro := TNewStaticText.Create(PartnerPage);
  Intro.Parent := PartnerPage.Surface;
  Intro.Left := 0;
  Intro.Top := 0;
  Intro.Width := PartnerPage.SurfaceWidth;
  Intro.Height := ScaleY(40);
  Intro.AutoSize := False;
  Intro.WordWrap := True;
  Intro.Font.Color := clGray;
  Intro.Caption := ExpandConstant('{cm:PartnerIntro}');

  Y := Intro.Top + Intro.Height + ScaleY(10);
  for I := 0 to PARTNER_COUNT - 1 do
  begin
    PartnerCheck[I] := TNewCheckBox.Create(PartnerPage);
    PartnerCheck[I].Parent := PartnerPage.Surface;
    PartnerCheck[I].Left := 0;
    PartnerCheck[I].Top := Y;
    PartnerCheck[I].Width := PartnerPage.SurfaceWidth;
    PartnerCheck[I].Height := ScaleY(17);
    PartnerCheck[I].Caption := Titles[I];
    PartnerCheck[I].Font.Style := [fsBold];
    PartnerCheck[I].Checked := False;   { OPT-IN: never pre-checked }
    Y := Y + ScaleY(18);

    Desc := TNewStaticText.Create(PartnerPage);
    Desc.Parent := PartnerPage.Surface;
    Desc.Left := ScaleX(20);
    Desc.Top := Y;
    Desc.Width := PartnerPage.SurfaceWidth - ScaleX(20);
    Desc.Height := ScaleY(15);
    Desc.AutoSize := False;
    Desc.WordWrap := False;
    Desc.Font.Color := clGray;
    Desc.Caption := Descs[I];
    Y := Y + ScaleY(24);
  end;
end;

procedure OpenSelectedPartners();
var
  I, ResultCode: Integer;
  Url: String;
begin
  for I := 0 to PARTNER_COUNT - 1 do
  begin
    if (PartnerCheck[I] <> nil) and (PartnerCheck[I].Checked) then
    begin
      Url := '{#PartnersURL}?ref=' + PartnerId[I]
        + '&utm_source=installer&utm_medium=offerwall&utm_campaign=v{#MyAppVersion}';
      { Open de-elevated, in the original user's default browser, fire-and-forget. }
      ShellExecAsOriginalUser('open', Url, '', '', SW_SHOWNORMAL, ewNoWait, ResultCode);
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssDone then
    OpenSelectedPartners();
end;
