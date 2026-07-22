import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const repo = path.resolve(process.argv[2] || path.join(import.meta.dirname, '..', '..'));
const video = path.join(repo, 'outputs', 'adventurer_directed_production_scene.mp4');
const metricsPath = path.join(repo, 'reports', 'adventurer_directed_production_metrics.json');
const storyboardPath = path.join(repo, 'reports', 'sbz_adventurer_production_scene.json');
const outputDir = path.join(repo, 'outputs', 'adventurer_directed_production_encoded_milestones');
const manifestPath = path.join(repo, 'reports', 'adventurer_encoded_milestone_manifest.json');
for (const file of [video, metricsPath, storyboardPath]) if (!fs.existsSync(file)) throw new Error(`Missing: ${file}`);
const metrics = JSON.parse(fs.readFileSync(metricsPath));
const storyboard = JSON.parse(fs.readFileSync(storyboardPath));
const frames = [...new Set(metrics.milestoneFrames)].sort((a, b) => a - b);
if (fs.existsSync(outputDir)) fs.rmSync(outputDir, { recursive: true, force: true });
fs.mkdirSync(outputDir, { recursive: true });
const expression = frames.map(frame => `eq(n\\,${frame})`).join('+');
const result = spawnSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-i', video,
  '-vf', `select=${expression}`, '-fps_mode', 'vfr', '-q:v', '2', path.join(outputDir, 'encoded_%02d.jpg')],
{ encoding: 'utf8' });
if (result.status !== 0) throw new Error(`Encoded milestone extraction failed: ${result.stderr}`);
const extracted = fs.readdirSync(outputDir).filter(name => name.endsWith('.jpg')).sort();
if (extracted.length !== frames.length) throw new Error(`Expected ${frames.length} encoded milestones, got ${extracted.length}`);
const sha256 = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const entries = extracted.map((source, index) => {
  const frame = frames[index];
  const beat = storyboard.beats.find(item => frame >= Math.round(item.start * storyboard.fps) &&
    frame < Math.round(item.end * storyboard.fps)) || storyboard.beats.at(-1);
  const target = `${String(index + 1).padStart(2, '0')}_${beat.id}_encoded_f${String(frame).padStart(3, '0')}.jpg`;
  fs.renameSync(path.join(outputDir, source), path.join(outputDir, target));
  return { frame, beatId: beat.id, file: target, sha256: sha256(path.join(outputDir, target)) };
});
const manifest = { schemaVersion: 1, sourceVideo: path.relative(repo, video).replaceAll('\\', '/'),
  sourceVideoSha256: sha256(video), extractedFromEncodedOutput: true, entries };
fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
console.log(`ENCODED_MILESTONES_OK count=${entries.length}`);
