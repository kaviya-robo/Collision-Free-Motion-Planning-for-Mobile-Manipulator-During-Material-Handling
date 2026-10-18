"""
render_urdf.py - independent check of the URDF: assemble all visual meshes with forward
kinematics (optionally at given joint angles) and save a matplotlib render.

    python render_urdf.py PACKAGE_DIR OUT.png [joint=value ...]
"""
import math
import os
import struct
import sys
import xml.etree.ElementTree as ET

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def rpy_mat(r, p, y):
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                     [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                     [-sp, cp * sr, cp * cr]])


def tf(origin):
    T = np.eye(4)
    if origin is not None:
        T[:3, :3] = rpy_mat(*map(float, origin.get("rpy", "0 0 0").split()))
        T[:3, 3] = list(map(float, origin.get("xyz", "0 0 0").split()))
    return T


def axis_rot(axis, a):
    k = np.array(axis) / np.linalg.norm(axis)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    T = np.eye(4)
    T[:3, :3] = np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K
    return T


def load_stl(path):
    d = open(path, "rb").read()
    n = struct.unpack("<I", d[80:84])[0]
    a = np.frombuffer(d[84:84 + 50 * n], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    return a["v"].reshape(n, 3, 3).astype(float)


def main():
    pkg, out = sys.argv[1], sys.argv[2]
    q = {k: float(v) for k, v in (a.split("=") for a in sys.argv[3:])}
    root = ET.parse(os.path.join(pkg, "urdf", "tb3_omx.urdf")).getroot()
    colors = {m.get("name"): tuple(map(float, m.find("color").get("rgba").split()))
              for m in root.findall("material") if m.find("color") is not None}
    joints = {j.find("child").get("link"): j for j in root.findall("joint")}

    def world(link):
        if link not in joints:
            return np.eye(4)
        j = joints[link]
        T = world(j.find("parent").get("link")) @ tf(j.find("origin"))
        ax = j.find("axis")
        name = j.get("name")
        mim = j.find("mimic")
        val = q.get(mim.get("joint") if mim is not None else name, 0.0)
        if ax is not None and val:
            axis = list(map(float, ax.get("xyz").split()))
            if j.get("type") == "prismatic":
                M = np.eye(4); M[:3, 3] = np.array(axis) * val
                T = T @ M
            else:
                T = T @ axis_rot(axis, val)
        return T

    fig = plt.figure(figsize=(10, 8))
    axp = fig.add_subplot(111, projection="3d")
    allv = []
    for l in root.findall("link"):
        W = world(l.get("name"))
        for v in l.findall("visual"):
            mesh = v.find("geometry/mesh")
            if mesh is None:
                continue
            f = os.path.join(pkg, "meshes", os.path.basename(mesh.get("filename")))
            tri = load_stl(f)
            T = W @ tf(v.find("origin"))
            pts = tri.reshape(-1, 3) @ T[:3, :3].T + T[:3, 3]
            tri = pts.reshape(-1, 3, 3)
            allv.append(pts)
            c = colors.get(v.find("material").get("name"), (0.6, 0.6, 0.6, 1))
            nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
            nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
            shade = 0.45 + 0.55 * np.clip(nrm @ np.array([0.3, -0.5, 0.8]) / 1.0, 0, 1)
            fc = np.clip(np.outer(shade, c[:3]), 0, 1)
            axp.add_collection3d(Poly3DCollection(tri, facecolors=fc, edgecolors="none"))
    P = np.vstack(allv)
    lo, hi = P.min(0), P.max(0)
    c, s = (lo + hi) / 2, (hi - lo).max() / 2
    axp.set_xlim(c[0] - s, c[0] + s); axp.set_ylim(c[1] - s, c[1] + s); axp.set_zlim(0, 2 * s)
    axp.set_box_aspect((1, 1, 1))
    axp.view_init(elev=22, azim=-60)
    axp.set_xlabel("x [m]"); axp.set_ylabel("y [m]"); axp.set_zlabel("z [m]")
    axp.set_title("URDF check (%s)" % (", ".join("%s=%g" % kv for kv in q.items()) or "zero pose"))
    plt.tight_layout()
    plt.savefig(out, dpi=110)
    print("bbox m:", np.round(lo, 4), np.round(hi, 4))


if __name__ == "__main__":
    main()
