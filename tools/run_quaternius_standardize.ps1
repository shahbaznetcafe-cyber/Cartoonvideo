param(
    [string]$Repository = "D:\flayer\sbz-studio"
)

$candidates = @(
    "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
    "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
    "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
    "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
    "C:\Program Files\Blender Foundation\Blender 4.3\blender.exe"
)
$blender = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $blender) {
    throw "Blender not found. Searched: $($candidates -join '; ')"
}

$source = Join-Path $Repository "work\quaternius\Individual Characters-20260715T071335Z-1-001\Individual Characters\glTF\Adventurer.gltf"
$outputDir = Join-Path $Repository "assets\characters\quaternius_master"
$workDir = Join-Path $Repository "work\character_poc"
New-Item -ItemType Directory -Force -Path $outputDir, $workDir | Out-Null

& $blender --background --python (Join-Path $Repository "blender\standardize_quaternius_master.py") -- `
    $source `
    (Join-Path $outputDir "master_character.glb") `
    (Join-Path $workDir "master_character.blend") `
    (Join-Path $workDir "conversion_report.json")
if ($LASTEXITCODE -ne 0) { throw "Blender standardization failed with exit code $LASTEXITCODE" }
