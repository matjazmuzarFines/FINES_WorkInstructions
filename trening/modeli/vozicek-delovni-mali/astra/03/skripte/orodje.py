"""Shematske 3D oblike orodja, obloka in sledi. Isti globinski test kot pri CAD."""
from osnova import OUT
from studio import unit,turn
import numpy as np
from math import pi, cos, sin

def install(renderer):
    renderer.extra_mesh={}
    def profile(name,rings,sides,color,metal=.55,rough=.33,emission=False,flutes=0):
        vertices=[];normals=[]
        def point(i,r,z):
            t=2*pi*i/sides
            rad=r*(1-.10*(i%2)) if flutes else r
            return np.array([rad*cos(t),rad*sin(t),z])
        for (ra,za),(rb,zb) in zip(rings,rings[1:]):
            for i in range(sides):
                a,b,c,d=point(i,ra,za),point(i+1,ra,za),point(i+1,rb,zb),point(i,rb,zb)
                for tri in [(a,b,c),(a,c,d)]:
                    n=np.cross(tri[1]-tri[0],tri[2]-tri[0])
                    if np.linalg.norm(n)<1e-9:continue
                    vertices.extend(tri);normals.extend([unit(n)]*3)
        v=np.array(vertices,"f4");n=np.array(normals,"f4")
        ctx=renderer.ctx
        buf=ctx.buffer(np.column_stack((v,n)).astype("f4").tobytes())
        pos=ctx.buffer(v.tobytes())
        vao=ctx.vertex_array(renderer.prog,[(buf,"3f 3f","vert","normal")])
        dv=ctx.vertex_array(renderer.depth,[(pos,"3f","vert")])
        mi=len(renderer.mat)
        renderer.mat.append(dict(name=name,extras=dict(srgb=color),emission=emission,
            pbrMetallicRoughness=dict(metallicFactor=metal,roughnessFactor=rough)))
        renderer.extra_mesh[name]=[(0,mi,vao,dv)]
    profile("jeklen nastavek",[(0,0),(1,0),(1,1),(0,1)],24,[.71,.75,.79])
    profile("bakrena šoba",[(0,0),(.7,0),(.78,.18),(1,.8),(.94,1),(0,1)],32,[.82,.49,.30])
    profile("ročaj",[(0,0),(.62,0),(.85,.09),(1,.21),(.84,.54),(1,.81),(.91,.94),(.63,1),(0,1)],32,[.13,.27,.33],.12,.40,flutes=1)
    profile("obroč",[(0,0),(1,0),(1,1),(0,1)],24,[.90,.53,.15],.32)
    profile("natični ključ",[(.77,0),(1,0),(1,.15),(.9,.22),(.9,.78),(.72,1),(0,1)],12,[.60,.68,.72])
    profile("šestrobni nastavek",[(0,0),(.83,0),(1,.22),(1,1),(0,1)],6,[.50,.56,.61])
    profile("zvar",[(0,0),(.81,.04),(1,.35),(.82,.78),(.5,1),(0,1)],16,[.39,.37,.34],.74)
    profile("talina",[(0,0),(.8,.08),(1,.42),(.63,.84),(0,1)],20,[1,.59,.10],emission=True)
    profile("oblok",[(0,0),(1,.3),(.3,1),(0,1)],16,[.86,.96,1.],emission=True)

def rod(name,origin,direction,r,length,angle=0):
    z=unit(np.array(direction,dtype=float))
    ref=np.array([0.,0.,1.]) if abs(z[2])<.89 else np.array([0.,1.,0.])
    x=unit(np.cross(ref,z));y=np.cross(z,x)
    m=np.eye(4);m[:3,:3]=np.column_stack((x*r,y*r,z*length))@turn(angle)
    m[:3,3]=origin
    return name,m

def driver(site,shift,angle,phase):
    from potek import smooth
    if phase<.20 or phase>2.63:return []
    d=-np.array(site["os"])
    wood=site["skupina"] in ("spodnja","srednja","zgornja")
    small=site["skupina"]!="kolesa"
    # Socket overlaps the sides of a hex head. The bit enters the illustrated recess.
    clearance=20*(1-smooth((phase-.2)/.64))+28*smooth((phase-2.03)/.60)
    pos=np.array(site["glava_mm"])+shift+d*((1.1 if wood else .5)+clearance)
    tip=1.25 if wood else (5.2 if small else 6.8)
    length=7 if wood else 10
    return [rod("šestrobni nastavek" if wood else "natični ključ",pos,d,tip,length,angle),
            rod("jeklen nastavek",pos+d*length,d,1.65 if wood else 2.8,16,angle),
            rod("obroč",pos+d*(length+16),d,4.2,3,angle),
            rod("ročaj",pos+d*(length+19),d,5.9,31,angle),
            rod("obroč",pos+d*(length+43)+np.array([0,0,0]),d,5.35,1.7,angle)]

def weld_props(points,eye,progress,active):
    lengths=np.linalg.norm(np.diff(points,axis=0),axis=1)
    ds=np.r_[0,np.cumsum(lengths)]
    def at(s):return np.array([np.interp(s,ds,points[:,k]) for k in range(3)])
    end=progress*ds[-1];toward=unit(np.array(eye,dtype=float))
    props=[]
    for s in np.arange(.1,end,.95):
        tangent=unit(at(min(s+.25,ds[-1]))-at(max(0,s-.25)))
        props.append(rod("zvar",at(s)-tangent*.47+toward*.25,tangent,1.18,1.35))
    if active:
        tip=at(end)
        tangent=unit(at(min(end+.4,ds[-1]))-at(max(0,end-.4)))
        direction=unit(toward*.76+np.array([0,0,.42])-tangent*.85)
        neck=unit(direction+tangent*.56)
        props.extend([rod("talina",tip-tangent*.65+toward*.4,tangent,1.5,2),
            rod("oblok",tip+toward*.45,direction,.75,2.8),
            rod("jeklen nastavek",tip+direction*2.8,direction,.44,3.2),
            rod("bakrena šoba",tip+direction*5.7,direction,3.4,12),
            rod("jeklen nastavek",tip+direction*17,direction,2.7,9),
            rod("jeklen nastavek",tip+direction*26,neck,2.7,10),
            rod("ročaj",tip+direction*26+neck*10,neck,5.2,32)])
    return props
