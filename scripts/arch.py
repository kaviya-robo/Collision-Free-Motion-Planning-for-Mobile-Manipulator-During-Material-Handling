import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
NAVY="#1F2A44";TEAL="#1B9E77";GREY="#8a93a3"
def box(ax,x,y,w,h,t,fc="#F3F5F8",ec=NAVY,ls="-",fs=9,bold=False,tc=NAVY):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.02,rounding_size=0.06",fc=fc,ec=ec,lw=1.4,ls=ls))
    ax.text(x+w/2,y+h/2,t,ha="center",va="center",fontsize=fs,color=tc,fontweight="bold" if bold else "normal",linespacing=1.3)
def arr(ax,a,b,ls="-",c=NAVY):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle="-|>",mutation_scale=12,lw=1.3,color=c,ls=ls))
# ------------ fig 1: system architecture
fig,ax=plt.subplots(figsize=(12,6.6));ax.set_xlim(0,12);ax.set_ylim(0,6.6);ax.axis("off")
cols=[(0.2,"1. Design layer\n(done)"),(3.2,"2. Description layer\n(done)"),(6.2,"3. Planning / control\n(next step)"),(9.2,"4. Simulation / hardware\n(next step)")]
for x,t in cols:
    ax.add_patch(FancyBboxPatch((x,0.2),2.6,5.5,boxstyle="round,pad=0.02,rounding_size=0.1",fc="white",ec=GREY,lw=1,ls="--"))
    ax.text(x+1.3,5.35,t,ha="center",va="center",fontsize=10,fontweight="bold",color=TEAL if "done" in t else "#c07a00")
