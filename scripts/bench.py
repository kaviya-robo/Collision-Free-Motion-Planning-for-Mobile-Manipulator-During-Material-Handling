import numpy as np, math, time, json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
pi=math.pi
# kinematics from robot_spec.py (metres); arm base in base_link frame
BASE=np.array([-0.092,0,0.091])
J1=np.array([.012,0,.017]);J2=np.array([0,0,.0595]);J3=np.array([.024,0,.128]);J4=np.array([.124,0,0]);EE=np.array([.126,0,0])
LIM=np.array([[-.9*pi,.9*pi],[-.57*pi,.5*pi],[-.3*pi,.44*pi],[-.57*pi,.65*pi]])
def Rz(a):c,s=math.cos(a),math.sin(a);return np.array([[c,-s,0],[s,c,0],[0,0,1]])
def Ry(a):c,s=math.cos(a),math.sin(a);return np.array([[c,0,s],[0,1,0],[-s,0,c]])
def fk(q):
    p=BASE+J1;R=Rz(q[0]);pts=[BASE,p]
    p=p+R@J2;R=R@Ry(q[1]);pts.append(p)
    p=p+R@J3;R=R@Ry(q[2]);pts.append(p)
    p=p+R@J4;R=R@Ry(q[3]);pts.append(p)
    pts.append(p+R@EE);return np.array(pts)
# obstacles: spheres (centre, radius) in front of robot; arm links = capsules radius 0.025
OBS=[(np.array([.09,0.0,.21]),.05),(np.array([.10,.12,.14]),.04),(np.array([.10,-.12,.14]),.04)]
RL=.025
def seg_sphere(a,b,c,r):
    d=b-a;t=np.clip(np.dot(c-a,d)/np.dot(d,d),0,1);return np.linalg.norm(a+t*d-c)<r+RL
def free(q):
    if np.any(q<LIM[:,0])or np.any(q>LIM[:,1]):return False
    P=fk(q)
    if np.any(P[2:,2]<0.02):return False  # keep above deck-ish / ground
    for i in range(2,len(P)-1):
        for c,r in OBS:
            if seg_sphere(P[i],P[i+1],c,r):return False
    return True
def edge_free(a,b,step=.05):
    n=max(2,int(np.linalg.norm(b-a)/step));return all(free(a+(b-a)*t) for t in np.linspace(0,1,n+1))
rng=np.random.default_rng(0)
def sample():return LIM[:,0]+rng.random(4)*(LIM[:,1]-LIM[:,0])
QS=np.array([-1.2,-.2,.6,.3]);QG=np.array([1.2,-.2,.6,.3])
assert free(QS) and free(QG),(free(QS),free(QG))
def path_len(p):return sum(np.linalg.norm(p[i+1]-p[i]) for i in range(len(p)-1))
def steer(a,b,eta):d=b-a;n=np.linalg.norm(d);return b if n<=eta else a+d*eta/n
def rrt(star,T=10.0,eta=.4,goal_bias=.1):
    t0=time.time();V=[QS];par=[-1];cost=[0.];best=None;tfirst=None
    while time.time()-t0<T:
        q=QG if rng.random()<goal_bias else sample()
        d=[np.linalg.norm(v-q) for v in V];i=int(np.argmin(d));qn=steer(V[i],q,eta)
        if not edge_free(V[i],qn):continue
        if star:
            r=min(1.5,2.0*(1+1/4)**(1/4)*(math.log(len(V)+1)/(len(V)+1))**(1/4)*1.0)
            near=[j for j,v in enumerate(V) if np.linalg.norm(v-qn)<r]
            bi,bc=i,cost[i]+np.linalg.norm(V[i]-qn)
            for j in near:
                c=cost[j]+np.linalg.norm(V[j]-qn)
                if c<bc and edge_free(V[j],qn):bi,bc=j,c
            V.append(qn);par.append(bi);cost.append(bc);k=len(V)-1
            for j in near:
                c=bc+np.linalg.norm(V[j]-qn)
                if c<cost[j] and edge_free(qn,V[j]):
                    par[j]=k;cost[j]=c
        else:
            V.append(qn);par.append(i);cost.append(cost[i]+np.linalg.norm(V[i]-qn));k=len(V)-1
        if np.linalg.norm(V[k]-QG)<1e-6 or (np.linalg.norm(V[k]-QG)<eta and edge_free(V[k],QG)):
            if np.linalg.norm(V[k]-QG)>1e-6:
                V.append(QG.copy());par.append(k);cost.append(cost[k]+np.linalg.norm(V[k]-QG));k=len(V)-1
            if tfirst is None:tfirst=time.time()-t0
            if not star:best=k;break
            if best is None or cost[k]<cost[best]:best=k
    if best is None:return None
    p=[];k=best
    while k!=-1:p.append(V[k]);k=par[k]
    return dict(path=p[::-1],tfirst=tfirst,nodes=len(V),length=path_len(p))
