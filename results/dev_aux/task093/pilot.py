import json,time
from pathlib import Path
from harness import *
B=Path(__file__).resolve().parent;out={"complete":False,"scope":"Cost/terminal pilot only, not learning or heldout","games":[]};write(B/"pilot-declaration.json",{"opening_seeds":[771,772],"weights0":{"P":208,"K":0,"N":73,"B":901,"R":149,"Q":397},"weights1":{"P":208,"K":0,"N":701,"B":89,"R":997,"Q":131},"nodes":128,"cap":64,"depth":4,"freeze":"No cap extension or outcome-label use"});start=time.perf_counter()
for seed in (771,772):
 g=play({"P":208,"K":0,"N":73,"B":901,"R":149,"Q":397},{"P":208,"K":0,"N":701,"B":89,"R":997,"Q":131},make_opening(seed),nodes=128,cap=64,depth=4);out["games"].append(g);write(B/"pilot.json",out);print(seed,g["status"],len(g["actions"]),g["wall_seconds"],g["error"],flush=True)
out["complete"]=True;out["wall_seconds"]=time.perf_counter()-start;write(B/"pilot.json",out)
