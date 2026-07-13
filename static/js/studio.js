let polling=null, OPTS=null, CUR_JOB=null, CHAR_CAPS={};
let ELEVEN_VOICES_LOADED=false;
const ORDER=['story','voice','asset','render'];
function escHtml(value){
  return String(value==null?'':value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function elevenVoiceLabel(voice){
  const labels=voice.labels||{};
  const traits=[labels.gender,labels.age,labels.accent,labels['use case']||labels.use_case]
    .filter(Boolean).slice(0,3);
  return `${voice.recommended?'⭐ ':''}${voice.name}${traits.length?' · '+traits.join(' · '):''}`;
}
async function loadElevenLabsVoices(force=false){
  if(ELEVEN_VOICES_LOADED && !force) return;
  const sel=document.getElementById('elevenlabs_voice_id');
  const status=document.getElementById('eleven_voice_status');
  sel.disabled=true;
  status.textContent='ElevenLabs account voices load ho rahi hain...';
  try{
    const response=await fetch('/api/voices/elevenlabs'+(force?'?refresh=1':''));
    const data=await response.json();
    if(!response.ok || !data.available) throw new Error(data.error||'voices load nahi huin');
    sel.innerHTML='';
    const recommended=(data.voices||[]).filter(v=>v.recommended);
    const others=(data.voices||[]).filter(v=>!v.recommended);
    const addGroup=(label,voices)=>{
      if(!voices.length) return;
      const group=document.createElement('optgroup'); group.label=label;
      voices.forEach(voice=>{
        const option=document.createElement('option'); option.value=voice.voice_id;
        option.textContent=elevenVoiceLabel(voice);
        option.title=voice.description||''; group.appendChild(option);
      });
      sel.appendChild(group);
    };
    addGroup('⭐ Children & Storytelling — Recommended',recommended);
    addGroup('All ElevenLabs account voices',others);
    if(!data.voices || !data.voices.length){
      const option=document.createElement('option'); option.value='';
      option.textContent='Account mein koi voice available nahi'; sel.appendChild(option);
    }
    const configured=(OPTS.defaults&&OPTS.defaults.elevenlabs_voice_id)||data.selected||'';
    if(configured && [...sel.options].some(option=>option.value===configured)) sel.value=configured;
    else if(data.selected) sel.value=data.selected;
    sel.disabled=!(data.voices&&data.voices.length);
    status.textContent=`${data.voices.length} voices · ${data.recommended_count} children/story recommended · Model: ${data.model}`;
    ELEVEN_VOICES_LOADED=true;
  }catch(error){
    sel.innerHTML='<option value="">ElevenLabs voices unavailable</option>';
    status.textContent='⚠️ '+error.message;
    sel.disabled=true; ELEVEN_VOICES_LOADED=false;
  }
}
function syncVoiceProviderUI(){
  const provider=document.getElementById('tts_provider').value;
  document.getElementById('edge_voice_group').classList.toggle('hidden',provider!=='edge');
  document.getElementById('eleven_voice_group').classList.toggle('hidden',provider!=='elevenlabs');
  if(provider==='elevenlabs') loadElevenLabsVoices();
}
function capabilityMarkup(cap){
  if(!cap) return '<span class="capBadge bad">NOT VALIDATED</span>';
  const tier=cap.tier||'UNSUPPORTED', pct=Number(cap.compatibility_percent||0);
  const cls=!cap.valid_glb?'bad':tier==='FULL_FACIAL'?'full':tier==='VISEME_FACE'?'viseme':tier==='LEGACY_JAW'?'legacy':'';
  const vis=(cap.visemes&&cap.visemes.missing)||[], face=(cap.facial&&cap.facial.missing)||[];
  const warns=(cap.warnings||[]).map(w=>escHtml(w.message||w)).join('<br>');
  const errs=(cap.errors||[]).map(e=>escHtml(e.message||e)).join('<br>');
  return `<details class="capDetails"><summary><span class="capBadge ${cls}">${escHtml(tier)}</span> ${pct}% compatibility</summary>`
    +`<div class="capBody"><b>GLB:</b> ${cap.valid_glb?'Valid':'Invalid'} · <b>Bones:</b> ${(cap.skeleton_bones||[]).length}`
    +` · <b>Skinned meshes:</b> ${(cap.skinned_meshes||[]).length}<br>`
    +`<b>Mixamo:</b> ${cap.mixamo_compatible?'Compatible':'No'} · <b>TalkingHead strict:</b> ${cap.talkinghead_compatible?'Compatible':'No'}<br>`
    +`<b>Visemes:</b> ${15-vis.length}/15${vis.length?`<br><b>Missing:</b> ${escHtml(vis.join(', '))}`:''}`
    +`<br><b>Facial:</b> ${9-face.length}/9${face.length?`<br><b>Missing:</b> ${escHtml(face.join(', '))}`:''}`
    +(warns?`<br><span style="color:#fbbf24"><b>Warning:</b> ${warns}</span>`:'')
    +(errs?`<br><span style="color:#fca5a5"><b>Error:</b> ${errs}</span>`:'')+`</div></details>`;
}
async function load3dValidation(){
  try{
    const payload=await (await fetch('/api/characters3d/validation')).json();
    CHAR_CAPS={};
    (payload.characters||[]).forEach(cap=>{
      const blend=((cap.character&&cap.character.blend)||'').replace(/\\/g,'/').split('/').pop().replace(/\.(blend|glb)$/i,'').toLowerCase();
      if(blend) CHAR_CAPS[blend]=cap;
    });
  }catch(e){ CHAR_CAPS={}; }
}
async function stopJob(){
  if(!CUR_JOB) return;
  const b=document.getElementById('stopBtn'); b.disabled=true; b.textContent='⏹ Ruk raha hai...';
  try{ await fetch('/api/stop/'+CUR_JOB,{method:'POST'}); }catch(e){}
}

async function load(){
  OPTS = await (await fetch('/api/options')).json();
  const sel=document.getElementById('style');
  OPTS.styles.forEach(s=>{const o=document.createElement('option');o.value=s;o.textContent=s;
    if(s===OPTS.defaults.style)o.selected=true; sel.appendChild(o);});
  const p=OPTS.providers;
  document.getElementById('provStatus').textContent=
    `LLM:${p.llm.join('/')} · IMG:${p.image.join('/')} · TTS:${p.tts.join('/')}`;
  if(OPTS.defaults && OPTS.defaults.urdu_accent){ const ua=document.getElementById('urdu_accent'); if(ua) ua.value=OPTS.defaults.urdu_accent; }
  const tts=document.getElementById('tts_provider');
  if(OPTS.defaults && OPTS.defaults.tts_provider) tts.value=OPTS.defaults.tts_provider;
  tts.addEventListener('change',syncVoiceProviderUI);
  document.getElementById('refresh_eleven_voices').addEventListener('click',()=>loadElevenLabsVoices(true));
  syncVoiceProviderUI();
  if(OPTS.defaults && OPTS.defaults.render_engine){ const re=document.getElementById('render_engine'); if(re) re.value=OPTS.defaults.render_engine; }
  if(OPTS.defaults){
    document.getElementById('cap_enabled').checked=!!OPTS.defaults.subtitles_on;
    document.getElementById('intro_on').checked=!!OPTS.defaults.intro_on;
  }
  loadTemplates();
  checkResumable();       // crash/close ke baad adhoore projects dikhao
  loadProjectsList();     // purane projects ka count + list
  initScriptTabs();       // script banane ke 4 tareeqe (tabs) switch karo
}

// Script card ke tabs (Idea se / Long-Form / Characters / Template) — ek waqt ek panel
function initScriptTabs(){
  const tabs=document.querySelectorAll('#scriptTabs .tab');
  const panels=document.querySelectorAll('#scriptCard .tabpanel');
  tabs.forEach(t=>t.addEventListener('click',()=>{
    tabs.forEach(x=>x.classList.remove('on')); t.classList.add('on');
    const k=t.dataset.t;
    panels.forEach(p=>p.classList.toggle('hidden', p.dataset.t!==k));
  }));
}

let TPL_SEL=null, TPLS=[], CHARS=[], CHAR_SEL=new Set();
async function loadTemplates(){
  TPLS = await (await fetch('/api/story-templates')).json();
  CHARS = await (await fetch('/api/characters')).json();
  const g=document.getElementById('tplGrid'); g.innerHTML='';
  TPLS.forEach(t=>{
    const b=document.createElement('button');
    b.className='tplChip'; b.dataset.id=t.id;
    b.innerHTML=`<div style="font-size:18px">${t.emoji}</div><div style="font-size:11px;line-height:1.2">${t.name}</div>`;
    b.title=t.desc;
    b.onclick=()=>selectTemplate(t.id);
    g.appendChild(b);
  });
  const cg=document.getElementById('tplChars'); cg.innerHTML='';
  CHARS.forEach(c=>{
    const b=document.createElement('button');
    b.className='tplChip'; b.dataset.cid=c.id; b.style.padding='6px 2px';
    b.innerHTML=`<div style="font-size:15px">${c.emoji}</div><div style="font-size:10px">${c.name}</div>`;
    b.onclick=()=>toggleChar(c.id);
    cg.appendChild(b);
  });
}
function toggleChar(cid){
  if(CHAR_SEL.has(cid)) CHAR_SEL.delete(cid); else CHAR_SEL.add(cid);
  document.querySelectorAll('#tplChars .tplChip').forEach(c=>c.classList.toggle('on',CHAR_SEL.has(c.dataset.cid)));
}
function selectTemplate(id){
  TPL_SEL=TPLS.find(t=>t.id===id);
  document.querySelectorAll('#tplGrid .tplChip').forEach(c=>c.classList.toggle('on',c.dataset.id===id));
  document.getElementById('tplPanel').classList.remove('hidden');
  document.getElementById('tplName').textContent=`${TPL_SEL.emoji} ${TPL_SEL.name_en}`;
  document.getElementById('tplTopic').placeholder='e.g. '+TPL_SEL.sample_topic;
  // template ke default characters pre-select karo
  CHAR_SEL=new Set(TPL_SEL.chars);
  document.querySelectorAll('#tplChars .tplChip').forEach(c=>c.classList.toggle('on',CHAR_SEL.has(c.dataset.cid)));
  document.getElementById('tplMsg').textContent=TPL_SEL.desc;
}
async function genFromTemplate(){
  if(!TPL_SEL) return;
  const btn=document.getElementById('tplGenBtn'), msg=document.getElementById('tplMsg');
  if(CHAR_SEL.size<2){ msg.innerHTML='<span class="err">Kam az kam 2 characters chuno.</span>'; return; }
  btn.disabled=true; btn.textContent='⏳ Likh raha hoon...';
  msg.textContent='AI script likh raha hai...';
  try{
    const body={template_id:TPL_SEL.id, topic:document.getElementById('tplTopic').value,
      language:document.getElementById('tplLang').value,
      length:segVal('tplLenSeg')||'medium', characters:[...CHAR_SEL]};
    const j=await (await fetch('/api/story-templates/generate',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).json();
    if(j.error){ msg.innerHTML='<span class="err">'+j.error+'</span>'; }
    else{
      document.getElementById('script').value=j.script;
      msg.innerHTML='<span style="color:var(--green)">✅ Script ready — upar Script box mein aa gaya. Edit kar sakte ho, phir Generate Video.</span>';
      document.getElementById('script').scrollIntoView({behavior:'smooth',block:'center'});
    }
  }catch(e){ msg.innerHTML='<span class="err">Fail: '+e+'</span>'; }
  btn.disabled=false; btn.textContent='✍️ Script Likho';
}

// Phase 2 — free-form: bina template, seedha idea se script
async function genFreeform(){
  const btn=document.getElementById('ffGenBtn'), msg=document.getElementById('ffMsg');
  const idea=document.getElementById('ffIdea').value.trim();
  if(!idea){ msg.innerHTML='<span class="err">Pehle apna idea likhein.</span>'; return; }
  const pro=document.getElementById('ffPro').checked;
  btn.disabled=true; btn.textContent=pro?'⏳ Plan → Draft → Polish...':'⏳ Soch raha hoon...';
  msg.innerHTML='<span style="color:var(--muted)">'+(pro?'Pro pipeline: plan, hook variants, draft, polish...':'AI story bana raha hai...')+'</span>';
  try{
    const body={idea, genre:document.getElementById('ffGenre').value,
      language:document.getElementById('ffLang').value,
      length:segVal('ffLenSeg')||'medium', quality:pro?'pro':'fast'};
    const j=await (await fetch('/api/freeform',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).json();
    if(j.error){ msg.innerHTML='<span class="err">'+j.error+'</span>'; }
    else{
      document.getElementById('script').value=j.script||'';
      const cast=(j.cast||[]).join(', ');
      msg.innerHTML='<span style="color:var(--green)">✅ '+(j.title?('“'+j.title+'” '):'')
        +'</span><span style="color:var(--muted)">'
        +(j.genre?('['+j.genre+'] '):'')+(cast?('· '+cast):'')
        +' — Script box mein aa gaya. Edit karke Generate.</span>';
      document.getElementById('script').scrollIntoView({behavior:'smooth',block:'center'});
    }
  }catch(e){ msg.innerHTML='<span class="err">Fail: '+e+'</span>'; }
  btn.disabled=false; btn.textContent='⚡ Script Banao';
}

// Phase 3 — long-form multi-scene story
async function genLongform(){
  const btn=document.getElementById('lfGenBtn'), msg=document.getElementById('lfMsg'),
    out=document.getElementById('lfOutline');
  const idea=document.getElementById('lfIdea').value.trim();
  if(!idea){ msg.innerHTML='<span class="err">Pehle apna idea likhein.</span>'; return; }
  btn.disabled=true; btn.textContent='⏳ Kahani ban rahi hai...';
  msg.innerHTML='<span style="color:var(--muted)">Outline + scenes likhe ja rahe hain (~20–40s)...</span>';
  out.innerHTML='';
  try{
    const body={idea, genre:document.getElementById('lfGenre').value,
      language:document.getElementById('lfLang').value,
      minutes:segVal('lfMinSeg')||'5min'};
    const j=await (await fetch('/api/longform',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).json();
    if(j.error){ msg.innerHTML='<span class="err">'+j.error+'</span>'; }
    else{
      document.getElementById('script').value=j.script||'';
      const cast=(j.cast||[]).join(', ');
      msg.innerHTML='<span style="color:var(--green)">✅ '+(j.title?('“'+j.title+'” '):'')
        +'</span><span style="color:var(--muted)">'+(j.genre?('['+j.genre+'] '):'')
        +(cast?('· '+cast):'')+'</span>';
      if(j.logline) msg.innerHTML+='<div style="color:var(--muted);margin-top:4px">'+j.logline+'</div>';
      // scene outline chips
      if(j.scenes&&j.scenes.length){
        out.innerHTML='<div style="font-weight:700;margin-bottom:4px">🎬 '+j.scenes.length
          +' Scenes:</div>'+j.scenes.map((s,i)=>'<div style="padding:3px 0;border-bottom:1px solid rgba(255,255,255,.06)"><b style="color:var(--green)">'
          +(i+1)+'. '+(s.location||'')+'</b> <span style="color:var(--muted)">— '+(s.goal||'')+'</span></div>').join('');
      }
      document.getElementById('script').scrollIntoView({behavior:'smooth',block:'center'});
    }
  }catch(e){ msg.innerHTML='<span class="err">Fail: '+e+'</span>'; }
  btn.disabled=false; btn.textContent='🎬 Story Likho';
}

// ---------- Phase 4: Characters & Series ----------
let LIB_CHARS=[], SERIES=[], CUR_SERIES=null, NEW_CAST=new Set();
async function loadLib(){
  LIB_CHARS=await (await fetch('/api/characters-lib')).json();
  SERIES=await (await fetch('/api/series')).json();
  renderCharList(); renderSeriesSel(); renderCastPicker();
}
function renderCharList(){
  const el=document.getElementById('charList'); el.innerHTML='';
  if(!LIB_CHARS.length){ el.innerHTML='<span style="color:var(--muted);font-size:12px">Abhi koi character nahi.</span>'; return; }
  LIB_CHARS.forEach(c=>{
    const chip=document.createElement('div');
    chip.style.cssText='background:rgba(255,255,255,.06);border-radius:14px;padding:3px 8px;font-size:12px;display:flex;align-items:center;gap:6px';
    chip.innerHTML='<b>'+c.name+'</b><span style="color:var(--muted)">'+(c.trait?('· '+c.trait.slice(0,24)):'')+'</span><span style="cursor:pointer;color:var(--err)" onclick="delChar(\''+c.id+'\')">✕</span>';
    chip.title=(c.trait||'')+(c.catchphrase?(' — "'+c.catchphrase+'"'):'');
    el.appendChild(chip);
  });
}
async function addChar(){
  const name=document.getElementById('chName').value.trim();
  if(!name){ alert('Character ka naam likhein'); return; }
  await fetch('/api/characters-lib',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name, gender:document.getElementById('chGender').value,
      trait:document.getElementById('chTrait').value, catchphrase:document.getElementById('chPhrase').value})});
  document.getElementById('chName').value='';document.getElementById('chTrait').value='';document.getElementById('chPhrase').value='';
  await loadLib();
}
async function delChar(cid){
  await fetch('/api/characters-lib/'+cid,{method:'DELETE'}); await loadLib();
}
function renderSeriesSel(){
  const sel=document.getElementById('serSel'); const cur=sel.value;
  sel.innerHTML='<option value="">— Select series —</option>';
  SERIES.forEach(s=>{const o=document.createElement('option');o.value=s.id;
    o.textContent=s.name+' ('+s.episodes+' ep)';sel.appendChild(o);});
  sel.value=cur;
}
function renderCastPicker(){
  const el=document.getElementById('serCast'); el.innerHTML='';
  if(!LIB_CHARS.length){ el.innerHTML='<span style="color:var(--muted);font-size:12px">Pehle character add karein.</span>'; return; }
  LIB_CHARS.forEach(c=>{
    const b=document.createElement('button');
    b.className='tplChip'; b.style.cssText='padding:4px 8px;font-size:12px';
    b.textContent=c.name; b.classList.toggle('on',NEW_CAST.has(c.id));
    b.onclick=()=>{NEW_CAST.has(c.id)?NEW_CAST.delete(c.id):NEW_CAST.add(c.id); b.classList.toggle('on');};
    el.appendChild(b);
  });
}
function toggleNewSeries(){ document.getElementById('newSeriesBox').classList.toggle('hidden'); NEW_CAST=new Set(); renderCastPicker(); }
async function createSeries(){
  const name=document.getElementById('serName').value.trim();
  if(!name){ alert('Series naam likhein'); return; }
  if(NEW_CAST.size<1){ alert('Kam az kam 1 cast character chuno'); return; }
  const r=await (await fetch('/api/series',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name, premise:document.getElementById('serPremise').value,
      genre:document.getElementById('serGenre').value, language:document.getElementById('serLang').value,
      cast:[...NEW_CAST]})})).json();
  if(r.error){ alert(r.error); return; }
  document.getElementById('newSeriesBox').classList.add('hidden');
  document.getElementById('serName').value='';document.getElementById('serPremise').value='';
  await loadLib();
  document.getElementById('serSel').value=r.id; selectSeries(r.id);
}
async function selectSeries(sid){
  if(!sid){ document.getElementById('epBox').classList.add('hidden'); CUR_SERIES=null; return; }
  CUR_SERIES=await (await fetch('/api/series/'+sid)).json();
  document.getElementById('epBox').classList.remove('hidden');
  const castNames=(CUR_SERIES.cast||[]).map(cid=>{const c=LIB_CHARS.find(x=>x.id===cid);return c?c.name:cid;}).join(', ');
  document.getElementById('serInfo').innerHTML='<b style="color:var(--green)">'+CUR_SERIES.name+'</b> — Cast: '+castNames
    +(CUR_SERIES.premise?('<br>'+CUR_SERIES.premise):'');
  const eps=CUR_SERIES.episodes||[];
  document.getElementById('epHistory').innerHTML = eps.length
    ? '<b>📼 '+eps.length+' Episodes:</b>'+eps.map(e=>'<div style="padding:2px 0"><b>Ep '+e.num+':</b> '+e.title+' <span style="color:var(--muted)">— '+(e.summary||'').slice(0,80)+'</span></div>').join('')
    : '<span style="color:var(--muted)">Abhi koi episode nahi — Ep 1 banao.</span>';
  document.getElementById('epGenBtn').textContent='🎬 Generate Episode '+(eps.length+1);
}
async function genEpisode(){
  if(!CUR_SERIES) return;
  const btn=document.getElementById('epGenBtn'), msg=document.getElementById('epMsg');
  btn.disabled=true; btn.textContent='⏳ Episode ban raha...';
  msg.innerHTML='<span style="color:var(--muted)">Cast + pichhle episodes ka continuity use ho raha hai...</span>';
  try{
    const j=await (await fetch('/api/series/'+CUR_SERIES.id+'/episode',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({idea:document.getElementById('epIdea').value, length:segVal('epLenSeg')||'medium'})})).json();
    if(j.error){ msg.innerHTML='<span class="err">'+j.error+'</span>'; }
    else{
      document.getElementById('script').value=j.script||'';
      msg.innerHTML='<span style="color:var(--green)">✅ Episode '+j.episode_num+': “'+j.title+'”</span>'
        +'<div style="color:var(--muted);margin-top:3px">'+(j.summary||'')+'</div>';
      document.getElementById('epIdea').value='';
      await selectSeries(CUR_SERIES.id);  // history refresh
      document.getElementById('script').scrollIntoView({behavior:'smooth',block:'center'});
    }
  }catch(e){ msg.innerHTML='<span class="err">Fail: '+e+'</span>'; }
  btn.disabled=false;
}
loadLib();
load();

