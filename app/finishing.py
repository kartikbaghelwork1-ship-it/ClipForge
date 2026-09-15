"""User-controlled glow, blur strips, and black bars, before caption compositing."""
def finish_graph(graph, source, width, height, settings):
    current=source
    motion=settings.get('motion_blur',0)
    if motion:
        graph.append(f"[{current}]tmix=frames=3:weights='1 {motion*.35:.3f} {motion*.15:.3f}'[motion_soft]")
        current='motion_soft'
    glow=settings.get('video_glow',0)
    if glow:
        graph.append(f'[{current}]split=2[glow_base][glow_src]')
        graph.append(f'[glow_src]gblur=sigma={max(2,width/90):.2f}[glow_soft]')
        graph.append(f'[glow_base][glow_soft]blend=all_mode=screen:all_opacity={glow*.40:.3f}[bloomed]')
        current='bloomed'
    for edge in ['top','bottom']:
        amount=settings.get('blur_'+edge,0)
        if amount<=0: continue
        h=max(2,int(height*amount)//2*2)
        y=0 if edge=='top' else height-h
        graph.append(f'[{current}]split=2[base_{edge}][strip_{edge}]')
        graph.append(f'[strip_{edge}]crop={width}:{h}:0:{y},gblur=sigma={max(2,settings.get("blur_strength",18)*width/720):.2f}[soft_{edge}]')
        graph.append(f'[base_{edge}][soft_{edge}]overlay=0:{y}:shortest=1[blurred_{edge}]')
        current='blurred_'+edge
    bars=[]
    for edge in ['top','bottom']:
        amount=settings.get('bar_'+edge,0)
        if amount>0:
            h=max(2,round(height*amount))
            y=0 if edge=='top' else height-h
            bars.append(f'drawbox=x=0:y={y}:w=iw:h={h}:color=black:t=fill')
    if bars:
        graph.append(f'[{current}]'+','.join(bars)+'[barred]')
        current='barred'
    return current
