from osnova import OUT,EXPORT,CACHE,read,save
from potek import sequence,states,axis_matrix,FPS
import numpy as np
import struct,json,math
from OCP.gp import gp_Trsf

B=np.array([[1.,0,0],[0,0,1],[0,-1,0]])
# Display palette in sRGB. Surface finish is an illustration.
PALETTE={"jeklo":([.49,.55,.58],.75,.34),"inox":([.73,.76,.77],.90,.22),"iveral":([.73,.55,.36],.04,.52),
         "tekalna plast":([.16,.19,.21],.12,.60),"litina":([.50,.54,.55],.74,.31),"temen polimer":([.24,.27,.29],.12,.42),
         "oznaka zavore":([.65,.56,.30],.35,.39),"vijak · predlog":([.87,.53,.24],.69,.29),"vložek · predlog":([.23,.63,.66],.62,.29)}


def rotation(z):
    c,s=np.cos(z),np.sin(z)
    return np.array([[c,-s,0],[s,c,0],[0,0,1]])

def quaternion(m):
    t=gp_Trsf()
    t.SetValues(*np.column_stack((m,np.zeros(3))).flatten())
    q=t.GetRotation()
    return [q.X(),q.Y(),q.Z(),q.W()]

def hardware(r,length,wood):
    verts=[]; norms=[]; ix=[]
    def tri(a,b,c):
        k=len(verts);n=np.cross(np.subtract(b,a),np.subtract(c,a));size=np.linalg.norm(n)
        if size<1e-8:return
        verts.extend([a,b,c]);norms.extend([n/size]*3);ix.append([k,k+1,k+2])
    def ring(rad,z,t):
        return [rad*np.cos(t),rad*np.sin(t),z]
    def lathe(profile,count):
        for (r0,z0),(r1,z1) in zip(profile,profile[1:]):
            for k in range(count):
                t=k*2*np.pi/count;u=(k+1)*2*np.pi/count
                a,b,c,d=ring(r0,z0,t),ring(r0,z0,u),ring(r1,z1,u),ring(r1,z1,t)
                tri(a,b,c);tri(a,c,d)
    if wood:
        lathe([(r*.48,-1.9),(r*1.8,-1.9),(r*1.95,-1.55),(r*.8,.7)],32)
        lathe([(0,-.7),(r*.48,-.7),(r*.48,-1.9)],6)
    else:
        lathe([(0,-r*.95),(r*1.56,-r*.95),(r*1.85,-r*.76),(r*1.85,-.22),(r*1.6,0),(r*.82,0)],6)
    lathe([(r*.81,0),(r*.81,length-1.5),(0,length)],24)
    pitch=1.5 if wood else 1.15
    ts=np.linspace(0,2*np.pi*(length-2)/pitch,int((length-2)/pitch*24)+1)
    for a,b in zip(ts,ts[1:]):
        for (ra,za),(rb,zb) in zip([(r*.8,0),(r,.38*pitch)],[(r,.38*pitch),(r*.8,.75*pitch)]):
            A=ring(ra,1+a*pitch/(2*np.pi)+za,a);D=ring(rb,1+a*pitch/(2*np.pi)+zb,a)
            C=ring(rb,1+b*pitch/(2*np.pi)+zb,b);E=ring(ra,1+b*pitch/(2*np.pi)+za,b)
            tri(A,E,C);tri(A,C,D)
    return np.array(verts),np.array(norms),np.array(ix)