// segmented buttons
document.querySelectorAll('.seg').forEach(seg=>{
  seg.querySelectorAll('button').forEach(b=>b.onclick=()=>{
    seg.querySelectorAll('button').forEach(x=>x.classList.remove('on'));
    b.classList.add('on');
  });
});
function segVal(id){const e=document.querySelector('#'+id+' button.on');return e?e.dataset.v:null;}

function collectSettings(){
  const ttsProvider=document.getElementById('tts_provider').value;
  return {
    style: document.getElementById('style').value,
    aspect: segVal('aspectSeg'),
    quality: document.getElementById('quality').value,
    fps: document.getElementById('fps').value,
    fast_preview: document.getElementById('fast_preview').checked,
    motion_preset: segVal('motionSeg'),
    render_mode: segVal('modeSeg'),
    story_mode: segVal('storySeg'),
    multi_char: document.getElementById('multiChar').checked,
    render_engine: document.getElementById('render_engine').value,
    gpu: document.getElementById('gpu_encode').checked ? 'auto' : 'off',
    vignette: document.getElementById('vignette').checked,
    subtitles_on: document.getElementById('cap_enabled').checked,
    intro_on: document.getElementById('intro_on').checked,
    outro_on: true,
    tts_provider: ttsProvider,
    urdu_accent: ttsProvider==='edge' ? document.getElementById('urdu_accent').value : '',
    elevenlabs_voice_id: ttsProvider==='elevenlabs' ? document.getElementById('elevenlabs_voice_id').value : '',
    voice_volume: document.getElementById('voice_volume').value,
    music_volume: document.getElementById('music_volume').value,
    captions: {
      enabled: document.getElementById('cap_enabled').checked,
      words_per_group: document.getElementById('cap_words').value,
      font_size: document.getElementById('cap_size').value,
      position: segVal('posSeg'),
      highlight_color: document.getElementById('cap_hl').value,
      highlight_style: segVal('hlSeg'),
      per_speaker_color: document.getElementById('cap_perspk').checked,
    }
  };
}

