from pathlib import Path
import subprocess
from .captions import write_ass
from .finishing import finish_graph
import shutil
from .catalog import PRESETS
from .effects import motion_filter, sound_track
from .media import probe
from .tracking import plan_framing

RENDER_VERSION = 4


def render(source,folder,clip,words,meta,settings,quality='preview'):
    duration=clip['end']-clip['start']
    aspect=3/4 if settings.get('aspect','9:16')=='3:4' else 9/16
    width=720 if quality in {'preview','720p'} else 1080
    height=round(width/aspect)//2*2
    preset=PRESETS[settings['preset']]
    fps=min(60,max(12,meta.get('fps') or probe(source).get('fps',30)))
    folder.mkdir(parents=True,exist_ok=True)
    write_ass(words,clip['start'],clip['end'],settings['style'],folder/'captions.ass',settings,round(720/aspect))
    cw,ch,shots,framing=plan_framing(source,clip['start'],duration,meta,settings,aspect)
    (folder/'tracking.cmd').write_text('\n'.join(f"{s['start']:.3f} crop@reframe x {s['x']:.2f};" for s in shots))
    cy=max(0,min(meta['height']-ch,settings.get('focal_y',.5)*meta['height']-ch/2))
    fits=[s for s in shots if s['fit']]
    graph=[]
    graph.append(f'[0:v]setpts=PTS-STARTPTS,fps={fps},setsar=1[src]')
    crop=f'sendcmd=f=tracking.cmd,crop@reframe={cw}:{ch}:{shots[0]["x"]:.2f}:{cy:.2f},scale={width}:{height}:flags=lanczos,setsar=1'
    if fits:
        if len(fits)==len(shots):
            graph.append('[src]split=2[bg0][fg0]')
        else:
            graph.append('[src]split=3[bg0][fg0][crop0]')
            graph.append(f'[crop0]{crop}[cropped]')
        # Low-resolution background blur is cheap; foreground retains source detail.
        graph.append(f'[bg0]scale=180:{round(180/aspect)//2*2}:force_original_aspect_ratio=increase,crop=180:{round(180/aspect)//2*2},gblur=sigma=12,eq=brightness=-0.12:saturation=0.7,scale={width}:{height}[bg]')
        graph.append(f'[fg0]scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2:flags=lanczos,setsar=1[fg]')
        graph.append('[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1[fit]')
        if len(fits)==len(shots):
            graph.append('[fit]null[framed]')
        else:
            fit_expr='+'.join(f'between(t,{s["start"]:.4f},{s["end"]:.4f})' for s in fits)
            graph.append(f"[fit][cropped]overlay=0:0:enable='not({fit_expr})':shortest=1[framed]")
    else:
        graph.append(f'[src]{crop}[framed]')
    finished=finish_graph(graph,'framed',width,height,settings)
    filters=[]
    if settings.get('motion',False):
        filters.append(f'fade=t=in:st=0:d=0.08,fade=t=out:st={max(0,duration-.1):.3f}:d=0.10')
    if settings.get('enhance',True):
        # Light sharpening only; strong temporal denoise erased detail in moving footage.
        filters.append('unsharp=5:5:0.25:5:5:0')
    if settings['captions']:
        fonts=Path(__file__).resolve().parent.parent/'static'/'fonts'
        shutil.copytree(fonts,folder/'fonts',dirs_exist_ok=True)
        filters.append('ass=captions.ass:fontsdir=fonts')
    graph.append(f'[{finished}]'+(','.join(filters) or 'null')+'[v]')
    args=['ffmpeg','-y','-v','error','-ss',str(clip['start']),'-i',str(source.resolve())]
    # Sound accents are opt-in. Do not automatically add beeps to every few seconds.
    add_sfx=settings.get('sfx',False) and settings.get('motion',False)
    if add_sfx:
        sound_track(folder/'effects.wav',duration,preset)
        args+=['-i',str((folder/'effects.wav').resolve())]
    if meta['has_audio']:
        audio='asetpts=PTS-STARTPTS'
        if settings.get('enhance',True): audio+=',afftdn=nf=-35'
        audio+=',loudnorm=I=-16:TP=-1.5:LRA=11'
        graph.append(f'[0:a]{audio}[voice]')
        if add_sfx: graph.append('[voice][1:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]')
        else: graph.append('[voice]anull[a]')
    elif add_sfx: graph.append('[1:a]anull[a]')
    args+=['-filter_complex_threads','2','-filter_complex',';'.join(graph),'-map','[v]']
    if meta['has_audio'] or add_sfx: args+=['-map','[a]','-c:a','aac','-b:a','192k']
    output=folder/'video.mp4'
    args+=['-t',str(duration),'-c:v','libx264','-preset','fast' if quality=='preview' else 'medium','-crf','18' if quality=='preview' else '16',
           '-pix_fmt','yuv420p','-movflags','+faststart','-threads','4',str(output.resolve())]
    proc=subprocess.run(args,cwd=folder,capture_output=True,text=True,timeout=3600)
    if proc.returncode: raise RuntimeError(proc.stderr[-2200:])
    return {'path':output,'framing':framing,'width':width,'height':height,'fps':fps,'render_version':RENDER_VERSION}
