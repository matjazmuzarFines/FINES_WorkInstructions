from osnova import OUT, EXPORT, save
from cad import extract
import json
import struct
import numpy as np
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepGProp import BRepGProp
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Pnt, gp_Trsf, gp_Vec
from OCP.TopLoc import TopLoc_Location

FPS = 25
BASIS = np.array([[1.,0,0],[0,0,1],[0,-1,0]])
MATERIALS = {
    "ogrodje": ([0.34, 0.45, 0.53], 0.52, 0.38),
    "polica": ([0.70, 0.49, 0.27], 0., 0.60),
    "kolo": ([0.22, 0.26, 0.29], 0.30, 0.45),
}


def material(p):
    return "polica" if "lesena" in p["opis"] else "kolo" if p["telesa"] > 1 else "ogrodje"


def steps():
    common = "ni znano / zahteva potrditev"
    data = [
        ("P123", "Kolo pod ploščo", "Kolo P123 približaj plošči P113 od spodaj. Končni položaj in zasuk sta prevzeta iz STEP-a.", -105, "P113",
         [-465,-160,571], [-0.66,-1,0.29], 580),
        ("P117", "Zgornja polica", "Polico P117 spusti med zgornje povezave. Daljši rob ostane vzporeden z daljšo stranico vozička.", 145, "P110",
         [-5,0,1215], [-0.59,-1,0.57], 1460),
    ]
    return [dict(st=i, naslov=name, opis=desc, deli=[pid], referencni_deli=[ref],
                 gibanje=dict(tip="premik",od_mm=[0,0,z],do_mm=[0,0,0],trajanje_s=3.2, interpolacija="gladki kubični prehod"),
                 kamera=dict(pogled="Ortografski pogled s strani ročaja in sprednje stranice",cilj_mm=target,smer_proti_kameri=direction,sirina_mm=width),
                 opozorila=["Samostojen geometrijski prikaz. Vrstni red, podpiranje vozička, pritrditev, orodje in momenti zahtevajo potrditev tehnologa."],
                 potrditev=common)
            for i,(pid,name,desc,z,ref,target,direction,width) in enumerate(data,1)]


def check_paths(parts, worlds, moves):
    checks = {}
    for step in moves:
        pid, = step["deli"]
        part = next(p for p in parts if p["id"] == pid)
        offset = np.asarray(step["gibanje"]["od_mm"])
        lo = np.array(part["bbox_mm"]["min"]) + np.minimum(offset, 0)
        hi = np.array(part["bbox_mm"]["max"]) + np.maximum(offset, 0)
        swept = BRepPrimAPI_MakeBox(gp_Pnt(*lo), gp_Pnt(*hi)).Shape()
        candidates = {}
        for other in parts:
            if other["id"] == pid:
                continue
            b = other["bbox_mm"]
            if np.any(np.minimum(hi, b["max"]) - np.maximum(lo, b["min"]) <= 0.0001):
                continue
            test = BRepAlgoAPI_Common(swept, worlds[other["id"]])
            assert test.IsDone()
            props = GProp_GProps()
            BRepGProp.VolumeProperties_s(test.Shape(), props)
            candidates[other["id"]] = round(abs(props.Mass()),6)
        samples = {}
        for dz in [0, 0.5, 2, 8, 16, 25]:
            t = gp_Trsf()
            t.SetTranslation(gp_Vec(0, 0, dz * float(np.sign(offset[2]))))
            moved = worlds[pid].Moved(TopLoc_Location(t))
            values = {}
            for oid in candidates:
                op = BRepAlgoAPI_Common(moved, worlds[oid])
                assert op.IsDone()
                prop = GProp_GProps()
                BRepGProp.VolumeProperties_s(op.Shape(), prop)
                values[oid] = round(abs(prop.Mass()), 6)
            samples[str(dz)] = values
        checks[pid] = dict(od_mm=offset.tolist(),prekrivanje_ovojnice_mm3=candidates, dejanski_preseki_mm3_po_odmiku_mm=samples,
                           prag_mm=0.0001, najvecji_presek_mm3=max(candidates.values(),default=0.))
    return checks


