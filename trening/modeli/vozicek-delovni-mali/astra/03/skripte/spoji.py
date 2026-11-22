from osnova import OUT, EXPORT, SOURCE, save
from cad import bounds, walk
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane
from OCP.BRepTools import BRepTools
from OCP.TopAbs import TopAbs_FACE, TopAbs_WIRE
from OCP.TopoDS import TopoDS
import numpy as np


def openings(shape):
    result=[]
    for item in walk(shape,TopAbs_FACE):
        face=TopoDS.Face(item)
        surface=BRepAdaptor_Surface(face)
        if surface.GetType()!=GeomAbs_Plane:
            continue
        normal=np.abs(surface.Plane().Axis().Direction().Coord())
        axis=int(np.argmax(normal))
        if normal[axis]<0.9999:
            continue
        outer=BRepTools.OuterWire_s(face)
        for wire in walk(face,TopAbs_WIRE):
            if wire.IsSame(outer):
                continue
            box=bounds(wire)
            lo,hi=np.array(box["min"]),np.array(box["max"])
            width=np.delete(hi-lo,axis)
            if width.min()<2 or width.max()>25:
                continue
            result.append(dict(os=axis,center_mm=((hi+lo)/2).round(4).tolist(),razpon_mm=width.round(4).tolist()))
    return result

if __name__=="__main__":
    from cad import extract
    p,m,w,s=extract(False)
    holes={pid:openings(shape) for pid,shape in w.items()}
    save(EXPORT/"odprtine.json",holes)
    for pid in ["P113","P123","P098","P107","P117","P118","P119"]:
        print(pid,[h for h in holes[pid] if pid!="P123" or h["center_mm"][2]>564],flush=True)

