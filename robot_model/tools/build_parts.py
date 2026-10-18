"""
build_parts.py - parametric part definitions (one function per SolidWorks part) for the
TurtleBot3 Waffle Pi + OpenMANIPULATOR-X mobile manipulator.

Each part is modelled in its own frame (ROS axes, mm). Arm links, wheel, LiDAR and finger use
their URDF link frame as part origin, so the STL meshes export with zero visual offset.
Waffle plates and the camera are modelled in base_link x/y coordinates.
Purchased components (DYNAMIXEL, boards, battery, LiDAR) are envelope models with the
manufacturer's main dimensions.
"""
import math

from robot_spec import (ALU, BLUE, BRASS, FRAME, GLASS, PCB, PLATE, RED, RUBBER, WHITE,
                        CHASSIS_X, CHASSIS_L, CHASSIS_W, J1, J2, J3, J4, GRIP, EE, ARM_MOUNT_XYZ)

PARTS = {}


def part(fn):
    PARTS[fn.__name__] = fn
    return fn


# ============================================================ TURTLEBOT3 WAFFLE PI
def waffle_plate(p, top):
    p.g("Plate_L", CHASSIS_L, "plate length along x")
    p.g("Plate_W", CHASSIS_W, "plate width along y")
    p.g("Plate_X", CHASSIS_X, "plate centre x in base_link")
    p.g("Plate_R", 20, "corner radius")
    p.g("Plate_T", 3, "plate thickness")
    p.g("Hole_D", 9, "waffle hole diameter")
    p.g("Hole_P", 24, "waffle hole pitch")
    p.g("Hole_N", 10, "holes per row / column")
    with p.sketch("XY") as s:
        s.rect("Plate_X", 0, "Plate_L", "Plate_W", "Plate_R")
        s.grid("Plate_X - (Hole_N - 1)*Hole_P/2", "-(Hole_N - 1)*Hole_P/2", "Hole_D",
               "Hole_N", "Hole_N", "Hole_P", "Hole_P")
    p.extrude(s, 0, "Plate_T", name="Waffle_Plate", color=PLATE)
    if top:
        p.g("Arm_X", ARM_MOUNT_XYZ[0], "OpenMANIPULATOR link1 x in base_link")
        p.g("Cut_L", 50, "joint-1 DYNAMIXEL cut-out length")
        p.g("Cut_W", 32, "joint-1 DYNAMIXEL cut-out width")
        with p.sketch("XY") as s:
            s.rect("Arm_X", 0, "Cut_L", "Cut_W", 2)
        p.extrude(s, cut=True, through=True, name="Arm_Cutout")
    p.material("ABS")
    p.body_color(PLATE)
    return p


@part
def TB01_Waffle_Plate(cad):
    return waffle_plate(cad.part("TB01_Waffle_Plate", "TurtleBot3 waffle plate (layers 1 and 2)"), False)


@part
def TB02_Waffle_Plate_Top(cad):
    return waffle_plate(cad.part("TB02_Waffle_Plate_Top",
                                 "TurtleBot3 waffle plate, top layer with OpenMANIPULATOR cut-out"), True)


def pcb_support(cad, name, length):
    p = cad.part(name, "TurtleBot3 PCB support / spacer %g mm" % length)
    p.g("SO_L", length, "spacer length")
    p.g("SO_D", 6, "outer diameter")
    p.g("SO_Bore", 3.2, "M3 bore")
    with p.sketch("XY") as s:
        s.circle(0, 0, "SO_D")
        s.circle(0, 0, "SO_Bore")
    p.extrude(s, 0, "SO_L", name="Spacer", color=ALU)
    p.material("6061 Alloy")
    p.body_color(ALU)
    return p


@part
def TB03_PCB_Support_42(cad):
    return pcb_support(cad, "TB03_PCB_Support_42", 42)


@part
def TB04_PCB_Support_40(cad):
    return pcb_support(cad, "TB04_PCB_Support_40", 40)


def xm430_globals(p):
    p.g("XM_L", 46.5, "DYNAMIXEL XM430 length")
    p.g("XM_W", 28.5, "DYNAMIXEL XM430 width")
    p.g("XM_D", 34, "DYNAMIXEL XM430 depth (along horn axis)")
    p.g("Horn_Off", 12, "horn axis offset from body centre")
    p.g("Horn_D", 22, "horn diameter")
    p.g("Horn_T", 2.5, "horn thickness")


