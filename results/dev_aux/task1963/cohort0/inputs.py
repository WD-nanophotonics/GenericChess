"""Input-only symmetric exchange-opportunity feasibility, no prices or WDL."""
from pathlib import Path
from collections import Counter
from dataclasses import replace
import random,time,json,hashlib
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.schema import RuleInitialSetupOption
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import serialize_ruleset,deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from scripts.generic_proof_fixtures import krk_ruleset
from scripts.generic_proof_rnb_bridge import orbit,actor_state,uci
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_win_proof import _same_state
from scripts.generic_session_native_material import _load_transport
OUT=Path('results/dev_aux/task1963/cohort0')
def write(n,d):
 with (OUT/n).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2)
def targets(actor,raw,moves):
 return {raw[(int(m[3])-1)*4+ord(m[2])-97].upper() for m,_ in moves if raw[(int(m[3])-1)*4+ord(m[2])-97]!='.'}
def run():
 seed=20261016641960;plan=dict(status='FROZEN_BEFORE_INPUT_DRAW',seed=seed,wanted=32,attempt_cap=50000,seconds_cap=60.,source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),question='Prospective1960 input-only cohort: can a NEW symmetric oneRtwoNperside price-independent contactlaw cheaply create32TRAIN_DEVfullpublicinputs withNOimmediateRcapture before any W-L?',filter='Uniform eight-square KkRrNNnn placements (constant2!2!multiplicity), bothkingssafe, BOTHsides>=4legalmoves, atleastonelegalenemyNcaptureandNOlegalenemyRcapture. No price or action-quality labels. No materialweights/search/proofs/WDL/previouspriceactions. D4+colorunique, excludeold1822and1846orbits. Initialside0/rolesequallyweighted in future study.',decision='PrioroneRtwoNcontactlaw has alllegalrho3leafpairs but0rootbestsetchanges atd2/4/6 andweakheldoutW-L. NineofsixteenbestsetsincludedimmediateRcaptures (notall, notcompletecause). Changedprice-freepremise: protectbothRfromimmediatecapture butretainNcontact; testfixedfull-depthactivation BEFOREanynewW-L. Retainall32roots/no parameter-successfilter. This filters rules/geometry, not those observed scores or learnedprices. DoesNOTprove cheap terminals, actual W-L signal or unbiased universalmu. If sparse retain failure, do not relaxfilter/extendcap. No Native or rewardgames in this producer. Predeclared split first16TRAIN/last16DEV. Followup study freezes ALL13 inventory-derived chamber representatives/boundaries includingrho<1. Follow task1960 prospective fixed proofON4096/cold per-game policy; original1938OFF baseline is superseded for these NEW inputs before any labels.')
 write('plan.json',plan);actor=RoyalActor(4);rng=random.Random(seed);seen=set();roots=[];counts=Counter();t=_load_transport();beg=time.perf_counter()
 for oldpath in ('results/dev_aux/task1822/qualification.json','results/dev_aux/task1846/qualification.json','results/dev_aux/task1919/feasibility.json','results/dev_aux/task1922/feasibility.json','results/dev_aux/task1933/feasibility.json','results/dev_aux/task1938/feasibility.json','results/dev_aux/task1941/feasibility.json'):
  for old in json.loads(Path(oldpath).read_text(encoding='utf-8'))['roots']:seen.update(orbit(tuple(old['root'])))
 while len(roots)<32 and counts['attempts']<50000 and time.perf_counter()-beg<60:
  counts['attempts']+=1
  if counts['attempts']%128==0:t.stop_check(Path.cwd())
  board=['.']*16
  for square,piece in zip(rng.sample(range(16),8),'KkRrNNnn'):board[square]=piece
  raw=tuple(board)+(0,)
  # Cheap prefilter only movement geometry, to avoid enumerating illegal moves.
  occupied=[i for i,p in enumerate(board) if p!='.']
  if not all({'N'} <= {board[b].upper() for a in occupied for b in occupied if actor.side(board[a])==side and actor.side(board[b])!=side and board[b].upper() in ('R','N') and actor.hit(raw,a,b)} for side in (0,1)):
   counts['geometry_reject']+=1;continue
  if any(actor.attacked(raw,actor.king(raw,side),1-side) for side in (0,1)):
   counts['king_check_reject']+=1;continue
  moves=[actor.moves(tuple(board)+(side,)) for side in (0,1)]
  if any(len(x)<4 for x in moves):counts['legal_count_reject']+=1;continue
  if not all('N' in targets(actor,raw,x) and 'R' not in targets(actor,raw,x) for x in moves):counts['legal_capture_reject']+=1;continue
  if raw in seen:counts['orbit_reject']+=1;continue
  seen.update(orbit(raw));roots.append(raw);counts['accepted']+=1
 elapsed=time.perf_counter()-beg;qualified=[]
 if roots:
  n=PieceType('N','Leaper',tuple(LeapAtom(d) for d in ((1,2),(2,1),(-1,2),(-2,1),(1,-2),(2,-1),(-1,-2),(-2,-1))))
  def rows(raw):
   board=tuple(None if x=='.' else Piece(int(x.islower()),x.upper(),x.upper()) for x in raw[:-1]);return tuple(tuple(board[i:i+4]) for i in range(0,16,4))
  rs=krk_ruleset(4);mask=(False,)*16
  rs=replace(rs,piece_types=rs.piece_types+(n,),initial_position=rows(roots[0]),initial_setup_options=tuple(RuleInitialSetupOption('family-'+str(i),rows(raw)) for i,raw in enumerate(roots[1:],1)),drop_allowed={'R':(mask,mask),'N':(mask,mask)},max_ply=96)
  text=serialize_ruleset(rs);c=compile_ruleset_for_execution(deserialize_ruleset(text))
  for i,raw in enumerate(roots):
   s=GameSession(c,None if i==0 else 'family-'+str(i));replayed=GameSession.replay(c,deserialize_game_record(serialize_game_record(s.to_record())));assert _same_state(replayed.state,s.state) and actor_state(s.state)==raw
   actual={uci(a) for a in s.legal_actions()};assert actual=={a for a,_ in actor.moves(raw)} and 'N' in targets(actor,raw,[(a,None) for a in actual]) and 'R' not in targets(actor,raw,[(a,None) for a in actual])
   qualified.append(dict(family=i,phase='TRAIN' if i<16 else 'DEV',setup=s.to_record().initial_setup_key,root=list(raw),state_sha=hashlib.sha256(repr(s.state).encode()).hexdigest(),legal=len(actual)))
  with (OUT/'rules.json').open('x',encoding='utf-8') as f:f.write(text)
 write('feasibility.json',dict(status='FULL_32_INPUTS' if len(roots)==32 else 'PARTIAL_OR_EMPTY_FILTER_RESULT',roots=qualified,counts=dict(counts),generation_seconds=elapsed,seconds=time.perf_counter()-beg,native_go=0,games=0,proof_calls=0,prices_or_WDL_filter=False,scope=plan['decision']))
 print(json.dumps(dict(accepted=len(roots),counts=dict(counts),seconds=time.perf_counter()-beg)))
if __name__=='__main__':run()
