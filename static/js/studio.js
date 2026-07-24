let polling=null, OPTS=null, CUR_JOB=null, CHAR_CAPS={}, POLL_FAILURES=0, POLL_IN_FLIGHT=false, POLL_RETRY_TIMER=null, LAST_JOB_STATUS=null;
let CHARACTER_CATALOG=null, CHARACTER_LIBRARY='sbz', CHARACTER_CATEGORY='all';
let CAST_CHARACTER_LIBRARY='sbz';
let TEMPLATE_CHARACTER_LIBRARY='sbz';
let ASSET_CATALOG=null, ASSET_CATEGORY='backgrounds';
let ELEVEN_VOICES_LOADED=false, EDGE_VOICES_LOADED=false;
let SCRIPT_ENGINE_OPTIONS=null, SCRIPT_ENGINE_JOB=null, SCRIPT_ENGINE_RESULT=null;
let SCRIPT_ENGINE_PROJECT='', SCRIPT_ENGINE_APPROVED=false, SCRIPT_ENGINE_POLL=null;
let MANUAL_SCENE_TIMER=null, MANUAL_SCENE_TOKEN=0, PLAN_SOURCE_SCRIPT='';
const ORDER=['story','voice','asset','render'];
function escHtml(value){
  return String(value==null?'':value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function uiIcon(name){
  return `<svg class="icon" aria-hidden="true"><use href="/static/icons/icons.svg?v=20260715-character-catalog#icon-${name}"></use></svg>`;
}
function feedbackMarkup(type,message,icon){
  const iconName=icon||(type==='success'?'check':type==='warning'?'warning':type==='loading'?'render':'info');
  return `<span class="feedback-inline ${type}">${uiIcon(iconName)}<span>${escHtml(message)}</span></span>`;
}
function setButtonLoading(button,loading,label='Working…'){
  if(!button) return;
  if(loading){
    if(!button.dataset.idleLabel) button.dataset.idleLabel=button.textContent.trim();
    button.disabled=true; button.dataset.loading='true'; button.classList.add('is-loading');
    button.setAttribute('aria-busy','true'); button.textContent=label;
  }else{
    button.disabled=false; button.classList.remove('is-loading'); button.removeAttribute('data-loading');
    button.removeAttribute('aria-busy');
    if(button.dataset.idleLabel){button.textContent=button.dataset.idleLabel;delete button.dataset.idleLabel;}
  }
}
function showStudioToast(message,type='info',title='Notice',allowUndo=false){
  const toast=document.getElementById('generationToast'); if(!toast) return;
  const types=['success','warning','danger','info']; type=types.includes(type)?type:'info';
  toast.classList.remove('success','warning','danger','info','hidden'); toast.classList.add(type);
  toast.setAttribute('role',type==='danger'?'alert':'status');
  toast.setAttribute('aria-live',type==='danger'?'assertive':'polite');
  const icon=document.getElementById('generationToastIcon');
  if(icon) icon.innerHTML=uiIcon(type==='success'?'check':type==='warning'||type==='danger'?'warning':'info');
  const heading=document.getElementById('generationToastTitle'); if(heading) heading.textContent=title;
  const copy=document.getElementById('generationToastMessage'); if(copy) copy.textContent=message;
  const undo=document.getElementById('undoGeneratedScriptBtn'); if(undo) undo.classList.toggle('hidden',!allowUndo);
  clearTimeout(TOAST_TIMER); TOAST_TIMER=setTimeout(()=>acceptGeneratedScript(),allowUndo?12000:6000);
}
function notifyValidation(message,focusId='',regionId=''){
  showStudioToast(message,'warning','Action needed');
  const region=regionId?document.getElementById(regionId):null;
  if(region){region.innerHTML=feedbackMarkup('warning',message);region.classList.remove('hidden');}
  const field=focusId?document.getElementById(focusId):null;
  if(field){field.setAttribute('aria-invalid','true');field.focus();}
}
function elevenVoiceLabel(voice){
  const labels=voice.labels||{};
  const traits=[labels.gender,labels.age,labels.accent,labels['use case']||labels.use_case]
    .filter(Boolean).slice(0,3);
  return `${voice.recommended?'Recommended · ':''}${voice.name}${traits.length?' · '+traits.join(' · '):''}`;
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
    addGroup('Children & Storytelling — Recommended',recommended);
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
    status.textContent='Voice service: '+error.message;
    sel.disabled=true; ELEVEN_VOICES_LOADED=false;
  }
}
function ensureProviderControls(){
  const tts=document.getElementById('tts_provider');
  if(tts && ![...tts.options].some(option=>option.value==='google')){
    const option=document.createElement('option'); option.value='google';
    option.textContent='Google Cloud TTS (free quota)';
    tts.insertBefore(option,[...tts.options].find(item=>item.value==='elevenlabs')||null);
  }
  const body=document.querySelector('#advancedProviderGroup .advanced-group-body');
  if(body && !document.getElementById('llm_provider')){
    const controls=document.createElement('div'); controls.className='provider-model-controls';
    controls.innerHTML='<label for="llm_provider">Text API gateway</label><select id="llm_provider"></select>'
      +'<label for="llm_model">Runware script model</label><select id="llm_model"></select>'
      +'<div id="llm_model_status" class="hint">Available models load ho rahe hain.</div>';
    body.prepend(controls);
  }
}
function voiceOptionLabel(voice){
  return `${voice.name} · ${voice.gender||'Voice'}`;
}
async function loadEdgeVoices(force=false){
  if(EDGE_VOICES_LOADED && !force) return;
  const sel=document.getElementById('edge_voice'), status=document.getElementById('edge_voice_status');
  if(!sel || !status) return;
  sel.disabled=true; status.textContent='Free Hindi and Urdu voices load ho rahi hain...';
  try{
    const response=await fetch('/api/voices/edge'+(force?'?refresh=1':''));
    const data=await response.json();
    if(!response.ok || !data.available) throw new Error(data.error||'voices load nahi huin');
    sel.innerHTML='<option value="">Auto by character</option>';
    const locales={};
    (data.voices||[]).forEach(voice=>(locales[voice.locale]??=[]).push(voice));
    Object.entries(locales).forEach(([locale,voices])=>{
      const group=document.createElement('optgroup'); group.label=locale;
      voices.forEach(voice=>{const option=document.createElement('option');option.value=voice.name;option.textContent=voiceOptionLabel(voice);group.appendChild(option);});
      sel.appendChild(group);
    });
    const selected=(OPTS.defaults&&OPTS.defaults.edge_voice)||data.selected||'';
    if([...sel.options].some(option=>option.value===selected)) sel.value=selected;
    sel.disabled=false; status.textContent=`${data.voices.length} free Hindi/Urdu voices available`; EDGE_VOICES_LOADED=true;
  }catch(error){sel.disabled=false;status.textContent='Voice list: '+error.message;EDGE_VOICES_LOADED=false;}
}
async function loadGoogleVoices(){
  const sel=document.getElementById('google_tts_voice'); if(!sel) return;
  const status=document.getElementById('google_voice_status');
  let data={voices:(OPTS&&OPTS.google_voices)||[],available:false,selected:OPTS?.defaults?.google_tts_voice};
  try{const response=await fetch('/api/voices/google');if(response.ok)data=await response.json();}catch(error){}
  const voices=data.voices||[]; sel.innerHTML='';
  voices.forEach(voice=>{const option=document.createElement('option');option.value=voice.name;option.textContent=`${voice.name} · ${voice.gender} · ${voice.tier}`;sel.appendChild(option);});
  const configured=OPTS?.defaults?.google_tts_voice||data.selected;
  if(configured && [...sel.options].some(option=>option.value===configured)) sel.value=configured;
  if(status) status.textContent=data.available?'Google Cloud TTS configured · free quota may apply':'API key/billing setup required · monthly free quota may apply';
}
function syncLLMModels(){
  const provider=document.getElementById('llm_provider'), model=document.getElementById('llm_model'), status=document.getElementById('llm_model_status');
  if(!provider || !model || !OPTS) return;
  const catalog=OPTS.llm_models||[], providers=[...new Set(catalog.map(item=>item.provider))];
  const configuredProvider=OPTS.defaults?.llm_provider||'runware';
  if(!provider.options.length){providers.forEach(name=>{const option=document.createElement('option');option.value=name;option.textContent=name==='runware'?'Runware API (all vendors)':name[0].toUpperCase()+name.slice(1);provider.appendChild(option);});provider.value=providers.includes(configuredProvider)?configuredProvider:providers[0]||'';}
  const selectedProvider=provider.value, current=model.value||OPTS.defaults?.llm_model||'';
  model.innerHTML=''; catalog.filter(item=>item.provider===selectedProvider).forEach(item=>{const option=document.createElement('option');option.value=item.model;option.textContent=`${item.vendor||'Runware'} · ${item.label} · ${item.cost}`;model.appendChild(option);});
  if([...model.options].some(option=>option.value===current)) model.value=current;
  const chosen=catalog.find(item=>item.provider===selectedProvider&&item.model===model.value);
  if(status) status.textContent=chosen?`Runs through your Runware API key · ${chosen.description} · ${chosen.cost}`:'Configure the Runware API key before generation.';
}
function syncVoiceProviderUI(){
  const provider=document.getElementById('tts_provider').value;
  document.getElementById('edge_voice_group').classList.toggle('hidden',provider!=='edge');
  document.getElementById('edge_voice_options')?.classList.toggle('hidden',provider!=='edge');
  document.getElementById('google_voice_group')?.classList.toggle('hidden',provider!=='google');
  document.getElementById('eleven_voice_group').classList.toggle('hidden',provider!=='elevenlabs');
  if(provider==='edge') loadEdgeVoices();
  if(provider==='google') loadGoogleVoices();
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
function performanceMarkup(performance){
  if(!performance)return '';
  const mode=performance.speech_mode||'body_only';
  const labels={viseme_facial:'Full facial + viseme sync',viseme:'Viseme lip-sync',jaw_openness:'Jaw lip-sync',body_only:'Body acting only',static:'Static visual role'};
  const cls=mode==='viseme_facial'?'full':mode==='viseme'?'viseme':mode==='jaw_openness'?'legacy':'body';
  const warning=performance.warning||performance.performance_warning||'';
  return `<span class="performanceBadge ${cls}" title="${escHtml(warning)}">${escHtml(labels[mode]||performance.label||mode)}</span>`;
}
function castingDecisionMarkup(decision){
  if(!decision)return '';
  const labels={skeletal_action:'Action-led',dialogue:'Dialogue-led',hybrid:'Action + dialogue',balanced:'Balanced'};
  const title=decision.message||'';
  return `<span class="performanceBadge body" title="${escHtml(title)}">${escHtml(labels[decision.need]||decision.route||'Casting plan')}</span>`;
}
async function load3dValidation(packages=[]){
  try{
    const requested=[...new Set((packages||[]).filter(Boolean).map(value=>String(value).toLowerCase()))];
    const query=requested.length?`?packages=${encodeURIComponent(requested.join(','))}`:'';
    const payload=await (await fetch('/api/characters3d/validation'+query)).json();
    if(!requested.length) CHAR_CAPS={};
    (payload.characters||[]).forEach(cap=>{
      const blend=((cap.character&&cap.character.blend)||'').replace(/\\/g,'/').split('/').pop().replace(/\.(blend|glb)$/i,'').toLowerCase();
      if(blend) CHAR_CAPS[blend]=cap;
    });
  }catch(e){ CHAR_CAPS={}; }
}
async function stopJob(){
  if(!CUR_JOB) return;
  const b=document.getElementById('stopBtn'); b.disabled=true; b.textContent='Stopping…';
  try{ await fetch('/api/stop/'+CUR_JOB,{method:'POST'}); }catch(e){}
}

const SCRIPT_STAGE_TASK={story_idea:'STORY_ARCHITECT',story_outline:'STORY_ARCHITECT',character_profiles:'STORY_ARCHITECT',scene_breakdown:'FAST_PARSER',character_dialogue:'DIALOGUE_WRITER',script_doctor:'SCRIPT_DOCTOR',visual_story_beats:'FAST_PARSER',animation_plan:'ANIMATION_PLANNER',storyboard:'ANIMATION_PLANNER'};
const SCRIPT_STAGE_LABEL={story_idea:'Story Idea',story_outline:'Story Outline',character_profiles:'Character Profiles',scene_breakdown:'Scene Breakdown / Parser',character_dialogue:'Character Dialogue',script_doctor:'Script Doctor',visual_story_beats:'Visual Story Beats',animation_plan:'Capability-Aware Animation Plan',storyboard:'Validated Storyboard JSON'};
function titleFromId(value){return String(value||'').split('_').map(word=>word?word[0].toUpperCase()+word.slice(1):'').join(' ');}
function populateScriptEngineModels(select,selected){
  if(!select||!SCRIPT_ENGINE_OPTIONS)return;
  const models=SCRIPT_ENGINE_OPTIONS.models?.models||[];select.innerHTML='';
  models.forEach(model=>{const option=document.createElement('option');option.value=model.internalId;option.textContent=`${model.family} · ${model.displayName} · ${model.costPreference}`;option.title=`AIR: ${model.runwareAir} · ${model.intendedTasks.join(', ')}`;select.appendChild(option);});
  if(selected&&[...select.options].some(option=>option.value===selected))select.value=selected;
}
function syncScriptEngineControls(resetModel=true){
  if(!SCRIPT_ENGINE_OPTIONS)return;
  const stage=document.getElementById('scriptEngineStage')?.value||'scene_breakdown';
  const doctor=stage==='script_doctor';document.getElementById('scriptDoctorModeGroup')?.classList.toggle('hidden',!doctor);
  const compare=document.getElementById('scriptEngineCompare')?.checked===true;document.getElementById('scriptEngineComparisonGroup')?.classList.toggle('hidden',!compare);
  if(resetModel){const task=SCRIPT_STAGE_TASK[stage],primary=SCRIPT_ENGINE_OPTIONS.routing?.tasks?.[task]?.primary;populateScriptEngineModels(document.getElementById('scriptEngineModel'),primary);populateScriptEngineModels(document.getElementById('scriptEngineComparisonModel'));const comparison=document.getElementById('scriptEngineComparisonModel');if(comparison&&comparison.options.length>1)comparison.selectedIndex=1;}
}
async function loadScriptEngineOptions(){
  try{
    const response=await fetch('/api/script-engine/options');const data=await response.json();if(!response.ok)throw new Error(data.error||'Script engine options unavailable');SCRIPT_ENGINE_OPTIONS=data;
    const stage=document.getElementById('scriptEngineStage'),language=document.getElementById('scriptEngineLanguage'),mode=document.getElementById('scriptDoctorMode');
    if(!stage||!language||!mode)return;
    stage.innerHTML=data.stages.map(value=>`<option value="${escHtml(value)}">${escHtml(SCRIPT_STAGE_LABEL[value]||titleFromId(value))}</option>`).join('');stage.value='scene_breakdown';
    language.innerHTML=data.languages.map(value=>`<option value="${escHtml(value)}">${escHtml(titleFromId(value))}</option>`).join('');language.value=document.getElementById('ffLang')?.value||'roman_urdu';
    mode.innerHTML=data.scriptDoctorModes.map(value=>`<option value="${escHtml(value)}">${escHtml(titleFromId(value))}</option>`).join('');mode.value='robotic_naturalizer';
    syncScriptEngineControls(true);stage.addEventListener('change',()=>syncScriptEngineControls(true));document.getElementById('scriptEngineCompare')?.addEventListener('change',()=>syncScriptEngineControls(false));
  }catch(error){const status=document.getElementById('scriptEngineStatus');if(status)status.innerHTML=feedbackMarkup('danger',error.message);}
}
function scriptEngineContent(stage){
  const script=document.getElementById('script')?.value.trim()||'';if(stage==='story_idea')return document.getElementById('ffIdea')?.value.trim()||script;return script;
}
function scriptEngineMetadataMarkup(metadata){
  if(!metadata)return'';const cost=metadata.cost==null?'Cost unavailable':`$${Number(metadata.cost).toFixed(6)}`;return [`Model: ${metadata.modelDisplayName}`,`AIR: ${metadata.modelAir}`,`${metadata.latencyMs} ms`,cost,`Cache: ${metadata.cache}`,`Retries: ${metadata.retryCount}`,metadata.fallbackUsed?`Fallback: ${metadata.fallbackReason}`:'No fallback'].map(value=>`<span>${escHtml(value)}</span>`).join('');
}
async function pollScriptEngineJob(){
  if(!SCRIPT_ENGINE_JOB)return;const response=await fetch('/api/script-engine/status/'+encodeURIComponent(SCRIPT_ENGINE_JOB));const job=await response.json();if(!response.ok){throw new Error(job.error||'Script job unavailable');}
  const status=document.getElementById('scriptEngineStatus');if(job.state==='queued'||job.state==='running'){status.innerHTML=feedbackMarkup('loading',job.state==='queued'?'Request queued.':'Runware stage generate ho raha hai.');return;}
  clearInterval(SCRIPT_ENGINE_POLL);SCRIPT_ENGINE_POLL=null;document.getElementById('scriptEngineCancelBtn')?.classList.add('hidden');setButtonLoading(document.getElementById('scriptEngineRunBtn'),false);
  if(job.state==='done'){
    SCRIPT_ENGINE_RESULT=job.result;const primary=job.result.primary;document.getElementById('scriptEngineOutput').value=JSON.stringify(primary.output,null,2);document.getElementById('scriptEngineMetadata').innerHTML=scriptEngineMetadataMarkup(primary.metadata);document.getElementById('scriptEngineApproveBtn').disabled=false;
    const comparison=job.result.comparison;status.innerHTML=feedbackMarkup('success',comparison?'Both validated outputs are ready. Primary output is editable below.':'Validated structured output is ready.');if(comparison)status.innerHTML+=`<div class="feedback-detail">Comparison: ${escHtml(comparison.metadata.modelDisplayName)} · ${comparison.metadata.latencyMs} ms${comparison.metadata.cost==null?'':` · $${Number(comparison.metadata.cost).toFixed(6)}`}</div>`;
  }else if(job.state==='cancelled'){status.innerHTML=feedbackMarkup('warning','Generation cancelled.');}else{status.innerHTML=feedbackMarkup('danger',job.error||'Generation failed.');if(job.diagnostics?.length)status.innerHTML+=`<div class="feedback-detail">${escHtml(job.diagnostics.map(item=>item.message||item).join(' · '))}</div>`;}
  SCRIPT_ENGINE_JOB=null;
}
async function runScriptEngineStage(){
  if(!SCRIPT_ENGINE_OPTIONS){await loadScriptEngineOptions();if(!SCRIPT_ENGINE_OPTIONS)return;}
  const stage=document.getElementById('scriptEngineStage').value,content=scriptEngineContent(stage),status=document.getElementById('scriptEngineStatus');
  if(!content){notifyValidation('Is stage ke liye pehle idea ya script likhein.','script','scriptEngineStatus');return;}
  if((stage==='animation_plan'||stage==='storyboard')&&!SCRIPT_ENGINE_APPROVED){status.innerHTML=feedbackMarkup('warning','Animation planning se pehle current structured output approve karein.');return;}
  if(!SCRIPT_ENGINE_PROJECT)SCRIPT_ENGINE_PROJECT=STUDIO_UI.projectName.startsWith('project-')?STUDIO_UI.projectName:`script-draft-${Date.now()}`;
  const compare=document.getElementById('scriptEngineCompare').checked;const payload={stage,content,language:document.getElementById('scriptEngineLanguage').value,mode:stage==='script_doctor'?document.getElementById('scriptDoctorMode').value:null,model:document.getElementById('scriptEngineModel').value,compare,comparison_model:compare?document.getElementById('scriptEngineComparisonModel').value:null,allow_fallback:true,use_cache:true,project:SCRIPT_ENGINE_PROJECT,approved_input:SCRIPT_ENGINE_APPROVED};
  setButtonLoading(document.getElementById('scriptEngineRunBtn'),true,'Generating…');document.getElementById('scriptEngineCancelBtn').classList.remove('hidden');document.getElementById('scriptEngineApproveBtn').disabled=true;status.innerHTML=feedbackMarkup('loading','Secure backend request start ho rahi hai.');
  try{const response=await fetch('/api/script-engine/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const data=await response.json();if(!response.ok)throw new Error(data.error||'Stage start nahi hua');SCRIPT_ENGINE_JOB=data.job_id;clearInterval(SCRIPT_ENGINE_POLL);SCRIPT_ENGINE_POLL=setInterval(()=>pollScriptEngineJob().catch(error=>{clearInterval(SCRIPT_ENGINE_POLL);SCRIPT_ENGINE_POLL=null;status.innerHTML=feedbackMarkup('danger',error.message);setButtonLoading(document.getElementById('scriptEngineRunBtn'),false);}),700);await pollScriptEngineJob();}catch(error){status.innerHTML=feedbackMarkup('danger',error.message);setButtonLoading(document.getElementById('scriptEngineRunBtn'),false);document.getElementById('scriptEngineCancelBtn').classList.add('hidden');}
}
async function cancelScriptEngineStage(){if(!SCRIPT_ENGINE_JOB)return;await fetch('/api/script-engine/cancel/'+encodeURIComponent(SCRIPT_ENGINE_JOB),{method:'POST'});}
async function approveScriptEngineStage(){
  if(!SCRIPT_ENGINE_RESULT)return;const stage=document.getElementById('scriptEngineStage').value,status=document.getElementById('scriptEngineStatus');let output;try{output=JSON.parse(document.getElementById('scriptEngineOutput').value);}catch(error){status.innerHTML=feedbackMarkup('danger','Edited output valid JSON nahi hai.');return;}
  try{const response=await fetch('/api/script-engine/approve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project:SCRIPT_ENGINE_PROJECT,stage,output})});const data=await response.json();if(!response.ok)throw new Error((data.diagnostics||[]).join(' · ')||data.error||'Approval failed');SCRIPT_ENGINE_APPROVED=true;status.innerHTML=feedbackMarkup('success','Stage approved and saved. Ab next stage generate ho sakta hai.');if(stage==='script_doctor'&&output.script)replaceScriptWithGenerated(output.script,STUDIO_UI.projectName,'Script Doctor');document.getElementById('scriptEngineApproveBtn').disabled=true;}catch(error){status.innerHTML=feedbackMarkup('danger',error.message);}
}

async function loadMusicOptions(){
  const select=document.getElementById('music_track'), status=document.getElementById('music_track_status');
  if(!select)return;
  try{
    const response=await fetch('/api/music'); const data=await response.json();
    [...select.querySelectorAll('option:not([value="auto"])')].forEach(option=>option.remove());
    (data.tracks||[]).forEach(track=>{const option=document.createElement('option');option.value=track.id;option.textContent=`${track.title} — ${track.category}`;select.appendChild(option);});
    const selected=OPTS?.defaults?.music_track||data.selected||'auto';
    select.value=[...select.options].some(option=>option.value===selected)?selected:'auto';
    if(status)status.textContent=(data.tracks||[]).length?`${data.tracks.length} local track(s). Auto script ke mood se choose karega.`:'No local music track found in assets/music.';
  }catch(error){if(status)status.textContent='Music library unavailable; Auto mode will be used.';}
}
async function load(){
  OPTS = await (await fetch('/api/options')).json();
  ensureProviderControls();
  const sel=document.getElementById('style');
  OPTS.styles.forEach(s=>{const o=document.createElement('option');o.value=s;o.textContent=s;
    if(s===OPTS.defaults.style)o.selected=true; sel.appendChild(o);});
  const p=OPTS.providers;
  const providerSummary=`LLM:${p.llm.join('/')} · IMG:${p.image.join('/')} · TTS:${p.tts.join('/')}`;
  document.getElementById('provStatus').textContent=providerSummary;
  const advancedProviders=document.getElementById('advancedProviderDetails');
  if(advancedProviders) advancedProviders.textContent=providerSummary;
  const providerHealth=document.getElementById('dashboardProviderHealth');
  const providerDetail=document.getElementById('dashboardEngineDetail');
  const providerCount=(p.llm?.length||0)+(p.image?.length||0)+(p.tts?.length||0);
  if(providerHealth) providerHealth.textContent=providerCount?'Engine ready':'Setup required';
  if(providerDetail) providerDetail.textContent=providerCount?`${p.llm.length} text · ${p.image.length} image · ${p.tts.length} voice providers available`:'Open Settings to configure providers.';
  if(OPTS.defaults && OPTS.defaults.urdu_accent){ const ua=document.getElementById('urdu_accent'); if(ua) ua.value=OPTS.defaults.urdu_accent; }
  const tts=document.getElementById('tts_provider');
  if(OPTS.defaults && OPTS.defaults.tts_provider) tts.value=OPTS.defaults.tts_provider;
  tts.addEventListener('change',syncVoiceProviderUI);
  document.getElementById('refresh_eleven_voices').addEventListener('click',()=>loadElevenLabsVoices(true));
  document.getElementById('refresh_edge_voices')?.addEventListener('click',()=>loadEdgeVoices(true));
  const speed=document.getElementById('voice_speed'), speedOut=document.getElementById('voiceSpeedValue');
  if(speed){speed.value=OPTS.defaults?.voice_speed||1;const updateSpeed=()=>{if(speedOut)speedOut.textContent=`${Number(speed.value).toFixed(2)}×`;};speed.addEventListener('input',updateSpeed);updateSpeed();}
  loadGoogleVoices();
  loadMusicOptions();
  syncLLMModels();
  document.getElementById('llm_provider')?.addEventListener('change',syncLLMModels);
  document.getElementById('llm_model')?.addEventListener('change',syncLLMModels);
  syncVoiceProviderUI();
  if(OPTS.defaults && OPTS.defaults.render_engine){ const re=document.getElementById('render_engine'); if(re) re.value=OPTS.defaults.render_engine; }
  if(OPTS.defaults){
    document.getElementById('cap_enabled').checked=!!OPTS.defaults.subtitles_on;
    document.getElementById('intro_on').checked=!!OPTS.defaults.intro_on;
  }
  loadCharacterCatalog();
  loadAssetCatalog();
  loadTemplates();
  checkResumable();       // crash/close ke baad adhoore projects dikhao
  loadProjectsList();     // purane projects ka count + list
  initScriptTabs();
  loadScriptEngineOptions();
  initStudioWorkspace();
}

// Script card ke tabs (Idea se / Long-Form / Characters / Template) — ek waqt ek panel
function initScriptTabs(){
  document.querySelectorAll('#scriptModeTabs [data-script-mode]').forEach(tab=>{
    tab.addEventListener('click',()=>selectScriptMode(tab.dataset.scriptMode));
  });
  document.querySelectorAll('#scriptTabs [data-t]').forEach(tab=>{
    tab.addEventListener('click',()=>selectAIGenerator(tab.dataset.t));
  });
}

function selectScriptMode(mode,persist=true){
  mode=mode==='ai'?'ai':'write';
  STUDIO_UI.scriptMode=mode;
  document.querySelectorAll('#scriptModeTabs [data-script-mode]').forEach(tab=>{
    const active=tab.dataset.scriptMode===mode;
    tab.classList.toggle('active',active);
    tab.setAttribute('aria-selected',String(active));
  });
  document.querySelectorAll('#scriptCard [data-script-mode-panel]').forEach(panel=>{
    const active=panel.dataset.scriptModePanel===mode;
    panel.classList.toggle('active',active);
    panel.hidden=!active;
  });
  if(mode==='ai') selectAIGenerator(STUDIO_UI.aiTab||'quick',false);
  if(persist) scheduleWorkspaceAutosave();
}

function selectAIGenerator(tab,persist=true){
  const allowed=['quick','longform','series','templates'];
  tab=allowed.includes(tab)?tab:'quick';
  STUDIO_UI.aiTab=tab;
  document.querySelectorAll('#scriptTabs [data-t]').forEach(button=>{
    const active=button.dataset.t===tab;
    button.classList.toggle('on',active);
    button.setAttribute('aria-selected',String(active));
  });
  document.querySelectorAll('#scriptAIPanel .tabpanel[data-t]').forEach(panel=>{
    panel.classList.toggle('hidden',panel.dataset.t!==tab);
  });
  if(persist) scheduleWorkspaceAutosave();
}

function openAIGenerator(tab='quick'){
  showStudioView('create',false);
  setCreateStep(1,false);
  selectScriptMode('ai',false);
  selectAIGenerator(tab,false);
  document.getElementById('scriptCard')?.scrollIntoView({behavior:'smooth',block:'start'});
  scheduleWorkspaceAutosave();
}

function catalogStatusClass(item){
  if(item.status==='ready') return 'ready';
  if(item.status==='blocked_license') return 'license-review';
  if(item.status==='needs_rig_adapter') return 'needs-rig-adapter';
  return '';
}
function catalogInitials(name){
  return String(name||'?').trim().split(/\s+/).slice(0,2).map(word=>word[0]||'').join('').toUpperCase()||'?';
}
async function loadCharacterCatalog(){
  const grid=document.getElementById('characterCatalogGrid');
  try{
    const response=await fetch('/api/character-catalog');
    const data=await response.json();
    if(!response.ok) throw new Error(data.error||'Character catalog unavailable');
    CHARACTER_CATALOG=data;
    const summary=data.summary||{};
    const sbzCount=document.getElementById('sbzCatalogCount'), qCount=document.getElementById('quaterniusCatalogCount');
    if(sbzCount) sbzCount.textContent=summary.sbz||0;
    if(qCount) qCount.textContent=summary.quaternius||0;
    document.querySelectorAll('#characterCatalogTabs [data-character-library]').forEach(button=>{
      button.onclick=()=>setCharacterLibrary(button.dataset.characterLibrary);
    });
    const search=document.getElementById('characterCatalogSearch');
    const category=document.getElementById('characterCatalogCategory');
    const ready=document.getElementById('characterCatalogReadyOnly');
    if(search) search.oninput=renderCharacterCatalog;
    if(category) category.onchange=()=>{CHARACTER_CATEGORY=category.value;renderCharacterCatalog();};
    if(ready) ready.onchange=renderCharacterCatalog;
    setCharacterLibrary(CHARACTER_LIBRARY,false);
  }catch(error){
    if(grid) grid.innerHTML=`<div class="empty-state compact catalog-empty"><span>${uiIcon('warning')}</span><div><strong>Character catalog unavailable</strong><p>${escHtml(error.message)}</p></div></div>`;
  }
}
function setCharacterLibrary(library,focus=true){
  CHARACTER_LIBRARY=library==='quaternius'?'quaternius':'sbz';
  CAST_CHARACTER_LIBRARY=CHARACTER_LIBRARY;
  CHARACTER_CATEGORY='all';
  document.querySelectorAll('#characterCatalogTabs [data-character-library]').forEach(button=>{
    const active=button.dataset.characterLibrary===CHARACTER_LIBRARY;
    button.classList.toggle('active',active); button.setAttribute('aria-selected',String(active));
  });
  const category=document.getElementById('characterCatalogCategory');
  if(category&&CHARACTER_CATALOG){
    const choices=CHARACTER_CATALOG.categories?.[CHARACTER_LIBRARY]||[];
    category.innerHTML='<option value="all">All categories</option>'+choices.map(item=>`<option value="${escHtml(item.id)}">${escHtml(item.label)}</option>`).join('');
    category.value='all';
  }
  renderCharacterCatalog();
  if(focus) document.querySelector(`#characterCatalogTabs [data-character-library="${CHARACTER_LIBRARY}"]`)?.focus();
}
function renderCharacterCatalog(){
  if(!CHARACTER_CATALOG) return;
  const grid=document.getElementById('characterCatalogGrid'); if(!grid) return;
  const query=(document.getElementById('characterCatalogSearch')?.value||'').trim().toLowerCase();
  const readyOnly=document.getElementById('characterCatalogReadyOnly')?.checked===true;
  const libraryItems=(CHARACTER_CATALOG.characters||[]).filter(item=>item.library===CHARACTER_LIBRARY);
  const items=libraryItems.filter(item=>(CHARACTER_CATEGORY==='all'||item.category===CHARACTER_CATEGORY)
    &&(!readyOnly||item.selectable)
    &&(!query||`${item.name} ${item.pack} ${item.category} ${item.status_label}`.toLowerCase().includes(query)));
  const summary=document.getElementById('characterCatalogSummary');
  if(summary) summary.innerHTML=`<strong>${items.length}</strong><span>of ${libraryItems.length} characters</span>`;
  const notice=document.getElementById('characterCatalogNotice');
  if(notice){
    const s=CHARACTER_CATALOG.summary||{};
    notice.classList.toggle('hidden',CHARACTER_LIBRARY!=='quaternius');
    if(CHARACTER_LIBRARY==='quaternius') notice.textContent=`${s.quaternius_ready||0} production ready · ${s.quaternius_pending||0} awaiting standardization or rig mapping · ${s.license_blocked||0} held for license review.`;
  }
  if(!items.length){
    grid.innerHTML=`<div class="empty-state compact catalog-empty"><span>${uiIcon('search')}</span><div><strong>No matching characters</strong><p>Search, category ya ready-only filter change karein.</p></div></div>`; return;
  }
  grid.innerHTML=items.map(item=>{
    const pending=!item.selectable, blocked=item.status==='blocked_license';
    const thumb=item.thumbnail?`<img src="${escHtml(item.thumbnail)}" alt="" loading="lazy">`:'';
    const action=pending?`<button type="button" class="library-character-action" disabled>${escHtml(item.status_label)}</button>`
      :`<button type="button" class="library-character-action" data-character-package="${escHtml(item.package)}" onclick="useCatalogCharacter(this.dataset.characterPackage)">Use in story</button>`;
    return `<article class="library-character-card ${pending?'pending':''} ${blocked?'license-blocked':''}"><div class="library-character-head"><div class="library-character-avatar"><span>${escHtml(catalogInitials(item.name))}</span>${thumb}</div><div class="library-character-title"><h3 title="${escHtml(item.name)}">${escHtml(item.name)}</h3><span title="${escHtml(item.pack)}">${escHtml(item.pack)}</span></div></div><span class="catalog-status ${catalogStatusClass(item)}">${escHtml(item.status_label)}</span><div class="library-character-meta"><span>${escHtml(item.category)}</span><span>${escHtml(item.tier)}</span><span>${Number(item.clip_count||0)} clips</span></div><p class="library-character-reason" title="${escHtml(item.reason)}">${escHtml(item.reason)}</p>${action}</article>`;
  }).join('');
  grid.querySelectorAll('.library-character-avatar img').forEach(image=>image.addEventListener('error',()=>image.closest('.library-character-card')?.classList.add('avatar-missing')));
}
function useCatalogCharacter(packageName){
  const character=CHARS.find(item=>item.package===packageName);
  if(!character){showStudioToast('Character abhi template selection ke liye ready nahi.','warning','Character unavailable');return;}
  CHAR_SEL.add(character.id); TEMPLATE_CHARACTER_LIBRARY=character.library||'sbz';
  openAIGenerator('templates'); setTemplateCharacterLibrary(TEMPLATE_CHARACTER_LIBRARY,false); renderTemplateCharacters();
  showStudioToast(`${character.name} story cast mein select ho gaya.`,'success','Character selected');
}
async function loadAssetCatalog(){
  const grid=document.getElementById('assetCatalogGrid'); if(!grid) return;
  try{
    const response=await fetch('/api/asset-catalog');const data=await response.json();
    if(!response.ok)throw new Error(data.error||'Asset catalog unavailable');ASSET_CATALOG=data;
    const counts=data.summary||{};
    const ids={backgrounds:'assetBackgroundCount',props:'assetPropCount',vehicles:'assetVehicleCount',weapons:'assetWeaponCount'};
    Object.entries(ids).forEach(([category,id])=>{const el=document.getElementById(id);if(el)el.textContent=counts[category]||0;});
    document.querySelectorAll('#assetCatalogTabs [data-asset-category]').forEach(button=>button.onclick=()=>setAssetCategory(button.dataset.assetCategory));
    const search=document.getElementById('assetCatalogSearch');if(search)search.oninput=renderAssetCatalog;
    setAssetCategory(ASSET_CATEGORY,false);
  }catch(error){grid.innerHTML=`<div class="empty-state compact catalog-empty"><span>${uiIcon('warning')}</span><div><strong>Asset catalog unavailable</strong><p>${escHtml(error.message)}</p></div></div>`;}
}
function setAssetCategory(category,focus=true){
  ASSET_CATEGORY=['backgrounds','props','vehicles','weapons'].includes(category)?category:'backgrounds';
  document.querySelectorAll('#assetCatalogTabs [data-asset-category]').forEach(button=>{const active=button.dataset.assetCategory===ASSET_CATEGORY;button.classList.toggle('active',active);button.setAttribute('aria-selected',String(active));});
  renderAssetCatalog();if(focus)document.querySelector(`#assetCatalogTabs [data-asset-category="${ASSET_CATEGORY}"]`)?.focus();
}
function renderAssetCatalog(){
  if(!ASSET_CATALOG)return;const grid=document.getElementById('assetCatalogGrid');if(!grid)return;
  const query=(document.getElementById('assetCatalogSearch')?.value||'').trim().toLowerCase();
  const items=(ASSET_CATALOG.assets||[]).filter(item=>item.category===ASSET_CATEGORY&&(!query||`${item.name} ${item.pack}`.toLowerCase().includes(query)));
  const summary=document.getElementById('assetCatalogSummary');if(summary)summary.innerHTML=`<strong>${items.length}</strong><span>${escHtml(ASSET_CATEGORY)}</span>`;
  const blocked=items.filter(item=>item.license_status==='blocked').length,notice=document.getElementById('assetCatalogNotice');
  if(notice){notice.classList.toggle('hidden',!blocked);if(blocked)notice.textContent=`${blocked} Pirate Kit assets license verification tak production selection se blocked hain.`;}
  if(!items.length){grid.innerHTML=`<div class="empty-state compact catalog-empty"><span>${uiIcon('search')}</span><div><strong>No matching assets</strong><p>Search text ya category change karein.</p></div></div>`;return;}
  grid.innerHTML=items.map(item=>{const integrated=item.production_selectable,blockedAsset=item.license_status==='blocked';const label=integrated?'Production ready':blockedAsset?'License review':'Scene composition pending';return `<article class="library-character-card ${integrated?'':'pending'} ${blockedAsset?'license-blocked':''}"><div class="library-character-head"><div class="library-character-avatar"><span>${uiIcon(item.category==='vehicles'?'render':'assets')}</span></div><div class="library-character-title"><h3 title="${escHtml(item.name)}">${escHtml(item.name)}</h3><span title="${escHtml(item.pack)}">${escHtml(item.pack)}</span></div></div><span class="catalog-status ${integrated?'ready':blockedAsset?'license-review':''}">${escHtml(item.status_label)}</span><div class="library-character-meta"><span>${escHtml(item.category)}</span><span>${escHtml(item.path.split('.').pop().toUpperCase())}</span></div><p class="library-character-reason">${integrated?'Available in the current background renderer.':blockedAsset?'Not enabled until the pack license is verified.':'Local source is cataloged; a composed scene preset is still required.'}</p><button type="button" class="library-character-action" disabled>${label}</button></article>`;}).join('');
}

let TPL_SEL=null, TPLS=[], CHARS=[], CHAR_SEL=new Set();
async function loadTemplates(){
  TPLS = await (await fetch('/api/story-templates')).json();
  CHARS = await (await fetch('/api/characters')).json();
  const g=document.getElementById('tplGrid'); g.innerHTML='';
  TPLS.forEach(t=>{
    const b=document.createElement('button');
    b.className='tplChip'; b.dataset.id=t.id;
    b.innerHTML=`<span class="template-chip-icon">${uiIcon('templates')}</span><span>${escHtml(t.name)}</span>`;
    b.title=t.desc;
    b.onclick=()=>selectTemplate(t.id);
    g.appendChild(b);
  });
  document.querySelectorAll('#tplCharacterTabs [data-template-character-library]').forEach(button=>{
    button.onclick=()=>setTemplateCharacterLibrary(button.dataset.templateCharacterLibrary);
  });
  renderTemplateCharacters();
}
function recommendedTemplateCast(library,allowed){
  const names=TPL_SEL?.cast_recommendations?.[library]||TPL_SEL?.chars||[];
  const ids=names.filter(name=>allowed.some(character=>character.id===name));
  return ids.length>=2?ids:allowed.slice(0,Math.min(3,allowed.length)).map(character=>character.id);
}
function setTemplateCharacterLibrary(library,focus=true){
  TEMPLATE_CHARACTER_LIBRARY=library==='quaternius'?'quaternius':'sbz';
  CAST_CHARACTER_LIBRARY=TEMPLATE_CHARACTER_LIBRARY;
  const allowed=CHARS.filter(character=>(character.library||'sbz')===TEMPLATE_CHARACTER_LIBRARY);
  const existing=[...CHAR_SEL].filter(id=>allowed.some(character=>character.id===id));
  CHAR_SEL=new Set(existing.length>=2?existing:(TPL_SEL?recommendedTemplateCast(TEMPLATE_CHARACTER_LIBRARY,allowed):existing));
  document.querySelectorAll('#tplCharacterTabs [data-template-character-library]').forEach(button=>{
    const active=button.dataset.templateCharacterLibrary===TEMPLATE_CHARACTER_LIBRARY;
    button.classList.toggle('active',active);button.setAttribute('aria-selected',String(active));
  });
  renderTemplateCharacters();
  if(focus) document.querySelector(`#tplCharacterTabs [data-template-character-library="${TEMPLATE_CHARACTER_LIBRARY}"]`)?.focus();
}
function renderTemplateCharacters(){
  const cg=document.getElementById('tplChars'); if(!cg) return; cg.innerHTML='';
  const visible=CHARS.filter(c=>(c.library||'sbz')===TEMPLATE_CHARACTER_LIBRARY);
  visible.forEach(c=>{
    const b=document.createElement('button');
    b.className='tplChip'; b.dataset.cid=c.id; b.style.padding='6px 2px';
    b.classList.toggle('on',CHAR_SEL.has(c.id));
    b.innerHTML=`<span class="template-chip-icon">${uiIcon('characters')}</span><span>${escHtml(c.name)}</span>`;
    b.title=`${c.performance_label||c.tier||'Character'}${c.performance_warning?` — ${c.performance_warning}`:''}`;
    b.onclick=()=>toggleChar(c.id);
    cg.appendChild(b);
  });
  if(!visible.length) cg.innerHTML=`<div class="empty-state compact catalog-empty"><span>${uiIcon('warning')}</span><div><strong>No ready characters</strong><p>Library catalog mein standardization status dekhein.</p></div></div>`;
  const label=TEMPLATE_CHARACTER_LIBRARY==='quaternius'?'Quaternius ready characters':'SBZ Originals';
  const summary=document.getElementById('tplCharacterSummary');if(summary)summary.textContent=`${label} · ${visible.length}`;
}
function activeLibraryStoryCast(){
  const library=CAST_CHARACTER_LIBRARY==='quaternius'?'quaternius':'sbz';
  const allowed=CHARS.filter(character=>(character.library||'sbz')===library);
  const selected=[...CHAR_SEL].map(id=>CHARS.find(character=>character.id===id))
    .filter(character=>character&&(character.library||'sbz')===library)
    .map(character=>character.name);
  // Selected cards always win. When nothing is explicitly selected, provide a
  // small default cast from the active library only.
  return selected.length?selected:allowed.slice(0,3).map(character=>character.name);
}
function toggleChar(cid){
  if(CHAR_SEL.has(cid)) CHAR_SEL.delete(cid); else CHAR_SEL.add(cid);
  renderTemplateCharacters();
}
function selectTemplate(id){
  TPL_SEL=TPLS.find(t=>t.id===id);
  document.querySelectorAll('#tplGrid .tplChip').forEach(c=>c.classList.toggle('on',c.dataset.id===id));
  document.getElementById('tplPanel').classList.remove('hidden');
  document.getElementById('tplName').textContent=TPL_SEL.name_en;
  document.getElementById('tplTopic').placeholder='e.g. '+TPL_SEL.sample_topic;
  // Active library ka cast hi use ho.  Agar template defaults is library
  // mein nahin hain (for example Quaternius), first two ready characters
  // select ho jate hain instead of leaving the template unusable.
  const activeLibrary=TEMPLATE_CHARACTER_LIBRARY==='quaternius'?'quaternius':'sbz';
  const allowed=CHARS.filter(character=>(character.library||'sbz')===activeLibrary);
  CHAR_SEL=new Set(recommendedTemplateCast(activeLibrary,allowed));
  renderTemplateCharacters();
  document.getElementById('tplMsg').textContent=TPL_SEL.desc;
}
async function genFromTemplate(){
  if(!TPL_SEL) return;
  const btn=document.getElementById('tplGenBtn'), msg=document.getElementById('tplMsg');
  if(CHAR_SEL.size<2){ msg.innerHTML='<span class="err">Kam az kam 2 characters chuno.</span>'; return; }
  btn.disabled=true; btn.textContent='Writing script…';
  msg.innerHTML=feedbackMarkup('loading','AI script likh raha hai…');
  try{
    const body={template_id:TPL_SEL.id, topic:document.getElementById('tplTopic').value,
      // Templates share the right-side Story basics; no duplicated controls.
      language:document.getElementById('ffLang').value,
      length:selectedVideoDuration(), characters:activeLibraryStoryCast(),
      character_library:TEMPLATE_CHARACTER_LIBRARY};
    const j=await (await fetch('/api/story-templates/generate',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).json();
    if(j.error){ msg.innerHTML='<span class="err">'+j.error+'</span>'; }
    else{
      replaceScriptWithGenerated(j.script,TPL_SEL?.name_en||'Template story','Template');
      renderRetentionPanel(j);
      msg.innerHTML=feedbackMarkup('success','Script ready hai. Editor mein review karke Generate Video karein.');
    }
  }catch(e){ msg.innerHTML='<span class="err">Fail: '+e+'</span>'; }
  btn.disabled=false; btn.textContent='Generate Script';
}

// Phase 2 — free-form: bina template, seedha idea se script
async function genFreeform(){
  const btn=document.getElementById('ffGenBtn'), msg=document.getElementById('ffMsg');
  const idea=document.getElementById('ffIdea').value.trim();
  if(!idea){ msg.innerHTML='<span class="err">Pehle apna idea likhein.</span>'; return; }
  const pro=document.getElementById('ffPro').checked;
  btn.disabled=true; btn.textContent=pro?'Plan → Draft → Polish…':'Creating story…';
  msg.innerHTML=feedbackMarkup('loading',pro?'Pro pipeline: plan, hook variants, draft and polish.':'AI story bana raha hai.');
  try{
    const body={idea, genre:document.getElementById('ffGenre').value,
      language:document.getElementById('ffLang').value,
      length:segVal('ffLenSeg')||'1min', quality:pro?'pro':'fast',
      characters:activeLibraryStoryCast(), character_library:CAST_CHARACTER_LIBRARY};
    const j=await (await fetch('/api/freeform',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).json();
    if(j.error){ msg.innerHTML='<span class="err">'+j.error+'</span>'; }
    else{
      replaceScriptWithGenerated(j.script||'',j.title||'AI story','Quick Idea');
      renderRetentionPanel(j);
      const cast=(j.cast||[]).join(', ');
      msg.innerHTML=feedbackMarkup('success',`${j.title?`“${j.title}” · `:''}${j.genre?`${j.genre} · `:''}${cast?`${cast} · `:''}Script editor mein ready hai.`);
    }
  }catch(e){ msg.innerHTML='<span class="err">Fail: '+e+'</span>'; }
  btn.disabled=false; btn.textContent='Generate Script';
}

// Phase 3 — long-form multi-scene story
async function genLongform(){
  const btn=document.getElementById('lfGenBtn'), msg=document.getElementById('lfMsg'),
    out=document.getElementById('lfOutline');
  const idea=document.getElementById('lfIdea').value.trim();
  if(!idea){ msg.innerHTML='<span class="err">Pehle apna idea likhein.</span>'; return; }
  btn.disabled=true; btn.textContent='Building long story…';
  msg.innerHTML=feedbackMarkup('loading','Outline aur scenes likhe ja rahe hain.');
  out.innerHTML='';
  try{
    const body={idea, genre:document.getElementById('lfGenre').value,
      language:document.getElementById('lfLang').value,
      minutes:segVal('lfMinSeg')||'5min',
      characters:activeLibraryStoryCast(), character_library:CAST_CHARACTER_LIBRARY};
    const j=await (await fetch('/api/longform',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).json();
    if(j.error){ msg.innerHTML='<span class="err">'+j.error+'</span>'; }
    else{
      replaceScriptWithGenerated(j.script||'',j.title||'Long-form story','Long-form');
      renderRetentionPanel(j);
      const cast=(j.cast||[]).join(', ');
      msg.innerHTML=feedbackMarkup('success',`${j.title?`“${j.title}” · `:''}${j.genre?`${j.genre} · `:''}${cast||'Long-form story ready'}`);
      if(j.logline) msg.innerHTML+=`<div class="feedback-detail">${escHtml(j.logline)}</div>`;
      // scene outline chips
      if(j.scenes&&j.scenes.length){
        out.innerHTML=`<div class="outline-heading">${uiIcon('render')} ${j.scenes.length} scenes</div><div class="outline-list">`+j.scenes.map((s,i)=>`<div><b>${i+1}. ${escHtml(s.location||'')}</b><span>${escHtml(s.goal||'')}</span></div>`).join('')+'</div>';
      }
    }
  }catch(e){ msg.innerHTML='<span class="err">Fail: '+e+'</span>'; }
  btn.disabled=false; btn.textContent='Generate Long Story';
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
    const safeName=escHtml(c.name), safeTrait=c.trait?('- '+escHtml(c.trait.slice(0,24))):'';
    const catalogBadge=c.source==='3d_library'?'<span class="performanceBadge body">3D catalog</span>':'';
    const deleteButton=c.source==='3d_library'?'':'<button type="button" class="icon-button chip-delete" aria-label="Delete '+safeName+'" data-character-id="'+escHtml(c.id)+'" data-character-name="'+safeName+'">'+uiIcon('trash')+'</button>';
    chip.innerHTML='<b>'+safeName+'</b><span style="color:var(--muted)">'+safeTrait+'</span>'+catalogBadge+deleteButton;
    chip.querySelector('.chip-delete')?.addEventListener('click',event=>delChar(event.currentTarget.dataset.characterId,event.currentTarget.dataset.characterName));
    chip.title=(c.trait||'')+(c.catchphrase?(' - "'+c.catchphrase+'"'):'');
    el.appendChild(chip);
  });
}

async function addChar(){
  const name=document.getElementById('chName').value.trim();
  if(!name){ notifyValidation('Character ka naam likhein.','chName'); return; }
  await fetch('/api/characters-lib',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name, gender:document.getElementById('chGender').value,
      trait:document.getElementById('chTrait').value, catchphrase:document.getElementById('chPhrase').value})});
  document.getElementById('chName').value='';document.getElementById('chTrait').value='';document.getElementById('chPhrase').value='';
  await loadLib();
}
async function delChar(cid,name='character'){
  requestCharacterDelete(cid,name);
}
function renderSeriesSel(){
  const sel=document.getElementById('serSel'), menu=document.getElementById('serOptions'); if(!sel||!menu)return;
  const cur=sel.value;
  sel.innerHTML='<option value="">Select series</option>';
  SERIES.forEach(s=>{const o=document.createElement('option');o.value=s.id;
    o.textContent=s.name+' ('+s.episodes+' ep)';sel.appendChild(o);});
  sel.value=SERIES.some(series=>String(series.id)===String(cur))?cur:'';
  menu.innerHTML='';
  if(!SERIES.length){
    const empty=document.createElement('div');empty.className='series-dropdown-empty';
    empty.innerHTML='<strong>No saved series yet</strong><span>Create a new series to start episode continuity.</span>';
    menu.appendChild(empty);
  }else{
    SERIES.forEach(series=>{
      const episodes=Number(series.episodes||0), option=document.createElement('button');
      option.type='button';option.className='series-dropdown-option';option.dataset.seriesId=series.id;
      option.setAttribute('role','option');option.setAttribute('aria-selected',String(String(series.id)===String(sel.value)));
      const copy=document.createElement('span'), name=document.createElement('strong'), meta=document.createElement('small'), count=document.createElement('span');
      copy.className='series-option-copy';name.textContent=series.name;meta.textContent=episodes?`Continue with episode ${episodes+1}`:'Start the first episode';
      count.className='series-option-count';count.textContent=`${episodes} ${episodes===1?'episode':'episodes'}`;
      copy.append(name,meta);option.append(copy,count);
      option.onclick=()=>chooseSeries(series.id);option.onkeydown=handleSeriesOptionKeydown;
      menu.appendChild(option);
    });
  }
  syncSeriesDropdownDisplay();
}
function syncSeriesDropdownDisplay(){
  const sel=document.getElementById('serSel'), label=document.getElementById('serDropdownLabel'), meta=document.getElementById('serDropdownMeta');
  if(!sel||!label||!meta)return;
  const series=SERIES.find(item=>String(item.id)===String(sel.value));
  label.textContent=series?.name||'Select a series';
  if(series){const episodes=Number(series.episodes||0);meta.textContent=episodes?`${episodes} ${episodes===1?'episode':'episodes'} saved \u00b7 Episode ${episodes+1} is next`:'Ready for episode 1';}
  else meta.textContent=SERIES.length?'Choose a saved story to continue':'No saved series \u00b7 create your first one';
  document.querySelectorAll('#serOptions [role="option"]').forEach(option=>option.setAttribute('aria-selected',String(String(option.dataset.seriesId)===String(sel.value))));
}
function setSeriesDropdownOpen(open,focusOption=false){
  const dropdown=document.getElementById('seriesDropdown'), button=document.getElementById('serDropdownButton'), menu=document.getElementById('serOptions');
  if(!dropdown||!button||!menu)return;
  const shouldOpen=!!open;dropdown.classList.toggle('open',shouldOpen);menu.classList.toggle('hidden',!shouldOpen);button.setAttribute('aria-expanded',String(shouldOpen));
  if(shouldOpen&&focusOption){
    const selected=menu.querySelector('[role="option"][aria-selected="true"]'), first=menu.querySelector('[role="option"]');
    (selected||first)?.focus();
  }
}
function toggleSeriesDropdown(event){event?.stopPropagation();const button=document.getElementById('serDropdownButton');setSeriesDropdownOpen(button?.getAttribute('aria-expanded')!=='true');}
function handleSeriesDropdownKeydown(event){
  if(['ArrowDown','ArrowUp','Enter',' '].includes(event.key)){event.preventDefault();setSeriesDropdownOpen(true,true);}
  else if(event.key==='Escape')setSeriesDropdownOpen(false);
}
function handleSeriesOptionKeydown(event){
  const options=[...document.querySelectorAll('#serOptions [role="option"]')], index=options.indexOf(event.currentTarget);
  if(event.key==='ArrowDown'){event.preventDefault();options[(index+1)%options.length]?.focus();}
  else if(event.key==='ArrowUp'){event.preventDefault();options[(index-1+options.length)%options.length]?.focus();}
  else if(event.key==='Home'){event.preventDefault();options[0]?.focus();}
  else if(event.key==='End'){event.preventDefault();options.at(-1)?.focus();}
  else if(event.key==='Escape'){event.preventDefault();setSeriesDropdownOpen(false);document.getElementById('serDropdownButton')?.focus();}
  else if(event.key==='Tab')setSeriesDropdownOpen(false);
}
function chooseSeries(sid){
  const sel=document.getElementById('serSel');if(!sel)return;
  sel.value=String(sid);syncSeriesDropdownDisplay();setSeriesDropdownOpen(false);document.getElementById('serDropdownButton')?.focus();selectSeries(sid);
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
function toggleNewSeries(){
  setSeriesDropdownOpen(false);
  const box=document.getElementById('newSeriesBox'), button=document.getElementById('newSeriesButton');box.classList.toggle('hidden');
  button?.setAttribute('aria-expanded',String(!box.classList.contains('hidden')));NEW_CAST=new Set();renderCastPicker();
  if(!box.classList.contains('hidden'))document.getElementById('serName')?.focus();
}
async function createSeries(){
  const name=document.getElementById('serName').value.trim();
  if(!name){ notifyValidation('Series naam likhein.','serName'); return; }
  if(NEW_CAST.size<1){ notifyValidation('Kam az kam 1 cast character chuno.','','epMsg'); return; }
  const r=await (await fetch('/api/series',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name, premise:document.getElementById('serPremise').value,
      genre:document.getElementById('serGenre').value, language:document.getElementById('serLang').value,
      cast:[...NEW_CAST]})})).json();
  if(r.error){ showStudioToast(r.error,'danger','Series could not be created'); return; }
  document.getElementById('newSeriesBox').classList.add('hidden');
  document.getElementById('newSeriesButton')?.setAttribute('aria-expanded','false');
  document.getElementById('serName').value='';document.getElementById('serPremise').value='';
  await loadLib();
  chooseSeries(r.id);
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
    ? '<b>'+eps.length+' Episodes:</b>'+eps.map(e=>'<div style="padding:2px 0"><b>Ep '+e.num+':</b> '+e.title+' <span style="color:var(--muted)">— '+(e.summary||'').slice(0,80)+'</span></div>').join('')
    : '<span style="color:var(--muted)">Abhi koi episode nahi — Ep 1 banao.</span>';
  document.getElementById('epGenBtn').textContent='Generate Episode '+(eps.length+1);
}
async function genEpisode(){
  if(!CUR_SERIES) return;
  const btn=document.getElementById('epGenBtn'), msg=document.getElementById('epMsg');
  btn.disabled=true; btn.textContent='Creating episode…';
  msg.innerHTML=feedbackMarkup('loading','Cast aur previous episodes ki continuity use ho rahi hai.');
  try{
    const j=await (await fetch('/api/series/'+CUR_SERIES.id+'/episode',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({idea:document.getElementById('epIdea').value, length:segVal('epLenSeg')||'1min'})})).json();
    if(j.error){ msg.innerHTML='<span class="err">'+j.error+'</span>'; }
    else{
      replaceScriptWithGenerated(j.script||'',j.title||CUR_SERIES.name,'Series episode');
      renderRetentionPanel(j);
      msg.innerHTML=feedbackMarkup('success',`Episode ${j.episode_num}: “${j.title}”`)
        +`<div class="feedback-detail">${escHtml(j.summary||'')}</div>`;
      document.getElementById('epIdea').value='';
      await selectSeries(CUR_SERIES.id);  // history refresh
    }
  }catch(e){ msg.innerHTML='<span class="err">Fail: '+e+'</span>'; }
  btn.disabled=false;
}
// Keep every script generator on the same duration vocabulary. Template markup
// remains backward-compatible, then is upgraded here before event binding.
const VIDEO_DURATION_OPTIONS=[['30sec','30 sec'],['1min','1 min'],['2min','2 min'],['3min','3 min'],['5min','5 min'],['8min','8 min'],['10min','10 min'],['15min','15 min']];
function hydrateDurationSegment(id,defaultValue='1min'){
  const seg=document.getElementById(id); if(!seg) return;
  seg.classList.add('duration-grid','duration-grid-wide');
  seg.innerHTML=VIDEO_DURATION_OPTIONS.map(([value,label])=>`<button type="button" data-v="${value}" class="${value===defaultValue?'on':''}">${label}</button>`).join('');
}

// segmented buttons
document.querySelectorAll('.seg').forEach(seg=>{
  seg.querySelectorAll('button').forEach(b=>b.onclick=()=>{
    seg.querySelectorAll('button').forEach(x=>x.classList.remove('on'));
    b.classList.add('on');
    renderWorkflowSummary();
    scheduleWorkspaceAutosave();
  });
});
function segVal(id){const e=document.querySelector('#'+id+' button.on');return e?e.dataset.v:null;}
function setSegVal(id,value){
  const seg=document.getElementById(id); if(!seg) return false;
  let matched=false;
  seg.querySelectorAll('button').forEach(button=>{
    const active=button.dataset.v===value; button.classList.toggle('on',active); matched=matched||active;
  });
  return matched;
}
function selectedVideoDuration(){ return segVal('ffLenSeg')||'1min'; }

function schedulePastedScriptPlan(){
  clearTimeout(MANUAL_SCENE_TIMER);
  const token=++MANUAL_SCENE_TOKEN;
  MANUAL_SCENE_TIMER=setTimeout(async()=>{
    const editor=document.getElementById('script'), script=editor?.value.trim()||'';
    if(token!==MANUAL_SCENE_TOKEN||script.length<10) return;
    const feedback=document.getElementById('scriptFeedback');
    if(feedback) feedback.innerHTML=feedbackMarkup('loading','Pasted script detected. Cast aur scenes automatically ban rahe hain.');
    await preview({automatic:true,sourceScript:script});
  },700);
}

// Phase 2 desktop workspace shell. This stays provider/backend neutral and only
// coordinates existing DOM controls, views, and workflow state.
const STUDIO_SESSION_KEY='sbz-studio-session-v2';
const STUDIO_STEP_TITLES=['','Script setup','Cast & scene focus','Style & audio','Render setup'];
let STUDIO_UI={view:'dashboard',step:1,projectName:'Untitled video',scriptMode:'write',aiTab:'quick'};
let WORKSPACE_INITIALIZED=false, AUTOSAVE_TIMER=null, GENERATED_SCRIPT_UNDO=null, TOAST_TIMER=null, ADVANCED_RETURN_FOCUS=null;
let GENERATION_STARTED_AT=0, ELAPSED_TIMER=null, RENDER_ESTIMATE_TOKEN=0, CURRENT_RESULT_PROJECT='', DELETE_PENDING=null;

function setAutosaveState(state,label){
  const el=document.getElementById('autosaveStatus');
  if(!el) return;
  el.classList.remove('saving','saved');
  if(state) el.classList.add(state);
  el.innerHTML='<span class="status-dot"></span> '+(label||'Autosave ready');
}

function workspaceSnapshot(){
  const fields={};
  document.querySelectorAll('input[id],select[id],textarea[id]').forEach(el=>{
    if(el.type==='button' || el.id.startsWith('castInspector')) return;
    fields[el.id]=el.type==='checkbox'?{checked:el.checked}:{value:el.value};
  });
  const segments={};
  document.querySelectorAll('.seg[id]').forEach(seg=>{segments[seg.id]=segVal(seg.id);});
  return {view:STUDIO_UI.view,step:STUDIO_UI.step,projectName:STUDIO_UI.projectName,
    scriptMode:STUDIO_UI.scriptMode,aiTab:STUDIO_UI.aiTab,fields,segments};
}

function saveWorkspaceDraft(){
  try{
    sessionStorage.setItem(STUDIO_SESSION_KEY,JSON.stringify(workspaceSnapshot()));
    setAutosaveState('saved','Session saved');
  }catch(e){ setAutosaveState('','Session active'); }
}

function scheduleWorkspaceAutosave(){
  if(!WORKSPACE_INITIALIZED) return;
  setAutosaveState('saving','Saving…');
  clearTimeout(AUTOSAVE_TIMER);
  AUTOSAVE_TIMER=setTimeout(saveWorkspaceDraft,450);
}

function restoreWorkspaceDraft(){
  try{
    const raw=sessionStorage.getItem(STUDIO_SESSION_KEY);
    if(!raw) return null;
    const draft=JSON.parse(raw);
    Object.entries(draft.fields||{}).forEach(([id,state])=>{
      const el=document.getElementById(id); if(!el) return;
      if(Object.prototype.hasOwnProperty.call(state,'checked')) el.checked=!!state.checked;
      else if(el.tagName==='SELECT'){
        if([...el.options].some(option=>option.value===String(state.value))) el.value=state.value;
      }else el.value=state.value==null?'':state.value;
    });
    Object.entries(draft.segments||{}).forEach(([id,value])=>{
      const seg=document.getElementById(id); if(!seg || value==null) return;
      seg.querySelectorAll('button').forEach(button=>button.classList.toggle('on',button.dataset.v===value));
    });
    STUDIO_UI.view=draft.view||'dashboard';
    STUDIO_UI.step=Math.min(4,Math.max(1,Number(draft.step)||1));
    STUDIO_UI.projectName=draft.projectName||'Untitled video';
    STUDIO_UI.scriptMode=draft.scriptMode==='ai'?'ai':'write';
    STUDIO_UI.aiTab=['quick','longform','series','templates'].includes(draft.aiTab)?draft.aiTab:'quick';
    return draft;
  }catch(e){ return null; }
}

function closeTopPopovers(){
  document.querySelectorAll('.top-popover').forEach(popover=>popover.classList.add('hidden'));
  document.querySelectorAll('.popover-wrap>[aria-expanded]').forEach(button=>button.setAttribute('aria-expanded','false'));
}

function toggleTopPopover(id,button){
  const popover=document.getElementById(id); if(!popover) return;
  const open=popover.classList.contains('hidden');
  closeTopPopovers();
  popover.classList.toggle('hidden',!open);
  if(button) button.setAttribute('aria-expanded',String(open));
}

function toggleInspector(force){
  const open=typeof force==='boolean'?force:!document.body.classList.contains('inspector-open');
  if(open && STUDIO_UI.view!=='create') showStudioView('create',false);
  document.body.classList.toggle('inspector-open',open);
  const toggle=document.getElementById('inspectorToggle');
  if(toggle) toggle.setAttribute('aria-expanded',String(open));
}

function syncAdvancedSettingsUI(){
  const music=document.getElementById('music_volume');
  const value=document.getElementById('musicVolumeValue');
  if(music && value) value.textContent=`${Math.round(Number(music.value||0)*100)}%`;
}

function toggleAdvancedSettings(force,section=''){
  const drawer=document.getElementById('advancedSettingsDrawer'); if(!drawer) return;
  const open=typeof force==='boolean'?force:!document.body.classList.contains('advanced-settings-open');
  if(open){
    ADVANCED_RETURN_FOCUS=document.activeElement;
    closeTopPopovers(); toggleInspector(false);
  }
  document.body.classList.toggle('advanced-settings-open',open);
  drawer.setAttribute('aria-hidden',String(!open));
  document.querySelectorAll('[data-advanced-settings-trigger]').forEach(button=>button.setAttribute('aria-expanded',String(open)));
  if(open){
    syncAdvancedSettingsUI();
    const group=section==='captions'?document.getElementById('advancedCaptionsGroup'):
      section==='providers'?document.getElementById('advancedProviderGroup'):document.getElementById('advancedRenderGroup');
    if(group){group.open=true;requestAnimationFrame(()=>group.scrollIntoView({block:'start',behavior:'smooth'}));}
    document.getElementById('advancedSettingsClose')?.focus();
  }else if(ADVANCED_RETURN_FOCUS && typeof ADVANCED_RETURN_FOCUS.focus==='function'){
    ADVANCED_RETURN_FOCUS.focus(); ADVANCED_RETURN_FOCUS=null;
  }
}

function modalFocusable(container){
  return [...container.querySelectorAll('button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),summary,[tabindex]:not([tabindex="-1"])')]
    .filter(element=>element.getClientRects().length>0);
}

function trapModalFocus(event){
  if(event.key!=='Tab') return;
  const deleteDialog=document.getElementById('deleteProjectDialog');
  const activeDialog=deleteDialog&&!deleteDialog.classList.contains('hidden')?deleteDialog:
    document.body.classList.contains('advanced-settings-open')?document.getElementById('advancedSettingsDrawer'):null;
  if(!activeDialog) return;
  const focusable=modalFocusable(activeDialog); if(!focusable.length) return;
  const first=focusable[0],last=focusable[focusable.length-1];
  if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
  else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
}

function showStudioView(view,persist=true){
  const panel=document.querySelector(`[data-view-panel="${view}"]`); if(!panel) return;
  STUDIO_UI.view=view;
  document.querySelectorAll('[data-view-panel]').forEach(item=>item.classList.toggle('active',item===panel));
  document.querySelectorAll('.nav-item[data-view]').forEach(item=>{
    const active=item.dataset.view===view;
    item.classList.toggle('active',active); item.setAttribute('aria-selected',String(active));
  });
  const shell=document.getElementById('studioShell');
  if(shell) shell.classList.toggle('no-inspector',view!=='create');
  document.body.classList.remove('inspector-open');
  toggleAdvancedSettings(false);
  if(view==='create') setCreateStep(STUDIO_UI.step,false);
  if(view==='projects') loadProjectsList();
  if(view==='dashboard'){checkResumable();loadProjectsList();}
  document.getElementById('workspace')?.scrollTo({top:0,behavior:'auto'});
  closeTopPopovers();
  if(persist) scheduleWorkspaceAutosave();
}

function setCreateStep(step,persist=true){
  step=Math.min(4,Math.max(1,Number(step)||1));
  STUDIO_UI.step=step;
  if(STUDIO_UI.view!=='create'){
    STUDIO_UI.view='create';
    showStudioView('create',false);
  }
  document.querySelectorAll('[data-step-panel]').forEach(panel=>panel.classList.toggle('active',Number(panel.dataset.stepPanel)===step));
  document.querySelectorAll('.workflow-step[data-step]').forEach(button=>{
    const current=Number(button.dataset.step), active=current===step;
    button.classList.toggle('active',active); button.classList.toggle('complete',current<step);
    button.setAttribute('aria-selected',String(active));
  });
  document.querySelectorAll('[data-inspector-step]').forEach(panel=>panel.classList.toggle('active',Number(panel.dataset.inspectorStep)===step));
  const title=document.getElementById('inspectorTitle'); if(title) title.textContent=STUDIO_STEP_TITLES[step];
  const createTitle=document.getElementById('createViewTitle');
  if(createTitle) createTitle.textContent=['','Build your story','Shape cast and scenes','Set the look and sound','Preview and render'][step];
  if(step===2){
    const hasRenderedPreview=!!document.querySelector('#pvScenes .pvScene');
    document.getElementById('castEmptyState')?.classList.toggle('hidden',hasRenderedPreview);
    document.getElementById('previewCard')?.classList.toggle('hidden',!hasRenderedPreview);
  }
  if(step===4) renderWorkflowSummary();
  document.getElementById('workspace')?.scrollTo({top:0,behavior:'auto'});
  if(window.innerWidth<1280) document.body.classList.remove('inspector-open');
  if(persist) scheduleWorkspaceAutosave();
}

function updateScriptCount(){
  const value=document.getElementById('script')?.value||'';
  const words=(value.trim().match(/\S+/g)||[]).length;
  const lines=value?value.split(/\r?\n/).filter(line=>line.trim()).length:0;
  updateScriptLanguageIndicator(value);
  const out=document.getElementById('scriptCount');
  if(out) out.textContent=`${words} ${words===1?'word':'words'} · ${lines} ${lines===1?'line':'lines'}`;
}

function updateScriptLanguageIndicator(value=''){
  const out=document.getElementById('scriptLanguageIndicator'); if(!out) return;
  if(/[\u0600-\u06ff]/.test(value)) out.textContent='Urdu';
  else{
    const selected=document.getElementById('ffLang')?.value||'roman_urdu';
    const labels={english:'English',hindi:'Hindi',hinglish:'Hindi + English 85/15',urdu:'Urdu',roman_urdu:'Roman Urdu'};
    out.textContent=labels[selected]||'Roman Urdu';
  }
}

function renderWorkflowSummary(){
  const aspectLabels={landscape:'Landscape',portrait:'Portrait',square:'Square'};
  const engine=document.getElementById('render_engine')?.value||'threejs';
  const quality=document.getElementById('quality')?.value||'1080p';
  const tts=document.getElementById('tts_provider')?.value||'edge';
  const aspect=segVal('aspectSeg')||'landscape';
  const set=(id,value)=>{const el=document.getElementById(id);if(el)el.textContent=value;};
  set('summaryStoryMode','3D Characters');
  set('summaryFormat',`${aspectLabels[aspect]||aspect} · ${quality}`);
  const voiceLabels={elevenlabs:'ElevenLabs',google:'Google Cloud TTS',edge:'Edge TTS'};
  set('summaryVoice',voiceLabels[tts]||tts);
  set('summarySubtitles',document.getElementById('cap_enabled')?.checked?'Enabled':'Optional');
  set('renderSceneCount',PLAN?.scenes?.length??PLAN?.parsed?.scenes?.length??'—');
  set('renderCharacterCount',PLAN?.characters?.length??PLAN?.parsed?.characters?.length??'—');
  set('renderQuality',quality);
  set('renderEngineSummary',engine==='blender'?'Blender':'Three.js');
  set('renderProjectTitle',STUDIO_UI.projectName||'Untitled video');
  set('renderFormatSummary',`${aspectLabels[aspect]||aspect} · ${quality}`);
  set('renderVoiceSummary',voiceLabels[tts]||tts);
  set('renderCaptionSummary',document.getElementById('cap_enabled')?.checked?'Enabled':'Optional');
  const metrics=getRenderMetrics();
  set('renderSceneCount',metrics.scenes);
  set('renderCharacterCount',metrics.characters);
  set('renderEstimatedDuration',formatRenderDuration(metrics.duration));
  const hasScript=(document.getElementById('script')?.value.trim().length||0)>=10;
  const direct=document.getElementById('genBtn'), primary=document.getElementById('pvGenBtn');
  if(direct) direct.disabled=!hasScript;
  if(primary) primary.disabled=!hasScript;
  if(STUDIO_UI.step===4) updateRenderEstimate(metrics);
  syncAdvancedSettingsUI();
}

function getRenderMetrics(){
  const script=document.getElementById('script')?.value.trim()||'';
  const planScenes=PLAN?.scenes||PLAN?.parsed?.scenes||[];
  const planCharacters=PLAN?.characters||PLAN?.parsed?.characters||[];
  const sceneCards=[...document.querySelectorAll('#pvScenes .pvScene')];
  const scenes=sceneCards.length||planScenes.length||Math.max(1,(script.match(/^\s*\[?scene\b/gim)||[]).length);
  const lines=sceneCards.length?document.querySelectorAll('#pvScenes .pvLine').length:
    planScenes.reduce((total,scene)=>total+(scene.lines||[]).length,0)||script.split(/\r?\n/).filter(line=>line.includes(':')).length||1;
  const speakerNames=new Set(script.split(/\r?\n/).map(line=>(line.match(/^\s*([^:\n]{1,40}):/)||[])[1]).filter(Boolean));
  const characters=planCharacters.length||Math.max(1,speakerNames.size);
  let duration=0;
  sceneCards.forEach(scene=>{
    const raw=String(scene.dataset.duration||'');
    const value=parseFloat(raw)||0;
    duration+=/min/i.test(raw)?value*60:value;
  });
  if(!duration){
    const words=(script.match(/\S+/g)||[]).length;
    duration=Math.max(5,Math.round(words/2.2+lines*.45));
  }
  return {scenes,lines,characters,duration};
}

function formatRenderDuration(seconds){
  const total=Math.max(0,Math.round(Number(seconds)||0));
  const minutes=Math.floor(total/60), remaining=total%60;
  return minutes?`${minutes}m ${String(remaining).padStart(2,'0')}s`:`${remaining}s`;
}

async function updateRenderEstimate(metrics=getRenderMetrics()){
  const token=++RENDER_ESTIMATE_TOKEN;
  const out=document.getElementById('renderEstimatedCost'), detail=document.getElementById('costEst');
  if(out) out.textContent='Calculating…';
  try{
    const response=await fetch('/api/cost',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scenes:metrics.scenes,lines:metrics.lines,chars:metrics.characters})});
    const cost=await response.json(); if(token!==RENDER_ESTIMATE_TOKEN) return;
    if(out) out.textContent=`$${Number(cost.total||0).toFixed(2)}`;
    if(detail) detail.textContent=`Estimate includes story, ${metrics.scenes} backgrounds, ${metrics.characters} characters${Number(cost.ai_video||0)>0?' and AI video clips':''}.`;
  }catch(error){
    if(token!==RENDER_ESTIMATE_TOKEN) return;
    if(out) out.textContent='Unavailable';
    if(detail) detail.textContent='Cost estimate will not affect generation.';
  }
}