@part
def TB05_DYNAMIXEL_XM430_W210(cad):
    p = cad.part("TB05_DYNAMIXEL_XM430_W210", "DYNAMIXEL XM430-W210-T wheel actuator (envelope)")
    xm430_globals(p)
    with p.sketch("XY") as s:
        s.rect(0, 0, "XM_L", "XM_W", 2)
    p.extrude(s, "-XM_D/2", "XM_D/2", name="Housing", color=RUBBER)
    with p.sketch("XY") as s:
        s.circle("Horn_Off", 0, "Horn_D")
    p.extrude(s, "XM_D/2", "XM_D/2 + Horn_T", name="Horn", color=ALU)
    with p.sketch("XY") as s:
        s.circle("Horn_Off", 0, 14)
    p.extrude(s, "-XM_D/2 - 1.5", "-XM_D/2", name="Idler", color=ALU)
    p.material("PA Type 6")
    p.body_color(RUBBER)
    return p


@part
def TB06_Motor_Bracket(cad):
    p = cad.part("TB06_Motor_Bracket", "Wheel DYNAMIXEL mounting bracket")
    p.g("Br_L", 46.5, "bracket length")
    p.g("Br_W", 34, "bracket width")
    p.g("Br_T", 5.75, "bracket height (sets wheel axle height 33 mm)")
    with p.sketch("XY") as s:
        s.rect(0, 0, "Br_L", "Br_W", 2)
    p.extrude(s, 0, "Br_T", name="Bracket", color=FRAME)
    p.material("6061 Alloy")
    p.body_color(FRAME)
    return p


@part
def TB07_LiPo_Battery(cad):
    p = cad.part("TB07_LiPo_Battery", "LiPo 11.1 V 1800 mAh battery LB-012 (envelope)")
    p.g("Bat_L", 88, "length")
    p.g("Bat_W", 35, "width")
    p.g("Bat_H", 26.5, "height")
    with p.sketch("XY") as s:
        s.rect(0, 0, "Bat_L", "Bat_W", 3)
    p.extrude(s, 0, "Bat_H", name="Cell_Pack", color=BLUE)
    with p.sketch("XY") as s:
        s.rect("-Bat_L/2 - 4", 0, 8, 12, 1)
    p.extrude(s, 8, 18, name="Connector", color=RED)
    p.material("ABS")
    p.body_color(BLUE)
    return p


@part
def TB08_OpenCR_Board(cad):
    p = cad.part("TB08_OpenCR_Board", "OpenCR 1.0 controller board (envelope)")
    p.g("PCB_L", 105, "board length")
    p.g("PCB_W", 75, "board width")
    p.g("PCB_T", 1.6, "board thickness")
    with p.sketch("XY") as s:
        s.rect(0, 0, "PCB_L", "PCB_W", 3)
    p.extrude(s, 0, "PCB_T", name="PCB", color=PCB)
    with p.sketch("XY") as s:
        s.rect(0, 0, 14, 14)
        s.rect(45, -28, 8, 10)
    p.extrude(s, "PCB_T", "PCB_T + 4", name="ICs", color=RUBBER)
    with p.sketch("XY") as s:
        s.rect(-30, 30, 34, 6)
        s.rect(30, 30, 34, 6)
        s.rect(-44, -28, 12, 9)
    p.extrude(s, "PCB_T", "PCB_T + 9", name="Connectors", color=WHITE)
    p.material("ABS")
    p.body_color(PCB)
    return p


@part
def TB09_Raspberry_Pi_4(cad):
    p = cad.part("TB09_Raspberry_Pi_4", "Raspberry Pi 4 Model B SBC (envelope)")
    p.g("PCB_L", 85, "board length")
    p.g("PCB_W", 56, "board width")
    p.g("PCB_T", 1.4, "board thickness")
    with p.sketch("XY") as s:
        s.rect(0, 0, "PCB_L", "PCB_W", 3)
    p.extrude(s, 0, "PCB_T", name="PCB", color=PCB)
    with p.sketch("XY") as s:
        s.rect(32, -18, 21, 16)
        s.rect(34, 0, 17, 13)
        s.rect(34, 17, 17, 13)
    p.extrude(s, "PCB_T", "PCB_T + 15.5", name="Ports", color=ALU)
    with p.sketch("XY") as s:
        s.rect(-10, 0, 15, 15)
        s.rect(-8, 24, 51, 5)
    p.extrude(s, "PCB_T", "PCB_T + 8.5", name="SoC_GPIO", color=RUBBER)
    p.material("ABS")
    p.body_color(PCB)
    return p


