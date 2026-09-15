/* Dedicated, non-destructive clip editor. All controls are sent to the renderer. */
const palettes={electric:'Electric · yellow / green / red',candy:'Candy · pink / violet',fire:'Fire · red / gold',ice:'Ice · cyan / blue'};
function editorSelect(name,label,values,value){
  return '<label>'+label+'<select name="'+name+'">'+Object.entries(values).map(([k,v])=>'<option value="'+k+'" '+(k===value?'selected':'')+'>'+v+'</option>').join('')+'</select></label>';
}
function editorNumber(name,label,value,min,max,step=1){
  return '<label>'+label+'<input name="'+name+'" type="number" min="'+min+'" max="'+max+'" step="'+step+'" value="'+value+'"></label>';
}
function editorRange(name,label,value,min=0,max=1,step=.05){
  return '<label>'+label+' <output class="range-value">'+value+'</output><input name="'+name+'" type="range" aria-label="'+label+'" min="'+min+'" max="'+max+'" step="'+step+'" value="'+value+'"></label>';
}
function finishFields(s){
  return '<h3>Caption finish</h3><div class="field-row">'+
    editorSelect('caption_mode','Display',{style:'Style default',phrase:'Short phrases',word:'One word at a time'},s.caption_mode||'style')+
    editorSelect('caption_palette','Colors',palettes,s.caption_palette||'electric')+'</div>'+
    editorRange('caption_glow','Caption glow',s.caption_glow??.8)+
    editorSelect('caption_animation','Entrance',{float:'Float · speech synced',pop:'Pop · speech synced',none:'Still'},s.caption_animation||'float')+editorRange('caption_offset','Caption timing · seconds',s.caption_offset||0,-2,2,.05)+editorRange('motion_blur','Motion blur · subtle frame trails',s.motion_blur||0)+
    '<h3>Video finish</h3><div class="field-row">'+
    editorNumber('bar_top','Top black bar (%)',Math.round((s.bar_top||0)*100),0,35)+
    editorNumber('bar_bottom','Bottom black bar (%)',Math.round((s.bar_bottom||0)*100),0,35)+'</div><div class="field-row">'+
    editorNumber('blur_top','Blur top (%)',Math.round((s.blur_top||0)*100),0,45)+
    editorNumber('blur_bottom','Blur bottom (%)',Math.round((s.blur_bottom||0)*100),0,45)+'</div>'+
    editorRange('video_glow','Video glow',s.video_glow||0)+
    '<p class="helper">Bars cover the edges. Blur affects only the selected regions. Captions stay sharp on top.</p>';
}
function readFinish(form){
  const data=new FormData(form),s={};
  for(const key of ['caption_mode','caption_palette','caption_animation'])s[key]=data.get(key);
  for(const key of ['caption_glow','video_glow','caption_offset','motion_blur'])s[key]=Number(data.get(key));
  for(const key of ['bar_top','bar_bottom','blur_top','blur_bottom'])s[key]=Number(data.get(key))/100;
  return s;
}
function creationFinish(){return readFinish(document.getElementById('creation-finish'));}
document.addEventListener('input',event=>{if(event.target.matches('input[type=range]')){const out=event.target.parentElement.querySelector('output');if(out)out.value=event.target.value;}});
document.addEventListener('DOMContentLoaded',()=>{
  const details=document.createElement('details');details.className='panel default-finishing';
  details.innerHTML='<summary>Caption & video finish · glow, colors, bars and blur</summary><form id="creation-finish">'+finishFields({})+'</form>';
  document.querySelector('.caption-panel').after(details);
});
function openClipEditor(clip,job){
  const s=clip.settings,dialog=document.createElement('dialog');
  dialog.className='clip-editor';
  const words=(clip.words||job.words).filter(w=>w.end>clip.start&&w.start<clip.end).map(w=>w.word).join(' ');
  const transcript=clip.edited_transcript??words;
  const keys=[...new Set(transcript.split(/\s+/).map(w=>w.toLowerCase().replace(/[^\p{L}\p{N}_]/gu,'')))].filter(Boolean).slice(0,200);
  dialog.innerHTML='<div class="editor-top"><div><b>Clip editor</b><small>Frame it. Style it. Make it yours.</small></div><button class="secondary close-editor">Done ✕</button></div>'+
    '<div class="editor-layout"><div class="editor-preview"><video controls playsinline src="'+esc(clip.preview||clip.export||'')+'"></video><p>Current rendered preview. Apply edits to see the exact result.</p><div class="editor-message" role="status"></div></div>'+
    '<form class="editor-form"><h3>Frame & trim</h3><div class="field-row">'+
    editorNumber('start','Start (seconds)',clip.start,0,job.meta.duration,.01)+editorNumber('end','End (seconds)',clip.end,0,job.meta.duration,.01)+'</div><div class="field-row">'+
    editorSelect('aspect','Layout',{'9:16':'9:16 · full screen','3:4':'3:4 · portrait'},s.aspect||'9:16')+
    editorSelect('framing','Framing',{auto:'Fill · automatic crop',center:'Fill · center crop',manual:'Fill · manual position',safe:'Safe auto · may letterbox',fit:'Fit · entire wide scene'},s.framing||'auto')+'</div>'+
    editorRange('focal_x','Horizontal focal point',s.focal_x??.5,0,1,.01)+editorRange('focal_y','Vertical focal point',s.focal_y??.5,0,1,.01)+
    '<h3>Caption style</h3>'+editorSelect('style','Style',Object.fromEntries(Object.entries(catalog.styles).map(([k,v])=>[k,v.name])),s.style)+
    '<div class="editor-style-sample" aria-label="Caption appearance sample">YOUR <span>BEST</span> MOMENT</div><div class="field-row">'+
    editorNumber('caption_size','Size',s.caption_size||48,24,80)+'</div><div class="field-row">'+editorNumber('caption_x','Left / right (%)',Math.round((s.caption_x??.5)*100),0,100,.1)+editorNumber('caption_y','Up / down (%)',Math.round((s.caption_y??.53)*100),0,100,.1)+'</div><div class="position-presets"><button type="button" class="secondary" data-caption-position="15">Top</button><button type="button" class="secondary" data-caption-position="50">Center</button><button type="button" class="secondary" data-caption-position="80">Bottom</button></div><p class="helper">Drag anywhere on the video to place captions. Near the edges, text may be cut off.</p>'+
    finishFields(s)+
    '<details class="word-colors"><summary>Individual word colors</summary><p class="helper">Enable a word to override its palette color. Repeated words share a color.</p><div class="word-color-grid">'+
    keys.map(w=>'<label><input class="color-use" type="checkbox" '+(s.word_colors?.[w]?'checked':'')+'><span>'+esc(w)+'</span><input class="word-color" data-word="'+esc(w)+'" type="color" value="'+esc(s.word_colors?.[w]||'#FAFF00')+'"></label>').join('')+'</div></details>'+
    '<label>Caption text<textarea name="transcript">'+esc(transcript)+'</textarea></label><p class="helper">Unchanged word count preserves word timing. Changed word counts are evenly timed.</p>'+
    '<div class="editor-actions"><button class="primary" type="submit">Apply edits · HD preview</button><button class="secondary reset-fill" type="button">Reset to 9:16 fill</button></div></form></div>';
  document.body.append(dialog);const form=dialog.querySelector('form');
  dialog.querySelector('.close-editor').onclick=()=>dialog.close();dialog.onclose=()=>dialog.remove();
  const field=n=>form.elements.namedItem(n);
  for(const n of ['focal_x','focal_y'])field(n).oninput=()=>field('framing').value='manual';
  dialog.querySelectorAll('.word-color').forEach(i=>i.oninput=()=>i.parentElement.querySelector('.color-use').checked=true);
  function sample(){const id=field('style').value;dialog.querySelector('.editor-style-sample').dataset.style=id;}
  field('style').onchange=sample;sample();
  dialog.querySelector('.reset-fill').onclick=()=>{field('aspect').value='9:16';field('framing').value='auto';field('bar_top').value=0;field('bar_bottom').value=0;field('blur_top').value=0;field('blur_bottom').value=0;};
  form.onsubmit=async e=>{
    e.preventDefault();if(!form.reportValidity())return;
    const a=+field('start').value,b=+field('end').value,message=dialog.querySelector('.editor-message');
    if(b<=a||b-a>120){message.textContent='Select a range between 0 and 120 seconds.';return;}
    const next={...s,...readFinish(form),aspect:field('aspect').value,framing:field('framing').value,style:field('style').value,
      focal_x:+field('focal_x').value,focal_y:+field('focal_y').value,caption_size:+field('caption_size').value,caption_x:+field('caption_x').value/100,caption_y:+field('caption_y').value/100,
      word_colors:Object.fromEntries([...dialog.querySelectorAll('.word-color')].filter(i=>i.parentElement.querySelector('.color-use').checked).map(i=>[i.dataset.word,i.value]))};
    const body={start:a,end:b,settings:next,quality:'preview'};
    if(field('transcript').value!==transcript||clip.edited_transcript!==undefined)body.transcript=field('transcript').value;
    const button=form.querySelector('[type=submit]');button.disabled=true;
    try{await api('/api/jobs/'+job.id+'/clips/'+clip.id+'/render',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      dialog.close();toast('Rendering your edits in HD');clearTimeout(pollTimer);poll();
    }catch(error){message.textContent=error.message;button.disabled=false;}
  };
  dialog.showModal();
  mountLivePreview(dialog,form,clip,job);
}
function captionSwatch(id){
  const samples={
    neon:'<span style="color:#faff00">PUT ON</span> <span style="color:#39ff14">THE</span><br><span style="color:#ff3434">GLOW</span>',
    one_word:'<span style="color:#39ff14">UNREAL</span>',
    magenta:'<span style="color:#ff00d9">I DON’T<br>HAVE IT</span>',
    money:'<span style="color:#fff">MAKE US LAUGH</span><br><span style="color:#89ff00">YOU WIN</span>',
    hormozi:'BIG <span style="color:#ffff00">IDEAS</span>',
    creator:'<span style="color:#49e5ff">WATCH</span> THIS',
    minimal:'A simple story',
    reference:'I’M THE BEST',
    karaoke:'WATCH <span style="color:#ffda57">THIS</span>',
    typewriter:'one word_',
    clean:'Less is more',
    boxed:'YOUR STORY',
    impact:'BIG ENERGY',
    pop:'MAKE IT',
    slide:'KEEP GOING'
  };
  return samples[id]||'YOUR STORY';
}