def prm(N=1500,k=10):
    t0=time.time();V=[QS,QG]
    while len(V)<N:
        q=sample()
        if free(q):V.append(q)
    A=np.array(V);E={i:[] for i in range(len(V))}
    for i in range(len(V)):
        d=np.linalg.norm(A-A[i],axis=1)
        for j in np.argsort(d)[1:k+1]:
            j=int(j)
            if j>i and edge_free(V[i],V[j]):
                w=d[j];E[i].append((j,w));E[j].append((i,w))
    import heapq
    D={0:0};pr={};h=[(0,0)]
    while h:
        d,u=heapq.heappop(h)
        if u==1:break
        if d>D.get(u,1e9):continue
        for v,w in E[u]:
            if d+w<D.get(v,1e9):D[v]=d+w;pr[v]=u;heapq.heappush(h,(d+w,v))
    if 1 not in pr:return None
    p=[];k=1
    while k!=0:p.append(V[k]);k=pr[k]
    p.append(V[0]);p=p[::-1]
    return dict(path=p,tfirst=time.time()-t0,nodes=len(V),length=path_len(p))
RES={"RRT":[],"RRT*":[],"PRM":[]};PATHS={}
RUNS=10
for r in range(RUNS):
    rng=np.random.default_rng(100+r)
    for name,f in [("RRT",lambda:rrt(False)),("RRT*",lambda:rrt(True,T=10.0)),("PRM",lambda:prm())]:
        t0=time.time();x=f();el=time.time()-t0
        if x is None:RES[name].append(None);print(name,r,"fail");continue
        RES[name].append(dict(time=x["tfirst"],total=el,nodes=x["nodes"],length=x["length"]))
        PATHS.setdefault(name,x["path"]);print(name,r,round(x["tfirst"],2),round(x["length"],2),x["nodes"],flush=True)
summ={}
for n,L in RES.items():
    ok=[x for x in L if x];summ[n]=dict(success=len(ok),runs=RUNS,time_mean=float(np.mean([x["time"] for x in ok])) if ok else None,time_sd=float(np.std([x["time"] for x in ok])) if ok else None,len_mean=float(np.mean([x["length"] for x in ok])) if ok else None,len_sd=float(np.std([x["length"] for x in ok])) if ok else None,nodes_mean=float(np.mean([x["nodes"] for x in ok])) if ok else None)
json.dump(summ,open("out/bench.json","w"),indent=1);print(json.dumps(summ,indent=1))
# figures
cols={"RRT":"#d95f02","RRT*":"#1b9e77","PRM":"#7570b3"}
fig,ax=plt.subplots(1,3,figsize=(11,3.4))
for a,(k,l) in zip(ax,[("time","Time to first solution (s)"),("length","Path length (rad, joint space)"),("nodes","Tree / roadmap nodes")]):
    for i,n in enumerate(RES):
        v=[x[k] for x in RES[n] if x];a.bar(i,np.mean(v),yerr=np.std(v),color=cols[n],capsize=4)
    a.set_xticks(range(3));a.set_xticklabels(list(RES));a.set_title(l,fontsize=10);a.spines[['top','right']].set_visible(False)
plt.tight_layout();plt.savefig("out/bench.png",dpi=200)
fig=plt.figure(figsize=(6,5));ax=fig.add_subplot(111,projection="3d")
for n,p in PATHS.items():
    for q in p[::max(1,len(p)//6)]:
        P=fk(q);ax.plot(P[:,0],P[:,1],P[:,2],color=cols[n],alpha=.5,lw=1.2)
    ax.plot([],[],color=cols[n],label=n)
for c,r in OBS:
    u,v=np.mgrid[0:2*pi:12j,0:pi:8j];ax.plot_wireframe(c[0]+r*np.cos(u)*np.sin(v),c[1]+r*np.sin(u)*np.sin(v),c[2]+r*np.cos(v),color="gray",lw=.4)
ax.set_xlim(-.1,.5);ax.set_ylim(-.3,.3);ax.set_zlim(0,.5);ax.set_xlabel("x (m)");ax.set_ylabel("y (m)");ax.set_zlabel("z (m)");ax.legend();ax.set_title("Planned arm motion (sample run per planner)",fontsize=10)
plt.tight_layout();plt.savefig("out/paths.png",dpi=200)
# workspace
qs=np.array([sample() for _ in range(20000)]);E=np.array([fk(q)[-1] for q in qs])
fig,ax=plt.subplots(1,2,figsize=(9,3.8))
ax[0].scatter(E[:,0],E[:,2],s=1,alpha=.3,color="#1b6ca8");ax[0].set_xlabel("x (m)");ax[0].set_ylabel("z (m)");ax[0].set_title("Reachable workspace, side view (x-z)",fontsize=10);ax[0].set_aspect("equal")
ax[1].scatter(E[:,0],E[:,1],s=1,alpha=.3,color="#1b6ca8");ax[1].set_xlabel("x (m)");ax[1].set_ylabel("y (m)");ax[1].set_title("Top view (x-y)",fontsize=10);ax[1].set_aspect("equal")
plt.tight_layout();plt.savefig("out/workspace.png",dpi=200)
json.dump(dict(reach_max=float(np.max(np.linalg.norm(E-BASE,axis=1))),zmax=float(E[:,2].max()),xmax=float(E[:,0].max())),open("out/ws.json","w"))
print(open("out/ws.json").read())