@part
def TB10_Ball_Caster(cad):
    p = cad.part("TB10_Ball_Caster", "Rear ball caster")
    p.g("Cas_D", 20, "housing diameter")
    p.g("Cas_H", 6, "housing height")
    p.g("Ball_D", 8, "ball diameter")
    with p.sketch("XY") as s:
        s.circle(0, 0, "Cas_D")
    p.extrude(s, "-Cas_H", 0, name="Housing", color=RUBBER)
    with p.sketch("XY") as s:
        s.circle(0, 0, "Ball_D")
    p.extrude(s, "-Cas_H - Ball_D/2", "-Cas_H", name="Ball", color=ALU)
    p.material("AISI 304")
    p.body_color(ALU)
    return p


@part
def TB11_Pi_Camera(cad):
    p = cad.part("TB11_Pi_Camera", "Raspberry Pi Camera v2 with front bracket (base_link coordinates)")
    p.g("Front_X", CHASSIS_X + CHASSIS_L / 2, "front edge of the waffle plates")
    p.g("Br_T", 2, "bracket thickness")
    p.g("Br_W", 30, "bracket width")
    p.g("Br_Z0", 80, "bracket bottom")
    p.g("Br_Z1", 106, "bracket top")
    p.g("Cam_S", 25, "camera board size")
    p.g("Lens_D", 8, "lens diameter")
    p.g("Lens_Z", 93, "lens centre height (camera_rgb_frame)")
    with p.sketch("XY") as s:
        s.rect("Front_X + Br_T/2", 0, "Br_T", "Br_W")
    p.extrude(s, "Br_Z0", "Br_Z1", name="Bracket", color=FRAME)
    with p.sketch("XY") as s:
        s.rect("Front_X - 7", 0, 14, "Br_W")
    p.extrude(s, 91, "91 + Br_T", name="Bracket_Tab", color=FRAME)
    with p.sketch("YZ") as s:
        s.rect(0, "Lens_Z", "Cam_S", "Cam_S - 1")
    p.extrude(s, "Front_X + Br_T", "Front_X + Br_T + 1", name="Camera_PCB", color=PCB)
    with p.sketch("YZ") as s:
        s.rect(0, "Lens_Z", 8.5, 8.5)
    p.extrude(s, "Front_X + Br_T + 1", "Front_X + Br_T + 4", name="Lens_Housing", color=RUBBER)
    with p.sketch("YZ") as s:
        s.circle(0, "Lens_Z", "Lens_D")
    p.extrude(s, "Front_X + Br_T + 4", "Front_X + Br_T + 5", name="Lens", color=GLASS)
    p.material("ABS")
    p.body_color(PCB)
    return p


@part
def TB12_LDS01_Lidar(cad):
    p = cad.part("TB12_LDS01_Lidar", "LDS-01 360 deg laser distance sensor (origin = base_scan)")
    p.g("Base_D", 60, "base diameter")
    p.g("Base_Z0", -31, "base bottom (sits on the top plate)")
    p.g("Turret_D", 56, "rotating turret diameter")
    p.g("Turret_Z0", -12, "turret bottom")
    p.g("Turret_Z1", 3, "turret top")
    p.g("Cap_D", 58, "cap diameter")
    p.g("Cap_Z1", 8.5, "cap top")
    with p.sketch("XY") as s:
        s.circle(0, 0, "Base_D")
    p.extrude(s, "Base_Z0", "Turret_Z0", name="Base", color=RUBBER)
    with p.sketch("XY") as s:
        s.circle(0, 0, "Turret_D")
    p.extrude(s, "Turret_Z0", "Turret_Z1", name="Turret_Window", color=GLASS)
    with p.sketch("XY") as s:
        s.circle(0, 0, "Cap_D")
    p.extrude(s, "Turret_Z1", "Cap_Z1", name="Cap", color=RUBBER)
    p.material("ABS")
    p.body_color(RUBBER)
    return p


