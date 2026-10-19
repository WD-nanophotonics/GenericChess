"""POST-HOC sensitivity (designed after seeing fitness): registered contrasts restricted to
EVAL slots whose root record never occurred as a TRAIN episode root. Not a registered result."""
from pathlib import Path
import json
from results.dev_aux.task2586.analyze import contrast
D=Path('results/dev_aux/task2586');E=D/'eval';G=D/'generic'
def run():
 ep=json.loads((E/'eval-plan.json').read_text());rows={tuple(g['slot']):g for g in map(json.loads,(E/'eval-games.jsonl').open())}
 train={(g['generator_seed'],json.dumps(g['initial_record'],sort_keys=True))for g in map(json.loads,(G/'games.jsonl').open())}
 rootkey=lambda s:(s[0],json.dumps(rows[tuple(s)]['initial_record'],sort_keys=True))
 exposed={(s[0],s[2])for s in ep['slots']if rootkey(s)in train};fresh=[s for s in ep['slots']if(s[0],s[2])not in exposed]
 pairs=[('Fixed@100k','initial'),('Fixed@400k','initial'),('Fixed@400k','Fixed@100k'),('OldRulesMean','initial'),('Fixed@400k','OldRulesMean')]
 out=dict(status='POST_HOC_SENSITIVITY_NOT_REGISTERED',exposed_rule_families=sorted(exposed),fresh_slots=len(fresh),all_slots=len(ep['slots']),contrasts={a+' - '+b:dict(fresh=contrast(rows,fresh,a,b)['bounds'],by_foe={o:contrast(rows,[s for s in fresh if s[5]==o],a,b)['bounds']for o in ep['foes']})for a,b in pairs})
 (E/'exposure-sensitivity.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=1))
if __name__=='__main__':run()