function setCurrentProject(name){
  STUDIO_UI.projectName=name||'Untitled video';
  const el=document.getElementById('currentProjectName'); if(el) el.textContent=STUDIO_UI.projectName;
  const renderTitle=document.getElementById('renderProjectTitle'); if(renderTitle) renderTitle.textContent=STUDIO_UI.projectName;
  scheduleWorkspaceAutosave();
}

function focusGeneratedScript(title){
  if(title) setCurrentProject(title);
  showStudioView('create',false); setCreateStep(1,false); updateScriptCount();
  selectScriptMode('write',false);
  document.getElementById('script')?.scrollIntoView({behavior:'smooth',block:'center'});
  scheduleWorkspaceAutosave();
}

function replaceScriptWithGenerated(script,title,source='AI'){
  const editor=document.getElementById('script'); if(!editor) return;
  GENERATED_SCRIPT_UNDO={text:editor.value,projectName:STUDIO_UI.projectName};
  editor.value=script||'';
  focusGeneratedScript(title);
  showGenerationToast(`${source} script editor mein ready hai. Aap isay edit ya undo kar sakte hain.`,true);
}

function showGenerationToast(message,allowUndo=false){
  showStudioToast(message,'success',allowUndo?'Script ready':'Success',allowUndo);
}

function undoGeneratedScript(){
  if(!GENERATED_SCRIPT_UNDO){acceptGeneratedScript();return;}
  const editor=document.getElementById('script');
  if(editor) editor.value=GENERATED_SCRIPT_UNDO.text;
  setCurrentProject(GENERATED_SCRIPT_UNDO.projectName);
  GENERATED_SCRIPT_UNDO=null;
  updateScriptCount(); scheduleWorkspaceAutosave();
  const toast=document.getElementById('generationToast'); if(toast) toast.classList.add('hidden');
  editor?.focus();
}