def write_glb(parts, meshes, stats, moves):
    g = dict(asset=dict(version="2.0", generator="Astra / Open CASCADE"), scene=0,
             scenes=[dict(nodes=[0])], nodes=[dict(name=stats["koren"], children=[])],
             meshes=[], accessors=[], bufferViews=[], materials=[], animations=[])
    binary = bytearray()

    def accessor(values, kind, target=None):
        arr = np.ascontiguousarray(values)
        assert arr.dtype in (np.dtype("<f4"), np.dtype("<u4"))
        view = dict(buffer=0, byteOffset=len(binary), byteLength=arr.nbytes)
        if target:
            view["target"] = target
        g["bufferViews"].append(view)
        binary.extend(arr.tobytes())
        rows = arr.reshape(-1, int(kind[-1]) if kind.startswith("VEC") else 1)
        acc = dict(bufferView=len(g["bufferViews"])-1, componentType=5126 if arr.dtype.kind == "f" else 5125,
                   count=len(rows), type=kind, min=rows.min(0).tolist(), max=rows.max(0).tolist())
        g["accessors"].append(acc)
        return len(g["accessors"])-1

    for name,(color,metal,roughness) in MATERIALS.items():
        g["materials"].append(dict(name=name, pbrMetallicRoughness=dict(baseColorFactor=color+[1], metallicFactor=metal, roughnessFactor=roughness)))
    mesh_ids = {}
    for code,(v,n,idx) in meshes.items():
        p = next(p for p in parts if p["ime"] == code)
        attrs = dict(POSITION=accessor(((v@BASIS.T)/1000).astype("<f4"),"VEC3",34962),
                     NORMAL=accessor((n@BASIS.T).astype("<f4"),"VEC3",34962))
        mesh_ids[code] = len(g["meshes"])
        g["meshes"].append(dict(name=code, primitives=[dict(attributes=attrs, indices=accessor(idx.ravel(),"SCALAR",34963),
                                                           material=list(MATERIALS).index(material(p)))]))
    parents = {stats["koren"]:0}
    for sub in stats["podsestavi"]:
        parents[sub["pot"]] = len(g["nodes"])
        g["nodes"][0]["children"].append(len(g["nodes"]))
        g["nodes"].append(dict(name=sub["sifra"], extras=sub, children=[]))
    node_ids = {}
    for p in parts:
        m = np.array(p["matrika_lokalno_v_sestav_mm"])
        tr = gp_Trsf()
        tr.SetValues(*np.column_stack((BASIS@m[:3,:3]@BASIS.T, np.zeros(3))).ravel())
        q = tr.GetRotation()
        node_ids[p["id"]] = len(g["nodes"])
        g["nodes"][parents[p["stars"]]]["children"].append(len(g["nodes"]))
        g["nodes"].append(dict(name=p["id"],mesh=mesh_ids[p["ime"]],translation=(BASIS@m[:3,3]/1000).tolist(),
                               rotation=[q.X(),q.Y(),q.Z(),q.W()],extras=dict(pot=p["pot"],opis=p["opis"],telesa=p["telesa"])))
    for step in moves:
        pid, = step["deli"]
        ni = node_ids[pid]
        dest = np.array(g["nodes"][ni]["translation"])
        delta = BASIS@step["gibanje"]["od_mm"]/1000
        duration = step["gibanje"]["trajanje_s"]
        ts = np.linspace(0, duration, round(duration*FPS)+1)
        u = ts/duration
        xyz = dest + (1-u*u*(3-2*u))[:,None]*delta
        g["animations"].append(dict(name=pid+" · "+step["naslov"],
                 samplers=[dict(input=accessor(ts.astype("<f4"),"SCALAR"),output=accessor(xyz.astype("<f4"),"VEC3"),interpolation="LINEAR")],
                 channels=[dict(sampler=0,target=dict(node=ni,path="translation"))]))
    g["buffers"]=[dict(byteLength=len(binary))]
    header=json.dumps(g,ensure_ascii=False,separators=(",",":")).encode()
    header+=b" "*(-len(header)%4)
    with (EXPORT/"vozicek.glb").open("wb") as stream:
        stream.write(struct.pack("<4sII",b"glTF",2,28+len(header)+len(binary)))
        stream.write(struct.pack("<I4s",len(header),b"JSON")+header)
        stream.write(struct.pack("<I4s",len(binary),b"BIN\0")+binary)


def build():
    parts, meshes, worlds, stats = extract()
    moves = steps()
    stats["poti"] = check_paths(parts,worlds,moves)
    for step in moves:
        pid, = step["deli"]
        end = stats["poti"][pid]["dejanski_preseki_mm3_po_odmiku_mm"]["0"]
        touches = [oid for oid,v in end.items() if v>0.001]
        if touches:
            step["opozorila"].append("V končni legi CAD zazna prostorninski presek z deli "+", ".join(touches)+". Naleganje zahteva pregled konstruktorja.")
    write_glb(parts,meshes,stats,moves)
    save(OUT/"deli.json",parts)
    save(OUT/"koraki.json",moves)
    save(EXPORT/"kontrola_cad.json",stats)
    print(stats["poti"])


if __name__ == "__main__":
    build()

