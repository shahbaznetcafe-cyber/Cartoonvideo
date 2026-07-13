#!/bin/bash
BLENDER="/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"
OUT="D:/flayer/sbz-studio/blender/anim_tomato"; rm -rf "$OUT"
"$BLENDER" --background --python /d/flayer/sbz-studio/blender/animate_character.py -- "D:/flayer/sbz-studio/blender/rigged/blend/tomato.blend" "D:/flayer/sbz-studio/blender/_tomato_open.json" "$OUT" 0 happy 2>&1 | grep -E "ANIM_KEYED|RENDER_DONE|NO_RIG|Error"
ffmpeg -y -framerate 30 -i "$OUT/frame_%04d.png" -i "D:/flayer/sbz-studio/blender/_tomato.mp3" -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest "$OUT/tomato_talking.mp4" -loglevel error
echo "MP4 $OUT/tomato_talking.mp4"
