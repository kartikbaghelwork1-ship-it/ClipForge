import copy
import json
import os
import re
import shutil
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .catalog import STYLES, PRESETS
from .media import probe, extract_audio, thumbnail, run
from .highlights import rank, audio_energy
from .render import render
from .transcribe import transcribe

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("CLIPFORGE_DATA", ROOT / "data")).resolve()
DATA.mkdir(parents=True, exist_ok=True)
POOL = ThreadPoolExecutor(max_workers=1)
LOCK = threading.RLock()
JOBS = {}
for p in DATA.glob("*/job.json"):
    try:
        j = json.loads(p.read_text())
        if j["status"] not in {"ready","error"}:
            j.update(status="error", stage="Interrupted by restart. Create a new project to retry.")
        for c in j.get("clips", []):
            if c.get("status") == "rendering":
                c.update(status="error",error="Render interrupted. Please retry.")
        JOBS[j["id"]] = j
    except (ValueError, KeyError):
        pass

app = FastAPI(title="Clipforge", docs_url="/api/docs")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost","127.0.0.1","[::1]","testserver"])

@app.middleware("http")
async def local_only(request: Request, call_next):
    origin = request.headers.get("origin")
    if request.method not in {"GET","HEAD","OPTIONS"} and origin and origin != str(request.base_url).rstrip("/"):
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail":"Requests must come from this local app."},status_code=403)
    return await call_next(request)

class Settings(BaseModel):
    preset: str = "reference"
    style: str = "neon"
    tracking: bool = True
    captions: bool = True
    motion: bool = False
    sfx: bool = False
    enhance: bool = True
    model: str = "small"
    aspect: str = "9:16"
    framing: str = "auto"
    focal_x: float = Field(default=0.5, ge=0, le=1)
    focal_y: float = Field(default=0.5, ge=0, le=1)
    caption_size: int = Field(default=48, ge=24, le=80)
    caption_x: float = Field(default=0.5, ge=0, le=1)
    caption_y: float = Field(default=0.53, ge=0, le=1)
    caption_glow: float = Field(default=0.8, ge=0, le=1)
    caption_animation: str = "float"
    caption_offset: float = Field(default=0, ge=-2, le=2)
    motion_blur: float = Field(default=0, ge=0, le=1)
    caption_mode: str = "style"
    caption_palette: str = "electric"
    word_colors: dict[str, str] = Field(default_factory=dict, max_length=200)
    bar_top: float = Field(default=0, ge=0, le=0.35)
    bar_bottom: float = Field(default=0, ge=0, le=0.35)
    blur_top: float = Field(default=0, ge=0, le=0.45)
    blur_bottom: float = Field(default=0, ge=0, le=0.45)
    blur_strength: int = Field(default=18, ge=2, le=40)
    video_glow: float = Field(default=0, ge=0, le=1)
    length: int = Field(default=30,ge=10,le=90)
    count: int = Field(default=3,ge=1,le=8)

