"""En glavni 3D-pogled in prostorski kazalec za bližnje posnetke."""
from osnova import OUT,EXPORT,CACHE,read,save
from studio import Renderer,ortho,unit
from potek import FPS,smooth,screw_phase,states,HANDLE,WHEELS
from orodje import install,driver,weld_props
from PIL import Image,ImageDraw,ImageFont
from functools import lru_cache
import numpy as np
import imageio_ffmpeg as ff
import subprocess,os
from uuid import uuid4

SIZE=(1280,720)
LOC=(212,146)
EYE=np.array([-.83,-1.55,.62])
GLOBAL=(np.array([-6.,0.,911.]),EYE,2260.)
SCALE=Image.Resampling.LANCZOS

def mix(a,b,t):
    ac,ae,aw=a;bc,be,bw=b
    return (np.asarray(ac)*(1-t)+np.asarray(bc)*t,
            unit(unit(np.asarray(ae))*(1-t)+unit(np.asarray(be))*t),aw**(1-t)*bw**t)

def project(cam,size,points):
    m=ortho(*cam,size[0]/size[1])
    pts=np.asarray(points)@m[:2,:3].T+m[:2,3]
    return (pts*[1,-1]+1)*np.array(size)*.5

@lru_cache
def font(size):
    return ImageFont.truetype(os.path.join(os.environ["WINDIR"],"Fonts","seguisb.ttf"),size)

def label(im,title,note):
    d=ImageDraw.Draw(im)
    for y,txt,f in [(24,title,23),(60,note,16)]:
        if not txt:continue
        box=d.textbbox((28,y),txt,font=font(f),anchor="lt")
        d.rounded_rectangle((18,y-7,box[2]+11,box[3]+8),radius=5,fill=(245,247,245))
        d.text((28,y),txt,anchor="lt",font=font(f),fill=(29,47,55))