function acceptGeneratedScript(){
  GENERATED_SCRIPT_UNDO=null;
  clearTimeout(TOAST_TIMER);
  document.getElementById('generationToast')?.classList.add('hidden');
}

function populateCastInspector(plan){
  const character=document.getElementById('castInspectorCharacter');
  const voice=document.getElementById('castInspectorVoice');
  const emotion=document.getElementById('castInspectorEmotion');
  const action=document.getElementById('castInspectorAction');
  const background=document.getElementById('castInspectorBackground');
  const characters=plan?.characters||[];
  character.innerHTML=characters.map(item=>`<option value="${escHtml(item.name||item.id)}">${escHtml(item.name||item.id)}</option>`).join('')||'<option>No characters</option>';
  character.disabled=!characters.length;
  voice.value=characters[0]?.voice||'Automatic';
  const firstLine=document.querySelector('#pvScenes .pvLine');
  const firstScene=document.querySelector('#pvScenes .pvScene');
  if(firstLine) selectPreviewLine(firstLine);
  else if(firstScene) selectPreviewScene(firstScene);
  else{
    emotion.disabled=true; action.disabled=true; background.disabled=true;
    document.getElementById('castInspectorSelection').textContent='No editable scenes in this plan.';
  }
}

function selectedPreviewLine(){ return document.querySelector('#pvScenes .pvLine.active'); }
function selectedPreviewScene(){ return selectedPreviewLine()?.closest('.pvScene')||document.querySelector('#pvScenes .pvScene.active'); }
function findPlanCharacterBySpeaker(speaker){
  return (PLAN?.characters||[]).find(item=>String(item.name)===String(speaker)||String(item.id)===String(speaker));
}

