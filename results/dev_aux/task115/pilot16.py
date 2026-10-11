"""Separate frozen four-game16ply pilot. Never invokes evolution or auto-expands."""
import argparse,hashlib,importlib.util,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'results/dev_aux/task109'))
import adapter

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
GAME=load('short104_pilot16',ROOT/'results/dev_aux/task104/short_game.py')
PROFILES=({'P':208,'N':73,'B':901,'R':149,'Q':397,'K':0},{'P':208,'N':701,'B':89,'R':997,'Q':131,'K':0})
CAP=16;SECONDS=120

def execute(factory,output,stop,clock=time.monotonic,scope='REAL_QUALIFIED_MATURE'):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    started=clock();deadline=started+SECONDS;rows=[];physical=0
    journal=adapter.Journal(output/'events.jsonl')
    try:
        for profile,weights in enumerate(PROFILES):
            for color in (True,False):
                adapter.guard(deadline,stop,clock);engine=None
                ctx=dict(opening_seed=41001,random_seed=42001,agent_color=color,phase='pilot',name=f'pilot16-p{profile}-c{int(color)}')
                try:
                    engine=factory(deadline)
                    game=adapter.play_game(engine,weights,ctx,deadline,output/'variant.ini',journal,GAME.opening,GAME.score,stop,clock,cap=CAP)
                    physical+=1
                finally:
                    if engine:engine.close()
                adapter.guard(deadline,stop,clock)
                rows.append(dict(profile=profile,weights=weights,context=ctx,result=game,reward=game['reward']))
                adapter.atomic_json(output/'pilot.json',dict(complete=len(rows)==4,scope=scope,rows=rows))
        pairs=[]
        for color in (True,False):
            pair=[r for r in rows if r['context']['agent_color']==color]
            a,b=pair
            diverged=next((i for i,(x,y) in enumerate(zip(a['result']['actions'],b['result']['actions'])) if x!=y),None)
            pairs.append(dict(agent_color=color,reward_difference=b['reward']-a['reward'],first_action_difference_ply=diverged,
                              profile_scores=[a['result']['score'],b['result']['score']]))
        behavior=any(p['first_action_difference_ply'] is not None for p in pairs)
        reward_signal=any(p['reward_difference']!=0 for p in pairs)
        classification=('BEHAVIOR_AND_REWARD_SIGNAL' if reward_signal and behavior else
                        'BEHAVIOR_WITHOUT_REWARD_SIGNAL' if behavior else
                        'NO_OBSERVED_BEHAVIOR_SIGNAL')
        if reward_signal and not behavior:raise ValueError('reward differs without paired deterministic trajectory divergence')
        result=dict(status='FOUR_GAME_PILOT_COMPLETE',scope=scope,cap=CAP,limit_seconds=SECONDS,physical_completed_games=physical,accepted_games=len(rows),
                    pairs=pairs,paired_reward_signal=reward_signal,paired_behavior_signal=behavior,signal_classification=classification,
                    opposite_color_reward_directions=pairs[0]['reward_difference']*pairs[1]['reward_difference']<0,
                    wall_seconds=clock()-started,mature_training_calls=0,learned_updates=0,automatic_expansion=False,learning_failure=False,
                    note='Observed profile signal is a pilot screening observation, not statistical proof, human-ratio recovery or permission to auto-expand. Setup/leaf probes/search/journal/cleanup included; qualification separately reported by CLI.')
    except BaseException as err:
        result=dict(status='INTERRUPTED',scope=scope,cap=CAP,limit_seconds=SECONDS,error=type(err).__name__+': '+str(err),physical_completed_games=physical,
                    accepted_games=len(rows),wall_seconds=clock()-started,mature_training_calls=0,learned_updates=0,automatic_expansion=False,learning_failure=False)
    finally:journal.close()
    adapter.atomic_json(output/'status.json',result);return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--qualification',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();stop=lambda:adapter.stop_check(ROOT);stop()
    output=args.output.resolve();allowed=(ROOT/'results/dev_aux').resolve()
    if output==allowed or not output.is_relative_to(allowed):raise ValueError('fresh auxiliary output subdirectory required')
    started=time.monotonic()
    # This entry accepts the already verified Fairy qualification schema only.
    # A Yane executable cannot be relabeled/reused through this Chess UCI route.
    try:binary,digest,q=adapter.validated_entry(args.binary,args.qualification)
    except (OSError,ValueError,RuntimeError,KeyError) as err:
        output.mkdir(parents=True,exist_ok=False)
        result=dict(status='BLOCKED_BEFORE_LAUNCH',error=type(err).__name__+': '+str(err),mature_games_executed=0,learning_failure=False)
        adapter.atomic_json(output/'status.json',result);print(json.dumps(result));return 3
    qualification_seconds=time.monotonic()-started
    def factory(deadline):
        adapter.guard(deadline,stop)
        if hashlib.sha256(binary.read_bytes()).hexdigest()!=digest:raise RuntimeError('qualified binary changed')
        engine=adapter.UCI(binary,ROOT,deadline,stop);engine.backend='QUALIFIED_FAIRY_BINARY:'+digest;return engine
    result=execute(factory,output,stop)
    result.update(binary_sha256=digest,qualification_seconds=qualification_seconds)
    adapter.atomic_json(output/'status.json',result);print(json.dumps(result));return 0 if result['status']=='FOUR_GAME_PILOT_COMPLETE' else 3
if __name__=='__main__':sys.exit(main())