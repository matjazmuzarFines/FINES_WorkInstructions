from osnova import OUT,EXPORT,read,save
from potek import states,axis_matrix
import json,struct
import numpy as np
import moderngl as gl
from PIL import Image

B=np.array([[1.,0,0],[0,0,1],[0,-1,0]])
def unit(x):return x/np.linalg.norm(x)
def ortho(center,eye,width,aspect):
    e=unit(np.array(eye));r=unit(np.cross([0,0,1],e));u=np.cross(e,r)
    m=np.eye(4);m[:3,:3]=[r*2/width,u*2/width*aspect,-e/4000];m[:3,3]=-m[:3,:3]@center
    return m
def glmat(m):return m.T.astype("f4").tobytes()
def turn(z):
    c,s=np.cos(z),np.sin(z)
    return np.array([[c,-s,0],[s,c,0],[0,0,1]])

VERT="""#version 330
in vec3 vert;in vec3 normal;
uniform mat4 vp,model,light;
out vec3 pos,n,local;out vec4 shadow;
void main(){vec4 p=model*vec4(vert,1.);pos=p.xyz;local=vert;n=transpose(inverse(mat3(model)))*normal;shadow=light*p;gl_Position=vp*p;}
"""
DEPTH="""#version 330
in vec3 vert;uniform mat4 vp,model;
void main(){gl_Position=vp*model*vec4(vert,1.);}
"""
FRAG="""#version 330
in vec3 pos,n,local;in vec4 shadow;
uniform vec3 base,eye;uniform float rough,metal,bias;uniform int mode;uniform sampler2DShadow shadowMap;uniform vec4 clipPlane,window;
out vec4 frag;
float hash(vec2 p){return fract(sin(dot(p,vec2(12.9898,78.233)))*43758.5453);}
float grainNoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+1.),f.x),f.y);}
vec3 studio(vec3 r,float blur){
float strip1=exp(-pow((r.x+.35*r.z-.21)/(.11+blur*.46),2.));
float strip2=exp(-pow((r.y-.49*r.z+.27)/(.16+blur*.42),2.));
return vec3(.16,.20,.23)+vec3(.33,.34,.35)*smoothstep(-.7,.8,r.z)+vec3(.86,.80,.67)*strip1+vec3(.51,.61,.71)*strip2;
}
void main(){
if(dot(vec4(pos,1.),clipPlane)>0.)discard;
if(window.w>0. && abs(pos.x-window.x)<17. && abs(pos.y-window.y)<27. && pos.z<window.z-.7)discard;
vec3 N=normalize(n),V=normalize(eye),L=normalize(vec3(-.52,-.65,1.15));
if(dot(N,V)<0.) N=-N;
vec3 C=pow(base,vec3(2.2));float R=rough;
if(mode==1){
float wave=8.*grainNoise(pos.xy*vec2(.008,.025))+2.4*sin(pos.x*.013);
float grain=.55*grainNoise(vec2(pos.x*.009,pos.y*.34+wave))+.30*grainNoise(vec2(pos.x*.024,pos.y*1.1+wave))+.15*sin(pos.y*.42+wave);
C*=.82+.34*grain;R=.43;
}
float ndl=max(dot(N,L),0.),nv=max(dot(N,V),.02);
vec3 H=normalize(V+L);float nh=max(dot(N,H),0.);
vec3 F0=mix(vec3(.045),C,metal);
vec3 F=F0+(1.-F0)*pow(1.-nv,5.);
vec3 sc=shadow.xyz*.5+.5;float occ=1.;
if(all(greaterThan(sc,vec3(0)))&&all(lessThan(sc,vec3(1)))){
occ=0.;for(int x=-1;x<=1;x++)for(int y=-1;y<=1;y++)
occ+=texture(shadowMap,vec3(sc.xy+vec2(x,y)*.00105,sc.z-bias*(1.+2.*(1.-ndl))))/9.;
}
float geom=.42+.58*occ;
float a=R*R;float d=a*a/(3.14159*pow(nh*nh*(a*a-1.)+1.,2.)+.0001);
vec3 diffuse=C*(1.-metal*.83)*(.38+.17*N.z+1.12*ndl*geom);
vec3 spec=studio(reflect(-V,N),R)*F*(.72+.28*occ)+min(d*.32,3.)*F0*ndl*occ;
vec3 col=diffuse+spec;
if(mode==2)col=vec3(.82,.85,.83)*(.84+.16*occ);
col=col/(.78+col*.32);
frag=vec4(pow(max(col,0.),vec3(1./2.2)),1.);
if(mode==3)frag=vec4(base,1.);
}
"""

