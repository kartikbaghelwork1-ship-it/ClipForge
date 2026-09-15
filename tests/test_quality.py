import subprocess
import cv2
import numpy as np
from app.render import render
from app.media import probe
from app.captions import write_ass
from app.tracking import choose_center


def test_stationary_scene_has_no_added_shake_and_keeps_edges(tmp_path):
    source=tmp_path/'still.mp4'
    vf='color=c=black:s=640x360:r=30,drawbox=x=0:y=0:w=80:h=360:c=red:t=fill,drawbox=x=560:y=0:w=80:h=360:c=blue:t=fill,drawgrid=w=40:h=40:t=2:c=white'
    subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i',vf,'-t','2','-c:v','libx264','-crf','16',str(source)],check=True)
    settings=dict(preset='reference',style='reference',aspect='3:4',framing='fit',captions=False,motion=True,sfx=False,enhance=False)
    result=render(source,tmp_path/'render',{'start':0,'end':2},[],probe(source),settings)
    meta=probe(result['path'])
    assert (meta['width'],meta['height'])==(720,960)
    cap=cv2.VideoCapture(str(result['path']));frames=[]
    for at in [.6,1.,1.4]:
        cap.set(cv2.CAP_PROP_POS_MSEC,at*1000);ok,frame=cap.read();assert ok;frames.append(frame)
    cap.release()
    for frame in frames[1:]:
        assert np.mean(cv2.absdiff(frame,frames[0]))<.5
    center=frames[0][420:540]
    assert center[:,10:65,2].mean()>170  # red edge survives
    assert center[:,655:705,0].mean()>170  # blue edge survives


def test_group_framing_falls_back_instead_of_cutting_off_people():
    group=[[(100,20,80,80),(700,20,80,80)]]*5
    _,safe=choose_center(group,1000,400)
    assert not safe
    single=[[(450+i,20,80,80)] for i in [-3,0,2,-1,1]]
    center,safe=choose_center(single,1000,400)
    assert safe and abs(center-490)<3
    assert choose_center([[],[],single[0]],1000,400)[1] is False


def test_reference_caption_phrase_does_not_jump_or_bounce(tmp_path):
    path=tmp_path/'words.ass'
    words=[{'word':w,'start':i*.3,'end':(i+1)*.3} for i,w in enumerate(['I','am','the','best'])]
    write_ass(words,0,2,'reference',path,{'caption_size':38,'caption_y':.53,'caption_animation':'none'},960)
    dialogues=[l for l in path.read_text().splitlines() if l.startswith('Dialogue')]
    assert len(dialogues)==4
    assert all(all(w in l for w in ['I','AM','THE','BEST']) for l in dialogues)
    assert all(r'\pos(360,509)' in l for l in dialogues)
    assert not any(r'\fsc' in l or r'\move' in l for l in dialogues)
    assert '&H0039FF92' in dialogues[-1]


def test_switching_between_fit_and_crop_renders_at_scene_boundary(tmp_path,monkeypatch):
    import importlib
    renderer=importlib.import_module('app.render')
    source=tmp_path/'scenes.mp4'
    subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','testsrc2=size=640x360:rate=30','-t','2','-c:v','libx264',str(source)],check=True)
    monkeypatch.setattr(renderer,'plan_framing',lambda *args:(270,360,[{'start':0,'end':1,'fit':True,'x':180},{'start':1,'end':2,'fit':False,'x':200}],'Mixed'))
    settings=dict(preset='reference',style='reference',aspect='3:4',captions=False,motion=False,sfx=False,enhance=False)
    result=renderer.render(source,tmp_path/'mixed',{'start':0,'end':2},[],probe(source),settings)
    assert abs(probe(result['path'])['duration']-2)<.1
    cap=cv2.VideoCapture(str(result['path']))
    for at in [.8,1.2]:
        cap.set(cv2.CAP_PROP_POS_MSEC,at*1000);ok,frame=cap.read()
        assert ok and frame.mean()>20
    cap.release()
