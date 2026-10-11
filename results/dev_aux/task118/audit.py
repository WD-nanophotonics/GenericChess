"""Exposed feature-rank and direct-label identity audit; no training or new games."""
import hashlib,json,time
from fractions import Fraction
from pathlib import Path
import chess
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent
p114=ROOT/'results/dev_aux/task114/result.json';p116=ROOT/'results/dev_aux/task116/result.json'
games=json.loads(p114.read_bytes())['games'];states=json.loads(p116.read_bytes())['states']
TYPES=[chess.PAWN,chess.KNIGHT,chess.BISHOP,chess.ROOK,chess.QUEEN];NAMES=['P','N','B','R','Q'];start=time.perf_counter()
def guard():
 if time.perf_counter()-start>=120:raise TimeoutError('120s postprocessing cap')
 for root in [ROOT,ROOT.parent/'GenericChess 2']:
  for name,key in [('rollout.json','user_paused'),('slack.json','stopped')]:
   if json.loads((root/'.local_agent'/name).read_bytes()).get(key):raise RuntimeError('persistent user stop')
def feature(b,side):return [len(b.pieces(t,side))-len(b.pieces(t,not side)) for t in TYPES]
def rank(matrix):
 a=[[Fraction(x) for x in r] for r in matrix];pivot=0
 for col in range(len(a[0]) if a else 0):
  row=next((r for r in range(pivot,len(a)) if a[r][col]),None)
  if row is None:continue
  a[pivot],a[row]=a[row],a[pivot];v=a[pivot][col];a[pivot]=[x/v for x in a[pivot]]
  for r in range(len(a)):
   if r!=pivot and a[r][col]:
    v=a[r][col];a[r]=[x-v*y for x,y in zip(a[r],a[pivot])]
  pivot+=1
 return pivot
rows=[]
for state in states:
 guard();b=chess.Board(state['fen']);side=state['agent_color'];before=feature(b,side);deltas=[];terminal=0
 assert b.turn==side
 for m in b.legal_moves:
  child=b.copy(stack=True);child.push(m)
  if child.is_game_over(claim_draw=False):terminal+=1;continue
  after=feature(child,side);deltas.append([a-z for a,z in zip(after,before)])
 rows.append({'seed':state['seed'],'opening_length':state['opening_length'],'agent_color':side,'legal_nonterminal_deltas':deltas,'terminal_children':terminal,'full_material_rank':rank(deltas),'free_NBRQ_rank':rank([d[1:] for d in deltas]),'exposed_types':[n for i,n in enumerate(NAMES) if any(d[i] for d in deltas)]})
summary=[]
for depth in [6,24,48]:
 group=[r for r in rows if r['opening_length']==depth];all_d=[d for r in group for d in r['legal_nonterminal_deltas']]
 summary.append({'opening_length':depth,'states':len(group),'nonterminal_child_rows':len(all_d),'nonzero_rows':sum(any(d) for d in all_d),'aggregate_full_material_rank':rank(all_d),'aggregate_free_NBRQ_rank':rank([d[1:] for d in all_d]),'exposed_types':[n for i,n in enumerate(NAMES) if any(d[i] for d in all_d)]})
final_rows=[];terminal_rows=[]
for g in games:
 guard();b=chess.Board(g['end_fen']);f=feature(b,g['agent_color'])
 if g['score']['terminal']:terminal_rows.append({'root_seed':g['root_seed'],'opening_length':g['opening_length'],'policy':g['policy'],'termination':g['score']['termination'],'reward':g['score']['reward']});continue
 quantity=sum(f);exact=Fraction(quantity,15)
 assert quantity==g['score']['quantity_difference']
 assert abs(float(exact)-g['score']['reward'])<1e-12
 final_rows.append({'root_seed':g['root_seed'],'opening_length':g['opening_length'],'policy':g['policy'],'agent_color':g['agent_color'],'material_feature':f,'quantity_target_numerator':quantity,'quantity_target_denominator':15})
final_rank=rank([r['material_feature'] for r in final_rows]);assert len(final_rows)+len(terminal_rows)==96
result={'complete':True,'input_sha256':{'task114':hashlib.sha256(p114.read_bytes()).hexdigest(),'task116':hashlib.sha256(p116.read_bytes()).hexdigest()},'material_features':NAMES,'first_choice_rows':rows,'summary':summary,'nonterminal_final_rows':final_rows,'nonterminal_final_count':len(final_rows),'nonterminal_final_matrix_rank':final_rank,'terminal_count':len(terminal_rows),'terminal_rows_excluded_from_identity':terminal_rows,'exact_direct_label_solution':[{'numerator':1,'denominator':15} for _ in NAMES],'direct_linear_solution_unique_without_intercept':final_rank==5,'wall_seconds':time.perf_counter()-start,'mature_games_executed':0,'learned_updates':0,'findings':['One-ply material-feature variation is a structural diagnostic only; deeper search and future outcomes can create value information absent here.','Directly supervising the final nonterminal material vector with its final unit-count reward has the exact equal-unit solution by definition; if rank5 it is the unique unconstrained no-intercept solution. This shortcut cannot be presented as recovered human prices.','This identity does not apply to reinforcement policy optimization or return prediction from earlier states. Those estimates can reflect future consequences and depend on the play distribution.','Terminal/mate targets are excluded, not silently replaced with material counts.','These are already exposed records; no holdout promotion, distribution re-selection, new games, fitted human values or actual training.']}
(OUT/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps({k:result[k] for k in ['summary','nonterminal_final_count','nonterminal_final_matrix_rank','terminal_count','direct_linear_solution_unique_without_intercept','wall_seconds']}))