async function suggestStyle(){
  const script=document.getElementById('script').value.trim();
  if(script.length<10){alert('Pehle script likhein');return;}
  const r=await (await fetch('/api/suggest-style',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({script})})).json();
  if(r.style) document.getElementById('style').value=r.style;
}

function _scriptLang(){ const t=document.getElementById('tplLang'); return t?t.value:'roman_urdu'; }

async function analyzeScript(){
  const script=document.getElementById('script').value.trim();
  const fb=document.getElementById('scriptFeedback');
  if(script.length<10){fb.innerHTML='<span class="err">Pehle script likhein</span>';return;}
  fb.innerHTML='<span style="color:var(--muted)">🔍 Analyze ho raha...</span>';
  try{
    const r=await (await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({script,language:_scriptLang()})})).json();
    if(r.error){fb.innerHTML='<span class="err">'+r.error+'</span>';return;}
    let h='<div style="border:1px solid rgba(255,255,255,.12);border-radius:8px;padding:8px">';
    if(r.hook_score!=null){const c=r.hook_score>=7?'var(--green)':(r.hook_score>=5?'#FBBF24':'var(--red)');
      h+=`<div><b>Hook:</b> <span style="color:${c}">${r.hook_score}/10</span> &nbsp; <b>Pacing:</b> ${r.pacing||'-'} &nbsp; <b>Music:</b> ${r.music_mood||'-'}</div>`;}
    if(r.title_ideas&&r.title_ideas.length){h+='<div style="margin-top:5px"><b>📌 Title ideas:</b><ul style="margin:3px 0 0 16px;padding:0">'+r.title_ideas.map(t=>`<li style="cursor:pointer" onclick="navigator.clipboard.writeText('${(t+'').replace(/'/g,"")}')">${t}</li>`).join('')+'</ul></div>';}
    if(r.improvements&&r.improvements.length){h+='<div style="margin-top:5px"><b>💡 Behtari:</b><ul style="margin:3px 0 0 16px;padding:0">'+r.improvements.map(t=>`<li>${t}</li>`).join('')+'</ul></div>';}
    if(r.strong_points&&r.strong_points.length){h+='<div style="margin-top:5px;color:var(--green)"><b>✅ Achha:</b> '+r.strong_points.join(', ')+'</div>';}
    h+='</div>';
    fb.innerHTML=h;
  }catch(e){fb.innerHTML='<span class="err">Analyze fail: '+e+'</span>';}
}

