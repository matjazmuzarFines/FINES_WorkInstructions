"""
Korak 4: render videa in predogleda (VTK offscreen, PBR + okoljska osvetlitev + SSAO, ffmpeg).

Vse je krmiljeno s podatki: deli.json (materiali), spoji.json (zvari, vijaki), koraki.json (poti, spajanje, kamera).

Zagon:
  trening/okolje/fable/venv312/Scripts/python trening/modeli/vozicek-delovni-mali/fable/02/skripte/04_render.py
  ... 04_render.py --slicice     samo kontrolne slicice in predogled (hitro, brez videa)
Izhodi: video.mp4, predogled.png, izvoz/slicice/*.png, izvoz/video_casovnica.json
"""
import json
import math
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray, vtk_to_numpy

POSKUS = Path(__file__).resolve().parents[1]
IZVOZ = POSKUS / "izvoz"
SLICICE = IZVOZ / "slicice"
SLICICE.mkdir(parents=True, exist_ok=True)
SAMO_SLICICE = "--slicice" in sys.argv

OUT_W, OUT_H, FPS = 1920, 1080, 30
SS = 1.5                               # nadvzorcenje (render 2880x1620 -> lanczos na 1920x1080)
W, H = int(OUT_W * SS), int(OUT_H * SS)
FONT = "C:/Windows/Fonts/segoeui.ttf"
FONT_B = "C:/Windows/Fonts/segoeuib.ttf"
POUDAREK = np.array([1.0, 0.45, 0.05])
BARVA_NACINA = {"varjenje": (0.86, 0.33, 0.05), "vijacenje": (0.10, 0.40, 0.80), "polaganje + vijacenje": (0.10, 0.40, 0.80),
                "polaganje": (0.12, 0.55, 0.30), "zakovicenje": (0.45, 0.25, 0.70)}

POGLEDI = {   # smer od sredisca proti kameri (Z gor); "spredaj" = stran -Y, "desno" = +X (dogovor)
    "zgoraj spredaj-desno": (1.0, -1.25, 0.95),
    "spredaj-desno": (1.0, -1.3, 0.55),
    "spredaj-desno nizko": (1.0, -1.4, 0.12),
    "od spodaj": (1.0, -1.3, -0.6),
    "zadaj-levo": (-1.3, 1.0, 0.5),
    "celota": (1.0, -1.35, 0.6),
}

deli_all = json.loads((POSKUS / "deli.json").read_text(encoding="utf-8"))["deli"]
deli = [d for d in deli_all if not d["id"].startswith("V")]
koraki = json.loads((POSKUS / "koraki.json").read_text(encoding="utf-8"))["koraki"]
spoji_doc = json.loads((POSKUS / "spoji.json").read_text(encoding="utf-8"))
SPOJ = {s["id"]: s for s in spoji_doc["spoji"]}
VIJ = {v["id"]: v for v in spoji_doc["vijacni_material"]}
KOS = {k["id"]: (v, k) for v in VIJ.values() for k in v["kosi"]}
meshes = np.load(IZVOZ / "mreze.npz")
vmesh = np.load(IZVOZ / "vijaki.npz")
DEL = {d["id"]: d for d in deli}
IDS = [d["id"] for d in deli]


def px(v):
    return int(round(v * SS))


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ materiali (razred -> PBR)
def razred(d):
    return d["material_razred_step"] or d["material_razred_geometrija"]


MATERIALI = {   # barva, kovinskost, hrapavost
    "jeklo": ((0.52, 0.53, 0.55), 1.0, 0.48),
    "jeklo (plocevina / cev)": ((0.52, 0.53, 0.55), 1.0, 0.48),
    "inox": ((0.86, 0.87, 0.88), 1.0, 0.22),
    "les / iverna plosca": ((1.0, 1.0, 1.0), 0.0, 0.62),       # barvo da tekstura
    "vijak": ((0.80, 0.82, 0.86), 1.0, 0.30),
    "zvar": ((0.33, 0.34, 0.38), 1.0, 0.65),
}


