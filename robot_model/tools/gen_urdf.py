"""
gen_urdf.py - write the ROS 2 description package from robot_spec + exported meshes.

    python gen_urdf.py BUILD_DIR OUT_PACKAGE_DIR

Link / joint names match turtlebot3_manipulation_description (ROS 2 Humble) exactly, so the
official MoveIt 2 config (SRDF, OMPL planners), ros2_control controllers and Gazebo plugins
keep working. Inertial values are the official ROBOTIS values (measured hardware).
"""
import math
import os
import shutil
import sys

import robot_spec as S

PKG = "tb3_omx_description"
MESH = "package://%s/meshes/" % PKG


def m(v):
    return " ".join(("%.6f" % (x / 1000.0)).rstrip("0").rstrip(".") if x else "0" for x in v)


def r(v):
    return " ".join(("%.6f" % x).rstrip("0").rstrip(".") if x else "0" for x in v)


COLORS = {
    "frame": S.FRAME, "plate": S.PLATE, "pcb": S.PCB, "blue": S.BLUE, "rubber": S.RUBBER,
    "alu": S.ALU,
}
COLOR_OF = {v: k for k, v in COLORS.items()}

# official inertials: (mass, com xyz m, ixx ixy ixz iyy iyz izz)
INERTIA = {
    "base_link": (1.3729096, (0, 0, 0), (8.7002718e-03, -4.7576583e-05, 1.1160499e-04, 8.6195418e-03, -3.5422299e-06, 1.4612727e-02)),
    "wheel": (2.8498940e-02, (0, 0, 0), (1.1175580e-05, -4.2369783e-11, -5.9381719e-09, 1.1192413e-05, -1.4400107e-11, 2.0712558e-05)),
    "caster": (0.005, (0, 0, 0), (0.001, 0, 0, 0.001, 0, 0.001)),
    "base_scan": (0.114, (0, 0, 0), (0.001, 0, 0, 0.001, 0, 0.001)),
    "link1": (7.9119962e-02, (3.0876154e-04, 0, -1.2176461e-04), (1.2505234e-05, 0, -1.7855208e-07, 2.1898364e-05, 0, 1.9267361e-05)),
    "link2": (9.8406837e-02, (-3.0184870e-04, 5.4043684e-04, 0.018 + 2.9433464e-02), (3.4543422e-05, -1.6031095e-08, -3.8375155e-07, 3.2689329e-05, 2.8511935e-08, 1.8850320e-05)),
    "link3": (1.3850917e-01, (1.0308393e-02, 3.7743363e-04, 1.0170197e-01), (3.3055381e-04, -9.7940978e-08, -3.8505711e-05, 3.4290447e-04, -1.5717516e-06, 6.0346498e-05)),
    "link4": (1.3274562e-01, (9.0909590e-02, 3.8929816e-04, 2.2413279e-04), (3.0654178e-05, -1.2764155e-06, -2.6874417e-07, 2.4230292e-04, 1.1559550e-08, 2.5155057e-04)),
    "link5": (1.4327573e-01, (4.4206755e-02, 3.6839985e-07, 8.9142216e-03), (8.0870749e-05, 0, -1.0157896e-06, 7.5980465e-05, 0, 9.3127351e-05)),
    "finger": (1.0e-03, (0, 0, 0), (1.0e-06, 0, 0, 1.0e-06, 0, 1.0e-06)),
}


def inertial(key):
    mass, com, I = INERTIA[key]
    return ('    <inertial>\n      <origin xyz="%s" rpy="0 0 0"/>\n      <mass value="%g"/>\n'
            '      <inertia ixx="%g" ixy="%g" ixz="%g" iyy="%g" iyz="%g" izz="%g"/>\n    </inertial>\n'
            % ((r(com), mass) + I))


def visual(mesh, color, xyz=(0, 0, 0), rpy=(0, 0, 0)):
    return ('    <visual>\n      <origin xyz="%s" rpy="%s"/>\n      <geometry><mesh filename="%s%s.stl"/></geometry>\n'
            '      <material name="%s"/>\n    </visual>\n' % (m(xyz), r(rpy), MESH, mesh, color))


def collision(geom, xyz=(0, 0, 0), rpy=(0, 0, 0)):
    return ('    <collision>\n      <origin xyz="%s" rpy="%s"/>\n      <geometry>%s</geometry>\n    </collision>\n'
            % (m(xyz), r(rpy), geom))


def mesh_geom(name):
    return '<mesh filename="%s%s.stl"/>' % (MESH, name)


def link(name, body=""):
    return '  <link name="${prefix}%s">\n%s  </link>\n\n' % (name, body) if body else '  <link name="${prefix}%s"/>\n\n' % name


