"""Qualification-gated short pilot and frozen evolution. No resume/retry loop."""
import argparse, importlib.util, json, sys, time
from pathlib import Path
from adapter import UCI, Journal, atomic_json, guard, play_game, stop_check, validated_entry
ROOT=Path(__file__).resolve().parents[3]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module
GAME=load("aux_short104",ROOT/"results/dev_aux/task104/short_game.py")
EVOLUTION=load("aux_evolution108",ROOT/"results/dev_aux/task108/evolution.py")
PROFILES=({"P":208,"N":73,"B":901,"R":149,"Q":397,"K":0},
          {"P":208,"N":701,"B":89,"R":997,"Q":131,"K":0})

def execute(factory,output,stop,clock=time.monotonic,scope="REAL_QUALIFIED_MATURE",
            pilot_seconds=900,stage_seconds=900):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    journal=Journal(output/"events.jsonl");pilot=[];controller=None
    status="STARTED";completed={"pilot":0,"train":0,"heldout":0};started=clock();pilot_deadline=started+pilot_seconds
    try:
        def game(weights,context,deadline):
            guard(deadline,stop,clock);engine=None
            try:
                engine=factory(deadline)
                result=play_game(engine,weights,context,deadline,output/"variant.ini",journal,
                                 GAME.opening,GAME.score,stop,clock)
                completed[context["phase"]]+=1
            finally:
                if engine:engine.close()
            guard(deadline,stop,clock)
            return result
        for profile,weights in enumerate(PROFILES):
            for color in (True,False):
                context=dict(opening_seed=41001,random_seed=42001,agent_color=color,phase="pilot",
                             name="pilot-p"+str(profile)+"-c"+str(int(color)))
                result=game(weights,context,pilot_deadline)
                pilot.append(dict(profile=profile,context=context,weights=weights,result=result,reward=result["reward"]))
                atomic_json(output/"pilot.json",dict(complete=len(pilot)==4,rows=pilot,scope=scope))
        signal=EVOLUTION.pilot_informative(pilot)
        # Pilot total includes fresh-process setup/cleanup and game/journal cost.
        cost=clock()-started;projection=cost/4*480
        if not signal:status="NO_PAIRED_PILOT_SIGNAL"
        elif projection>stage_seconds:status="PROJECTED_COST_EXCEEDS_FROZEN_BUDGET"
        else:
            # Training900s begins only after pilot; pilot cost is additional and separately reported.
            controller=EVOLUTION.Experiment(game,clock=clock,stop=stop,budget_seconds=stage_seconds)
            result=controller.run(pilot)
            atomic_json(output/"controller.json",result)
            status="COMPLETE" if result["completed"] else result.get("status","INCOMPLETE")
        result=dict(status=status,scope=scope,pilot_games_completed=completed["pilot"],pilot_rows_accepted=len(pilot),completed_games_by_phase=dict(completed),
                    training_callbacks_accepted=0 if controller is None else len(controller.calls),training_games_completed=completed["train"]+completed["heldout"],
                    pilot_seconds=cost,projected_480_game_seconds=projection,
                    total_wall_seconds=clock()-started,learning_failure=False,
                    note="Scope and completed records determine scientific claims; this status never certifies human-value recovery.")
        atomic_json(output/"status.json",result);return result
    except BaseException as error:
        result=dict(status="INTERRUPTED",scope=scope,error=type(error).__name__+": "+str(error),
                    pilot_games_completed=completed["pilot"],pilot_rows_accepted=len(pilot),completed_games_by_phase=dict(completed),training_callbacks_accepted=0 if controller is None else len(controller.calls),training_games_completed=completed["train"]+completed["heldout"],
                    total_wall_seconds=clock()-started,learning_failure=False,
                    partial_evidence="events.jsonl preserves started game, each move, completed games; no automatic resume.")
        atomic_json(output/"status.json",result)
        if controller is not None:
            atomic_json(output/"controller_partial.json",dict(completed=False,calls=controller.calls,runs=controller.runs))
        return result
    finally:journal.close()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--binary",type=Path,default=ROOT/".local_agent/material-selfplay/fairy-material.exe")
    parser.add_argument("--qualification",type=Path,default=ROOT/"results/dev_aux/task091/qualification.json")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    # Stop has precedence over qualification, and a failed entry never constructs a transport.
    stop=lambda:stop_check(ROOT)
    stop()
    allowed=(ROOT/"results/dev_aux").resolve()
    args.output=args.output.resolve()
    if args.output==allowed or not args.output.is_relative_to(allowed):
        raise ValueError("output must be a fresh DEV_AUX results subdirectory")
    try:binary,digest,evidence=validated_entry(args.binary,args.qualification)
    except (OSError,ValueError,RuntimeError,KeyError) as error:
        args.output.mkdir(parents=True,exist_ok=False)
        result=dict(status="BLOCKED_BEFORE_LAUNCH",mature_games_executed=0,learning_failure=False,
                    error=type(error).__name__+": "+str(error))
        atomic_json(args.output/"status.json",result);print(json.dumps(result));return 3
    def factory(deadline):
        # The sole writer owns this entry. Detect replacement before a new game.
        import hashlib
        guard(deadline,stop)
        if hashlib.sha256(binary.read_bytes()).hexdigest()!=digest:
            raise RuntimeError("qualified binary changed")
        engine=UCI(binary,ROOT,deadline,stop)
        engine.backend="QUALIFIED_FAIRY_BINARY:"+digest
        return engine
    result=execute(factory,args.output,stop)
    result["binary_sha256"]=digest
    atomic_json(args.output/"status.json",result)
    print(json.dumps(result));return 0 if result["status"]=="COMPLETE" else 3
if __name__=="__main__":sys.exit(main())