class Renderer:
    def __init__(self):
        self.ctx=gl.create_standalone_context()
        self.ctx.enable(gl.DEPTH_TEST)
        self.prog=self.ctx.program(vertex_shader=VERT,fragment_shader=FRAG)
        self.depth=self.ctx.program(vertex_shader=DEPTH,fragment_shader="#version 330\nvoid main(){}")
        self.shadow=self.ctx.depth_texture((1536,1536));self.shadow.repeat_x=False;self.shadow.repeat_y=False
        self.sfb=self.ctx.framebuffer(depth_attachment=self.shadow)
        self.targets={}
        data=(EXPORT/"vozicek.glb").read_bytes()
        magic,ver,size,jlen=struct.unpack_from("<4sIII",data)
        assert magic==b"glTF" and size==len(data) and ver==2
        g=json.loads(data[20:20+jlen]);binary=memoryview(data)[28+jlen:]
        def field(j):
            a=g["accessors"][j];v=g["bufferViews"][a["bufferView"]]
            cols={"VEC3":3,"VEC4":4,"SCALAR":1}[a["type"]]
            return np.frombuffer(binary[v["byteOffset"]:v["byteOffset"]+v["byteLength"]],"<u4" if a["componentType"]==5125 else "<f4").reshape(a["count"],cols)
        self.mesh=[];positions=[]
        for mesh in g["meshes"]:
            primitives=mesh["primitives"];attrs=primitives[0]["attributes"]
            v=field(attrs["POSITION"])@B*1000;n=field(attrs["NORMAL"])@B
            buf=self.ctx.buffer(np.column_stack((v,n)).astype("f4").tobytes());position=self.ctx.buffer(v.astype("f4").tobytes())
            pos=[];ls=[]
            for pr in primitives:
                idx=field(pr["indices"]).ravel()
                assert idx.max()<len(v)
                ib=self.ctx.buffer(idx.tobytes())
                vao=self.ctx.vertex_array(self.prog,[(buf,"3f 3f","vert","normal")],ib)
                depth=self.ctx.vertex_array(self.depth,[(position,"3f","vert")],ib)
                ls.append((pr["extras"]["telo"],pr["material"],vao,depth))
            self.mesh.append(ls);positions.append(v)
        self.mat=g["materials"];self.nodes={};self.boxes={}
        parts={p["id"]:p for p in read(OUT/"deli.json")};errs=[]
        for node in g["nodes"]:
            if "mesh" not in node:continue
            q=np.array(node["rotation"]);x,y,z,w=q
            assert np.isclose(q@q,1)
            skew=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
            mat=np.eye(4);mat[:3,:3]=B.T@(np.eye(3)+2*w*skew+2*skew@skew)@B
            mat[:3,3]=np.array(node["translation"])@B*1000
            pid=node["name"];i=node["mesh"];self.nodes[pid]=(i,mat)
            v=positions[i]@mat[:3,:3].T+mat[:3,3];b=parts[pid]["bbox_mm"]
            self.boxes[pid]=(v.min(0),v.max(0))
            errs.append(np.abs(np.array([v.min(0),v.max(0)])-[b["min"],b["max"]]).max())
        assert set(parts)==set(self.nodes) and max(errs)<.25
        self.sites={s["id"]:s for s in read(EXPORT/"pritrdilna_mesta.json")}
        def scene_parts(index):
            visited=set()
            def visit(i):
                assert i not in visited
                visited.add(i)
                for c in g["nodes"][i].get("children",[]):visit(c)
            for i in g["scenes"][index]["nodes"]:visit(i)
            return {g["nodes"][i]["name"] for i in visited if "mesh" in g["nodes"][i]}
        assert scene_parts(g["scene"])=={pid for pid,p in parts.items() if p["vir"]=="STEP"}
        steps={s["naslov"]:s for s in read(OUT/"koraki.json")}
        held={k for st in steps.values() for k in st.get("zadrzana_mesta",[])}
        assert scene_parts(1)==set(parts)-held and scene_parts(2)==set(parts)
        for clip in g["animations"]:
            step=steps[clip["name"]]; covered=set()
            for ch in clip["channels"]:
                target=ch["target"];pid=g["nodes"][target["node"]]["name"];covered.add(pid)
                samp=clip["samplers"][ch["sampler"]];ts=field(samp["input"]).ravel();values=field(samp["output"])
                assert np.all(np.diff(ts)>0) and ts[-1]==step["gibanje"]["trajanje_s"]
                for k in [0,len(ts)//2,-1]:
                    offset,angle=states(step,ts[k]/ts[-1],self.sites)[pid]
                    m=self.nodes[pid][1]
                    if target["path"]=="translation":
                        assert np.allclose(values[k]@B*1000,m[:3,3]+offset,atol=.002)
                    else:
                        x,y,z,w=values[k];sk=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
                        assert np.allclose(B.T@(np.eye(3)+2*w*sk+2*sk@sk)@B,m[:3,:3]@turn(angle),atol=1e-4)
            assert covered==set(step["deli"])-set(step.get("zadrzana_mesta",[]))
        self.qa=dict(najvecja_razlika_bbox_mm=float(max(errs)),glb_vozlisca_delov=len(self.nodes),animacije=len(g["animations"]),gpu=self.ctx.info["GL_RENDERER"])
        self.cad=[pid for pid in self.nodes if pid.startswith("P")]
    def depth_image(self,ids,cam,size=(360,240),cut=None,offsets=None):
        w,h=size
        if not hasattr(self,"probe"):
            self.probe=self.ctx.framebuffer(depth_attachment=self.ctx.depth_texture(size))
        self.probe.use();self.probe.clear(depth=1.)
        vp=ortho(*cam,w/h)
        if not hasattr(self,"probe_shader"):
            self.probe_shader=self.ctx.program(vertex_shader="""#version 330
in vec3 vert;uniform mat4 model,vp;out vec3 p;void main(){vec4 v=model*vec4(vert,1.);p=v.xyz;gl_Position=vp*v;}""",
                fragment_shader="""#version 330
in vec3 p;uniform vec4 window;void main(){if(window.w>0. && abs(p.x-window.x)<17. && abs(p.y-window.y)<27. && p.z<window.z-.7)discard;}""")
            self.probe_vaos={}
        shader=self.probe_shader;shader["vp"].write(glmat(vp))
        for pid in ids:
            idx,m=self.nodes[pid]
            lo,hi=self.boxes[pid]
            if offsets and pid in offsets:
                shift=np.array(offsets[pid]);m=m.copy();m[:3,3]+=shift;lo=lo+shift;hi=hi+shift
            if np.any(np.abs(vp[:2,:3]@((lo+hi)/2)+vp[:2,3])>1.05+np.abs(vp[:2,:3])@((hi-lo)/2)):continue
            shader["model"].write(glmat(m));shader["window"].value=(*cut[1],1.) if cut and pid==cut[0] else (0,0,0,0)
            for _,_,_,vao in self.mesh[idx]:
                if vao not in self.probe_vaos:
                    self.probe_vaos[vao]=self.ctx.vertex_array(shader,vao._content,vao.index_buffer)
                self.probe_vaos[vao].render()
        return np.frombuffer(self.probe.read(attachment=-1,components=1,dtype="f4"),"f4").reshape(h,w)

    def view(self,ids,cam,size,changes=None,extras=(),cut=None):
        w,h=size
        if size not in self.targets:self.targets[size]=self.ctx.simple_framebuffer((w,h),components=3,samples=4)
        if not hasattr(self,"resolve"):self.resolve={}
        if size not in self.resolve:self.resolve[size]=self.ctx.simple_framebuffer(size,components=3)
        center,eye,span=cam
        vp=ortho(center,eye,span,w/h)
        light=ortho(center,[-.52,-.65,1.15],span*1.6,1)
        draws=[]
        for pid in ids:
            idx,m=self.nodes[pid]
            offset=np.zeros(3)
            if changes and pid in changes:
                offset,theta=changes[pid];m=m.copy();m[:3,3]+=offset
                if theta:m[:3,:3]=m[:3,:3]@turn(theta)
            lo,hi=self.boxes[pid]
            c=vp[:2,:3]@((lo+hi)*.5+offset)+vp[:2,3]
            radius=np.abs(vp[:2,:3])@((hi-lo)*.5)
            if np.any(np.abs(c)>1.05+radius):continue
            group=self.mesh[idx]
            draws.append((pid,glmat(m),group))
        if extras:
            matrices=np.array([m for _,m in extras])
            centers=matrices[:,:3,3]+.5*matrices[:,:3,2]
            margins=np.abs(vp[:2,:3]@matrices[:,:3,:3]).sum(axis=2)
            keep=np.all(np.abs(centers@vp[:2,:3].T+vp[:2,3])<1.05+margins,axis=1)
            draws.extend((name,glmat(m),self.extra_mesh[name]) for (name,m),visible in zip(extras,keep) if visible)
        self.sfb.use();self.sfb.clear(depth=1.);self.depth["vp"].write(glmat(light))
        for pid,m,group in draws:
            self.depth["model"].write(m)
            for _,_,_,dv in group:dv.render()
        fb=self.targets[size];fb.use();fb.clear(.925,.936,.932,depth=1.)
        self.shadow.use(0)
        self.prog["shadowMap"]=0;self.prog["vp"].write(glmat(vp));self.prog["light"].write(glmat(light))
        self.prog["eye"].value=tuple(unit(np.asarray(eye)));self.prog["bias"]=max(.000018,span/6000000)
        for pid,m,group in draws:
            self.prog["clipPlane"].value=(0.,0.,0.,0.)
            self.prog["window"].value=(*cut[1],1.) if cut and pid==cut[0] else (0.,0.,0.,0.)
            self.prog["model"].write(m)
            for _,mi,vao,_ in group:
                mat=self.mat[mi];pbr=mat["pbrMetallicRoughness"]
                self.prog["base"].value=tuple(mat["extras"]["srgb"])
                self.prog["metal"]=pbr["metallicFactor"];self.prog["rough"]=pbr["roughnessFactor"]
                self.prog["mode"]=3 if mat.get("emission") else int(mat["name"]=="iveral")
                vao.render()
        res=self.resolve[size];self.ctx.copy_framebuffer(res,fb)
        return Image.frombytes("RGB",size,res.read(components=3,alignment=1)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)