@part
def TB13_Wheel(cad):
    p = cad.part("TB13_Wheel", "TurtleBot3 wheel + tire, 66 mm (origin = wheel joint, axle = +z)")
    p.g("Tire_D", 66, "tire outer diameter (URDF radius 0.033)")
    p.g("Tire_W", 18, "tire width (URDF length 0.018)")
    p.g("Rim_D", 46, "rim diameter")
    p.g("Rim_W", 14, "rim width")
    p.g("Hub_D", 18, "hub diameter")
    p.g("Hub_W", 22, "hub width")
    with p.sketch("XY") as s:
        s.circle(0, 0, "Tire_D")
        s.circle(0, 0, "Rim_D")
    p.extrude(s, mid="Tire_W", name="Tire", color=RUBBER)
    with p.sketch("XY") as s:
        s.circle(0, 0, "Rim_D")
        for k in range(5):
            a = 2 * math.pi * k / 5
            s.circle(round(14 * math.cos(a), 4), round(14 * math.sin(a), 4), 8)
    p.extrude(s, mid="Rim_W", name="Rim", color=FRAME)
    with p.sketch("XY") as s:
        s.circle(0, 0, "Hub_D")
    p.extrude(s, mid="Hub_W", name="Hub", color=ALU)
    p.material("ABS")
    p.body_color(RUBBER)
    p.ref_axis("Axis_Z", "Front Plane", "Right Plane")
    return p


# ============================================================ OPENMANIPULATOR-X
def horns(p, cx, cz):
    """DYNAMIXEL horn (+y) and idler (-y) of the parent joint, carried by this link."""
    for lo, hi, nm in (("XM_D/2", "XM_D/2 + Horn_T", "Horn"), ("-XM_D/2 - Horn_T", "-XM_D/2", "Idler")):
        with p.sketch("XZ") as s:
            s.circle(cx, cz, "Horn_D")
        p.extrude(s, lo, hi, name=nm, color=ALU)


def side_plates(p, a, b, prefix):
    """Pair of frame plates hugging the DYNAMIXELs (|y| = XM_D/2 .. XM_D/2 + Frame_T)."""
    for side, (lo, hi) in (("L", ("XM_D/2", "XM_D/2 + Frame_T")), ("R", ("-XM_D/2 - Frame_T", "-XM_D/2"))):
        with p.sketch("XZ") as s:
            s.slot(a, b, "Frame_W")
        p.extrude(s, lo, hi, name="%s_%s" % (prefix, side), color=FRAME)


def frame_globals(p):
    xm430_globals(p)
    p.g("Frame_W", 22, "frame plate width")
    p.g("Frame_T", 2.5, "frame plate thickness")


@part
def OM01_Link1(cad):
    p = cad.part("OM01_Link1", "OpenMANIPULATOR-X link1: base + joint-1 DYNAMIXEL (URDF link1)")
    xm430_globals(p)
    p.g("J1_X", J1[0], "joint1 axis x (URDF)")
    p.g("J1_Z", J1[2], "joint1 height (URDF) = DYNAMIXEL top face")
    p.g("Base_L", 62, "base frame length")
    p.g("Base_W", 44, "base frame width")
    p.g("Base_T", 3, "base frame thickness")
    with p.sketch("XY") as s:
        s.rect(0, 0, "XM_L", "XM_W", 2)
    p.extrude(s, "-XM_D/2", "XM_D/2", name="Joint1_DYNAMIXEL", color=RUBBER)
    with p.sketch("XY") as s:
        s.rect(0, 0, "Base_L", "Base_W", 4)
        s.rect(0, 0, "XM_L", "XM_W")
    p.extrude(s, 0, "Base_T", name="Base_Frame", color=FRAME)
    p.material("ABS")
    p.body_color(RUBBER)
    p.ref_plane("J1_XP", "YZ", "J1_X")
    p.ref_plane("J1_ZP", "XY", "J1_Z")
    p.ref_axis("J1_Axis", "J1_XP", "Front Plane")
    return p


