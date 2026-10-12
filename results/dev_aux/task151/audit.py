"""Finalactualdeployment/rootqualification/oracle audit; preserveallnegative results."""
import json,hashlib,random,math,sys,importlib.util,statistics
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task151';O.mkdir(exist_ok=True)
s=importlib.util.spec_from_file_location('score151',R/'results/dev_aux/task104/short_game.py');G=importlib.util.module_from_spec(s);s.loader.exec_module(G)
D=json.loads((R/'results/dev_aux/task150/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task150/games.json').read_bytes());assert X['complete'] and len(X['calls'])==192
counts=dict(games=0,moves=0,searches=0,probes=0,acks=0);nodes=[]
for c in X['calls']:
 x=c['context'];r=c['result'];w=c['weights'];assert w==D['profiles'][x['profile_index']]['weights'];assert r['opening']==D['roots'][str(x['opening_seed'])]
 b=chess.Board()
 for text in r['opening']:assert chess.Move.from_uci(text) in b.legal_moves;b.push_uci(text)
 rng=random.Random(x['random_seed']);si=0
 for text in r['actions']:
  assert not b.is_game_over(claim_draw=False);m=chess.Move.from_uci(text);assert m in b.legal_moves
  if b.turn==x['agent_color']:
   meta=r['search_records'][si];assert meta['full_history']==[m.uci() for m in b.move_stack] and meta['backend'].endswith(D['binary_sha256']) and meta['nodes_limit']==1024;nodes.append(meta['reported_nodes']);assert isinstance(nodes[-1],int) and nodes[-1]>0;si+=1;counts['searches']+=1
  else:assert m==rng.choice(sorted(b.legal_moves,key=lambda x:x.uci()))
  b.push(m);counts['moves']+=1
 assert si==len(r['search_records']) and b.fen()==r['final_fen'];assert r['score']==G.score(b,x['agent_color'],len(r['actions']),16) and r['reward']==r['score']['reward'];counts['games']+=1
 assert len(r['candidate_leaf_probes'])==5
 for p in r['candidate_leaf_probes']:assert math.isfinite(p['measured_white_pawns']) and abs(p['measured_white_pawns']-w[p['type']]/208)<=.011;counts['probes']+=1
 f=r['search_table_ack'].split();assert int(f[4])==x['mode'];assert {int(t.split(':')[0]):tuple(map(int,t.split(':')[1:])) for t in f[5:]}=={i+1:(w[k],w[k]) for i,k in enumerate('PNBRQ')};counts['acks']+=1
# Actualrootqualification afterorderingchange.
Q=json.loads((R/'results/dev_aux/task149/result.json').read_bytes());QD=json.loads((R/'results/dev_aux/task149/declaration.json').read_bytes());assert Q['complete'] and len(Q['rows'])==96
for row in Q['rows']:
 root=next(x for x in QD['roots'] if x['id']==row['root_id']);b=chess.Board(root['fen'])
 for text in root['history']:b.push_uci(text)
 assert b.fen()==root['expected_fen'];assert chess.Move.from_uci(row['move']) in b.legal_moves;assert row['metadata']['full_history']==root['history'];assert row['table_ack']['alignment']==row['alignment']
 assert row['table_ack']['prices']=={str(i+1):[row['weights'][k],row['weights'][k]] for i,k in enumerate('PNBRQ')}
 for p in row['leaf_probes']:assert abs(p['measured_white_pawns']-row['weights'][p['type']]/208)<=.011
# Independentrecursive witnessreplay, provingdeclinehas legalnontargetescape at eachnode.
oracle_checks=[]
for task in ('145','148'):
 data=json.loads((R/f'results/dev_aux/task{task}/result.json').read_bytes());assert data['complete'];w=data['witness']['candidate'];root=chess.Board(data['witness']['fen']);color=root.turn
 def material(b):return sum(w[chess.piece_symbol(t).upper()]*(len(b.pieces(t,color))-len(b.pieces(t,not color))) for t in range(1,6))
 base=material(root);root.push_uci(data['witness']['move']);target=root.peek().to_square;count=0
 def replay(b,node):
  nonlocal_dummy=None
  assert b.fen()==node['fen'];legal=list(b.legal_moves);target_moves=sorted(m.uci() for m in legal if m.to_square==target and b.is_capture(m))
  assert target_moves==[x['move'] for x in node['legal_target_captures']]
  non_target=[m.uci() for m in legal if not (m.to_square==target and b.is_capture(m))]
  assert non_target,'Decline must have an actuallegalnontargetaction in thiswitness'
  value=material(b)-base;assert value==node['decline_value'];choices=[value];n=1
  for c in node['legal_target_captures']:
   b.push_uci(c['move']);v,z=replay(b,c['child']);b.pop();assert v==c['value'];choices.append(v);n+=z
  expected=(max if b.turn==color else min)(choices);assert expected==node['value'];return expected,n
 v,n=replay(root,data['oracle_tree']);assert v==data['oracle_value']
 for mode in data['rows']:
  for answer in mode['answers']:assert answer['candidate_target_oracle_ge']==(v>=answer['threshold'])
 oracle_checks.append(dict(task=task,value=v,nodes=n,all_declines_have_legal_nontarget_action=True))
summary=json.loads((R/'results/dev_aux/task150/summary.json').read_bytes());groups={}
for align in (0,1):
 rows=[r for r in summary['profiles'] if r['training_alignment']==align];assert len(rows)==3
 groups[str(align)]=dict(endpoint_count=3,mean_original_deployment_delta=statistics.mean(r['paired_original_mean'] for r in rows),mean_bounded_deployment_delta=statistics.mean(r['paired_bounded_mean'] for r in rows),mate_wins_mode1=sum(r['mate_wins']['1'] for r in rows),mate_wins_mode3=sum(r['mate_wins']['3'] for r in rows))
out=dict(complete=True,deployment_counts=counts,reported_nodes_total=sum(nodes),reported_nodes_min=min(nodes),reported_nodes_max=max(nodes),root_qualification_searches=96,root_qualification_probes=480,oracle_witness_checks=oracle_checks,training_origin_deployment_summaries=groups,scope='Actualtrace/qualification replay and restrictedlegalexchange arithmetic. Deploymentfixedweights doesnotdecidefuturemode3training efficacy; source/kernelremainapproximate.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
