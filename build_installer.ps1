<#
    build_installer.ps1 — produce the FreeSystemDoctor Windows installer.

    Steps:
      1. (optional) rebuild the portable .exe via PyInstaller   (-Rebuild)
      2. compile the Inno Setup installer from installer\FreeSystemDoctor.iss
      3. emit SHA256SUMS.txt for the installer + portable exe

    Usage:
      .\build_installer.ps1                 # use existing exe in -SourceDir
      .\build_installer.ps1 -Rebuild        # rebuild exe first
      .\build_installer.ps1 -SourceDir dist # use dist\ instead of dist_test\
#>
param(
    [switch]$Rebuild,
    [string]$SourceDir = "dist_test",
    [string]$OutDir    = "dist_installer"
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

if ($Rebuild) {
    Write-Host "==> Rebuilding portable exe (PyInstaller)..." -ForegroundColor Cyan
    python -m PyInstaller FreeSystemDoctor.spec --distpath $SourceDir --workpath build_test --noconfirm
}

$exe = Join-Path $root "$SourceDir\FreeSystemDoctor.exe"
if (-not (Test-Path $exe)) { throw "Portable exe not found: $exe  (run with -Rebuild)" }

# Locate Inno Setup compiler
$iscc = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 (ISCC.exe) not found. Install from https://jrsoftware.org/isdl.php" }

New-Item -ItemType Directory -Force -Path (Join-Path $root $OutDir) | Out-Null

Write-Host "==> Compiling installer..." -ForegroundColor Cyan
& $iscc "/DSourceDir=..\$SourceDir" "/DOutDir=..\$OutDir" "installer\FreeSystemDoctor.iss"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

# Checksums for everything users will download
Write-Host "==> Writing SHA256SUMS.txt..." -ForegroundColor Cyan
$sums = Join-Path $root "$OutDir\SHA256SUMS.txt"
Remove-Item $sums -ErrorAction SilentlyContinue
$targets = @(
    (Get-ChildItem (Join-Path $root $OutDir) -Filter "FreeSystemDoctor-Setup-*.exe"),
    (Get-Item $exe)
)
foreach ($t in $targets) {
    $h = (Get-FileHash $t.FullName -Algorithm SHA256).Hash.ToLower()
    "$h  $($t.Name)" | Add-Content -Encoding ascii $sums
}

Write-Host "`n==> Done. Artifacts in $OutDir\:" -ForegroundColor Green
Get-ChildItem (Join-Path $root $OutDir) | ForEach-Object {
    "{0,-42} {1,8:N1} MB" -f $_.Name, ($_.Length/1MB)
}
Get-Content $sums
