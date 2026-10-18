"""make_readme.py - write README.md (with the parameter tables from parts_report.json)."""
import json
import os
import sys

root = sys.argv[1]
rep = json.load(open(os.path.join(root, "tools", "parts_report.json")))
import re

notes = {}
for line in open(os.path.join(root, "tools", "build_parts.py"), encoding="utf-8"):
    for name, note in re.findall(r'p\.g\("(\w+)",\s*[^,]+(?:\([^)]*\))?[^,]*,\s*"([^"]*)"\)', line):
        notes.setdefault(name, note)

rows = []
for part in sorted(rep):
    r = rep[part]
    bb = r["bbox_mm"]
    rows.append("\n#### %s\nSize %.1f x %.1f x %.1f mm, mass %.3f kg (SolidWorks material)\n\n"
                "| Global variable | Value | Meaning |\n|---|---|---|\n"
                % (part, bb[1] - bb[0], bb[3] - bb[2], bb[5] - bb[4], r["mass_kg"]))
    for k, v in r["globals"].items():
        rows.append("| `%s` | %g | %s |\n" % (k, v, notes.get(k, "")))

readme = """# Mobile Manipulator: TurtleBot3 + OpenMANIPULATOR-X

A SolidWorks 2025 model of the **TurtleBot3 Waffle Pi** mobile base carrying an
**OpenMANIPULATOR-X** arm. Every part has editable parameters. The package also includes a
ROS 2 description (URDF + meshes) for your motion-planning project: MoveIt 2 + OMPL (RRT / RRT* / PRM) + Gazebo.

![robot](04_Renders/ASM00_iso.png)

## Folder contents

| Folder | What is inside |
|---|---|
| `01_SolidWorks_2025/` | 19 parametric parts (`.SLDPRT`) + 2 assemblies (`.SLDASM`), saved with SolidWorks 2025 |
| `02_STEP/` | Whole robot as one STEP file, for other CAD tools |
| `03_ROS2_URDF/tb3_omx_description/` | ROS 2 package: URDF, xacro, STL meshes, RViz launch, Gazebo/MoveIt drop-in script |
| `04_Renders/` | Images of the assembly and of every part |
| `tools/` | Python scripts that regenerate everything (SolidWorks API + URDF writer) |

## SolidWorks 2025

Open **`01_SolidWorks_2025/ASM00_TB3_OpenManipulatorX.SLDASM`**. Keep all files of this folder
together. Parts and assemblies sit in one folder, so SolidWorks finds the references wherever you unzip.

| File | Content |
|---|---|
| `ASM00_TB3_OpenManipulatorX.SLDASM` | Complete robot (origin = ground, `base_footprint`) |
| `ASM01_TB3_Waffle_Pi_Base.SLDASM` | Mobile base subassembly (origin = `base_link`, 10 mm above ground) |
| `TB01..TB13_*.SLDPRT` | TurtleBot3 Waffle Pi parts: waffle plates, PCB supports, DYNAMIXEL XM430, bracket, battery, OpenCR, Raspberry Pi 4, ball caster, Pi camera, LDS-01, wheel |
| `OM01..OM06_*.SLDPRT` | OpenMANIPULATOR-X: link1 ... link5 (each with its DYNAMIXEL) and gripper finger |

**Moving the arm in SolidWorks.** Joints 1 to 4 are mated as real revolute joints: a collinear
axis mate plus a coincident plane on each joint. The wheels rotate on their axle. Drag a link
to move it.

**Two-finger gripper (end effector).** The gripper DYNAMIXEL and a guide rail sit on link5.
Two parallel fingers (`OM06_Gripper_Finger`, the right one is the same part flipped 180 deg)
clamp onto the rail with top and bottom lips. Each finger carries a jaw and a rubber grip pad,
and the pads face each other. Each finger is a slider mate with a limit mate (-10 ... +19 mm
from the 21 mm home position, same as the URDF), so the jaw opening runs from about 6 mm to 64 mm.
The tool point `end_effector_link` is at the finger tips (link5 x = 126 mm).

![gripper](04_Renders/ASM00_gripper_iso.png)

**Parameters.** In any part, open *Tools > Equations* (Global Variables), change a value and
rebuild. All sketch and feature dimensions are linked to these variables. Examples: `J3_Z`
(upper-arm length), `J4_X` (forearm length), `Hole_P` / `Hole_N` (waffle hole grid), `Tire_D`
(wheel). If you change a joint offset, change the same value in `tools/robot_spec.py` and rerun
`tools/build_robot.py` + `tools/gen_urdf.py` so the assembly and the URDF follow.

**Coordinates.** Parts are modelled in the ROS convention (x forward, y left, z up) and mapped
onto the SolidWorks axes, so the robot stands upright in the *Isometric* view. Each arm link,
wheel, finger and the LiDAR has its part origin exactly on its URDF link frame. Reference
planes and axes (`J1_Axis`, `J2_Axis`, ..., `G_XP`) mark the joint locations.

## Kinematics (identical to the official ROBOTIS model)

| Joint | Parent -> child | Origin (m) | Axis | Limits |
|---|---|---|---|---|
| base_fixed | base_link -> link1 | (-0.092, 0, 0.091) | fixed | - |
| joint1 | link1 -> link2 | (0.012, 0, 0.017) | z | +/- 0.9 pi |
| joint2 | link2 -> link3 | (0, 0, 0.0595) | y | -0.57 pi ... 0.5 pi |
| joint3 | link3 -> link4 | (0.024, 0, 0.128) | y | -0.3 pi ... 0.44 pi |
| joint4 | link4 -> link5 | (0.124, 0, 0) | y | -0.57 pi ... 0.65 pi |
| gripper_left/right | link5 -> gripper | (0.0817, +/-0.021, 0) | +/-y | -0.010 ... 0.019 m |
| end_effector_joint | link5 -> end_effector_link | (0.126, 0, 0) | fixed | - |
| wheel_left/right | base_link -> wheel | (0, +/-0.144, 0.023) | z (rpy -1.57) | continuous |

All 18 joints (origin, rpy, type and axis) were checked automatically against
`turtlebot3_manipulation_description` (ROS 2 Humble branch).

## ROS 2 (Humble, Ubuntu 22.04)

```bash
cd ~/turtlebot3_ws/src
cp -r <unzipped>/03_ROS2_URDF/tb3_omx_description .
cd ~/turtlebot3_ws && colcon build --symlink-install --packages-select tb3_omx_description
source install/setup.bash
ros2 launch tb3_omx_description display.launch.py      # RViz + joint sliders
```

* `urdf/tb3_omx.urdf`: standalone URDF that needs no other package. Use it in RViz, for
  `check_urdf`, or to import the robot into another tool.
* `urdf/tb3_omx.urdf.xacro`: drop-in version that reuses the official Gazebo plugins,
  ros2_control hardware and controllers from `turtlebot3_manipulation_description`.

### Gazebo + MoveIt 2 (for the motion-planning comparison)

The official launch files always load
`turtlebot3_manipulation_description/urdf/turtlebot3_manipulation.urdf.xacro`. The helper
script swaps that file for the one in this package and keeps a backup:

```bash
cd ~/turtlebot3_ws/src
git clone -b humble https://github.com/ROBOTIS-GIT/turtlebot3_manipulation.git
git clone -b humble https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git
sudo apt install ros-humble-dynamixel-sdk ros-humble-ros2-control ros-humble-ros2-controllers ros-humble-gripper-controllers ros-humble-moveit*
bash tb3_omx_description/scripts/use_with_turtlebot3_manipulation.sh ~/turtlebot3_ws
cd ~/turtlebot3_ws && colcon build --symlink-install && source install/setup.bash
ros2 launch turtlebot3_manipulation_moveit_config moveit_gazebo.launch.py
```

Undo it with `use_with_turtlebot3_manipulation.sh ~/turtlebot3_ws --undo`.
Link and joint names are unchanged, so the official SRDF, `ompl_planning.yaml` (choose
`RRTkConfigDefault`, `RRTstarkConfigDefault` or `PRMkConfigDefault` in the RViz MotionPlanning
panel), controllers and Nav2 configuration all work as they are.

Meshes are in metres, ROS frame, binary STL. Inertial values are the official ROBOTIS values
(measured hardware). Base and wheel collisions use the official primitives; arm collisions use
the link meshes.

## Notes and limits

* Purchased components (DYNAMIXEL XM430-W210, OpenCR 1.0, Raspberry Pi 4, LiPo LB-012,
  LDS-01, Pi camera) are simplified envelope models built from their main published dimensions.
  They are not the vendors' detailed CAD.
* The waffle plates are modelled as single 266 x 266 mm plates with a parametric hole grid.
  This matches the official collision footprint and wheel/caster positions.
* SolidWorks material is assigned per part (ABS, 6061 alloy, ...). It is used only for the
  SolidWorks mass properties; the URDF uses the official inertials.

## Regenerating (Windows + SolidWorks 2025 + Python 3 with pywin32)

```bash
cd tools
python build_robot.py C:\\temp\\tb3omx        # parts, assemblies, renders, STEP, raw meshes
python gen_urdf.py C:\\temp\\tb3omx ..\\03_ROS2_URDF\\tb3_omx_description
```

Keep the build folder path short, because SolidWorks rejects paths longer than about 255 characters.

## Part parameters (Tools > Equations in each part)
""" + "".join(rows)

open(os.path.join(root, "README.md"), "w", encoding="utf-8").write(readme)
print("README written, %d parts" % len(rep))
