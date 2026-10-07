param(
    [string]$VlcDir = "C:\Program Files\VideoLAN\VLC",
    [string]$FfmpegPath = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path -LiteralPath (Join-Path $VlcDir "libvlc.dll"))) {
    throw "VLC nao encontrado em '$VlcDir'. Use -VlcDir para informar o caminho."
}
if (-not $FfmpegPath) {
    $Command = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($Command) { $FfmpegPath = $Command.Source }
}
if (-not $FfmpegPath -or -not (Test-Path -LiteralPath $FfmpegPath)) {
    throw "FFmpeg nao encontrado. Use -FfmpegPath para informar o executavel."
}

$env:TUBEGRAB_VLC_DIR = (Resolve-Path -LiteralPath $VlcDir).Path
$env:TUBEGRAB_FFMPEG_PATH = (Resolve-Path -LiteralPath $FfmpegPath).Path
$Probe = Join-Path (Split-Path -Parent $env:TUBEGRAB_FFMPEG_PATH) "ffprobe.exe"
if (Test-Path -LiteralPath $Probe) {
    $env:TUBEGRAB_FFPROBE_PATH = (Resolve-Path -LiteralPath $Probe).Path
}

Push-Location $ProjectRoot
try {
    python -m PyInstaller --noconfirm --clean "TubeGrab-onefile.spec"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller terminou com codigo $LASTEXITCODE." }

    # Mantem o artefato final em uma pasta de identificacao simples para publicacao.
    $DownloadDir = Join-Path $ProjectRoot "download"
    $BuiltExe = Join-Path $ProjectRoot "dist\TubeGrab-Portable.exe"
    $PublishedExe = Join-Path $DownloadDir "TubeGrab-Portable.exe"
    New-Item -ItemType Directory -Path $DownloadDir -Force | Out-Null
    Copy-Item -LiteralPath $BuiltExe -Destination $PublishedExe -Force
    Write-Host "Executavel criado em: $PublishedExe" -ForegroundColor Green
} finally {
    Pop-Location
}
