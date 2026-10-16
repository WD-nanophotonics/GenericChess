"""Rank-DAG feasibility, not a production proof backend or universal solver."""
from pathlib import Path
from collections import defaultdict
import json,hashlib,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_inventory_proof_transport import execution_differences
from results.dev_aux.task2068.teacher import CanonicalTeacher
OUT=Path('results/dev_aux/task2084')
def run():
 start=time.perf_counter();p=json.loads((OUT/'plan.json').read_text());teacher=CanonicalTeacher('results/dev_aux/task2056','results/dev_aux/task2058','results/dev_aux/task2059');labels=list(teacher.rows.values());byindex={l['index']:l for l in labels};plans=json.loads(Path('results/dev_aux/task2063/run-plan.json').read_text());games=[json.loads(x)for x in Path('results/dev_aux/task2063/games.jsonl').read_text().splitlines()];moves=defaultdict(list)
 for x in Path('results/dev_aux/task2063/moves.jsonl').read_text().splitlines():r=json.loads(x);moves[r['slot']].append(r)
 cases=[];seen=set()
 for game in games:
  if game['outcome']=='UNKNOWN':continue
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(plans['roots'][game['family']]['rules']).read_text()));assert not execution_differences(teacher.reference,c)
  for step in moves[game['slot']]:
   if step['source']!='MATERIAL_SEARCH':continue
   record={**game['record'],'actions':game['record']['actions'][:step['ply']]};s=GameSession.replay(c,deserialize_game_record(json.dumps(record)));l=teacher.rows[teacher.key(actor_state(s.state))];rh=hashlib.sha256(repr(s.to_record()).encode()).hexdigest()
   if l['label']!='WIN'or max(n for _,n in s.state.repetition_counts)>1 or l['rank']>96-s.state.ply_count or rh in seen:continue
   seen.add(rh);target=s.state.position.side_to_move;root=l['index'];dag={};sizes={}
   def visit(i):
    if i in dag:return
    node=byindex[i];value={'WIN':1,'DRAW':0,'LOSS':-1}[node['label']];value=value if node['board'][-1]==target else-value;assert value==1
    if node['status']!='ongoing':assert node['rank']==0;dag[i]=[];sizes[i]=1;return
    edges=[e for e in node['actions']if e['action']==node['winning_action']]if node['board'][-1]==target else node['actions'];assert edges
    for e in edges:assert byindex[e['child']]['rank']<node['rank'];visit(e['child'])
    dag[i]=edges;sizes[i]=1+sum(sizes[e['child']]for e in edges)
   visit(root);trace=[];actualroot=s.to_record();peak=s.state.ply_count
   while s.result.status is SessionStatus.ONGOING:
    n=teacher.rows[teacher.key(actor_state(s.state))];edges=dag[n['index']];edge=edges[0]if s.state.position.side_to_move==target else max(edges,key=lambda e:(byindex[e['child']]['rank'],e['action']));actual={uci(a):a for a in s.legal_actions()}
    if s.state.position.side_to_move!=target:assert set(actual)=={e['action']for e in edges}
    s.submit(actual[edge['action']]);trace.append(edge['action']);assert max(n for _,n in s.state.repetition_counts)<=2;assert s.state.ply_count-peak<=l['rank']
    replay=GameSession.replay(c,s.to_record());assert replay.state==s.state and replay.result==s.result
   assert s.result.winner==target
   cases.append(dict(case=len(cases),source_slot=game['slot'],source_ply=step['ply'],source_proof_reason=step['proof_reason'],source_proof_nodes=step['proof_nodes'],source_proof_seconds=step['proof_seconds'],target=target,root_rank=l['rank'],remaining_ply=96-peak,DAG_nodes=len(dag),DAG_edges=sum(len(x)for x in dag.values()),expanded_tree_nodes=sizes[root],root_record=json.loads(serialize_game_record(actualroot)),longest_defense_trace=trace,actual_result=dict(status=s.result.status.value,winner=s.result.winner),final_record=json.loads(serialize_game_record(s.to_record()))))
   if len(cases)==p['max_cases']:break
  if len(cases)==p['max_cases']:break
 assert len(cases)==8
 (OUT/'cases.json').write_text(json.dumps(cases,indent=2));result=dict(status='COMPLETE_SCOPED_RANK_DAG_FEASIBILITY',cases=len(cases),actual_checkmates=len(cases),actual_trace_moves=sum(len(x['longest_defense_trace'])for x in cases),DAG_nodes=sum(x['DAG_nodes']for x in cases),DAG_edges=sum(x['DAG_edges']for x in cases),expanded_tree_nodes=sum(x['expanded_tree_nodes']for x in cases),prior_failed_PN_seconds=sum(x['source_proof_seconds']for x in cases),total_including_teacher_load_seconds=time.perf_counter()-start,scope=p['scope'],not_integrated_into_active_or_product_search=True);assert result['total_including_teacher_load_seconds']<p['seconds_cap'];(OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
