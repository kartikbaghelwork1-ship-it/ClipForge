import time
import subprocess
from fastapi.testclient import TestClient
from app import main


def wait_ready(client, jid):
    for _ in range(200):
        job=client.get('/api/jobs/'+jid).json()
        if job['status'] in {'ready','error'} and not any(c['status']=='rendering' for c in job['clips']):
            return job
        time.sleep(.1)
    raise AssertionError('Job did not finish in 20 seconds')


def test_upload_preview_edit_export_and_media_ranges(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'DATA',tmp_path)
    monkeypatch.setattr(main,'JOBS',{})
    source=tmp_path/'input.mp4'
    subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','testsrc2=size=640x360:rate=30','-t','3','-c:v','libx264','-preset','ultrafast',str(source)],check=True)
    with TestClient(main.app) as client:
        assert client.get('/').status_code==200
        assert len(client.get('/api/catalog').json()['styles'])==15
        assert client.post('/api/jobs',headers={'Origin':'https://evil.example'}).status_code==403
        assert client.post('/api/jobs',data={'url':'http://localhost:9000'}).status_code==422
        with source.open('rb') as f:
            response=client.post('/api/jobs',files={'file':('test.mp4',f,'video/mp4')},data={'settings':'{"count":1}'})
        assert response.status_code==202,response.text
        jid=response.json()['id']
        job=wait_ready(client,jid)
        assert job['status']=='ready',job
        clip=job['clips'][0]
        assert clip['status']=='ready',clip
        assert job['warnings']
        media=client.get(clip['preview'],headers={'Range':'bytes=0-99'})
        assert media.status_code==206
        assert len(media.content)==100
        assert client.get(f'/api/media/{jid}/job.json').status_code==404
        body={'start':0,'end':3,'settings':job['settings'],'quality':'720p','transcript':'Test caption correction'}
        assert client.post(f'/api/jobs/{jid}/clips/1/render',json=body).status_code==202
        finished=wait_ready(client,jid)['clips'][0]
        assert finished['status']=='ready',finished
        result=client.get(finished['export']+'?download=true')
        assert result.status_code==200
        assert 'attachment' in result.headers['content-disposition']
        framing=client.get(f'/api/jobs/{jid}/clips/1/framing')
        assert framing.status_code==200 and framing.json()['shots']
        proxy=client.post(f'/api/jobs/{jid}/clips/1/source-preview',json=body)
        assert proxy.status_code==200,proxy.text
        assert proxy.json()['offset']==0
        assert client.get(proxy.json()['url'],headers={'Range':'bytes=0-99'}).status_code==206
        body['end']=10000
        assert client.post(f'/api/jobs/{jid}/clips/1/source-preview',json=body).status_code==422
        assert client.post(f'/api/jobs/{jid}/clips/1/render',json=body).status_code==422
