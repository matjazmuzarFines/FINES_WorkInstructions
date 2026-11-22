"""Izbor dostopnega pogleda na podlagi globine celotnega trenutno sestavljenega modela."""
from osnova import OUT, EXPORT,read,save
from studio import Renderer,ortho,unit
from potek import FRAME,HANDLE
import numpy as np
from itertools import product
from math import sin,cos,pi

def visibility(renderer, ids, cam, points, cut=None):
    depth=renderer.depth_image(ids,cam,cut=cut)
    return test_depth(depth,cam,points)

def test_depth(depth,cam,points):
    h,w=depth.shape
    p=np.asarray(points)@ortho(*cam,w/h)[:3,:3].T+ortho(*cam,w/h)[:3,3]
    xy=(p[:,:2]+1)*[w/2,h/2]
    x,y=xy.astype(int).T
    inside=(x>0)&(y>0)&(x<w-1)&(y<h-1)
    x=x.clip(1,w-2);y=y.clip(1,h-2)
    # Depth tolerance in mm. The neighbourhood median damps single-pixel edges.
    near=np.median([depth[y,x],depth[y-1,x],depth[y+1,x],depth[y,x-1],depth[y,x+1]],axis=0)
    return inside & (((p[:,2]+1)*.5-near)*8000 < .55)

def make_plan(r):
    steps=read(OUT/"koraki.json")
    seams=read(EXPORT/"stiki_ogrodja.json")
    inserts={i["vijak"]:i["id"] for i in read(EXPORT/"vlozki.json")}
    assembled=list(FRAME)
    plans=[]
    for st in steps:
        g=st["gibanje"];mode=g["tip"]
        if mode=="premik":assembled.extend(k for k in st["deli"] if k not in assembled)
        if mode=="var" and g["stik"]==4:assembled.extend(HANDLE)
        plan=dict(st=st["st"],sestav=list(assembled),mesta=[])
        if mode=="var":
            seam=seams[g["stik"]]
            edges=np.array(seam["kandidati_mm"])
            offsets={}
            if g["stik"]>=4:
                offsets={k:[-110,0,0] for k in HANDLE}
                plan["odmiki_mm"]=offsets
                edges+=np.array([-110,0,0])
            origin=edges.reshape(-1,3).mean(0)
            best=None
            for az,elev in product(range(0,360,45),[-50,-23,22,52,76]):
                a,b=np.deg2rad([az+13,elev]);eye=np.array([cos(a)*cos(b),sin(a)*cos(b),sin(b)])
                cam=(origin,eye,200)
                depth=r.depth_image(assembled,cam,offsets=offsets)
                for points in edges:
                    vis=test_depth(depth,cam,points)
                    groups=np.split(np.where(vis)[0],np.where(np.diff(np.where(vis)[0])!=1)[0]+1)
                    for group in groups:
                        if len(group)<5:continue
                        pts=points[group]
                        ds=np.diff(pts,axis=0)
                        length=np.linalg.norm(ds,axis=1).sum()
                        screen=np.linalg.norm(ds-(ds@eye)[:,None]*eye,axis=1).sum()
                        score=screen*(.9+.1*max(0.,eye[2]))
                        if best is None or score>best[0]:
                            best=(score,pts,eye,length)
            if best is None or best[0]<3:raise ValueError(seam["ime"])
            score,pts,eye,length=best
            plan["zvar"]=dict(tocke_mm=pts.tolist(),smer=eye.tolist(),dolzina_mm=round(length,2),vidni_vzorci=len(pts),
                              sirina_mm=max(91,min(245,length*2.2+48)))
        if mode=="vijak":
            for pid in st["deli"]:
                s=r.sites[pid];axis=np.array(s["os"]);head=np.array(s["glava_mm"])
                if pid in inserts:assembled.append(inserts[pid])
                cut=(s["nosilec"],s["stik_mm"]) if s["skupina"]=="spodnja" else None
                # Test the screw head and exposed shank in multiple poses, plus the driver.
                distances=np.array([2,4,7,12,17,24,35,52])
                points=head-distances[:,None]*axis
                if s["skupina"]=="kolesa":
                    lo,hi=r.boxes[s["nosilec"]]
                    center=.76*((lo+hi)/2)+.24*head
                    span=334
                else:center=head-axis*16;span=139
                pref=unit(np.array([-.78,-.92,-.48]))
                best=None
                for az,elev in product(range(0,360,45),[-65,-30,-12,18,42,68]):
                    a,b=np.deg2rad([az+10,elev]);eye=np.array([cos(a)*cos(b),sin(a)*cos(b),sin(b)])
                    alignment=-eye@axis
                    if alignment<.12 or alignment>.97:continue
                    cam=(center,eye,span)
                    visible=visibility(r,assembled,cam,points,cut)
                    score=visible.sum()*10+float(visible[0])*5-abs(alignment-.47)*2+eye@pref*.38
                    stopped=pid in st.get("zadrzana_mesta",[])
                    mark=np.array(s["stik_mm"])-axis*3.0
                    if stopped:
                        visible_mark=bool(visibility(r,assembled,cam,[mark])[0])
                        score+=200*visible_mark
                    if best is None or score>best[0]:best=(score,eye,visible)
                _,eye,visible=best
                plan["mesta"].append(dict(id=pid,smer=eye.tolist(),center_mm=center.tolist(),sirina_mm=span,
                    vidne_sonde=visible.astype(int).tolist(),prerez=cut))
                if pid in st.get("zadrzana_mesta",[]):
                    assert best[0]>200, (pid,"reža ni vidna")
                    plan["mesta"][-1]["oznaka_reze_mm"]=mark.tolist()
                if pid not in st.get("zadrzana_mesta",[]):assembled.append(pid)
        plans.append(plan)
        print(st["naslov"],(plan.get("zvar") or {}).get("dolzina_mm"),[(s["id"],sum(s["vidne_sonde"])) for s in plan["mesta"]],flush=True)
    held={k for st in steps for k in st.get("zadrzana_mesta",[])}
    assert len(assembled)==len(set(assembled)) and set(assembled)==set(r.nodes)-held
    save(EXPORT/"pogledi.json",plans)
    for st,p in zip(steps,plans):
        st["kamera"]["podatki"]="izvoz/pogledi.json"
        st["kamera"]["stanje_sestava"]=p["sestav"]
    save(OUT/"koraki.json",steps)
    return plans

if __name__=="__main__":make_plan(Renderer())
