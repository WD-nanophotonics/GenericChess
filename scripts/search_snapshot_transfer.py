"""Transfer the one exact-map change to two existing standard benchmark positions."""
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
import json,time,hashlib,argparse
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.search_performance_study import gate,stamp,digest
from scripts.search_snapshot_ab import legacy_items
from generic_chess.ai.benchmark.suite import DEFAULT_SUITE,build_position
from generic_chess.generation.generator import generate_game
from generic_chess.core.search_runtime import RuntimeCountsSnapshot
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from tools.local_agent.common import write_json

def prepare(d):
    plan=json.loads((d/'plan.json').read_text());gate(plan);cases=[]
    for key in ['classic6_ply16','classic8_ply24']:
        spec=next(x for x in DEFAULT_SUITE if x.key==key)
        game=generate_game(spec.config);cc,opening=build_position(spec)
        assert cc.ruleset_fingerprint==game.compiled_ruleset.ruleset_fingerprint
        s=L.GameSession(cc)
        for a in opening:s.submit(a)
        rr=L.ruleset_to_dict(game.ruleset,include_metadata=True);rec=L.record_value(s.to_record())
        cases.append(dict(key=key,execution_api='compile_ruleset',rule=rr,record=rec,input_sha256=digest([rr,rec]),side=s.state.position.side_to_move,ply=s.state.ply_count,result=L.record_value(s.result),source='existing DEFAULT_SUITE/'+key,expected_WDL=None))
    write_json(d/'transfer-inputs.json',{'cases':cases,'prepared_at':stamp(),'rule_semantics_not_simplified':True});print('prepared transfer',[(x['key'],x['ply'],x['result']['status'])for x in cases],flush=True)

def run(d):
    plan=json.loads((d/'plan.json').read_text());inp=json.loads((d/'transfer-inputs.json').read_text());out=d/'transfer.jsonl'
    if out.exists():raise ValueError('new transfer only, no implicit rerun')
    current=RuntimeCountsSnapshot.items;started=stamp();tick=time.perf_counter();cpu=time.process_time();n=0
    for case in inp['cases']:
      gate(plan);c=compile_ruleset(L.ruleset_from_dict(case['rule']));s=replay(c,case['record']);player=AlphaBetaPlayer(c,use_disk_cache=False)
      for rep in range(2):
       for mode in ['depth','nodes','wall']:
        pair=[]
        for arm in (['old','new']if rep==0 else['new','old']):
            gate(plan);player.reset();lim=SearchLimits(max_depth=3 if mode=='depth'else 64,max_nodes=65536 if mode!='wall'else None,max_time_seconds=60 if mode!='wall'else 8,quiescence_max_depth=4);start=stamp();t=time.perf_counter();cp=time.process_time()
            with patch.object(RuntimeCountsSnapshot,'items',legacy_items if arm=='old'else current):dec=player.choose_action(s,lim)
            row=dict(case=case['key'],input_sha256=case['input_sha256'],rep=rep,mode=mode,arm=arm,started_at=start,ended_at=stamp(),wall_seconds=time.perf_counter()-t,cpu_seconds=time.process_time()-cp,limits=L.record_value(lim),decision=L.record_value(dec),legal=dec.action in s.legal_actions()if dec.action else s.result.status.value!='ongoing')
            assert row['legal'];pair.append(row)
            with out.open('a',encoding='utf-8')as f:f.write(json.dumps(row)+'\n')
            n+=1;print(case['key'],rep,mode,arm,'D',dec.completed_depth,'work',dec.nodes+dec.qnodes,'sec',round(row['wall_seconds'],3),flush=True)
        a,b=[x['decision']for x in pair]
        if mode!='wall'and a['termination_reason']!='time_limit'and b['termination_reason']!='time_limit':assert(a['score'],a['completed_depth'],a['nodes'],a['qnodes'],a['principal_variation'])==(b['score'],b['completed_depth'],b['nodes'],b['qnodes'],b['principal_variation'])
    write_json(d/'transfer-receipt.json',dict(started_at=started,ended_at=stamp(),wall_seconds=time.perf_counter()-tick,cpu_seconds=time.process_time()-cpu,queries=n,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('phase',choices=['prepare','run']);a.add_argument('--directory',type=Path,required=True);v=a.parse_args();(prepare if v.phase=='prepare'else run)(v.directory)
