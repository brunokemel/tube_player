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
    $FfmpegCommand = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($FfmpegCommand) {
        $FfmpegPath = $FfmpegCommand.Source
    }
}
if (-not $FfmpegPath -or -not (Test-Path -LiteralPath $FfmpegPath)) {
    throw "FFmpeg nao encontrado. Use -FfmpegPath para informar o executavel."
}

$env:TUBEGRAB_VLC_DIR = (Resolve-Path -LiteralPath $VlcDir).Path
$env:TUBEGRAB_FFMPEG_PATH = (Resolve-Path -LiteralPath $FfmpegPath).Path
$FfprobeCandidate = Join-Path (Split-Path -Parent $env:TUBEGRAB_FFMPEG_PATH) "ffprobe.exe"
if (Test-Path -LiteralPath $FfprobeCandidate) {
    $env:TUBEGRAB_FFPROBE_PATH = (Resolve-Path -LiteralPath $FfprobeCandidate).Path
}

Push-Location $ProjectRoot
try {
    python -m PyInstaller --noconfirm --clean "TubeGrab.spec"
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller terminou com codigo $LASTEXITCODE."
    }
    Write-Host "Build concluido em: $ProjectRoot\dist\TubeGrab" -ForegroundColor Green
} finally {
    Pop-Location
}