function selectPreviewScene(scene,keepLine=false){
  if(!scene) return;
  if(!keepLine){
    document.querySelectorAll('#pvScenes .pvLine').forEach(item=>item.classList.remove('active'));
    document.getElementById('castInspectorCharacter').disabled=true;
    document.getElementById('castInspectorEmotion').disabled=true;
    document.getElementById('castInspectorAction').disabled=true;
  }
  document.querySelectorAll('#pvScenes .pvScene').forEach(item=>item.classList.toggle('active',item===scene));
  const scenes=[...document.querySelectorAll('#pvScenes .pvScene')], order=scenes.indexOf(scene)+1;
  const selection=document.getElementById('castInspectorSelection');
  if(selection) selection.textContent=`Scene ${order} selected`;
  const background=document.getElementById('castInspectorBackground');
  const mood=document.getElementById('castInspectorMood');
  background.disabled=false; background.value=scene.querySelector('.pvBg')?.value||'';
  mood.disabled=false; mood.value=scene.querySelector('.pvMood')?.value||'';
  document.getElementById('castInspectorScene').value=`Scene ${order}`;
  document.getElementById('castInspectorDuration').value=scene.dataset.duration||'—';
}

function selectPreviewLine(line){
  if(!line) return;
  document.querySelectorAll('#pvScenes .pvLine').forEach(item=>item.classList.toggle('active',item===line));
  const scene=line.closest('.pvScene'); selectPreviewScene(scene,true);
  const lines=[...scene.querySelectorAll('.pvLine')], lineNumber=lines.indexOf(line)+1;
  const scenes=[...document.querySelectorAll('#pvScenes .pvScene')], sceneNumber=scenes.indexOf(scene)+1;
  document.getElementById('castInspectorSelection').textContent=`Scene ${sceneNumber} · Dialogue ${lineNumber}`;
  const speaker=line.querySelector('.pvSpeaker')?.value||'';
  const character=document.getElementById('castInspectorCharacter');
  character.disabled=false;
  if([...character.options].some(option=>option.value===speaker)) character.value=speaker;
  const selected=findPlanCharacterBySpeaker(speaker);
  document.getElementById('castInspectorVoice').value=selected?.voice||'Automatic';
  const emotion=document.getElementById('castInspectorEmotion');
  const action=document.getElementById('castInspectorAction');
  emotion.disabled=false; emotion.value=line.querySelector('.pvEmo')?.value||'neutral';
  action.disabled=false; action.value=line.querySelector('.pvAction')?.value||'';
}

