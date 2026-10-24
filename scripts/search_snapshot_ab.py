"""Counterbalanced exact-map A/B; old method explicit, never a data-capsule exec."""
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone
import time,json,argparse,hashlib
from scripts.search_performance_study import limits,gate,stamp
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.verify_leaper_delayed_capture import load
from scripts.research_record import record_value
from generic_chess.core.search_runtime import RuntimeCountsSnapshot,_identity_sort_key
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.audit_instrumentation import TimingAuditRecorder
from tools.local_agent.common import write_json

# Exact prechange implementation, copied as reviewed ordinary benchmark code.
def legacy_items(self):
    values={}
    if self.parent is None:values.update(dict(self.root_items))
    else:
        values.update(dict(self.parent.items()))
        if self.key is not None:
            if self.count:values[self.key]=self.count
            else:values.pop(self.key,None)
    return tuple(sorted(values.items(),key=lambda item:_identity_sort_key(item[0])))

def run(d):
    plan=load(d/'plan.json');reg=load(d/'snapshot-ab-plan.json');inp=load(d/'inputs.json');out=d/'snapshot-ab.jsonl'
    if out.exists():raise ValueError('retain existing measurements, no implicit rerun')
    current_items=RuntimeCountsSnapshot.items;start=stamp();tick=time.perf_counter();proc=time.process_time()
    prepared=[]
    for case in inp['cases']:
        gate(plan);t=time.perf_counter();c=L.compile_rule(L.ruleset_from_dict(case['rule']));s=replay(c,case['record']);player=AlphaBetaPlayer(c,use_disk_cache=False);prepared.append((case,c,s,player,time.perf_counter()-t))
    queries=0
    for rep in range(4):
      for qdepth in (0,4):
       for case,c,s,player,setup in prepared:
        for mode in ('depth','nodes','wall'):
         order=('old','new')if rep in (0,3)else('new','old')
         pair=[]
         for arm in order:
            gate(plan);player.reset();remaining=(datetime.fromisoformat(plan['deadline'])-datetime.now(timezone.utc)).total_seconds();assert remaining>65
            lim=SearchLimits(max_depth=6 if mode=='depth'else 64,max_nodes=65536 if mode!='wall'else None,max_time_seconds=60 if mode!='wall'else 8,quiescence_max_depth=qdepth)
            before=record_value(s.to_record());started=stamp();cpu=time.process_time();t=time.perf_counter()
            with patch.object(RuntimeCountsSnapshot,'items',legacy_items if arm=='old'else current_items):dec=player.choose_action(s,lim)
            row=dict(case=case['key'],input_sha256=case['input_sha256'],rep=rep,qdepth=qdepth,mode=mode,arm=arm,order=list(order),limits=record_value(lim),started_at=started,ended_at=stamp(),wall_seconds=time.perf_counter()-t,cpu_seconds=time.process_time()-cpu,setup_seconds=setup,decision=record_value(dec),legal=dec.action in s.legal_actions()if dec.action else s.result.status.value!='ongoing',state_unchanged=before==record_value(s.to_record()))
            assert row['legal']and row['state_unchanged'];pair.append(row)
            with out.open('a',encoding='utf-8')as f:f.write(json.dumps(row)+'\n')
            queries+=1;print(rep,qdepth,case['key'],mode,arm,'D',dec.completed_depth,'work',dec.nodes+dec.qnodes,'sec',round(row['wall_seconds'],3),flush=True)
         x,y=pair;dx,dy=x['decision'],y['decision']
         # Algorithm preserves all tree/order semantics. Only time-bound work may differ.
         if mode!='wall'and dx['termination_reason']!='time_limit'and dy['termination_reason']!='time_limit':
            assert (dx['score'],dx['completed_depth'],dx['nodes'],dx['qnodes'],dx['principal_variation'])==(dy['score'],dy['completed_depth'],dy['nodes'],dy['qnodes'],dy['principal_variation']), 'exact reconstruction changed deterministic search'
    write_json(d/'snapshot-ab-receipt.json',dict(started_at=start,ended_at=stamp(),wall_seconds=time.perf_counter()-tick,cpu_seconds=time.process_time()-proc,queries=queries,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',type=Path,required=True);v=a.parse_args();run(v.directory)
