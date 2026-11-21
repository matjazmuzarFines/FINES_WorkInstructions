"""
Korak 3: render videa in predogleda iz izvoz/mreze.npz + deli.json + koraki.json (VTK offscreen + ffmpeg).

Animacija je v celoti krmiljena s koraki.json (deli, odmiki, trajanje, pogled kamere) -
popravek koraka = popravek JSON + ponoven zagon te skripte.

Zagon:
  trening/okolje/fable/venv312/Scripts/python trening/modeli/vozicek-delovni-mali/fable/01/skripte/03_render.py
Izhodi: video.mp4, predogled.png, izvoz/slicice/*.png (kontrolne slicice)
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray, vtk_to_numpy

POSKUS = Path(__file__).resolve().parents[1]
IZVOZ = POSKUS / "izvoz"
SLICICE = IZVOZ / "slicice"
SLICICE.mkdir(parents=True, exist_ok=True)

W, H, FPS = 1920, 1080, 30
FONT = "C:/Windows/Fonts/segoeui.ttf"
FONT_B = "C:/Windows/Fonts/segoeuib.ttf"
POUDAREK = (1.0, 0.50, 0.05)
NAMESCENO = (0.70, 0.71, 0.73)

# pogledi: smer od sredisca proti kameri (Z gor). "spredaj" = stran -Y, "desno" = +X (dogovor, glej porocilo).
POGLEDI = {
    "izometrija spredaj-desno, zgoraj": (1.0, -1.25, 0.95),
    "izometrija spredaj-desno": (1.0, -1.3, 0.55),
    "izometrija od spodaj": (1.0, -1.3, -0.55),
    "izometrija zadaj-levo": (-1.3, 1.0, 0.55),
    "celota": (1.0, -1.35, 0.7),
}

deli = json.loads((POSKUS / "deli.json").read_text(encoding="utf-8"))["deli"]
koraki = json.loads((POSKUS / "koraki.json").read_text(encoding="utf-8"))["koraki"]
meshes = np.load(IZVOZ / "mreze.npz")
DEL = {d["id"]: d for d in deli}
IDS = [d["id"] for d in deli]


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def make_polydata(V, F):
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(V.astype(np.float64), deep=True))
    cells = np.hstack([np.full((len(F), 1), 3, dtype=np.int64), F.astype(np.int64)]).ravel()
    ca = vtk.vtkCellArray()
    ca.ImportLegacyFormat(numpy_to_vtkIdTypeArray(cells, deep=True))
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(ca)
    n = vtk.vtkPolyDataNormals()
    n.SetInputData(pd)
    n.SplittingOn()
    n.SetFeatureAngle(40)
    n.ConsistencyOff()
    n.AutoOrientNormalsOff()
    n.Update()
    return n.GetOutput()


def text(ren, s, x, y, size, bold=False, color=(0.1, 0.1, 0.12), just="left", bg=None):
    t = vtk.vtkTextActor()
    t.SetInput(s)
    p = t.GetTextProperty()
    p.SetFontFamily(vtk.VTK_FONT_FILE)
    p.SetFontFile(FONT_B if bold else FONT)
    p.SetFontSize(size)
    p.SetColor(*color)
    if just == "right":
        p.SetJustificationToRight()
    elif just == "center":
        p.SetJustificationToCentered()
    if bg is not None:
        p.SetBackgroundColor(*bg)
        p.SetBackgroundOpacity(0.85)
        p.SetFrame(False)
    t.SetDisplayPosition(int(x), int(y))
    ren.AddViewProp(t)
    return t


# ------------------------------------------------------------------ scena
rw = vtk.vtkRenderWindow()
rw.SetOffScreenRendering(1)
rw.SetSize(W, H)
rw.SetMultiSamples(0)
ren = vtk.vtkRenderer()
ren.SetBackground(0.97, 0.97, 0.98)
ren.SetBackground2(0.80, 0.83, 0.88)
ren.GradientBackgroundOn()
ren.UseFXAAOn()
rw.AddRenderer(ren)
lk = vtk.vtkLightKit()
lk.SetKeyLightIntensity(0.85)
lk.AddLightsToRenderer(ren)

actors, base_color, centers = {}, {}, {}
for pid in IDS:
    pd = make_polydata(meshes[pid + "_V"], meshes[pid + "_F"])
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(pd)
    a = vtk.vtkActor()
    a.SetMapper(m)
    c = DEL[pid]["barva_rgb"] or [0.7, 0.7, 0.7]
    # STEP barve so ohranjene; zelo temne police (Iveral 0.095) rahlo posvetlim, da so na zaslonu berljive
    if max(c) < 0.2:
        c = [0.28, 0.26, 0.25]
    base_color[pid] = tuple(c)
    pr = a.GetProperty()
    pr.SetColor(*c)
    pr.SetAmbient(0.15)
    pr.SetDiffuse(0.85)
    pr.SetSpecular(0.25)
    pr.SetSpecularPower(30)
    ren.AddActor(a)
    actors[pid] = a
    b = DEL[pid]["bbox_mm"]
    centers[pid] = (np.array(b["min"]) + np.array(b["max"])) / 2

# tla (senca ni, samo referencna ravnina)
zmin = min(DEL[p]["bbox_mm"]["min"][2] for p in IDS)
plane = vtk.vtkPlaneSource()
plane.SetOrigin(-6000, -6000, zmin - 0.5)
plane.SetPoint1(6000, -6000, zmin - 0.5)
plane.SetPoint2(-6000, 6000, zmin - 0.5)
pm = vtk.vtkPolyDataMapper()
pm.SetInputConnection(plane.GetOutputPort())
floor = vtk.vtkActor()
floor.SetMapper(pm)
floor.GetProperty().SetColor(0.93, 0.93, 0.94)
floor.GetProperty().SetAmbient(0.6)
floor.GetProperty().SetDiffuse(0.3)
floor.GetProperty().SetSpecular(0.0)
ren.AddActor(floor)

# 3D oznake ID (billboard)
labels = {}
for pid in IDS:
    la = vtk.vtkBillboardTextActor3D()
    la.SetInput(pid)
    tp = la.GetTextProperty()
    tp.SetFontFamily(vtk.VTK_FONT_FILE)
    tp.SetFontFile(FONT_B)
    tp.SetFontSize(26)
    tp.SetColor(1, 1, 1)
    tp.SetBackgroundColor(0.75, 0.33, 0.0)
    tp.SetBackgroundOpacity(0.95)
    tp.SetJustificationToCentered()
    la.VisibilityOff()
    ren.AddActor(la)
    labels[pid] = la

t_title = text(ren, "", 40, H - 80, 40, bold=True)
t_sub = text(ren, "", 40, H - 125, 26, color=(0.25, 0.25, 0.3))
t_parts = text(ren, "", 40, 40, 24, color=(0.15, 0.15, 0.2))
t_warn = text(ren, "Zaporedje je predlog AI - ni potrjeno (zahteva potrditev tehnologa)", W - 40, 40, 22,
              color=(0.65, 0.1, 0.05), just="right")
t_src = text(ren, "MLU123069200 · STEP Autodesk Inventor 2027 · 28 delov", W - 40, H - 60, 20,
             color=(0.35, 0.35, 0.4), just="right")

cam = ren.GetActiveCamera()
cam.SetViewAngle(30)
cam.SetViewUp(0, 0, 1)


def frame_cam(pts, view, margin=1.15):
    pts = np.asarray(pts)
    c = (pts.min(0) + pts.max(0)) / 2
    d = np.array(view, float)
    d /= np.linalg.norm(d)
    # razdalja tako, da vse tocke padejo v vidno polje (preprosta projekcija)
    up = np.array([0, 0, 1.0])
    right = np.cross(d, up)
    if np.linalg.norm(right) < 1e-6:
        right = np.array([1.0, 0, 0])
    right /= np.linalg.norm(right)
    upv = np.cross(right, d)
    rel = pts - c
    half_v = math.tan(math.radians(15))
    half_h = half_v * W / H
    dist = 0
    for p in rel:
        x, y, z = p @ right, p @ upv, p @ d
        dist = max(dist, abs(x) / half_h + z, abs(y) / half_v + z)
    dist *= margin
    return c, c + d * dist


def bbox_corners(pid, off=np.zeros(3)):
    b = DEL[pid]["bbox_mm"]
    mn, mx = np.array(b["min"]) + off, np.array(b["max"]) + off
    return [np.array([x, y, z]) for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for z in (mn[2], mx[2])]


def set_cam(focal, pos):
    cam.SetFocalPoint(*focal)
    cam.SetPosition(*pos)
    cam.SetViewUp(0, 0, 1)
    # tla samo, ce je kamera nad njimi (sicer pri pogledu od spodaj zakrijejo dele)
    floor.SetVisibility(int(pos[2] > zmin + 1.0))
    ren.ResetCameraClippingRange()


def set_part(pid, visible, offset=np.zeros(3), color=None, opacity=1.0):
    a = actors[pid]
    a.SetVisibility(visible)
    a.SetPosition(*offset)
    a.GetProperty().SetColor(*(color or base_color[pid]))
    a.GetProperty().SetOpacity(opacity)


def lerp(a, b, t):
    return tuple(np.array(a) * (1 - t) + np.array(b) * t)


# ------------------------------------------------------------------ casovnica
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                       "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-vf", "vflip",
                       "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                       "-movflags", "+faststart", str(POSKUS / "video.mp4")], stdin=subprocess.PIPE)
w2i = vtk.vtkWindowToImageFilter()
w2i.SetInput(rw)
w2i.SetInputBufferTypeToRGB()
w2i.ReadFrontBufferOff()
n_frames = [0]
timeline = []   # (cas_s, opis) za porocilo


def grab(save=None):
    rw.Render()
    w2i.Modified()
    w2i.Update()
    img = w2i.GetOutput()
    arr = vtk_to_numpy(img.GetPointData().GetScalars())
    ff.stdin.write(arr.tobytes())
    n_frames[0] += 1
    if save:
        wr = vtk.vtkPNGWriter()
        wr.SetFileName(str(save))
        wr.SetInputConnection(w2i.GetOutputPort())
        wr.Write()


all_pts = [p for pid in IDS for p in bbox_corners(pid)]


def orbit(seconds, title, sub, az0, az1, save=None):
    n = int(seconds * FPS)
    for i in range(n):
        az = math.radians(az0 + (az1 - az0) * ease(i / max(1, n - 1)))
        base = np.array(POGLEDI["celota"])
        r = math.hypot(base[0], base[1])
        ang = math.atan2(base[1], base[0]) + az
        v = (r * math.cos(ang), r * math.sin(ang), base[2])
        f, p = frame_cam(all_pts, v, 1.12)
        set_cam(f, p)
        t_title.SetInput(title)
        t_sub.SetInput(sub)
        grab(save if (save and i == n // 2) else None)


# --- predogled.png (en kader celega sestava) ---
for pid in IDS:
    set_part(pid, True)
f, p = frame_cam(all_pts, POGLEDI["celota"], 1.12)
set_cam(f, p)
t_title.SetInput("Voziček proizvodni montažni 1000x500 h=890")
t_sub.SetInput("MLU123069200 · končni sestav · 28 delov (14 produktov) iz STEP")
t_parts.SetInput("")
t_warn.SetVisibility(False)
rw.Render()
w2i.Modified()
w2i.Update()
pw = vtk.vtkPNGWriter()
pw.SetFileName(str(POSKUS / "predogled.png"))
pw.SetInputConnection(w2i.GetOutputPort())
pw.Write()
t_warn.SetVisibility(True)

# --- uvod ---
timeline.append((0.0, "uvod: celoten sestav"))
orbit(4.0, "Voziček proizvodni montažni 1000x500 h=890", "Montažno navodilo - predlog (MLU123069200)", -20, 20)

# --- koraki ---
def label_pos(pid, off, od_spodaj):
    """Oznaka nad delom; pri pogledu od spodaj pod delom (sicer jo zakrije sestav)."""
    b = DEL[pid]["bbox_mm"]
    c = centers[pid] + off
    z = (b["min"][2] + off[2] - 45) if od_spodaj else (b["max"][2] + off[2] + 45)
    return np.array([c[0], c[1], z])


placed = []
prev_cam = None
for k in koraki:
    ids = k["deli"]
    offs = {pid: np.array(k["gibanje"]["po_delih_od_mm"][pid], float) for pid in ids}
    dur = float(k["gibanje"]["trajanje_s"])
    view = POGLEDI.get(k["kamera"]["pogled"], POGLEDI["celota"])
    pts = [p for pid in placed for p in bbox_corners(pid)]
    od_spodaj = view[2] < 0
    for pid in ids:
        pts += bbox_corners(pid) + bbox_corners(pid, offs[pid])
        for o in (np.zeros(3), offs[pid]):   # tudi polozaj oznake mora biti v kadru
            pts.append(label_pos(pid, o, od_spodaj) + np.array([0, 0, -40 if od_spodaj else 40]))
    # kamera kadrira ze namesceno + trenutni del (na zacetku in koncu poti)
    focal, pos = frame_cam(pts, view, 1.12)
    timeline.append((n_frames[0] / FPS, f"korak {k['st']}: {k['naslov']}"))
    t_title.SetInput(f"Korak {k['st']}/{len(koraki)}: {k['naslov']}")
    t_sub.SetInput(f"Smer vstavljanja: {k['gibanje']['smer']} · pot preverjena na trke: {k['gibanje']['kontrola_poti']}")
    imena = {}
    for pid in ids:
        imena.setdefault(DEL[pid]["ime"].strip(), []).append(pid)
    t_parts.SetInput("   ".join(f"{', '.join(v)}: {ime} ({DEL[v[0]]['sifra']})" for ime, v in imena.items()))
    for pid in IDS:
        if pid in placed:
            set_part(pid, True, color=NAMESCENO)
        elif pid not in ids:
            set_part(pid, False)

    def label_at(pid, off):
        labels[pid].SetPosition(*label_pos(pid, off, od_spodaj))

    # 1) prehod kamere + pojav dela v izhodiscnem polozaju (0.9 s)
    n = int(0.9 * FPS)
    c0 = prev_cam or (focal, pos)
    for i in range(n):
        t = ease(i / (n - 1))
        set_cam(lerp(c0[0], focal, t), lerp(c0[1], pos, t))
        for pid in ids:
            set_part(pid, True, offs[pid], POUDAREK, opacity=t)
            label_at(pid, offs[pid])
            labels[pid].SetVisibility(t > 0.5)
        grab()
    # 2) premik v koncni polozaj
    n = int(dur * FPS)
    for i in range(n):
        t = ease(i / (n - 1))
        for pid in ids:
            o = offs[pid] * (1 - t)
            set_part(pid, True, o, POUDAREK)
            label_at(pid, o)
        grab()
    # 3) zadrzanje s poudarkom (0.9 s) + kontrolna slicica
    n = int(0.9 * FPS)
    for i in range(n):
        grab(SLICICE / f"korak_{k['st']:02d}.png" if i == n // 2 else None)
    # 4) prehod v pravo barvo (0.4 s)
    n = int(0.4 * FPS)
    for i in range(n):
        t = ease(i / (n - 1))
        for pid in ids:
            set_part(pid, True, color=lerp(POUDAREK, NAMESCENO, t))
        grab()
    for pid in ids:
        labels[pid].VisibilityOff()
    placed += ids
    prev_cam = (focal, pos)

# --- zakljucek: vse v pravih barvah, kroženje ---
for pid in IDS:
    set_part(pid, True)
t_parts.SetInput("Barve iz STEP: jeklo (sivo), Iveral police (temno), inox ročaj (svetlo), kolesa TENTE (modro)")
timeline.append((n_frames[0] / FPS, "zakljucek: koncni sestav"))
f, p = frame_cam(all_pts, POGLEDI["celota"], 1.12)
n = int(1.0 * FPS)
for i in range(n):
    t = ease(i / (n - 1))
    set_cam(lerp(prev_cam[0], f, t), lerp(prev_cam[1], p, t))
    t_title.SetInput("Končni sestav")
    t_sub.SetInput("28 delov · vsi deli iz STEP, ID-ji kot v deli.json in vozicek.glb")
    grab()
orbit(5.0, "Končni sestav", "28 delov · vsi deli iz STEP, ID-ji kot v deli.json in vozicek.glb", 0, 60,
      save=SLICICE / "zakljucek.png")

ff.stdin.close()
ff.wait()
dolzina = n_frames[0] / FPS
(IZVOZ / "video_casovnica.json").write_text(json.dumps(
    {"fps": FPS, "velikost": [W, H], "slicic": n_frames[0], "dolzina_s": round(dolzina, 2),
     "poglavja": [{"cas_s": round(t, 2), "opis": d} for t, d in timeline]}, ensure_ascii=False, indent=2),
    encoding="utf-8")
print("slicic", n_frames[0], "dolzina", round(dolzina, 1), "s, ffmpeg", ff.returncode)