function bindCastInspector(){
  const character=document.getElementById('castInspectorCharacter');
  character?.addEventListener('change',()=>{
    const line=selectedPreviewLine(), speaker=line?.querySelector('.pvSpeaker');
    if(speaker && [...speaker.options].some(option=>option.value===character.value)) speaker.value=character.value;
    const selected=findPlanCharacterBySpeaker(character.value);
    document.getElementById('castInspectorVoice').value=selected?.voice||'Automatic';
    validatePreviewPlan(false);
  });
  document.getElementById('castInspectorEmotion')?.addEventListener('change',event=>{
    const target=selectedPreviewLine()?.querySelector('.pvEmo'); if(target) target.value=event.target.value;
    scheduleWorkspaceAutosave();
  });
  document.getElementById('castInspectorAction')?.addEventListener('input',event=>{
    const target=selectedPreviewLine()?.querySelector('.pvAction'); if(target) target.value=event.target.value;
    scheduleWorkspaceAutosave();
  });
  document.getElementById('castInspectorBackground')?.addEventListener('input',event=>{
    const target=selectedPreviewScene()?.querySelector('.pvBg'); if(target) target.value=event.target.value;
    validatePreviewPlan(false);
    scheduleWorkspaceAutosave();
  });
  document.getElementById('castInspectorMood')?.addEventListener('input',event=>{
    const target=selectedPreviewScene()?.querySelector('.pvMood'); if(target) target.value=event.target.value;
    scheduleWorkspaceAutosave();
  });
  const scenes=document.getElementById('pvScenes');
  scenes?.addEventListener('click',event=>{
    const move=event.target.closest('[data-move-scene]');
    if(move){moveSceneCard(move,Number(move.dataset.moveScene));return;}
    const line=event.target.closest('.pvLine');
    if(line) selectPreviewLine(line);
    else{
      const scene=event.target.closest('.pvScene'); if(scene) selectPreviewScene(scene);
    }
  });
  const syncSelection=event=>{
    const line=event.target.closest('.pvLine'); if(line) selectPreviewLine(line);
    else{
      const scene=event.target.closest('.pvScene');
      if(scene){
        if(event.target.classList.contains('pvMood')) scene.querySelector('.pvMoodBadge').textContent=event.target.value||'neutral';
        selectPreviewScene(scene);
      }
    }
    validatePreviewPlan(false); scheduleWorkspaceAutosave();
  };
  scenes?.addEventListener('input',syncSelection);
  scenes?.addEventListener('change',syncSelection);
}

function initStudioWorkspace(){
  if(WORKSPACE_INITIALIZED) return;
  document.querySelectorAll('.nav-item[data-view]').forEach(item=>item.addEventListener('click',()=>showStudioView(item.dataset.view)));
  document.querySelectorAll('.workflow-step[data-step]').forEach(item=>item.addEventListener('click',()=>setCreateStep(item.dataset.step)));
  const scriptEditor=document.getElementById('script');
  scriptEditor?.addEventListener('input',()=>{
    updateScriptCount();
    SCRIPT_ENGINE_APPROVED=false;
    if(PLAN&&scriptEditor.value.trim()!==PLAN_SOURCE_SCRIPT){
      PLAN=null; PLAN_SOURCE_SCRIPT='';
      document.getElementById('previewCard')?.classList.add('hidden');
      document.getElementById('castEmptyState')?.classList.remove('hidden');
    }
  });
  scriptEditor?.addEventListener('paste',()=>setTimeout(schedulePastedScriptPlan,0));
  document.addEventListener('input',event=>{if(event.target.hasAttribute('aria-invalid'))event.target.removeAttribute('aria-invalid');if(event.target.closest('#studioShell,#advancedSettingsDrawer')){syncAdvancedSettingsUI();scheduleWorkspaceAutosave();}},true);
  document.addEventListener('change',event=>{if(event.target.closest('#studioShell,#advancedSettingsDrawer')){renderWorkflowSummary();scheduleWorkspaceAutosave();}},true);
  document.addEventListener('click',event=>{if(!event.target.closest('.popover-wrap'))closeTopPopovers();if(!event.target.closest('.project-overflow'))closeProjectMenus();if(!event.target.closest('#seriesDropdown'))setSeriesDropdownOpen(false);});
  document.addEventListener('keydown',event=>{trapModalFocus(event);if(event.key==='Escape'){closeTopPopovers();closeProjectMenus();setSeriesDropdownOpen(false);closeDeleteProjectDialog();toggleInspector(false);toggleAdvancedSettings(false);}});
  window.addEventListener('resize',()=>{if(window.innerWidth>=1280)document.body.classList.remove('inspector-open');});
  bindCastInspector();
  restoreWorkspaceDraft();
  WORKSPACE_INITIALIZED=true;
  document.getElementById('currentProjectName').textContent=STUDIO_UI.projectName;
  selectScriptMode(STUDIO_UI.scriptMode,false);
  selectAIGenerator(STUDIO_UI.aiTab,false);
  document.getElementById('ffLang')?.addEventListener('change',()=>updateScriptLanguageIndicator(document.getElementById('script')?.value||''));
  syncVoiceProviderUI(); syncAdvancedSettingsUI(); updateScriptCount(); renderWorkflowSummary();
  showStudioView(STUDIO_UI.view,false);
  setAutosaveState('saved','Session saved');
}

function collectSettings(){
  const ttsProvider=document.getElementById('tts_provider').value;
  return {
    style: document.getElementById('style').value,
    aspect: segVal('aspectSeg'),
    quality: document.getElementById('quality').value,
    fps: document.getElementById('fps').value,
    fast_preview: document.getElementById('fast_preview').checked,
    multi_char: document.getElementById('multiChar').checked,
    render_engine: document.getElementById('render_engine').value,
    gpu: document.getElementById('gpu_encode').checked ? 'auto' : 'off',
    vignette: document.getElementById('vignette').checked,
    subtitles_on: document.getElementById('cap_enabled').checked,
    intro_on: document.getElementById('intro_on').checked,
    outro_on: true,
    tts_provider: ttsProvider,
    urdu_accent: ttsProvider==='edge' ? document.getElementById('urdu_accent').value : '',
    edge_voice: ttsProvider==='edge' ? (document.getElementById('edge_voice')?.value||'') : '',
    google_tts_voice: ttsProvider==='google' ? (document.getElementById('google_tts_voice')?.value||'') : '',
    elevenlabs_voice_id: ttsProvider==='elevenlabs' ? document.getElementById('elevenlabs_voice_id').value : '',
    voice_speed: Number(document.getElementById('voice_speed')?.value||1),
    target_duration: selectedVideoDuration(),
    llm_provider: document.getElementById('llm_provider')?.value||OPTS?.defaults?.llm_provider||'runware',
    llm_model: document.getElementById('llm_model')?.value||OPTS?.defaults?.llm_model||'',
    voice_volume: document.getElementById('voice_volume').value,
    music_volume: document.getElementById('music_volume').value,
    music_track: document.getElementById('music_track')?.value||'auto',
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
  if(script.length<10){notifyValidation('Pehle script likhein.','script','scriptFeedback');return;}
  const r=await (await fetch('/api/suggest-style',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({script})})).json();
  if(r.style) document.getElementById('style').value=r.style;
}

