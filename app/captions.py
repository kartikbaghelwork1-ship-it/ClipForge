"""Readable, phrase-stable captions with word accents, not bouncing single words."""
import re
from .catalog import STYLES


def stamp(t):
    n=max(0,round(t*100))
    return f'{n//360000}:{n//6000%60:02}:{n//100%60:02}.{n%100:02}'


def escape(text):
    return text.replace('\\','＼').replace('{','(').replace('}',')').replace('\n',' ').strip()


def ass_color(value):
    s=value.lstrip('#')
    return '&H00'+s[4:6]+s[2:4]+s[0:2]


def group_words(words,start,end,size=40):
    selected=[]
    for w in sorted(words,key=lambda w:w['start']):
        if w['end']<=start or w['start']>=end: continue
        a=max(start,w['start'])-start
        b=min(end,w['end'])-start
        if b>a: selected.append(dict(w,start=a,end=b))
    groups=[]; group=[]
    # Conservative character budget for bold uppercase letters; at most two lines.
    budget=max(14,int(620/(size*.65)))
    for w in selected:
        candidate=' '.join(x['word'] for x in group+[w])
        if group and (len(group)>=5 or len(candidate)>budget*1.65 or
                      w['start']-group[-1]['end']>.35 or w['end']-group[0]['start']>2.2 or
                      re.search(r'[.!?]$',group[-1]['word'])):
            groups.append(group);group=[]
        group.append(w)
    if group: groups.append(group)
    return groups,budget


def emphasis(word,default):
    token=re.sub(r'[^a-z]','',word.lower())
    if token in {'no','not','never','lost','lose','stop','embarrass','bad','wrong','crazy'}: return '#FF4343'
    if token in {'best','win','won','yes','great','good','amazing'}: return '#92FF39'
    if token in {'twice','two','three','how','why','what'}: return '#55EAFF'
    return default


PALETTES={
    'electric':['#FAFF00','#FFFFFF','#39FF14','#FF3434','#51EDFF','#FF00D9'],
    'candy':['#FF00D9','#B26BFF','#50E9FF','#FFFFFF'],
    'fire':['#FF3434','#FF8C00','#FFED38','#FFFFFF'],
    'ice':['#55EFFF','#7AA5FF','#FFFFFF','#C595FF'],
}


def word_key(word):
    return re.sub(r'[^\w]','',word.lower())


def write_ass(words,start,end,style_id,path,settings=None,canvas_height=1280):
    settings=settings or {}
    style=STYLES[style_id]
    size=settings.get('caption_size',style.get('size',48))
    position=round(canvas_height*settings.get('caption_y',.53))
    horizontal=round(720*settings.get('caption_x',.5))
    animation=style['animation'];accent=style['color']
    glowing=animation in {'glow','single','solid_glow','lines_glow'}
    font='Montserrat ExtraBold' if glowing else 'Arial'
    boxed=animation=='box'
    header=f'''[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: {canvas_height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00202020,&H85000000,-1,0,0,0,100,100,{0.6 if glowing else 0},0,{3 if boxed else 1},{0.7 if glowing else (6 if boxed else 2.2)},0.8,5,55,55,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    offset=settings.get('caption_offset',0)
    words=[dict(w,start=w['start']+offset,end=w['end']+offset) for w in words]
    groups,budget=group_words(words,start,end,size)
    movement=settings.get('caption_animation','float')
    single=settings.get('caption_mode','style')=='word' or (animation=='single' and settings.get('caption_mode','style')!='phrase')
    if single: groups=[[w] for g in groups for w in g]
    lines=[];palette=PALETTES[settings.get('caption_palette','electric')]
    overrides=settings.get('word_colors',{})
    word_offset=0
    for gi,group in enumerate(groups):
        a=group[0]['start'];b=min(end-start,group[-1]['end']+.08)
        if gi+1<len(groups): b=min(b,groups[gi+1][0]['start'])
        tokens=[escape(w['word']).upper() for w in group]
        total=len(' '.join(tokens));split=None
        if (total>budget or animation=='lines_glow') and len(tokens)>1:
            split=min(range(1,len(tokens)),key=lambda i:abs(len(' '.join(tokens[:i]))-len(' '.join(tokens[i:]))))
        max_line=max(len(' '.join(tokens[:split])),len(' '.join(tokens[split:]))) if split else total
        shrink=min(size,max(18,int(size*budget/max(budget,max_line))))
        def phrase(active,layer):
            strength=settings.get('caption_glow',.8)
            if layer==0:
                tags=f'{{\\bord{5+5*strength:.1f}\\blur{7+9*strength:.1f}\\shad0\\alpha&H80&}}'
            elif layer==1:
                tags=f'{{\\bord{1+2*strength:.1f}\\blur{2+3*strength:.1f}\\shad0\\alpha&H40&}}'
            else:
                tags=r'{\bord0.7\blur0\shad1\alpha&H00&}' if glowing else ''
            pieces=[f'{{\\fs{shrink}}}'+tags]
            for i,token in enumerate(tokens):
                if animation in {'glow','single'}:
                    c=palette[(word_offset+i)//2%len(palette)] if not single else palette[(word_offset+i)%len(palette)]
                elif animation=='solid_glow': c=accent
                elif animation=='lines_glow': c='#FFFFFF' if split and i<split else accent
                elif style_id=='reference': c=emphasis(token,accent) if i==active else '#FFFFFF'
                else: c=accent if i==active else '#FFFFFF'
                c=overrides.get(word_key(group[i]['word']),c)
                outline=c if layer<2 else '#161616'
                pieces.append('{\\1c'+ass_color(c)+'\\3c'+ass_color(outline)+'}')
                if (animation=='type' or movement!='none') and active is not None:
                    pieces.append(r'{\alpha&HFF&}' if i>active else ('{\\alpha&H'+('80' if layer==0 else '40' if layer==1 else '00')+'&}'))
                pieces.append(token)
                if i+1<len(tokens):pieces.append(r'\N' if split==i+1 else ' ')
            return ''.join(pieces)
        def add(a,b,active):
            if b<=a:return
            layers=[0,1,2] if glowing and settings.get('caption_glow',.8)>0 else [2]
            entrance=min(160,max(10,round((b-a)*1000)))
            placement=f'\\pos({horizontal},{position})'
            if movement=='float': placement=f'\\move({horizontal},{position+12},{horizontal},{position},0,{entrance})\\fad(45,0)'
            elif movement=='pop': placement=f'\\pos({horizontal},{position})\\fscx92\\fscy92\\t(0,{entrance},\\fscx100\\fscy100)\\fad(35,0)'
            for layer in layers:
                lines.append(f'Dialogue: {layer},{stamp(a)},{stamp(b)},Main,,0,0,0,,{{\\an5{placement}}}'+phrase(active,layer))
        if glowing and movement=='none':
            add(a,b,None)
        elif movement!='none' or animation in {'reference','pop','impact','karaoke','type'}:
            for i,w in enumerate(group):
                stop=group[i+1]['start'] if i+1<len(group) else b
                add(w['start'],stop,i)
        else: add(a,b,None)
        word_offset+=len(group)
    path.write_text(header+'\n'.join(lines)+'\n',encoding='utf-8')
