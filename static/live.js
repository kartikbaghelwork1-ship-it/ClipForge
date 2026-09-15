/* Source-backed canvas preview: edits never stack over burned-in captions. */
function mountLivePreview(dialog,form,clip,job){
 const pane=dialog.querySelector('.editor-preview');
 pane.querySelector('video').remove();pane.querySelector('p').remove();
 const stage=document.createElement('div');stage.className='live-stage';
 stage.innerHTML='<canvas aria-label="Live clip preview"></canvas><button type="button" class="caption-anchor" aria-label="Move captions. Drag or use arrow keys" title="Drag to move captions · arrow keys for precise positioning">✥</button><span class="source-loading">Loading source…</span><video playsinline preload="auto" hidden></video>';
 const controls=document.createElement('div');controls.className='live-controls';
 controls.innerHTML='<div><span class="live-badge">● LIVE PREVIEW</span><span class="live-time">0:00</span></div><input aria-label="Preview timeline" type="range" min="0" step="0.01" value="0"><button type="button" class="secondary play-live">▶ Play preview</button><p>Instant editing preview. Auto framing uses the last rendered crop; HD renders confirm the final finish.</p>';
 pane.prepend(controls);pane.prepend(stage);
 const video=stage.querySelector('video'),canvas=stage.querySelector('canvas'),ctx=canvas.getContext('2d'),seek=controls.querySelector('input');
 const frame=document.createElement('canvas'),fc=frame.getContext('2d'),history=document.createElement('canvas'),hc=history.getContext('2d');
 const value=n=>form.elements.namedItem(n)?.value;
 let raf,previous=-1,settings,groups=[],budget=20,offset=0,sourceWords=clip.words||job.words||[],cropShots=[],dirty=true,sourceOffset=0,proxyLoading=false;
 const anchor=stage.querySelector('.caption-anchor');
 function position(x,y){
  form.elements.namedItem('caption_x').value=(Math.max(0,Math.min(1,x))*100).toFixed(1);
  form.elements.namedItem('caption_y').value=(Math.max(0,Math.min(1,y))*100).toFixed(1);
  read();
 }
 let dragging=false;
 function move(event){const rect=canvas.getBoundingClientRect();position((event.clientX-rect.left)/rect.width,(event.clientY-rect.top)/rect.height);}
 stage.addEventListener('pointerdown',event=>{if(event.button!==0)return;dragging=true;stage.setPointerCapture(event.pointerId);event.preventDefault();move(event);});
 stage.addEventListener('pointermove',event=>{if(dragging)move(event);});
 stage.addEventListener('pointerup',()=>dragging=false);stage.addEventListener('pointercancel',()=>dragging=false);
 anchor.onkeydown=event=>{const directions={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]},d=directions[event.key];if(d){event.preventDefault();const step=event.shiftKey?.05:.005;position(settings.caption_x+d[0]*step,settings.caption_y+d[1]*step);}};
 dialog.querySelectorAll('[data-caption-position]').forEach(button=>button.onclick=()=>position(.5,+button.dataset.captionPosition/100));
 video.src='/api/media/' +job.id+'/'+encodeURIComponent(job.source);
 function read(){
  settings={...clip.settings,...readFinish(form),aspect:value('aspect'),framing:value('framing'),focal_x:+value('focal_x'),focal_y:+value('focal_y'),style:value('style'),caption_size:+value('caption_size'),caption_x:+value('caption_x')/100,caption_y:+value('caption_y')/100};
  settings.word_colors=Object.fromEntries([...dialog.querySelectorAll('.word-color')].filter(x=>x.parentElement.querySelector('.color-use').checked).map(x=>[x.dataset.word,x.value]));
  const a=+value('start'),b=+value('end');seek.max=Math.max(.01,b-a);offset=settings.caption_offset;
  let words=sourceWords.filter(w=>w.end>a&&w.start<b).map(w=>({...w}));const tokens=value('transcript').trim().split(/\s+/).filter(Boolean);
  if(tokens.join(' ')!==words.map(w=>w.word).join(' ')){
   const from=words.length?Math.max(a,words[0].start):a,to=words.length?Math.min(b,words.at(-1).end):b;
   words=tokens.map((word,i)=>({word,start:tokens.length===words.length?words[i].start:from+i*(to-from)/tokens.length,end:tokens.length===words.length?words[i].end:from+(i+1)*(to-from)/tokens.length}));
  }
  words=words.map(w=>({...w,start:Math.max(a,w.start+offset),end:Math.min(b,w.end+offset)})).filter(w=>w.end>w.start);
  groups=[];let group=[];budget=Math.max(14,Math.floor(620/(settings.caption_size*.65)));
  for(const w of words){const candidate=[...group,w].map(x=>x.word).join(' ');if(group.length&&(group.length>=5||candidate.length>budget*1.65||w.start-group.at(-1).end>.35||w.end-group[0].start>2.2||/[.!?]$/.test(group.at(-1).word))){groups.push(group);group=[];}group.push(w);}if(group.length)groups.push(group);
  if(settings.caption_mode==='word'||settings.style==='one_word'&&settings.caption_mode!=='phrase')groups=groups.flatMap(g=>g.map(w=>[w]));
  if(video.currentTime+sourceOffset<a||video.currentTime+sourceOffset>b)video.currentTime=a-sourceOffset;
  anchor.style.left=settings.caption_x*100+'%';anchor.style.top=settings.caption_y*100+'%';
  dirty=true;
 }
 form.addEventListener('input',read);form.addEventListener('change',read);dialog.querySelector('.reset-fill').addEventListener('click',read);
 video.onloadedmetadata=()=>{video.currentTime=+value('start')-sourceOffset;};
 video.onloadeddata=()=>{stage.querySelector('.source-loading')?.remove();dirty=true;};
 video.onerror=async()=>{
  if(proxyLoading)return;proxyLoading=true;const message=pane.querySelector('.editor-message');message.textContent='Preparing a browser-compatible preview…';
  try{const response=await fetch('/api/jobs/'+job.id+'/clips/'+clip.id+'/source-preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({start:+value('start'),end:+value('end'),settings:clip.settings})});if(!response.ok)throw Error('Preview conversion failed. Try a shorter clip.');const data=await response.json();if(!dialog.open)return;sourceOffset=data.offset;video.src=data.url;message.textContent='Compatible preview ready. Reopen the editor after changing the trim range.';}catch(e){message.textContent=e.message;}
 };
 const play=controls.querySelector('button');play.onclick=async()=>{if(video.paused){if(video.currentTime+sourceOffset>=+value('end')-.05)video.currentTime=+value('start')-sourceOffset;try{await video.play();}catch(e){pane.querySelector('.editor-message').textContent=e.message;}}else video.pause();};
 video.onplay=()=>play.textContent='Ⅱ Pause';video.onpause=()=>play.textContent='▶ Play preview';
 seek.oninput=()=>{video.currentTime=+value('start')+Number(seek.value)-sourceOffset;dirty=true;};video.onseeked=()=>{previous=-1;dirty=true;};
 // Saved shot positions match the automatic renderer, without scanning the video on every slider move.
 fetch('/api/jobs/'+job.id+'/clips/'+clip.id+'/framing').then(r=>r.json()).then(data=>{cropShots=data.shots||[];dirty=true;}).catch(()=>{});
 const colors={electric:['#FAFF00','#FFFFFF','#39FF14','#FF3434','#51EDFF','#FF00D9'],candy:['#FF00D9','#B26BFF','#50E9FF','#FFFFFF'],fire:['#FF3434','#FF8C00','#FFED38','#FFFFFF'],ice:['#55EFFF','#7AA5FF','#FFFFFF','#C595FF']};
 function drawCaption(t,W,H){
  if(!settings.captions)return;
  let gi=groups.findIndex((g,i)=>t>=g[0].start&&t<Math.min(g.at(-1).end+.08,groups[i+1]?.[0].start??Infinity));if(gi<0)return;
  const group=groups[gi],active=group.findLastIndex(w=>w.start<=t),style=catalog.styles[settings.style],anim=settings.caption_animation;
  const tokens=group.map(w=>w.word.toUpperCase());let split=0;
  if((tokens.join(' ').length>budget||settings.style==='money')&&tokens.length>1){let best=Infinity;for(let i=1;i<tokens.length;i++){let d=Math.abs(tokens.slice(0,i).join(' ').length-tokens.slice(i).join(' ').length);if(d<best){best=d;split=i;}}}
  const maxline=split?Math.max(tokens.slice(0,split).join(' ').length,tokens.slice(split).join(' ').length):tokens.join(' ').length;
  const size=Math.min(settings.caption_size,Math.max(18,Math.floor(settings.caption_size*budget/Math.max(budget,maxline)))),scale=W/720;
  const progress=Math.min(1,Math.max(0,(t-group[Math.max(0,active)].start)/.16));
  ctx.save();ctx.translate(W*settings.caption_x,H*settings.caption_y+(anim==='float'?12*(1-progress)*scale:0));if(anim==='pop'){let z=.92+.08*progress;ctx.scale(z,z);}ctx.globalAlpha=anim==='none'?1:Math.min(1,(t-group[Math.max(0,active)].start)/.045);
  const glowing=['neon','one_word','magenta','money'].includes(settings.style);ctx.font='900 '+size*scale+'px '+(glowing?'CaptionHeavy':'Arial');ctx.textBaseline='middle';
  const rows=split?[tokens.slice(0,split),tokens.slice(split)]:[tokens];let index=0,totalBefore=groups.slice(0,gi).reduce((n,g)=>n+g.length,0);
  rows.forEach((row,line)=>{const space=ctx.measureText(' ').width;const lengths=row.map(w=>ctx.measureText(w).width);let x=-(lengths.reduce((a,b)=>a+b,0)+space*(row.length-1))/2,y=(line-(rows.length-1)/2)*size*scale*1.18;
   row.forEach((word,j)=>{let i=index++,color=style.color;
    if(['neon','one_word'].includes(settings.style)){let p=colors[settings.caption_palette];color=p[(group.length===1?totalBefore+i:Math.floor((totalBefore+i)/2))%p.length];}
    else if(settings.style==='money')color=split&&i<split?'#FFFFFF':style.color;
    else if(settings.style!=='magenta'&&i!==active)color='#FFFFFF';
    color=settings.word_colors[word.toLowerCase().replace(/[^\p{L}\p{N}_]/gu,'')]||color;
    if(anim==='none'||i<=active){ctx.fillStyle=color;ctx.strokeStyle='#161616';ctx.lineWidth=glowing?1.4*scale:4.4*scale;ctx.shadowColor=color;ctx.shadowBlur=glowing?settings.caption_glow*22*scale:0;ctx.strokeText(word,x,y);ctx.fillText(word,x,y);if(glowing)ctx.fillText(word,x,y);}
    x+=lengths[j]+space;
   });
  });ctx.restore();
 }
 function draw(){
  raf=requestAnimationFrame(draw);if(!dialog.open)return;
  const t=video.currentTime+sourceOffset,a=+value('start'),b=+value('end');if(t>=b&&!video.paused){video.pause();video.currentTime=b-.001-sourceOffset;}
  seek.value=Math.max(0,t-a);controls.querySelector('.live-time').textContent=Math.max(0,t-a).toFixed(2)+' / '+Math.max(0,b-a).toFixed(2)+' s';
  if(video.readyState<2||(!dirty&&t===previous))return;
  const changed=t!==previous;previous=t;dirty=false;
  const W=720,H=settings.aspect==='3:4'?960:1280;
  if(canvas.height!==H){canvas.width=frame.width=history.width=W;canvas.height=frame.height=history.height=H;stage.style.aspectRatio=W+'/'+H;}
  const sw=video.videoWidth,sh=video.videoHeight,ratio=W/H;let cw=Math.min(sw,sh*ratio),ch=Math.min(sh,sw/ratio);
  let x=Math.max(0,Math.min(sw-cw,sw*(settings.framing==='center'?.5:settings.focal_x)-cw/2)),y=Math.max(0,Math.min(sh-ch,sh*settings.focal_y-ch/2));
  if(['auto','safe'].includes(settings.framing)){const shot=cropShots.filter(s=>s.time<=t-clip.start).at(-1);if(shot)x=Math.max(0,Math.min(sw-cw,shot.x));}
  fc.filter='none';fc.clearRect(0,0,W,H);fc.drawImage(video,x,y,cw,ch,0,0,W,H);
  if(settings.framing==='fit'){fc.filter='blur(24px) brightness(.85)';fc.drawImage(video,x,y,cw,ch,0,0,W,H);fc.filter='none';const k=Math.min(W/sw,H/sh);fc.drawImage(video,(W-sw*k)/2,(H-sh*k)/2,sw*k,sh*k);}
  if(settings.motion_blur&&changed&&history.width){fc.globalAlpha=settings.motion_blur*.25;fc.drawImage(history,0,0);fc.globalAlpha=1;}hc.clearRect(0,0,W,H);hc.drawImage(frame,0,0);
  ctx.clearRect(0,0,W,H);ctx.drawImage(frame,0,0);
  if(settings.video_glow){ctx.save();ctx.globalCompositeOperation='screen';ctx.globalAlpha=settings.video_glow*.4;ctx.filter='blur(8px)';ctx.drawImage(frame,0,0);ctx.restore();}
  for(const edge of ['top','bottom']){const h=H*settings['blur_'+edge],y=edge==='top'?0:H-h;if(h>0){ctx.save();ctx.beginPath();ctx.rect(0,y,W,h);ctx.clip();ctx.filter='blur(18px)';ctx.drawImage(frame,0,0);ctx.restore();}const bar=H*settings['bar_'+edge];ctx.fillStyle='#000';ctx.fillRect(0,edge==='top'?0:H-bar,W,bar);}
  drawCaption(t,W,H);
 }
 read();draw();document.fonts.ready.then(()=>dirty=true);
 dialog.addEventListener('close',()=>{cancelAnimationFrame(raf);video.pause();video.removeAttribute('src');video.load();},{once:true});
}
document.addEventListener('DOMContentLoaded',()=>{
 const theme=localStorage.getItem('clipforge-theme')||'dark';document.documentElement.dataset.theme=theme;
 const button=document.createElement('button');button.className='secondary theme-toggle';button.textContent=theme==='dark'?'☀ Light mode':'☾ Dark mode';
 button.onclick=()=>{const next=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=next;localStorage.setItem('clipforge-theme',next);button.textContent=next==='dark'?'☀ Light mode':'☾ Dark mode';};document.querySelector('header').append(button);
});