function _scriptLang(){ const t=document.getElementById('ffLang'); return t?t.value:'roman_urdu'; }

async function analyzeScript(){
  const script=document.getElementById('script').value.trim();
  const fb=document.getElementById('scriptFeedback');
  if(script.length<10){fb.innerHTML='<span class="err">Pehle script likhein</span>';return;}
  fb.innerHTML=feedbackMarkup('loading','Script analyze ho raha hai.','info');
  try{
    const r=await (await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({script,language:_scriptLang()})})).json();
    if(r.error){fb.innerHTML='<span class="err">'+r.error+'</span>';return;}
    let h='<div style="border:1px solid rgba(255,255,255,.12);border-radius:8px;padding:8px">';
    if(r.hook_score!=null){const c=r.hook_score>=7?'var(--green)':(r.hook_score>=5?'#FBBF24':'var(--red)');
      h+=`<div><b>Hook:</b> <span style="color:${c}">${r.hook_score}/10</span> &nbsp; <b>Pacing:</b> ${r.pacing||'-'} &nbsp; <b>Music:</b> ${r.music_mood||'-'}</div>`;}
    if(r.title_ideas&&r.title_ideas.length){h+='<div style="margin-top:5px"><b>Title ideas:</b><ul style="margin:3px 0 0 16px;padding:0">'+r.title_ideas.map(t=>`<li style="cursor:pointer" onclick="navigator.clipboard.writeText('${(t+'').replace(/'/g,"")}')">${t}</li>`).join('')+'</ul></div>';}
    if(r.improvements&&r.improvements.length){h+='<div style="margin-top:5px"><b>Improvements:</b><ul style="margin:3px 0 0 16px;padding:0">'+r.improvements.map(t=>`<li>${t}</li>`).join('')+'</ul></div>';}
    if(r.strong_points&&r.strong_points.length){h+='<div class="analysis-strength"><b>Strong points:</b> '+r.strong_points.join(', ')+'</div>';}
    h+='</div>';
    fb.innerHTML=h;
  }catch(e){fb.innerHTML='<span class="err">Analyze fail: '+e+'</span>';}
}

async function improveScript(){
  const el=document.getElementById('script'); const script=el.value.trim();
  const fb=document.getElementById('scriptFeedback');
  if(script.length<10){fb.innerHTML='<span class="err">Pehle script likhein</span>';return;}
  fb.innerHTML=feedbackMarkup('loading','Script improve ho raha hai.');
  try{
    const r=await (await fetch('/api/improve',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({script,language:_scriptLang()})})).json();
    if(r.script&&!r.script.startsWith('[error]')){
      el.value=r.script;
      fb.innerHTML=feedbackMarkup('success','Improved script editor mein ready hai.');
    } else { fb.innerHTML='<span class="err">'+(r.script||'fail')+'</span>'; }
  }catch(e){fb.innerHTML='<span class="err">Improve fail: '+e+'</span>';}
}

