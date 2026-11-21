import re
import subprocess
from osnova import OUT, EXPORT, read, save
import imageio_ffmpeg
from PIL import Image, ImageDraw
from film import FPS, W, H, font
import numpy as np


def verify():
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    # Decode every frame. Read the inspection images from the encoded video.
    cmd = [ff,"-hide_banner","-loglevel","info","-i",str(OUT/"video.mp4"),"-map","0:v:0","-f","null","-"]
    result = subprocess.run(cmd,capture_output=True,check=True)
    log=result.stderr.decode(errors="replace")
    assert "Video: h264" in log and "yuv420p" in log and "1280x720" in log and "25 fps" in log
    n = int(re.findall(r"frame=\s*(\d+)",log)[-1])
    assert n == read(EXPORT/"kontrola_glb.json")["slike"]
    times=[1.0,4.0,5.7,8.6,11.4,13.3,16.2,18.4,21.0]
    ids=[round(t*FPS) for t in times]
    filt = "select='"+"+".join(f"eq(n,{i})" for i in ids)+"'"
    raw=subprocess.check_output([ff,"-v","error","-i",str(OUT/"video.mp4"),"-vf",filt,"-fps_mode","passthrough",
                                 "-f","rawvideo","-pix_fmt","rgb24","pipe:1"])
    assert len(raw)==W*H*3*len(ids)
    frames=np.frombuffer(raw,"u1").reshape(-1,H,W,3)
    sheet=Image.new("RGB",(1260,3*265),"#f8f8f5")
    pen=ImageDraw.Draw(sheet)
    for k,(t,a) in enumerate(zip(times,frames)):
        x,y=k%3*420,k//3*265
        sheet.paste(Image.fromarray(a).resize((420,236),Image.Resampling.LANCZOS),(x,y))
        pen.text((x+10,y+239),f"{t:.1f} s",fill="#18333b",font=font(14,mono=True))
    sheet.save(EXPORT/"kontrolni_kadri.jpg",quality=92)
    save(EXPORT/"kontrola_videa.json",dict(kodek="H.264",format="yuv420p",velikost=[W,H],fps=FPS,
                                          dekodirane_slike=n,pregledani_casi_s=times))


if __name__=="__main__":
    verify()

