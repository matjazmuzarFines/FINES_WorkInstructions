"""Meritev razdalje od shematske glave proti kolesu na osi orodja."""
from osnova import EXPORT,read,save
from cad import extract
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Pnt,gp_Dir,gp_Lin
import numpy as np

def wheel_access():
    worlds=extract(False)[2]
    sites=[s for s in read(EXPORT/"pritrdilna_mesta.json") if s["skupina"]=="kolesa"]
    result={}
    for site in sites:
        origin=np.array(site["glava_mm"])
        test=IntCurvesFace_ShapeIntersector()
        test.Load(worlds[site["nosilec"]],1e-7)
        samples=[]
        for xy in [[0,0]]+[[5.9*np.cos(t),5.9*np.sin(t)] for t in np.arange(8)*np.pi/4]:
            p=origin+[*xy,0.]
            test.Perform(gp_Lin(gp_Pnt(*p),gp_Dir(0,0,-1)),0.001,110)
            hit=min((test.WParameter(i) for i in range(1,test.NbPnt()+1)),default=None)
            samples.append(round(hit,3) if hit is not None else None)
        result[site["id"]]=samples
    save(EXPORT/"dostop_koles.json",result)
    return result

if __name__=="__main__":print(wheel_access())
