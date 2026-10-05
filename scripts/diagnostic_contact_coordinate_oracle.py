"""Independent diagnostic coordinates; no compiled/event/occupancy imports."""
from collections import deque
def moves(mode,source,target,blocker,owner,*,capture):
    # Reflect inputs once; no compiled geometry tables shared with constructor.
    if owner:
        for dest in moves(mode,89-source,89-target,89-blocker,0,capture=capture):yield 89-dest
        return
    sf,sr=source%9,source//9
    if mode in ('R','C'):
        for df,dr in ((1,0),(-1,0),(0,1),(0,-1)):
            f,r=sf+df,sr+dr;occupied=0
            while 0<=f<9 and 0<=r<10:
                dest=f+9*r
                if dest==blocker:
                    if mode=='R':break
                    occupied+=1
                elif dest==target:
                    if capture and ((mode=='R' and occupied==0) or (mode=='C' and occupied==1)):yield dest
                    if mode=='R':break
                    occupied+=1
                elif not capture and occupied==0:yield dest
                if occupied>=2:break
                f+=df;r+=dr
        return
    if mode=='H':offsets=[(df,dr) for df in (-2,-1,1,2) for dr in (-2,-1,1,2) if abs(df)+abs(dr)==3]
    elif mode=='E':
        if sr>=5:return
        offsets=[(df,dr) for df in (-2,2) for dr in (-2,2)]
    elif mode=='A':
        if not (3<=sf<=5 and sr<=2):return
        offsets=[(df,dr) for df in (-1,1) for dr in (-1,1)]
    elif mode=='S':offsets=[(0,1)]+([(1,0),(-1,0)] if sr>=5 else [])
    else:raise ValueError('explicit ordinary diagnostic mode required')
    for df,dr in offsets:
        f,r=sf+df,sr+dr
        if not (0<=f<9 and 0<=r<10):continue
        dest=f+9*r
        if mode=='E' and r>=5:continue
        if mode=='A' and not (3<=f<=5 and r<=2):continue
        if mode in ('H','E'):
            leg=(df//2,dr//2) if mode=='E' else ((1 if df>0 else -1,0) if abs(df)==2 else (0,1 if dr>0 else -1))
            eye=(sf+leg[0])+9*(sr+leg[1])
            if eye in (target,blocker):continue
        if capture and dest==target:yield dest
        if not capture and dest not in (target,blocker):yield dest

def screen_possible(target,blocker):
    tf,tr=target%9,target//9;bf,br=blocker%9,blocker//9
    return (tr==br and 0<bf<8) or (tf==bf and 0<br<9)

def distance(mode,source,target,blocker,owner=0):
    if mode=='C' and not screen_possible(target,blocker):return 0
    if owner:return distance(mode,89-source,89-target,89-blocker,0)
    sf,sr=source%9,source//9;tf,tr=target%9,target//9
    if mode=='A' and not (3<=sf<=5 and sr<=2 and 3<=tf<=5 and tr<=2):return 0
    if mode=='E' and (sr>=5 or tr>=5):return 0
    if mode=='S' and tr<sr:return 0
    queue=deque([(source,0)]);seen={source}
    while queue:
        here,cost=queue.popleft()
        if any(True for _ in moves(mode,here,target,blocker,0,capture=True)):return cost+1
        for nxt in moves(mode,here,target,blocker,0,capture=False):
            if nxt not in seen:seen.add(nxt);queue.append((nxt,cost+1))
    return 0
