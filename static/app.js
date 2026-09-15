const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const esc = s => String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let catalog, preset='reference', style='neon', mode='upload', selectedFile=null, current=null, pollTimer, currentJob;
async function api(path, options={}) {
  const r = await fetch(path, options);
  const data = await r.json();
  if (!r.ok) throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail||data));
  return data;
}
function error(message) { const el=$('#global-error'); el.textContent=message; el.classList.toggle('hidden',!message); }
function toast(message) { $('#toast').textContent=message; $('#toast').classList.remove('hidden'); setTimeout(()=>$('#toast').classList.add('hidden'),4000); }
function settings() {
  return {preset,style,aspect:$('#aspect').value,framing:$('#framing').value,caption_size:catalog.styles[style].size,caption_y:.53,...creationFinish(),...Object.fromEntries(['tracking','captions','motion','sfx','enhance'].map(k=>[k,$('#'+k).checked])), model:$('#model').value,length:+$('#length').value,count:+$('#count').value};
}
function drawCatalog() {
  $('#presets').innerHTML=Object.entries(catalog.presets).map(([id,p])=>`<button class="preset ${id===preset?'active':''}" data-preset="${id}" aria-pressed="${id===preset}"><span class="preset-icon">${p.icon}</span><b>${p.name}</b><small>${p.description}</small></button>`).join('');
  $('#styles').innerHTML=Object.entries(catalog.styles).map(([id,s])=>`<button class="style ${id===style?'active':''}" data-style="${id}" aria-pressed="${id===style}" title="${s.description}"><span class="caption-sample" style="--accent:${s.color}"><b>${captionSwatch(id)}</b></span><span>${s.name}</span></button>`).join('');
  $$('.preset').forEach(b=>b.onclick=()=>{preset=b.dataset.preset;style=catalog.presets[preset].style;drawCatalog();});
  $$('.style').forEach(b=>b.onclick=()=>{style=b.dataset.style;drawCatalog();});
}
function setMode(next) {
  mode=next;
  for(const m of ['upload','youtube']) { $('#'+m+'-panel').classList.toggle('hidden',m!==mode); $('#'+m+'-tab').classList.toggle('active',m===mode); $('#'+m+'-tab').setAttribute('aria-selected',m===mode); }
}
function chooseFile(file) { if(!file)return; selectedFile=file; $('#file-name').textContent=file.name; $('#file-detail').textContent=`${(file.size/1024/1024).toFixed(1)} MB · click to change`; }
$('#upload-tab').onclick=()=>setMode('upload'); $('#youtube-tab').onclick=()=>setMode('youtube');
$('#file').onchange=e=>chooseFile(e.target.files[0]);
$('#dropzone').ondragover=e=>{e.preventDefault();$('#dropzone').classList.add('drag');};
$('#dropzone').ondragleave=()=>$('#dropzone').classList.remove('drag');
$('#dropzone').ondrop=e=>{e.preventDefault();$('#dropzone').classList.remove('drag');chooseFile(e.dataTransfer.files[0]);};
$('#motion').onchange=()=>{ $('#sfx').disabled=!$('#motion').checked; };
function showCreate() { clearTimeout(pollTimer);current=null;history.replaceState(null,'',location.pathname);$('#create-view').classList.remove('hidden');$('#project-view').classList.add('hidden');error('');refreshProjects(); }
$('#new-project').onclick=showCreate; $('#back').onclick=showCreate;
$('#generate').onclick=async()=>{
  error('');
  if(mode==='upload'&&!selectedFile)return error('Choose a video to get started.');
  if(mode==='youtube'&&!$('#url').value.trim())return error('Paste a YouTube video link to get started.');
  if(mode==='upload'&&selectedFile.size>2*1024**3)return error('Choose a video smaller than 2 GB.');
  const body=new FormData();body.append('settings',JSON.stringify(settings()));
  if(mode==='upload')body.append('file',selectedFile);else body.append('url',$('#url').value.trim());
  const b=$('#generate');b.disabled=true;b.textContent='Adding your video…';
  try{const job=await api('/api/jobs',{method:'POST',body});openProject(job.id);}
  catch(e){error(e.message);}finally{b.disabled=false;b.innerHTML='Generate clips <span>↗</span>';}
};
async function refreshProjects(){
  try{const jobs=await api('/api/jobs');$('#projects').innerHTML=jobs.length?jobs.map(j=>`<button class="project-link ${j.id===current?'active':''}" data-job="${j.id}" title="${esc(j.name)}">${j.status==='processing'||j.status==='queued'?'◌':'▤'} &nbsp; ${esc(j.name)}</button>`).join(''):'<p class="muted">Your projects will live here.</p>';
  $$('.project-link').forEach(b=>b.onclick=()=>openProject(b.dataset.job));}catch(e){error(e.message);}
}
function openProject(id){clearTimeout(pollTimer);current=id;history.replaceState(null,'','#'+id);$('#create-view').classList.add('hidden');$('#project-view').classList.remove('hidden');$('#clips').innerHTML='';error('');refreshProjects();poll();}
function formatTime(t){return `${Math.floor(t/60)}:${String(Math.floor(t%60)).padStart(2,'0')}`;}
function options(items,selected){return Object.entries(items).map(([k,v])=>`<option value="${k}" ${k===selected?'selected':''}>${v.name}</option>`).join('');}
function clipCard(c,job){
  const el=document.createElement('article');el.className='clip';el.dataset.id=c.id;
  const media=c.preview||c.export;
  const wordData=c.words||job.words;
  const words=wordData.filter(w=>w.end>c.start&&w.start<c.end).map(w=>w.word).join(' ');
  const busy=c.status==='rendering'||c.status==='queued';
  el.innerHTML=`<div class="video-wrap" style="aspect-ratio:${c.width&&c.height?c.width/c.height:9/16}">${media?`<video controls playsinline preload="metadata" src="${esc(media)}"></video>`:`<div class="video-placeholder">${busy?'<span class="spinner"></span>':'◌'}<span>${busy?'Making your clip…':'Preview unavailable'}</span></div>`}</div>
  <div class="clip-meta"><span>CLIP ${c.id} · ${formatTime(c.start)}–${formatTime(c.end)}</span><span class="score">${c.score} / 100</span></div><h3>${esc(c.title)}</h3><div class="reasons">${esc(c.reasons.join(' · '))}<br>${esc(c.framing||'9:16 vertical')} ${c.preview?(c.render_version>=2?'· 720p HD preview':'· old 360p render'):''}</div>
  ${c.error?`<div class="alert error">${esc(c.error)}</div>`:''}
  ${busy?'<p class="helper">Rendering in the local queue…</p>':''}
  ${!busy?`<button class="secondary upgrade">✦ Apply neon + fill screen</button>`:''}
  <details><summary>Framing, captions & quality</summary><div class="field-row"><label>Start (seconds)<input class="start" type="number" min="0" step="0.1" value="${c.start}"></label><label>End (seconds)<input class="end" type="number" min="0" max="${job.meta.duration}" step="0.1" value="${c.end}"></label></div>
  <div class="field-row"><label>Preset<select class="clip-preset">${options(catalog.presets,c.settings.preset)}</select></label><label>Caption style<select class="clip-style">${options(catalog.styles,c.settings.style)}</select></label></div>
  <div class="field-row"><label>Layout<select class="clip-aspect">${options({'3:4':{name:'3:4 · reference'},'9:16':{name:'9:16 · full height'}},c.settings.aspect||'3:4')}</select></label><label>Framing<select class="clip-framing">${options({auto:{name:'Fill · automatic crop'},safe:{name:'Safe auto · may letterbox'},fit:{name:'Fit · wide video inside frame'},center:{name:'Center crop'},manual:{name:'Manual crop'}},c.settings.framing||'auto')}</select></label></div>
  <label class="edit-label">Horizontal focal point · left ↔ right<input class="focal-x" type="range" min="0" max="1" step="0.01" value="${c.settings.focal_x??.5}"></label>
  <label class="edit-label">Vertical focal point · top ↔ bottom<input class="focal-y" type="range" min="0" max="1" step="0.01" value="${c.settings.focal_y??.5}"></label>
  <div class="field-row"><label>Caption size<input class="caption-size" type="number" min="24" max="80" value="${c.settings.caption_size||38}"></label><label>Caption position (%)<input class="caption-y" type="number" min="0" max="100" value="${Math.round((c.settings.caption_y??.53)*100)}"></label></div>
  <label class="edit-label">Speech model<select class="clip-model">${options({tiny:{name:'Tiny · draft'},base:{name:'Base'},small:{name:'Small · better accuracy'}},c.settings.model||'small')}</select></label>
  <label class="edit-label"><input type="checkbox" class="retranscribe"> Re-transcribe this range (replaces corrected text)</label>
  <label class="edit-label">Caption text<textarea class="transcript">${esc(c.edited_transcript??words)}</textarea></label><p class="helper">Same word count keeps original timing. A changed word count is evenly timed. After trimming, use “Reset text to range” to pull the matching transcript.</p>
  <div class="edit-actions"><button class="secondary reset-text">Reset text to range</button><button class="secondary preview" ${busy?'disabled':''}>Update preview</button></div></details>
  <div class="export-row"><select class="quality" aria-label="Export quality"><option value="720p">720p</option><option value="1080p" selected>1080p</option></select><button class="secondary export" ${busy?'disabled':''}>${busy?'Rendering…':'Export MP4 ↗'}</button></div>${c.export?`<a class="download" href="${esc(c.export)}?download=true" download>↓ Download ${esc(c.export_quality)} MP4</a>`:''}`;
  const editButton=document.createElement('button');editButton.className='primary open-editor';editButton.disabled=busy;editButton.textContent='Open clip editor ↗';editButton.onclick=()=>openClipEditor(c,job);el.insertBefore(editButton,$('details',el));
  $('.reset-text',el).onclick=()=>{const a=+$('.start',el).value,b=+$('.end',el).value;$('.transcript',el).value=wordData.filter(w=>w.end>a&&w.start<b).map(w=>w.word).join(' ');};
  $('.clip-preset',el).onchange=()=>{$('.clip-style',el).value=catalog.presets[$('.clip-preset',el).value].style;};
  async function requestRender(quality,upgrade=false){
    const a=+$('.start',el).value,b=+$('.end',el).value;
    if(!Number.isFinite(a)||!Number.isFinite(b)||a<0||b<=a||b>job.meta.duration+0.01||b-a>120)return toast('Choose a valid range of up to 120 seconds.');
    let changedSettings={...c.settings,preset:$('.clip-preset',el).value,style:$('.clip-style',el).value,
      aspect:$('.clip-aspect',el).value,framing:$('.clip-framing',el).value,focal_x:+$('.focal-x',el).value,focal_y:+$('.focal-y',el).value,
      caption_size:+$('.caption-size',el).value,caption_y:+$('.caption-y',el).value/100,model:$('.clip-model',el).value,motion:false,sfx:false};
    if(upgrade)changedSettings={...changedSettings,preset:'reference',style:'neon',aspect:'9:16',framing:'auto',caption_size:48,caption_glow:.8,caption_y:.53,model:'small',enhance:true};
    const body={start:a,end:b,quality,settings:changedSettings,retranscribe:(upgrade&&job.meta.has_audio)||$('.retranscribe',el).checked};
    const text=$('.transcript',el).value;
    if(!body.retranscribe&&(text!==(c.edited_transcript??words)||c.edited_transcript!==undefined))body.transcript=text;
    $$('.export,.preview,.upgrade',el).forEach(b=>b.disabled=true);
    try{await api(`/api/jobs/${job.id}/clips/${c.id}/render`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});toast(quality==='preview'?'Updating your preview':'Rendering your MP4');clearTimeout(pollTimer);poll();}
    catch(e){toast(e.message);$$('.export,.preview,.upgrade',el).forEach(b=>b.disabled=false);}
  }
  for(const selector of ['.focal-x','.focal-y'])$(selector,el).oninput=()=>{$('.clip-framing',el).value='manual';};
  if($('.upgrade',el))$('.upgrade',el).onclick=()=>requestRender('preview',true);
  $('.preview',el).onclick=()=>requestRender('preview');$('.export',el).onclick=()=>requestRender($('.quality',el).value);
  return el;
}
async function poll(){
  const id=current;if(!id)return;
  try{
    const j=await api('/api/jobs/'+id);if(current!==id)return;currentJob=j;
    $('#project-name').textContent=j.name;$('#stage').textContent=j.stage;$('#progress').value=j.progress;$('#progress-number').textContent=j.progress+'%';
    $('#progress-panel').classList.toggle('hidden',['ready','error'].includes(j.status));
    $('#warnings').innerHTML=(j.warnings||[]).map(w=>`<div class="alert">${esc(w)}</div>`).join('');
    if(j.status==='error')error(j.error||j.stage);else error('');
    $('#result-title').textContent=j.clips.length?`${j.clips.length} moments, ready to make yours`:'Your clips will appear here';
    for(const c of j.clips){const signature=JSON.stringify([c.status,c.revision,c.preview,c.export,c.error]);const old=$(`.clip[data-id="${c.id}"]`);if(!old||old.dataset.signature!==signature){const el=clipCard(c,j);el.dataset.signature=signature;if(old)old.replaceWith(el);else $('#clips').append(el);}}
    if(!['ready','error'].includes(j.status)||j.clips.some(c=>['rendering','queued'].includes(c.status)))pollTimer=setTimeout(poll,1600);
    else refreshProjects();
  }catch(e){if(current===id){error('Connection interrupted. '+e.message);pollTimer=setTimeout(poll,4000);}}
}
(async()=>{
  try{catalog=await api('/api/catalog');drawCatalog();const h=await api('/api/health');if(!h.ffmpeg||!h.ffprobe){$('#health').textContent='FFmpeg missing';error('Install FFmpeg and ffprobe before generating clips.');}await refreshProjects();if(/^[a-f0-9]{32}$/.test(location.hash.slice(1)))openProject(location.hash.slice(1));}
  catch(e){error('Could not connect to the local engine. '+e.message);}
})();
