"""
robot_spec.py - single source of truth shared by the CAD build and the URDF writer.

Kinematics are identical to the official ROBOTIS TurtleBot3 Waffle Pi + OpenMANIPULATOR-X
description (turtlebot3_manipulation_description, ROS 2 Humble), so the URDF stays a drop-in
replacement for the official MoveIt 2 / Gazebo / Nav2 configuration. All values in mm, ROS frame.
"""
import math

# ---------------------------------------------------------------- colours (RGB 0..1)
ORANGE = (0.95, 0.42, 0.05)
ANTHRACITE = (0.22, 0.24, 0.26)  # RAL 7016-like (deck, joint caps)
WHITE = (0.92, 0.92, 0.90)       # RAL 9003-like (body shell)
RUBBER = (0.07, 0.07, 0.07)
ALU = (0.72, 0.74, 0.76)
YELLOW = (0.98, 0.76, 0.00)      # RAL 1003 safety yellow
RED = (0.78, 0.04, 0.04)         # RAL 3000 safety red
TEAL = (0.00, 0.80, 0.72)        # status LED light
PCB = (0.05, 0.38, 0.16)
BLUE = (0.10, 0.28, 0.65)
COPPER = (0.85, 0.52, 0.22)
BRASS = (0.80, 0.66, 0.32)
GLASS = (0.04, 0.05, 0.07)

# ---------------------------------------------------------------- kinematics (official values)
BASE_LINK_Z = 10.0                       # base_footprint -> base_link
WHEEL_XYZ = (0.0, 144.0, 23.0)           # base_link -> wheel_left (right: y negated)
WHEEL_R, WHEEL_W = 33.0, 18.0
CASTER_XYZ = (-177.0, 64.0, -4.0)
IMU_XYZ = (0.0, 0.0, 68.0)
SCAN_XYZ = (-24.0, 0.0, 122.0)
CAMERA_XYZ = (73.0, -11.0, 84.0)
CAMERA_RGB_XYZ = (3.0, 11.0, 9.0)
ARM_MOUNT_XYZ = (-92.0, 0.0, 91.0)       # base_link -> link1
J1 = (12.0, 0.0, 17.0)                   # link1 -> link2, axis z
J2 = (0.0, 0.0, 59.5)                    # link2 -> link3, axis y
J3 = (24.0, 0.0, 128.0)                  # link3 -> link4, axis y
J4 = (124.0, 0.0, 0.0)                   # link4 -> link5, axis y
GRIP = (81.7, 21.0, 0.0)                 # link5 -> gripper_left (right: y negated)
EE = (126.0, 0.0, 0.0)                   # link5 -> end_effector_link

LIMITS = {
    "joint1": (-math.pi * 0.9, math.pi * 0.9),
    "joint2": (-math.pi * 0.57, math.pi * 0.5),
    "joint3": (-math.pi * 0.3, math.pi * 0.44),
    "joint4": (-math.pi * 0.57, math.pi * 0.65),
    "gripper": (-0.010, 0.019),
}


def add(*vs):
    return tuple(sum(v[i] for v in vs) for i in range(3))


# Zero-pose positions in the top assembly frame (= base_footprint, ground level).
P_BASE = (0.0, 0.0, BASE_LINK_Z)
P_LINK1 = add(P_BASE, ARM_MOUNT_XYZ)
P_LINK2 = add(P_LINK1, J1)
P_LINK3 = add(P_LINK2, J2)
P_LINK4 = add(P_LINK3, J3)
P_LINK5 = add(P_LINK4, J4)
P_FINGER_L = add(P_LINK5, GRIP)
P_FINGER_R = add(P_LINK5, (GRIP[0], -GRIP[1], GRIP[2]))
P_SCAN = add(P_BASE, SCAN_XYZ)
P_WHEEL_L = add(P_BASE, WHEEL_XYZ)
P_WHEEL_R = add(P_BASE, (WHEEL_XYZ[0], -WHEEL_XYZ[1], WHEEL_XYZ[2]))