class RenderRequest(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    settings: Settings
    quality: str = "preview"
    retranscribe: bool = False
    transcript: str | None = Field(default=None,max_length=10000)


def validate_settings(s):
    if s.caption_animation not in {"float", "pop", "none"}:
        raise HTTPException(422,"Unknown caption animation.")
    if s.caption_mode not in {"style","phrase","word"} or s.caption_palette not in {"electric","candy","fire","ice"}:
        raise HTTPException(422,"Unknown caption mode or palette.")
    if any(len(k)>100 or not re.fullmatch(r"#[0-9a-fA-F]{6}",v) for k,v in s.word_colors.items()):
        raise HTTPException(422,"Word colors must be valid six-digit hex colors.")
    if s.aspect not in {"3:4","9:16"} or s.framing not in {"auto","safe","fit","center","manual"}:
        raise HTTPException(422,"Unknown layout or framing mode.")
    if s.preset not in PRESETS or s.style not in STYLES or s.model not in {"tiny","base","small"}:
        raise HTTPException(422,"Unknown preset, caption style, or speech model.")


def save(job):
    with LOCK:
        directory = DATA / job["id"]
        directory.mkdir(exist_ok=True)
        temp = directory / "job.tmp"
        temp.write_text(json.dumps(job,ensure_ascii=False))
        temp.replace(directory / "job.json")


def update(job, **fields):
    with LOCK:
        job.update(fields)
        save(job)


def get_job(jid):
    with LOCK:
        if jid not in JOBS:
            raise HTTPException(404,"Project not found.")
        return JOBS[jid]


def youtube_url(value):
    parsed = urlparse(value.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in {"youtube.com","www.youtube.com","m.youtube.com","youtu.be"} or parsed.port not in {None,443}:
        raise ValueError("Paste an https://youtube.com or https://youtu.be video link.")
    video_id = parsed.path.strip("/") if host=="youtu.be" else parse_qs(parsed.query).get("v",[""])[0]
    if parsed.path.startswith(("/shorts/","/embed/")):
        video_id = parsed.path.split("/")[2]
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}",video_id):
        raise ValueError("The link needs a valid YouTube video ID.")
    return "https://www.youtube.com/watch?v=" + video_id


def process(jid, url=None):
    job = get_job(jid)
    folder = DATA / jid
    try:
        if url:
            update(job,stage="Downloading YouTube video",progress=8,status="processing")
            import sys
            run([sys.executable,"-m","yt_dlp","--no-playlist","--max-filesize","2G","--match-filter","duration <= 10800 & !is_live",
                 "--socket-timeout","30","--retries","2","--js-runtimes","node","-f","bv*[height<=2160]+ba/b[height<=2160]",
                 "--merge-output-format","mp4","-o",str(folder / "source.%(ext)s"),url],3600)
            files = [p for p in folder.glob("source.*") if p.suffix not in {".part",".ytdl",".json"}]
            if not files:
                raise ValueError("No video was downloaded. The video may be unavailable, live, or over the size/duration limit.")
            job["source"] = files[0].name
        source = folder / job["source"]
        update(job,stage="Reading video and extracting audio",progress=16,status="processing")
        meta = probe(source)
        thumbnail(source,folder/"poster.jpg",min(1,meta["duration"]/2))
        update(job,meta=meta,poster=f"/api/media/{jid}/poster.jpg")
        audio = folder / "audio.wav"
        segments,words,language = [],[],None
        warnings = []
        if meta["has_audio"]:
            extract_audio(source,audio)
            update(job,stage="Transcribing locally · first use downloads the speech model",progress=27)
            try:
                segments, words, language = transcribe(audio,job["settings"]["model"],DATA/"models")
                if not words:
                    warnings.append("No speech detected. Clips use audio energy and have no captions.")
            except Exception as e:
                warnings.append("Transcription unavailable; clips use audio energy without captions. " + str(e)[:350])
        else:
            warnings.append("Source has no audio. Clips use timeline sampling without captions.")
        update(job,stage="Finding promising moments",progress=48,segments=segments,words=words,language=language,warnings=warnings)
        clips = rank(segments,audio_energy(audio),meta["duration"],job["settings"]["length"],job["settings"]["count"])
        for i, clip in enumerate(clips):
            clip.update(id=str(i+1),status="queued",settings=copy.deepcopy(job["settings"]),revision=0)
        update(job,clips=clips)
        for i, clip in enumerate(clips):
            update(job,stage=f"Reframing and captioning clip {i+1} of {len(clips)}",progress=52+int(i/max(1,len(clips))*44))
            render_clip(job,clip,"preview")
        update(job,status="ready",stage="Your clips are ready",progress=100)
    except Exception as e:
        update(job,status="error",stage="Processing stopped",error=str(e)[-2400:])


def render_clip(job,clip,quality,request=None):
    try:
        with LOCK:
            clip["status"] = "rendering"
            clip.pop("error",None)
            if request:
                changed = (clip["start"] != request.start or clip["end"] != request.end
                           or clip["settings"] != request.settings.model_dump()
                           or request.retranscribe
                           or (request.transcript is not None and request.transcript != clip.get("edited_transcript")))
                if changed:
                    # Keep the approved preview when only export resolution changes.
                    clip.pop("preview",None)
                    clip.pop("export",None)
                clip.update(start=request.start,end=request.end,settings=request.settings.model_dump())
                if request.transcript is not None:
                    clip["edited_transcript"] = request.transcript
            clip["revision"] += 1
            revision = clip["revision"]
            save(job)
        if request and request.retranscribe:
            folder = DATA / job['id'] / 'clips' / clip['id'] / str(revision)
            folder.mkdir(parents=True, exist_ok=True)
            if not job['meta']['has_audio']:
                raise ValueError('This video has no speech audio to transcribe.')
            audio = folder / 'speech.wav'
            run(['ffmpeg','-y','-v','error','-ss',clip['start'],'-i',DATA/job['id']/job['source'],
                 '-t',clip['end']-clip['start'],'-vn','-ar','16000','-ac','1',audio])
            _,fresh_words,_ = transcribe(audio,clip['settings']['model'],DATA/'models')
            if not fresh_words:
                raise ValueError('No speech detected in this range. Existing text was retained.')
            with LOCK:
                clip['words'] = [dict(w,start=w['start']+clip['start'],end=w['end']+clip['start']) for w in fresh_words]
                clip.pop('edited_transcript',None)
                save(job)
        words = clip.get('words',job["words"])
        if "edited_transcript" in clip:
            # Preserve original word timing when the word count matches; otherwise spread
            # replacement words within the selected spoken window, explicitly shown in UI.
            tokens = clip["edited_transcript"].split()
            old = [w for w in words if w["end"]>clip["start"] and w["start"]<clip["end"]]
            if len(tokens)==len(old):
                words = [dict(w,word=t) for w,t in zip(old,tokens)]
            else:
                a,b = (max(clip["start"],old[0]["start"]),min(clip["end"],old[-1]["end"])) if old else (clip["start"],clip["end"])
                step = (b-a)/max(1,len(tokens))
                words = [{"word":t,"start":a+i*step,"end":a+(i+1)*step} for i,t in enumerate(tokens)]
        relative = f"clips/{clip['id']}/{revision}/{quality}"
        result = render(DATA/job["id"]/job["source"],DATA/job["id"]/relative,clip,words,job["meta"],clip["settings"],quality)
        with LOCK:
            clip["preview" if quality=="preview" else "export"] = f"/api/media/{job['id']}/{relative}/video.mp4"
            clip.update(status="ready",framing=result["framing"], render_version=result["render_version"], width=result["width"], height=result["height"], fps=result["fps"])
            if quality!="preview":
                clip["export_quality"] = quality
            save(job)
    except Exception as e:
        with LOCK:
            clip.update(status="error",error=str(e)[-1600:])
            save(job)

@app.get("/api/health")
def health():
    return {"ffmpeg":bool(shutil.which("ffmpeg")),"ffprobe":bool(shutil.which("ffprobe")),"local":True}

@app.get("/api/catalog")
def catalog():
    return {"styles":STYLES,"presets":PRESETS}

@app.get("/api/jobs")
def list_jobs():
    with LOCK:
        return [{k:j.get(k) for k in ("id","name","status","stage","progress","poster")} for j in reversed(list(JOBS.values()))]

@app.get("/api/jobs/{jid}")
def read_job(jid:str):
    with LOCK:
        return copy.deepcopy(get_job(jid))

@app.post("/api/jobs",status_code=202)
async def create_job(file: UploadFile | None = File(default=None),url: str = Form(default=""),settings: str = Form(default="{}")):
    try:
        opts = Settings.model_validate_json(settings)
        validate_settings(opts)
        if bool(file) == bool(url.strip()):
            raise ValueError("Choose either one video upload or one YouTube link.")
        clean_url = youtube_url(url) if url.strip() else None
    except ValueError as e:
        raise HTTPException(422,str(e))
    jid = uuid.uuid4().hex
    folder = DATA / jid
    folder.mkdir()
    name = file.filename if file else "YouTube · " + clean_url.split("=")[-1]
    job = {"id":jid,"name":name,"status":"queued","stage":"Waiting in local queue","progress":0,
           "settings":opts.model_dump(),"clips":[],"words":[],"segments":[],"warnings":[]}
    if file:
        suffix = Path(file.filename or "video.mp4").suffix.lower()
        if suffix not in {".mp4",".mov",".mkv",".webm",".avi",".m4v"}:
            raise HTTPException(422,"Use MP4, MOV, MKV, WebM, AVI, or M4V.")
        job["source"] = "source" + suffix
        target = folder/job["source"]
        size = 0
        try:
            with target.open("wb") as stream:
                while chunk := await file.read(1024*1024):
                    size += len(chunk)
                    if size>2*1024**3:
                        raise HTTPException(413,"Maximum upload size is 2 GB.")
                    stream.write(chunk)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        finally:
            await file.close()
    with LOCK:
        JOBS[jid] = job
        save(job)
    POOL.submit(process,jid,clean_url)
    return {"id":jid}

@app.post("/api/jobs/{jid}/clips/{cid}/render",status_code=202)
def rerender(jid:str,cid:str,body:RenderRequest):
    validate_settings(body.settings)
    job = get_job(jid)
    with LOCK:
        clip = next((c for c in job["clips"] if c["id"]==cid),None)
        if not clip:
            raise HTTPException(404,"Clip not found.")
        if job["status"] != "ready" or clip["status"] == "rendering":
            raise HTTPException(409,"Please wait for the current render.")
        if not body.end>body.start or body.end>job["meta"]["duration"]+0.01 or body.end-body.start>120:
            raise HTTPException(422,"Choose a valid clip range of up to 120 seconds within the source video.")
        if body.quality not in {"preview","720p","1080p"}:
            raise HTTPException(422,"Choose preview, 720p, or 1080p.")
        clip["status"] = "rendering"
        save(job)
    POOL.submit(render_clip,job,clip,body.quality,body)
    return {"ok":True}

@app.post("/api/jobs/{jid}/clips/{cid}/source-preview")
def source_preview(jid: str, cid: str, request: RenderRequest):
    job=JOBS.get(jid)
    clip=next((c for c in job.get('clips',[]) if str(c['id'])==cid),None) if job else None
    if not clip: raise HTTPException(404,"Clip not found")
    a,b=request.start,request.end
    if not 0 < b-a <= 120 or b>job['meta']['duration']:
        raise HTTPException(422,"Invalid preview range")
    # A browser-compatible source proxy, before reframing or captions. Original stays intact.
    name=f"source-preview-{a:.3f}-{b:.3f}.mp4"
    target=DATA/jid/name
    if not target.exists():
        import uuid
        temp=DATA/jid/f"proxy-{uuid.uuid4().hex}.mp4"
        try:
            run(['ffmpeg','-y','-v','error','-ss',a,'-i',DATA/jid/job['source'],'-t',b-a,
                 '-vf',"scale='min(1280,iw)':-2",'-c:v','libx264','-preset','ultrafast','-crf','20',
                 '-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart','-threads','2',temp],300)
            temp.replace(target)
        finally:
            temp.unlink(missing_ok=True)
    return {"url":f"/api/media/{jid}/{name}","offset":a,"end":b}


@app.get("/api/jobs/{jid}/clips/{cid}/framing")
def preview_framing(jid: str, cid: str):
    job=JOBS.get(jid)
    clip=next((c for c in job.get('clips',[]) if str(c['id'])==cid),None) if job else None
    if not clip: raise HTTPException(404,"Clip not found")
    url=clip.get('preview') or clip.get('export')
    if not url: return {"shots":[]}
    relative=url.split(f'/api/media/{jid}/',1)[-1]
    path=(DATA/jid/relative).parent/'tracking.cmd'
    if not path.is_file(): return {"shots":[]}
    return {"shots":[{"time":float(a),"x":float(x)} for a,x in re.findall(r'([\d.]+) crop@reframe x ([\d.]+)',path.read_text())]}


@app.get("/api/media/{jid}/{filename:path}")
def media(jid:str,filename:str,download:bool=False):
    get_job(jid)
    base = (DATA/jid).resolve()
    target = (base/filename).resolve()
    if not target.is_relative_to(base) or not target.is_file() or target.suffix not in {".mp4",".jpg",".mov",".webm",".mkv",".m4v",".avi"}:
        raise HTTPException(404,"Media not found.")
    return FileResponse(target,filename=f"clipforge-{jid[:6]}.mp4" if download and target.suffix==".mp4" else None,
                        content_disposition_type="attachment" if download else "inline")

app.mount("/",StaticFiles(directory=ROOT/"static",html=True),name="web")
