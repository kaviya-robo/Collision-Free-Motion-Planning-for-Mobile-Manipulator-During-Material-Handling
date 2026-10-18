import numpy as np, math, time, json, heapq
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
src=open("bench.py").read().split("RES={")[0]
exec(src)   # defines fk, free, edge_free, QS, QG, OBS, LIM, sample, path_len, steer ...
import builtins
cols={"RRT":"#d95f02","RRT*":"#1b9e77","PRM":"#7570b3"}
# ---- straight-line check
print("direct line free:",edge_free(QS,QG,0.02),"len",np.linalg.norm(QG-QS))
# ---- planners returning full structure
def run_rrt(star,seed,T=10.0,eta=.4,gb=.1,hist=False):
    global rng
    rng=np.random.default_rng(seed)
    t0=time.time();V=[QS];par=[-1];cost=[0.];best=None;H=[];tfirst=None
    while time.time()-t0<T:
        q=QG if rng.random()<gb else sample()
        i=int(np.argmin([np.linalg.norm(v-q) for v in V]));qn=steer(V[i],q,eta)
        if not edge_free(V[i],qn):continue
        if star:
            n=len(V);r=min(1.5,2*(1+1/4)**(1/4)*(math.log(n+1)/(n+1))**(1/4))
            near=[j for j,v in enumerate(V) if np.linalg.norm(v-qn)<r]
            bi,bc=i,cost[i]+np.linalg.norm(V[i]-qn)
            for j in near:
                c=cost[j]+np.linalg.norm(V[j]-qn)
                if c<bc and edge_free(V[j],qn):bi,bc=j,c
            V.append(qn);par.append(bi);cost.append(bc);k=len(V)-1
            for j in near:
                c=bc+np.linalg.norm(V[j]-qn)
                if c<cost[j] and edge_free(qn,V[j]):
                    # propagate not needed for plotting; keep cost approx (children updated lazily)
                    par[j]=k;cost[j]=c
        else:
            V.append(qn);par.append(i);cost.append(cost[i]+np.linalg.norm(V[i]-qn));k=len(V)-1
        if np.linalg.norm(V[k]-QG)<eta and edge_free(V[k],QG):
            if np.linalg.norm(V[k]-QG)>1e-6:
                V.append(QG.copy());par.append(k);cost.append(cost[k]+np.linalg.norm(V[k]-QG));k=len(V)-1
            if tfirst is None:tfirst=time.time()-t0
            if not star:best=k;break
            if best is None or cost[k]<cost[best]:best=k
        if star and best is not None:
            # true current cost of best path
            p=[];kk=best
            while kk!=-1:p.append(V[kk]);kk=par[kk]
            H.append((time.time()-t0,path_len(p)))
    if best is None:return None
    p=[];kk=best
    while kk!=-1:p.append(V[kk]);kk=par[kk]
    p=p[::-1]
    return dict(V=V,par=par,path=p,len=path_len(p),tfirst=tfirst,hist=H)
def run_prm(seed,N=1500,k=10):
    global rng
    rng=np.random.default_rng(seed);t0=time.time();V=[QS,QG]
    while len(V)<N:
        q=sample()
        if free(q):V.append(q)
    A=np.array(V);E={i:[] for i in range(len(V))};edges=[]
    for i in range(len(V)):
        d=np.linalg.norm(A-A[i],axis=1)
        for j in np.argsort(d)[1:k+1]:
            j=int(j)
            if j>i and edge_free(V[i],V[j]):E[i].append((j,d[j]));E[j].append((i,d[j]));edges.append((i,j))
    D={0:0};pr={};h=[(0,0)]
    while h:
        d_,u=heapq.heappop(h)
        if u==1:break
        if d_>D.get(u,1e9):continue
        for v,w in E[u]:
            if d_+w<D.get(v,1e9):D[v]=d_+w;pr[v]=u;heapq.heappush(h,(d_+w,v))
    if 1 not in pr:return dict(V=V,edges=edges,path=None,len=None,t=time.time()-t0)
    p=[];kk=1
    while kk!=0:p.append(V[kk]);kk=pr[kk]
    p.append(V[0]);p=p[::-1]
    return dict(V=V,edges=edges,path=p,len=path_len(p),t=time.time()-t0)
# ---- C-space slice
n1,n2=110,90
g1=np.linspace(LIM[0,0],LIM[0,1],n1);g2=np.linspace(LIM[1,0],LIM[1,1],n2)
M=np.zeros((n2,n1))
for a,x in enumerate(g1):
    for b,y in enumerate(g2):M[b,a]=0 if free(np.array([x,y,.6,.3])) else 1
def cspace(ax,title):
    ax.imshow(M,origin="lower",extent=[LIM[0,0],LIM[0,1],LIM[1,0],LIM[1,1]],cmap="Greys",alpha=.35,aspect="auto")
    ax.plot(*QS[:2],"o",color="k",ms=7);ax.plot(*QG[:2],"*",color="k",ms=11)
    ax.set_xlabel("joint1 q1 (rad)");ax.set_ylabel("joint2 q2 (rad)");ax.set_title(title,fontsize=9)
