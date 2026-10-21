$ErrorActionPreference = "Stop"
python -m PyInstaller --noconfirm --clean --onedir --windowed --name "JOGAR AGORA" --add-data "assets;assets" run.py
if ($LASTEXITCODE -ne 0) { throw "A compilação do executável falhou." }
$packageRoot = Join-Path $env:GITHUB_WORKSPACE "dist\JOGAR AGORA"
$exe = Join-Path $packageRoot "JOGAR AGORA.exe"
if (-not (Test-Path $exe -PathType Leaf)) { throw "A compilação não criou o executável esperado." }
$assetRoot = Join-Path $packageRoot "_internal\assets"
if (-not (Test-Path (Join-Path $assetRoot "v7\city_beta4_four_lanes.png"))) { $assetRoot = Join-Path $packageRoot "assets" }
foreach ($relative in @("v7\city_beta4_four_lanes.png", "v7\desert_beta4_grounded.png", "v7\beach_banded_v72.png", "audio_beta4\music_menu.wav")) {
  if (-not (Test-Path (Join-Path $assetRoot $relative) -PathType Leaf)) { throw "Recurso essencial ausente no pacote: $relative" }
}
@"
SOLDADOS VS ZUMBIS — PACOTE WINDOWS

1. Extraia este ZIP inteiro para uma pasta.
2. Abra JOGAR AGORA.exe.
3. Não mova o executável sozinho; os arquivos internos são necessários.
"@ | Set-Content -Encoding utf8 (Join-Path $packageRoot "LEIA-ME.txt")
python .github/scripts/smoke_test_exe.py --exe $exe --timeout 90
if ($LASTEXITCODE -ne 0) { throw "O teste de inicialização falhou." }
$zip = Join-Path $env:GITHUB_WORKSPACE "dist\Soldados-vs-Zumbis-Windows.zip"
Compress-Archive -Path "$packageRoot\*" -DestinationPath $zip -CompressionLevel Optimal -Force
if ((Get-Item $zip).Length -lt 1MB) { throw "O ZIP final parece incompleto." }
Write-Host "Pacote preparado: $zip"
