"""Replay64actual ablationroots and compare to sameexposedroot diagnostics."""
import json,hashlib,re,time
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task141';O.mkdir(exist_ok=True);D=json.loads((R/'results/dev_aux/task139/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task139/result.json').read_bytes());OLD=json.loads((R/'results/dev_aux/task133/result.json').read_bytes());AB=json.loads((R/'results/dev_aux/task134/audit.json').read_bytes());assert X['complete'] and len(X['rows'])==64
def info(meta):
 lines=meta['uci_info'];report=[l for l in lines if l.startswith('info depth ')]
 assert report
 row=report[-1].split();v=dict(kind='cp',value=int(row[row.index('cp')+1])) if 'cp' in row else dict(kind='mate',value=int(row[row.index('mate')+1]))
 return v
nodes=[];pairs=[];baseline_same=0;regret=[]
for profile,w in D['profiles'].items():
 for root in D['roots']:
  b=chess.Board(root['fen'])
  for text in root['history']:
   m=chess.Move.from_uci(text);assert m in b.legal_moves;b.push(m)
  assert b.fen()==root['expected_fen'] and b.is_valid()
  pair=[next(x for x in X['rows'] if x['profile']==profile and x['root_id']==root['id'] and x['alignment']==align) for align in (0,1)]
  for align,x in enumerate(pair):
   m=chess.Move.from_uci(x['move']);assert m in b.legal_moves
   assert x['weights']==w and x['metadata']['full_history']==root['history'] and x['metadata']['root_fen']==root['fen'];assert x['metadata']['backend'].endswith(X['binary_sha256']) and x['metadata']['nodes_limit']==1024
   ack=x['table_ack'];assert ack['alignment']==align
   mg=(126,781,825,1276,2538);eg=(208,854,915,1380,2682)
   expected={str(i+1):[w[k],w[k]] if align else [mg[i],eg[i]] for i,k in enumerate('PNBRQ')};assert ack['prices']==expected
   assert len(x['leaf_probes'])==5
   for p in x['leaf_probes']:assert abs(p['measured_white_pawns']-w[p['type']]/208)<=.011
   assert isinstance(x['metadata']['reported_nodes'],int) and x['metadata']['reported_nodes']>0
   nodes.append(x['metadata']['reported_nodes'])
  pairs.append(dict(profile=profile,root=root['id'],actions=[x['move'] for x in pair],changed=pair[0]['move']!=pair[1]['move'],values=[info(x['metadata']) for x in pair],depths=[x['metadata']['reported_depth'] for x in pair]))
  if root['scope']=='exposedfirstdivergence':
   oldid=root['id'][4:];prev=next(x for x in OLD['rows'] if x['root_id']==oldid and x['arm']==profile)
   baseline_same+=pair[0]['move']==prev['mature']
   scores={}
   for a in prev['actions']:
    vv=[r['value'] for r in a['replies']];scores[a['move']]=min(vv)
   best=max(scores.values());regret.append(dict(profile=profile,root=oldid,shallow_minimax_regret=[best-scores[x['move']] for x in pair],scope='Same2plylabel horizon; notstrength/wdl ornecessarySEEproof'))
result=dict(complete=True,source_result_sha256=hashlib.sha256((R/'results/dev_aux/task139/result.json').read_bytes()).hexdigest(),actual_searches=64,leaf_probes=320,table_acks=64,total_reported_nodes=sum(nodes),reported_nodes_min=min(nodes),reported_nodes_max=max(nodes),matched_action_changes=sum(x['changed'] for x in pairs),original_cold_baseline_action_matches=baseline_same,original_cold_baseline_pairs=16,pairs=pairs,shallow_label_overlay=regret,scope='Actualjointsearch-table intervention isolateswithinnewbinarypricefamily underconfigurednodebudget. Deeperselectivebehavior andfixedmarginsremain, nolearningbenefitclaim. Old/newcompiler comparisonseparate.')
(O/'audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('complete','actual_searches','leaf_probes','table_acks','total_reported_nodes','reported_nodes_min','reported_nodes_max','matched_action_changes','original_cold_baseline_action_matches')},indent=2))
