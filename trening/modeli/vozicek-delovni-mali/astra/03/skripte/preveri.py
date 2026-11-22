"""Neodvisno branje MP4 in preizkus vidnosti geometrije v končni sestavi."""
from osnova import OUT,EXPORT,read,save
from film import Film,SIZE,GLOBAL,project,filmstrip,FPS
from orodje import weld_props
from PIL import Image
import subprocess,re
import numpy as np
import imageio_ffmpeg as ff

def geometry(film):
    parts=read(OUT/"deli.json");ids={p["id"] for p in parts}
    cad={p["id"]:p["pot"] for p in parts if p["vir"]=="STEP"}
    old=OUT.parent/"02"/"deli.json"
    if old.exists():
        assert cad=={p["id"]:p["pot"] for p in read(old) if p["vir"]=="STEP"}
    assert len(cad)==28 and len(parts)==len(ids)==108
    ref=set()
    for st in film.st:
        assert set(st["deli"]+st["referencni_deli"])<=ids
        plan=film.plans[st["st"]-1]
        assert ref.issubset(plan["sestav"])
        ref=set(plan["sestav"])
    assert len(film.held)==8
    r=film.r
    margin=[]
    # Project a conservative envelope of every component separately.
    for pid in cad:
        lo,hi=r.boxes[pid]
        c=np.array([[x,y,z] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])])
        xy=project(GLOBAL,SIZE,c);margin.append(min(xy.min(),(SIZE-xy).min()))
    assert min(margin)>20
    def different(a,b):
        return int((np.abs(np.asarray(a,dtype="i2")-np.asarray(b,dtype="i2")).max(axis=2)>16).sum())
    pixels={};beads={}
    for st,plan in zip(film.st,film.plans):
        scene=list(plan["sestav"])
        if "zvar" in plan:
            z=plan["zvar"];points=np.array(z["tocke_mm"])
            cam=(points.mean(0),z["smer"],z["sirina_mm"])
            changes={k:(np.array(d),0.) for k,d in plan.get("odmiki_mm",{}).items()}
            empty=r.view(scene,cam,SIZE,changes)
            bead=r.view(scene,cam,SIZE,changes,weld_props(points,z["smer"],1,False))
            beads[st["naslov"]]=different(empty,bead)
            assert beads[st["naslov"]]>65,(st["naslov"],beads)
        for shot in plan["mesta"]:
            pid=shot["id"]
            if pid in film.held:
                assert "oznaka_reze_mm" in shot
                continue
            if pid in film.insert:scene.append(film.insert[pid])
            cam=(shot["center_mm"],shot["smer"],shot["sirina_mm"])
            empty=r.view(scene,cam,SIZE,cut=shot["prerez"])
            scene.append(pid)
            with_screw=r.view(scene,cam,SIZE,cut=shot["prerez"])
            pixels[pid]=different(empty,with_screw)
            assert pixels[pid]>25,(pid,pixels[pid])
    assert len(pixels)==64 and len(beads)==6
    result=dict(rob_predogleda_px=round(min(margin),2),piksli_vijaki=pixels,piksli_zvari=beads)
    save(EXPORT/"kontrola_vidnosti.json",result)
    return result

def verify(film):
    geo=geometry(film)
    ffmpeg=ff.get_ffmpeg_exe()
    video=str(OUT/"video.mp4")
    log=subprocess.run([ffmpeg,"-hide_banner","-i",video,"-f","null","-"],capture_output=True,check=True).stderr.decode(errors="replace")
    assert all(x in log for x in ("Video: h264","1280x720","25 fps","yuv420p"))
    header=log.split("Stream mapping:")[0]
    bounds=re.findall(r"Chapter #0:\d+: start ([\d.]+), end ([\d.]+)",header)
    timeline=read(EXPORT/"casovnica.json")
    assert [(float(a),float(b)) for a,b in bounds]==[(item["od_s"],item["do_s"]) for item in timeline]
    count=int(re.findall(r"frame=\s*(\d+)",log)[-1])
    begin=0;refs={}
    for idx,(st,seconds) in enumerate(film.timetable):
        if st is None:times=[1.]
        elif st["gibanje"]["tip"]=="vijak":times=[2+3*i+1.52 for i in range(len(st["deli"]))]
        else:times=[1.80,3.48]
        for j,t in enumerate(times):
            frame=round(t*FPS)
            refs[begin+frame]=(idx,st,frame/FPS,j)
        begin+=seconds*FPS
    assert count==begin
    filt="select='"+"+".join("eq(n,"+str(k)+")" for k in refs)+"'"
    cmd=[ffmpeg,"-v","error","-i",video,"-vf",filt,"-fps_mode","passthrough","-f","rawvideo","-pix_fmt","rgb24","pipe:1"]
    proc=subprocess.Popen(cmd,stdout=subprocess.PIPE)
    metrics={};samples=[]
    try:
        for k,(idx,st,t,j) in refs.items():
            raw=proc.stdout.read(SIZE[0]*SIZE[1]*3)
            assert len(raw)==SIZE[0]*SIZE[1]*3
            decoded=Image.frombytes("RGB",SIZE,raw)
            expected=np.asarray(film.frame(st,t,idx==len(film.timetable)-1),dtype="f4")
            mse=np.mean((expected-np.asarray(decoded))**2)
            psnr=float(10*np.log10(255**2/max(mse,1e-9)))
            assert psnr>31,(k,psnr)
            metrics[k]=round(psnr,2)
            if not st or j==(0 if st["gibanje"]["tip"]=="vijak" else 1) or (st["gibanje"].get("skupina")=="kolesa" and j==2):
                samples.append(decoded.copy())
        assert proc.stdout.read()==b"" and proc.wait()==0
    finally:
        proc.stdout.close()
        if proc.poll() is None:proc.kill();proc.wait()
    filmstrip(samples,EXPORT/"kontrolni_kadri.jpg")
    save(EXPORT/"kontrola_videa.json",dict(dekodirane_slike=count,fps=FPS,kodek="H.264",velikost=list(SIZE),
        trajanje_s=count/FPS,psnr_db=metrics))
    print("Preverjeno",count,"slik,",len(refs),"primerjav. Najmanjši PSNR",min(metrics.values()),flush=True)

if __name__=="__main__":
    import sys
    if "--geometrija" in sys.argv:print(geometry(Film()))
    else:verify(Film())
