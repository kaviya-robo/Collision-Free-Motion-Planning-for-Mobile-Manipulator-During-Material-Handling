"""
swcad.py - a small parametric SolidWorks 2025 builder driven from Python (pywin32 / COM).

All geometry is written in ROS REP-103 coordinates (x forward, y left, z up) and millimetres.
SolidWorks parts are Y-up, so the mapping used everywhere is  SW(X, Y, Z) = ROS(x, z, -y):

    ROS XY plane -> SW "Top Plane"    sketch (u, v) = (x, y)   normal +z
    ROS XZ plane -> SW "Front Plane"  sketch (u, v) = (x, z)   normal -y
    ROS YZ plane -> SW "Right Plane"  sketch (u, v) = (y, z)   normal +x

Every dimension may be a number or an expression of the part's global variables, e.g.
"Chassis_L - 2*Shell_T". Expressions become SolidWorks equations, so editing a global variable
in Tools > Equations regenerates the part.
"""
import math
import os
import re
import struct

import pythoncom
import win32com.client
from win32com.client import VARIANT

NOTHING = VARIANT(pythoncom.VT_DISPATCH, None)
EMPTY_STRS = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_BSTR, [])
EPS = 1e-9
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# ROS vector -> SW vector (column convention): SW = C * ROS
C = ((1, 0, 0), (0, 0, 1), (0, -1, 0))

PLANES = {"XY": ("Top Plane", +1), "XZ": ("Front Plane", -1), "YZ": ("Right Plane", +1)}


def cv(obj, name, *args):
    """Call a COM member that may be exposed as a method or as a property."""
    attr = getattr(obj, name)
    if isinstance(attr, win32com.client.dynamic.CDispatch):
        return attr
    return attr(*args) if callable(attr) else attr


def dvec(vals):
    return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [float(v) for v in vals])


def byref_int():
    return VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)


def fmt(v):
    return ("%.6f" % v).rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def matmul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def transpose(a):
    return tuple(tuple(a[j][i] for j in range(3)) for i in range(3))


def rot_rpy(roll, pitch, yaw):
    """URDF fixed-axis roll-pitch-yaw -> 3x3 rotation (column convention)."""
    cr, sr, cp, sp, cy, sy = (math.cos(roll), math.sin(roll), math.cos(pitch), math.sin(pitch),
                              math.cos(yaw), math.sin(yaw))
    return ((cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr),
            (sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr),
            (-sp, cp * sr, cp * cr))


IDENTITY = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


def sw_pose(rot_ros, t_ros_mm):
    """ROS pose (rotation, translation mm) -> SolidWorks 16-value transform array."""
    m = matmul(matmul(C, rot_ros), transpose(C))
    t = [sum(C[i][k] * t_ros_mm[k] for k in range(3)) / 1000.0 for i in range(3)]
    return [m[0][0], m[1][0], m[2][0], m[0][1], m[1][1], m[2][1], m[0][2], m[1][2], m[2][2],
            t[0], t[1], t[2], 1.0, 0.0, 0.0, 0.0]


class CAD:
    def __init__(self):
        self.sw = win32com.client.Dispatch("SldWorks.Application")
        self.sw.Visible = True
        self.sw.CommandInProgress = True  # big speed-up for API-driven modelling
        self.sw.SetUserPreferenceToggle(10, False)   # swInputDimValOnCreate
        self.sw.SetUserPreferenceToggle(249, False)  # swSketchInference
        self.tpl_part = self.sw.GetUserPreferenceStringValue(8)
        self.tpl_asm = self.sw.GetUserPreferenceStringValue(9)
        self.math = cv(self.sw, "GetMathUtility")
        self.math._FlagAsMethod("CreateTransform")
        # STL export: binary, millimetres, fine, keep the part coordinate system
        self.sw.SetUserPreferenceToggle(69, True)
        self.sw.SetUserPreferenceToggle(71, True)
        self.sw.SetUserPreferenceToggle(72, True)
        self.sw.SetUserPreferenceIntegerValue(211, 0)
        self.sw.SetUserPreferenceIntegerValue(78, 2)

    def open(self, path):
        kind = 2 if path.upper().endswith(".SLDASM") else 1
        err, warn = byref_int(), byref_int()
        m = self.sw.OpenDoc6(path, kind, 1, "", err, warn)
        if m is None:
            raise RuntimeError("open failed (%s) %s" % (err.value, path))
        return m

    def part(self, name, title=""):
        return Part(self, name, title)

    def asm(self, name, title=""):
        return Asm(self, name, title)


