"""Sličica modela iz STEP za pregled treningov (aplikacija: Admin -> AI orodja -> AI trening).

Prebere prvi STEP v trening/modeli/<id>/vhod/ (tudi podmape, npr. vhod/step/), ga tesselira z OpenCascade
(barve delov iz STEP, če jih ima) in izriše izometrični pogled z VTK (brez okna, brez besedila).
Rezultat: trening/modeli/<id>/slika.png (640 x 480).

Zagon (okolje trening/okolje/fable):
    trening/okolje/fable/venv312/Scripts/python.exe trening/orodja/slika_modela.py <id> [--gor y|z]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.Interface import Interface_Static
from OCP.Quantity import Quantity_Color, Quantity_TypeOfColor
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_Label
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
from OCP.XCAFDoc import XCAFDoc_ColorGen, XCAFDoc_ColorSurf, XCAFDoc_ColorTool, XCAFDoc_DocumentTool, XCAFDoc_ShapeTool
from OCP.collections import Sequence_TDF_Label

KOREN = Path(__file__).resolve().parents[1]
SIVA = (0.72, 0.74, 0.77)


def srgb(c):
    """OpenCascade hrani barve linearno - za prikaz (kot v CAD) jih pretvorimo v sRGB."""
    return tuple(c.Values(Quantity_TypeOfColor.Quantity_TOC_sRGB))


def barva(ct, lab):
    c = Quantity_Color()
    for vrsta in (XCAFDoc_ColorSurf, XCAFDoc_ColorGen):
        if XCAFDoc_ColorTool.GetColor_s(lab, vrsta, c):
            return srgb(c)
    return None


def deli_iz_step(step: Path):
    """[(TopoDS_Shape v globalnih koordinatah, (r, g, b)), ...] - listni deli sestava."""
    Interface_Static.SetCVal_s("xstep.cascade.unit", "MM")
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    r = STEPCAFControl_Reader()
    r.SetColorMode(True)
    r.SetNameMode(True)
    if r.ReadFile(str(step)) != 1:
        sys.exit(f"STEP ni mogoče prebrati: {step}")
    r.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    koreni = Sequence_TDF_Label()
    st.GetFreeShapes(koreni)
    out = []

    def hodi(lab, loc, podedovana):
        b = barva(ct, lab) or podedovana
        if XCAFDoc_ShapeTool.IsAssembly_s(lab):
            komp = Sequence_TDF_Label()
            XCAFDoc_ShapeTool.GetComponents_s(lab, komp, False)
            for i in range(1, komp.Length() + 1):
                c = komp.Value(i)
                ref = TDF_Label()
                XCAFDoc_ShapeTool.GetReferredShape_s(c, ref)
                hodi(ref, loc.Multiplied(XCAFDoc_ShapeTool.GetLocation_s(c)), barva(ct, c) or b)
        else:
            # oblika brez premika (barve ploskev so vezane nanjo), premik se uporabi pri mreži
            out.append((XCAFDoc_ShapeTool.GetShape_s(lab), loc, b))

    for i in range(1, koreni.Length() + 1):
        hodi(koreni.Value(i), TopLoc_Location(), None)
    return out, ct, doc  # doc mora ostati živ, sicer ColorTool nima oznak


def barva_ploskve(ct, f):
    """STEP ima barve pogosto na ploskvah (STYLED_ITEM) - te imajo prednost pred barvo dela."""
    c = Quantity_Color()
    for vrsta in (XCAFDoc_ColorSurf, XCAFDoc_ColorGen):
        if ct.GetColor(f, vrsta, c):
            return srgb(c)
    return None


def mreza(shape, premik, ct, barva_dela, odklon, po_barvah):
    """Doda trikotnike dela v slovar {barva: ([točke], [trikotniki])}."""
    BRepMesh_IncrementalMesh(shape, odklon, False, 0.5, True)
    t_dela = premik.Transformation()
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        f = TopoDS.Face(exp.Current())
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(f, loc)
        if tri is not None:
            b = barva_ploskve(ct, f) or barva_dela or SIVA
            tocke, trikotniki = po_barvah.setdefault(tuple(round(x, 3) for x in b), ([], []))
            n = len(tocke)
            t = t_dela.Multiplied(loc.Transformation())
            for i in range(1, tri.NbNodes() + 1):
                p = tri.Node(i).Transformed(t)
                tocke.append((p.X(), p.Y(), p.Z()))
            obrni = f.Orientation() == TopAbs_REVERSED
            for i in range(1, tri.NbTriangles() + 1):
                a, bb, c = tri.Triangle(i).Get()
                trikotniki.append((n + a - 1, n + c - 1, n + bb - 1) if obrni else (n + a - 1, n + bb - 1, n + c - 1))
        exp.Next()


def actor(tocke, trikotniki, rgb):
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(tocke, deep=True))
    celice = np.hstack([np.full((len(trikotniki), 1), 3, dtype=np.int64), trikotniki]).ravel()
    ca = vtk.vtkCellArray()
    ca.ImportLegacyFormat(numpy_to_vtkIdTypeArray(celice, deep=True))
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(ca)
    normale = vtk.vtkPolyDataNormals()
    normale.SetInputData(pd)
    normale.SetFeatureAngle(35)
    m = vtk.vtkPolyDataMapper()
    m.SetInputConnection(normale.GetOutputPort())
    a = vtk.vtkActor()
    a.SetMapper(m)
    p = a.GetProperty()
    p.SetColor(*rgb)
    p.SetAmbient(0.25)
    p.SetDiffuse(0.75)
    p.SetSpecular(0.15)
    return a


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", help="ID modela (mapa trening/modeli/<id>)")
    ap.add_argument("--gor", choices=["y", "z"], default="z", help="os, ki kaže navzgor (STEP sestav: z)")
    ap.add_argument("--sirina", type=int, default=640)
    ap.add_argument("--visina", type=int, default=480)
    ap.add_argument("--barve", action="store_true", help="izpiši barve iz STEP (za preverjanje)")
    a = ap.parse_args()

    mapa = KOREN / "modeli" / a.model
    stepi = sorted(p for p in (mapa / "vhod").rglob("*") if p.suffix.lower() in (".stp", ".step"))
    if not stepi:
        sys.exit(f"V {mapa / 'vhod'} ni STEP datoteke.")
    deli, ct, _doc = deli_iz_step(stepi[0])

    po_barvah: dict = {}
    for s, premik, b in deli:
        mreza(s, premik, ct, b, 0.5, po_barvah)
    vse = [(np.array(t, dtype=float), np.array(tr, dtype=np.int64), b) for b, (t, tr) in po_barvah.items() if tr]
    if a.barve:
        for b, (_, tr) in sorted(po_barvah.items(), key=lambda x: -len(x[1][1])):
            print(f"barva {b}: {len(tr)} trikotnikov")
    if not vse:
        sys.exit("STEP nima geometrije za izris.")

    ren = vtk.vtkRenderer()
    ren.GradientBackgroundOn()
    ren.SetBackground(0.97, 0.97, 0.98)
    ren.SetBackground2(0.86, 0.88, 0.91)
    for t, tr, b in vse:
        ren.AddActor(actor(t, tr, b))

    xs = np.vstack([t for t, _, _ in vse])
    lo, hi = xs.min(0), xs.max(0)
    sredina = (lo + hi) / 2
    velikost = np.linalg.norm(hi - lo)
    gor = np.array([0, 1, 0]) if a.gor == "y" else np.array([0, 0, 1])
    smer = np.array([1.0, 0.75, 1.3]) if a.gor == "y" else np.array([1.0, -1.3, 0.75])
    smer /= np.linalg.norm(smer)

    cam = ren.GetActiveCamera()
    cam.SetFocalPoint(*sredina)
    cam.SetPosition(*(sredina + smer * velikost * 2.2))
    cam.SetViewUp(*gor)
    cam.SetViewAngle(30)
    ren.ResetCamera()
    cam.Zoom(1.15)
    ren.ResetCameraClippingRange()

    # osvetlitev s treh strani (ključna, polnilna, zadnja) - temni deli ostanejo berljivi
    luci = vtk.vtkLightKit()
    luci.SetKeyLightIntensity(0.95)
    luci.AddLightsToRenderer(ren)

    okno = vtk.vtkRenderWindow()
    okno.SetOffScreenRendering(1)
    okno.SetMultiSamples(8)
    okno.AddRenderer(ren)
    okno.SetSize(a.sirina, a.visina)
    okno.Render()

    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(okno)
    w2i.Update()
    izhod = mapa / "slika.png"
    png = vtk.vtkPNGWriter()
    png.SetFileName(str(izhod))
    png.SetInputConnection(w2i.GetOutputPort())
    png.Write()
    print(f"{izhod.relative_to(KOREN.parent)} ({len(deli)} delov, {stepi[0].name})")


if __name__ == "__main__":
    main()
