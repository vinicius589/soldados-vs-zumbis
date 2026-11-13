$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
function Test-Python312([string]$Executable) {
    try {
        $result = & $Executable -c 'import sys,struct,venv; print(31264 if sys.version_info[:2] == (3,12) and struct.calcsize(chr(80)) == 8 else 0)' 2>$null
        return ($LASTEXITCODE -eq 0 -and $result -contains '31264')
    } catch { return $false }
}
try {
    Write-Host 'Preparando as bibliotecas do jogo. A instalacao pode precisar de internet.'
    $venvPath = Join-Path $PSScriptRoot '.venv'
    $environmentPython = Join-Path $venvPath 'Scripts\python.exe'
    $marker = Join-Path $PSScriptRoot '.ambiente-pronto'
    if (Test-Path -LiteralPath $marker) { Remove-Item -LiteralPath $marker }
    if (-not (Test-Python312 $environmentPython)) {
        $candidates = @()
        try {
            $located = & py -3.12 -c 'import sys; print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0) { $candidates += $located }
        } catch {}
        $candidates += @(Get-Command python.exe -All -ErrorAction SilentlyContinue | ForEach-Object { $_.Source })
        $candidates += @(
            "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
            "$env:ProgramFiles\Python312\python.exe",
            "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
        )
        $runtime = $null
        foreach ($candidate in $candidates) {
            if ($candidate -and (Test-Python312 $candidate)) { $runtime = $candidate; break }
        }
        if (-not $runtime) {
            throw 'Python 3.12 x64 nao encontrado. Instale-o pelo gerenciador Python com: py install 3.12. Depois execute este arquivo novamente.'
        }
        Write-Host "Python selecionado: $runtime"
        if (Test-Path -LiteralPath $venvPath) {
            $resolved = (Resolve-Path -LiteralPath $venvPath).Path
            if ($resolved -ne $venvPath -or ((Get-Item -LiteralPath $venvPath).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                throw 'A pasta .venv e um caminho redirecionado. Verifique-a antes de preparar o ambiente.'
            }
            $backupName = '.venv-backup-' + [guid]::NewGuid().ToString('N')
            Rename-Item -LiteralPath $venvPath -NewName $backupName
            Write-Host "Ambiente anterior preservado em $backupName"
        }
        Write-Host '[1/3] Criando ambiente isolado...'
        & $runtime -m venv $venvPath
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar o ambiente isolado.' }
        if (-not (Test-Python312 $environmentPython)) { throw 'O ambiente criado nao passou na verificacao de Python 3.12 x64.' }
    } else { Write-Host '[1/3] Ambiente Python 3.12 x64 existente validado.' }
    Write-Host '[2/3] Verificando o instalador de bibliotecas...'
    & $environmentPython -m pip --version
    if ($LASTEXITCODE -ne 0) {
        & $environmentPython -m ensurepip --upgrade
        if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel preparar o pip.' }
    }
    Write-Host '[3/3] Instalando as bibliotecas do jogo...'
    & $environmentPython -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar bibliotecas. Confira a conexao e a mensagem acima.' }
    & $environmentPython -c 'import pygame, OpenGL, numpy'
    if ($LASTEXITCODE -ne 0) { throw 'A verificacao das bibliotecas falhou.' }
    Set-Content -LiteralPath $marker -Value 'SVZ_ENVIRONMENT_READY_V1' -Encoding ascii
    Write-Host 'Ambiente preparado com sucesso! Agora abra JOGAR.bat.'
    exit 0
} catch {
    Write-Host "ERRO: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'A preparacao nao foi concluida. Corrija a causa e execute novamente.'
    exit 1
}