@part
def OM02_Link2(cad):
    p = cad.part("OM02_Link2", "OpenMANIPULATOR-X link2: horn bracket + joint-2 DYNAMIXEL (URDF link2)")
    xm430_globals(p)
    p.g("J2_Z", J2[2], "joint2 height above joint1 (URDF)")
    p.g("Br_T", 2, "bracket thickness")
    p.g("Wall_Z1", "J2_Z - 25.5", "bracket side wall top (follows joint 2)")
    with p.sketch("XY") as s:
        s.circle(0, 0, "Horn_D")
    p.extrude(s, 0, "Horn_T", name="Joint1_Horn", color=ALU)
    with p.sketch("XY") as s:
        s.rect(0, 0, "XM_W + 2*Br_T", "XM_D", 1)
    p.extrude(s, "Horn_T", "Horn_T + Br_T", name="Bracket_Base", color=FRAME)
    with p.sketch("XY") as s:
        s.rect("XM_W/2 + Br_T/2", 0, "Br_T", "XM_D")
        s.rect("-XM_W/2 - Br_T/2", 0, "Br_T", "XM_D")
    p.extrude(s, "Horn_T + Br_T", "Wall_Z1", name="Bracket_Walls", color=FRAME)
    with p.sketch("XY") as s:
        s.rect(0, 0, "XM_W", "XM_D", 2)
    p.extrude(s, "J2_Z - Horn_Off - XM_L/2", "J2_Z - Horn_Off + XM_L/2", name="Joint2_DYNAMIXEL", color=RUBBER)
    p.material("ABS")
    p.body_color(FRAME)
    p.ref_axis("Axis_Z", "Front Plane", "Right Plane")
    p.ref_plane("J2_ZP", "XY", "J2_Z")
    p.ref_axis("J2_Axis", "J2_ZP", "Right Plane")
    return p


@part
def OM03_Link3(cad):
    p = cad.part("OM03_Link3", "OpenMANIPULATOR-X link3: upper-arm frame + joint-3 DYNAMIXEL (URDF link3)")
    frame_globals(p)
    p.g("J3_X", J3[0], "joint3 x offset from joint2 (URDF)")
    p.g("J3_Z", J3[2], "joint3 z offset from joint2 (URDF)")
    p.g("Frame_Z1", "J3_Z - 28", "frame plates upper end (follows joint 3)")
    horns(p, 0, 0)
    side_plates(p, (0, 0), ("J3_X*Frame_Z1/J3_Z", "Frame_Z1"), "Frame")
    with p.sketch("XY") as s:
        s.rect("J3_X", 0, "XM_W", "XM_D", 2)
    p.extrude(s, "J3_Z - Horn_Off - XM_L/2", "J3_Z - Horn_Off + XM_L/2", name="Joint3_DYNAMIXEL", color=RUBBER)
    p.material("ABS")
    p.body_color(FRAME)
    p.ref_axis("Axis_Y", "Top Plane", "Right Plane")
    p.ref_plane("J3_XP", "YZ", "J3_X")
    p.ref_plane("J3_ZP", "XY", "J3_Z")
    p.ref_axis("J3_Axis", "J3_XP", "J3_ZP")
    return p


@part
def OM04_Link4(cad):
    p = cad.part("OM04_Link4", "OpenMANIPULATOR-X link4: forearm frame + joint-4 DYNAMIXEL (URDF link4)")
    frame_globals(p)
    p.g("J4_X", J4[0], "joint4 x offset from joint3 (URDF)")
    p.g("Frame_X1", "J4_X - 28", "frame plates end (follows joint 4)")
    horns(p, 0, 0)
    side_plates(p, (0, 0), ("Frame_X1", 0), "Frame")
    with p.sketch("XY") as s:
        s.rect("J4_X - Horn_Off", 0, "XM_L", "XM_D", 2)
    p.extrude(s, "-XM_W/2", "XM_W/2", name="Joint4_DYNAMIXEL", color=RUBBER)
    p.material("ABS")
    p.body_color(FRAME)
    p.ref_axis("Axis_Y", "Top Plane", "Right Plane")
    p.ref_plane("J4_XP", "YZ", "J4_X")
    p.ref_axis("J4_Axis", "J4_XP", "Top Plane")
    return p


