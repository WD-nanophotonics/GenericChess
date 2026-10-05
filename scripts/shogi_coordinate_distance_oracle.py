"""Independent coordinate reverse BFS; no compiled prefix or frontier helper."""
from collections import Counter,deque
MODES=('P','L','N','S','G','B','R','TB','TR')
STEPS={'P':((0,1),),'N':((-1,2),(1,2)),
 'S':((0,1),(-1,1),(1,1),(-1,-1),(1,-1)),
 'G':((0,1),(-1,1),(1,1),(-1,0),(1,0),(0,-1)),
 'TB':((0,1),(0,-1),(-1,0),(1,0)),
 'TR':((-1,-1),(-1,1),(1,-1),(1,1))}
RAYS={'L':((0,1),),'B':((-1,-1),(-1,1),(1,-1),(1,1)),
 'R':((0,-1),(0,1),(-1,0),(1,0)),
 'TB':((-1,-1),(-1,1),(1,-1),(1,1)),
 'TR':((0,-1),(0,1),(-1,0),(1,0))}
PROMOTED={'P':'G','L':'G','N':'G','S':'G','B':'TB','R':'TR'}

def neighbors(mode,source,blocker,owner):
    sign=1 if owner==0 else -1;x,y=source%9,source//9
    for dx,dy in STEPS.get(mode,()):
        u,v=x+sign*dx,y+sign*dy
        if 0<=u<9 and 0<=v<9 and v*9+u!=blocker:yield v*9+u
    for dx,dy in RAYS.get(mode,()):
        u,v=x+sign*dx,y+sign*dy
        while 0<=u<9 and 0<=v<9:
            if v*9+u==blocker:break
            yield v*9+u;u+=sign*dx;v+=sign*dy

def variants(mode,source,target,owner):
    rank=lambda s:s//9 if owner==0 else 8-s//9
    promotion=mode in PROMOTED and (rank(source)>=6 or rank(target)>=6)
    forced=mode in ('P','L') and rank(target)==8 or mode=='N' and rank(target)>=7
    if not forced:yield mode
    if promotion:yield PROMOTED[mode]

def coordinate_histograms(checkpoint=lambda:None):
    totals={mode:Counter() for mode in MODES};zeros={mode:0 for mode in MODES}
    index={mode:i for i,mode in enumerate(MODES)}
    for blocker in range(81):
        checkpoint();reverse=[[] for _ in range(81*len(MODES))]
        for mode in MODES:
            for source in range(81):
                if source==blocker:continue
                parent=index[mode]*81+source
                for target in neighbors(mode,source,blocker,0):
                    for current in variants(mode,source,target,0):reverse[index[current]*81+target].append(parent)
        for target in range(81):
            if target==blocker:continue
            distances=[-1]*len(reverse);queue=deque()
            for i in range(len(MODES)):
                node=i*81+target;distances[node]=0;queue.append(node)
            while queue:
                child=queue.popleft();distance=distances[child]+1
                for parent in reverse[child]:
                    if distances[parent]<0:distances[parent]=distance;queue.append(parent)
            for mode in MODES:
                offset=index[mode]*81
                for source in range(81):
                    if source in (blocker,target):continue
                    distance=distances[offset+source]
                    if distance<0:zeros[mode]+=1
                    else:totals[mode][distance]+=1
        yield blocker,{mode:dict(histogram=dict(sorted(totals[mode].items())),unreachable=zeros[mode]) for mode in MODES}
