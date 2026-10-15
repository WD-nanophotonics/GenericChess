"""Paired fixed-state cost/coverage of a price-independent proof trigger."""
import ast,json,random,time
from pathlib import Path
from dataclasses import asdict
from scripts.generic_proof_native_study import mod
from scripts.generic_proof_rnb_bridge import compile_rnb,from_actor,actor_state,uci
from scripts.generic_proof_player import ProofMaterialPlayer
from scripts.generic_win_proof_pn import prove_win_pn
from generic_chess.core.position import count_entities
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action


def run():
    out=Path('results/dev_aux/task1771');out.mkdir(exist_ok=False);p=Path('results/dev_aux/task1763');plan=json.loads((p/'plan.json').read_text());games=[json.loads(x) for x in (p/'run/games.jsonl').read_text().splitlines()];c=compile_rnb();by={False:[],True:[]};seen=set()
    families={f['family']:f for f in plan['families']}
    for row_index,row in enumerate(games):
        s=from_actor(c,families[row['family']]['roots'][row['color']])
        for ply,step in enumerate(row['trajectory']):
            identity=repr(s)
            if identity not in seen:
                seen.add(identity);by[count_entities(s.position)<=4].append((row_index,ply,s))
            a=next(a for a in legal_actions(s,c) if uci(a)==step['decision']['action']);s=apply_action(s,a,c)
    rng=random.Random(20261015546);selected=[]
    for small in (False,True):rng.shuffle(by[small]);selected+=by[small][:32]
    assert len(selected)==64
    (out/'plan.json').write_text(json.dumps(dict(source='1763 exposed paid states,32each <=4/>4entities, no price/WDL selection',seed=20261015546,cases=[dict(row=i,ply=j) for i,j,_ in selected],nodes=4096,seconds=1.,total_seconds=180.,trigger='count_entities(board+hands)<=4; existing verified strategy always continues',purpose='Cost/coverage diagnostic, not new WDL/learning validation'),indent=2))
    D=mod('TRIGGER_DRIVER54','results/dev_aux/task1720/driver.py');tree=ast.parse(Path('scripts/generic_proof_native_study.py').read_text(encoding='utf-8-sig'));fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run');cls=next(n for n in fn.body if isinstance(n,ast.ClassDef) and n.name=='TimedDriver');env=dict(D=D,time=time);exec(compile(ast.Module(body=[cls],type_ignores=[]),'timed_driver_class','exec'),env)
    plan.update(seconds_cap=180,max_go=300);d=env['TimedDriver'](plan,out/'run');records=[];start=time.perf_counter()
    try:
        d.start_engine()
        def normal(state,nodes,seconds,cancel):
            move,used=d.choose_timed(actor_state(state),[720]*4,nodes,seconds)
            return next(a for a in legal_actions(state,c) if uci(a)==move),used
        with (out/'calls.jsonl').open('x') as log:
            for i,(row,ply,s) in enumerate(selected):
                arms=['PLAIN','PN_ALL','PN_SMALL'];arms=arms[i%3:]+arms[:i%3]
                for arm in arms:
                    d.guard();player=ProofMaterialPlayer(c,None,normal_search=normal,proof_enabled=arm!='PLAIN',proof_search=prove_win_pn,proof_trigger=(lambda state:count_entities(state.position)<=4) if arm=='PN_SMALL' else None)
                    result=player.choose(s,max_nodes=4096,seconds=1.,cancel=lambda:time.monotonic()>=d.deadline)
                    record=dict(row=row,ply=ply,arm=arm,entities=count_entities(s.position),decision={**asdict(result),'action':uci(result.action) if result.action else None})
                    assert result.action in legal_actions(s,c);records.append(record);log.write(json.dumps(record)+'\n');log.flush()
    finally:d.close()
    summary={}
    for arm in ['PLAIN','PN_ALL','PN_SMALL']:
        rows=[r for r in records if r['arm']==arm];summary[arm]=dict(calls=len(rows),seconds=sum(r['decision']['seconds'] for r in rows),proofs=sum(r['decision']['source']=='PROOF' for r in rows),proof_nodes=sum(r['decision']['proof_nodes'] for r in rows),native_nodes=sum(r['decision']['search_nodes'] for r in rows))
    result=dict(status='COMPLETE' if len(records)==192 else 'PARTIAL',seconds=time.perf_counter()-start,actual_native_go=d.queries,summary=summary)
    (out/'result.json').write_text(json.dumps(result,indent=2));print(result)


if __name__=='__main__':run()