async function improveScript(){
  const el=document.getElementById('script'); const script=el.value.trim();
  const fb=document.getElementById('scriptFeedback');
  if(script.length<10){fb.innerHTML='<span class="err">Pehle script likhein</span>';return;}
  fb.innerHTML='<span style="color:var(--muted)">✨ Behtar likha ja raha...</span>';
  try{
    const r=await (await fetch('/api/improve',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({script,language:_scriptLang()})})).json();
    if(r.script&&!r.script.startsWith('[error]')){
      el.value=r.script;
      fb.innerHTML='<span style="color:var(--green)">✅ Script behtar ho gaya (upar box mein). Analyze karke dekh lein.</span>';
    } else { fb.innerHTML='<span class="err">'+(r.script||'fail')+'</span>'; }
  }catch(e){fb.innerHTML='<span class="err">Improve fail: '+e+'</span>';}
}

// Track C — YouTube Package (metadata)
function _copy(t){ navigator.clipboard.writeText(t).catch(()=>{}); }
async function genPackage(){
  const script=document.getElementById('script').value.trim();
  const pk=document.getElementById('pkgPanel');
  if(script.length<20){ pk.innerHTML='<span class="err">Pehle script banayein.</span>'; return; }
  pk.innerHTML='<span style="color:var(--muted)">📦 YouTube package ban raha (titles, description, tags, thumbnail)...</span>';
  try{
    const m=await (await fetch('/api/metadata',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({script,language:_scriptLang()})})).json();
    if(m.error){ pk.innerHTML='<span class="err">'+m.error+'</span>'; return; }
    const box=(label,content)=>`<div style="margin-top:8px"><div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:3px">${label}</div>${content}</div>`;
    const titles=(m.titles||[]).map(t=>`<div style="display:flex;gap:6px;align-items:center;padding:3px 0"><span style="flex:1">${t}</span><button class="btn btn-sm" style="padding:1px 7px" onclick="_copy(${JSON.stringify(t).replace(/"/g,'&quot;')})">copy</button></div>`).join('');
    const tags=(m.tags||[]).map(t=>`<span style="background:var(--card2,rgba(255,255,255,.06));border-radius:12px;padding:2px 8px;font-size:11px;margin:2px;display:inline-block">${t}</span>`).join('');
    const chapters=(m.chapters||[]).length?box('Chapters',(m.chapters||[]).map(c=>`<div style="font-size:12px">${c}</div>`).join('')):'';
    pk.innerHTML='<div style="border:1px solid rgba(255,255,255,.12);border-radius:10px;padding:10px 12px;font-size:13px">'
      +'<div style="font-weight:700;color:#a78bfa">📦 YouTube Package</div>'
      +box('🏷️ Thumbnail text','<div style="font-weight:800;font-size:18px;letter-spacing:.02em">'+(m.thumbnail_text||'')+'</div>')
      +box('📝 Titles (5)',titles)
      +box('📄 Description','<div style="white-space:pre-wrap">'+(m.description||'')+'</div><button class="btn btn-sm" style="margin-top:4px;padding:1px 8px" onclick="_copy('+JSON.stringify(m.description||'').replace(/"/g,'&quot;')+')">copy description</button>')
      +box('🔖 Tags',tags+'<div><button class="btn btn-sm" style="margin-top:5px;padding:1px 8px" onclick="_copy('+JSON.stringify((m.tags||[]).join(', ')).replace(/"/g,'&quot;')+')">copy all tags</button></div>')
      +box('📌 Pinned comment',(m.pinned_comment||''))
      +chapters
      +'</div>';
  }catch(e){ pk.innerHTML='<span class="err">Package fail: '+e+'</span>'; }
}

function setStages(active,i,total,msg,fin){
  const ai=ORDER.indexOf(active);
  document.querySelectorAll('#steps li').forEach(li=>{
    const si=ORDER.indexOf(li.dataset.s); li.classList.remove('active','done');
    const m=li.querySelector('.msg');
    if(fin||si<ai){li.classList.add('done');}
    else if(si===ai){li.classList.add('active'); m.textContent=(total>1?`${i}/${total} `:'')+(msg||'');}
  });
}

const EMOTIONS=['neutral','happy','sad','angry','excited','scared','confused','thinking','surprised'];
let PLAN=null;

let COSTUMES=[], ACCESSORIES=[], HELD=[];
async function preview(){
  const script=document.getElementById('script').value.trim();
  if(script.length<10){alert('Script likhein');return;}
  const btn=document.getElementById('previewBtn');
  btn.disabled=true; btn.textContent='⏳ Plan bana raha hoon...';
  document.getElementById('errMsg').classList.add('hidden');
  try{
    if(!COSTUMES.length){ try{ COSTUMES=await (await fetch('/api/costumes')).json(); }catch(e){} }
    if(!ACCESSORIES.length){ try{ ACCESSORIES=await (await fetch('/api/accessories')).json(); }catch(e){} }
    if(!HELD.length){ try{ HELD=await (await fetch('/api/held')).json(); }catch(e){} }
    if(!Object.keys(CHAR_CAPS).length){ await load3dValidation(); }
    const j=await (await fetch('/api/preview',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({script})})).json();
    if(j.error){ showErr(j.error); }
    else { PLAN=j; renderPreview(j); }
  }catch(e){ showErr('Preview fail: '+e); }
  btn.disabled=false; btn.textContent='👁️ Preview & Edit';
}

function renderPreview(p){
  document.getElementById('pvTitle').textContent=p.title||'';
  // characters
  const cc=document.getElementById('pvChars'); cc.innerHTML='';
  const grpOpts=(arr)=>{
    const g={}; arr.forEach(c=>{(g[c.group||'x']=g[c.group||'x']||[]).push(c);});
    return Object.keys(g).map(k=>{
      const inner=g[k].map(c=>`<option value="${c.id}">${c.label}</option>`).join('');
      return k==='—' ? inner : `<optgroup label="${k}">${inner}</optgroup>`;
    }).join('');
  };
  const costOpts=grpOpts(COSTUMES), accOpts=grpOpts(ACCESSORIES), heldOpts=grpOpts(HELD);
  p.characters.forEach(ch=>{
    const opts=p.veggies.map(v=>`<option value="${v.name}" ${v.package===ch.package?'selected':''}>${v.emoji} ${v.name}</option>`).join('');
    const d=document.createElement('div'); d.className='pvRow'; d.dataset.cid=ch.id;
    const cap=CHAR_CAPS[String(ch.package||'').toLowerCase()]||ch.capability;
    d.innerHTML=`<img src="${ch.avatar||''}" class="pvAv" onerror="this.style.visibility='hidden'">`
      +`<div style="flex:1;min-width:70px"><b>${ch.name}</b> <span style="color:var(--muted);font-size:11px">${ch.voice||''}</span><div class="capSlot">${capabilityMarkup(cap)}</div></div>`
      +`<select class="pvVeg" title="3D character" style="width:100px">${opts}</select>`
      +`<select class="pvCostume" title="Costume (rang)" style="width:100px">${costOpts}</select>`
      +`<select class="pvAcc" title="Pehnawa (head/face)" style="width:100px">${accOpts}</select>`
      +`<select class="pvHeld" title="Haath mein" style="width:100px">${heldOpts}</select>`;
    cc.appendChild(d);
    d.querySelector('.pvVeg').addEventListener('change',ev=>{
      const selected=p.veggies.find(v=>v.name===ev.target.value);
      const next=selected&&CHAR_CAPS[String(selected.package||'').toLowerCase()];
      d.querySelector('.capSlot').innerHTML=capabilityMarkup(next);
    });
  });
  // scenes + lines
  const sc=document.getElementById('pvScenes'); sc.innerHTML='';
  p.scenes.forEach((s,si)=>{
    const box=document.createElement('div'); box.className='pvScene'; box.dataset.si=si;
    let h=`<div style="font-size:12px;color:var(--muted)">Scene ${s.id} · ${s.mood||''}</div>`
      +`<label style="font-size:11px">Background</label>`
      +`<input class="pvBg" value="${(s.background_prompt||'').replace(/"/g,'&quot;')}">`;
    (s.lines||[]).forEach((ln,li)=>{
      const eo=EMOTIONS.map(e=>`<option ${e===(ln.emotion||'neutral')?'selected':''}>${e}</option>`).join('');
      h+=`<div class="pvLine" data-li="${li}" style="display:flex;gap:5px;margin-top:5px;align-items:center">`
        +`<span style="min-width:62px;font-size:11px;color:var(--green)">${ln.speaker}</span>`
        +`<select class="pvEmo" style="width:92px">${eo}</select>`
        +`<input class="pvText" style="flex:1" value="${(ln.text||'').replace(/"/g,'&quot;')}"></div>`;
    });
    box.innerHTML=h; sc.appendChild(box);
  });
  document.getElementById('previewCard').classList.remove('hidden');
  document.getElementById('previewCard').scrollIntoView({behavior:'smooth',block:'start'});
}

function collectEditedParsed(){
  const p=JSON.parse(JSON.stringify(PLAN.parsed));   // deep copy
  // veggie overrides
  const ov={}, cos={}, acc={}, held={};
  document.querySelectorAll('#pvChars .pvRow').forEach(r=>{
    ov[r.dataset.cid]=r.querySelector('.pvVeg').value;
    const cv=r.querySelector('.pvCostume');
    if(cv && cv.value && cv.value!=='default') cos[r.dataset.cid]=cv.value;
    const av=r.querySelector('.pvAcc');
    if(av && av.value && av.value!=='none') acc[r.dataset.cid]=av.value;
    const hv=r.querySelector('.pvHeld');
    if(hv && hv.value && hv.value!=='none') held[r.dataset.cid]=hv.value;
  });
  p.char_overrides=ov;
  p.costumes=cos;
  p.accessories=acc;
  p.held=held;
  // scenes: bg + lines (emotion, text)
  document.querySelectorAll('#pvScenes .pvScene').forEach(box=>{
    const s=p.scenes[+box.dataset.si];
    s.background_prompt=box.querySelector('.pvBg').value;
    box.querySelectorAll('.pvLine').forEach(le=>{
      const ln=s.lines[+le.dataset.li];
      ln.emotion=le.querySelector('.pvEmo').value;
      ln.text=le.querySelector('.pvText').value;
    });
  });
  return p;
}

async function confirmGenerate(){ startJob(collectEditedParsed()); }

async function generate(){ startJob(null); }

async function checkResumable(){
  try{
    const list=await (await fetch('/api/resumable')).json();
    const card=document.getElementById('resumeCard'), el=document.getElementById('resumeList');
    if(!list.length){ card.classList.add('hidden'); return; }
    el.innerHTML=list.map(p=>{
      const st=p.state==='error'?'⚠️ ruk gaya':'⏳ adhoora';
      return `<div style="display:flex;gap:8px;align-items:center;padding:6px 0;border-top:1px solid rgba(255,255,255,.06)">
        <div style="flex:1"><b>${p.title||p.name}</b> <span style="color:var(--muted);font-size:11px">${st} · stage: ${p.stage||'?'} · ${p.done_clips||0} clips · ${p.updated||''}</span></div>
        <button class="btn btn-green btn-sm" onclick="resumeProject('${p.name}')">▶ Resume</button>
        <button class="btn btn-sm" style="background:var(--err,#b33)" onclick="dropProject('${p.name}',this)">🗑</button>
      </div>`;
    }).join('');
    card.classList.remove('hidden');
  }catch(e){}
}
let PROJECTS_SHOWN=false;
async function loadProjectsList(){
  try{
    const list=await (await fetch('/api/projects')).json();
    document.getElementById('projCount').textContent='('+list.length+')';
    const el=document.getElementById('projList');
    if(!list.length){ el.innerHTML='<div style="color:var(--muted);font-size:12px">Abhi koi project nahi.</div>'; return; }
    el.innerHTML=list.map(p=>{
      const d=p.created||new Date((p.mtime||0)*1000).toLocaleString();
      // complete -> Video; adhoora -> Resume (usi project ko jahan tak bana wahin se aage)
      const act=p.has_video
        ? `<button class="btn btn-sm" style="background:#2563eb" onclick="playProject('${p.name}')">▶ Video</button>`
        : `<button class="btn btn-sm" style="background:#f59e0b;color:#000" onclick="resumeProject('${p.name}')">▶ Resume</button>`;
      return `<div style="display:flex;gap:6px;align-items:center;padding:6px 0;border-top:1px solid rgba(255,255,255,.06)">
        <div style="flex:1;min-width:0"><b>${p.title||p.name}</b> ${p.has_video?'':'<span style="color:#f59e0b;font-size:10px">● adhoora</span>'}<br><span style="color:var(--muted);font-size:11px">${p.characters||0} chars · ${p.scenes||0} scenes · ${d}</span></div>
        <button class="btn btn-green btn-sm" onclick="openProject('${p.name}')">📂 Load</button>
        ${act}
        <button class="btn btn-sm" style="background:var(--err,#b33)" onclick="delProject('${p.name}',event)">🗑</button>
      </div>`;
    }).join('');
  }catch(e){}
}
function toggleProjects(){
  const el=document.getElementById('projList');
  PROJECTS_SHOWN=!PROJECTS_SHOWN;
  el.classList.toggle('hidden',!PROJECTS_SHOWN);
  if(PROJECTS_SHOWN) loadProjectsList();
}
async function openProject(name){
  const p=await (await fetch('/api/project/'+encodeURIComponent(name))).json();
  if(p.error){ alert(p.error); return; }
  document.getElementById('script').value=p.script||'';
  PLAN = p.parsed ? {parsed:p.parsed} : null;   // preview/generate isi plan par
  if(p.settings){
    if(p.settings.subtitles_on!==undefined) document.getElementById('cap_enabled').checked=!!p.settings.subtitles_on;
    else if(p.settings.captions) document.getElementById('cap_enabled').checked=!!p.settings.captions.enabled;
    if(p.settings.intro_on!==undefined) document.getElementById('intro_on').checked=!!p.settings.intro_on;
  }
  document.getElementById('script').scrollIntoView({behavior:'smooth',block:'center'});
  const fb=document.getElementById('scriptFeedback');
  if(fb) fb.innerHTML='<span style="color:var(--green)">✅ "'+(p.title||name)+'" load ho gaya — script box mein. Edit karke Preview/Generate karo'+(p.has_video?', ya ▶ Video se purani dekho.':'.')+'</span>';
  if(p.has_video) playProject(name);
}
function playProject(name){
  document.getElementById('resultCard').classList.remove('hidden');
  document.getElementById('rTitle').textContent=name;
  document.getElementById('rVideo').src='/projects/'+name+'/final.mp4?t='+Date.now();
  document.getElementById('rDownload').href='/projects/'+name+'/final.mp4';
  document.getElementById('resultCard').scrollIntoView({behavior:'smooth',block:'center'});
}
async function delProject(name,ev){
  if(ev) ev.stopPropagation();
  if(!confirm('"'+name+'" delete karein? (video + saara data)')) return;
  await fetch('/api/projects/'+encodeURIComponent(name),{method:'DELETE'});
  loadProjectsList();
}
async function resumeProject(name){
  const btn=document.getElementById('genBtn'); if(btn) btn.disabled=true;
  document.getElementById('progressCard').classList.remove('hidden');
  document.getElementById('resumeCard').classList.add('hidden');
  setStages('story',0,1,'Resume ho raha...');
  const r=await (await fetch('/api/resume/'+name,{method:'POST'})).json();
  if(r.error){ showErr(r.error); return; }
  CUR_JOB=r.job_id; _resetStop();
  polling=setInterval(()=>poll(r.job_id),1500);
}
async function dropProject(name,elBtn){
  if(!confirm('Ye adhoora project delete karein?')) return;
  await fetch('/api/projects/'+name,{method:'DELETE'});
  checkResumable();
}
async function startJob(parsed){
  const script=document.getElementById('script').value.trim();
  if(!parsed && script.length<10){alert('Script likhein');return;}
  const btn=document.getElementById('genBtn');
  btn.disabled=true;
  document.getElementById('progressCard').classList.remove('hidden');
  document.getElementById('previewCard').classList.add('hidden');
  document.getElementById('resultCard').classList.add('hidden');
  document.getElementById('errMsg').classList.add('hidden');
  setStages('story',0,1,'');
  const body={script,settings:collectSettings()};
  if(parsed) body.parsed=parsed;
  const r=await (await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body)})).json();
  if(r.error){showErr(r.error);return;}
  CUR_JOB=r.job_id; _resetStop();
  polling=setInterval(()=>poll(r.job_id),1500);
}
function _resetStop(){ const b=document.getElementById('stopBtn'); if(b){b.disabled=false;b.textContent='⏹ STOP Generation';} }