box(ax,0.4,3.8,2.2,0.9,"robot_spec.py\n(joint offsets, limits,\nlayout: single source)",fs=8)
box(ax,0.4,2.5,2.2,0.9,"SolidWorks 2025\n19 parametric parts\n2 assemblies",fs=8)
box(ax,0.4,1.2,2.2,0.9,"STEP export\nRenders",fs=8)
box(ax,3.4,3.8,2.2,0.9,"gen_urdf.py\n(writes URDF from\nthe same spec)",fs=8)
box(ax,3.4,2.5,2.2,0.9,"tb3_omx_description\nURDF / xacro,\n19 STL meshes",fs=8)
box(ax,3.4,1.2,2.2,0.9,"RViz display\n+ joint sliders",fs=8)
box(ax,6.4,3.8,2.2,0.9,"MoveIt 2 (move_group)\nSRDF, kinematics",ls="--",fs=8)
box(ax,6.4,2.5,2.2,0.9,"OMPL planners\nRRT | RRT* | PRM",ls="--",fs=8,fc="#E3F4EE")
box(ax,6.4,1.2,2.2,0.9,"ros2_control\narm + gripper controllers",ls="--",fs=8)
box(ax,9.4,3.8,2.2,0.9,"Gazebo\nphysics + sensors",ls="--",fs=8)
box(ax,9.4,2.5,2.2,0.9,"Nav2 + LiDAR\n(base navigation)",ls="--",fs=8)
box(ax,9.4,1.2,2.2,0.9,"Real robot\nOpenCR + DYNAMIXEL",ls="--",fs=8)
arr(ax,(1.5,3.8),(1.5,3.4));arr(ax,(1.5,2.5),(1.5,2.1))
arr(ax,(2.6,4.25),(3.4,4.25));arr(ax,(2.6,2.95),(3.4,2.95));arr(ax,(4.5,3.8),(4.5,3.4));arr(ax,(4.5,2.5),(4.5,2.1))
arr(ax,(5.6,2.95),(6.4,4.1),"--");arr(ax,(7.5,3.8),(7.5,3.4),"--");arr(ax,(7.5,2.5),(7.5,2.1),"--")
arr(ax,(8.6,1.65),(9.4,1.65),"--");arr(ax,(8.6,4.25),(9.4,4.25),"--");arr(ax,(10.5,2.5),(10.5,2.1),"--",c=GREY)
ax.text(6,6.2,"System architecture of the TurtleBot3 + OpenMANIPULATOR-X motion-planning project",ha="center",fontsize=12,fontweight="bold",color=NAVY)
ax.text(6,0.0,"solid boxes = completed in this project     dashed boxes = planned for the full MoveIt 2 / Gazebo study",ha="center",fontsize=8.5,color=GREY)
plt.savefig("out/arch_system.png",dpi=200,bbox_inches="tight");plt.close()
# ------------ fig 2: planning pipeline (what the benchmark implements)
fig,ax=plt.subplots(figsize=(12,3.4));ax.set_xlim(0,12);ax.set_ylim(0,3.4);ax.axis("off")
items=["Start q_s\nGoal q_g\n(joint space)","Planner\nRRT / RRT* / PRM\nsamples q in Q","Collision checker\nFK -> link capsules\nvs. obstacle spheres","Path\n(sequence of\nwaypoints)","Metrics\ntime, length,\nsuccess, nodes"]
xs=[0.2,2.6,5.0,7.5,9.8]
for x,t in zip(xs,items):box(ax,x,1.0,2.0,1.4,t,fs=9,fc="#E3F4EE" if "Planner" in t else "#F3F5F8")
for a,b in zip(xs[:-1],xs[1:]):arr(ax,(a+2.0,1.7),(b,1.7))
ax.annotate("",xy=(3.6,1.0),xytext=(6.0,1.0),arrowprops=dict(arrowstyle="<|-|>",lw=1.3,color=NAVY,connectionstyle="arc3,rad=0.35"))
ax.text(4.8,0.35,"free / in-collision queries",ha="center",fontsize=8.5,color=GREY)
ax.text(6,3.05,"Planning pipeline implemented in the benchmark",ha="center",fontsize=12,fontweight="bold",color=NAVY)
plt.savefig("out/arch_pipeline.png",dpi=200,bbox_inches="tight");plt.close()
# ------------ equations
EQ={
"fk":r"$^{0}\!T_{ee}(\mathbf{q})=T_{base}\,\prod_{i=1}^{4}\left[\,\mathrm{Trans}(\mathbf{o}_i)\;\mathrm{Rot}(\hat{\mathbf{a}}_i,\,q_i)\right]\,\mathrm{Trans}(\mathbf{o}_{ee})$",
"cfree":r"$\mathcal{Q}_{free}=\{\mathbf{q}:\ \mathbf{q}_{min}\leq\mathbf{q}\leq\mathbf{q}_{max},\ \ d\,(\mathrm{link}_i(\mathbf{q}),\,c_j)>r_j+r_l\ \ \forall i,j,\ \ z_i(\mathbf{q})\geq z_{min}\}$",
"dist":r"$d(\overline{\mathbf{ab}},\mathbf{c})=\min_{t\in[0,1]}\left\|\,\mathbf{a}+t(\mathbf{b}-\mathbf{a})-\mathbf{c}\,\right\|$",
"len":r"$L(\sigma)=\sum_{k=0}^{m-1}\left\|\,\mathbf{q}_{k+1}-\mathbf{q}_k\,\right\|_2$",
"steer":r"$\mathbf{q}_{new}=\mathbf{q}_{near}+\min\left(1,\ \dfrac{\eta}{\|\mathbf{q}_{rand}-\mathbf{q}_{near}\|}\right)(\mathbf{q}_{rand}-\mathbf{q}_{near})$",
"parent":r"$\mathbf{q}_{parent}=\arg\min_{\mathbf{q}_j\in\mathcal{Q}_{near}}\left[\,c(\mathbf{q}_j)+\|\mathbf{q}_j-\mathbf{q}_{new}\|\,\right]$",
"rewire":r"$c(\mathbf{q}_{new})+\|\mathbf{q}_{new}-\mathbf{q}_j\|<c(\mathbf{q}_j)\ \Rightarrow\ \mathrm{parent}(\mathbf{q}_j)\leftarrow\mathbf{q}_{new}$",
"radius":r"$r_n=\min\left\{\,\gamma\left(\dfrac{\ln n}{n}\right)^{1/d},\ \eta\right\},\qquad \gamma>2\left(1+\dfrac{1}{d}\right)^{1/d}\left(\dfrac{\mu(\mathcal{Q}_{free})}{\zeta_d}\right)^{1/d}$",
"opt":r"$P\left(\lim_{n\to\infty}c(\sigma_n)=c^{*}\right)=1\quad(\mathrm{RRT}^{*})$",
"prm":r"$E=\{(\mathbf{q}_i,\mathbf{q}_j):\ \mathbf{q}_j\in k\mathrm{NN}(\mathbf{q}_i),\ \overline{\mathbf{q}_i\mathbf{q}_j}\subset\mathcal{Q}_{free}\},\qquad w_{ij}=\|\mathbf{q}_i-\mathbf{q}_j\|$",
"dij":r"$D(v)=\min_{u:\,(u,v)\in E}\left[\,D(u)+w_{uv}\,\right],\qquad D(\mathbf{q}_s)=0$",
"dyn":r"$\mathbf{M}(\mathbf{q})\,\ddot{\mathbf{q}}+\mathbf{C}(\mathbf{q},\dot{\mathbf{q}})\,\dot{\mathbf{q}}+\mathbf{g}(\mathbf{q})=\boldsymbol{\tau}$",
"ctc":r"$\boldsymbol{\tau}=\mathbf{M}(\mathbf{q})\left[\ddot{\mathbf{q}}_d+K_d\,\dot{\mathbf{e}}+K_p\,\mathbf{e}\right]+\mathbf{C}(\mathbf{q},\dot{\mathbf{q}})\dot{\mathbf{q}}+\mathbf{g}(\mathbf{q}),\quad \mathbf{e}=\mathbf{q}_d-\mathbf{q}$",
}
for k,v in EQ.items():
    fig=plt.figure(figsize=(0.01,0.01));fig.text(0,0,v,fontsize=15);fig.savefig(f"out/eq_{k}.png",dpi=220,bbox_inches="tight",pad_inches=0.06,transparent=False,facecolor="white");plt.close()

