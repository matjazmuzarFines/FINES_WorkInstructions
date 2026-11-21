"""Skupne funkcije: ponovno branje STEP v XCAF in vrnitev oblik po ID-jih iz deli.json."""
import json
from pathlib import Path

import numpy as np
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ShapeTool
from OCP.TDF import TDF_Label
from OCP.collections import Sequence_TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf, gp_Vec
from OCP.Interface import Interface_Static

POSKUS = Path(__file__).resolve().parents[1]
MODEL = POSKUS.parents[1]


def np_to_trsf(M):
    t = gp_Trsf()
    t.SetValues(*M[0, :4], *M[1, :4], *M[2, :4])
    return t


def _name(lab):
    a = TDataStd_Name()
    return a.Get().ToExtString() if lab.FindAttribute(TDataStd_Name.GetID_s(), a) else ""


def load_shapes():
    """Vrne {ID: TopoDS_Shape v globalnih koordinatah} po deli.json (ujemanje po imenu pojavitve)."""
    deli = json.loads((POSKUS / "deli.json").read_text(encoding="utf-8"))["deli"]
    step = sorted((MODEL / "vhod").glob("*.st*p"))[0]
    Interface_Static.SetCVal_s("xstep.cascade.unit", "MM")
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    r = STEPCAFControl_Reader()
    r.SetNameMode(True)
    r.ReadFile(str(step))
    r.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    roots = Sequence_TDF_Label()
    st.GetFreeShapes(roots)
    by_inst = {}

    def walk(lab, M):
        comps = Sequence_TDF_Label()
        XCAFDoc_ShapeTool.GetComponents_s(lab, comps, False)
        for i in range(1, comps.Length() + 1):
            c = comps.Value(i)
            ref = TDF_Label()
            XCAFDoc_ShapeTool.GetReferredShape_s(c, ref)
            loc = XCAFDoc_ShapeTool.GetLocation_s(c).Transformation()
            m = np.eye(4)
            for a in range(3):
                for b in range(4):
                    m[a, b] = loc.Value(a + 1, b + 1)
            MM = M @ m
            if XCAFDoc_ShapeTool.IsAssembly_s(ref):
                walk(ref, MM)
            else:
                by_inst[_name(c)] = (XCAFDoc_ShapeTool.GetShape_s(ref), MM)

    walk(roots.Value(1), np.eye(4))
    out = {}
    for d in deli:
        shp, M = by_inst[d["pojavitev"]]
        assert np.allclose(M, np.array(d["transformacija_mm"]), atol=1e-6), d["id"]
        out[d["id"]] = shp.Moved(TopLoc_Location(np_to_trsf(M)))
    return deli, out


def translated(shape, v):
    t = gp_Trsf()
    t.SetTranslation(gp_Vec(*v))
    return shape.Moved(TopLoc_Location(t))