def wood_texture(n=1024, seed=7):
    """Proceduralna tekstura lesa (letnice vzdolz U). Deterministicna (seed)."""
    rng = np.random.default_rng(seed)
    y = np.linspace(0, 1, n)[:, None]
    x = np.linspace(0, 1, n)[None, :]
    low = rng.random((9, 5))
    yi, xi = np.linspace(0, 8, n), np.linspace(0, 4, n)
    y0, x0 = np.clip(yi.astype(int), 0, 7), np.clip(xi.astype(int), 0, 3)
    fy, fx = (yi - y0)[:, None], (xi - x0)[None, :]
    warp = (low[y0][:, x0] * (1 - fy) * (1 - fx) + low[y0 + 1][:, x0] * fy * (1 - fx)
            + low[y0][:, x0 + 1] * (1 - fy) * fx + low[y0 + 1][:, x0 + 1] * fy * fx)
    rings = np.sin((y * 26 + warp * 3.2 + 0.25 * np.sin(x * 7)) * 2 * np.pi)
    streak = rng.random((n, 1))
    k = np.ones(5) / 5
    streak = np.convolve(streak[:, 0], k, mode="same")[:, None]
    fine = rng.random((n, n // 16)).repeat(16, axis=1)
    val = 0.80 + 0.10 * rings + 0.10 * (streak - 0.5) * 2 + 0.05 * (fine - 0.5)
    base = np.array([0.80, 0.60, 0.38])
    dark = np.array([0.52, 0.34, 0.18])
    t = np.clip((val - 0.6) / 0.4, 0, 1)[..., None]
    img = dark * (1 - t) + base * t
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def np_texture(img, srgb=True, repeat=True):
    h, w = img.shape[:2]
    im = vtk.vtkImageData()
    im.SetDimensions(w, h, 1)
    arr = numpy_to_vtk(img.reshape(-1, img.shape[2]), deep=True)
    im.GetPointData().SetScalars(arr)
    t = vtk.vtkTexture()
    t.SetInputData(im)
    t.InterpolateOn()
    t.MipmapOn()
    t.SetRepeat(repeat)
    if srgb:
        t.UseSRGBColorSpaceOn()
    return t


def environment():
    """Studijsko okolje (equirect, float): svetel strop, mehka okna za odseve na kovini."""
    h, w = 256, 512
    v = np.linspace(1, -1, h)[:, None]              # +1 zenit ... -1 tla
    u = np.linspace(0, 2 * np.pi, w)[None, :]
    lum = (0.55 + 0.45 * np.clip(v, 0, 1)) * np.where(v < 0, 0.55 + 0.25 * (1 + v), 1.0)
    img = np.ones((h, w, 3), np.float32) * lum[..., None].astype(np.float32)
    for (u0, du, v0, dv, I) in [(0.9, 0.5, 0.55, 0.25, 5.0), (2.9, 0.7, 0.45, 0.2, 3.5), (4.6, 0.5, 0.6, 0.2, 4.0), (0.0, 6.3, 0.97, 0.03, 3.0)]:
        m = (np.abs(((u - u0 + np.pi) % (2 * np.pi)) - np.pi) < du / 2) & (np.abs(v - v0) < dv / 2)
        img[np.broadcast_to(m, (h, w))] = I
    return img


def make_polydata(V, F, uv=None, cell_rgb=None):
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(np.ascontiguousarray(V, dtype=np.float64), deep=True))
    cells = np.hstack([np.full((len(F), 1), 3, dtype=np.int64), F.astype(np.int64)]).ravel()
    ca = vtk.vtkCellArray()
    ca.ImportLegacyFormat(numpy_to_vtkIdTypeArray(cells, deep=True))
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(ca)
    if cell_rgb is not None:
        a = numpy_to_vtk((np.clip(cell_rgb, 0, 1) * 255).astype(np.uint8), deep=True)
        a.SetName("rgb")
        pd.GetCellData().SetScalars(a)
    n = vtk.vtkPolyDataNormals()
    n.SetInputData(pd)
    n.SplittingOn()
    n.SetFeatureAngle(35)
    n.ConsistencyOff()
    n.AutoOrientNormalsOff()
    n.Update()
    out = n.GetOutput()
    if uv is not None:
        P = vtk_to_numpy(out.GetPoints().GetData())
        N = vtk_to_numpy(out.GetPointData().GetNormals())
        ax = np.argmax(np.abs(N), axis=1)
        tc = np.empty((len(P), 2), np.float32)
        for a_, (i, j) in {0: (1, 2), 1: (0, 2), 2: (0, 1)}.items():
            m = ax == a_
            tc[m, 0] = P[m, i] / uv
            tc[m, 1] = P[m, j] / (uv * 0.45)
        t = numpy_to_vtk(tc, deep=True)
        t.SetName("uv")
        out.GetPointData().SetTCoords(t)
    return out


def edges_actor(pd, angle=38):
    fe = vtk.vtkFeatureEdges()
    fe.SetInputData(pd)
    fe.BoundaryEdgesOff()
    fe.NonManifoldEdgesOff()
    fe.ManifoldEdgesOff()
    fe.FeatureEdgesOn()
    fe.SetFeatureAngle(angle)
    fe.ColoringOff()
    fe.Update()
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(fe.GetOutput())
    m.ScalarVisibilityOff()
    m.SetResolveCoincidentTopologyToPolygonOffset()
    m.SetRelativeCoincidentTopologyLineOffsetParameters(0, -4)
    a = vtk.vtkActor()
    a.SetMapper(m)
    p = a.GetProperty()
    p.SetColor(0.08, 0.08, 0.10)
    p.SetLineWidth(max(1.0, 1.1 * SS))
    p.SetOpacity(0.55)
    p.LightingOff()
    return a


def pbr(actor, color, metallic, rough):
    p = actor.GetProperty()
    p.SetInterpolationToPBR()
    p.SetColor(*color)
    p.SetMetallic(metallic)
    p.SetRoughness(rough)
    p.SetOcclusionStrength(1.0)


# ------------------------------------------------------------------ scena
rw = vtk.vtkRenderWindow()
rw.SetOffScreenRendering(1)
rw.SetSize(W, H)
rw.SetMultiSamples(0)
ren = vtk.vtkRenderer()
ren.SetBackground(0.80, 0.83, 0.87)
ren.SetBackground2(0.95, 0.96, 0.97)
ren.GradientBackgroundOn()
ren.UseFXAAOn()
rw.AddRenderer(ren)

env = environment()
env_tex = np_texture(env, srgb=False, repeat=False)
env_tex.SetColorModeToDirectScalars()
ren.UseImageBasedLightingOn()
ren.SetEnvironmentTexture(env_tex)
ren.SetEnvironmentUp(0, 0, 1)
ren.SetEnvironmentRight(1, 0, 0)
ren.AutomaticLightCreationOff()
key = vtk.vtkLight()
key.SetLightTypeToCameraLight()
key.SetPosition(-0.5, 0.9, 1.0)
key.SetFocalPoint(0, 0, 0)
key.SetIntensity(1.6)
ren.AddLight(key)
ren.UseSSAOOn()
ren.SetSSAORadius(45.0)
ren.SetSSAOBias(1.5)
ren.SetSSAOKernelSize(64)
ren.SetSSAOBlur(True)

wood = np_texture(wood_texture())

PART = {}       # pid -> {"actors": [...], "edges": [...], "mat": [(color, metal, rough, tex, scalars)], "center": c}
for pid in IDS:
    d = DEL[pid]
    V, F = meshes[pid + "_V"], meshes[pid + "_F"]
    r = razred(d)
    entry = {"actors": [], "edges": [], "mat": []}
    subsets = []
    if pid + "_C" in meshes.files:          # kupljen del z barvami po ploskvah (kolo)
        C = meshes[pid + "_C"].copy()
        blue = (C[:, 2] > 0.9) & (C[:, 0] < 0.7) & (C[:, 0] > 0.5)   # privzeta modra dobavitelja -> pocinkano jeklo (predpostavka)
        grey = (np.abs(C[:, 0] - C[:, 1]) < 0.01) & (np.abs(C[:, 1] - C[:, 2]) < 0.01) & (C[:, 0] > 0.5)
        metal = blue | grey
        Cm = C.copy()
        Cm[blue] = (0.74, 0.76, 0.80)
        Cm[C[:, 0] < 0] = (0.5, 0.5, 0.5)
        subsets.append((F[metal], Cm[metal], 1.0, 0.35))
        subsets.append((F[~metal], Cm[~metal], 0.0, 0.55))
    for sub in (subsets or [None]):
        if sub is None:
            color, metal_, rough = MATERIALI.get(r, ((0.7, 0.7, 0.7), 0.0, 0.6))
            is_wood = r.startswith("les")
            pd = make_polydata(V, F, uv=600.0 if is_wood else None)
        else:
            Fs, Cs, metal_, rough = sub
            color, is_wood = (1.0, 1.0, 1.0), False
            pd = make_polydata(V, Fs, cell_rgb=Cs)
        m = vtk.vtkPolyDataMapper()
        m.SetInputData(pd)
        if sub is None:
            m.ScalarVisibilityOff()
        else:
            m.SetScalarModeToUseCellData()
            m.SetColorModeToDirectScalars()
        a = vtk.vtkActor()
        a.SetMapper(m)
        pbr(a, color, metal_, rough)
        if is_wood:
            a.GetProperty().SetBaseColorTexture(wood)
        ren.AddActor(a)
        entry["actors"].append(a)
        entry["mat"].append((np.array(color), metal_, rough, sub is not None))
        e = edges_actor(pd, 50 if sub is not None else 38)
        ren.AddActor(e)
        entry["edges"].append(e)
    b = d["bbox_mm"]
    entry["center"] = (np.array(b["min"]) + np.array(b["max"])) / 2
    PART[pid] = entry

# vijacni material: en aktor na kos
FAST = {}
for kid, (v, k) in KOS.items():
    pd = make_polydata(vmesh[v["vrsta"] + "_V"], vmesh[v["vrsta"] + "_F"])
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(pd)
    m.ScalarVisibilityOff()
    a = vtk.vtkActor()
    a.SetMapper(m)
    pbr(a, *MATERIALI["vijak"])
    a.VisibilityOff()
    ren.AddActor(a)
    FAST[kid] = {"actor": a, "M": np.array(k["matrika_mm"]), "pos": np.array(k["pos_mm"]), "dir": np.array(k["smer"]),
                 "dostop": k["dostop_skozi_profil_mm"], "owner": k["skozi"]}

zmin = min(DEL[p]["bbox_mm"]["min"][2] for p in IDS)
# tla: brez ravnine (velika ravnina + SSAO da pasove); samo mehka kontaktna senca pod vozickom
_n = 256
_yy, _xx = np.mgrid[-1:1:_n * 1j, -1:1:_n * 1j]
_r = np.sqrt(np.abs(_xx) ** 2.6 + np.abs(_yy) ** 2.6)
_alpha = np.clip(1 - _r, 0, 1) ** 1.6 * 0.42
_img = np.zeros((_n, _n, 4), np.uint8)
_img[..., :3] = 30
_img[..., 3] = (_alpha * 255).astype(np.uint8)
shadow_tex = np_texture(_img, srgb=False, repeat=False)
plane = vtk.vtkPlaneSource()
plane.SetOrigin(-950, -620, zmin - 0.5)
plane.SetPoint1(950, -620, zmin - 0.5)
plane.SetPoint2(-950, 620, zmin - 0.5)
pm = vtk.vtkPolyDataMapper()
pm.SetInputConnection(plane.GetOutputPort())
floor = vtk.vtkActor()
floor.SetMapper(pm)
floor.SetTexture(shadow_tex)
floor.GetProperty().LightingOff()
floor.ForceTranslucentOn()
ren.AddActor(floor)

cam = ren.GetActiveCamera()
cam.SetViewAngle(28)


# ------------------------------------------------------------------ zvari (svetleca sled + trajna gosenica)
def resample(poly, step=3.0):
    poly = np.asarray(poly, float)
    seg = np.linalg.norm(np.diff(poly, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    if s[-1] < 1e-6:
        return poly[:1]
    n = max(2, int(s[-1] / step) + 1)
    t = np.linspace(0, s[-1], n)
    return np.stack([np.interp(t, s, poly[:, i]) for i in range(3)], axis=1)


SEAMS = {sid: [resample(p) for p in s["obod_mm"]] for sid, s in SPOJ.items() if s["tip"] == "varjenje"}


def tube_actor(radius, color, lighting=True, opacity=1.0, metallic=None):
    pd = vtk.vtkPolyData()
    tf = vtk.vtkTubeFilter()
    tf.SetInputData(pd)
    tf.SetRadius(radius)
    tf.SetNumberOfSides(10)
    tf.CappingOn()
    m = vtk.vtkPolyDataMapper()
    m.SetInputConnection(tf.GetOutputPort())
    a = vtk.vtkActor()
    a.SetMapper(m)
    if metallic is not None:
        pbr(a, color, metallic, 0.65)
    else:
        a.GetProperty().SetColor(*color)
    if not lighting:
        a.GetProperty().LightingOff()
    a.GetProperty().SetOpacity(opacity)
    a.VisibilityOff()
    ren.AddActor(a)
    return a, pd


def set_lines(pd, polylines):
    pts = vtk.vtkPoints()
    lines = vtk.vtkCellArray()
    i = 0
    for pl in polylines:
        if len(pl) < 2:
            continue
        lines.InsertNextCell(len(pl))
        for p in pl:
            pts.InsertNextPoint(*p)
            lines.InsertCellPoint(i)
            i += 1
    pd.SetPoints(pts)
    pd.SetLines(lines)
    pd.Modified()


glow_a, glow_pd = tube_actor(2.6, (1.0, 0.80, 0.35), lighting=False)
halo_a, halo_pd = tube_actor(7.0, (1.0, 0.55, 0.10), lighting=False, opacity=0.28)
arc_src = vtk.vtkSphereSource()
arc_src.SetRadius(6.0)
arc_src.SetThetaResolution(16)
arc_src.SetPhiResolution(16)
arc_pd = vtk.vtkPolyData()
arc_gl = vtk.vtkGlyph3D()
arc_gl.SetInputData(arc_pd)
arc_gl.SetSourceConnection(arc_src.GetOutputPort())
arc_m = vtk.vtkPolyDataMapper()
arc_m.SetInputConnection(arc_gl.GetOutputPort())
arc_a = vtk.vtkActor()
arc_a.SetMapper(arc_m)
arc_a.GetProperty().LightingOff()
arc_a.GetProperty().SetColor(1.0, 0.97, 0.85)
arc_a.VisibilityOff()
ren.AddActor(arc_a)
BEADS = {}      # sid -> (actor, owner pid) trajna gosenica zvara


def add_bead(sid):
    a, pd = tube_actor(1.7, MATERIALI["zvar"][0], metallic=1.0)
    set_lines(pd, SEAMS[sid])
    a.VisibilityOn()
    BEADS[sid] = (a, SPOJ[sid]["deli"][0])


def weld_progress(sids, t, offset):
    """t 0..1: sled raste po obodu; t>=1: skrij sled."""
    if t >= 1.0:
        for a in (glow_a, halo_a, arc_a):
            a.VisibilityOff()
        return
    lines, heads = [], []
    for sid in sids:
        for pl in SEAMS[sid]:
            n = max(2, int(round(len(pl) * t)) + 1)
            seg = pl[:n] + offset
            lines.append(seg)
            heads.append(seg[-1])
    set_lines(glow_pd, lines)
    set_lines(halo_pd, lines)
    pts = vtk.vtkPoints()
    for h in heads:
        pts.InsertNextPoint(*h)
    arc_pd.SetPoints(pts)
    arc_pd.Modified()
    flick = 0.8 + 0.4 * math.sin(t * 90.0)
    arc_src.SetRadius(5.0 * flick)
    for a in (glow_a, halo_a, arc_a):
        a.VisibilityOn()


# ------------------------------------------------------------------ 2D napisi
def text_actor(s="", size=24, bold=False, color=(0.1, 0.1, 0.12), bg=None, bg_op=0.92, just="left", vjust="bottom", frame=None):
    t = vtk.vtkTextActor()
    t.SetInput(s)
    p = t.GetTextProperty()
    p.SetFontFamily(vtk.VTK_FONT_FILE)
    p.SetFontFile(FONT_B if bold else FONT)
    p.SetFontSize(px(size))
    p.SetColor(*color)
    p.SetLineSpacing(1.15)
    {"left": p.SetJustificationToLeft, "right": p.SetJustificationToRight, "center": p.SetJustificationToCentered}[just]()
    {"bottom": p.SetVerticalJustificationToBottom, "top": p.SetVerticalJustificationToTop,
     "center": p.SetVerticalJustificationToCentered}[vjust]()
    if bg is not None:
        p.SetBackgroundColor(*bg)
        p.SetBackgroundOpacity(bg_op)
    if frame is not None:
        p.FrameOn()
        p.SetFrameColor(*frame)
        p.SetFrameWidth(px(2))
    ren.AddViewProp(t)
    return t


def place(t, x, y):
    t.SetDisplayPosition(int(x), int(y))


def text_size(t):
    bb = [0, 0, 0, 0]
    t.GetBoundingBox(ren, bb)
    return bb[1] - bb[0] + 1, bb[3] - bb[2] + 1


# vodilne crte (pod napisi)
lead_pd = vtk.vtkPolyData()
lead_m = vtk.vtkPolyDataMapper2D()
lead_m.SetInputData(lead_pd)
lead_a = vtk.vtkActor2D()
lead_a.SetMapper(lead_m)
lead_a.GetProperty().SetColor(0.10, 0.10, 0.12)
lead_a.GetProperty().SetLineWidth(px(2.2))
ren.AddViewProp(lead_a)
dot_pd = vtk.vtkPolyData()
dot_m = vtk.vtkPolyDataMapper2D()
dot_m.SetInputData(dot_pd)
dot_a = vtk.vtkActor2D()
dot_a.SetMapper(dot_m)
dot_a.GetProperty().SetColor(0.10, 0.10, 0.12)
dot_a.GetProperty().SetPointSize(px(9))
ren.AddViewProp(dot_a)

def panel(x0, y0, x1, y1, color=(1, 1, 1), op=0.78):
    pts = vtk.vtkPoints()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        pts.InsertNextPoint(x, y, 0)
    ca = vtk.vtkCellArray()
    ca.InsertNextCell(4)
    for i in range(4):
        ca.InsertCellPoint(i)
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(ca)
    m = vtk.vtkPolyDataMapper2D()
    m.SetInputData(pd)
    a = vtk.vtkActor2D()
    a.SetMapper(m)
    a.GetProperty().SetColor(*color)
    a.GetProperty().SetOpacity(op)
    ren.AddViewProp(a)
    return a


panel_top = panel(0, H - px(232), W, H)
panel_bot = panel(0, 0, W, px(128))
t_sklop = text_actor("", 20, bold=True, color=(0.35, 0.38, 0.45))
t_title = text_actor("", 40, bold=True)
t_badge = text_actor("", 28, bold=True, color=(1, 1, 1), bg=(0.5, 0.5, 0.5), bg_op=1.0)
t_join = text_actor("", 22, color=(0.12, 0.12, 0.16), vjust="top")
t_instr = text_actor("", 24, color=(0.08, 0.08, 0.10))
t_warn = text_actor("PREDLOG – zaporedje, način spajanja in vijačni material zahtevajo potrditev tehnologa", 18,
                    color=(0.70, 0.10, 0.05), just="right")
t_src = text_actor("MLU123069200 · STEP (Autodesk Inventor 2027)", 17, color=(0.35, 0.35, 0.4), just="right")
place(t_sklop, px(40), H - px(48))
place(t_title, px(40), H - px(104))
place(t_warn, W - px(40), px(26))
place(t_src, W - px(40), H - px(44))
place(t_instr, px(40), px(58))


def set_header(sklop, title, nacin=None, join_text=""):
    t_sklop.SetInput(sklop.upper())
    t_title.SetInput(title)
    if nacin:
        t_badge.SetInput("  " + nacin[0] + "  ")
        t_badge.GetTextProperty().SetBackgroundColor(*nacin[1])
        t_badge.VisibilityOn()
        place(t_badge, px(40), H - px(168))
        bw, _ = text_size(t_badge)
        t_join.SetInput(textwrap.fill(join_text, max(60, int((OUT_W - 110 - bw / SS) / 10.6))))
        place(t_join, px(40) + bw + px(18), H - px(126))
        t_join.VisibilityOn()
    else:
        t_badge.VisibilityOff()
        t_join.VisibilityOff()


CALLOUTS = []     # {"t": actor, "anchors": fn -> [xyz], "pos": (x, y), "size": (w, h)}
POOL = [text_actor("", 24, bold=False, color=(0.05, 0.05, 0.08), bg=(1, 1, 1), bg_op=0.95, frame=(0.10, 0.10, 0.12)) for _ in range(6)]
for p_ in POOL:
    p_.VisibilityOff()
    p_.GetTextProperty().SetLineSpacing(1.05)


def to_display(p):
    ren.SetWorldPoint(p[0], p[1], p[2], 1.0)
    ren.WorldToDisplay()
    d = ren.GetDisplayPoint()
    return np.array([d[0], d[1]])


def clear_callouts():
    CALLOUTS.clear()
    for p in POOL:
        p.VisibilityOff()
    set_leaders([], [])


def set_leaders(lines, dots):
    pts = vtk.vtkPoints()
    ca = vtk.vtkCellArray()
    i = 0
    for a, b in lines:
        pts.InsertNextPoint(a[0], a[1], 0)
        pts.InsertNextPoint(b[0], b[1], 0)
        ca.InsertNextCell(2)
        ca.InsertCellPoint(i)
        ca.InsertCellPoint(i + 1)
        i += 2
    lead_pd.SetPoints(pts)
    lead_pd.SetLines(ca)
    lead_pd.Modified()
    pts2 = vtk.vtkPoints()
    cv = vtk.vtkCellArray()
    for j, d in enumerate(dots):
        pts2.InsertNextPoint(d[0], d[1], 0)
        cv.InsertNextCell(1)
        cv.InsertCellPoint(j)
    dot_pd.SetPoints(pts2)
    dot_pd.SetVerts(cv)
    dot_pd.Modified()


def layout_callouts(specs, scene_pts):
    """specs: [(besedilo, anchors_fn)]. Napis postavi ob del (stran od sredisca prizora), brez prekrivanja."""
    clear_callouts()
    sc = np.mean([to_display(p) for p in scene_pts], axis=0) if len(scene_pts) else np.array([W / 2, H / 2])
    rects = []
    for i, (txt, fn) in enumerate(specs[:len(POOL)]):
        t = POOL[i]
        t.SetInput(txt)
        t.VisibilityOn()
        w, h = text_size(t)
        an = np.mean([to_display(p) for p in fn()], axis=0)
        dvec = an - sc
        if np.linalg.norm(dvec) < 1:
            dvec = np.array([1.0, 0.6])
        dvec = dvec / np.linalg.norm(dvec)
        if abs(dvec[0]) < 0.35:
            dvec[0] = 0.35 * (1 if dvec[0] >= 0 else -1)
        best = None
        for dist in (px(150), px(210), px(270), px(340), px(420)):
            for rot in (0, 25, -25, 50, -50, 80, -80):
                c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
                dv = np.array([dvec[0] * c - dvec[1] * s_, dvec[0] * s_ + dvec[1] * c])
                cx, cy = an + dv * dist
                x0 = min(max(cx - w / 2, px(30)), W - w - px(30))
                y0 = min(max(cy - h / 2, px(140)), H - h - px(245))
                r = (x0, y0, x0 + w, y0 + h)
                if all(r[2] < q[0] - px(10) or q[2] < r[0] - px(10) or r[3] < q[1] - px(10) or q[3] < r[1] - px(10) for q in rects):
                    best = r
                    break
            if best:
                break
        best = best or r
        rects.append(best)
        place(t, best[0], best[1])
        CALLOUTS.append({"t": t, "anchors": fn, "rect": best})


def update_callouts():
    lines, dots = [], []
    for c in CALLOUTS:
        x0, y0, x1, y1 = c["rect"]
        for p in c["anchors"]():
            d = to_display(p)
            q = np.array([min(max(d[0], x0), x1), min(max(d[1], y0), y1)])
            lines.append((q, d))
            dots.append(d)
    set_leaders(lines, dots)


# ------------------------------------------------------------------ stanje delov
STATE = {pid: {"off": np.zeros(3), "tint": 0.0, "vis": False, "op": 1.0} for pid in IDS}


def apply_part(pid):
    s, e = STATE[pid], PART[pid]
    for a, ed, (color, metal_, rough, scal) in zip(e["actors"], e["edges"], e["mat"]):
        a.SetVisibility(int(s["vis"]))
        ed.SetVisibility(int(s["vis"] and s["op"] > 0.6))
        a.SetPosition(*s["off"])
        ed.SetPosition(*s["off"])
        pr = a.GetProperty()
        t = s["tint"]
        if scal:
            a.GetMapper().SetScalarVisibility(int(t < 0.5))
            pr.SetColor(*(POUDAREK if t >= 0.5 else color))
        else:
            pr.SetColor(*(color * (1 - t) + POUDAREK * t))
        pr.SetMetallic(metal_ * (1 - 0.7 * t))
        pr.SetOpacity(s["op"])
    for sid, (a, owner) in BEADS.items():
        if owner == pid:
            a.SetPosition(*s["off"])


def set_fastener(kid, vis, back=0.0, angle=0.0, tint=1.0):
    f = FAST[kid]
    a = f["actor"]
    a.SetVisibility(int(vis))
    T = np.eye(4)
    T[2, 3] = -back
    c, s_ = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    R = np.eye(4)
    R[:2, :2] = [[c, -s_], [s_, c]]
    M = f["M"] @ T @ R
    m = vtk.vtkMatrix4x4()
    for i in range(4):
        for j in range(4):
            m.SetElement(i, j, float(M[i, j]))
    a.SetUserMatrix(m)
    col = np.array(MATERIALI["vijak"][0]) * (1 - tint) + POUDAREK * tint
    a.GetProperty().SetColor(*col)
    a.GetProperty().SetMetallic(1.0 - 0.6 * tint)


def frame_cam(pts, view, margin=1.12, fx=0.82, fy=0.66):
    pts = np.asarray(pts)
    c = (pts.min(0) + pts.max(0)) / 2
    d = np.array(view, float)
    d /= np.linalg.norm(d)
    up = np.array([0, 0, 1.0])
    right = np.cross(d, up)
    right /= np.linalg.norm(right)
    upv = np.cross(right, d)
    rel = pts - c
    half_v = math.tan(math.radians(cam.GetViewAngle() / 2))
    half_h = half_v * W / H
    # napisi zgoraj in spodaj zasedajo del slike -> koristno polje je manjse
    dist = 0
    for p in rel:
        x, y, z = p @ right, p @ upv, p @ d
        dist = max(dist, abs(x) / (half_h * fx) + z, abs(y) / (half_v * fy) + z)
    dist *= margin
    c = c - upv * 0.03 * dist          # sliko rahlo dvigni nad spodnji napis
    return c, c + d * dist


def set_cam(focal, pos):
    cam.SetFocalPoint(*focal)
    cam.SetPosition(*pos)
    cam.SetViewUp(0, 0, 1)
    floor.SetVisibility(int(pos[2] > zmin + 1.0))
    ren.ResetCameraClippingRange()


def lerp(a, b, t):
    return tuple(np.array(a) * (1 - t) + np.array(b) * t)


def bbox_corners(pid, off=np.zeros(3)):
    b = DEL[pid]["bbox_mm"]
    mn, mx = np.array(b["min"]) + off, np.array(b["max"]) + off
    return [np.array([x, y, z]) for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for z in (mn[2], mx[2])]


def path_point(pts, t):
    pts = [np.array(p, float) for p in pts]
    seg = [np.linalg.norm(b - a) for a, b in zip(pts[:-1], pts[1:])]
    total = sum(seg)
    if total < 1e-9:
        return pts[-1]
    s = t * total
    for a, b, L in zip(pts[:-1], pts[1:], seg):
        if s <= L or L == seg[-1] and b is pts[-1]:
            return a + (b - a) * (min(s, L) / L if L > 0 else 1)
        s -= L
    return pts[-1]


# ------------------------------------------------------------------ zajem
ff = None
if not SAMO_SLICICE:
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-vf", f"vflip,scale={OUT_W}:{OUT_H}:flags=lanczos",
                           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                           "-movflags", "+faststart", str(POSKUS / "video.mp4")], stdin=subprocess.PIPE)
w2i = vtk.vtkWindowToImageFilter()
w2i.SetInput(rw)
w2i.SetInputBufferTypeToRGB()
w2i.ReadFrontBufferOff()
n_frames = [0]
timeline = []


def save_png(path):
    """Shrani trenutni kader, pomanjsan na izhodno locljivost."""
    rs = vtk.vtkImageResize()
    rs.SetInputConnection(w2i.GetOutputPort())
    rs.SetOutputDimensions(OUT_W, OUT_H, 1)
    rs.InterpolateOn()
    wr = vtk.vtkPNGWriter()
    wr.SetFileName(str(path))
    wr.SetInputConnection(rs.GetOutputPort())
    wr.Write()


def grab(save=None):
    n_frames[0] += 1
    if n_frames[0] % 300 == 0:
        print("slicica", n_frames[0], flush=True)
    if SAMO_SLICICE and not save:
        return
    update_callouts()
    rw.Render()
    w2i.Modified()
    w2i.Update()
    if ff:
        ff.stdin.write(vtk_to_numpy(w2i.GetOutput().GetPointData().GetScalars()).tobytes())
    if save:
        save_png(save)


def run(seconds, fn, save=None, save_at=0.5):
    n = max(1, int(round(seconds * FPS)))
    k_save = int(save_at * (n - 1))
    for i in range(n):
        fn(i / (n - 1) if n > 1 else 1.0)
        grab(save if (save and i == k_save) else None)


all_pts = [p for pid in IDS for p in bbox_corners(pid)]


def orbit_view(az_deg):
    base = np.array(POGLEDI["celota"])
    r = math.hypot(base[0], base[1])
    ang = math.atan2(base[1], base[0]) + math.radians(az_deg)
    return (r * math.cos(ang), r * math.sin(ang), base[2])


def show_all(final=True):
    for pid in IDS:
        STATE[pid].update(off=np.zeros(3), tint=0.0, vis=True, op=1.0)
        apply_part(pid)
    for kid in FAST:
        set_fastener(kid, final, 0, 0, 0.0)


# povzetek spajanja za uvod/zakljucek
n_zvar = sum(1 for s in SPOJ.values() if s["tip"] == "varjenje")
vij_povzetek = ", ".join(f"{v['kolicina']}x {v['ime'].replace(' (predpostavka)', '')}" for v in VIJ.values())
sk = {}
for v in VIJ.values():
    sk[v["ime"].replace(" (predpostavka)", "")] = sk.get(v["ime"].replace(" (predpostavka)", ""), 0) + v["kolicina"]
vij_povzetek = " · ".join(f"{n}x {k}" for k, n in sk.items())

# ------------------------------------------------------------------ predogled.png
show_all(True)
for sid in SEAMS:
    add_bead(sid)
set_cam(*frame_cam(all_pts, POGLEDI["celota"], 1.05))
set_header("MLU123069200 · končni sestav", "Voziček proizvodni montažni 1000x500 h=890")
POVZETEK = textwrap.fill(f"28 delov iz STEP · {n_zvar} varjenih stikov · vijačni material (predpostavka iz lukenj, ni v STEP): "
                         f"{vij_povzetek}", 135)
t_instr.SetInput(POVZETEK)
rw.Render()
w2i.Modified()
w2i.Update()
save_png(POSKUS / "predogled.png")

# ------------------------------------------------------------------ uvod
timeline.append((0.0, "uvod: celoten sestav"))


def intro(t):
    set_cam(*frame_cam(all_pts, orbit_view(-25 + 50 * ease(t)), 1.05))


set_header("Montažno navodilo – predlog", "Voziček proizvodni montažni 1000x500 h=890")
t_instr.SetInput("Sklopi: A. zvarjenec okvirja (varjenje)  ·  B. končna montaža (vijačenje, polaganje)  ·  C. podsestav ročaja (varjenje)")
run(4.5, intro, save=SLICICE / "uvod.png")

# ponastavi: vse skrito
for pid in IDS:
    STATE[pid].update(vis=False)
    apply_part(pid)
for kid in FAST:
    set_fastener(kid, False)
for sid, (a, _) in list(BEADS.items()):
    ren.RemoveActor(a)
BEADS.clear()

# ------------------------------------------------------------------ koraki
prev_cam = None
for k in koraki:
    st = k["st"]
    ids = k["deli_step"]
    paths = {p: [np.array(q, float) for q in v] for p, v in k["gibanje"]["pot_po_delih_mm"].items()}
    end_off = np.array(k["gibanje"]["do_mm"], float)
    sp = k["spajanje"]
    nacin = sp["nacin"]
    view = POGLEDI[k["kamera"]["pogled"]]
    kosi = [kid for g in sp["vijacni_material"] for kid in g["kosi"]]
    seams = [sid for sid in sp["spoji"] if sid in SEAMS]
    visible_now = [p for p in IDS if STATE[p]["vis"]]

    pts = [c for p in visible_now for c in bbox_corners(p, STATE[p]["off"])]
    for p in ids:
        for q in paths[p]:
            pts += bbox_corners(p, q)
    if not ids:
        pts += all_pts[:0] or [c for p in visible_now for c in bbox_corners(p)]
    main_cam = frame_cam(pts, view, 1.06)
    timeline.append((n_frames[0] / FPS, f"korak {st}: {k['naslov']} ({sp['napis']})"))

    set_header(k["sklop"], f"Korak {st}/{len(koraki)}: {k['naslov']}", (sp["napis"], BARVA_NACINA.get(nacin, (0.4, 0.4, 0.4))), sp["opis"])
    t_instr.SetInput(textwrap.fill(k["opis"], 135))
    clear_callouts()

    # --- napisi ob delih (ime + kolicina; sifra in ID drobno za sledljivost)
    groups = {}
    for p in ids:
        groups.setdefault(DEL[p]["sifra"], []).append(p)
    specs = []
    for sif, pl in groups.items():
        ime = " ".join(DEL[pl[0]]["ime"].split())
        ime = ime[0].upper() + ime[1:]
        kol = f"{len(pl)}x  " if len(pl) > 1 else ""
        idr = pl[0] if len(pl) == 1 else f"{pl[0]}–{pl[-1]}" if int(pl[-1][1:]) - int(pl[0][1:]) == len(pl) - 1 else ", ".join(pl)
        txt = f" {kol}{ime} \n {sif} · {idr} "
        specs.append((txt, (lambda pl=pl: [PART[p]["center"] + STATE[p]["off"] for p in pl])))

    # 1) prehod kamere, deli se pojavijo v izhodiscu
    c0 = prev_cam or main_cam
    for p in ids:
        STATE[p].update(off=paths[p][0].copy(), tint=1.0, vis=True, op=0.0)
        apply_part(p)
    set_cam(*main_cam)
    if specs:
        layout_callouts(specs, pts)

    def ph1(t):
        e = ease(t)
        set_cam(lerp(c0[0], main_cam[0], e), lerp(c0[1], main_cam[1], e))
        for p in ids:
            STATE[p]["op"] = e
            apply_part(p)
    run(1.0, ph1)

    # 2) premik po poti
    if ids:
        def ph2(t):
            e = ease(t)
            for p in ids:
                STATE[p]["off"] = path_point(paths[p], e)
                apply_part(p)
        run(float(k["gibanje"]["trajanje_s"]) * (1.5 if len(next(iter(paths.values()))) > 2 else 1.0), ph2,
            save=SLICICE / f"korak_{st:02d}_a_premik.png", save_at=0.55)
        run(0.5, lambda t: None)

    # 3) spajanje (detajlni pogled)
    items = [np.mean(np.vstack(SEAMS[sid]), axis=0) + end_off for sid in seams] + [FAST[kid]["pos"] for kid in kosi]
    if items:
        items = np.array(items)
        campos = np.array(main_cam[1])
        seed = items[np.argmin(np.linalg.norm(items - campos, axis=1))]
        cl = items[np.linalg.norm(items - seed, axis=1) < 190.0]
        cc = cl.mean(0)
        pad = 50.0
        dpts = [cc + np.array([sx, sy, sz]) * pad for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)] + list(cl)
        det_cam = frame_cam(dpts, view, 1.0, fx=0.72, fy=0.60)
        clear_callouts()
        # deli tega koraka ostanejo rahlo poudarjeni
        for p in ids:
            STATE[p]["tint"] = 0.0      # med spajanjem pravi material, da se zvar / vijak jasno vidi
            apply_part(p)
        run(0.9, lambda t: set_cam(lerp(main_cam[0], det_cam[0], ease(t)), lerp(main_cam[1], det_cam[1], ease(t))))
        in_cl = lambda q: np.linalg.norm(q - seed) < 190.0   # noqa: E731
        if seams:
            sp_specs = [(" Zvar po obodu stika \n vrsta in mera zvara: ni znano ",
                         lambda: [np.mean(np.vstack(SEAMS[sid]), axis=0) + end_off for sid in seams
                                  if in_cl(np.mean(np.vstack(SEAMS[sid]), axis=0) + end_off)][:4])]
            layout_callouts(sp_specs, dpts)
            run(2.6, lambda t: weld_progress(seams, t, end_off), save=SLICICE / f"korak_{st:02d}_b_spoj.png", save_at=0.6)
            weld_progress(seams, 1.0, end_off)
            for sid in seams:
                add_bead(sid)
                BEADS[sid][0].SetPosition(*end_off)
            run(0.6, lambda t: None)
        if kosi:
            sp_specs = []
            for g in sp["vijacni_material"]:
                gk = [kid for kid in g["kosi"] if in_cl(FAST[kid]["pos"])]
                if gk:
                    v = VIJ[g["id"]]
                    sp_specs.append((f" {g['kolicina']}x  {v['ime'].replace(' (predpostavka)', '')} \n predpostavka iz lukenj · ni v STEP · {g['id']} ",
                                     (lambda gk=gk: [FAST[kid]["pos"] - FAST[kid]["dir"] * FAST[kid]["_back"] for kid in gk][:6])))
            is_nut = nacin == "zakovicenje"
            for kid in kosi:
                FAST[kid]["_back"] = 45.0 + FAST[kid]["dostop"]

            def ph_screw(t):
                e = ease(min(1.0, t / 0.85))
                for kid in kosi:
                    b0 = 45.0 + FAST[kid]["dostop"]
                    FAST[kid]["_back"] = b0 * (1 - e)
                    set_fastener(kid, True, FAST[kid]["_back"], 0 if is_nut else 1440.0 * e, tint=1.0)
            ph_screw(0.0)
            layout_callouts(sp_specs, dpts)
            run(3.0, ph_screw, save=SLICICE / f"korak_{st:02d}_b_spoj.png", save_at=0.45)
            run(0.5, lambda t: [set_fastener(kid, True, 0, 0, tint=1 - ease(t)) for kid in kosi])
        clear_callouts()
        run(0.9, lambda t: set_cam(lerp(det_cam[0], main_cam[0], ease(t)), lerp(det_cam[1], main_cam[1], ease(t))))

    # 4) konec koraka: prava barva materiala
    def ph4(t):
        for p in ids:
            STATE[p]["tint"] = (0.0 if len(items) else 1.0) * (1 - ease(t))
            apply_part(p)
    run(0.6, ph4, save=SLICICE / f"korak_{st:02d}_c_konec.png", save_at=1.0)
    clear_callouts()
    prev_cam = main_cam