class _Doc:
    """Shared document helpers (global variables, equations, ref geometry, save)."""

    def _init_doc(self, cad, name, tpl, title):
        self.cad, self.sw, self.name = cad, cad.sw, name
        self.m = self.sw.NewDocument(tpl, 0, 0, 0)
        self.ext = self.m.Extension
        self.ext.SetUserPreferenceInteger(263, 0, 5)  # MMGS
        self.sm, self.fm = self.m.SketchManager, self.m.FeatureManager
        self.sm.AddToDB = True
        self.fm.EnableFeatureTree = False
        # NOTE: ActiveView.EnableGraphicsUpdate = False must not be used - SolidWorks then skips
        # the centre point of centre-rectangles, which the dimensioning relies on.
        self.eqm = cv(self.m, "GetEquationMgr")
        self.G = {}
        self.n = {}
        self.path = None
        if title:
            self.prop("Description", title)

    # ---------- parameters ----------
    def g(self, name, value, note=""):
        """Add a global variable (shown in Tools > Equations)."""
        self.G[name] = float(value) if isinstance(value, (int, float)) else self.ev(value)
        rhs = fmt(value) if isinstance(value, (int, float)) else self.sx(value)
        txt = '"%s" = %s' % (name, rhs) + (" '%s" % note if note else "")
        if self.eqm.Add2(-1, txt, False) < 0:
            raise RuntimeError("equation rejected: " + txt)
        return name

    def ev(self, e):
        if isinstance(e, (int, float)):
            return float(e)
        return float(eval(e, {"__builtins__": {}}, dict(self.G, sqrt=math.sqrt)))

    def sx(self, e):
        """Python expression -> SolidWorks equation right-hand side (None for plain numbers)."""
        if isinstance(e, (int, float)):
            return None
        return IDENT.sub(lambda mo: '"%s"' % mo.group(0) if mo.group(0) in self.G else mo.group(0), e)

    def link(self, dim_name, expr, value):
        rhs = self.sx(expr)
        if rhs is None:
            return
        if value < 0:
            rhs = "-(%s)" % rhs
        if self.eqm.Add2(-1, '"%s" = %s' % (dim_name, rhs), False) < 0:
            raise RuntimeError("link rejected: %s = %s" % (dim_name, rhs))

    def uid(self, prefix):
        self.n[prefix] = self.n.get(prefix, 0) + 1
        return "%s%d" % (prefix, self.n[prefix])

    def prop(self, key, value):
        mgr = self.ext.CustomPropertyManager("")
        mgr.Add3(key, 30, str(value), 1)

    # ---------- reference geometry ----------
    def select(self, name, kind="PLANE", append=False, mark=0):
        if not self.ext.SelectByID2(name, kind, 0, 0, 0, append, mark, NOTHING, 0):
            raise RuntimeError("cannot select %s %s" % (kind, name))

    def ref_plane(self, name, base, offset):
        """Plane parallel to ROS plane `base` ('XY','XZ','YZ') at ROS coordinate `offset`."""
        sw_name, sign = PLANES[base]
        val = self.ev(offset) * sign
        self.m.ClearSelection2(True)
        self.select(sw_name)
        f = self.fm.InsertRefPlane(8 + (256 if val < 0 else 0), abs(val) / 1000.0, 0, 0, 0, 0)
        if f is None:
            raise RuntimeError("ref plane failed " + name)
        f.Name = name
        expr = offset if (sign > 0 or isinstance(offset, (int, float))) else "-(%s)" % offset
        self.link("D1@" + name, expr, val)
        PLANES_LOCAL[(id(self), name)] = base
        return f

    def ref_axis(self, name, p1, p2):
        self.m.ClearSelection2(True)
        self.select(p1)
        self.select(p2, append=True)
        if not cv(self.m, "InsertAxis2", True):
            raise RuntimeError("axis failed " + name)
        f, last = cv(self.m, "FirstFeature"), None
        while f:  # newest reference axis (in assemblies the Mates folder comes last)
            if cv(f, "GetTypeName2") == "RefAxis":
                last = f
            f = cv(f, "GetNextFeature")
        last.Name = name
        return last

    def plane_of(self, plane):
        if plane in PLANES:
            return PLANES[plane]
        base = PLANES_LOCAL[(id(self), plane)]
        return plane, PLANES[base][1]

    def iso_view(self):
        self.ext.SetUserPreferenceToggle(198, 0, True)  # View > Hide All Types (planes/axes/origins)
        self.m.ShowNamedView2("*Isometric", 7)
        cv(self.m, "ViewZoomtofit2")

    def finish(self):
        """Solve all equations, rebuild and re-enable UI updates (call once before saving)."""
        cv(self.eqm, "EvaluateAll")
        cv(self.m, "ForceRebuild3", False)
        self.fm.EnableFeatureTree = True

    def save(self, path):
        self.finish()
        self.iso_view()
        err = self.m.SaveAs3(path, 0, 1)
        if err:
            raise RuntimeError("save failed (%s) %s" % (err, path))
        self.path = path
        return path

    def png(self, path):
        self.iso_view()
        return self.m.SaveAs3(path, 0, 1) == 0

    def export(self, path):
        err = self.m.SaveAs3(path, 0, 1)
        if err:
            raise RuntimeError("export failed (%s) %s" % (err, path))
        return path


