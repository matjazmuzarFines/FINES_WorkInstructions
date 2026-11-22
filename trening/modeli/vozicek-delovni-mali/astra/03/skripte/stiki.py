from osnova import EXPORT,save
from cad import walk,bounds,extract
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section,BRepAlgoAPI_Common
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf,gp_Vec
import numpy as np

def measure(worlds):
    contacts=[]
    for title,a,b in [("Spodnji cevi","P101","P104"),("Plošča kolesa in cev","P113","P101"),
                      ("Steber in zgornja povezava","P108","P110"),("Vogal zgornjega okvira","P110","P112"),
                      ("Ročaj pri sprednjem nosilcu","P099","P100"),("Ročaj pri zadnjem nosilcu","P099","P098")]:
        op=BRepAlgoAPI_Section(worlds[a],worlds[b],False);op.Build()
        assert op.IsDone()
        edges=[]
        for item in walk(op.Shape(),TopAbs_EDGE):
            edge=TopoDS.Edge(item);c=BRepAdaptor_Curve(edge)
            points=np.array([c.Value(t).Coord() for t in np.linspace(c.FirstParameter(),c.LastParameter(),25)])
            length=np.linalg.norm(np.diff(points,axis=0),axis=1).sum()
            if length>2:edges.append((length,points))
        if edges:
            _,pts=max(edges,key=lambda q:q[0])
            contacts.append(dict(ime=title,deli=[a,b],st_robov=len(edges),
                                 kandidati_mm=[np.round(p,4).tolist() for _,p in edges]))
        else:contacts.append(dict(ime=title,deli=[a,b],st_robov=0,sticni_rob_mm=[]))
    shelf={}
    for offset in [0,.5]:
        t=gp_Trsf();t.SetTranslation(gp_Vec(0,0,offset))
        board=worlds["P117"].Moved(TopLoc_Location(t))
        values={}
        for pid in ["P109","P110","P111","P112"]:
            common=BRepAlgoAPI_Common(board,worlds[pid]);assert common.IsDone()
            props=GProp_GProps();BRepGProp.VolumeProperties_s(common.Shape(),props)
            values[pid]=round(abs(props.Mass()),5)
        shelf[str(offset)]=values
    save(EXPORT/"stiki_ogrodja.json",contacts);save(EXPORT/"naleganje_police.json",shelf)
    print([(s["ime"],s["st_robov"]) for s in contacts],shelf,flush=True)
if __name__=="__main__":
    measure(extract(False)[2])