// Track C — YouTube Package (metadata)
function _copy(t){ navigator.clipboard.writeText(t).catch(()=>{}); }
async function genPackage(){
  const script=document.getElementById('script').value.trim();
  const pk=document.getElementById('pkgPanel');
  if(script.length<20){ pk.innerHTML='<span class="err">Pehle script banayein.</span>'; return; }
  pk.innerHTML=feedbackMarkup('loading','YouTube titles, description, tags aur thumbnail copy ban rahi hai.');
  try{
    const m=await (await fetch('/api/metadata',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({script,language:_scriptLang()})})).json();
    if(m.error){ pk.innerHTML='<span class="err">'+m.error+'</span>'; return; }
    const box=(label,content)=>`<div style="margin-top:8px"><div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:3px">${label}</div>${content}</div>`;
    const titles=(m.titles||[]).map(t=>`<div style="display:flex;gap:6px;align-items:center;padding:3px 0"><span style="flex:1">${t}</span><button class="btn btn-sm" style="padding:1px 7px" onclick="_copy(${JSON.stringify(t).replace(/"/g,'&quot;')})">copy</button></div>`).join('');
    const tags=(m.tags||[]).map(t=>`<span style="background:var(--card2,rgba(255,255,255,.06));border-radius:12px;padding:2px 8px;font-size:11px;margin:2px;display:inline-block">${t}</span>`).join('');
    const chapters=(m.chapters||[]).length?box('Chapters',(m.chapters||[]).map(c=>`<div style="font-size:12px">${c}</div>`).join('')):'';
    pk.innerHTML='<div style="border:1px solid rgba(255,255,255,.12);border-radius:10px;padding:10px 12px;font-size:13px">'
      +'<div class="package-heading">'+uiIcon('download')+' YouTube Package</div>'
      +box('Thumbnail text','<div style="font-weight:800;font-size:18px;letter-spacing:.02em">'+(m.thumbnail_text||'')+'</div>')
      +box('Titles (5)',titles)
      +box('Description','<div style="white-space:pre-wrap">'+(m.description||'')+'</div><button class="btn btn-sm" style="margin-top:4px;padding:1px 8px" onclick="_copy('+JSON.stringify(m.description||'').replace(/"/g,'&quot;')+')">copy description</button>')
      +box('Tags',tags+'<div><button class="btn btn-sm" style="margin-top:5px;padding:1px 8px" onclick="_copy('+JSON.stringify((m.tags||[]).join(', ')).replace(/"/g,'&quot;')+')">copy all tags</button></div>')
      +box('Pinned comment',(m.pinned_comment||''))
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
  const within=total>0?Math.min(1,Math.max(0,Number(i||0)/Number(total))):0;
  const percent=fin?100:Math.max(0,Math.min(99,Math.round(((Math.max(0,ai)+within)/ORDER.length)*100)));
  const bar=document.getElementById('overallProgress'), fill=document.getElementById('overallProgressFill');
  if(bar) bar.setAttribute('aria-valuenow',String(percent));
  if(fill) fill.style.width=`${percent}%`;
  const label=document.getElementById('overallProgressLabel'); if(label) label.textContent=`${percent}% complete`;
  const titles={story:'Analyzing your story',voice:'Creating voices and lip-sync',asset:'Preparing scenes and characters',render:'Compositing the final video'};
  const stage=document.getElementById('generationStage'); if(stage) stage.textContent=fin?'Finalizing your video':(titles[active]||'Preparing your video');
  const clip=document.getElementById('generationClip'); if(clip) clip.textContent=msg||(fin?'Render complete. Preparing playback.':'Working safely in the background.');
}

function setGenerationExperience(state){
  const ready=document.getElementById('renderReadyExperience');
  const progress=document.getElementById('progressCard');
  const result=document.getElementById('resultCard');
  ready?.classList.toggle('hidden',state!=='ready');
  progress?.classList.toggle('hidden',state!=='progress');
  result?.classList.toggle('hidden',state!=='result');
}

function startGenerationClock(resetClock=true){
  if(resetClock||!GENERATION_STARTED_AT) GENERATION_STARTED_AT=Date.now();
  clearInterval(ELAPSED_TIMER);
  const tick=()=>{
    const elapsed=Math.max(0,Math.floor((Date.now()-GENERATION_STARTED_AT)/1000));
    const out=document.getElementById('generationElapsed');
    if(out) out.textContent=`${String(Math.floor(elapsed/60)).padStart(2,'0')}:${String(elapsed%60).padStart(2,'0')}`;
  };
  tick(); ELAPSED_TIMER=setInterval(tick,1000);
}

function stopGenerationClock(){ clearInterval(ELAPSED_TIMER); ELAPSED_TIMER=null; }

const EMOTIONS=['neutral','happy','sad','angry','excited','scared','confused','thinking','surprised'];
let PLAN=null;

let COSTUMES=[], ACCESSORIES=[], HELD=[];
async function preview(options={}){
  const automatic=options.automatic===true;
  const script=document.getElementById('script').value.trim();
  if(script.length<10){notifyValidation('Script likhein.','script','scriptFeedback');return;}
  if(options.sourceScript&&options.sourceScript!==script) return;
  showStudioView('create',false); if(!automatic)setCreateStep(2,false);
  const btn=document.getElementById('previewBtn');
  setButtonLoading(btn,true,'Building plan…');
  document.getElementById('errMsg').classList.add('hidden');
  document.getElementById('previewError').classList.add('hidden');
  try{
    if(!COSTUMES.length){ try{ COSTUMES=await (await fetch('/api/costumes')).json(); }catch(e){} }
    if(!ACCESSORIES.length){ try{ ACCESSORIES=await (await fetch('/api/accessories')).json(); }catch(e){} }
    if(!HELD.length){ try{ HELD=await (await fetch('/api/held')).json(); }catch(e){} }
    const j=await (await fetch('/api/preview',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({script,target_duration:selectedVideoDuration(),character_library:CAST_CHARACTER_LIBRARY})})).json();
    if(j.error){
      showPreviewError(j.error);
      if(automatic){
        const feedback=document.getElementById('scriptFeedback');
        if(feedback) feedback.innerHTML=feedbackMarkup('danger',`Automatic scene plan nahi bana: ${j.error}`);
      }
    }
    else {
      (j.characters||[]).forEach(character=>{if(character.package&&character.capability)CHAR_CAPS[String(character.package).toLowerCase()]=character.capability;});
      PLAN=j; PLAN_SOURCE_SCRIPT=script; renderPreview(j);
      const duration=j.duration_analysis||{};
      const hint=document.getElementById('scriptDurationHint');
      if(hint&&duration.estimated_seconds){
        hint.textContent=`Target: ${duration.selected_label||selectedVideoDuration()} ? current script: ${formatRenderDuration(duration.estimated_seconds)} / ${duration.word_count||0} words ? recommended: ${duration.minimum_words||'?'}?${duration.maximum_words||'?'} words. Final duration actual voice audio se frame-accurate hogi.`;
      }
      if(automatic){
        setCreateStep(2,false);
        const sceneCount=(j.scenes||[]).length;
        showStudioToast(`${sceneCount} scene${sceneCount===1?'':'s'} automatically ready · target ${duration.selected_label||selectedVideoDuration()}.`,'success','Storyboard ready');
        if(duration.estimated_seconds&&!duration.within_target_tolerance){
          showStudioToast(`Current script ${formatRenderDuration(duration.estimated_seconds)} ka hai; ${duration.selected_label} target ke liye ${duration.minimum_words}?${duration.maximum_words} spoken words recommend hain. AI generation ab isi budget ko follow karegi.`,'warning','Duration needs content');
        }
      } else if(duration.estimated_seconds&&!duration.within_target_tolerance){
        showStudioToast(`Current script ${formatRenderDuration(duration.estimated_seconds)} ka hai. ${duration.selected_label} target ke liye recommended script budget ${duration.minimum_words}?${duration.maximum_words} words hai; final video hamesha actual voice audio duration par banti hai.`,'warning','Duration needs content');
      }      if((j.performance_warnings||[]).length){
        const alternatives=(j.dialogue_cast_recommendations||[]).map(item=>item.name).filter(Boolean).slice(0,3);
        const suggestion=alternatives.length?` Jaw lip-sync alternatives: ${alternatives.join(', ')}.`:'';
        showStudioToast(`${j.performance_warnings.length} dialogue line(s) body-only cast ke liye medium/action staging par route hongi.${suggestion}`,'warning','Character performance adjusted');
      }
      if(j.motion_preflight&&!j.motion_preflight.ready){
        const fallbackCount=Number(j.motion_preflight.counts?.safe_fallback||0)+Number(j.motion_preflight.counts?.unsafe_fallback||0);
        showStudioToast(`${fallbackCount} action(s) ke liye character ka safe authored substitute automatically select ho gaya hai. Cast & Scenes mein aap chahein to review kar sakte hain.`,'info','Motion safely staged');
      }else if(Number(j.motion_preflight?.counts?.semantic_substitute||0)>0){
        const substituteCount=Number(j.motion_preflight.counts.semantic_substitute);
        showStudioToast(`${substituteCount} story action(s) nearest real authored clip se stage hongi; source clip plan mein record hai.`,'info','Motion staging mapped');
      }
      if(Number(j.auto_direction_summary?.automatic_actions||0)>0){
        showStudioToast(`${j.auto_direction_summary.automatic_actions} line action(s) script se automatically direct ho gayi hain.`,'success','Story direction ready');
      }
    }
  }catch(e){
    showPreviewError('Preview fail: '+e);
    if(automatic){
      const feedback=document.getElementById('scriptFeedback');
      if(feedback) feedback.innerHTML=feedbackMarkup('danger','Automatic scene plan temporarily fail hua. Build Cast & Scene Plan dobara press karein.');
    }
  }
  setButtonLoading(btn,false);
}

function previewDuration(scene){
  if(scene?.duration){
    const value=String(scene.duration); return /(s|sec|min)$/i.test(value)?value:`${value}s`;
  }
  const lines=scene?.lines||[];
  const words=lines.reduce((total,line)=>total+(String(line.text||'').trim().match(/\S+/g)||[]).length,0);
  return `~${Math.max(3,Math.round(words/2.2+lines.length*.5))}s`;
}

function speakerOptions(characters,current){
  const names=(characters||[]).map(character=>character.name||character.id).filter(Boolean);
  if(current&&!names.includes(current)) names.unshift(current);
  return names.map(name=>`<option value="${escHtml(name)}" ${String(name)===String(current)?'selected':''}>${escHtml(name)}</option>`).join('');
}

function renderPreview(p){
  document.getElementById('pvTitle').textContent=p.title||'Untitled video';
  const characters=p.characters||[], veggies=p.veggies||[], scenes=p.scenes||[];
  const cc=document.getElementById('pvChars'); cc.innerHTML='';
  const grpOpts=(arr)=>{
    const groups={}; (arr||[]).forEach(item=>{(groups[item.group||'Other']=groups[item.group||'Other']||[]).push(item);});
    return Object.keys(groups).map(group=>{
      const inner=groups[group].map(item=>`<option value="${escHtml(item.id)}">${escHtml(item.label)}</option>`).join('');
      return group==='—'?inner:`<optgroup label="${escHtml(group)}">${inner}</optgroup>`;
    }).join('');
  };
  const costOpts=grpOpts(COSTUMES), accOpts=grpOpts(ACCESSORIES), heldOpts=grpOpts(HELD);
  characters.forEach(character=>{
    const libraryLabels={sbz:'SBZ Originals',quaternius:'Quaternius Library'};
    const activeLibrary=(p.parsed?.character_library||CAST_CHARACTER_LIBRARY||'sbz')==='quaternius'?'quaternius':'sbz';
    const choices=veggies.filter(item=>(item.library||'sbz')===activeLibrary);
    const options=`<optgroup label="${libraryLabels[activeLibrary]}">${choices.map(item=>`<option value="${escHtml(item.name)}" ${item.package===character.package?'selected':''}>${escHtml(item.name)}${item.tier?` Â· ${escHtml(item.tier)}`:''}</option>`).join('')}</optgroup>`;
    const card=document.createElement('article'); card.className='pvRow character-card'; card.dataset.cid=character.id;
    const capability=CHAR_CAPS[String(character.package||'').toLowerCase()]||character.capability;
    const initials=String(character.name||'?').trim().slice(0,2).toUpperCase();
    card.innerHTML=`<div class="character-card-head"><div class="character-avatar"><span>${escHtml(initials)}</span><img src="${escHtml(character.avatar||'')}" class="pvAv" alt="${escHtml(character.name||'Character')} thumbnail"></div>`
      +`<div class="character-identity"><h4>${escHtml(character.name||'Character')}</h4><span class="voice-pill">${escHtml(character.voice||'Automatic voice')}</span><div class="performanceSlot">${performanceMarkup(character.performance)} ${castingDecisionMarkup(character.casting_decision)}</div><div class="capSlot">${capabilityMarkup(capability)}</div></div></div>`
      +`<div class="character-controls"><label><span>3D character</span><select class="pvVeg">${options}</select></label>`
      +`<label><span>Costume</span><select class="pvCostume">${costOpts}</select></label>`
      +`<label><span>Accessory</span><select class="pvAcc">${accOpts}</select></label>`
      +`<label><span>Held item</span><select class="pvHeld">${heldOpts}</select></label></div>`;
    cc.appendChild(card);
    const image=card.querySelector('.pvAv');
    image?.addEventListener('error',()=>card.classList.add('avatar-missing'));
    card.querySelector('.pvVeg')?.addEventListener('change',async event=>{
      const selected=veggies.find(item=>item.name===event.target.value);
      const packageName=String(selected?.package||'').toLowerCase();
      let next=selected&&CHAR_CAPS[packageName];
      if(selected&&!next){card.querySelector('.capSlot').innerHTML='<span class="capBadge">Loading capability…</span>';await load3dValidation([packageName]);next=CHAR_CAPS[packageName];}
      card.querySelector('.capSlot').innerHTML=capabilityMarkup(next);
      card.querySelector('.performanceSlot').innerHTML=performanceMarkup(selected?{
        speech_mode:selected.speech_mode,lip_sync:selected.lip_sync,facial_ready:selected.facial_ready,
        label:selected.performance_label,warning:selected.performance_warning
      }:null);
    });
  });
  if(!characters.length) cc.innerHTML='<div class="empty-state compact"><span>'+uiIcon('characters')+'</span><div><strong>No characters found</strong><p>Script mein speaker names add karke plan dobara build karein.</p></div></div>';

  const sc=document.getElementById('pvScenes'); sc.innerHTML='';
  scenes.forEach((scene,sceneIndex)=>{
    const box=document.createElement('article'); box.className='pvScene scene-card'; box.dataset.si=sceneIndex; box.dataset.duration=previewDuration(scene);
    const lines=scene.lines||[], mood=scene.mood||'neutral';
    let html=`<header class="scene-card-header"><div class="scene-order"><span>Scene</span><strong data-scene-order>${sceneIndex+1}</strong></div>`
      +`<div class="scene-title"><h4>${escHtml(scene.location||`Scene ${scene.id||sceneIndex+1}`)}</h4><div><span class="scene-badge pvMoodBadge">${escHtml(mood)}</span><span class="scene-badge">${uiIcon('clock')} ${escHtml(box.dataset.duration)}</span><span class="scene-badge">${lines.length} lines</span></div></div>`
      +`<div class="scene-reorder"><button type="button" class="icon-button scene-move" data-move-scene="-1" aria-label="Move scene up">${uiIcon('arrow-up')}</button><button type="button" class="icon-button scene-move" data-move-scene="1" aria-label="Move scene down">${uiIcon('arrow-down')}</button></div></header>`
      +`<div class="scene-settings"><label><span>Background</span><input class="pvBg" value="${escHtml(scene.background_prompt||'')}" placeholder="Describe the scene background"></label><label><span>Mood</span><input class="pvMood" value="${escHtml(mood)}" placeholder="neutral"></label></div><div class="scene-validation hidden"></div>`
      +`<div class="dialogue-heading"><span>Dialogue</span><small>${lines.length} ${lines.length===1?'line':'lines'}</small></div><div class="dialogue-list">`;
    lines.forEach((line,lineIndex)=>{
      const emotionOptions=EMOTIONS.map(emotion=>`<option ${emotion===(line.emotion||'neutral')?'selected':''}>${emotion}</option>`).join('');
      html+=`<article class="pvLine dialogue-row" data-li="${lineIndex}"><div class="line-number"><span>Line</span><strong>${lineIndex+1}</strong></div><div class="dialogue-fields">`
        +`<label><span>Speaker</span><select class="pvSpeaker">${speakerOptions(characters,line.speaker)}</select></label>`
        +`<label><span>Emotion</span><select class="pvEmo">${emotionOptions}</select></label>`
        +`<label><span>Action</span><input class="pvAction" value="${escHtml(line.action||'')}" placeholder="gesture or movement"></label>`
        +`<label class="dialogue-text-field"><span>Dialogue</span><textarea class="pvText" rows="2" placeholder="Write the spoken line">${escHtml(line.text||'')}</textarea></label>`
        +`<div class="line-validation hidden"></div></div></article>`;
    });
    html+='</div>';
    box.innerHTML=html; sc.appendChild(box);
  });
  if(!scenes.length) sc.innerHTML='<div class="empty-state compact"><span>'+uiIcon('warning')+'</span><div><strong>No scenes found</strong><p>Script format check karke plan dobara build karein.</p></div></div>';
  updateSceneOrderLabels();
  document.getElementById('castEmptyState')?.classList.add('hidden');
  document.getElementById('previewCard').classList.remove('hidden');
  populateCastInspector(p);
  validatePreviewPlan(false);
  setCurrentProject(p.title||STUDIO_UI.projectName);
  renderWorkflowSummary();
  setCreateStep(2,false);
  document.getElementById('workspace')?.scrollTo({top:0,behavior:'auto'});
}

function updateSceneOrderLabels(){
  const scenes=[...document.querySelectorAll('#pvScenes .pvScene')];
  scenes.forEach((scene,index)=>{
    const label=scene.querySelector('[data-scene-order]'); if(label) label.textContent=index+1;
    const buttons=scene.querySelectorAll('[data-move-scene]');
    if(buttons[0]) buttons[0].disabled=index===0;
    if(buttons[1]) buttons[1].disabled=index===scenes.length-1;
  });
  const lineCount=document.querySelectorAll('#pvScenes .pvLine').length;
  document.getElementById('pvSceneCount').textContent=scenes.length;
  document.getElementById('pvDialogueCount').textContent=lineCount;
  document.getElementById('pvCharacterCount').textContent=document.querySelectorAll('#pvChars .pvRow').length;
}

function moveSceneCard(button,direction){
  const scene=button.closest('.pvScene'), list=scene?.parentElement; if(!scene||!list) return;
  if(direction<0&&scene.previousElementSibling) list.insertBefore(scene,scene.previousElementSibling);
  if(direction>0&&scene.nextElementSibling) list.insertBefore(scene.nextElementSibling,scene);
  updateSceneOrderLabels(); selectPreviewScene(scene); validatePreviewPlan(false); scheduleWorkspaceAutosave();
}

function validatePreviewPlan(showErrors=true){
  const validation=document.getElementById('previewValidation'), status=document.getElementById('previewPlanStatus');
  const scenes=[...document.querySelectorAll('#pvScenes .pvScene')], errors=[];
  if(!PLAN) errors.push('Build the cast and scene plan first.');
  if(PLAN&&!scenes.length) errors.push('At least one scene is required.');
  scenes.forEach((scene,sceneIndex)=>{
    const sceneErrors=[], background=scene.querySelector('.pvBg');
    const missingBackground=!background?.value.trim();
    background?.classList.toggle('field-invalid',missingBackground);
    if(missingBackground) sceneErrors.push('Background is required');
    const lines=[...scene.querySelectorAll('.pvLine')];
    if(!lines.length) sceneErrors.push('Add at least one dialogue line');
    lines.forEach((line,lineIndex)=>{
      const speaker=line.querySelector('.pvSpeaker'), text=line.querySelector('.pvText');
      const lineErrors=[];
      speaker?.classList.toggle('field-invalid',!speaker.value.trim());
      text?.classList.toggle('field-invalid',!text.value.trim());
      if(!speaker?.value.trim()) lineErrors.push('Choose a speaker');
      if(!text?.value.trim()) lineErrors.push('Dialogue cannot be empty');
      const message=line.querySelector('.line-validation');
      message.textContent=lineErrors.join(' · '); message.classList.toggle('hidden',!lineErrors.length);
      line.classList.toggle('has-error',!!lineErrors.length);
      lineErrors.forEach(error=>errors.push(`Scene ${sceneIndex+1}, line ${lineIndex+1}: ${error}`));
    });
    const message=scene.querySelector('.scene-validation');
    message.textContent=sceneErrors.join(' · '); message.classList.toggle('hidden',!sceneErrors.length);
    scene.classList.toggle('has-error',!!sceneErrors.length);
    sceneErrors.forEach(error=>errors.push(`Scene ${sceneIndex+1}: ${error}`));
  });
  updateSceneOrderLabels();
  const valid=!errors.length;
  status.className=`status-pill ${valid?'success':'warning'}`;
  status.textContent=valid?'Plan ready':errors.length===1?'1 item needs attention':`${errors.length} items need attention`;
  validation.classList.toggle('hidden',valid);
  validation.innerHTML=valid?'':`<span>${uiIcon('warning')}</span><div><strong>${errors.length} ${errors.length===1?'item':'items'} need attention</strong><p>${escHtml(errors.slice(0,3).join(' · '))}${errors.length>3?' · …':''}</p></div>`;
  const continueButton=document.getElementById('castContinueBtn'), generateButton=document.getElementById('pvGenBtn');
  if(continueButton) continueButton.disabled=!valid;
  if(generateButton) generateButton.disabled=!valid;
  if(showErrors&&!valid){
    const first=document.querySelector('#pvScenes .field-invalid');
    first?.scrollIntoView({behavior:'smooth',block:'center'}); first?.focus();
  }
  return valid;
}

function continueFromCast(){ if(validatePreviewPlan(true)) setCreateStep(3); }

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
  // Scenes follow the visible card order and preserve the original parsed objects.
  const reorderedScenes=[];
  document.querySelectorAll('#pvScenes .pvScene').forEach(box=>{
    const s=p.scenes[+box.dataset.si];
    if(!s) return;
    s.background_prompt=box.querySelector('.pvBg').value;
    s.mood=box.querySelector('.pvMood')?.value||s.mood;
    box.querySelectorAll('.pvLine').forEach(le=>{
      const ln=s.lines[+le.dataset.li];
      if(!ln) return;
      ln.speaker=le.querySelector('.pvSpeaker').value;
      ln.emotion=le.querySelector('.pvEmo').value;
      ln.action=le.querySelector('.pvAction').value;
      ln.text=le.querySelector('.pvText').value;
    });
    reorderedScenes.push(s);
  });
  p.scenes=reorderedScenes;
  return p;
}

async function confirmGenerate(){
  if(!PLAN){ setCreateStep(2); return; }
  if(!validatePreviewPlan(true)) return;
  startJob(collectEditedParsed());
}

async function generatePreferred(){
  if(PLAN){
    if(!validatePreviewPlan(true)) return;
    return startJob(collectEditedParsed());
  }
  return startJob(null);
}

function showPreviewError(message){
  const error=document.getElementById('previewError');
  error.textContent=message; error.classList.remove('hidden');
}

async function generate(){ startJob(null); }

async function checkResumable(){
  try{
    const list=await (await fetch('/api/resumable')).json();
    const card=document.getElementById('resumeCard'), el=document.getElementById('resumeList');
    const notice=document.getElementById('resumeNotice'), count=document.getElementById('resumeNoticeCount');
    if(count) count.textContent=list.length;
    const dashboardUnfinished=document.getElementById('dashboardUnfinishedCount'); if(dashboardUnfinished) dashboardUnfinished.textContent=list.length;
    if(notice) notice.classList.toggle('hidden',!list.length);
    if(!list.length){ card.classList.add('hidden'); return; }
    el.innerHTML=list.map(p=>`<article class="resume-project-row"><span class="resume-project-icon">${uiIcon('projects')}</span><div><strong>${escHtml(p.title||p.name)}</strong><span>${escHtml(p.stage||'Paused')} · ${Number(p.done_clips||0)} cached clips · ${escHtml(p.updated||'Recently updated')}</span></div><button type="button" class="btn btn-secondary btn-sm" data-project-name="${escHtml(p.name)}" onclick="resumeProject(this.dataset.projectName)">Resume</button><button type="button" class="icon-button resume-delete" data-project-name="${escHtml(p.name)}" data-project-title="${escHtml(p.title||p.name)}" onclick="dropProject(this.dataset.projectName,this)" aria-label="Delete unfinished project">${uiIcon('trash')}</button></article>`).join('');
    card.classList.remove('hidden');
  }catch(e){}
}
let PROJECTS_SHOWN=true;

function formatProjectDuration(seconds){
  const value=Math.max(0,Math.round(Number(seconds)||0));
  if(!value) return 'Duration pending';
  return value>=60?`${Math.floor(value/60)}m ${String(value%60).padStart(2,'0')}s`:`${value}s`;
}

function formatProjectDate(project){
  if(project.created) return project.created;
  if(project.updated) return project.updated;
  return new Date(Number(project.mtime||0)*1000).toLocaleString();
}

function projectCardMarkup(project){
  const complete=!!project.has_video;
  const status=complete?'Complete':project.state==='error'?'Needs attention':'In progress';
  const statusClass=complete?'success':project.state==='error'?'danger':'warning';
  const name=escHtml(project.name), title=escHtml(project.title||project.name);
  const primaryAction=complete?'play':'resume', primaryLabel=complete?'Open video':'Resume project';
  return `<article class="project-card"><div class="project-thumbnail ${complete?'complete':''}"><span>${uiIcon(complete?'play':'projects')}</span><small>${complete?'MP4 ready':'Work in progress'}</small></div><div class="project-card-body"><div class="project-card-title"><div><span class="status-pill ${statusClass}">${status}</span><h3>${title}</h3></div><div class="project-overflow"><button type="button" class="icon-button project-menu-button" aria-label="Project actions" aria-expanded="false" onclick="toggleProjectMenu(this,event)">•••</button><div class="project-menu hidden" data-project-menu><button type="button" data-action="open" data-project-name="${name}" onclick="handleProjectAction(this,event)">${uiIcon('folder')} Load project</button>${complete?`<button type="button" data-action="play" data-project-name="${name}" onclick="handleProjectAction(this,event)">${uiIcon('play')} Preview video</button>`:`<button type="button" data-action="resume" data-project-name="${name}" onclick="handleProjectAction(this,event)">${uiIcon('render')} Resume render</button>`}<button type="button" class="danger" data-action="delete" data-project-name="${name}" data-project-title="${title}" onclick="handleProjectAction(this,event)">${uiIcon('trash')} Delete</button></div></div></div><div class="project-card-meta"><span>${Number(project.scenes||0)} scenes</span><span>${Number(project.characters||0)} characters</span><span>${formatProjectDuration(project.duration)}</span></div><div class="project-modified">Modified ${escHtml(formatProjectDate(project))}</div><button type="button" class="btn ${complete?'btn-primary':'btn-secondary'} project-open-button" data-action="${primaryAction}" data-project-name="${name}" onclick="handleProjectAction(this,event)">${primaryLabel}</button></div></article>`;
}

function recentProjectMarkup(project){
  const complete=!!project.has_video, name=escHtml(project.name);
  return `<article class="recent-project-card"><span class="recent-project-thumb">${uiIcon(complete?'play':'projects')}</span><div><strong>${escHtml(project.title||project.name)}</strong><span>${complete?'Complete':'In progress'} · ${formatProjectDuration(project.duration)}</span></div><button type="button" class="text-button" data-action="${complete?'play':'resume'}" data-project-name="${name}" onclick="handleProjectAction(this,event)">${complete?'Open':'Resume'} →</button></article>`;
}

async function loadProjectsList(){
  const el=document.getElementById('projList');
  const recent=document.getElementById('dashboardRecentProjects');
  if(el&&!el.children.length) el.innerHTML=Array.from({length:3},()=>'<div class="project-skeleton" aria-hidden="true"><span></span><i></i><i></i><b></b></div>').join('');
  if(recent&&!recent.children.length) recent.innerHTML=Array.from({length:2},()=>'<div class="recent-skeleton" aria-hidden="true"><span></span><i></i></div>').join('');
  try{
    const list=await (await fetch('/api/projects')).json();
    document.getElementById('projCount').textContent='('+list.length+')';
    const dashboardCount=document.getElementById('dashboardProjectCount'); if(dashboardCount) dashboardCount.textContent=list.length;
    const completed=list.filter(project=>project.has_video).length;
    const completedCount=document.getElementById('dashboardCompletedCount'); if(completedCount) completedCount.textContent=completed;
    const sceneCount=document.getElementById('dashboardSceneCount'); if(sceneCount) sceneCount.textContent=list.reduce((total,project)=>total+Number(project.scenes||0),0);
    if(!list.length){
      el.innerHTML='<div class="empty-state large project-empty"><span>'+uiIcon('projects')+'</span><div><h2>No projects yet</h2><p>Create your first video to start the local library.</p><button type="button" class="btn btn-primary" onclick="showStudioView(\'create\')">Create New Video</button></div></div>';
      if(recent) recent.innerHTML='<div class="empty-state compact"><span>'+uiIcon('projects')+'</span><div><strong>No recent work</strong><p>Your first project will appear here.</p></div></div>';
      return;
    }
    el.innerHTML=list.map(projectCardMarkup).join('');
    if(recent) recent.innerHTML=list.slice(0,4).map(recentProjectMarkup).join('');
  }catch(e){
    if(el) el.innerHTML='<div class="empty-state compact project-empty"><span>'+uiIcon('warning')+'</span><div><strong>Projects unavailable</strong><p>Local project list load nahi hui. Dobara view open karke retry karein.</p></div></div>';
    if(recent) recent.innerHTML='<div class="empty-state compact"><span>'+uiIcon('warning')+'</span><div><strong>Recent work unavailable</strong><p>Projects view se retry karein.</p></div></div>';
  }
}
function toggleProjects(){
  const el=document.getElementById('projList');
  PROJECTS_SHOWN=!PROJECTS_SHOWN;
  el.classList.toggle('hidden',!PROJECTS_SHOWN);
  const button=document.getElementById('projectListToggle'); if(button) button.textContent=PROJECTS_SHOWN?'Collapse list':'Show projects';
  if(PROJECTS_SHOWN) loadProjectsList();
}

function closeProjectMenus(){
  document.querySelectorAll('[data-project-menu]').forEach(menu=>menu.classList.add('hidden'));
  document.querySelectorAll('.project-menu-button').forEach(button=>button.setAttribute('aria-expanded','false'));
}

function toggleProjectMenu(button,event){
  event?.stopPropagation(); const menu=button.parentElement.querySelector('[data-project-menu]');
  const open=menu.classList.contains('hidden'); closeProjectMenus();
  menu.classList.toggle('hidden',!open); button.setAttribute('aria-expanded',String(open));
}

function handleProjectAction(button,event){
  event?.stopPropagation(); const name=button.dataset.projectName, action=button.dataset.action; closeProjectMenus();
  if(action==='open') return openProject(name);
  if(action==='play') return playProject(name);
  if(action==='resume') return resumeProject(name);
  if(action==='delete') return requestProjectDelete(name,button.dataset.projectTitle||name);
}
async function openProject(name){
  const p=await (await fetch('/api/project/'+encodeURIComponent(name))).json();
  if(p.error){ showStudioToast(p.error,'danger','Project could not be opened'); return; }
  showStudioView('create',false); setCreateStep(1,false); setCurrentProject(p.title||name);
  document.getElementById('script').value=p.script||'';
  PLAN = p.parsed ? {parsed:p.parsed} : null;   // preview/generate isi plan par
  if(p.settings){
    if(p.settings.subtitles_on!==undefined) document.getElementById('cap_enabled').checked=!!p.settings.subtitles_on;
    else if(p.settings.captions) document.getElementById('cap_enabled').checked=!!p.settings.captions.enabled;
    if(p.settings.intro_on!==undefined) document.getElementById('intro_on').checked=!!p.settings.intro_on;
  }
  updateScriptCount(); renderWorkflowSummary(); scheduleWorkspaceAutosave();
  document.getElementById('script').scrollIntoView({behavior:'smooth',block:'center'});
  const fb=document.getElementById('scriptFeedback');
  if(fb) fb.innerHTML=feedbackMarkup('success',`“${p.title||name}” load ho gaya. Script edit karke Preview ya Generate karein${p.has_video?', ya completed video open karein.':'.'}`);
  if(p.has_video) playProject(name);
}
function playProject(name){
  showStudioView('create',false); setCreateStep(4,false); setCurrentProject(name);
  CURRENT_RESULT_PROJECT=name; setGenerationExperience('result');
  document.getElementById('rTitle').textContent=name;
  document.getElementById('rVideo').src='/projects/'+name+'/final.mp4?t='+Date.now();
  document.getElementById('rDownload').href='/projects/'+name+'/final.mp4';
  document.getElementById('resultCard').scrollIntoView({behavior:'smooth',block:'center'});
}
async function delProject(name,ev){
  if(ev) ev.stopPropagation();
  requestProjectDelete(name,name);
}
async function resumeProject(name){
  showStudioView('create',false); setCreateStep(4,false); setCurrentProject(name);
  const btn=document.getElementById('genBtn'); if(btn) btn.disabled=true;
  setGenerationExperience('progress'); startGenerationClock();
  document.getElementById('resumeCard').classList.add('hidden');
  setStages('story',0,1,'Resume ho raha...');
  let response, r;
  try{
    response=await fetch('/api/resume/'+name,{method:'POST'});
    r=await response.json();
  }catch(e){ r={error:String(e)}; }
  if(!response||!response.ok||r.error){
    if(btn) btn.disabled=false;
    setGenerationExperience('idle'); stopGenerationClock&&stopGenerationClock();
    // A busy/conflict must not hide the resume list — surface it and step back.
    notifyValidation(r.error||'Resume start nahi hua.','','scriptFeedback');
    checkResumable&&checkResumable();
    return;
  }
  CUR_JOB=r.job_id; _resetStop();
  beginJobPolling(r.job_id);
}
async function dropProject(name,elBtn){
  requestProjectDelete(name,elBtn?.dataset.projectTitle||name);
}

function requestProjectDelete(name,title){
  const dialog=document.getElementById('deleteProjectDialog');
  DELETE_PENDING={type:'project',name,title,returnFocus:document.activeElement};
  document.getElementById('deleteDialogEyebrow').textContent='Delete project';
  document.getElementById('deleteProjectDialogTitle').textContent=`Delete “${title}”?`;
  document.getElementById('deleteProjectDialogMessage').textContent='Video, cached clips aur project data permanently remove ho jayega.';
  document.getElementById('confirmProjectDeleteButton').textContent='Delete project';
  dialog.classList.remove('hidden'); dialog.setAttribute('aria-hidden','false');
  document.getElementById('cancelDeleteButton')?.focus();
}

function requestCharacterDelete(id,name){
  const dialog=document.getElementById('deleteProjectDialog');
  DELETE_PENDING={type:'character',id,name,returnFocus:document.activeElement};
  document.getElementById('deleteDialogEyebrow').textContent='Delete character';
  document.getElementById('deleteProjectDialogTitle').textContent=`Delete “${name}”?`;
  document.getElementById('deleteProjectDialogMessage').textContent='Saved character library se remove ho jayega. Existing rendered projects safe rahenge.';
  document.getElementById('confirmProjectDeleteButton').textContent='Delete character';
  dialog.classList.remove('hidden'); dialog.setAttribute('aria-hidden','false');
  document.getElementById('cancelDeleteButton')?.focus();
}

function closeDeleteProjectDialog(){
  const dialog=document.getElementById('deleteProjectDialog'); if(!dialog||dialog.classList.contains('hidden')) return;
  dialog.classList.add('hidden'); dialog.setAttribute('aria-hidden','true');
  const focus=DELETE_PENDING?.returnFocus; DELETE_PENDING=null;
  if(focus&&typeof focus.focus==='function') focus.focus();
}

async function confirmProjectDelete(){
  if(!DELETE_PENDING) return;
  const pending=DELETE_PENDING, button=document.getElementById('confirmProjectDeleteButton');
  setButtonLoading(button,true,'Deleting…');
  try{
    const url=pending.type==='character'?'/api/characters-lib/'+encodeURIComponent(pending.id):'/api/projects/'+encodeURIComponent(pending.name);
    const response=await fetch(url,{method:'DELETE'});
    const result=await response.json(); if(!response.ok||result.error) throw new Error(result.error||'Item delete nahi hua');
    closeDeleteProjectDialog();
    if(pending.type==='character') await loadLib();
    else await Promise.all([loadProjectsList(),checkResumable()]);
    showStudioToast(pending.type==='character'?'Character delete ho gaya.':'Project delete ho gaya.','success','Deleted');
  }catch(error){document.getElementById('deleteProjectDialogMessage').textContent=error.message;}
  setButtonLoading(button,false);
}
async function startJob(parsed){
  const script=document.getElementById('script').value.trim();
  if(!parsed && script.length<10){notifyValidation('Script likhein.','script','scriptFeedback');return;}
  showStudioView('create',false); setCreateStep(4,false);
  const btn=document.getElementById('genBtn');
  setButtonLoading(btn,true,'Starting render…');
  setButtonLoading(document.getElementById('pvGenBtn'),true,'Starting render…');
  setGenerationExperience('progress'); startGenerationClock();
  document.getElementById('errMsg').classList.add('hidden');
  setStages('story',0,1,'');
  const body={script,settings:collectSettings()};
  if(parsed) body.parsed=parsed;
  let response, r;
  try{
    response=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body)});
    r=await response.json();
  }catch(e){ r={error:String(e)}; }
  // Busy / error: never leave the UI stuck in the render view — go back to the
  // script step, reset the buttons, and show a clear message.
  if(!response||!response.ok||r.error){
    setButtonLoading(btn,false); setButtonLoading(document.getElementById('pvGenBtn'),false);
    setGenerationExperience('idle'); stopGenerationClock&&stopGenerationClock();
    setCreateStep(1,false);
    notifyValidation(r.error||'Generation start nahi hua.','script','scriptFeedback');
    return;
  }
  setCurrentProject(r.project||STUDIO_UI.projectName);
  CUR_JOB=r.job_id; _resetStop();
  beginJobPolling(r.job_id);
}
function _resetStop(){ const b=document.getElementById('stopBtn'); if(b){b.disabled=false;b.textContent='Stop Generation';} }

