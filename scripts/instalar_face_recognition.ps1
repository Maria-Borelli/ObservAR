<#
.SYNOPSIS
    Instala tudo que o ObservAR precisa para usar o backend biométrico
    "face_recognition" (reconhecimento facial real) em qualquer PC Windows,
    sem precisar compilar o dlib.

.DESCRIPTION
    - Localiza (ou cria) o ambiente virtual .venv na raiz do projeto.
    - Instala as dependências do projeto (requirements.txt).
    - Instala o face_recognition usando binários pré-compilados:
        dlib-bin, face_recognition_models, Pillow, setuptools<81 e
        face_recognition (sem dependências, para não recompilar o dlib).
    - Valida que o face_recognition importa e carrega os modelos.
    - Mostra como ativar o backend no arquivo .env.

.NOTES
    Execute a partir da raiz do projeto OU de qualquer lugar: o script se
    localiza sozinho. Se o PowerShell bloquear a execução, rode antes:
        Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#>

$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}

function Write-Ok($msg) {
    Write-Host "[OK] $msg" -ForegroundColor Green
}

function Write-Warn($msg) {
    Write-Host "[!]  $msg" -ForegroundColor Yellow
}

function Write-Err($msg) {
    Write-Host "[ERRO] $msg" -ForegroundColor Red
}

# -------------------------------------------------------------------------
# 1. Localiza a raiz do projeto (pasta-pai de /scripts) e o venv.
# -------------------------------------------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Step "Projeto localizado em: $ProjectRoot"

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Warn "Ambiente virtual .venv nao encontrado. Criando um novo..."

    $SystemPython = (Get-Command python -ErrorAction SilentlyContinue)
    if (-not $SystemPython) {
        Write-Err "Python nao encontrado no PATH. Instale o Python 3.10+ e tente de novo."
        exit 1
    }

    python -m venv (Join-Path $ProjectRoot ".venv")

    if (-not (Test-Path $VenvPython)) {
        Write-Err "Falha ao criar o ambiente virtual."
        exit 1
    }
    Write-Ok "Ambiente virtual criado."
} else {
    Write-Ok "Ambiente virtual .venv encontrado."
}

# Mostra a versao do Python do venv.
$PyVersion = & $VenvPython --version
Write-Host "Python do venv: $PyVersion"

# -------------------------------------------------------------------------
# 2. Atualiza o pip e instala as dependencias do projeto.
# -------------------------------------------------------------------------
Write-Step "Atualizando o pip"
& $VenvPython -m pip install --upgrade pip

Write-Step "Instalando dependencias do projeto (requirements.txt)"
$Requirements = Join-Path $ProjectRoot "requirements.txt"
if (Test-Path $Requirements) {
    & $VenvPython -m pip install -r $Requirements
    Write-Ok "Dependencias do projeto instaladas."
} else {
    Write-Warn "requirements.txt nao encontrado; pulando esta etapa."
}

# -------------------------------------------------------------------------
# 3. Instala o face_recognition sem compilar o dlib.
#    A ordem importa:
#      - dlib-bin: wheel pre-compilado do dlib (sem CMake/Build Tools).
#      - face_recognition_models + Pillow: dependencias de runtime.
#      - setuptools<81: o face_recognition_models usa pkg_resources,
#        removido no setuptools 81+.
#      - face_recognition --no-deps: evita re-puxar o dlib de fonte.
# -------------------------------------------------------------------------
Write-Step "Instalando dlib-bin (binario pre-compilado, sem compilacao)"
try {
    & $VenvPython -m pip install dlib-bin
    Write-Ok "dlib-bin instalado."
} catch {
    Write-Err "Nao foi possivel instalar o dlib-bin para esta versao de Python."
    Write-Warn "Alternativa: use o backend 'opencv' no .env (BIOMETRIC_BACKEND=opencv),"
    Write-Warn "que funciona sem o dlib. O ObservAR suporta os dois backends."
    exit 1
}

Write-Step "Instalando dependencias de runtime do face_recognition"
& $VenvPython -m pip install face_recognition_models Pillow "setuptools<81"

Write-Step "Instalando face_recognition (sem dependencias)"
& $VenvPython -m pip install --no-deps face_recognition
Write-Ok "face_recognition instalado."

# -------------------------------------------------------------------------
# 4. Valida a instalacao de verdade (importa e carrega os modelos).
# -------------------------------------------------------------------------
Write-Step "Validando a instalacao"
$Validador = Join-Path $ScriptDir "_validar_face_recognition.py"
& $VenvPython $Validador
if ($LASTEXITCODE -ne 0) {
    Write-Err "A validacao falhou. Veja a mensagem acima."
    exit 1
}

# -------------------------------------------------------------------------
# 5. Orientacoes finais.
# -------------------------------------------------------------------------
Write-Step "Tudo pronto!"
Write-Host "Para usar o reconhecimento facial real, confirme no arquivo .env:"
Write-Host "    BIOMETRIC_BACKEND=face_recognition"
Write-Host "    BIOMETRIC_TOLERANCE=0.6"
Write-Host ""
Write-Host "Depois rode a aplicacao com:  .\.venv\Scripts\python.exe app.py"
Write-Host ""
