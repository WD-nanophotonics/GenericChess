import collections,json,math
from pathlib import Path
from evolution import Experiment,select,weights,pilot_informative
checks=[]
def check(name,x):
 if not x:raise AssertionError(name)
 checks.append(name)
check("incumbent tie",select([1,1,1])==0)
check("plus tie priority",select([0,2,2])==1)
check("minus improvement",select([0,-1,2])==2)
check("all tied pilot halt",not pilot_informative([dict(reward=0)]*4))
check("color asymmetry not profile signal",not pilot_informative([dict(reward=x) for x in (1,0,1,0)]))
check("paired profile difference",pilot_informative([dict(reward=x) for x in (1,0,2,0)]))
def game(w,context,deadline):
 # Synthetic oracle rewards N; neither real game nor human material target.
 r=w["N"]/208
 w["P"]=-1;context["phase"]="mutated-private-copy"
 return dict(reward=r,backend="SYNTHETIC_CONTROLLER_TEST_ONLY")
e=Experiment(game,clock=lambda:0);result=e.run()
check("exact480calls",len(e.calls)==480 and e.completed)
check("exact phase counts",collections.Counter(c["context"]["phase"] for c in e.calls)=={"train":432,"heldout":48})
check("callback cannot mutate frozen scale",all(c["weights"]["P"]==208 for c in e.calls))
train={c["context"]["opening_seed"] for c in e.calls if c["context"]["phase"]=="train"};held={c["context"]["opening_seed"] for c in e.calls if c["context"]["phase"]=="heldout"}
check("heldout disjoint",not train&held)
for run in e.runs:
 check("sixgenerations"+str(run["seed"]),len(run["iterations"])==6)
 for i in run["iterations"]:
  check("nondecreasing synthetic selection"+str((run["seed"],i["generation"])),i["means"][i["selected"]]>=i["means"][0])
 for generation in range(6):
  arms=[[c["context"] for c in e.calls if c["context"]["name"].startswith(f"s{run['seed']}-g{generation}-a{a}-")] for a in range(3)]
  signatures=[[(x["opening_seed"],x["random_seed"],x["agent_color"]) for x in arm] for arm in arms]
  check("identical paired seeds"+str((run["seed"],generation)),signatures[0]==signatures[1]==signatures[2])
try:e.run();raise AssertionError("rerun accepted")
except RuntimeError:checks.append("no automatic rerun")
clock_values=iter([0,900]);f=Experiment(game,clock=lambda:next(clock_values))
try:f.run();raise AssertionError("fuse accepted")
except TimeoutError:check("fuse before game",len(f.calls)==0)
def stopped():raise RuntimeError("user stop")
f=Experiment(game,clock=lambda:0,stop=stopped)
try:f.run();raise AssertionError("stop accepted")
except RuntimeError:check("stop before game",len(f.calls)==0)
for invalid in ([float("nan"),0,0],[0,float("inf"),0]):
 try:select(invalid);raise AssertionError("invalid accepted")
 except ValueError:checks.append("reject nonfinite reward")
for invalid_pilot in ([dict(reward=float("nan"))]*4,[dict(reward=None)]*4,[{}]*4):
 try:pilot_informative(invalid_pilot);raise AssertionError("invalid pilot accepted")
 except ValueError:checks.append("reject invalid pilot before signal decision")
shared={"reward":1,"metadata":{"nodes":1}}
def mutable_game(w,context,deadline):return shared
m=Experiment(mutable_game,clock=lambda:0);m.call(weights([0,0,0,0]),1,2,True,"train","fixture")
shared["metadata"]["nodes"]=99
check("record owns callback result",m.calls[0]["result"]["metadata"]["nodes"]==1)
output=dict(complete=True,checks=checks,check_count=len(checks),phase_counts={"train":432,"heldout":48},real_engine_games=0,scope="Pure controller oracle checks, not learning or mature-search evidence.")
Path(__file__).with_name("test_result.json").write_bytes((json.dumps(output,indent=2)+"\n").encode());print(json.dumps(output))