function beginJobPolling(id){
  clearInterval(polling); clearTimeout(POLL_RETRY_TIMER);
  POLL_FAILURES=0; POLL_IN_FLIGHT=false; LAST_JOB_STATUS=null;
  polling=setInterval(()=>poll(id),1500);
  poll(id);
}
function stopJobPolling(){
  clearInterval(polling); polling=null;
  clearTimeout(POLL_RETRY_TIMER); POLL_RETRY_TIMER=null;
}
function schedulePollRetry(id){
  clearTimeout(POLL_RETRY_TIMER);
  const delay=Math.min(10000,1500*Math.max(1,POLL_FAILURES));
  POLL_RETRY_TIMER=setTimeout(()=>poll(id),delay);
}
async function poll(id){
  // Do not overlap status requests. Slow local rendering can otherwise create a
  // queue of old polls and make a healthy job look disconnected in the UI.
  if(POLL_IN_FLIGHT) return;
  POLL_IN_FLIGHT=true;
  try{
    const response=await fetch('/api/status/'+id,{cache:'no-store'});
    const j=await response.json();
    // A failed job legitimately contains an error message. Handle that state
    // below instead of treating it like a lost network connection forever.
    if(!response.ok||(!j.state&&j.error)) throw new Error(j.error||`Status request failed (${response.status})`);
    POLL_FAILURES=0;
    LAST_JOB_STATUS=j;
    if(j.state==='running'){
      let message=j.message||'Working safely in the background.';
      const heartbeat=Number(j.heartbeat_at||j.updated_at||0);
      const progressAt=Number(j.progress_updated_at||j.updated_at||0);
      if(heartbeat&&Date.now()/1000-heartbeat>20) message='Backend heartbeat slow hai; reconnecting without losing cached work...';
      else if(progressAt&&Date.now()/1000-progressAt>50){
        message=j.stage==='render'
          ? `${message} Current 3D clip local frames render kar raha hai; completed clips cached hain.`
          : `${message} Provider response ka wait ho raha hai; timeout/fallback automatic hai.`;
      }
      setStages(j.stage,j.i,j.total,message);
    }
    else if(j.state==='done'){stopJobPolling();stopGenerationClock();setStages('render',1,1,'',true);showResult(j.result);checkResumable();loadProjectsList();}
    else if(j.state==='stopped'||j.state==='interrupted'){
      stopJobPolling();stopGenerationClock();reset();setGenerationExperience('ready');
      const fb=document.getElementById('scriptFeedback'); if(fb)fb.innerHTML=feedbackMarkup('warning',j.message||'Generation interrupted. Completed work safe hai aur Projects se resume ho sakta hai.');
      checkResumable();loadProjectsList();
    }
    else if(j.state==='error'){stopJobPolling();showErr(j.error||j.message||'Generation failed');checkResumable();}
  }catch(error){
    POLL_FAILURES+=1;
    // A poll failure is not proof that the render worker stopped. Keep polling
    // and preserve the progress screen; the backend owns the real job state.
    const notice=POLL_FAILURES>=6
      ? 'Status check delayed hai; automatic reconnect chal raha hai. Completed work safe/cached hai.'
      : `Status reconnect ho raha hai (${POLL_FAILURES})...`;
    const last=LAST_JOB_STATUS||{};
    setStages(last.stage||'story',last.i||0,last.total||1,notice);
    schedulePollRetry(id);
  }finally{
    POLL_IN_FLIGHT=false;
  }
}
function showResult(res){
  showStudioView('create',false); setCreateStep(4,false);
  setGenerationExperience('result');
  document.getElementById('rTitle').textContent=res.title||'Video Ready';
  setCurrentProject(res.title||STUDIO_UI.projectName);
  CURRENT_RESULT_PROJECT=String(res.video_rel||'').split('/')[0]||STUDIO_UI.projectName;
  document.getElementById('rVideo').src='/projects/'+res.video_rel+'?t='+Date.now();
  document.getElementById('rDownload').href='/projects/'+res.video_rel;
  reset();
}
function showErr(m){stopJobPolling();stopGenerationClock();const e=document.getElementById('errMsg');e.textContent=m;e.classList.remove('hidden');reset();}
function reset(){
  const b=document.getElementById('genBtn');setButtonLoading(b,false);b.textContent='Generate directly from script';
  const pb=document.getElementById('previewBtn');setButtonLoading(pb,false);pb.textContent='Build Cast & Scene Plan';
  const pg=document.getElementById('pvGenBtn');if(pg){setButtonLoading(pg,false);pg.disabled=(document.getElementById('script')?.value.trim().length||0)<10;}
}

async function openProjectFolder(){
  const name=CURRENT_RESULT_PROJECT||STUDIO_UI.projectName; if(!name) return;
  const button=document.getElementById('openProjectFolderBtn'); button.disabled=true;
  try{
    const response=await fetch('/api/project/'+encodeURIComponent(name)+'/open-folder',{method:'POST'});
    const result=await response.json();
    if(!response.ok||result.error) throw new Error(result.error||'Folder could not be opened');
    showGenerationToast('Project folder Windows Explorer mein open ho gaya.',false);
  }catch(error){showGenerationToast(error.message,false);}
  button.disabled=false;
}

function toggleExportOptions(force){
  const panel=document.getElementById('exportOptionsPanel'), button=document.getElementById('exportOptionsButton');
  const open=typeof force==='boolean'?force:panel.classList.contains('hidden');
  panel.classList.toggle('hidden',!open); button.setAttribute('aria-expanded',String(open));
}

async function exportProject(){
  const name=CURRENT_RESULT_PROJECT||STUDIO_UI.projectName;
  const want=[];
  if(document.getElementById('exportSrt').checked) want.push('srt');
  if(document.getElementById('exportAudio').checked) want.push('audio');
  if(document.getElementById('exportThumbnail').checked) want.push('thumbnail');
  if(document.getElementById('exportSeo').checked) want.push('seo');
  const button=document.getElementById('exportBtn'), out=document.getElementById('exportResult');
  button.disabled=true; out.textContent='Creating export package…';
  try{
    const response=await fetch('/api/export/'+encodeURIComponent(name),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({want})});
    const result=await response.json(); if(!response.ok||result.error) throw new Error(result.error||'Export failed');
    const files=Object.entries(result).filter(([,value])=>value).map(([key,value])=>key==='seo'?'<span>SEO package ready</span>':`<a href="/projects/${escHtml(value)}" download>${escHtml(key.toUpperCase())}</a>`).join('');
    out.innerHTML=files?`<div class="export-result-links">${files}</div>`:'Export completed.';
  }catch(error){out.innerHTML=`<span class="err">${escHtml(error.message)}</span>`;}
  button.disabled=false;
}

function createAnotherVideo(){
  stopGenerationClock(); CURRENT_RESULT_PROJECT=''; PLAN=null;
  const script=document.getElementById('script'); if(script) script.value='';
  document.getElementById('rVideo')?.removeAttribute('src');
  document.getElementById('previewCard')?.classList.add('hidden');
  document.getElementById('castEmptyState')?.classList.remove('hidden');
  setCurrentProject('Untitled video'); setGenerationExperience('ready');
  toggleExportOptions(false); updateScriptCount(); renderWorkflowSummary();
  setCreateStep(1); document.getElementById('script')?.focus();
}

async function testRunware(){
  const btn=document.getElementById('testBtn'), out=document.getElementById('testResult');
  btn.disabled=true; btn.textContent='Testing providers…';
  out.innerHTML='<span style="color:var(--muted)">Runware ko test kiya ja raha hai...</span>';
  try{
    const img=document.getElementById('test_img').checked;
    const model=document.getElementById('llm_model')?.value||'';
    const j=await (await fetch('/api/test-runware',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({image:img,model})})).json();
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
    h+=`<div class="provider-test-summary ${j.ok?'success':'danger'}">${uiIcon(j.ok?'check':'warning')}<span>${j.ok?'Providers are working':'Provider issue found — review the details above'}</span></div>`;
    out.innerHTML=h;
  }catch(e){ out.innerHTML='<div class="err">Test fail: '+e+'</div>'; }
  btn.disabled=false; btn.textContent='🔎 Test API';
}

loadLib();
load();

// ---------------- Phase 6 — Retention review panel ----------------
// Surfaces the deterministic critic's findings and the scored hook alternatives
// next to the editable script, so the human edit gate is informed rather than blind.
let LAST_HOOK_RANKING=[];

function renderRetentionPanel(data){
  const panel=document.getElementById('retentionPanel');
  if(!panel) return;
  const report=(data&&data.retentionReport)||null;
  const ranking=(data&&data.hookRanking)||[];
  LAST_HOOK_RANKING=ranking;
  if(!report&&!ranking.length){ panel.classList.add('hidden'); panel.innerHTML=''; return; }

  const counts=(report&&report.riskCounts)||{high:0,med:0,low:0};
  const notes=(report&&report.notes)||[];
  const clean=notes.length===0&&!counts.high&&!counts.med;
  const chips=[
    clean?'<span class="rt-chip ok">No retention issues found</span>':'',
    counts.high?`<span class="rt-chip bad">${counts.high} high risk</span>`:'',
    counts.med?`<span class="rt-chip warn">${counts.med} to tighten</span>`:'',
    (report&&report.lineCount)?`<span class="rt-chip ok">${report.lineCount} lines</span>`:'',
  ].filter(Boolean).join('');

  let html=`<div class="retention-head"><h4>Retention review</h4>
    <div class="retention-score">${chips}</div></div>`;
  if(notes.length){
    html+='<ul class="retention-notes">'+notes.map(n=>
      `<li>${escHtml(n.note||n.flag||'')}</li>`).join('')+'</ul>';
  }
  if(ranking.length>1){
    html+='<div class="retention-sub">Hook alternatives — click to use</div><div class="hook-list">';
    html+=ranking.slice(0,8).map((h,i)=>
      `<button type="button" class="hook-option${i===0?' is-current':''}" data-hook-index="${i}">
        <span class="hk-score">${Math.round((h.total||0)*100)}</span>
        <span class="hk-angle">${escHtml(h.angle||'')}</span>
        <span class="hk-text">${escHtml(h.text||'')}</span>
      </button>`).join('');
    html+='</div>';
  }
  html+='<p class="retention-notes" style="padding-left:0;margin-top:10px;opacity:.75">'
      +'Structure checks only — real retention is confirmed from YouTube Analytics after upload.</p>';
  panel.innerHTML=html;
  panel.classList.remove('hidden');
  panel.querySelectorAll('[data-hook-index]').forEach(btn=>{
    btn.addEventListener('click',()=>applyHookChoice(parseInt(btn.dataset.hookIndex,10)));
  });
}

/** Swap the opening hook into line 1 of the script editor (keeps the line format). */
function applyHookChoice(index){
  const hook=LAST_HOOK_RANKING[index];
  const editor=document.getElementById('script');
  if(!hook||!editor) return;
  const lines=editor.value.split('\n');
  const target=lines.findIndex(l=>/^\s*[^:\[\n]+:/.test(l)&&!/^\s*\[/.test(l));
  if(target<0) return;
  // Preserve "Name: (emotion; action; location) " and replace only the spoken text.
  lines[target]=lines[target].replace(/^(\s*[^:\n]+:\s*(?:\([^)]*\)\s*)?)(.*)$/,
    (m,prefix)=>prefix+hook.text);
  editor.value=lines.join('\n');
  document.querySelectorAll('#retentionPanel [data-hook-index]').forEach(b=>
    b.classList.toggle('is-current',parseInt(b.dataset.hookIndex,10)===index));
  showStudioToast('Hook updated in the script editor.','success','Hook applied',false);
}