class Film:
    def __init__(self,r=None):
        self.r=r or Renderer();install(self.r)
        self.st=read(OUT/"koraki.json");self.plans=read(EXPORT/"pogledi.json")
        self.sites=self.r.sites
        self.insert={x["vijak"]:x["id"] for x in read(EXPORT/"vlozki.json")}
        self.logo=Image.open(OUT.parents[4]/"public"/"fines-logo.png").convert("RGBA")
        self.logo.thumbnail((100,29),SCALE)
        self.held={k for st in self.st for k in st.get("zadrzana_mesta",[])}
        self.complete=[k for k in self.r.nodes if k not in self.held]
        self.timetable=[(None,3)]+[(s,s["gibanje"]["trajanje_s"]) for s in self.st]+[(None,3)]
        self.loc_cache={}
        self.welded=[]
        for step,plan in zip(self.st,self.plans):
            if "zvar" not in plan:continue
            z=plan["zvar"];points=np.array(z["tocke_mm"])
            handle=step["gibanje"]["stik"]>=4
            if handle:points+=np.array([110,0,0])
            self.welded.append((step["st"],handle,weld_props(points,z["smer"],1,False)))
    def bounds(self,ids):
        return np.min([self.r.boxes[k][0] for k in ids],axis=0),np.max([self.r.boxes[k][1] for k in ids],axis=0)
    def locator(self,im,ids,point,changes):
        # A constant overview orientation preserves front/back and level between shots.
        cad=tuple(k for k in ids if k.startswith("P"))
        key=(cad,tuple((k,tuple(changes[k][0])) for k in cad if k in changes))
        cam=([0,0,910],EYE,1830.)
        if key not in self.loc_cache:self.loc_cache[key]=self.r.view(cad,cam,LOC,changes)
        loc=self.loc_cache[key].copy()
        d=ImageDraw.Draw(loc);x,y=project(cam,LOC,[point])[0]
        for radius,col,width in [(7,"white",4),(6,"#c34819",2),(2,"#c34819",2)]:
            d.ellipse((x-radius,y-radius,x+radius,y+radius),outline=col,width=width)
        x0=SIZE[0]-LOC[0]-18;y0=SIZE[1]-LOC[1]-17
        ImageDraw.Draw(im).rounded_rectangle((x0-2,y0-2,x0+LOC[0]+1,y0+LOC[1]+1),radius=4,fill="#cbd2d3")
        im.paste(loc,(x0,y0))
    def frame(self,st,t,finish=False):
        if st is None:
            ids=self.complete if finish else self.r.cad
            all_beads=[geom for _,_,bead in self.welded for geom in bead] if finish else []
            im=self.r.view(ids,GLOBAL,SIZE,extras=all_beads)
            label(im,"Mali delovni voziček","Predlog montaže" if not finish else "Predlog sestava")
            im.paste(self.logo,(SIZE[0]-self.logo.width-22,24),self.logo)
            return im
        plan=self.plans[st["st"]-1]
        g=st["gibanje"];mode=g["tip"];ids=list(plan["sestav"])
        changes=states(st,t/g["trajanje_s"],self.sites)
        changes.update({k:(np.array(d),0.) for k,d in plan.get("odmiki_mm",{}).items()})
        extras=[];cut=None;marker=None;note="";blocked=None
        if mode=="premik":
            lo,hi=self.bounds(st["deli"]);center=(lo+hi)/2
            if st["deli"]==WHEELS:
                cam=(center+[0,0,48],[-.62,-1,-.34],1510)
            elif st["naslov"]=="Ročaj":
                cam=(center+[40,0,0],[-1,-.70,.25],970)
            else:cam=(center,EYE,1535)
            cam=mix(GLOBAL,cam,smooth(t/1.25)*.89)
            marker=center
        elif mode=="var":
            info=plan["zvar"];pts=np.asarray(info["tocke_mm"]);eye=np.array(info["smer"])
            center=pts.mean(0);marker=center
            local=(center,eye,info["sirina_mm"])
            cam=mix(GLOBAL,local,smooth((t-.15)/1.25))
            progress=smooth((t-1.55)/2.65)
            extras=weld_props(pts,eye,progress,1.36<t<4.42)
            note="Predlog zvara"
        else:
            i,phase=screw_phase(st,t)
            pid=st["deli"][i];site=self.sites[pid];view=plan["mesta"][i]
            recent=[k for k in st["deli"][:i+1] if k not in self.held]
            ids.extend(recent);ids.extend(self.insert[k] for k in recent if k in self.insert)
            # Future fasteners first appear on their own turn.
            delta,angle=changes.get(pid,(np.zeros(3),0.))
            changes={} if pid in self.held else {pid:(delta,angle)}
            marker=np.array(site["stik_mm"])
            center=np.array(view["center_mm"]);eye=np.array(view["smer"]);span=view["sirina_mm"]
            cut=view["prerez"];local=(center,eye,span)
            if t<2.:
                cam=mix(GLOBAL,local,smooth((t-.18)/1.57))
            elif i and phase<.55:
                prev=plan["mesta"][i-1]
                prev_cam=(prev["center_mm"],prev["smer"],prev["sirina_mm"])
                dist=np.linalg.norm(center-np.array(prev["center_mm"]))
                # Keep nearby holes connected by a pan. A new edge starts on a wider view.
                if dist<110 and np.dot(prev["smer"],eye)>.5:
                    cam=mix(prev_cam,local,smooth(phase/.55))
                else:cam=mix((center,eye,span*2.4),local,smooth(phase/.55))
            else:cam=local
            extras=driver(site,delta,angle,phase) if t>=2 else []
            if g["skupina"]=="kolesa":note="Plošča brez izvrtine • preveri risbo"
            elif cut:note="Prerez cevi • predlog pritrditve"
            else:note="Predlog pritrditve"
            if pid in self.held:
                blocked=pid;extras=[]
                note="Dostop ovira kolo • preveri izvedbo"
        for number,handle,bead in self.welded:
            if number>=st["st"]:continue
            if handle and HANDLE[0] in changes:
                shift=changes[HANDLE[0]][0]
                for name,m in bead:
                    m=m.copy();m[:3,3]+=shift;extras.append((name,m))
            else:extras.extend(bead)
        im=self.r.view(ids,cam,SIZE,changes,extras,cut)
        if blocked:
            # Screen-space ring locates the measured opening; the screw is illustrated outside the assembly.
            x,y=project(cam,SIZE,[view["oznaka_reze_mm"]])[0]
            draw=ImageDraw.Draw(im);radius=15+2*np.cos(phase*np.pi)
            draw.ellipse((x-radius,y-radius,x+radius,y+radius),outline="white",width=5)
            draw.ellipse((x-radius,y-radius,x+radius,y+radius),outline="#c34819",width=2)
            if not hasattr(self,"sample"):
                sample_cam=(np.array(site["glava_mm"])+[0,0,5],[.5,-1,-.20],45)
                self.sample=self.r.view([pid],sample_cam,(154,112))
            im.paste(self.sample,(18,SIZE[1]-140))
            draw.text((27,SIZE[1]-40),"Predlagani vijak",font=font(16),fill=(29,47,55))
        if mode!="premik" and (mode=="vijak" and t>1 or mode=="var" and t>.9):
            self.locator(im,ids,marker,changes)
        label(im,st["naslov"],note)
        im.paste(self.logo,(SIZE[0]-self.logo.width-22,24),self.logo)
        return im
    def proof(self):
        rows=[self.frame(None,0)]
        rows[0].save(OUT/"predogled.png")
        for st in self.st:
            rows.append(self.frame(st,3.5 if st["gibanje"]["tip"]=="vijak" else 2.9))
        filmstrip(rows,EXPORT/"pregled_kamere.jpg")
    def encode(self):
        CACHE.mkdir(exist_ok=True)
        filename=CACHE/"brez_poglavij.mp4"
        cmd=[ff.get_ffmpeg_exe(),"-hide_banner","-loglevel","error","-y","-f","rawvideo","-pix_fmt","rgb24",
             "-s","1280x720","-r",str(FPS),"-i","pipe:0","-an","-c:v","libx264","-preset","veryfast",
             "-crf","17","-pix_fmt","yuv420p","-movflags","+faststart",str(filename)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        start=0;timeline=[]
        try:
            for index,(st,seconds) in enumerate(self.timetable):
                still=None
                for j in range(seconds*FPS):
                    if st is None and still is not None:raw=still
                    else:raw=self.frame(st,j/FPS,finish=index==len(self.timetable)-1).tobytes()
                    if st is None:still=raw
                    proc.stdin.write(raw)
                timeline.append(dict(st=st["st"] if st else None,od_s=start,do_s=start+seconds))
                start+=seconds;print("MP4",start,st["naslov"] if st else "Sestav",flush=True)
        finally:
            proc.stdin.close();code=proc.wait()
        if code:raise RuntimeError("FFmpeg: "+str(code))
        save(EXPORT/"casovnica.json",timeline)
        save(EXPORT/"kontrola_glb.json",self.r.qa)
        self.chapters(filename)

    def chapters(self, filename):
        timeline=read(EXPORT/"casovnica.json")
        fields=[";FFMETADATA1"]
        for i,item in enumerate(timeline):
            name=self.st[item["st"]-1]["naslov"] if item["st"] else ("Sestav" if i==0 else "Pregled sestava")
            fields.extend(["[CHAPTER]","TIMEBASE=1/1000","START="+str(item["od_s"]*1000),
                "END="+str(item["do_s"]*1000),"title="+name])
        CACHE.mkdir(exist_ok=True)
        meta=CACHE/"poglavja.ffmeta";meta.write_text("\n".join(fields)+"\n",encoding="utf-8")
        # NTFS retains the source ACL on rename. Create the published file in OUT.
        out=OUT/f".video-{uuid4().hex}.mp4"
        try:
            subprocess.run([ff.get_ffmpeg_exe(),"-v","error","-n","-i",str(filename),"-f","ffmetadata",
                "-i",str(meta),"-map","0:v:0","-map_chapters","1","-c:v","copy","-movflags","+faststart",str(out)],check=True)
            out.replace(OUT/"video.mp4")
        finally:
            out.unlink(missing_ok=True)

def filmstrip(images,path):
    w,h=320,180;cols=4
    img=Image.new("RGB",(cols*w,((len(images)+cols-1)//cols)*h),"#e9eeed")
    for i,v in enumerate(images):img.paste(v.resize((w,h),SCALE),(i%cols*w,i//cols*h))
    img.save(path,quality=91)

if __name__=="__main__":
    import sys
    film=Film();film.proof()
    if "--pregled" not in sys.argv:film.encode()
