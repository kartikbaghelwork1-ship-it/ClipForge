from pathlib import Path
import json
import subprocess
import pytest
from app.captions import write_ass
from app.catalog import STYLES, PRESETS
from app.highlights import rank
from app.main import youtube_url
from app.media import probe
from app.render import render


def test_youtube_validation():
    assert youtube_url('https://youtu.be/abcdefghijk?t=3') == 'https://www.youtube.com/watch?v=abcdefghijk'
    assert youtube_url('https://www.youtube.com/shorts/abcdefghijk') == 'https://www.youtube.com/watch?v=abcdefghijk'
    for url in ['http://127.0.0.1/video','https://youtube.com.evil.example/watch?v=abcdefghijk','https://youtube.com/watch?v=bad','file:///etc/passwd']:
        with pytest.raises(ValueError): youtube_url(url)


def test_highlights_bounded_and_distinct():
    segs=[{'start':i,'end':i+4,'text':'The secret is surprising. Here is why.'} for i in range(0,120,5)]
    clips=rank(segs,[0.8]*120,120,30,3)
    assert len(clips)==3
    for c in clips:
        assert 0<=c['start']<c['end']<=120
    for a,b in zip(clips,clips[1:]):
        assert max(0,min(a['end'],b['end'])-max(a['start'],b['start']))<=8
    assert len(rank([],[],5,30,8))==1


@pytest.fixture(scope='module')
def source(tmp_path_factory):
    p=tmp_path_factory.mktemp('source')/'sample.mp4'
    subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','testsrc2=size=640x360:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','5','-c:v','libx264','-preset','ultrafast','-c:a','aac',str(p)],check=True)
    return p


@pytest.mark.parametrize('style',list(STYLES))
def test_each_caption_style_renders_real_video(source,tmp_path,style):
    settings=dict(aspect='9:16',preset='gaming',style=style,tracking=True,captions=True,motion=True,sfx=True,enhance=True)
    words=[{'word':w,'start':i*.5,'end':(i+1)*.5} for i,w in enumerate(['Make','every','moment','count','right','now'])]
    result=render(source,tmp_path/style,{'start':0,'end':4},words,probe(source),settings)
    meta=probe(result['path'])
    assert (meta['width'],meta['height'])==(720,1280)
    assert abs(meta['duration']-4)<.15
    assert meta['has_audio']


def test_caption_injection_and_trim(tmp_path):
    target=tmp_path/'captions.ass'
    write_ass([{'word':'{\\pos(0,0)}','start':5,'end':6}],5,7,'pop',target)
    text=target.read_text()
    assert '0:00:00.00,0:00:01.08' in text
    assert r'{\pos(0,0)}' not in text


def test_no_audio_and_portrait(tmp_path):
    source=tmp_path/'silent.mp4'
    subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','color=c=blue:s=180x320:r=30','-t','2','-c:v','libx264',str(source)],check=True)
    settings=dict(aspect='9:16',preset='podcast',style='clean',tracking=True,captions=True,motion=False,sfx=False,enhance=False)
    result=render(source,tmp_path/'silent-render',{'start':0,'end':2},[],probe(source),settings,'720p')
    meta=probe(result['path'])
    assert (meta['width'],meta['height'])==(720,1280)
    assert not meta['has_audio']