def joint(name, kind, parent, child, xyz, rpy=(0, 0, 0), axis=None, limit=None, mimic=None):
    s = '  <joint name="${prefix}%s" type="%s">\n    <parent link="${prefix}%s"/>\n    <child link="${prefix}%s"/>\n' \
        '    <origin xyz="%s" rpy="%s"/>\n' % (name, kind, parent, child, m(xyz), r(rpy))
    if axis:
        s += '    <axis xyz="%s"/>\n' % r(axis)
    if limit:
        s += '    <limit velocity="4.8" effort="1" lower="%s" upper="%s"/>\n' % (r([limit[0]]), r([limit[1]]))
    if mimic:
        s += '    <mimic joint="${prefix}%s" multiplier="1"/>\n' % mimic
    if kind in ("revolute", "prismatic"):
        s += '    <dynamics damping="0.1"/>\n'
    return s + '  </joint>\n\n'


def body_macro():
    out = []
    # ---------------------------------------------------------------- mobile base
    out.append(link("base_footprint"))
    out.append(joint("base_joint", "fixed", "base_footprint", "base_link", (0, 0, S.BASE_LINK_Z)))
    vis = ""
    for name, rot, xyz, rpy in S.CHASSIS_LAYOUT:
        if name in S.URDF_BASE_VISUALS:
            vis += visual(name.lower(), COLOR_OF[S.URDF_BASE_VISUALS[name]], xyz, rpy)
    col = collision('<box size="0.266 0.266 0.094"/>', (S.CHASSIS_X, 0, 47))  # official box
    out.append(link("base_link", vis + col + inertial("base_link")))
    for side, sgn in (("left", 1), ("right", -1)):
        out.append(joint("wheel_%s_joint" % side, "continuous", "base_link", "wheel_%s_link" % side,
                         (S.WHEEL_XYZ[0], sgn * S.WHEEL_XYZ[1], S.WHEEL_XYZ[2]), (-1.57, 0, 0), axis=(0, 0, 1)))
        out.append(link("wheel_%s_link" % side, visual("tb13_wheel", "rubber")
                        + collision('<cylinder length="0.018" radius="0.033"/>') + inertial("wheel")))
    for side, sgn in (("right", -1), ("left", 1)):
        out.append(joint("caster_back_%s_joint" % side, "fixed", "base_link", "caster_back_%s_link" % side,
                         (S.CASTER_XYZ[0], sgn * S.CASTER_XYZ[1], S.CASTER_XYZ[2]), (-1.57, 0, 0)))
        out.append(link("caster_back_%s_link" % side,
                        collision('<box size="0.030 0.009 0.020"/>', (0, 1, 0)) + inertial("caster")))
    out.append(joint("imu_joint", "fixed", "base_link", "imu_link", S.IMU_XYZ))
    out.append(link("imu_link"))
    out.append(joint("scan_joint", "fixed", "base_link", "base_scan", S.SCAN_XYZ))
    out.append(link("base_scan", visual("tb12_lds01_lidar", "rubber")
                    + collision('<cylinder length="0.0395" radius="0.030"/>', (0, 0, -11.25)) + inertial("base_scan")))
    out.append(joint("camera_joint", "fixed", "base_link", "camera_link", S.CAMERA_XYZ))
    out.append(link("camera_link", collision('<box size="0.015 0.030 0.027"/>', (5, 11, 13))))
    out.append(joint("camera_rgb_joint", "fixed", "camera_link", "camera_rgb_frame", S.CAMERA_RGB_XYZ))
    out.append(link("camera_rgb_frame"))
    out.append(joint("camera_rgb_optical_joint", "fixed", "camera_rgb_frame", "camera_rgb_optical_frame",
                     (0, 0, 0), (-1.57, 0, -1.57)))
    out.append(link("camera_rgb_optical_frame"))
    # ---------------------------------------------------------------- manipulator
    out.append(joint("base_fixed", "fixed", "base_link", "link1", S.ARM_MOUNT_XYZ))
    arm = [("link1", "om01_link1"), ("link2", "om02_link2"), ("link3", "om03_link3"),
           ("link4", "om04_link4"), ("link5", "om05_link5")]
    joints = [("joint1", S.J1, (0, 0, 1)), ("joint2", S.J2, (0, 1, 0)), ("joint3", S.J3, (0, 1, 0)),
              ("joint4", S.J4, (0, 1, 0))]
    for i, (ln, mesh) in enumerate(arm):
        out.append(link(ln, visual(mesh, "frame") + collision(mesh_geom(mesh)) + inertial(ln)))
        if i < len(joints):
            jn, xyz, ax = joints[i]
            out.append(joint(jn, "revolute", ln, arm[i + 1][0], xyz, axis=ax, limit=S.LIMITS[jn]))
    out.append(joint("gripper_left_joint", "prismatic", "link5", "gripper_left_link", S.GRIP, axis=(0, 1, 0),
                     limit=S.LIMITS["gripper"]))
    out.append(link("gripper_left_link", visual("om06_gripper_finger", "frame")
                    + collision(mesh_geom("om06_gripper_finger")) + inertial("finger")))
    out.append('  <joint name="${prefix}gripper_right_joint_mimic" type="fixed">\n'
               '    <parent link="${prefix}link5"/>\n    <child link="dummy_mimic_fix"/>\n  </joint>\n'
               '  <link name="dummy_mimic_fix"/>\n\n')
    out.append(joint("gripper_right_joint", "prismatic", "link5", "gripper_right_link",
                     (S.GRIP[0], -S.GRIP[1], S.GRIP[2]), axis=(0, -1, 0), limit=S.LIMITS["gripper"],
                     mimic="gripper_left_joint"))
    flip = (math.pi, 0, 0)  # same finger mesh, rotated so the jaw faces the left finger
    out.append(link("gripper_right_link", visual("om06_gripper_finger", "frame", rpy=flip)
                    + collision(mesh_geom("om06_gripper_finger"), rpy=flip) + inertial("finger")))
    out.append(joint("end_effector_joint", "fixed", "link5", "end_effector_link", S.EE))
    out.append(link("end_effector_link"))
    return "".join(out)


