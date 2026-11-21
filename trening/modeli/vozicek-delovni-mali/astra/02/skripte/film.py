import os,subprocess,textwrap
from functools import lru_cache
from osnova import OUT,EXPORT,CACHE,read,save
from potek import FPS,WHEELS,motion,states
from studio import Renderer,ortho
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg

W,H=1920,1080
PAPER="#f9f8f3";INK="#182f32";MUTED="#4c6262";GREEN="#136e66";RULE="#c9d1ca";GOLD="#af5d26";BG="#ec ef ed".replace(" ","")
X,Y,SW,SH=535,134,1336,796
ALL=([-5,0,900],[-.66,-1,.46],2220)

@lru_cache
def font(size,style="body"):
    name={"body":"segoeui.ttf","bold":"segoeuib.ttf","mono":"consola.ttf","title":"georgiab.ttf"}[style]
    return ImageFont.truetype(os.path.join(os.environ["WINDIR"],"Fonts",name),size)
def text(d,xy,s,size=24,color=INK,style="body"):
    d.text(xy,s,font=font(size,style),fill=color,anchor="lt")
def wrap(d,x,y,s,width,size=26,color=INK,style="body"):
    line=""
    for word in s.split():
        candidate=(line+" "+word).strip()
        if line and d.textlength(candidate,font=font(size,style))>width:
            text(d,(x,y),line,size,color,style);y+=size+12;line=word
        else:line=candidate
    if line:text(d,(x,y),line,size,color,style);y+=size+12
    return y

def bounds_center(parts,pid):
    b=parts[pid]["bbox_mm"]
    return (np.array(b["min"])+b["max"])/2

def projected(cam,size,xyz):
    w,h=size
    v=ortho(cam[0],cam[1],cam[2],w/h)@np.append(xyz,1.)
    return ((1+v[0])*w/2,(1-v[1])*h/2)