PLANES_LOCAL = {}


class Part(_Doc):
    def __init__(self, cad, name, title=""):
        self._init_doc(cad, name, cad.tpl_part, title)

    def sketch(self, plane, name=None):
        return Sk(self, plane, name or self.uid("SK_"))

    def _feature_dims(self, f):
        out = []
        dd = f.GetFirstDisplayDimension
        while dd:
            d = dd.GetDimension2(0)
            parts = d.FullName.split("@")
            out.append((parts[0], parts[1], d))
            dd = f.GetNextDisplayDimension(dd)
        return out

    def extrude(self, sk, a0=None, a1=None, mid=None, cut=False, through=False, name=None,
                color=None, merge=True, transparency=0.0, emission=0.0):
        """Extrude sketch `sk` along its plane normal so that the ROS coordinate along that
        normal spans [a0, a1]; or symmetric total thickness `mid`; or a through-all cut."""
        sw_plane, sign = self.plane_of(sk.plane)
        self.m.ClearSelection2(True)
        self.select(sk.name, "SKETCH")
        fname = name or self.uid("CUT_" if cut else "EX_")
        links = []
        if through:
            f = self.fm.FeatureCut4(False, False, False, 1, 1, 0.01, 0.01, False, False, False, False,
                                    0, 0, False, False, False, False, False, True, True, True, True,
                                    False, 0, 0, False, False)
        else:
            if mid is not None:
                T1, depth, T0, off, flip = 6, self.ev(mid), 0, 0.0, False
                links.append(("D1", mid, depth))
            else:
                A0, A1 = self.ev(a0), self.ev(a1)
                if A1 < A0:
                    a0, a1, A0, A1 = a1, a0, A1, A0
                depth = A1 - A0
                if sign > 0:
                    e_u0, u0 = a0, A0
                else:
                    e_u0 = -a1 if isinstance(a1, (int, float)) else "-(%s)" % a1
                    u0 = -A1
                T1 = 0
                T0, off, flip = (0, 0.0, False) if abs(u0) < EPS else (3, abs(u0), u0 < 0)
                dexpr = None if isinstance(a0, (int, float)) and isinstance(a1, (int, float)) \
                    else "(%s)-(%s)" % (a1, a0)
                links.append(("D1", dexpr if dexpr else depth, depth))
                if T0 == 3:
                    links.append(("OFF", e_u0, u0))
            if cut:
                f = self.fm.FeatureCut4(True, False, False, T1, 0, depth / 1000.0, 0, False, False,
                                        False, False, 0, 0, False, False, False, False, False, True,
                                        True, True, True, False, T0, off / 1000.0, flip, False)
            else:
                f = self.fm.FeatureExtrusion3(True, False, False, T1, 0, depth / 1000.0, 0, False,
                                              False, False, False, 0, 0, False, False, False, False,
                                              merge, True, True, T0, off / 1000.0, flip)
        if f is None:
            raise RuntimeError("feature failed: %s on %s in %s" % (fname, sk.name, self.name))
        f.Name = fname
        own = [(n, d) for n, owner, d in self._feature_dims(f) if owner == fname]
        for key, expr, val in links:
            if key == "D1":
                cand = [d for n, d in own if n == "D1"]
            else:
                cand = [d for n, d in own if n != "D1"]
            if cand and not isinstance(expr, (int, float)):
                self.link("%s@%s" % (cand[0].Name, fname), expr, val)
        if color:
            self.color(f, color, transparency, emission)
        return f

    def color(self, f, rgb, transparency=0.0, emission=0.0):
        vals = dvec([rgb[0], rgb[1], rgb[2], 0.6, 0.9, 0.45, 0.35, transparency, emission])
        f.SetMaterialPropertyValues2(vals, 2, EMPTY_STRS)

    def body_color(self, rgb, transparency=0.0, emission=0.0):
        self.m.MaterialPropertyValues = dvec([rgb[0], rgb[1], rgb[2], 0.6, 0.9, 0.45, 0.35,
                                              transparency, emission])

    def material(self, mat):
        self.m.SetMaterialPropertyName2("Default", "solidworks materials.sldmat", mat)
        out = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BSTR, "")
        got = self.m.GetMaterialPropertyName2("Default", out)
        return got

    def mass_props(self):
        mp = self.ext.CreateMassProperty
        return {"mass": mp.Mass, "volume": mp.Volume, "com": [v * 1000 for v in mp.CenterOfMass]}

    def bbox_ros(self):
        """Overall bounding box of all bodies in ROS mm: (xmin,xmax,ymin,ymax,zmin,zmax)."""
        xs, ys, zs = [], [], []
        for b in self.m.GetBodies2(0, True) or []:
            bx = cv(b, "GetBodyBox")
            X0, Y0, Z0, X1, Y1, Z1 = [v * 1000 for v in bx]
            xs += [X0, X1]; zs += [Y0, Y1]; ys += [-Z0, -Z1]
        return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


