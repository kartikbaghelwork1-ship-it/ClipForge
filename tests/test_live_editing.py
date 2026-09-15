from app.captions import write_ass
from app.main import Settings,validate_settings
from app.render import render
from app.media import probe
from pathlib import Path
import pytest

def test_neon_reveals_on_word_times_with_float_and_offset(tmp_path):
    words=[dict(word='HELLO',start=.2,end=.6),dict(word='WORLD',start=.7,end=1.1)]
    path=tmp_path/'timed.ass'
    write_ass(words,0,2,'neon',path,{'caption_animation':'float','caption_offset':.15})
    events=[x for x in path.read_text().splitlines() if x.startswith('Dialogue: 2')]
    assert len(events)==2
    assert ',0:00:00.35,0:00:00.85,' in events[0]
    assert r'\move(360,690,360,678,0,160)' in events[0]
    assert r'{\alpha&HFF&}WORLD' in events[0]
    assert r'{\alpha&H00&}WORLD' in events[1]

def test_motion_blur_and_pop_encode_with_audio(tmp_path):
    import subprocess
    source=tmp_path/'sample.mp4'
    subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','testsrc2=size=640x360:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','2','-c:v','libx264','-preset','ultrafast','-c:a','aac',str(source)],check=True)
    settings=Settings(caption_animation='pop',motion_blur=.5,framing='center').model_dump()
    result=render(source,tmp_path/'clip',{'start':0,'end':1.3},[dict(word='TEST',start=.2,end=.9)],probe(source),settings)
    meta=probe(result['path'])
    assert (meta['width'],meta['height'])==(720,1280)
    assert meta['has_audio'] and abs(meta['duration']-1.3)<.15
    assert r'\t(0,160,\fscx100\fscy100)' in (tmp_path/'clip/captions.ass').read_text()

def test_animation_settings_reject_invalid_values():
    with pytest.raises(Exception): validate_settings(Settings(caption_animation='unknown'))
    with pytest.raises(ValueError): Settings(motion_blur=1.1)
    with pytest.raises(ValueError): Settings(caption_offset=3)

@pytest.mark.parametrize('animation',['float','pop','none'])
def test_caption_position_is_used_in_export(tmp_path,animation):
    path=tmp_path/'position.ass'
    write_ass([dict(word='MOVE',start=.1,end=.8)],0,1,'one_word',path,
              dict(caption_x=.25,caption_y=.9,caption_animation=animation))
    text=path.read_text()
    assert (r'\move(180,1164,180,1152,' if animation=='float' else r'\pos(180,1152)') in text
    assert Settings(caption_x=0,caption_y=1).caption_y==1
    with pytest.raises(ValueError): Settings(caption_x=1.01)
