"""Časovni potek, smeri in izvor geometrije za prikaz vozička."""
from osnova import EXPORT,read
import numpy as np

FPS = 25
FRAME = [f"P{i:03}" for i in range(101,117)]
WHEELS = ["P123","P125","P124","P122"]
HANDLE = ["P098","P099","P100"]
RAILS = ["P119","P120"]

def smooth(x):
    t = float(np.clip(x, 0, 1))
    return t*t*(3-2*t)

def axis_matrix(axis):
    z = np.asarray(axis, dtype=float)
    x = np.array([1.,0,0]) if abs(z[0])<.9 else np.array([0.,1,0])
    return np.column_stack((x,np.cross(z,x),z))

def sequence(parts, fix):
    rows = []
    def add(title, mode, ids, seconds, **settings):
        rows.append(dict(st=len(rows)+1, naslov=title, deli=ids,
            referencni_deli=settings.pop("refs",[]), kamera=dict(pogled="Celota in približanje mestu dela"),
            gibanje=dict(tip=mode,trajanje_s=seconds,**settings),
            opozorila=["Zaporedje, podpiranje in izbira orodja zahtevajo potrditev."],
            potrditev="ni znano / zahteva potrditev"))
        return rows[-1]
    def place(title,ids,offset):
        s=add(title,"premik",ids,5,od_mm=offset,do_mm=[0,0,0])
        s["opis"]="Prikaz približevanja v končno lego iz STEP. Smer je predlog."
    def weld(title,i,pair):
        s=add(title,"var",pair,5,stik=i)
        s["opis"]="Primer dela na vidnem odseku skupnega roba. Potek in mera zvara zahtevata varilno risbo."
    def screws(title,group,host_order):
        candidates=[s for s in fix if s["skupina"]==group]
        order=[]
        for host in host_order:
            current=[s for s in candidates if s["nosilec"]==host]
            # Keep equal access directions together and move along the same edge.
            current.sort(key=lambda s:(s["os"],s["stik_mm"]))
            order.extend(current)
        ids=[s["id"] for s in order]
        assert len(order)==len(candidates)
        s=add(title,"vijak",ids,3+3*len(ids),skupina=group,
              refs=sorted({p for q in order for p in (q["par"],q["nosilec"])}))
        s["opis"]="Vsako mesto je prikazano posebej po osi odprtine. Pritrdilo in orodje sta shematska."
        if group=="kolesa":
            s["opozorila"].append("Pritrditev koles z vijaki je potrjena v oceni 01. Na osi reže je plošča polna. Konica se ustavi ob plošči.")
            access=read(EXPORT/"dostop_koles.json")
            s["zadrzana_mesta"]=[pid for pid in ids if access[pid][0] is not None]
            s["opis"]+=" Na zadržanih mestih je prikazan ločen vijak ob označeni reži. Ravno orodje bi zadelo kolo."
    for i,(title,pair) in enumerate([
        ("Spodnji cevi",["P101","P104"]),("Plošča kolesa",["P113","P101"]),
        ("Steber in zgornja povezava",["P108","P110"]),("Vogal zgornjega okvira",["P110","P112"])]):
        weld(title,i,pair)
    place("Kolesa z zavoro",WHEELS,[0,0,-65])
    screws("Vijaki koles","kolesa",WHEELS)
    weld("Cev ročaja in sprednji nosilec",4,["P099","P100"])
    weld("Cev ročaja in zadnji nosilec",5,["P099","P098"])
    place("Ročaj",HANDLE,[-110,0,0])
    screws("Nosilca ročaja","rocaj",["P100","P098"])
    # These rails are on opposite sides. Show each short approach separately.
    place("Sprednja vmesna povezava",["P120"],[0,23,0])
    place("Zadnja vmesna povezava",["P119"],[0,-23,0])
    screws("Vijaki vmesnih povezav","nosilci",["P120","P119"])
    for title,pid,group,hosts in [
            ("Spodnja polica","P118","spodnja",["P101","P102"]),
            ("Srednja polica","P121","srednja",["P120","P119"]),
            ("Zgornja polica","P117","zgornja",["P110","P111","P109","P112"])]:
        place(title,[pid],[0,0,62])
        screws("Vijaki • "+title.lower(),group,hosts)
    return rows

def screw_phase(step,seconds):
    t=max(0.,seconds-2.0)
    n=len(step["deli"])
    i=min(int(t//3),n-1)
    return i, min(3.,t-i*3)

def states(step,p,sites):
    g=step["gibanje"]
    if g["tip"]=="premik":
        shift=np.array(g["od_mm"])*(1-smooth((p-.19)/.58))
        return {pid:(shift,0.) for pid in step["deli"]}
    if g["tip"]!="vijak":
        return {}
    t=p*g["trajanje_s"]-2.0
    values={}
    for i,pid in enumerate(step["deli"]):
        if pid in step.get("zadrzana_mesta",[]):continue
        phase=t-3*i
        s=sites[pid]
        # Free approach to entry, then slow axial feed during rotation.
        travel=48 if g["skupina"]=="spodnja" else 22
        engage=5 if g["skupina"]=="kolesa" else 8
        shift=travel-(travel-engage)*smooth((phase-.55)/.52)-engage*smooth((phase-1.07)/.95)
        angle=2*np.pi*1.75*smooth((phase-1.07)/.95)
        values[pid]=(-np.array(s["os"])*shift,angle)
    return values
