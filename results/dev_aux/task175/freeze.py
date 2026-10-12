"""Changed objective control on identical starts/roots, no longer games."""
import json,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task175';O.mkdir(exist_ok=True)
def prepare():
 if (O/'declaration.json').exists():raise FileExistsError('frozen')
 old=json.loads((R/'results/dev_aux/task169/declaration.json').read_bytes());diag=json.loads((R/'results/dev_aux/task174/analysis.json').read_bytes());assert diag['complete']
 changes=diag['methods']['unit2ply']['finalquantity_changed']
 if changes==0:
  (O/'decision.json').write_text(json.dumps(dict(execute=False,reason='Finalquantity target changeszero recordedunit-opponent candidates; do not repeat samepath.',diagnostic_sha256=hashlib.sha256((R/'results/dev_aux/task174/analysis.json').read_bytes()).hexdigest()),indent=2),encoding='utf-8');print('No decision-changing quantity control');return
 D={**old,'task_id':'175','question':'Does direct final material quantity rather than rare mate payoff change rapid material learning?','premise':f'Newreachablefullarmy component diagnostic changes{changes}/72unit-opponent candidate selections by finalquantity. Exactrescoring doesnot supply subsequenttrajectory; performone matchedchangedobjective control, no old rewardconstantscan.','opponents':['unit2ply'],'method_order':[[503,'unit2ply'],[504,'unit2ply'],[505,'unit2ply']],'train_slots':3024,'heldout_slots':96,'total_slots':3120,'reward':'Final PNBRQ unitcountdifference/15 even when true game termination earlier. Actual termination and originalTask104 score/reward preserved separately; material-only proxy may rewarda lostmate and cannot be assumedhumanprice orWDL.','freeze':'Allthreeends globally frozen beforeANYheldout; same503/504/505initialstarts,7train/8heldgeometry andmatchedseeds asoriginal169unit-opponent condition; roots/methodfamily exposed; noindependentblinddiscovery.','planned_slots_beforeconstruction_exclusions':3552,'excluded_slots_beforeexecution':432,'deadline_seconds':1200,'cost':'3120fixed16plyactualgames estimated12–16min fromnew169unitgamecost,1200sfuse. Originalcondition3120games inside169 matcheddeclaredcounts; noextraengineworker or singleexpectedhour run.','source_diagnostic_sha256':hashlib.sha256((R/'results/dev_aux/task174/analysis.json').read_bytes()).hexdigest()}
 (O/'declaration.json').write_text(json.dumps(D,indent=2),encoding='utf-8')
 s=(R/'results/dev_aux/task169/run.py').read_text(encoding='utf-8').replace('task169','task175')
 s=s.replace("score=G.score(b,color,len(moves),16);result=dict(","score=G.score(b,color,len(moves),16);result=dict(original_reward=score['reward'],objective='FINAL_UNIT_QUANTITY_INCLUDING_TERMINAL',")
 s=s.replace("reward=score['reward'],price_probes","reward=score['quantity_difference']/15,price_probes")
 compile(s,'run175','exec');(O/'run.py').write_text(s,encoding='utf-8');print(json.dumps(dict(frozen=True,games=3120,changed_quantity_choices=changes)))
if __name__=='__main__':prepare()
