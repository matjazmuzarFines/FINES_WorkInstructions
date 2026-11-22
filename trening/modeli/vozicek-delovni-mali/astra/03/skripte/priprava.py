from osnova import OUT,EXPORT,CACHE,save
from cad import extract,walk,TopAbs_SOLID
from spoji import openings
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.TopAbs import TopAbs_IN
from OCP.gp import gp_Pnt
from pathlib import Path
import numpy as np
import itertools

WHEELS=["P122","P123","P124","P125"]
GROUPS=["kolesa","nosilci","rocaj","spodnja","srednja","zgornja"]

def inside(shape,point):
    return any(BRepClass3d_SolidClassifier(s,gp_Pnt(*point),1e-5).State()==TopAbs_IN for s in walk(shape,TopAbs_SOLID))

def collect():
    CACHE.mkdir(exist_ok=True)
    parts,meshes,worlds,stats=extract()
    for i,(code,(v,n,ix,color,solid)) in enumerate(meshes.items()):
        np.savez(CACHE/f"{code}.npz",v=v,n=n,ix=ix,color=color,solid=(solid if solid is not None else []))
    source={p["id"]:p for p in parts}
    for p in parts:
        p["material_step"]=stats["materiali"][p["ime"]]
        p["sifra_step"]=p["ime"]
        p["ime"]=p["opis"]
        p["vir"]="STEP"
    holes={pid:openings(shape) for pid,shape in worlds.items()}
    fix=[]
    def location(group,pid,mate,center,direction,width,kind,evidence):
        direction=np.asarray(direction,dtype=float)
        xyz=np.array(center,dtype=float)
        # Local +Z points from the head to the tip.
        length={"kolesa":14,"nosilci":10,"rocaj":10}.get(group,11)
        seat=xyz-direction*length if group=="kolesa" else xyz
        fix.append(dict(id=f"V{len(fix)+1:03}",skupina=group,nosilec=pid,par=mate,
                        os=direction.tolist(),stik_mm=xyz.tolist(),glava_mm=seat.tolist(),prikaz_dolzine_mm=length,
                        mera_odprtine_mm=width,tip_prikaza=kind,dokaz=evidence))
    checks=[]
    for wheel in WHEELS:
        p=source[wheel]
        z=p["bbox_mm"]["max"][2]
        sites=sorted([q for q in holes[wheel] if q["os"]==2 and abs(q["center_mm"][2]-z)<.01 and 9<min(q["razpon_mm"])<10],key=lambda q:q["center_mm"])
        assert len(sites)==4
        for site in sites:
            a=np.array(site["center_mm"])
            mates=[pid for pid in ("P113","P114","P115","P116") if inside(worlds[pid],a+[0,0,1.5])]
            assert len(mates)==1 and not inside(worlds[wheel],a-[0,0,1])
            plate=mates[0]
            probes=[inside(worlds[plate],a+[0,0,d]) for d in (.1,1.5,2.9)]
            assert all(probes)
            checks.append(dict(kolo=wheel,plosca=plate,center_mm=a.tolist(),polno_na_globinah_mm=[.1,1.5,2.9]))
            location("kolesa",wheel,plate,a,[0,0,1],site["razpon_mm"],"vijak s šestrobo glavo",
                     "Reža na prirobnici. Plošča okvirja je na osi polna. Konica prikaza se ustavi na stiku.")
    for group,pids,side in [("nosilci",["P119","P120"],12.),("rocaj",["P098","P100"],6.4)]:
        for pid in pids:
            sign=np.sign(np.mean([source[pid]["bbox_mm"][k][1] for k in ["min","max"]]))
            rows=[q for q in holes[pid] if q["os"]==1 and abs(q["razpon_mm"][0]-side)<.02]
            y=min(abs(q["center_mm"][1]) for q in rows)
            for q in sorted(rows,key=lambda a:a["center_mm"]):
                a=np.array(q["center_mm"])
                if abs(abs(a[1])-y)>.01: continue
                candidates=[post for post in ["P105","P106","P107","P108"] if any(
                    h["os"]==1 and np.linalg.norm((np.array(h["center_mm"])-a)[[0,2]])<.02
                    and 0 < (h["center_mm"][1]-a[1])*sign < 6 for h in holes[post])]
                assert len(candidates)==1
                location(group,pid,candidates[0],a,[0,sign,0],q["razpon_mm"],"vijak s šestrobo glavo",
                         "Središče odprtine nosilca se ujema z osjo šesterokotne odprtine stebra. Navojni vložek je možna izvedba.")
    for group,board,pids in [("spodnja","P118",["P101","P102"]),("srednja","P121",["P119","P120"]),("zgornja","P117",["P109","P110","P111","P112"])]:
        for pid in pids:
            for q in holes[pid]:
                size=q["razpon_mm"][0]; axis=q["os"]
                if size != (4.5 if group=="spodnja" else 5.) and size!=4.: continue
                xyz=np.array(q["center_mm"])
                direct=np.zeros(3);direct[axis]=1 if axis==2 else -np.sign(xyz[axis])
                # Keep only the outside face of the drilled steel sheet.
                if inside(worlds[board],xyz+direct*0.1): continue
                same=[np.array(h["center_mm"]) for h in holes[pid] if h["os"]==axis and h["razpon_mm"]==q["razpon_mm"]
                      and np.linalg.norm(np.delete(np.array(h["center_mm"])-xyz,axis))<.01]
                if any((v-xyz)@direct<-.01 for v in same): continue
                assert inside(worlds[board],xyz+direct*9), (q,board)
                location(group,pid,board,xyz,direct,q["razpon_mm"],"shematski vijak za ploščo",
                         "Os izvrtine v jeklu sega v iveral. Izbira uporabljenih izvrtin in vijakov je predlog.")
    counts={g:sum(x["skupina"]==g for x in fix) for g in GROUPS}
    assert list(counts.values())==[16,4,4,6,16,26],counts
    stats.update(stiki_koles=checks,stevilo_mest=counts)
    from stiki import measure
    measure(worlds)
    save(EXPORT/"odprtine.json",holes)
    save(EXPORT/"kontrola_cad.json",stats)
    save(EXPORT/"pritrdilna_mesta.json",fix)
    save(CACHE/"cad.json",parts)
    print(counts,flush=True)

if __name__=="__main__":
    collect()