def mat(fig,x,y,rows,label):
    fig.text(x,y+0.5,label,fontsize=14,ha="right",va="center")
    for r,row in enumerate(rows):
        for c,v in enumerate(row):fig.text(x+0.09+0.1*c,y+0.9-0.4*r,v,fontsize=14,ha="center",va="center")
    fig.text(x+0.04,y+0.5,"$\\left[\\right.$",fontsize=1,alpha=0)
fig=plt.figure(figsize=(8,1.3));
lab1="$\\mathrm{Rot}(\\hat{z},q)=$";lab2="$\\mathrm{Rot}(\\hat{y},q)=$"
import matplotlib.lines as ml
def block(x0,rows,lab):
    fig.text(x0,0.5,lab,fontsize=14,ha="right",va="center")
    for r,row in enumerate(rows):
        for c,v in enumerate(row):fig.text(x0+0.04+0.075*c,0.8-0.3*r,v,fontsize=13,ha="center",va="center")
    for xx in (x0+0.0125,x0+0.04+0.075*2+0.04):
        fig.add_artist(ml.Line2D([xx,xx],[0.12,0.92],color="k",lw=1.2))
block(0.20,[["$\\cos q$","$-\\sin q$","0"],["$\\sin q$","$\\cos q$","0"],["0","0","1"]],lab1)
block(0.68,[["$\\cos q$","0","$\\sin q$"],["0","1","0"],["$-\\sin q$","0","$\\cos q$"]],lab2)
fig.savefig("out/eq_rot.png",dpi=220,bbox_inches="tight",pad_inches=0.06,facecolor="white");plt.close()
print("ok")
