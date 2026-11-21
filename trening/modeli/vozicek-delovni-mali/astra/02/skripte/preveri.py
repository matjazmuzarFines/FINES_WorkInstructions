from osnova import OUT,EXPORT,read,save
from film import Film,W,H,FPS,X,Y,SW,SH,font
from PIL import Image,ImageDraw
import imageio_ffmpeg
import numpy as np
import subprocess,re


def verify(film):
    ff=imageio_ffmpeg.get_ffmpeg_exe();path=str(OUT/"video.mp4")
    res=subprocess.run([ff,"-hide_banner","-i",path,"-map","0:v:0","-f","null","-"],capture_output=True,check=True)
    log=res.stderr.decode(errors="replace")
    assert all(token in log for token in ["Video: h264","1920x1080","yuv420p","25 fps"])
    frames=int(re.findall(r"frame=\s*(\d+)",log)[-1])
    samples={};start=0
    for chapter,(st,sec) in enumerate(film.timeline):
        count=sec*FPS
        for t in ([.1,.50,.92] if st else [.5]):
            rel=round(t*(count-1))
            samples[start+rel]=(chapter,st,rel/(count-1),t)
        start+=count
    assert frames==start==read(EXPORT/"kontrola_glb.json")["slike"]
    cmd=[ff,"-v","error","-i",path,"-vf","select='"+"+".join(f"eq(n,{n})" for n in samples)+"'",
         "-fps_mode","passthrough","-f","rawvideo","-pix_fmt","rgb24","pipe:1"]
    proc=subprocess.Popen(cmd,stdout=subprocess.PIPE)
    metrics={};difference={};first=None;sheet=Image.new("RGB",(3*528,5*328),"#f9f8f3");d=ImageDraw.Draw(sheet)
    for number,(ch,st,p,t) in samples.items():
        raw=proc.stdout.read(W*H*3);assert len(raw)==W*H*3
        array=np.frombuffer(raw,dtype="u1").reshape(H,W,3)
        expected=np.asarray(film.layout(st,p),dtype="f4")
        mse=np.mean((expected-array)**2);psnr=float(10*np.log10(255**2/max(mse,1e-12)))
        assert psnr>30,(number,psnr)
        metrics[number]=round(psnr,2)
        stage=array[Y:Y+SH,X:X+SW]
        if t==.1:first=stage.copy()
        if t==.92 and st["kljuc"]!="prerez":
            difference[st["kljuc"]]=int((np.max(np.abs(stage.astype("i2")-first),axis=2)>22).sum())
            assert difference[st["kljuc"]]>30
        if t==.5:
            x=ch%3*528;y=ch//3*328
            sheet.paste(Image.fromarray(array).resize((528,297),Image.Resampling.LANCZOS),(x,y))
            title=st["naslov"] if st else "Sestav"
            d.text((x+12,y+303),f"{number/FPS:05.2f} s   {title}",font=font(17),fill="#254743")
    assert proc.stdout.read()==b"" and proc.wait()==0
    sheet.save(EXPORT/"kontrolni_kadri.jpg",quality=94)
    save(EXPORT/"kontrola_videa.json",dict(dekodirane_slike=frames,trajanje_s=frames/FPS,fps=FPS,kodek="H.264",velikost=[W,H],
        psnr_kadrov_db=metrics,spremenjene_tocke_v_3d_pogledu=difference))
if __name__=="__main__":verify(Film())