class Sk:
    """A sketch on a ROS plane; geometry uses the plane's (u, v) = ROS coordinates (mm)."""

    def __init__(self, part, plane, name):
        self.p, self.plane, self.name = part, plane, name
        self.m, self.sm = part.m, part.sm
        self.dims = []
        self.fillets = []
        self.autodims = []
        sw_plane, _ = part.plane_of(plane)
        self.m.ClearSelection2(True)
        part.select(sw_plane)
        self.sm.InsertSketch(True)
        self.sk = self.sm.ActiveSketch

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if exc[0]:
            return False
        self.sm.InsertSketch(True)
        f = self.m.FeatureByPositionReverse(0)
        f.Name = self.name
        for dname, expr, val in self.dims:
            self.p.link("%s@%s" % (dname, self.name), expr, val)
        if self.fillets or self.autodims:
            # SolidWorks auto-created dims (sketch fillet radius, pattern spacing / count):
            # identify them by value and link them to their expressions
            pending = [(e, v, 1000.0) for e, v in self.fillets] + list(self.autodims)
            for n, owner, d in self.p._feature_dims(f):
                if owner == self.name and re.fullmatch(r"D\d+", n):
                    for expr, val, scale in pending:
                        if abs(d.SystemValue * scale - val) < 1e-6:
                            self.p.link("%s@%s" % (n, self.name), expr, val)
                            break
        return False

    def grid(self, cu, cv_, d, nx, ny, px, py):
        """Hole grid: seed circle at (cu, cv_) + parametric sketch linear pattern (+u, +v)."""
        self.circle(cu, cv_, d)
        arcs = [s for s in cv(self.sk, "GetSketchSegments") or [] if cv(s, "GetType") == 1]
        NX, NY, PX, PY = (self.p.ev(x) for x in (nx, ny, px, py))
        self.m.ClearSelection2(True)
        arcs[-1].Select4(False, NOTHING)
        if not self.sm.CreateLinearSketchStepAndRepeat(int(NX), int(NY), PX / 1000, PY / 1000, 0,
                                                       math.pi / 2, "", True, True, False, True, True):
            raise RuntimeError("sketch pattern failed in %s" % self.name)
        self.autodims += [(px, PX, 1000.0), (py, PY, 1000.0), (nx, NX, 1.0), (ny, NY, 1.0)]

    # ---------- helpers ----------
    def _pts(self):
        return list(cv(self.sk, "GetSketchPoints2") or [])

    def _find(self, u, v):
        for p in reversed(self._pts()):  # newest first (concentric profiles share centres)
            if abs(p.X * 1000 - u) < 1e-4 and abs(p.Y * 1000 - v) < 1e-4:
                return p
        have = sorted((round(p.X * 1000, 3), round(p.Y * 1000, 3)) for p in self._pts())
        raise RuntimeError("sketch point (%.3f, %.3f) not found in %s; points: %s"
                           % (u, v, self.name, have))

    def _origin(self, append=True):
        self.p.ext.SelectByID2("Point1@Origin", "EXTSKETCHPOINT", 0, 0, 0, append, 0, NOTHING, 0)

    def _add_dim(self, dd, expr, val, prefix):
        if dd is None:
            raise RuntimeError("dimension failed in %s" % self.name)
        d = dd.GetDimension2(0)
        dn = self.p.uid(self.name + "_" + prefix)[len(self.name) + 1:]
        d.Name = dn
        self.dims.append((dn, expr, val))
        return d

    def _place(self, pt, ue, ve):
        U, V = self.p.ev(ue), self.p.ev(ve)
        if abs(U) < EPS and abs(V) < EPS:
            self.m.ClearSelection2(True)
            pt.Select4(False, NOTHING)
            self._origin()
            self.m.SketchAddConstraints("sgCOINCIDENT")  # sgMERGEPOINTS does not bind to the origin
            return
        for axis, val, expr in (("u", U, ue), ("v", V, ve)):
            self.m.ClearSelection2(True)
            pt.Select4(False, NOTHING)
            self._origin()
            if abs(val) < EPS:
                self.m.SketchAddConstraints("sgVERTICALPOINTS2D" if axis == "u" else "sgHORIZONTALPOINTS2D")
            elif axis == "u":
                self._add_dim(self.m.AddHorizontalDimension2(U / 2000, V / 1000 - 0.01, 0), expr, val, "X")
            else:
                self._add_dim(self.m.AddVerticalDimension2(U / 1000 + 0.01, V / 2000, 0), expr, val, "Y")

    def _lines(self):
        hor, ver = [], []
        for s in cv(self.sk, "GetSketchSegments") or []:
            if s.ConstructionGeometry or cv(s, "GetType") != 0:
                continue
            a, b = cv(s, "GetStartPoint2"), cv(s, "GetEndPoint2")
            (hor if abs(a.Y - b.Y) < 1e-9 else ver).append((s, a, b))
        return hor, ver

    # ---------- primitives ----------
    def rect(self, cu, cv_, w, h, r=None):
        U, V, W, H_true = (self.p.ev(x) for x in (cu, cv_, w, h))
        # SolidWorks re-solves a filleted *square* centre-rectangle and shrinks two sides;
        # draw squares slightly off-square, fully dimension them, then set the true height.
        H = H_true - 0.37 if (r is not None and abs(W - H_true) < 1e-6) else H_true
        segs = self.sm.CreateCenterRectangle(U / 1000, V / 1000, 0, (U + W / 2) / 1000,
                                             (V + H / 2) / 1000, 0)
        if not segs:
            raise RuntimeError("rect failed in %s" % self.name)
        if r is not None:
            R = self.p.ev(r)
            self.m.ClearSelection2(True)
            corners = {(round(U + sx * W / 2, 4), round(V + sy * H / 2, 4)) for sx in (-1, 1) for sy in (-1, 1)}
            n = 0
            for p in self._pts():
                if (round(p.X * 1000, 4), round(p.Y * 1000, 4)) in corners:
                    p.Select4(True, NOTHING)
                    n += 1
            if n != 4 or self.sm.CreateFillet(R / 1000, 1) is None:
                raise RuntimeError("fillet failed in %s" % self.name)
            self.fillets.append((r, R))
        # width / height as distances between the parallel lines of this rectangle
        allh, allv = self._lines()

        def pick(lines, vertical, at, lo, hi):
            out = []
            for s, a, b in lines:
                c = (a.X if vertical else a.Y) * 1000
                s0, s1 = sorted([(a.Y if vertical else a.X) * 1000, (b.Y if vertical else b.X) * 1000])
                if abs(c - at) < 1e-4 and s0 >= lo - 1e-4 and s1 <= hi + 1e-4:
                    out.append(s)
            return out

        left = pick(allv, True, U - W / 2, V - H / 2, V + H / 2)
        right = pick(allv, True, U + W / 2, V - H / 2, V + H / 2)
        bot = pick(allh, False, V - H / 2, U - W / 2, U + W / 2)
        top = pick(allh, False, V + H / 2, U - W / 2, U + W / 2)
        if not (left and right and bot and top):
            raise RuntimeError("rect edges not found in %s" % self.name)
        self.m.ClearSelection2(True)
        left[0].Select4(False, NOTHING); right[0].Select4(True, NOTHING)
        self._add_dim(self.m.AddDimension2(U / 1000, (V + H / 2) / 1000 + 0.01, 0), w, W, "W")
        self.m.ClearSelection2(True)
        bot[0].Select4(False, NOTHING); top[0].Select4(True, NOTHING)
        dH = self._add_dim(self.m.AddDimension2((U + W / 2) / 1000 + 0.01, V / 1000, 0), h, H_true, "H")
        # locate the rectangle by its left and bottom edges (the centre point is not reliably
        # created by SolidWorks when the graphics are not refreshing)
        num = lambda *xs: all(isinstance(x, (int, float)) for x in xs)
        edge_x = U - W / 2 if num(cu, w) else "(%s)-(%s)/2" % (cu, w)
        edge_y = V - H_true / 2 if num(cv_, h) else "(%s)-(%s)/2" % (cv_, h)
        fix = []
        for line, val, target, expr, tag in ((left[0], U - W / 2, U - W / 2, edge_x, "X"),
                                             (bot[0], V - H / 2, V - H_true / 2, edge_y, "Y")):
            self.m.ClearSelection2(True)
            line.Select4(False, NOTHING)
            self._origin()
            if abs(val) < EPS:
                self.m.SketchAddConstraints("sgCOINCIDENT")
            else:
                d = self._add_dim(self.m.AddDimension2(val / 2000, val / 2000, 0), expr, target, tag)
                fix.append((d, abs(target)))
        if H != H_true:
            dH.SystemValue = H_true / 1000.0
            for d, target in fix:
                d.SystemValue = target / 1000.0

    def circle(self, cu, cv_, d):
        U, V, D = (self.p.ev(x) for x in (cu, cv_, d))
        at = lambda: sum(1 for p in self._pts()
                         if abs(p.X * 1000 - U) < 1e-4 and abs(p.Y * 1000 - V) < 1e-4)
        n_before = at()
        seg = self.sm.CreateCircleByRadius(U / 1000, V / 1000, 0, D / 2000)
        if seg is None:
            raise RuntimeError("circle failed in %s" % self.name)
        self.m.ClearSelection2(True)
        seg.Select4(False, NOTHING)
        self._add_dim(self.m.AddDimension2((U + D) / 1000, (V + D) / 1000, 0), d, D, "Dia")
        if at() > n_before:  # concentric circles share an already-located centre point
            self._place(self._find(U, V), cu, cv_)

    def slot(self, a, b, w):
        """Straight slot between centre points a=(u,v) and b=(u,v) with full width w."""
        Au, Av, Bu, Bv, W = (self.p.ev(x) for x in (a[0], a[1], b[0], b[1], w))
        s = self.sm.CreateSketchSlot(0, 0, W / 1000, Au / 1000, Av / 1000, 0, Bu / 1000, Bv / 1000, 0,
                                     0, 0, 0, 1, False)
        if s is None:
            raise RuntimeError("slot failed in %s" % self.name)
        # width: distance between the two straight sides (the most recent non-construction lines)
        L = math.hypot(Bu - Au, Bv - Av)
        nx, ny = -(Bv - Av) / L, (Bu - Au) / L
        sides = []
        for seg in cv(self.sk, "GetSketchSegments") or []:
            if seg.ConstructionGeometry or cv(seg, "GetType") != 0:
                continue
            p0 = cv(seg, "GetStartPoint2")
            for sgn in (1, -1):
                ex, ey = Au + sgn * nx * W / 2, Av + sgn * ny * W / 2
                fx, fy = Bu + sgn * nx * W / 2, Bv + sgn * ny * W / 2
                for qx, qy in ((ex, ey), (fx, fy)):
                    if abs(p0.X * 1000 - qx) < 1e-3 and abs(p0.Y * 1000 - qy) < 1e-3:
                        sides.append(seg)
        uniq = []
        for sgm in sides:
            if all(sgm is not u for u in uniq):
                uniq.append(sgm)
        if len(uniq) < 2:
            raise RuntimeError("slot sides not found in %s" % self.name)
        self.m.ClearSelection2(True)
        uniq[-2].Select4(False, NOTHING); uniq[-1].Select4(True, NOTHING)
        self._add_dim(self.m.AddDimension2((Au + Bu) / 2000 + 0.01, (Av + Bv) / 2000 + 0.01, 0), w, W, "W")
        self._place(self._find(Au, Av), a[0], a[1])
        self._place(self._find(Bu, Bv), b[0], b[1])


