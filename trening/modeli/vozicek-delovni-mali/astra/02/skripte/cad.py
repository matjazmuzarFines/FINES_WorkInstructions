import re
from hashlib import sha256
from osnova import OUT, EXPORT, SOURCE, save
import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepGProp import BRepGProp
from OCP.BRepLib import BRepLib_ToolTriangulatedShape
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.Bnd import Bnd_Box
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ShapeTool as ST
from OCP.XCAFDoc import XCAFDoc_ColorSurf, XCAFDoc_ColorGen
from OCP.Quantity import Quantity_Color, Quantity_TOC_sRGB
from OCP.collections import Sequence_TCollection_AsciiString, Sequence_TDF_Label


def label_name(label):
    attr = TDataStd_Name()
    assert label.FindAttribute(TDataStd_Name.GetID_s(), attr)
    return attr.Get().ToExtString()


def walk(shape, kind):
    it = TopExp_Explorer(shape, kind)
    while it.More():
        yield it.Current()
        it.Next()


def bounds(shape):
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, box, False, False)
    val = np.array([box.CornerMin().Coord(), box.CornerMax().Coord()]).round(5)
    return dict(zip(("min", "max"), val.tolist()))


def matrix(loc):
    t = loc.Transformation()
    m = np.eye(4)
    m[:3] = [[t.Value(i, j) for j in range(1, 5)] for i in range(1, 4)]
    return m


def mesh(shape, colors=None):
    assert BRepMesh_IncrementalMesh(shape, 0.055, False, 0.15, False).IsDone()
    positions, normals, triangles, styles = [], [], [], []
    for item in walk(shape, TopAbs_FACE):
        face = TopoDS.Face(item)
        rgb = (-1.,-1.,-1.)
        if colors:
            color = Quantity_Color()
            if any(colors.GetColor(face,kind,color) for kind in (XCAFDoc_ColorSurf,XCAFDoc_ColorGen)):
                rgb = tuple(round(x,3) for x in color.Values(Quantity_TOC_sRGB))
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        if not tri or not tri.NbTriangles():
            props = GProp_GProps()
            BRepGProp.SurfaceProperties_s(face, props)
            print("Ponovna tesselacija ploskve", props.Mass(), bounds(face), flush=True)
            original = face
            for deflection, angle in [(0.02, 0.10), (0.004, 0.04), (0.001, 0.02)]:
                face = TopoDS.Face(BRepBuilderAPI_Copy(original, True, False).Shape())
                BRepMesh_IncrementalMesh(face, deflection, False, angle, False)
                tri = BRep_Tool.Triangulation_s(face, loc)
                if tri and tri.NbTriangles():
                    break
            assert tri and tri.NbTriangles() > 0
        BRepLib_ToolTriangulatedShape.ComputeNormals_s(face, tri)
        reverse = face.Orientation() == TopAbs_REVERSED
        start = len(positions)
        for i in range(1, tri.NbNodes()+1):
            positions.append(tri.Node(i).Transformed(loc.Transformation()).Coord())
            n = tri.Normal(i).Transformed(loc.Transformation())
            normals.append((n.Reversed() if reverse else n).Coord())
        for i in range(1, tri.NbTriangles()+1):
            a, b, c = [start + j - 1 for j in tri.Triangle(i).Get()]
            triangles.append((a, c, b) if reverse else (a, b, c))
            styles.append(rgb)
    return tuple(np.asarray(lst, dtype=dtype) for lst, dtype in
                 zip((positions, normals, triangles, styles), ("<f4", "<f4", "<u4", "<f4")))


def source_data():
    raw = SOURCE.read_bytes()
    # This AP214 writer wraps STEP strings across physical lines.
    txt = raw.decode("latin1").replace("\r", "").replace("\n", "")
    txt = re.sub(r"\\X2\\([0-9A-F]+)\\X0\\", lambda m: bytes.fromhex(m[1]).decode("utf-16-be"), txt)
    products = {code: (int(i), name, desc) for i, code, name, desc in re.findall(
        r"#(\d+)=PRODUCT\('([^']*)','([^']*)','([^']*)',", txt)}
    uses = {name: int(i) for i, name in re.findall(r"#(\d+)=NEXT_ASSEMBLY_USAGE_OCCURRENCE\('([^']*)'", txt)}
    definitions = dict(re.findall(r"#(\d+)=PRODUCT_DEFINITION\('([^']+)'", txt))
    props=dict(re.findall(r"#(\d+)=PROPERTY_DEFINITION\('material property','material name',#(\d+)\)",txt))
    reps=dict(re.findall(r"#(\d+)=REPRESENTATION\('material name',\(#(\d+)\)",txt))
    names=dict(re.findall(r"#(\d+)=DESCRIPTIVE_REPRESENTATION_ITEM\('([^']*)'",txt))
    materials={definitions[props[p]]:dict(naziv=names[reps[r]],step_property=int(p),step_item=int(reps[r]))
               for p,r in re.findall(r"PROPERTY_DEFINITION_REPRESENTATION\(#(\d+),#(\d+)\)",txt) if p in props and r in reps}
    links = re.findall(r"NEXT_ASSEMBLY_USAGE_OCCURRENCE\('[^']*','[^']*','[^']*',#(\d+),#\d+,", txt)
    assert len(links) == len(uses)
    assembly_codes = {definitions[i] for i in links}
    assert len(uses) == txt.count("=NEXT_ASSEMBLY_USAGE_OCCURRENCE(")
    return products, uses, assembly_codes, dict(sha256=sha256(raw).hexdigest(), product=len(products), nauo=len(uses),
                               materiali=materials, manifold_solid_brep=txt.count("=MANIFOLD_SOLID_BREP("))


