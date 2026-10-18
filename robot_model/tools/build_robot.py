"""
build_robot.py - regenerate the whole SolidWorks 2025 model, STL meshes and renders.

    python build_robot.py [BUILD_DIR] [--parts NAME,NAME] [--no-asm]

SolidWorks 2025 must be installed (it is started automatically through COM).
Keep BUILD_DIR short (SolidWorks rejects paths longer than ~255 characters).
"""
import json
import os
import sys
import time

import swcad
from swcad import cv, byref_int
import build_parts
from build_parts import PARTS

DEFAULT_BUILD = r"C:\Users\%s\AppData\Local\Temp\tb3omx2" % os.environ.get("USERNAME", "user")


def build_assemblies(cad, build):
    import robot_spec as S
    sw_dir = os.path.join(build, "01_SolidWorks_2025")
    img_dir = os.path.join(build, "04_Renders")
    P = lambda n: os.path.join(sw_dir, n + ".SLDPRT")
    for n in PARTS:
        cad.open(P(n))

    # ---- chassis subassembly: origin = base_link, every component fixed
    t = time.time()
    a = cad.asm("ASM01_TB3_Waffle_Pi_Base", "TurtleBot3 Waffle Pi mobile base")
    for i, (name, rot, xyz, _) in enumerate(S.CHASSIS_LAYOUT):
        a.add(P(name), rot, xyz, fix=True, key="%s#%d" % (name, i))
    chassis = a.save(os.path.join(sw_dir, "ASM01_TB3_Waffle_Pi_Base.SLDASM"))
    a.png(os.path.join(img_dir, "ASM01_TB3_Waffle_Pi_Base.png"))
    print("chassis assembly %.0fs" % (time.time() - t), flush=True)

    # ---- top-level mobile manipulator
    t = time.time()
    a = cad.asm("ASM00_TB3_OpenManipulatorX",
                "Mobile manipulator: TurtleBot3 Waffle Pi + OpenMANIPULATOR-X")
    a.g("Wheel_Axle_Z", S.BASE_LINK_Z + S.WHEEL_XYZ[2], "wheel axle height above ground")
    a.g("Wheel_Y", S.WHEEL_XYZ[1], "wheel centre-plane offset (track/2)")
    a.ref_plane("Wheel_ZP", "XY", "Wheel_Axle_Z")
    a.ref_plane("Wheel_LP", "XZ", "Wheel_Y")
    a.ref_plane("Wheel_RP", "XZ", "-Wheel_Y")
    a.ref_axis("Wheel_Axis", "Wheel_ZP", "Right Plane")
    a.add(chassis, S.I3, S.P_BASE, fix=True, key="chassis")
    a.add(P("TB12_LDS01_Lidar"), S.I3, S.P_SCAN, fix=True, key="lidar")
    a.add(P("OM01_Link1"), S.I3, S.P_LINK1, fix=True, key="link1")
    a.add(P("OM02_Link2"), S.I3, S.P_LINK2, key="link2")
    a.add(P("OM03_Link3"), S.I3, S.P_LINK3, key="link3")
    a.add(P("OM04_Link4"), S.I3, S.P_LINK4, key="link4")
    a.add(P("OM05_Link5"), S.I3, S.P_LINK5, key="link5")
    a.add(P("OM06_Gripper_Finger"), S.I3, S.P_FINGER_L, key="finger_l")
    a.add(P("OM06_Gripper_Finger"), S.RX_180, S.P_FINGER_R, key="finger_r")
    a.add(P("TB13_Wheel"), S.RX_M90, S.P_WHEEL_L, key="wheel_l")
    a.add(P("TB13_Wheel"), S.RX_M90, S.P_WHEEL_R, key="wheel_r")
    # revolute joints: collinear axes + coincident plane
    a.mate(0, ("link1", "J1_Axis"), ("link2", "Axis_Z"), name="joint1_axis")
    a.mate(0, ("link1", "J1_ZP"), ("link2", "Top Plane"), name="joint1_plane")
    a.mate(0, ("link2", "J2_Axis"), ("link3", "Axis_Y"), name="joint2_axis")
    a.mate(0, ("link2", "Front Plane"), ("link3", "Front Plane"), name="joint2_plane")
    a.mate(0, ("link3", "J3_Axis"), ("link4", "Axis_Y"), name="joint3_axis")
    a.mate(0, ("link3", "Front Plane"), ("link4", "Front Plane"), name="joint3_plane")
    a.mate(0, ("link4", "J4_Axis"), ("link5", "Axis_Y"), name="joint4_axis")
    a.mate(0, ("link4", "Front Plane"), ("link5", "Front Plane"), name="joint4_plane")
    # prismatic gripper fingers with travel limits (URDF -10 .. +19 mm around 21 mm)
    lo, hi = S.GRIP[1] + S.LIMITS["gripper"][0] * 1000, S.GRIP[1] + S.LIMITS["gripper"][1] * 1000
    ref = 60.0  # = Grip_Ref in OM05_Link5: travel is measured from the plane on the far side
    for side, plane, flip in (("finger_l", "GL_REF", True), ("finger_r", "GR_REF", False)):
        a.mate(0, ("link5", "G_XP"), (side, "Right Plane"), name=side + "_x")
        a.mate(0, ("link5", "Top Plane"), (side, "Top Plane"), name=side + "_z")
        a.mate(5, ("link5", plane), (side, "Front Plane"), dist=S.GRIP[1] + ref, lo=lo + ref,
               hi=hi + ref, name=side + "_travel", flip=flip)
    # wheels: revolute about the axle
    for side, plane in (("wheel_l", "Wheel_LP"), ("wheel_r", "Wheel_RP")):
        a.mate(0, (None, "Wheel_Axis"), (side, "Axis_Z"), name=side + "_axle")
        a.mate(0, (None, plane), (side, "Top Plane"), name=side + "_plane")
    top = a.save(os.path.join(sw_dir, "ASM00_TB3_OpenManipulatorX.SLDASM"))
    for view, tag in (("*Isometric", "iso"), ("*Front", "side"), ("*Right", "front"), ("*Top", "top")):
        a.m.ShowNamedView2(view, -1)
        cv(a.m, "ViewZoomtofit2")
        a.m.SaveAs3(os.path.join(img_dir, "ASM00_%s.png" % tag), 0, 1)
    a.iso_view()
    os.makedirs(os.path.join(build, "02_STEP"), exist_ok=True)
    a.export(os.path.join(build, "02_STEP", "TB3_OpenManipulatorX_Mobile_Manipulator.STEP"))
    a.m.Save3(1, byref_int(), byref_int())
    print("top assembly %.0fs" % (time.time() - t), flush=True)
    return top


