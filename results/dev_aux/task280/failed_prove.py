import json,time,hashlib,itertools
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task280';T=json.loads((R/'results/dev_aux/task258/tree.json').read_bytes());start=time.monotonic();lo=32;hi=8192;bound=0;branchchecks=0;terminals=0;rows=[]
for root in T['roots']:
 actions=[]
 for a in root['actions']:
  successes=[];goals=[]
  for br in a['branches']:
   assert 'terminal' not in br,'No immediate/d2terminal required here';base=br['leaf2'];assert 'vector' in base;win=False;counts=[]
   for child in br['children']:
    ld=child['leaf']
    if 'terminal' in ld:
     assert ld['terminal']==99999997 and ld['goal']==100;win=True;terminals+=1
    else:
     vv=ld['vector'];delta=[x-y for x,y in zip(vv,base['vector'])];assert all(v>=0 for v in delta) and sum(delta) in (0,1),'Requiresno promotion/ownmaterialchanges';assert ld['goal']==sum(vv);counts.append(ld['goal']);minimum=sum(v*(lo if v>=0 else hi) for v in vv);maximum=sum(v*(hi if v>=0 else lo) for v in vv);bound=max(bound,abs(minimum),abs(maximum))
   # Nonterminalthirdmaterial isbase+0oronepositiveenemyprice: everypositiveprice maximizer getsmaxunitcount, regardlessvictimtype.
   assert counts or win;goals.append(100 if win else max(counts));successes.append(int(win));branchchecks+=1
  actions.append(dict(move=a['move'],replies=len(successes),mate_probability=str(Fraction(sum(successes),len(successes))),universal_third_max_quantity=str(Fraction(sum(goals),len(goals)))))
 mate_actions=[a for a in actions if Fraction(a['mate_probability'])>0]
 rows.append(dict(root=root['root'],actions=actions,positive_mate_actions=mate_actions))
# Ifunique positiveprobability action, its M*prob remainder gap dominatesforall5pricebox.
proved=[]
for root in rows:
 aa=root['positive_mate_actions']
 if len(aa)==1:
  a=aa[0];gap=99999997*Fraction(a['mate_probability'])-2*bound;assert gap>0;proved.append(dict(root=root['root'],unique_mean_D3_root_action=a['move'],mate_probability=a['mate_probability'],quantity_forall_prices=a['universal_third_max_quantity'],lower_score_gap=str(gap)))
out=dict(complete=True,price_domain=dict(PNBRQ=[lo,hi],K=0),max_absolute_nonterminal_material=bound,checked_Black_branches=branchchecks,actual_terminal_child_count=terminals,proved_roots=proved,no_terminal_root_ids=[r['root'] for r in rows if not r['positive_mate_actions']],seconds=time.monotonic()-start,source_sha256=hashlib.sha256((R/'results/dev_aux/task258/tree.json').read_bytes()).hexdigest(),premise='Actualfrozen235698leafboards independentlyaudited260. D3White maximizespositivepurematerial/terminal1e8-ply, Blackuniformmean. Root0/1/2 exactlyonepositiveprobabilitymateaction, allotheractionszero. Third nonterminalchanges0/oneenemycapture withpositiveprice and no promotions; quantityofanymaterialmaxizeristhereforeidentical. Entirecontinuousboxalgebra, not625point extrapolation.',conclusion='Allpricevectors intorrealPNBRQ32..8192(K0) have same3White rootchoices andsame finitequantity/mateby3goals; includesnewsemanticnormalizedandcommonscales. Thisshorttaskcannotidentifyhumanratios. BlackrootnoMATE/meanquantity maystillvary; otherhorizons/opponentmodel/48plymaturegamesnotcovered. No generalChess impossibility.',rows=rows)
(O/'proof.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2))