# ---------------------------------------------------------------- chassis layout (base_link frame)
CHASSIS_X = -64.0          # body centre x (official collision box centre)
CHASSIS_L = 266.0          # body length / width inside the bumpers & wheels
CHASSIS_W = 266.0
DECK_Z0 = 88.0             # deck top = 91 = arm mount height
DECK_T = 3.0
SHELF_Z0 = 45.0
STANDOFF_XY = [(x, y) for x in (-180.0, -64.0, 52.0) for y in (-110.0, 110.0)]
MOTOR_CENTER = (-12.0, 113.5, 23.0)  # drive motor body centre (left; right mirrored)


def rx(a):
    c, s = math.cos(a), math.sin(a)
    return ((1, 0, 0), (0, c, -s), (0, s, c))


def rz(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, -s, 0), (s, c, 0), (0, 0, 1))


I3 = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
RX_M90 = rx(-math.pi / 2)   # local z -> +y
RX_P90 = rx(math.pi / 2)    # local z -> -y
RZ_180 = rz(math.pi)
RX_180 = rx(math.pi)      # right gripper finger = left finger flipped (jaw faces inward)

FRAME = (0.80, 0.81, 0.83)   # light-grey OpenMANIPULATOR frames / brackets
PLATE = (0.16, 0.17, 0.18)   # TurtleBot3 waffle plates (dark grey plastic)

# (part name, rotation, translation in base_link frame mm, rpy for URDF)
CHASSIS_LAYOUT = [
    ("TB01_Waffle_Plate", I3, (0, 0, 0), (0, 0, 0)),                 # layer 1
    ("TB01_Waffle_Plate", I3, (0, 0, SHELF_Z0), (0, 0, 0)),          # layer 2
    ("TB02_Waffle_Plate_Top", I3, (0, 0, DECK_Z0), (0, 0, 0)),       # layer 3 (arm + LiDAR)
] + [("TB03_PCB_Support_42", I3, (x, y, 3.0), (0, 0, 0)) for x, y in STANDOFF_XY] \
  + [("TB04_PCB_Support_40", I3, (x, y, SHELF_Z0 + 3.0), (0, 0, 0)) for x, y in STANDOFF_XY] + [
    ("TB05_DYNAMIXEL_XM430_W210", RX_M90, MOTOR_CENTER, (-math.pi / 2, 0, 0)),
    ("TB05_DYNAMIXEL_XM430_W210", RX_P90, (MOTOR_CENTER[0], -MOTOR_CENTER[1], MOTOR_CENTER[2]), (math.pi / 2, 0, 0)),
    ("TB06_Motor_Bracket", I3, (MOTOR_CENTER[0], MOTOR_CENTER[1], 3.0), (0, 0, 0)),
    ("TB06_Motor_Bracket", I3, (MOTOR_CENTER[0], -MOTOR_CENTER[1], 3.0), (0, 0, 0)),
    ("TB07_LiPo_Battery", I3, (-110.0, 0, 3.0), (0, 0, 0)),
    ("TB08_OpenCR_Board", I3, (-140.0, 0, SHELF_Z0 + 3.0), (0, 0, 0)),
    ("TB09_Raspberry_Pi_4", I3, (0.0, 0, SHELF_Z0 + 3.0), (0, 0, 0)),
    ("TB10_Ball_Caster", I3, (CASTER_XYZ[0], CASTER_XYZ[1], 0.0), (0, 0, 0)),
    ("TB10_Ball_Caster", I3, (CASTER_XYZ[0], -CASTER_XYZ[1], 0.0), (0, 0, 0)),
    ("TB11_Pi_Camera", I3, (0, 0, 0), (0, 0, 0)),
]

# every chassis part is visible on the open TurtleBot3 frame -> all become base_link visuals
URDF_BASE_VISUALS = {
    "TB01_Waffle_Plate": PLATE, "TB02_Waffle_Plate_Top": PLATE, "TB03_PCB_Support_42": ALU,
    "TB04_PCB_Support_40": ALU, "TB05_DYNAMIXEL_XM430_W210": RUBBER, "TB06_Motor_Bracket": FRAME,
    "TB07_LiPo_Battery": BLUE, "TB08_OpenCR_Board": PCB, "TB09_Raspberry_Pi_4": PCB,
    "TB10_Ball_Caster": ALU, "TB11_Pi_Camera": PCB,
}