@part
def OM05_Link5(cad):
    p = cad.part("OM05_Link5", "OpenMANIPULATOR-X link5: wrist frame + gripper DYNAMIXEL (URDF link5)")
    frame_globals(p)
    p.g("Grip_X", GRIP[0], "finger joint x (URDF)")
    p.g("EE_X", EE[0], "end_effector_link x (URDF)")
    p.g("GM_X", 44, "gripper DYNAMIXEL centre x")
    p.g("Frame_X1", "GM_X - 14", "wrist plates end (follows gripper DYNAMIXEL)")
    p.g("Rail_T", 4.75, "gripper base / guide rail thickness (fingers ride on its front face)")
    p.g("Rail_L", 84, "gripper base plate length (y)")
    p.g("Rail_H", 24, "gripper base plate height")
    horns(p, 0, 0)
    side_plates(p, (0, 0), ("Frame_X1", 0), "Frame")
    with p.sketch("XY") as s:
        s.rect("GM_X", 0, "XM_L", "XM_D", 2)
    p.extrude(s, "-XM_W/2", "XM_W/2", name="Gripper_DYNAMIXEL", color=RUBBER)
    with p.sketch("XY") as s:
        s.rect("GM_X + XM_L/2 + Rail_T/2", 0, "Rail_T", "Rail_L", 1)
    p.extrude(s, "-Rail_H/2", "Rail_H/2", name="Gripper_Base", color=FRAME)
    p.material("ABS")
    p.body_color(FRAME)
    p.ref_axis("Axis_Y", "Top Plane", "Right Plane")
    p.ref_plane("G_XP", "YZ", "Grip_X")
    p.ref_plane("EE_XP", "YZ", "EE_X")
    # finger travel references on the far side, so each finger can only sit on its own side
    p.g("Grip_Ref", 60, "finger travel reference plane offset (|y|)")
    p.ref_plane("GL_REF", "XZ", "-Grip_Ref")
    p.ref_plane("GR_REF", "XZ", "Grip_Ref")
    return p


@part
def OM06_Gripper_Finger(cad):
    p = cad.part("OM06_Gripper_Finger", "OpenMANIPULATOR-X gripper palm/finger (URDF gripper_left/right_link)")
    p.g("Car_L", 9.7, "slider block length (rides on the gripper base)")
    p.g("Car_W", 12, "slider block width (y)")
    p.g("Fin_L", round(EE[0] - GRIP[0], 3), "finger length (tip = end_effector_link)")
    p.g("Fin_T", 5, "finger thickness (y)")
    p.g("Fin_H", 20, "finger height")
    p.g("Rail_T", 4.75, "guide rail thickness on link5 (lip length)")
    p.g("Rail_H", 24, "guide rail height on link5")
    p.g("Lip_T", 2, "lip thickness clamping over the rail")
    with p.sketch("XY") as s:
        s.rect("-Car_L/2", 0, "Car_L", "Car_W", 1)
    p.extrude(s, "-Rail_H/2 - Lip_T", "Rail_H/2 + Lip_T", name="Slider", color=FRAME)
    for side, (lo, hi) in (("Top", ("Rail_H/2", "Rail_H/2 + Lip_T")),
                           ("Bottom", ("-Rail_H/2 - Lip_T", "-Rail_H/2"))):
        with p.sketch("XY") as s:
            s.rect("-Car_L - Rail_T/2", 0, "Rail_T", "Car_W", 1)
        p.extrude(s, lo, hi, name="Rail_Lip_" + side, color=FRAME)
    with p.sketch("XY") as s:
        s.rect("Fin_L/2", 0, "Fin_L", "Fin_T", 1)
    p.extrude(s, "-Fin_H/2", "Fin_H/2", name="Finger", color=FRAME)
    # gripping jaw on the inner side (-y); the right finger is this part rotated 180 deg about x
    p.g("Jaw_X0", 20, "jaw start along the finger")
    p.g("Jaw_D", 4, "jaw depth towards the object")
    p.g("Pad_T", 1.5, "rubber grip pad thickness")
    p.g("Pad_H", 16, "rubber grip pad height")
    with p.sketch("XY") as s:
        s.rect("(Jaw_X0 + Fin_L)/2", "-Fin_T/2 - Jaw_D/2", "Fin_L - Jaw_X0", "Jaw_D", 1)
    p.extrude(s, "-Fin_H/2", "Fin_H/2", name="Jaw", color=FRAME)
    with p.sketch("XY") as s:
        s.rect("(Jaw_X0 + Fin_L)/2", "-Fin_T/2 - Jaw_D - Pad_T/2", "Fin_L - Jaw_X0 - 2", "Pad_T")
    p.extrude(s, "-Pad_H/2", "Pad_H/2", name="Grip_Pad", color=RUBBER)
    p.material("ABS")
    p.body_color(FRAME)
    return p
