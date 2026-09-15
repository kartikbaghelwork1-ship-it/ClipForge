"""Shot-locked framing. Never chase individual detections across a frame.
Uncertain / group shots retain the complete image instead of losing people.
"""
import cv2
import numpy as np


def choose_center(detections, width, crop_width):
    """Return a fixed focal point and confidence for a shot."""
    valid = [faces for faces in detections if len(faces)]
    if not valid or len(valid) < len(detections)*0.5:
        return width/2, False
    centers, extents = [], []
    for faces in valid:
        largest = max(f[2]*f[3] for f in faces)
        # Ignore tiny background faces, retain similarly sized foreground people.
        primary = [f for f in faces if f[2]*f[3] >= largest*.42]
        left = min(f[0] for f in primary)
        right = max(f[0]+f[2] for f in primary)
        centers.append((left+right)/2)
        extents.append(right-left)
    center = float(np.median(centers))
    # Face width plus breathing room must fit, including subject movement.
    spread = float(np.percentile(centers,90)-np.percentile(centers,10))
    reliable = np.percentile(extents,90)*1.65 + spread < crop_width*.9
    return center, bool(reliable)


def plan_framing(source, start, duration, meta, settings, aspect):
    width,height = meta['width'],meta['height']
    cw = max(2,min(width,int(height*aspect))//2*2)
    ch = max(2,min(height,int(cw/aspect))//2*2)
    mode = settings.get('framing','auto')
    fixed = max(0,min(width-cw,settings.get('focal_x',.5)*width-cw/2))
    default = {'start':0.,'end':duration,'x':fixed,'fit':False}
    if mode=='fit':
        return cw,ch,[dict(default,fit=True)],'Full scene'
    if mode in {'center','manual'} or not settings.get('tracking',True):
        return cw,ch,[default],'Manual crop' if mode=='manual' else 'Center crop'
    if abs(width/height-aspect)<.025:
        return cw,ch,[default],'Original framing'
    cap=cv2.VideoCapture(str(source))
    fps=cap.get(cv2.CAP_PROP_FPS) or 30
    cap.set(cv2.CAP_PROP_POS_MSEC,start*1000)
    cascade=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    shots=[]; detections=[]; previous=None; shot_start=0.; frame_index=0
    sample_stride=max(1,round(fps/10)); face_stride=max(1,round(fps/3))
    found=0
    def finish(end):
        center,reliable=choose_center(detections,width,cw)
        x=max(0,min(width-cw,center-cw/2))
        shots.append({'start':shot_start,'end':end,'x':x,'fit':mode=='safe' and not reliable})
    try:
        while frame_index/fps < duration:
            ok,frame=cap.read()
            if not ok: break
            t=frame_index/fps
            cut=False
            if frame_index%sample_stride==0:
                small=cv2.resize(frame,(160,90))
                if previous is not None:
                    diff=float(np.mean(cv2.absdiff(small,previous)))
                    cut=diff>46 and t-shot_start>.65
                previous=small
            if cut:
                finish(t);detections=[];shot_start=t
            if cut or frame_index%face_stride==0:
                ratio=min(1.,640/frame.shape[1])
                scaled=cv2.resize(frame,None,fx=ratio,fy=ratio)
                boxes=cascade.detectMultiScale(cv2.cvtColor(scaled,cv2.COLOR_BGR2GRAY),1.1,6,minSize=(30,30))
                boxes=[tuple(float(v)/ratio for v in f) for f in boxes]
                detections.append(boxes)
                found+=bool(boxes)
            frame_index+=1
        finish(duration)
    finally:
        cap.release()
    label='Fill · shot-locked crop' if all(not s['fit'] for s in shots) else 'Full scene / safe crop'
    return cw,ch,shots,label


def make_track(source,start,duration,meta,path,enabled=True):
    # Compatibility entry point for callers of the original tracking module.
    cw,ch,shots,label=plan_framing(source,start,duration,meta,{'tracking':enabled},9/16)
    path.write_text('\n'.join(f"{s['start']:.3f} crop@reframe x {s['x']:.2f};" for s in shots))
    return cw,ch,(meta['height']-ch)//2,int(label=='Stable face crop')
