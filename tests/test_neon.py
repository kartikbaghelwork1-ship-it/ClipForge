import subprocess
from pathlib import Path
import cv2
import numpy as np
from app.captions import write_ass
from app.main import Settings,validate_settings
from app.media import probe
from app.render import render
from app.tracking import plan_framing
from fastapi import HTTPException
import pytest


def test_default_fill_never_silently_letterboxes(tmp_path):
    source=tmp_path/'wide.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=s=640x360:r=15','-t','1','-c:v','libx264',str(source)],check=True)
    opts=Settings().model_dump()
    assert opts['aspect']=='9:16'
    cw,ch,shots,_=plan_framing(source,0,1,probe(source),opts,9/16)
    assert all(not s['fit'] for s in shots)
    assert abs(cw/ch-9/16)<.01


def test_single_word_has_one_token_per_event_and_no_overlaps(tmp_path):
    words=[dict(word=w,start=i*.3,end=(i+1)*.3) for i,w in enumerate(['MAKE','IT','HAPPEN'])]
    path=tmp_path/'one.ass'
    write_ass(words,0,2,'one_word',path)
    lines=[l for l in path.read_text().splitlines() if l.startswith('Dialogue: 2')]
    assert len(lines)==3
    for i,line in enumerate(lines):
        assert words[i]['word'] in line
        assert all(w['word'] not in line for j,w in enumerate(words) if i!=j)


def test_neon_has_distinct_glow_layers_and_custom_word_colors(tmp_path):
    words=[dict(word=w,start=i*.4,end=(i+1)*.4) for i,w in enumerate(['YOU','WIN','MONEY'])]
    path=tmp_path/'neon.ass'
    write_ass(words,0,2,'neon',path,{'word_colors':{'money':'#FF00D9'}})
    text=path.read_text()
    assert 'Montserrat ExtraBold' in text
    assert all('Dialogue: '+str(i) in text for i in [0,1,2])
    import re
    assert max(map(float,re.findall(r'\\blur([0-9.]+)',text)))>10
    assert '&H00D900FF' in text
    with pytest.raises(HTTPException):
        validate_settings(Settings(word_colors={'money':'invalid'}))


def test_glow_spreads_beyond_sharp_text_and_video_bars_are_real(tmp_path):
    source=tmp_path/'gray.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=0x303030:s=360x640:r=15','-t','1','-c:v','libx264',str(source)],check=True)
    words=[dict(word='GLOW',start=0,end=1)]
    frames=[]
    for strength in [0,1]:
        opts=Settings(style='neon',caption_glow=strength,caption_size=64,bar_top=.1,bar_bottom=.1,framing='center',captions=True,enhance=False).model_dump()
        result=render(source,tmp_path/str(strength),{'start':0,'end':1},words,probe(source),opts)
        cap=cv2.VideoCapture(str(result['path']));cap.set(cv2.CAP_PROP_POS_MSEC,500);ok,frame=cap.read();cap.release()
        assert ok
        assert frame[:80].mean()<3 and frame[-80:].mean()<3
        frames.append(frame)
    off,on=frames
    sharp=(off.max(axis=2)>130).astype(np.uint8)
    outside=cv2.dilate(sharp,np.ones((7,7),np.uint8))==0
    halo=((on.astype(float)-off).mean(axis=2)>8)&outside
    assert halo.sum()>1000
