import json
import os
import struct
import subprocess
from functools import lru_cache
from pathlib import Path
from osnova import OUT, EXPORT, read, save
import imageio_ffmpeg
import moderngl as gl
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W,H,SIDE,FPS = 1280,720,380,25
STAGE = W-SIDE
BG = (235,240,241)
INK = "#172e3a"
MUTED = "#536974"
TEAL = "#126963"
ORANGE = "#d76d36"
PAPER = "#fbfaf6"
WHOLE = dict(cilj_mm=[-5,0,908], smer_proti_kameri=[-.66,-1,.49], sirina_mm=1820)
BASIS = np.array([[1.,0,0],[0,0,1],[0,-1,0]])


def unit(v):
    return v / np.linalg.norm(v)


def unpack_model():
    data = (EXPORT/"vozicek.glb").read_bytes()
    magic, version, length, njson = struct.unpack_from("<4sIII",data)
    assert magic == b"glTF" and version == 2 and length == len(data)
    g = json.loads(data[20:20+njson])
    binary = memoryview(data)[28+njson:]
    assert len(binary) == g["buffers"][0]["byteLength"]
    def field(index):
        a = g["accessors"][index]
        v = g["bufferViews"][a["bufferView"]]
        typ = {5125:"<u4",5126:"<f4"}[a["componentType"]]
        cols = {"SCALAR":1,"VEC3":3}[a["type"]]
        return np.frombuffer(binary[v["byteOffset"]:v["byteOffset"]+v["byteLength"]],typ).reshape(a["count"],cols)
    meshes = {}
    inventory = {p["id"]:p for p in read(OUT/"deli.json")}
    errors = []
    scene_nodes = set()
    def visit(i):
        assert i not in scene_nodes
        scene_nodes.add(i)
        for j in g["nodes"][i].get("children",[]):
            visit(j)
    for i in g["scenes"][0]["nodes"]:
        visit(i)
    assert len(scene_nodes)==len(g["nodes"])
    for node in g["nodes"]:
        if "mesh" not in node:
            continue
        pid = node["name"]
        mesh = g["meshes"][node["mesh"]]["primitives"][0]
        q = np.array(node["rotation"])
        assert abs(q@q-1)<1e-6
        def rotate(v):
            t = 2*np.cross(q[:3],v)
            return v + q[3]*t + np.cross(q[:3],t)
        v = ((rotate(field(mesh["attributes"]["POSITION"]))+node["translation"])@BASIS)*1000
        n = rotate(field(mesh["attributes"]["NORMAL"]))@BASIS
        idx = field(mesh["indices"]).ravel()
        assert idx.max() < len(v) and len(idx)%3==0
        p = inventory[pid]
        b = p["bbox_mm"]
        errors.append(float(np.max(np.abs(np.array([v.min(0),v.max(0)])-[b["min"],b["max"]]))))
        meshes[pid] = (np.column_stack((v,n)).astype("f4"),idx)
    assert set(meshes)==set(inventory) and max(errors)<0.25
    for clip,step in zip(g["animations"],read(OUT/"koraki.json"),strict=True):
        target = g["nodes"][clip["channels"][0]["target"]["node"]]
        assert target["name"] == step["deli"][0]
        s = clip["samplers"][0]
        ts, xyz = field(s["input"]).ravel(),field(s["output"])
        assert np.all(np.diff(ts)>0) and np.isclose(ts[-1],step["gibanje"]["trajanje_s"])
        assert np.allclose((xyz[0]-xyz[-1])@BASIS*1000,step["gibanje"]["od_mm"],atol=.001)
        assert np.allclose(xyz[-1],target["translation"],atol=1e-6)
    return inventory, meshes, max(errors)


VERT = """#version 330
in vec3 vert; in vec3 norm;
uniform mat4 vp; uniform vec3 offset;
out vec3 n; out vec3 p;
void main(){p=vert+offset; n=norm; gl_Position=vp*vec4(p,1.0);}
"""
FRAG = """#version 330
in vec3 n; in vec3 p;
uniform vec3 color; uniform vec3 eye; uniform int wood;
out vec4 frag;
void main(){
vec3 N=normalize(n);
vec3 L=normalize(vec3(-0.38,-0.45,0.84));
float key=max(0.,dot(N,L)), sky=max(0.,N.z), rim=max(0.,dot(N,normalize(vec3(.7,.55,.35))));
float shade=.56+.37*key+.12*sky+.08*rim;
float spec=pow(max(0.,dot(N,normalize(L+eye))),32.);
vec3 rgb=color*shade+vec3(.13*spec);
if(wood==1) rgb*=.985+.015*sin(p.y*.44+.8*sin(p.x*.011));
frag=vec4(rgb,1.);
}
"""