class Film:
    def __init__(self):
        self.r=Renderer();self.steps=read(OUT/"koraki.json");self.parts={p["id"]:p for p in read(OUT/"deli.json")}
        self.sites=self.r.sites
        self.inserts={x["vijak"]:x["id"] for x in read(EXPORT/"vlozki.json")}
        self.scene_cache={}
        self.timeline=[(None,3)]+[(s,s["gibanje"]["trajanje_s"]) for s in self.steps]+[(None,3)]
    def tile(self,im,box,ids,cam,changes,label="",flange=False,lines=None,cut=None):
        x,y,w,h=box
        key=(tuple(ids),str(cam),w,h,flange,str(cut))
        varying=any(pid in changes for pid in ids)
        if key in self.scene_cache and not varying:
            view=self.scene_cache[key].copy()
        else:
            view=self.r.view(ids,cam,(w,h),changes,flange,cut)
            if not varying:self.scene_cache[key]=view.copy()
        dr=ImageDraw.Draw(view)
        if lines:
            for pts in lines:
                coords=[projected(cam,(w,h),pt) for pt in pts]
                if len(coords)>1:dr.line(coords,fill="#ffa540",width=5,joint="curve")
                px,py=coords[-1];dr.ellipse((px-7,py-7,px+7,py+7),fill="#ffcb67",outline="#76451c",width=2)
        if label:
            length=dr.textlength(label,font=font(20,"mono"))
            dr.rounded_rectangle((17,15,41+length,50),5,fill="#fbfaf4")
            text(dr,(29,23),label,20,GREEN,"mono")
        im.paste(view,(x,y))
    def diagram(self,dr,sites,kind):
        x,y,w,h=54,578,420,209
        text(dr,(x,y),"RAZPORED MEST",17,GREEN,"mono")
        if not sites:return
        coords=np.array([s["stik_mm"] for s in sites])
        axes=[0,1] if kind!="rocaj" else [1,2]
        a=coords[:,axes];lo=a.min(0);hi=a.max(0);span=np.maximum(hi-lo,[1,1])
        if kind in ("kolesa","poravnava"):
            # Expand the very small footprint of each flange for a legible four-hole symbol.
            cx=np.sign(a[:,0])*345;cy=np.sign(a[:,1])*112
            mids=np.array([np.mean(a[[t["nosilec"]==s["nosilec"] for t in sites]],axis=0) for s in sites])
            a=np.column_stack((cx,cy))+(a-mids)*1.25
            lo=a.min(0);hi=a.max(0);span=hi-lo
        px=x+21+(a[:,0]-lo[0])/span[0]*(w-42)
        py=y+50+(hi[1]-a[:,1])/span[1]*(h-92)
        dr.rounded_rectangle((x+10,y+40,x+w-10,y+h-30),radius=8,outline=RULE,width=2)
        for s,b,c in zip(sites,px,py):
            # Elevation and edge holes on shelves are distinguished by marker shape.
            if s["os"][2]:
                dr.ellipse((b-5,c-5,b+5,c+5),fill=GOLD)
            else:dr.rectangle((b-4,c-4,b+4,c+4),fill=GREEN)
        caption="Krog · od spodaj    Kvadrat · s strani" if kind in ("srednja","zgornja") else "Položaji na sestavu · shema"
        text(dr,(x,y+h-13),caption,18,MUTED)
    def base(self,step,finish=False):
        im=Image.new("RGB",(W,H),PAPER);d=ImageDraw.Draw(im)
        text(d,(53,39),"FINES",34,INK,"bold")
        d.line((178,38,178,78),fill=RULE,width=2)
        text(d,(204,49),"TEHNIČNA NAVODILA  /  MALI DELOVNI VOZIČEK",23,GREEN,"mono")
        d.text((W-49,52),"MLU123069200   /   ASTRA 02",font=font(20,"mono"),fill=MUTED,anchor="rt")
        d.line((52,103,W-50,103),fill=RULE,width=2)
        if step:
            text(d,(52,147),f"PRIKAZ {step['st']:02} / {len(self.steps):02}",22,GREEN,"mono")
            y=wrap(d,49,201,step["naslov"],452,48,INK,"title")
            y=wrap(d,52,y+31,step["opis"],427,27,INK)
            key=step["kljuc"]
            sites=[s for s in self.sites.values() if s["skupina"]==("kolesa" if key=="poravnava" else key)]
            if sites:self.diagram(d,sites,key)
            elif key.startswith("zvar") or key in ("okvir","stiki"):
                text(d,(52,608),"OZNAČENI STIK",18,GREEN,"mono")
                d.line((53,663,144,663),fill="#f0a245",width=6);d.ellipse((134,653,154,673),fill="#ffcb67",outline=GOLD,width=2)
                wrap(d,52,705,"Svetla sled pokaže mesto spoja. Obliko zvara določa risba.",419,23,MUTED)
            elif key=="prerez":
                text(d,(52,608),"MERITEV V MODELU",18,GREEN,"mono");text(d,(52,657),"16 od 16 osi",32,INK,"bold")
                wrap(d,52,723,"Na treh globinah v nosilni plošči je CAD potrdil poln material.",422,24,MUTED)
            else:
                text(d,(52,608),"POLICA IZ IVERALA",18,GREEN,"mono");text(d,(52,657),"993 × 493 × 18 mm",30,INK,"bold")
            text(d,(52,859),step["prikaz"],19,GREEN,"mono")
            foot=step["opozorila"][0]
        else:
            text(d,(52,147),"MONTAŽNI PREGLED",22,GREEN,"mono")
            wrap(d,48,211,"Mali delovni voziček",438,53,INK,"title")
            wrap(d,52,410,"Stiki ogrodja, pritrditev štirih koles, ročaja in treh polic.",424,30)
            text(d,(52,624),"VIR GEOMETRIJE",18,GREEN,"mono");text(d,(52,666),"28 delov  /  92 teles",30,INK,"bold")
            wrap(d,52,738,"Bakrena barva označuje predlagane vijake. Turkizna označuje možne vložke.",426,23,MUTED)
            foot="Pred izdajo v proizvodnjo potrdi pritrdila, podpiranje, tolerance in zaporedje."
        d.line((52,959,W-50,959),fill=RULE,width=2)
        text(d,(52,989),"ZA POTRDITEV",18,GREEN,"mono")
        wrap(d,270,987,foot,1570,23,MUTED)
        return im
    def layout(self,step,p=1,finish=False):
        im=self.base(step,finish)
        if not step:
            self.tile(im,(X,Y,SW,SH),self.r.cad,ALL,{},"Sestav STEP");return im
        k=step["kljuc"];changes=states(step,p,self.sites);u=motion(p)
        sites=[self.sites[i] for i in step["deli"] if i in self.sites]
        def four(i):
            w,h=(SW-12)//2,(SH-12)//2
            return X+(i%2)*(w+12),Y+(i//2)*(h+12),w,h
        def two(i):
            w=(SW-12)//2
            return X+i*(w+12),Y,w,SH
        if k in ("poravnava","kolesa"):
            for i,pid in enumerate(WHEELS):
                ss=[s for s in self.sites.values() if s["nosilec"]==pid and s["skupina"]=="kolesa"]
                mate=ss[0]["par"];c=np.mean([s["stik_mm"] for s in ss],axis=0)
                where=("Pri ročaju" if c[0]<0 else "Nasproti ročaja")+(" · zadaj" if c[1]>0 else " · spredaj")
                if k=="poravnava":
                    cam=(c+np.array([16,0,-61]),[-.65,-1,-.28],336)
                    ids=[mate,pid]
                else:
                    cam=(c+np.array([0,0,-12]),[-.46,-.72,-1.12],245)
                    ids=[mate,pid]+[s["id"] for s in ss]
                self.tile(im,four(i),ids,cam,changes,where+"  /  "+pid,k=="kolesa")
        elif k=="prerez":
            host="P123";ss=[s for s in self.sites.values() if s["nosilec"]==host];c=np.mean([s["stik_mm"] for s in ss],0)
            self.tile(im,two(0),[host,"P113"]+[s["id"] for s in ss],(c,[-.6,-1,.63],170),
                      {"P113":(np.array([0,0,40]),0)},"Razmaknjen pogled · P113 / P123",True)
            self.section(im,two(1),ss[0])
        elif k=="stiki":
            for i,joint in enumerate(read(EXPORT/"stiki_ogrodja.json")):
                pts=np.array(joint["sticni_rob_mm"]);assert len(pts)>1
                mid=pts.mean(0);axis=pts[-1]-pts[0]
                eye=[-.79,-1.,-.62 if i==1 else .65]
                span=max(88,np.linalg.norm(axis)*2.95)
                self.tile(im,four(i),joint["deli"],(mid,eye,span),{},joint["ime"],lines=[pts[:1+round((len(pts)-1)*u)]])
        elif k=="okvir":
            ids=step["deli"];c=[-5,0,948]
            seams=[[[x-12,y-15,600],[x-12+24*u,y-15,600]] for x in (-483,483) for y in (-233,233)]
            self.tile(im,(X,Y,790,SH),ids,(c,[-.68,-1,.45],1330),{},"Ogrodje · P101–P116",lines=seams)
            c=np.array([-483,-233,600])
            lines=[[c+[-15,-15,0],c+[-15+30*u,-15,0]]]
            self.tile(im,(X+802,Y,SW-802,SH),["P101","P104","P108","P113"],(c,[-.74,-1,.67],160),{},"Stik stebra s cevjo",lines=lines)
        elif k=="zvar_rocaja":
            c=np.array([-559.,0.,1285.5])
            circle=lambda y:[[c[0]+15*np.cos(a),y,c[2]+15*np.sin(a)] for a in np.linspace(0,2*np.pi*u,40)]
            ids=step["deli"]
            self.tile(im,(X,Y,790,SH),ids,([-530,0,1268],[-1,-.52,.5],570),{},"Ročaj · P098–P100",lines=[circle(-213.6),circle(214.4)])
            self.tile(im,(X+802,Y,SW-802,SH),ids,([-550,-213.6,1283],[.52,1,.44],120),{},"Stik cevi in nosilca",lines=[circle(-213.6)])
        elif k in ("rocaj","nosilci"):
            buckets=[]
            if k=="rocaj":
                buckets=[[s for s in sites if s["nosilec"]==pid] for pid in ("P098","P100")]
            else:buckets=[[s] for s in sites]
            for i,ss in enumerate(buckets):
                host,post=ss[0]["nosilec"],ss[0]["par"];c=np.mean([s["stik_mm"] for s in ss],0)
                ids=[post,host]+[s["id"] for s in ss]+[self.inserts[s["id"]] for s in ss]
                eye=[.55,-np.sign(c[1]),.28]
                cam=(c,eye,118 if k=="rocaj" else 95)
                self.tile(im,two(i) if k=="rocaj" else four(i),ids,cam,changes,("Nosilec " if k=="rocaj" else "Povezava ")+host+"  /  "+post)
            s=sites[0];c=np.array(s["stik_mm"]);dire=np.array(s["os"]);vid=s["id"]
            self.tile(im,(52,563,427,247),[vid,self.inserts[vid]],(c-dire*6,[.87,-.43,.32],63),
                      {vid:(-dire*15,0)},"Vijak in možni vložek")
        elif k=="polaganje":
            self.tile(im,(X,Y,SW,SH),self.r.cad,([0,0,1230],[-.61,-1,.60],1600),changes,"Polica · P117")
        else:
            ids=step["referencni_deli"]+step["deli"];board=step["referencni_deli"][0];center=bounds_center(self.parts,board)
            cam=(center+[0,0,-10],[-.02,-.74,-1.45],1850)
            self.tile(im,(X,Y,SW,423),ids,cam,changes,"Pogled od spodaj · "+board)
            types=[("Spodnja izvrtina",next(s for s in sites if s["os"][2]))]
            side=next((s for s in sites if not s["os"][2]),None)
            if side:types.append(("Bočna izvrtina",side))
            else:types.append(("Dostop skozi cev",sites[-1]))
            for j,(label,s) in enumerate(types):
                c=np.array(s["stik_mm"]);axis=np.array(s["os"])
                eye=[.55,-np.sign(c[1])*.85,-.65] if axis[2] else (-axis+np.array([.40,-.31,-.45])).tolist()
                if label=="Dostop skozi cev":eye=[.08,.13,-1.]
                cut=None
                if k=="spodnja" and j==0:
                    eye=[.92,-.40,-.18];cut=(s["nosilec"],[1,0,0,-c[0]])
                    label="Prerez cevi"
                self.tile(im,(X+j*((SW-12)//2+12),Y+435,(SW-12)//2,SH-435),[board,s["nosilec"],s["id"]],
                          (c-axis*(24 if k=="spodnja" else 9),eye,138 if k=="spodnja" else 92),changes,label+"  /  "+s["id"],cut=cut)
        return im

    def section(self,im,box,site):
        x,y,w,h=box
        d=ImageDraw.Draw(im);d.rectangle((x,y,x+w,y+h),fill=BG)
        text(d,(x+28,y+28),"Prerez skozi os vijaka",24,GREEN,"mono")
        cx=x+w//2;z=y+302;scale=13
        d.rectangle((x+55,z-3*scale,x+w-55,z),fill="#627779")
        for xx in range(x+62,x+w-80,25):
            d.line((xx,z-2,xx+20,z-3*scale+2),fill="#879a9a",width=2)
        gap=site["mera_odprtine_mm"][0]*scale/2
        for left,right in [(x+55,cx-gap),(cx+gap,x+w-55)]:
            d.rectangle((left,z+1,right,z+2.5*scale),fill="#a5b1ac")
        d.polygon([(cx,z),(cx+33,z+19),(cx+33,z+14*scale),(cx-33,z+14*scale),(cx-33,z+19)],fill="#c4793d")
        for yy in range(z+24,z+14*scale,10):d.line((cx-32,yy+6,cx+32,yy-4),fill="#914f27",width=2)
        d.rounded_rectangle((cx-55,z+14*scale,cx+55,z+17*scale),5,fill="#a96937")
        d.ellipse((cx-6,z-6,cx+6,z+6),fill="#ffcb67")
        text(d,(x+53,z-98),"Nosilna plošča · 3 mm",27,INK,"bold")
        text(d,(x+52,z+61),"Prirobnica",22,MUTED)
        text(d,(x+52,z+285),"Konica doseže polno ploščo.",29,INK,"bold")
        wrap(d,x+53,z+348,"Profil vijaka je shematski. Reža v prirobnici meri približno 10,70 × 9,20 mm.",w-96,23,MUTED)

    def proof(self):
        tiles=[]
        for st in [None]+self.steps:
            img=self.layout(st,.45)
            if st is None:img.save(OUT/"predogled.png")
            tiles.append(img.resize((480,270),Image.Resampling.LANCZOS))
        sheet=Image.new("RGB",(480*3,270*4),PAPER)
        for i,img in enumerate(tiles):sheet.paste(img,(i%3*480,i//3*270))
        sheet.save(CACHE/"postavitev.jpg",quality=93)

    def encode(self):
        ff=imageio_ffmpeg.get_ffmpeg_exe()
        proc=subprocess.Popen([ff,"-hide_banner","-v","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s","1920x1080","-r","25",
            "-i","pipe:0","-an","-c:v","libx264","-preset","veryfast","-crf","17","-pix_fmt","yuv420p","-movflags","+faststart",str(OUT/"video.mp4")],stdin=subprocess.PIPE)
        total=0
        try:
            for st,sec in self.timeline:
                last=None;raw=None
                for i in range(sec*FPS):
                    t=i/(sec*FPS-1);key=round(float(motion(t)),8) if st else 0
                    if key!=last:
                        raw=self.layout(st,t).tobytes();last=key
                    proc.stdin.write(raw);total+=1
                print(st["naslov"] if st else "Sestav",total,flush=True)
        finally:
            proc.stdin.close();code=proc.wait()
        assert code==0
        save(EXPORT/"kontrola_glb.json",dict(**self.r.qa,slike=total,fps=FPS))
if __name__=="__main__":
    import sys
    film=Film();film.proof()
    if "--pregled" not in sys.argv:film.encode()

