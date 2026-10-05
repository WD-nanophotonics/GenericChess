"""Independent8x8 reverse-coordinate closure, with target-aware native Pawn."""
from collections import Counter,deque
MODES=('P','N','B','R','Q')
KNIGHT=((-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1))
DIAGONALS=((-1,-1),(-1,1),(1,-1),(1,1))
ORTHOGONALS=((-1,0),(1,0),(0,-1),(0,1))

def moves(mode,source,blocker,target,*,capture=False):
    x,y=source%8,source//8
    if mode=='P':
        if capture:
            for dx in (-1,1):
                u,v=x+dx,y+1
                if 0<=u<8 and v<8 and v*8+u==target:yield target
        else:
            for step in ((1,2) if y==1 else (1,)):
                if y+step>=8:continue
                path=[(y+k)*8+x for k in range(1,step+1)]
                if all(q not in (blocker,target) for q in path):yield path[-1]
        return
    if mode=='N':
        for dx,dy in KNIGHT:
            u,v=x+dx,y+dy
            if 0<=u<8 and 0<=v<8 and v*8+u!=blocker:
                if capture and v*8+u==target or not capture and v*8+u!=target:yield v*8+u
        return
    rays=DIAGONALS if mode=='B' else ORTHOGONALS if mode=='R' else DIAGONALS+ORTHOGONALS
    for dx,dy in rays:
        u,v=x+dx,y+dy
        while 0<=u<8 and 0<=v<8:
            square=v*8+u
            if square==blocker:break
            if square==target:
                if capture:yield target
                break
            if not capture:yield square
            u+=dx;v+=dy

def coordinate_histograms(checkpoint=lambda:None):
    index={mode:i for i,mode in enumerate(MODES)};totals={mode:Counter() for mode in MODES};zeros={mode:0 for mode in MODES}
    for blocker in range(64):
        checkpoint()
        for target in range(64):
            if target==blocker:continue
            reverse=[[] for _ in range(320)];distances=[-1]*320;queue=deque()
            for mode in MODES:
                for source in range(64):
                    if source in (blocker,target):continue
                    parent=index[mode]*64+source
                    if any(moves(mode,source,blocker,target,capture=True)):distances[parent]=1;queue.append(parent)
                    for destination in moves(mode,source,blocker,target):
                        currents=('N','B','R','Q') if mode=='P' and destination//8==7 else (mode,)
                        for current in currents:reverse[index[current]*64+destination].append(parent)
            while queue:
                child=queue.popleft()
                for parent in reverse[child]:
                    if distances[parent]<0:distances[parent]=distances[child]+1;queue.append(parent)
            for mode in MODES:
                for source in range(64):
                    if source in (blocker,target):continue
                    distance=distances[index[mode]*64+source]
                    if distance<0:zeros[mode]+=1
                    else:totals[mode][distance]+=1
        yield blocker,{mode:dict(histogram=dict(sorted(totals[mode].items())),unreachable=zeros[mode]) for mode in MODES}