def materials():
    return "".join('  <material name="%s"><color rgba="%.3f %.3f %.3f 1"/></material>\n' % ((k,) + v)
                   for k, v in COLORS.items())


HEADER = """<?xml version="1.0"?>
<!--
  Mobile Manipulator: TurtleBot3 Waffle Pi + OpenMANIPULATOR-X
  Generated from the parametric SolidWorks 2025 model by tools/gen_urdf.py.
  Kinematics, joint limits, link/joint names and inertials are identical to the official
  ROBOTIS turtlebot3_manipulation_description (ROS 2 Humble); the meshes come from the
  parametric SolidWorks parts in 01_SolidWorks_2025.
-->
"""


def main():
    build, out = sys.argv[1], sys.argv[2]
    for d in ("urdf", "meshes", "launch", "rviz", "scripts"):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    body = body_macro()
    meshes = sorted({l.split("meshes/")[1].split('"')[0] for l in body.splitlines() if "meshes/" in l})
    for f in meshes:
        shutil.copy(os.path.join(build, "meshes", f), os.path.join(out, "meshes", f))
    # 1) standalone URDF (no xacro needed)
    plain = HEADER + '<robot name="turtlebot3_manipulation">\n' + materials() + "\n" + body.replace("${prefix}", "") + "</robot>\n"
    open(os.path.join(out, "urdf", "tb3_omx.urdf"), "w").write(plain)
    # 2) xacro macro + drop-in top-level xacro (uses official gazebo + ros2_control macros)
    macro = (HEADER + '<robot xmlns:xacro="http://www.ros.org/wiki/xacro">\n' + materials()
             + '\n  <xacro:macro name="tb3_omx" params="prefix">\n\n' + body
             + '  </xacro:macro>\n</robot>\n')
    open(os.path.join(out, "urdf", "tb3_omx_body.urdf.xacro"), "w").write(macro)
    top = HEADER + """<robot name="turtlebot3_manipulation" xmlns:xacro="http://www.ros.org/wiki/xacro">
  <xacro:arg name="prefix" default="" />
  <xacro:arg name="use_sim" default="false" />
  <xacro:arg name="use_fake_hardware" default="false" />
  <xacro:arg name="fake_sensor_commands" default="false" />

  <!-- geometry from the SolidWorks model (this package) -->
  <xacro:include filename="$(find tb3_omx_description)/urdf/tb3_omx_body.urdf.xacro" />
  <!-- official Gazebo + ros2_control macros (turtlebot3_manipulation_description) -->
  <xacro:include filename="$(find turtlebot3_manipulation_description)/gazebo/turtlebot3_waffle_pi.gazebo.xacro" />
  <xacro:include filename="$(find turtlebot3_manipulation_description)/gazebo/open_manipulator_x.gazebo.xacro" />
  <xacro:include filename="$(find turtlebot3_manipulation_description)/ros2_control/turtlebot3_manipulation_system.ros2_control.xacro" />

  <xacro:tb3_omx prefix="$(arg prefix)" />
  <xacro:turtlebot3_waffle_pi_gazebo prefix="$(arg prefix)" />
  <xacro:open_manipulator_x_gazebo prefix="$(arg prefix)" />

  <xacro:turtlebot3_manipulation_system
    name="TurtleBot3ManipulationSystem" prefix="$(arg prefix)" use_sim="$(arg use_sim)"
    use_fake_hardware="$(arg use_fake_hardware)"
    fake_sensor_commands="$(arg fake_sensor_commands)"/>

  <gazebo>
    <plugin name="gazebo_ros2_control" filename="libgazebo_ros2_control.so">
      <parameters>$(find turtlebot3_manipulation_bringup)/config/gazebo_controller_manager.yaml</parameters>
    </plugin>
  </gazebo>
</robot>
"""
    open(os.path.join(out, "urdf", "tb3_omx.urdf.xacro"), "w").write(top)
    print("URDF written: %d meshes" % len(meshes))


if __name__ == "__main__":
    main()
