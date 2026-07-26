param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$videoPath = Join-Path $RepoRoot 'outputs\sbz_professional_character_showcase.mp4'
$outputPath = Join-Path $RepoRoot 'reports\professional_character_showcase_validation.json'
$phase4Path = Join-Path $RepoRoot 'reports\phase4_multi_character_metrics.json'
$productionPath = Join-Path $RepoRoot 'reports\adventurer_directed_production_regression.json'
$contactSheet = Join-Path $RepoRoot 'outputs\sbz_professional_character_showcase_contact_sheet.jpg'
$ffmpeg = 'C:\Program Files\ffmpeg\bin\ffmpeg.exe'
$ffprobe = 'C:\Program Files\ffmpeg\bin\ffprobe.exe'
if (-not (Test-Path -LiteralPath $ffmpeg)) { $ffmpeg = (Get-Command ffmpeg).Source }
if (-not (Test-Path -LiteralPath $ffprobe)) { $ffprobe = (Get-Command ffprobe).Source }

foreach ($required in @($videoPath, $phase4Path, $productionPath, $contactSheet)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Missing showcase validation input: $required" }
}

function Invoke-CapturedProcess([string]$FilePath, [string[]]$Arguments) {
    $start = [System.Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $FilePath
    $start.UseShellExecute = $false
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.Arguments = ($Arguments | ForEach-Object {
        '"' + ([string]$_).Replace('"', '\"') + '"'
    }) -join ' '
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $start
    [void]$process.Start()
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    return @{ ExitCode = $process.ExitCode; Stdout = $stdout; Stderr = $stderr }
}

$probeResult = Invoke-CapturedProcess $ffprobe @(
    '-v', 'error', '-show_entries',
    'stream=index,codec_type,codec_name,width,height,pix_fmt,r_frame_rate,nb_frames,duration,sample_rate,channels:format=duration,size,bit_rate',
    '-of', 'json', $videoPath
)
if ($probeResult.ExitCode -ne 0) { throw "ffprobe failed: $($probeResult.Stderr)" }
$probe = $probeResult.Stdout | ConvertFrom-Json
$video = $probe.streams | Where-Object codec_type -eq 'video' | Select-Object -First 1
$audio = $probe.streams | Where-Object codec_type -eq 'audio' | Select-Object -First 1

$blackResult = Invoke-CapturedProcess $ffmpeg @(
    '-hide_banner', '-i', $videoPath, '-vf', 'blackdetect=d=0.20:pix_th=0.01',
    '-an', '-f', 'null', 'NUL'
)
$blackSegments = @([regex]::Matches($blackResult.Stderr, 'black_start:([\d.]+).*?black_end:([\d.]+)') |
    ForEach-Object { @{ start = [double]$_.Groups[1].Value; end = [double]$_.Groups[2].Value } })

$volumeResult = Invoke-CapturedProcess $ffmpeg @(
    '-hide_banner', '-i', $videoPath, '-vn', '-af', 'volumedetect', '-f', 'null', 'NUL'
)
$meanMatch = [regex]::Match($volumeResult.Stderr, 'mean_volume:\s*(-?[\d.]+) dB')
$maxMatch = [regex]::Match($volumeResult.Stderr, 'max_volume:\s*(-?[\d.]+) dB')
$meanVolume = if ($meanMatch.Success) { [double]$meanMatch.Groups[1].Value } else { $null }
$maxVolume = if ($maxMatch.Success) { [double]$maxMatch.Groups[1].Value } else { $null }

$phase4 = Get-Content -Raw -LiteralPath $phase4Path | ConvertFrom-Json
$production = Get-Content -Raw -LiteralPath $productionPath | ConvertFrom-Json
$duration = [double]$probe.format.duration
$checks = [ordered]@{
    fileExistsAndNonEmpty = (Get-Item -LiteralPath $videoPath).Length -gt 1000000
    h264HighQualityDelivery = $video.codec_name -eq 'h264' -and $video.pix_fmt -eq 'yuv420p'
    fullHdLandscape = [int]$video.width -eq 1920 -and [int]$video.height -eq 1080
    deterministicFrameRate = $video.r_frame_rate -eq '24/1'
    expectedFrameCount = [int]$video.nb_frames -eq 899
    expectedDuration = [math]::Abs($duration - 37.458333) -lt 0.02
    youtubeCompatibleAudio = $audio.codec_name -eq 'aac' -and [int]$audio.sample_rate -eq 48000 -and [int]$audio.channels -eq 2
    professionalAudioLevel = $null -ne $meanVolume -and $meanVolume -ge -24 -and $meanVolume -le -16 -and $maxVolume -lt -1
    noDetectedBlackSegments = $blackSegments.Count -eq 0
    multiCharacterCapturePassed = $phase4.status -eq 'PASS' -and $phase4.capture -eq $true -and
        $phase4.meta.mixerCount -eq 3 -and $phase4.meta.sharedSkeletonCorruption -eq $false -and
        $phase4.pageErrors.Count -eq 0
    directedStoryValidationPassed = $production.verdict -eq 'PASS_FOR_SINGLE_SCENE_REVIEW'
    milestoneVisualReviewPresent = Test-Path -LiteralPath $contactSheet
}
$passed = @($checks.Values | Where-Object { $_ -eq $true }).Count
$report = [ordered]@{
    schemaVersion = 1
    generatedAt = (Get-Date).ToString('o')
    verdict = if ($passed -eq $checks.Count) { 'PASS' } else { 'FAIL' }
    output = $videoPath
    sha256 = (Get-FileHash -LiteralPath $videoPath -Algorithm SHA256).Hash.ToLowerInvariant()
    checksPassed = $passed
    checksTotal = $checks.Count
    checks = $checks
    media = $probe
    audioAnalysis = @{ meanVolumeDb = $meanVolume; maxVolumeDb = $maxVolume }
    blackSegments = $blackSegments
    sources = @{
        directedStoryValidation = $productionPath
        multiCharacterMetrics = $phase4Path
        visualContactSheet = $contactSheet
    }
    knownLimitations = @(
        'Quaternius characters in this showcase are body-animation characters and are not classified FACIAL_READY.',
        'The showcase intentionally contains no dialogue or lip-sync claim.',
        'The opening title is intentionally static between its short fade-in and fade-out.'
    )
}
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $outputPath -Encoding UTF8
Write-Output "SBZ_SHOWCASE_VALIDATION=$($report.verdict) checks=$passed/$($checks.Count)"
if ($report.verdict -ne 'PASS') { exit 1 }
