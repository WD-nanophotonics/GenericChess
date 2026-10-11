"""Prospective finite generated states: primitive and Core terminal scope."""
import argparse,hashlib,json,random,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import full_q_refresh_comparison as p
from scripts.research_record import record_value,write_record
from scripts.native_core_availability import NativeCoreAvailability
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core import terminal,search_runtime

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);b=Path(ap.parse_args().output);b.mkdir(parents=True,exist_ok=True);assert not (b/'declaration.json').exists()
 seeds=[1041,1042,1043,1044];limit=24;children=8
 files=['generic_chess/_native/native_module.c','generic_chess/_native/native_semantic_runtime.c','scripts/native_core_availability.py',__file__]
 write_record(b/'declaration.json',dict(question='Does lazy availability preserve boolean and original Core terminal priority on new finite generated histories?',seeds=seeds,plies=limit,children_per_root=children,policy='First eight lexical legal children, plus root. Stop at natural terminal or300second whole-producer cost limit; retain censored cases, no rerun. No independent holdout restored by new seeds; adaptive structural development.',decision='Any mismatch rejects this scope; zero mismatches permits bounded cost comparison, not full generated-domain correctness or move-quality claim.',source_hashes={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files},binary_sha256=hashlib.sha256(Path('generic_chess/_native_core.cp312-win_amd64.pyd').read_bytes()).hexdigest()))
 rows=[];samples=[];start=time.perf_counter();censored=False
 for seed in seeds:
  p.rr.stopped();g=p.generate_game(p.GeneratorConfig(seed=seed,board_size=8,setup_preset='bilateral_random',allow_hybrid=True));src=p.compile_legacy_ruleset_for_semantic_execution(g.ruleset);c=p.SearchMetadataAdapter(ir=src.ir,_legacy_compiled=src._legacy_compiled,support=src.support);session=p.GameSession(c);query=NativeCoreAvailability(c);engine=semantic_engine_for(c);rng=random.Random(seed+17000)
  for ply in range(limit):
   p.rr.stopped()
   if time.perf_counter()-start>300:censored=True;break
   rt=SearchPathRuntime(session.state,c,history_witnesses=session._search_history_witnesses);saved=p.runtime_state(rt);actions=sorted(rt.legal_actions(),key=repr);sample=len(samples);samples.append(dict(seed=seed,ply=ply,state=record_value(session.state),witnesses=record_value(session._search_history_witnesses)))
   def check(label):
    before=p.runtime_state(rt);expected=engine.has_legal_action(rt.position);actual=query(rt);a=terminal.terminal_from_search_runtime(rt);query.install()
    try:z=search_runtime.terminal_from_search_runtime(rt)
    finally:query.restore()
    assert expected==actual and a==z,(seed,ply,label,expected,actual,a,z)
    assert p.runtime_state(rt)==before
    rows.append(dict(sample=sample,label=label,available=actual,terminal=record_value(a),imports=query.imports,queries=query.queries,fallbacks=query.fallbacks))
   check('root')
   for i,action in enumerate(actions[:children]):
    rt.push(action)
    try:check('child'+str(i))
    finally:rt.pop()
   rt.assert_balanced();assert p.runtime_state(rt)==saved
   if session.result.status.value != "ongoing" or not actions:break
   session.submit(rng.choice(actions))
  write_record(b/'samples.json',samples);write_record(b/'result.json',dict(complete=False,censored=censored,rows=rows,seconds=time.perf_counter()-start));print(seed,len(samples),len(rows),censored,flush=True)
  if censored:break
 write_record(b/'result.json',dict(complete=True,censored=censored,rows=rows,seconds=time.perf_counter()-start))
if __name__=='__main__':main()