def main():
    args = sys.argv[1:]
    build = args[0] if args and not args[0].startswith("--") else DEFAULT_BUILD
    only = None
    if "--parts" in args:
        only = args[args.index("--parts") + 1].split(",")
    sw_dir = os.path.join(build, "01_SolidWorks_2025")
    img_dir = os.path.join(build, "04_Renders", "parts")
    raw_dir = os.path.join(build, "_stl_raw")
    mesh_dir = os.path.join(build, "meshes")
    for d in (sw_dir, img_dir, raw_dir, mesh_dir):
        os.makedirs(d, exist_ok=True)
    cad = swcad.CAD()
    cad.sw.CloseAllDocuments(True)
    rep_path = os.path.join(build, "parts_report.json")
    report = json.load(open(rep_path)) if os.path.exists(rep_path) else {}
    t0 = time.time()
    try:
        for name, fn in PARTS.items():
            if only and name not in only:
                continue
            t = time.time()
            p = fn(cad)
            p.save(os.path.join(sw_dir, name + ".SLDPRT"))
            p.png(os.path.join(img_dir, name + ".png"))
            raw = p.export(os.path.join(raw_dir, name + ".STL"))
            ntri, lo, hi = swcad.stl_sw_to_ros(raw, os.path.join(mesh_dir, name.lower() + ".stl"))
            bb = p.bbox_ros()
            mp = p.mass_props()
            report[name] = {"bbox_mm": [round(v, 2) for v in bb], "mass_kg": round(mp["mass"], 4),
                            "stl_triangles": ntri, "globals": p.G}
            print("%-26s %5.1fs  x[%7.1f %7.1f] y[%7.1f %7.1f] z[%7.1f %7.1f] %.3fkg %5d tri"
                  % ((name, time.time() - t) + tuple(bb) + (mp["mass"], ntri)), flush=True)
            json.dump(report, open(rep_path, "w"), indent=1)
        print("parts done in %.0fs" % (time.time() - t0), flush=True)
        if "--no-asm" not in args:
            build_assemblies(cad, build)
    finally:
        cad.sw.CommandInProgress = False


if __name__ == "__main__":
    main()