class Scene:
    def __init__(self, mesh):
        self.ctx=gl.create_standalone_context()
        self.ctx.enable(gl.DEPTH_TEST)
        self.prog=self.ctx.program(vertex_shader=VERT,fragment_shader=FRAG)
        self.vaos={}
        for pid,(v,idx) in mesh.items():
            buf=self.ctx.buffer(v.tobytes())
            ib=self.ctx.buffer(idx.tobytes())
            self.vaos[pid]=self.ctx.vertex_array(self.prog,[(buf,"3f 3f","vert","norm")],ib,index_element_size=4)
        self.frames={}
    def view(self,camera,inventory,active=None,dz=0,only=None,size=(STAGE,H)):
        width,height=size
        if size not in self.frames:
            large=(width*2,height*2)
            self.frames[size]=self.ctx.simple_framebuffer(large,components=3)
        fb=self.frames[size]
        fb.use()
        fb.clear(*(v/255 for v in BG),depth=1)
        eye=unit(np.array(camera["smer_proti_kameri"]))
        right=unit(np.cross([0,0,1],eye))
        up=np.cross(eye,right)
        span=camera["sirina_mm"]
        vp=np.eye(4)
        vp[:3,:3]=np.array([right*2/span,up*2/span*width/height,-eye/4300])
        vp[:3,3]=-vp[:3,:3]@camera["cilj_mm"]
        self.prog["vp"].write(vp.T.astype("f4").tobytes())
        self.prog["eye"].value=tuple(eye)
        for pid,vao in self.vaos.items():
            if only and pid!=only:
                continue
            p=inventory[pid]
            wood="lesena" in p["opis"]
            color=(.77,.63,.46) if wood else (.38,.44,.48) if p["telesa"]>1 else (.53,.63,.69)
            if active==pid:
                color=(.97,.53,.25)
            self.prog["wood"].value=int(wood)
            self.prog["color"].value=color
            self.prog["offset"].value=(0.,0.,dz if pid==active else 0.)
            vao.render()
        return Image.frombytes("RGB",fb.size,fb.read(components=3,alignment=1)).transpose(Image.Transpose.FLIP_TOP_BOTTOM).resize(size,Image.Resampling.LANCZOS)


@lru_cache
def font(size,bold=False,mono=False):
    name="consola.ttf" if mono else "segoeuib.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts"/name),size)


def txt(d,x,y,s,size=20,color=INK,bold=False,mono=False):
    for i,line in enumerate(s.splitlines()):
        d.text((x,y+i*(size+6)),line,font=font(size,bold,mono),fill=color,anchor="lt")