class Asm(_Doc):
    def __init__(self, cad, name, title=""):
        self._init_doc(cad, name, cad.tpl_asm, title)
        self.comps = {}

    def add(self, doc_path, rot=IDENTITY, t=(0, 0, 0), fix=False, key=None):
        arr = sw_pose(rot, t)
        comp = self.m.AddComponent5(doc_path, 0, "", False, "", arr[9], arr[10], arr[11])
        if comp is None:
            raise RuntimeError("AddComponent failed: " + doc_path)
        comp.Transform2 = self.cad.math.CreateTransform(dvec(arr))
        if fix:
            self.m.ClearSelection2(True)
            comp.Select4(False, NOTHING, False)
            cv(self.m, "FixComponent")
        self.comps[key or comp.Name2] = comp
        return comp

    def _sel_feat(self, ref, append, mark):
        comp_key, feat = ref
        f = (self.comps[comp_key].FeatureByName(feat) if comp_key else self.m.FeatureByName(feat))
        if f is None:
            raise RuntimeError("mate reference not found: %s / %s" % ref)
        if not f.Select2(append, mark):
            raise RuntimeError("cannot select %s / %s" % ref)

    def mate(self, kind, ref1, ref2, dist=0.0, lo=None, hi=None, align=2, name=None, flip=False):
        """kind: 0 coincident, 1 concentric, 5 distance (limit if lo/hi given)."""
        self.m.ClearSelection2(True)
        self._sel_feat(ref1, False, 1)
        self._sel_feat(ref2, True, 1)
        err = byref_int()
        up = (hi if hi is not None else dist) / 1000.0
        low = (lo if lo is not None else dist) / 1000.0
        mt = self.m.AddMate5(kind, align, flip, dist / 1000.0, up, low, 1, 1, 0, 0, 0, False, False, 0, err)
        if mt is None or err.value not in (0, 1):
            raise RuntimeError("mate failed (%s): %s <-> %s" % (err.value, ref1, ref2))
        if name:
            self.m.FeatureByPositionReverse(0).Name = name
        return mt


def stl_sw_to_ros(src, dst):
    """Convert a binary STL exported by SolidWorks (SW frame, mm) to ROS frame in metres."""
    data = open(src, "rb").read()
    n = struct.unpack("<I", data[80:84])[0]
    out = bytearray(b"swcad: ROS REP-103 frame, metres".ljust(80, b" "))
    out += struct.pack("<I", n)
    lo = [1e9] * 3
    hi = [-1e9] * 3
    for i in range(n):
        off = 84 + i * 50
        v = struct.unpack("<12f", data[off:off + 48])
        verts = []
        for k in range(3):
            X, Y, Z = v[3 + 3 * k: 6 + 3 * k]
            p = (X / 1000.0, -Z / 1000.0, Y / 1000.0)
            verts.append(p)
            for j in range(3):
                lo[j] = min(lo[j], p[j]); hi[j] = max(hi[j], p[j])
        ax, ay, az = (verts[1][j] - verts[0][j] for j in range(3))
        bx, by, bz = (verts[2][j] - verts[0][j] for j in range(3))
        nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
        ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        out += struct.pack("<12fH", nx / ln, ny / ln, nz / ln, *verts[0], *verts[1], *verts[2], 0)
    open(dst, "wb").write(out)
    return n, lo, hi
