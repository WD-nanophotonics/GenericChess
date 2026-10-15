from pathlib import Path
import json,ast
R=Path.cwd();O=R/'results/dev_aux/task1698';plan=json.loads((R/'results/dev_aux/task1692/plan.json').read_bytes());plan.update(status='FROZEN_8BOARD_CANDIDATE_NODE4096_CONTROL',families=plan['families'][:16],DEV_families=16,candidate_nodes=4096,opponent_nodes=64,expected_seconds=120,seconds_cap=600,max_go=10000,max_new_episodes=64,root_subsample='Predeclaredfirst16exposed8DEVfamilies, same2colors; lowcostcandidate-budget mechanismcontrol, notnewholdout or8training.',opponent='Fixedunit720actualcold64 asold8control; onlycandidatebudgetchanges from64to4096 bothcandidateprices.',cache='(nodes,price,full64square+side); onlyold1693unit720cold64choices reuse foropponent. Neveraliasownunit4096withopunit64.',interpretation='Fixed4TRAINcandidate minusunit atcandidate4096 versusSAMEop64, comparewitholdcandidate64gain onSAME16families. Noautomaticadditionalfamilies/horizon/nodes afterresults. UNKNOWNkept, notnodes-equivalent Native/fulltree.')
(O/'plan.json').write_text(json.dumps(plan,indent=2))
s=(R/'results/dev_aux/task1688/transfer_fixed.py').read_text(encoding='utf-8-sig').replace("task1693'","task1699'").replace('task1692/plan.json','task1698/plan.json');s=s.replace('def choose(s,price):','def choose(s,price,nodes):').replace('key=price,s','key=nodes,price,s').replace("e.send('go nodes 64')","e.send('go nodes '+str(nodes))").replace("'command':'go nodes 64'","'command':'go nodes '+str(nodes),'nodes':nodes")
s=s.replace('u=choose(s,pp) if len(ll)>1 else ll[0][0]','u=choose(s,pp,plan[\'candidate_nodes\'] if s[64]==c else plan[\'opponent_nodes\']) if len(ll)>1 else ll[0][0]')
s=s.replace("BASE=tuple(plan['baseline'])","""BASE=tuple(plan['baseline'])
for oldline in (R/'results/dev_aux/task1693/choices.jsonl').open():
 old=json.loads(oldline)
 if tuple(old['price'])!=BASE:continue
 state=tuple(old['state']);assert old['fen']==T.fen(state) and old['move'] in dict(T.moves(state));cache[64,BASE,state]=old['move']
""");(O/'control.py').write_text(s,encoding='utf8');ast.parse(s);print('FROZEN_8_BUDGET',len(plan['families']),plan['candidate_nodes'],plan['opponent_nodes'])