async function poll(id){
  const j=await (await fetch('/api/status/'+id)).json();
  if(j.state==='running') setStages(j.stage,j.i,j.total,j.message);
  else if(j.state==='done'){clearInterval(polling);setStages('render',1,1,'',true);showResult(j.result);checkResumable();loadProjectsList();}
  else if(j.state==='stopped'){clearInterval(polling);reset();document.getElementById('progressCard').classList.add('hidden');
    const fb=document.getElementById('scriptFeedback'); if(fb)fb.innerHTML='<span style="color:#f59e0b">⏹ Generation ruk gaya — jitna bana wo safe. 📁 My Projects se ▶ Resume kar sakte.</span>';
    checkResumable();loadProjectsList();}
  else if(j.state==='error'){clearInterval(polling);showErr(j.error||'error');checkResumable();}
}

function showResult(res){
  document.getElementById('resultCard').classList.remove('hidden');
  document.getElementById('rTitle').textContent=res.title||'Video Ready';
  document.getElementById('rVideo').src='/projects/'+res.video_rel+'?t='+Date.now();
  document.getElementById('rDownload').href='/projects/'+res.video_rel;
  reset();
}
function showErr(m){const e=document.getElementById('errMsg');e.textContent='❌ '+m;e.classList.remove('hidden');reset();}
function reset(){
  const b=document.getElementById('genBtn');b.disabled=false;b.textContent='🚀 Direct Generate (skip preview)';
  const pb=document.getElementById('previewBtn');pb.disabled=false;pb.textContent='👁️ Preview & Edit';
  const pg=document.getElementById('pvGenBtn');if(pg)pg.disabled=false;
}

