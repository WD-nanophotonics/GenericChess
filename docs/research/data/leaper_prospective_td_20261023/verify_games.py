"""Shared-Core replay of all prior-control slots and supplied literal PVs."""
import sys,json,gzip,hashlib,copy,time,random,math,argparse
from pathlib import Path
from collections import Counter
from fractions import Fraction as F
sys.path.insert(0,str(Path.cwd()))
from scripts.leaper_design import compile_rule,ruleset_from_dict,GameSession,record_value,state_sha
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import empty_mobility
from generic_chess.ai.evaluation.analyzer import profile_movement_atoms
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,MATE
from scripts.leaper_microgames import role_stop_requested
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def replay(c,r):return GameSession.replay(c,deserialize_game_record(json.dumps(r)))
def match(s,r):
 aa=[a for a in s.legal_actions()if action_to_dict(a)==r];assert len(aa)==1;return aa[0]
def contrasts(cfg,inputs,games):
 lookup={(g['world'],g['prefix'],g['role'],g['price']):g['utility']for g in games};frames=[(w['world'],p,r)for w in inputs['worlds']for p in range(cfg.get('prefixes',4))for r in(0,1)];names=cfg.get('candidate_names',['unit','mobility','Static','B2C1','unit_TD','mobility_TD']);rows=[]
 for price in names:
  sums=[0,0];diff={other:[0,0]for other in names};outcomes=Counter();byrole={r:[0,0]for r in(0,1)};byworld={w['world']:[0,0]for w in inputs['worlds']}
  for w,p,r in frames:
   u=lookup.get((w,p,r,price),[-1,1]);outcomes[str(u)]+=1
   for j in(0,1):sums[j]+=u[j];byrole[r][j]+=u[j];byworld[w][j]+=u[j]
   for other in names:
    v=lookup.get((w,p,r,other),[-1,1])
    for j in(0,1):diff[other][j]+=0 if price==other else u[j]-v[1-j]
  rows.append(dict(price=price,denominator=len(frames),mean=[str(F(x,len(frames)))for x in sums],difference={k:[str(F(x,len(frames)))for x in v]for k,v in diff.items()},role_means={str(k):[str(F(x,len(frames)//2))for x in v]for k,v in byrole.items()},world_means={str(k):[str(F(x,2*cfg.get('prefixes',4)))for x in v]for k,v in byworld.items()},outcomes=dict(outcomes)))
 return rows
def main():
 ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--baseline',type=Path);ap.add_argument('--combined-analysis',type=Path);a=ap.parse_args();t=time.perf_counter();counts=Counter()
 if a.source.is_dir():
  cfg=json.loads((a.source/'config.json').read_bytes());inputs=json.loads((a.source/'inputs.json').read_bytes());summary=json.loads((a.source/'summary.json').read_bytes());games=[json.loads(l)for l in(a.source/'games.jsonl').read_text(encoding='utf8').splitlines()];qs=[json.loads(l)for l in(a.source/'queries.jsonl').read_text(encoding='utf8').splitlines()]
  for g in games:g['query_examples']=[qs[i]for i in g['query_ids']];g['query_count']=len(g['query_ids']);g['nodes']=sum(q['receipt']['nodes']for q in g['query_examples']);g['depth_histogram']=dict(Counter(str(q['receipt']['completed_depth'])for q in g['query_examples']))
  packet=None
 else:
  packet=json.loads(gzip.decompress(a.source.read_bytes()));assert packet['format']=='AUX-ABC-prospective-batch-v1';cfg=packet['config'];inputs=packet['inputs'];summary=packet['summary'];games=packet['games']
  for g in games:g['final_record']=packet['records'][g['record']]
 assert not cfg.get('pilot',False);worlds={w['world']:w for w in inputs['worlds']};compiled={w:compile_rule(ruleset_from_dict(x['rule']))for w,x in worlds.items()};opening={(o['world'],o['prefix']):o for o in inputs['openings']}
 for wid,c in compiled.items():
  assert c.ruleset_fingerprint==worlds[wid]['fingerprint'];n=c.board_size;totals={name:sum(len(empty_mobility(n,0,Square(x,y),profile_movement_atoms(c,name)))for x in range(n)for y in range(n))for name in 'ABC'};assert worlds[wid]['priors']['mobility']==[1,totals['B']/totals['A'],totals['C']/totals['A'],0,0,0]
  st=build_ruleset_profile(c,EvaluationConfig()).board_value_by_type;assert worlds[wid]['priors']['Static']==[1,st['B']/st['A'],st['C']/st['A'],0,0,0];assert worlds[wid]['priors']['unit']==[1,1,1,0,0,0]and worlds[wid]['priors']['B2C1']==[1,2,1,0,0,0]
 for o in opening.values():
  domain=cfg.get('prefix_domain','AUX-ABC-onebatch-eval-v1');seed=int.from_bytes(hashlib.sha256(f'{domain}:{cfg["seed"]}:{o["world"]}:{o["prefix"]}'.encode()).digest()[:8],'big');assert seed==o['seed'];rng=random.Random(seed);s=GameSession(compiled[o['world']])
  for step in range(8):
   if s.state.terminal_status.is_terminal:break
   aa=s.legal_actions();s.submit(aa[rng.randrange(len(aa))])
  assert canon(record_value(s.to_record()))==canon(o['record'])and state_sha(s.state)==o['id']and s.state.ply_count==o['ply']and s.state.terminal_status.is_terminal==o['terminal'];counts['openings']+=1
 expected={(w,p,r,name)for w in worlds for p in range(cfg.get('prefixes',4))for r in(0,1)for name in cfg.get('candidate_names',['unit','mobility','Static','B2C1','unit_TD','mobility_TD'])};seen=set();decoded={}
 for g in games:
  if time.perf_counter()-t>900 or role_stop_requested():raise RuntimeError('REPLAY_CAP_OR_STOP')
  key=(g['world'],g['prefix'],g['role'],g['price']);assert key in expected and key not in seen;seen.add(key);o=opening[key[:2]];c=compiled[g['world']];record=g['final_record'];rk=canon(record)
  if rk not in decoded:decoded[rk]=replay(c,record)
  final=decoded[rk];assert record['actions'][:len(o['record']['actions'])]==o['record']['actions']and g['opening_id']==o['id'];v=FixedScaleSessionEnv(final,unit_type='A').terminal();utility=[-1,1]if v is None or g['censor']else[v*(1 if g['role']==0 else-1)]*2;assert utility==g['utility'];counts['terminal_prefix_views']+=o['terminal'];counts['slots']+=1;counts['reported_queries']+=g['query_count'];counts['reported_nodes']+=g['nodes'];assert sum(g['depth_histogram'].values())==g['query_count']
  counts['served_actions']+=len(record['actions'])-len(o['record']['actions'])
  if 'query_examples'in g:
   s=replay(c,o['record']);assert len(g['query_examples'])==g['query_count']
   for q in g['query_examples']:
    assert q['id']==state_sha(s.state)and q['actor']==s.state.position.side_to_move and q['ply']==s.state.ply_count;r=q['receipt'];counts['checked_queries']+=1
    if r['action']is None:assert g['censor']and not r['complete'];continue
    pv=copy.copy(s)
    for action in r['pv']:pv.submit(match(pv,action));counts['PV_edges']+=1
    env=FixedScaleSessionEnv(pv,unit_type='A');v=env.terminal();weights=worlds[g['world']]['priors'][g['price']if q['actor']==g['role']else'mobility']
    if v is None:assert tuple(r['pv_phi'])==env.features()and math.isclose(Model(weights).raw(env.features()),r['value'],abs_tol=1e-10)and not r['pv_terminal']and len(r['pv'])==r['completed_depth']
    else:assert r['pv_terminal']and r['value']==MATE*v
    assert r['pv'][0]==r['action']
    if not g['censor']:assert r['complete']and r['completed_depth']==4
    if r['complete']and r['completed_depth']==4:s.submit(match(s,r['action']))
   assert canon(record_value(s.to_record()))==canon(record)
 assert len(expected)==cfg['planned']and len(seen)+len(summary['missing'])==len(expected);assert counts['reported_queries']==summary['queries']and counts['reported_nodes']==summary['nodes'];rows=contrasts(cfg,inputs,games)
 if packet:assert rows==packet['analysis']
 if a.baseline:
  assert a.combined_analysis;old=json.loads(gzip.decompress(a.baseline.read_bytes()));combined=json.loads(a.combined_analysis.read_bytes());assert hashlib.sha256(a.baseline.read_bytes()).hexdigest()==combined['reused_packet_sha256'];oldopen={(o['world'],o['prefix']):o for o in old['inputs']['openings']};assert set(oldopen)==set(opening)
  for key,o in opening.items():assert o['id']==oldopen[key]['id']and canon(o['record'])==canon(oldopen[key]['initial_record'])
  oldgames=[]
  for g in old['games']:
   z=dict(g,price='unit'if(g['B'],g['C'])==(1,1)else'B2C1',final_record=old['records'][g['record']]);c=compiled[g['world']];final=replay(c,z['final_record']);v=FixedScaleSessionEnv(final,unit_type='A').terminal();assert g['utility']==[v*(1 if g['role']==0 else-1)]*2;oldgames.append(z)
  cc=dict(cfg,candidate_names=['unit','mobility','Static','B2C1','unit_TD','mobility_TD']);assert contrasts(cc,inputs,games+oldgames)==combined['analysis'];lookup={(g['world'],g['prefix'],g['role'],g['price']):g for g in games+oldgames};matches={}
  for name in cc['candidate_names']:
   pairs=[(g,lookup[g['world'],g['prefix'],g['role'],'mobility'])for g in games+oldgames if g['price']==name];matches[name]=dict(identical_complete_records=sum(g['final_record']==u['final_record']for g,u in pairs),same_outcome=sum(g['utility']==u['utility']for g,u in pairs),outcome_difference=dict(Counter(str([g['utility'][0]-u['utility'][0],g['utility'][1]-u['utility'][1]])for g,u in pairs)))
  assert matches==combined['matches_vs_mobility'];counts['reused_baseline_slots']=len(oldgames)
 result=dict(status='PASS',seconds=time.perf_counter()-t,counts=counts,unique_records=len(decoded),analysis=rows,scope='Shared-Core legality/full outcomes/all prefix draws and supplied PVs only;no independent CPU certification or exact WDL tree proof. Full private and selected public PV scopes differ.');a.output.write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in result.items()if k!='analysis'}),flush=True)
if __name__=='__main__':main()