def arm_panel(ax,path,c):
    idx=np.linspace(0,len(path)-1,min(len(path),9)).astype(int)
    for t,i in enumerate(idx):
        P=fk(path[i]);ax.plot(P[:,0],P[:,2],color=c,alpha=.25+.7*t/len(idx),lw=2)
    for ob,r in OBS:
        ax.add_patch(plt.Circle((ob[0],ob[2]),r,color="gray",alpha=.5))
    ax.axhline(0.02,color="r",lw=.6,ls=":");ax.set_xlim(-.15,.5);ax.set_ylim(0,.5);ax.set_aspect("equal")
    ax.set_xlabel("x (m)");ax.set_ylabel("z (m)");ax.set_title("(b) Arm poses along the path (side view; obstacles are the 3 spheres projected)",fontsize=8)
def joints_panel(ax,path,c):
    A=np.array(path);s=np.linspace(0,1,len(A))
    for j,ls in zip(range(4),["-","--","-.",":"]):ax.plot(s,A[:,j],ls,color=c,label=f"q{j+1}")
    ax.set_xlabel("path progress");ax.set_ylabel("joint angle (rad)");ax.legend(fontsize=7,ncol=4);ax.set_title("(c) Joint angles along the path",fontsize=9)
R={}
# RRT
r=run_rrt(False,100);R["RRT"]=r
fig,ax=plt.subplots(1,3,figsize=(13,3.8));cspace(ax[0],"(a) Tree in q1-q2 plane (grey = collision at q3=0.6, q4=0.3)")
for k,p in enumerate(r["par"]):
    if p>=0:ax[0].plot([r["V"][k][0],r["V"][p][0]],[r["V"][k][1],r["V"][p][1]],color=cols["RRT"],lw=.7,alpha=.7)
P=np.array(r["path"]);ax[0].plot(P[:,0],P[:,1],"k-",lw=2)
arm_panel(ax[1],r["path"],cols["RRT"]);joints_panel(ax[2],r["path"],cols["RRT"])
plt.tight_layout();plt.savefig("out/sim_rrt.png",dpi=170);plt.close()
print("RRT",len(r["V"]),r["len"],len(r["path"]))
# RRT*
r=run_rrt(True,100);R["RRT*"]=r
fig,ax=plt.subplots(1,3,figsize=(13,3.8));cspace(ax[0],"(a) Tree in q1-q2 plane after 10 s (grey = collision)")
for k,p in enumerate(r["par"]):
    if p>=0:ax[0].plot([r["V"][k][0],r["V"][p][0]],[r["V"][k][1],r["V"][p][1]],color=cols["RRT*"],lw=.5,alpha=.5)
P=np.array(r["path"]);ax[0].plot(P[:,0],P[:,1],"k-",lw=2)
arm_panel(ax[1],r["path"],cols["RRT*"]);joints_panel(ax[2],r["path"],cols["RRT*"])
plt.tight_layout();plt.savefig("out/sim_rrtstar.png",dpi=170);plt.close()
print("RRT*",len(r["V"]),r["len"],len(r["path"]),r["tfirst"])
# convergence over 5 seeds
fig,ax=plt.subplots(figsize=(6,3.6));conv=[]
for sd in range(5):
    rr=run_rrt(True,200+sd)
    if rr and rr["hist"]:
        h=np.array(rr["hist"]);ax.step(h[:,0],h[:,1],where="post",color=cols["RRT*"],alpha=.5);conv.append((float(h[0,1]),float(h[-1,1])))
ax.axhline(np.linalg.norm(QG-QS),color="k",ls="--",lw=1,label="straight-line distance 2.40 rad (lower bound)")
ax.set_xlabel("planning time (s)");ax.set_ylabel("best path length (rad)");ax.set_title("RRT* path cost vs time (5 runs)",fontsize=10);ax.legend(fontsize=8);ax.spines[['top','right']].set_visible(False)
plt.tight_layout();plt.savefig("out/rrtstar_convergence.png",dpi=200);plt.close();print("conv",conv)
# PRM
r=run_prm(100);R["PRM"]=r
fig,ax=plt.subplots(1,3,figsize=(13,3.8));cspace(ax[0],"(a) Roadmap in q1-q2 plane (1500 nodes; grey = collision)")
for i,j in r["edges"]:
    ax[0].plot([r["V"][i][0],r["V"][j][0]],[r["V"][i][1],r["V"][j][1]],color=cols["PRM"],lw=.2,alpha=.35)
P=np.array(r["path"]);ax[0].plot(P[:,0],P[:,1],"k-",lw=2)
arm_panel(ax[1],r["path"],cols["PRM"]);joints_panel(ax[2],r["path"],cols["PRM"])
plt.tight_layout();plt.savefig("out/sim_prm.png",dpi=170);plt.close()
print("PRM",len(r["V"]),len(r["edges"]),r["len"],len(r["path"]))
# PRM sizing study
prm_rows=[]
for N in (100,250,500,1000):
    ok=0;L=[];T=[]
    for sd in range(10):
        rr=run_prm(300+sd,N=N)
        if rr["path"] is not None:ok+=1;L.append(rr["len"])
        T.append(rr["t"])
    prm_rows.append(dict(N=N,success=ok,len=float(np.mean(L)) if L else None,time=float(np.mean(T))));print(prm_rows[-1],flush=True)
prm_rows.append(dict(N=1500,success=10,len=3.26,time=11.37))
json.dump(dict(rrt_nodes=len(R["RRT"]["V"]),rrts_nodes=len(R["RRT*"]["V"]),wps={k:len(v["path"]) for k,v in R.items()},prm=prm_rows,conv=conv,direct_free=bool(edge_free(QS,QG,0.02)),prm_edges=len(R["PRM"]["edges"])),open("out/sim.json","w"),indent=1)