async function testRunware(){
  const btn=document.getElementById('testBtn'), out=document.getElementById('testResult');
  btn.disabled=true; btn.textContent='⏳ Testing...';
  out.innerHTML='<span style="color:var(--muted)">Runware ko test kiya ja raha hai...</span>';
  try{
    const img=document.getElementById('test_img').checked;
    const j=await (await fetch('/api/test-runware',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({image:img})})).json();
    const t=j.tests||{};
    const dot=ok=>ok?'<span style="color:var(--green)">●</span>':'<span style="color:var(--red)">●</span>';
    let h='';
    h+=`<div>${dot(t.key&&t.key.ok)} <b>API Key</b> — ${t.key?t.key.masked:'?'}</div>`;
    if(t.llm){h+=`<div>${dot(t.llm.ok)} <b>LLM</b> <span style="color:var(--muted)">(${t.llm.model})</span> — ${t.llm.ms}ms`
      + (t.llm.ok?` → "${t.llm.sample||''}"`:'')+`</div>`;
      if(!t.llm.ok) h+=`<div class="err">${t.llm.error}</div>`;}
    if(t.image){h+=`<div>${dot(t.image.ok)} <b>Image</b> <span style="color:var(--muted)">(${t.image.model})</span> — ${t.image.ms}ms</div>`;
      if(t.image.ok&&t.image.url) h+=`<div style="margin-top:5px"><img src="${t.image.url}" style="width:80px;height:80px;border-radius:8px;object-fit:cover"></div>`;
      if(!t.image.ok) h+=`<div class="err">${t.image.error}</div>`;}
    h+=`<div style="margin-top:8px;font-weight:700;color:${j.ok?'var(--green)':'var(--red)'}">`
      + (j.ok?'✅ Runware theek chal raha hai':'⚠️ Masla — upar detail dekho')+`</div>`;
    out.innerHTML=h;
  }catch(e){ out.innerHTML='<div class="err">Test fail: '+e+'</div>'; }
  btn.disabled=false; btn.textContent='🔎 Test API';
}