# ------------------------------------------------------------------ zakljucek
show_all(True)
timeline.append((n_frames[0] / FPS, "zakljucek: koncni sestav"))
set_header("MLU123069200 · končni sestav", "Končni sestav")
t_instr.SetInput(POVZETEK)
fin = frame_cam(all_pts, orbit_view(0), 1.05)
run(1.0, lambda t: set_cam(lerp(prev_cam[0], fin[0], ease(t)), lerp(prev_cam[1], fin[1], ease(t))))
run(6.0, lambda t: set_cam(*frame_cam(all_pts, orbit_view(70 * ease(t)), 1.05)), save=SLICICE / "zakljucek.png")

if ff:
    ff.stdin.close()
    ff.wait()
dolzina = n_frames[0] / FPS
(IZVOZ / "video_casovnica.json").write_text(json.dumps(
    {"fps": FPS, "velikost": [OUT_W, OUT_H], "nadvzorcenje": SS, "slicic": n_frames[0], "dolzina_s": round(dolzina, 2),
     "poglavja": [{"cas_s": round(t, 2), "opis": d} for t, d in timeline]}, ensure_ascii=False, indent=2), encoding="utf-8")
print("slicic", n_frames[0], "dolzina", round(dolzina, 1), "s, ffmpeg", ff.returncode if ff else "ni (samo slicice)")
