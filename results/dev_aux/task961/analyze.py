from pathlib import Path
import json,collections,re
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task961';O.mkdir(exist_ok=False);old=[json.loads(l) for l in (R/'results/dev_aux/task954/games.jsonl').open()];gg=[json.loads(l) for l in (R/'results/dev_aux/task958/games.jsonl').open()];table={(g['weights'][5],g['opponent'],g['root']['seed'],g['color']):g for g in old};controls=0;query_controls=0
for g in gg:
 if g['mode'] not in ['II','LL']:continue
 h=table[g['weights'][5],g['opponent'],g['root']['seed'],g['color']];assert g['actions']==h['actions'] and g['termination']==h['termination'] and g['final_sfen']==h['final_sfen'];assert len(g['queries'])==len(h['queries'])
 def score(q):
  ls=[l for l in q['lines'] if re.search(r' score (cp|mate) ',l)];l=ls[-1];m=re.search(r'\bdepth (\d+).*? score (cp|mate) (-?\d+)',l);return m.groups(),q['bestmove'],l.split(' pv ',1)[1] if ' pv ' in l else None,'lowerbound' in l,'upperbound' in l
 for q,z in zip(g['queries'],h['queries']):assert score(q)==score(z);query_controls+=1
 controls+=1
assert controls==144
rows=[]
def st(g):
 t=g['termination'];return 'C' if t['kind'].startswith('cap') else 'D' if t['winner'] is None else 'W' if t['winner']==g['color'] else 'L'
def v(g):return 1 if st(g)=='W' else -1 if st(g)=='L' else 0
for op in ['unit_search','uniform_random']:
 modes={}
 for mode in ['II','IL','LI','LL']:
  a=[g for g in gg if g['opponent']==op and g['mode']==mode];c=collections.Counter(map(st,a));modes[mode]=dict(N=len(a),counts=dict(c),J24=str(F(sum(map(v,a)),len(a))))
 vals={k:F(z['J24']) for k,z in modes.items()};rows.append(dict(opponent=op,modes=modes,leaf_only=str(vals['IL']-vals['II']),native_only=str(vals['LI']-vals['II']),joint=str(vals['LL']-vals['II']),interaction=str(vals['LL']-vals['LI']-vals['IL']+vals['II'])));print(rows[-1])
r=dict(status='PASS_ALL144_DUAL_CONSISTENT_CONTROLS_AND_FACTORIAL_RETURN',equivalent_games=controls,equivalent_queries=query_controls,rows=rows,new_go=0,scope='Actions/terminal/finalSFEN/depth/scorebounds/bestmove/printedPV exactmatchedtoqualified954, no timed-equivalenceclaim. Nativeaxis includescached/SEE/otherconsumers, notpureSEE. Full288scope959audited. Exposedfreshroot diagnostic, nofit/newholdoutclaim.');(O/'result.json').write_text(json.dumps(r,indent=2));print('EQUIVALENT',controls,query_controls)