def extract(with_mesh=True):
    products, uses, assembly_codes, stats = source_data()
    reader = STEPCAFControl_Reader()
    doc = TDocStd_Document(TCollection_ExtendedString("MDTV-XCAF"))
    assert reader.ReadFile(str(SOURCE)) == IFSelect_RetDone
    units = [Sequence_TCollection_AsciiString() for _ in range(3)]
    reader.Reader().FileUnits(*units)
    stats["enote"] = [v.ToCString() for v in units[0]]
    assert stats["enote"] == ["millimetre"]
    assert reader.Transfer(doc)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    colors = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    roots = Sequence_TDF_Label()
    tool.GetFreeShapes(roots)
    assert roots.Length() == 1
    root = roots.Value(1)
    root_name = label_name(root)
    root_shape = ST.GetShape_s(root)
    stats.update(koren=root_name, bbox_mm=bounds(root_shape), telesa_korena=sum(1 for _ in walk(root_shape, TopAbs_SOLID)))
    parts, meshes, groups, used, worlds = [], {}, [], set(), {}

    def visit(parent, parent_path, cum):
        labels = Sequence_TDF_Label()
        assert ST.GetComponents_s(parent, labels, False)
        for label in labels:
            occ = label_name(label)
            ref = TDF_Label()
            assert ST.GetReferredShape_s(label, ref)
            code = label_name(ref)
            ent, name, desc = products[code]
            used.add(occ)
            idx = uses[occ]
            path = parent_path + "/" + occ
            loc = cum.Multiplied(ST.GetLocation_s(label))
            if code in assembly_codes:
                groups.append(dict(pot=path, stars=parent_path, sifra=code, opis=desc, step_nauo=idx))
                visit(ref, path, loc)
                continue
            shape = ST.GetShape_s(ref)
            world = shape.Moved(loc)
            prop = GProp_GProps()
            BRepGProp.VolumeProperties_s(world, prop)
            count = sum(1 for _ in walk(shape, TopAbs_SOLID))
            assert count and prop.Mass() > 0
            pid = f"P{idx:03}"
            worlds[pid] = world
            parts.append(dict(id=pid, ime=name, opis=desc, tip="solid" if count == 1 else "večtelesni del",
                              stars=parent_path, kolicina=1, telesa=count, bbox_mm=bounds(world),
                              volumen_mm3=round(prop.Mass(), 3), pojavitev=occ, pot=path, step_product=ent, opomba=desc,
                              step_nauo=idx, matrika_lokalno_v_sestav_mm=matrix(loc).tolist()))
            if with_mesh and code not in meshes:
                if count > 1:
                    items=[mesh(solid,colors) for solid in walk(shape,TopAbs_SOLID)]
                    starts=np.cumsum([0]+[len(x[0]) for x in items[:-1]])
                    meshes[code]=(np.vstack([x[0] for x in items]),np.vstack([x[1] for x in items]),
                                  np.vstack([x[2]+offset for x,offset in zip(items,starts)]).astype("<u4"),
                                  np.vstack([x[3] for x in items]),np.repeat(np.arange(count),[len(x[2]) for x in items]))
                else:
                    meshes[code] = (*mesh(shape),None)

    visit(root, root_name, TopLoc_Location())
    assert used == set(uses)
    parts.sort(key=lambda p:p["id"])
    assert len(parts) == len(worlds)
    assert sum(p["telesa"] for p in parts) == stats["telesa_korena"]
    stats.update(podsestavi=groups, razlicni_listi=len(meshes),
                 trikotniki=sum(len(meshes[p["ime"]][2]) for p in parts) if with_mesh else 0)
    return parts, meshes, worlds, stats


if __name__ == "__main__":
    p, m, w, s = extract()
    print(s)
    for row in p:
        print(row["id"], row["opis"], row["bbox_mm"], row["telesa"])