class Film:
    def __init__(self):
        self.parts,meshes,self.error=unpack_model()
        self.scene=Scene(meshes)
        self.steps=read(OUT/"koraki.json")
        self.margins={}
        def inspect_view(key, cam, points):
            eye=unit(np.asarray(cam["smer_proti_kameri"]))
            right=unit(np.cross([0,0,1],eye))
            centered=points-np.asarray(cam["cilj_mm"])
            scale=STAGE/cam["sirina_mm"]
            x=STAGE/2+centered@right*scale
            y=H/2-centered@np.cross(eye,right)*scale
            margins=[x.min(),STAGE-x.max(),y.min(),H-y.max()]
            assert min(margins)>=8, (key,margins)
            self.margins[key]=np.round(margins,1).tolist()
        inspect_view("sestav",WHOLE,np.vstack([v[:,:3] for v,_ in meshes.values()]))
        self.thumbs={}
        for s in self.steps:
            pid,=s["deli"]
            vertices=meshes[pid][0][:,:3]
            inspect_view(pid,s["kamera"],np.vstack([vertices,vertices+s["gibanje"]["od_mm"]]))
            b=self.parts[pid]["bbox_mm"]
            cen=(np.array(b["min"])+b["max"])/2
            cam=dict(cilj_mm=cen,smer_proti_kameri=[-.76,-1,.55],sirina_mm=240 if pid=="P123" else 1230)
            self.thumbs[pid]=self.scene.view(cam,self.parts,only=pid,size=(306,142))
    def layout(self,index,phase="uvod",dz=0):
        step=self.steps[index] if index is not None else None
        pid=step["deli"][0] if step else None
        detail=step and phase!="lokacija"
        cam=step["kamera"] if detail else WHOLE
        im=Image.new("RGB",(W,H),PAPER)
        im.paste(self.scene.view(cam,self.parts,pid,dz),(SIDE,0))
        d=ImageDraw.Draw(im)
        d.line((SIDE-1,0,SIDE-1,H),fill="#c5cfd0")
        txt(d,32,33,"FINES",24,bold=True)
        txt(d,120,40,"/   TEHNIČNI PRIKAZ",13,MUTED,mono=True)
        d.line((32,79,SIDE-32,79),fill="#c8d0cd")
        txt(d,SIDE+30,32,"MLU123069200",15,MUTED,mono=True)
        status={"uvod":"SESTAVLJEN VOZIČEK","konec":"KONČNA LEGA","lokacija":"LEGA NA VOZIČKU","odmik":"ZAČETNI ODMIK","gib":"PREMIK","lega":"LEGA IZ STEP"}
        d.text((W-32,32),status[phase],font=font(15,mono=True),fill=MUTED,anchor="rt")
        if not step:
            txt(d,32,134,"GEOMETRIJSKI PRIKAZ",15,TEAL,mono=True)
            txt(d,30,179,"Mali delovni",43,bold=True)
            txt(d,30,232,"voziček",43,bold=True)
            txt(d,33,325,"Prikazana dela",24,bold=True)
            txt(d,33,373,"01",18,TEAL,mono=True)
            txt(d,83,371,"Kolo z zavoro",22)
            txt(d,33,417,"02",18,TEAL,mono=True)
            txt(d,83,415,"Zgornja polica",22)
            note="Zaporedje in pritrditev\\nzahtevata potrditev tehnologa."
        else:
            txt(d,32,113,f"PRIKAZ  0{index+1} / 02",15,TEAL,mono=True)
            title=["Kolo z zavoro","Zgornja polica"][index]
            txt(d,30,152,title,39,bold=True)
            txt(d,33,221,pid,25,TEAL,bold=True)
            txt(d,119,229,"Ø 80 mm" if index==0 else "993 × 493 × 18 mm",18,MUTED)
            im.paste(self.thumbs[pid],(32,278))
            d=ImageDraw.Draw(im)
            txt(d,33,448,"Dvig do plošče" if index==0 else "Spust na okvir",24,bold=True)
            text="Z odmikom 105 mm pod ploščo\\nP113. Zasuk kolesa ostane enak." if index==0 else "Z odmikom 145 mm nad okvirjem.\\nDaljši rob sledi stranici vozička."
            txt(d,33,492,text.replace("\\n","\n"),18,MUTED)
            note="Pritrditev kolesa in podpiranje\\nvozička zahtevata potrditev." if index==0 else "V končni legi CAD zazna majhen\\npresek s štirimi povezavami."
        d.line((32,608,SIDE-32,608),fill="#c8d0cd")
        txt(d,32,630,"PRED UPORABO V PROIZVODNJI",13,TEAL,mono=True)
        txt(d,32,659,note.replace("\\n","\n"),16,MUTED)
        if step and detail:
            label=f"{pid}    |    ODMIK  {abs(dz):.0f} mm"
            d.rounded_rectangle((SIDE+26,H-57,SIDE+305,H-20),radius=6,fill="#203844")
            d.ellipse((SIDE+39,H-43,SIDE+48,H-34),fill=ORANGE)
            txt(d,SIDE+60,H-46,label,16,"#ffffff",mono=True)
        return im

    def frames(self):
        def hold(img, seconds):
            raw=img.tobytes()
            for _ in range(round(FPS*seconds)):
                yield raw
        yield from hold(self.layout(None),3)
        for i,s in enumerate(self.steps):
            z=s["gibanje"]["od_mm"][2]
            yield from hold(self.layout(i,"lokacija"),2.2)
            yield from hold(self.layout(i,"odmik",z),1.8)
            count=round(FPS*s["gibanje"]["trajanje_s"])
            for k in range(count):
                u=k/(count-1)
                yield self.layout(i,"gib",z*(1-u*u*(3-2*u))).tobytes()
            yield from hold(self.layout(i,"lega"),2.6)
        yield from hold(self.layout(None,"konec"),2.0)


def run():
    film=Film()
    film.layout(None).save(OUT/"predogled.png")
    ff=imageio_ffmpeg.get_ffmpeg_exe()
    proc=subprocess.Popen([ff,"-hide_banner","-loglevel","error","-y","-f","rawvideo","-pixel_format","rgb24",
          "-video_size",f"{W}x{H}","-framerate",str(FPS),"-i","pipe:0","-an","-c:v","libx264","-preset","fast",
          "-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(OUT/"video.mp4")],stdin=subprocess.PIPE)
    count=0
    try:
        for frame in film.frames():
            proc.stdin.write(frame)
            count+=1
    finally:
        proc.stdin.close()
        code=proc.wait()
    assert code==0
    save(EXPORT/"kontrola_glb.json",dict(najvecja_razlika_bbox_mm=film.error,slike=count,fps=FPS,
                                        trajanje_s=count/FPS,robovi_pogleda_px=film.margins,grafika=film.scene.ctx.info["GL_RENDERER"]))


if __name__=="__main__":
    run()