def build():
    cache=CACHE
    parts=read(cache/"cad.json")
    fix=read(EXPORT/"pritrdilna_mesta.json")
    sites={f["id"]:f for f in fix}
    stats=read(EXPORT/"kontrola_cad.json")
    g=dict(asset=dict(version="2.0",generator="Astra 03 / Open CASCADE"),scene=0,
           scenes=[dict(name="Sestav STEP",nodes=[0]),dict(name="Shematska pritrdila",nodes=[0,2])],
           nodes=[dict(name=stats["koren"],children=[1]),dict(name="MLU124029200",children=[]),
                  dict(name="Pritrdila · predlog",children=[])],meshes=[],materials=[],animations=[],accessors=[],bufferViews=[])
    binary=bytearray()
    def acc(arr,kind,target=None):
        a=np.ascontiguousarray(arr,dtype="<u4" if target==34963 else "<f4")
        v=dict(buffer=0,byteOffset=len(binary),byteLength=a.nbytes)
        if target:v["target"]=target
        g["bufferViews"].append(v);binary.extend(a.tobytes())
        rows=a.reshape(-1,1 if kind=="SCALAR" else int(kind[-1]))
        g["accessors"].append(dict(bufferView=len(g["bufferViews"])-1,count=len(rows),componentType=5125 if target==34963 else 5126,
              type=kind,min=rows.min(0).tolist(),max=rows.max(0).tolist()))
        return len(g["accessors"])-1
    mats=list(PALETTE)
    for name,(col,metal,rough) in PALETTE.items():
        g["materials"].append(dict(name=name,pbrMetallicRoughness=dict(baseColorFactor=[x**2.2 for x in col]+[1],
                                  metallicFactor=metal,roughnessFactor=rough),extras=dict(srgb=col)))
    lookup={};nodeids={};rots={}
    def mesh(name,v,n,groups):
        attr=dict(POSITION=acc(v@B.T/1000,"VEC3",34962),NORMAL=acc(n@B.T,"VEC3",34962))
        prims=[dict(attributes=attr,indices=acc(idx.flatten(),"SCALAR",34963),material=mats.index(mat),extras=dict(telo=body))
               for body,mat,idx in groups]
        lookup[name]=len(g["meshes"])
        g["meshes"].append(dict(name=name,primitives=prims))
    def node(pid,code,orient,pos,parent,extras):
        i=len(g["nodes"]);nodeids[pid]=i;rots[pid]=orient
        g["nodes"].append(dict(name=pid,mesh=lookup[code],translation=(B@pos/1000).tolist(),
                              rotation=quaternion(B@orient@B.T),extras=extras))
        g["nodes"][parent]["children"].append(i)
    for p in parts:
        code=p["sifra_step"]
        if code not in lookup:
            a=np.load(cache/(code+".npz"));idx=a["ix"];groups=[]
            if len(a["solid"]):
                colors=a["color"];body=a["solid"];keys=[]
                for body_id in range(17):
                    use=body==body_id
                    for rgb in np.unique(colors[use],axis=0):
                        mask=use&np.all(colors==rgb,axis=1)
                        mat="litina"
                        if body_id==2:
                            mat="tekalna plast" if rgb[2]>.8 else "temen polimer"
                        elif rgb[0]>.85 and rgb[2]<.6:mat="oznaka zavore"
                        elif rgb[0]>=0 and rgb.max()<.4:mat="temen polimer" if body_id!=16 else "jeklo"
                        groups.append((body_id,mat,idx[mask]))
            else:
                mat={"Steel, Mild":"jeklo","Iveral":"iveral","Stainless Steel AISI 304":"inox"}[p["material_step"]["naziv"]]
                groups=[(0,mat,idx)]
            mesh(code,a["v"],a["n"],groups)
        m=np.array(p["matrika_lokalno_v_sestav_mm"])
        node(p["id"],code,m[:3,:3],m[:3,3],1 if "/" in p["stars"] else 0,dict(vir="STEP",pot=p["pot"],material=p["material_step"]["naziv"]))
    for s in fix:
        group=s["skupina"];code="shematski "+("kolo" if group=="kolesa" else "nosilec" if group in ("rocaj","nosilci") else "iveral")
        wood=code.endswith("iveral")
        r=3.35 if group=="kolesa" else 1.65 if wood else 2.6
        v,n,ix=hardware(r,s["prikaz_dolzine_mm"],wood) if code not in lookup else hardware_cache[code]
        if code not in lookup:
            mesh(code,v,n,[(0,"vijak · predlog",ix)])
            hardware_cache[code]=(v,n,ix)
        orient=axis_matrix(s["os"]);pos=np.array(s["glava_mm"]);pid=s["id"]
        node(pid,code,orient,pos,2,dict(vir="shematski predlog",mesto=s))
        pts=v@orient.T+pos
        parts.append(dict(id=pid,ime=s["tip_prikaza"]+" (predlog)",tip="shematsko pritrdilo",vir="predlog",stars=s["nosilec"],kolicina=1,
                          bbox_mm=dict(min=pts.min(0).tolist(),max=pts.max(0).tolist()),opomba=s["dokaz"]))
    # The hexagonal post opening can accept an insert. Show its bore separately.
    holes=read(EXPORT/"odprtine.json")
    inserts=[]
    for s in fix:
        if s["skupina"] not in ("rocaj","nosilci"):continue
        direction=np.array(s["os"]); a=np.array(s["stik_mm"])
        aligned=[np.array(h["center_mm"]) for h in holes[s["par"]] if h["os"]==1
                 and np.linalg.norm((a-np.array(h["center_mm"]))[[0,2]])<.02 and (np.array(h["center_mm"])-a)@direction>0]
        pos=min(aligned,key=lambda h:(h-a)@direction)
        # The measured opening has parallel flats normal to the CAD X axis.
        orient=axis_matrix(direction)@rotation(np.pi/6)
        # Connect concentric hexagonal loops, leaving a real open bore.
        rings=[(3.05,-.4),(5.4,-.4),(5.4,0),(4.85,0),(4.85,7),(3.05,7),(3.05,-.4)]
        polys=[]
        for (r1,z1),(r2,z2) in zip(rings,rings[1:]):
            for k in range(6):
                a0,a1=k*np.pi/3,(k+1)*np.pi/3
                pts=[(r*np.cos(t),r*np.sin(t),z) for r,z,t in [(r1,z1,a0),(r1,z1,a1),(r2,z2,a1),(r2,z2,a0)]]
                polys.extend([[pts[0],pts[1],pts[2]],[pts[0],pts[2],pts[3]]])
        verts=np.asarray(polys).reshape(-1,3);norm=np.cross(verts[1::3]-verts[::3],verts[2::3]-verts[::3])
        if "vložek" not in lookup:mesh("vložek",verts,np.repeat(norm/np.linalg.norm(norm,axis=1)[:,None],3,axis=0),
                                     [(0,"vložek · predlog",np.arange(len(verts)).reshape(-1,3))])
        pid=f"I{len(inserts)+1:03}";inserts.append(dict(id=pid,vijak=s["id"],skupina=s["skupina"],center_mm=pos.tolist()))
        node(pid,"vložek",orient,pos,2,dict(vir="shematski predlog",vijak=s["id"]))
        pts=verts@orient.T+pos
        barrel=pts[np.isclose(verts[:,2],7)]
        opening=next(h for h in holes[s["par"]] if np.linalg.norm(pos-np.array(h["center_mm"]))<.01)
        assert np.all(np.ptp(barrel[:,[0,2]],axis=0)<opening["razpon_mm"])
        parts.append(dict(id=pid,ime="Navojni vložek (predlog)",vir="predlog",tip="shematsko pritrdilo",stars=s["par"],kolicina=1,
                          bbox_mm=dict(min=pts.min(0).tolist(),max=pts.max(0).tolist()),opomba="Možna izvedba v šesterokotni odprtini stebra."))
    save(EXPORT/"vlozki.json",inserts)
    steps=sequence(parts,fix)
    for step in steps:
        step["referencni_deli"].extend(x["id"] for x in inserts if x["skupina"]==step["gibanje"].get("skupina"))
        if step["gibanje"]["tip"]=="vijak":
            start=states(step,0,sites)
            step["gibanje"]["po_delih"]={pid:dict(odmik_od_mm=shift.tolist(),odmik_do_mm=[0,0,0],os=sites[pid]["os"],
                    obrati_prikaza=1.75,vir="shematski premik") for pid,(shift,angle) in start.items()}
        step["vir_postopka"]=("Vijačenje koles je potrdil uporabnik v oceni astra/01. Izvedba pritrdila ostaja odprta."
                              if step["gibanje"].get("skupina")=="kolesa" else "Geometrija in opisi STEP, predlog postopka za tehnologa.")
    for step in steps:
        if step["gibanje"]["tip"] in ("var","prerez"):continue
        dur=step["gibanje"]["trajanje_s"]
        ts=np.linspace(0,dur,1+FPS*dur)
        times=acc(ts,"SCALAR")
        samp=[];chan=[]
        keys=[states(step,t/dur,sites) for t in ts]
        for pid in step["deli"]:
            if pid in step.get("zadrzana_mesta",[]):continue
            ni=nodeids[pid]
            xyz=g["nodes"][ni]["translation"]+np.array([B@k[pid][0]/1000 for k in keys])
            tracks=[("translation","VEC3",xyz)]
            if pid in sites:
                qs=np.array([quaternion(B@rots[pid]@rotation(k[pid][1])@B.T) for k in keys])
                for i in range(1,len(qs)):
                    if qs[i]@qs[i-1]<0:qs[i]*=-1
                tracks.append(("rotation","VEC4",qs))
            for path,kind,values in tracks:
                chan.append(dict(sampler=len(samp),target=dict(node=ni,path=path)))
                samp.append(dict(input=times,output=acc(values,kind),interpolation="LINEAR"))
        g["animations"].append(dict(name=step["naslov"],samplers=samp,channels=chan))
    held={pid for st in steps for pid in st.get("zadrzana_mesta",[])}
    parked=[nodeids[pid] for pid in sorted(held)]
    for ni in parked:
        g["nodes"][2]["children"].remove(ni)
        g["nodes"][ni]["extras"]["omejitev"]="Zadržano mesto, dostop ravnega orodja ovira kolo."
    g["scenes"].append(dict(name="Pregled vseh kandidatov, vključuje osem zadržanih mest",nodes=[0,2,len(g["nodes"])]))
    g["nodes"].append(dict(name="Zadržana mesta",children=parked))
    g["buffers"]=[dict(byteLength=len(binary))]
    j=json.dumps(g,ensure_ascii=False,separators=(",",":")).encode();j+=b" "*(-len(j)%4)
    (EXPORT/"vozicek.glb").write_bytes(struct.pack("<4sIII4s",b"glTF",2,28+len(j)+len(binary),len(j),b"JSON")+j+struct.pack("<I4s",len(binary),b"BIN\0")+binary)
    save(OUT/"deli.json",parts);save(OUT/"koraki.json",steps)

hardware_cache={}
if __name__=="__main__":build()

