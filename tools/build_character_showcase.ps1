param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$ffmpeg = 'C:\Program Files\ffmpeg\bin\ffmpeg.exe'
$ffprobe = 'C:\Program Files\ffmpeg\bin\ffprobe.exe'
if (-not (Test-Path -LiteralPath $ffmpeg)) { $ffmpeg = (Get-Command ffmpeg).Source }
if (-not (Test-Path -LiteralPath $ffprobe)) { $ffprobe = (Get-Command ffprobe).Source }

$story = Join-Path $RepoRoot 'outputs\adventurer_directed_production_scene.mp4'
$cast = Join-Path $RepoRoot 'outputs\phase4_multi_character_proof.mp4'
$music = Join-Path $RepoRoot 'assets\music\calm\calm_ambient.mp3'
$surprise = Join-Path $RepoRoot 'assets\sfx\surprise.wav'
$whoosh = Join-Path $RepoRoot 'assets\sfx\whoosh.wav'
$title = Join-Path $RepoRoot 'outputs\character_showcase_title.mp4'
$output = Join-Path $RepoRoot 'outputs\sbz_professional_character_showcase.mp4'
$metrics = Join-Path $RepoRoot 'reports\professional_character_showcase_metrics.json'
$fontRegular = 'C\:/Windows/Fonts/segoeui.ttf'
$fontBold = 'C\:/Windows/Fonts/seguisb.ttf'

foreach ($required in @($story, $cast, $music, $surprise, $whoosh)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Missing showcase input: $required" }
}

$titleFilter = "drawbox=x=0:y=0:w=iw:h=ih:color=0x090D14:t=fill," +
    "drawbox=x=188:y=342:w=12:h=236:color=0x4F8CFF:t=fill," +
    "drawtext=fontfile='$fontBold':text='SBZ AI VIDEO STUDIO':fontcolor=0xF1F5F9:fontsize=74:x=236:y=356," +
    "drawtext=fontfile='$fontRegular':text='PROFESSIONAL CHARACTER ANIMATION SHOWCASE':fontcolor=0x94A3B8:fontsize=30:x=240:y=466," +
    "drawtext=fontfile='$fontRegular':text='Authored motion  |  Story direction  |  Multi-character runtime':fontcolor=0x4F8CFF:fontsize=25:x=240:y=526," +
    "fade=t=in:st=0:d=0.35,fade=t=out:st=2.15:d=0.35"

& $ffmpeg -hide_banner -loglevel warning -y -f lavfi -i 'color=c=0x090D14:s=1920x1080:r=24:d=2.5' `
    -vf $titleFilter -an -c:v libx264 -preset medium -crf 17 -pix_fmt yuv420p -r 24 -movflags +faststart $title
if ($LASTEXITCODE -ne 0) { throw "Title render failed with exit code $LASTEXITCODE" }

$filter = @"
[0:v]setpts=PTS-STARTPTS,format=yuv420p[title];
[1:v]setpts=PTS-STARTPTS,drawbox=x=92:y=70:w=780:h=124:color=0x090D14@0.76:t=fill:enable='between(t,0.35,3.8)',drawbox=x=92:y=70:w=8:h=124:color=0x4F8CFF@0.96:t=fill:enable='between(t,0.35,3.8)',drawtext=fontfile='$fontBold':text='THE SUSPICIOUS BOX':fontcolor=white:fontsize=44:x=128:y=88:enable='between(t,0.35,3.8)',drawtext=fontfile='$fontRegular':text='A directed 3D story proof':fontcolor=0xB8C7DA:fontsize=24:x=130:y=146:enable='between(t,0.35,3.8)',format=yuv420p[story];
[2:v]setpts=PTS-STARTPTS,drawbox=x=110:y=790:w=1060:h=170:color=0x090D14@0.78:t=fill:enable='between(t,0.25,5.5)',drawbox=x=110:y=790:w=8:h=170:color=0x22C55E@0.96:t=fill:enable='between(t,0.25,5.5)',drawtext=fontfile='$fontBold':text='MULTI-CHARACTER PERFORMANCE':fontcolor=white:fontsize=42:x=148:y=814:enable='between(t,0.25,5.5)',drawtext=fontfile='$fontRegular':text='Independent mixers  |  Real clips  |  Grounded rigs  |  Preserved materials':fontcolor=0xB8C7DA:fontsize=24:x=150:y=876:enable='between(t,0.25,5.5)',format=yuv420p[cast];
[title][story]xfade=transition=fade:duration=0.35:offset=2.15[v01];
[v01][cast]xfade=transition=fade:duration=0.35:offset=31.80,fade=t=out:st=37.00:d=0.45[vout];
[3:a]atrim=0:37.45,asetpts=PTS-STARTPTS,volume=0.15,afade=t=in:st=0:d=1.2,afade=t=out:st=35.8:d=1.65[music];
[4:a]adelay=15900|15900,volume=0.62[surprise];
[5:a]asplit=2[whoosh1][whoosh2];
[whoosh1]adelay=1950|1950,volume=0.45[w1];
[whoosh2]adelay=31600|31600,volume=0.52[w2];
[music][surprise][w1][w2]amix=inputs=4:duration=longest:normalize=0,loudnorm=I=-20:TP=-2:LRA=10,alimiter=limit=0.93[aout]
"@

& $ffmpeg -hide_banner -loglevel warning -y -i $title -i $story -i $cast -stream_loop -1 -i $music `
    -i $surprise -i $whoosh -filter_complex $filter -map '[vout]' -map '[aout]' `
    -t 37.45 -c:v libx264 -preset medium -crf 17 -profile:v high -level 4.2 -pix_fmt yuv420p `
    -r 24 -fps_mode cfr -c:a aac -b:a 192k -ar 48000 -movflags +faststart $output
if ($LASTEXITCODE -ne 0) { throw "Showcase assembly failed with exit code $LASTEXITCODE" }

$probe = & $ffprobe -v error -show_entries 'stream=index,codec_type,codec_name,width,height,pix_fmt,r_frame_rate,nb_frames,duration' `
    -show_entries 'format=duration,size,bit_rate' -of json $output | ConvertFrom-Json
$report = [ordered]@{
    schemaVersion = 1
    status = 'ASSEMBLED_PENDING_VISUAL_VALIDATION'
    output = $output
    expectedDurationSeconds = 37.45
    storyInput = $story
    multiCharacterInput = $cast
    transitions = @(
        @{ atSeconds = 2.15; type = 'short_dissolve'; durationSeconds = 0.35; purpose = 'title_to_story' },
        @{ atSeconds = 31.80; type = 'short_dissolve'; durationSeconds = 0.35; purpose = 'story_to_cast' }
    )
    audio = @{ music = $music; surpriseCueSeconds = 15.90; whooshCueSeconds = @(1.95, 31.60) }
    probe = $probe
}
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $metrics -Encoding UTF8
Write-Output "SBZ_SHOWCASE_ASSEMBLED=$output"
