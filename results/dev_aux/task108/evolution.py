"""Frozen cheap experiment scheduler; the game callback owns real engine qualification."""
import math,random,time,copy
TYPES=("N","B","R","Q")
SEEDS=(103,104,105)
LOW,HIGH=math.log(.25),math.log(16)

def weights(theta):
    if len(theta)!=4 or any(not math.isfinite(x) for x in theta):raise ValueError("bad log weights")
    return {"P":208,"K":0,**{k:round(208*math.exp(x)) for k,x in zip(TYPES,theta)}}

def starts(seed):
    rng=random.Random(seed)
    return [rng.uniform(math.log(.35),math.log(12)) for _ in TYPES]

def select(means):
    if len(means)!=3 or any(not math.isfinite(x) for x in means):raise ValueError("invalid means")
    # Incumbent wins ties; plus has deterministic priority over minus ties.
    best=max(range(3),key=lambda i:means[i])
    return best if means[best]>means[0] else 0

def pilot_informative(records):
    if len(records)!=4:raise ValueError("four pilot games required")
    if any(not isinstance(r.get("reward"),(int,float)) or not math.isfinite(r["reward"]) for r in records):raise ValueError("invalid pilot reward")
    # Compare the two profiles within the same color, rather than color asymmetry.
    return any(records[color]["reward"]!=records[2+color]["reward"] for color in range(2))

class Experiment:
    def __init__(self,game,clock=time.monotonic,stop=lambda:None,budget_seconds=900):
        self.game=game;self.clock=clock;self.stop=stop;self.deadline=clock()+budget_seconds
        self.calls=[];self.runs=[];self.completed=False
    def call(self,w,opening_seed,random_seed,color,phase,name):
        self.stop()
        if self.clock()>=self.deadline:raise TimeoutError("frozen stage wall fuse")
        context=dict(opening_seed=opening_seed,random_seed=random_seed,agent_color=color,phase=phase,name=name)
        # Never pass live controller parameter dictionaries to a callback.
        result=self.game(dict(w),dict(context),self.deadline)
        reward=result["reward"]
        if not isinstance(reward,(int,float)) or not math.isfinite(reward):raise ValueError("nonfinite game reward")
        self.calls.append(dict(context=context,weights=dict(w),result=copy.deepcopy(result)))
        return reward
    def run(self,pilot_records=None):
        if self.calls or self.runs:raise RuntimeError("controller cannot auto-rerun")
        if pilot_records is None:return dict(completed=False,status="PILOT_REQUIRED",calls=[])
        if not pilot_informative(pilot_records):return dict(completed=False,status="NO_PAIRED_PILOT_SIGNAL",calls=[])
        for seed in SEEDS:
            initial=starts(seed);theta=initial[:];rng=random.Random(seed+900000)
            run=dict(seed=seed,initial_weights=weights(initial),iterations=[],heldout=[]);self.runs.append(run)
            for generation in range(6):
                delta=[rng.choice((-1,1)) for _ in TYPES]
                candidates=[theta[:]]+[[max(LOW,min(HIGH,t+sign*.4*d)) for t,d in zip(theta,delta)] for sign in (1,-1)]
                before=weights(theta);means=[];groups=[]
                for arm,candidate in enumerate(candidates):
                    rewards=[]
                    for opening_index in range(4):
                        opening_seed=61000+generation*4+opening_index
                        random_seed=71000+generation*4+opening_index
                        for color in (True,False):
                            name=f"s{seed}-g{generation}-a{arm}-o{opening_index}-c{int(color)}"
                            rewards.append(self.call(weights(candidate),opening_seed,random_seed,color,"train",name))
                    means.append(sum(rewards)/8);groups.append(rewards)
                chosen=select(means);theta=candidates[chosen][:]
                run["iterations"].append(dict(generation=generation,before=before,delta=delta,means=means,rewards=groups,selected=chosen,after=weights(theta)))
            run["final_weights"]=weights(theta)
            # Final was frozen before any heldout callback and never changes afterward.
            for opening_index in range(4):
                for arm,w in (("initial",run["initial_weights"]),("final",run["final_weights"])):
                    for color in (True,False):
                        context=f"s{seed}-heldout-a{arm}-o{opening_index}-c{int(color)}"
                        reward=self.call(w,81000+opening_index,91000+opening_index,color,"heldout",context)
                        run["heldout"].append(dict(arm=arm,opening_index=opening_index,color=color,reward=reward))
        self.completed=True
        return dict(completed=True,runs=self.runs,calls=self.calls,
                    scope="Callback-defined execution; synthetic testing cannot establish mature learning.")
