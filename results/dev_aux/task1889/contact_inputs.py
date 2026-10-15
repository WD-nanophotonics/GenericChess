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
OUT=Path('results/dev_aux/task1889')
def write(n,d):
 with (OUT/n).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2)
def targets(actor,raw,moves):
 return {raw[(int(m[3])-1)*4+ord(m[2])-97].upper() for m,_ in moves if raw[(int(m[3])-1)*4+ord(m[2])-97]!='.'}
def run():
 seed=2026101562089;plan=dict(status='FROZEN_BEFORE_INPUT_DRAW',seed=seed,wanted=16,attempt_cap=50000,seconds_cap=60.,source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),question='Can a symmetric price-independent legal capture-opportunity filter cheaply produce a new distinct KRN root law before future true-W-L pilot?',filter='Uniform six-square KkRrNn placements, bothkingssafe, BOTHsides>=4legalmoves and legalcaptures of BOTHenemyR ANDenemyN. No materialweights/search/proofs/WDL/previouspriceactions. D4+colorunique, excludeold1822/1846/1872orbits. Initialside0/rolesequallyweighted in future study.',decision='Frozen1881contactH24 completed192games765.662s; TRAINselected2 beforeDEV, DEV2-minus1=3/32(actualW-L events), only3families androle0. This limitedpositive warrants ONE small freshinput/opponent transfer check, not price tuning or claimstablehumanratio. Fixedtheta2vsunit1, opponent64and512,16freshfamilies/bothroles planned128games expected600s/hard1200s plus<=60sNativefrontier qualification. No reward/outcome/proxyfilter in inputgeneration, all16acceptedrootsretained; no oldcap extension/extra workers. If sparse retain failure, no relaxingfilter.')
 write('plan.json',plan);actor=RoyalActor(4);rng=random.Random(seed);seen=set();roots=[];counts=Counter();t=_load_transport();beg=time.perf_counter()
 for oldpath in ('results/dev_aux/task1822/qualification.json','results/dev_aux/task1846/qualification.json','results/dev_aux/task1872/feasibility.json'):
  for old in json.loads(Path(oldpath).read_text())['roots']:seen.update(orbit(tuple(old['root'])))
 while len(roots)<16 and counts['attempts']<50000 and time.perf_counter()-beg<60:
  counts['attempts']+=1
  if counts['attempts']%128==0:t.stop_check(Path.cwd())
  board=['.']*16
  for square,piece in zip(rng.sample(range(16),6),'KkRrNn'):board[square]=piece
  raw=tuple(board)+(0,)
  # Cheap prefilter only movement geometry, to avoid enumerating illegal moves.
  occupied=[i for i,p in enumerate(board) if p!='.']
  if not all({'R','N'} <= {board[b].upper() for a in occupied for b in occupied if actor.side(board[a])==side and actor.side(board[b])!=side and board[b].upper() in ('R','N') and actor.hit(raw,a,b)} for side in (0,1)):
   counts['geometry_reject']+=1;continue
  if any(actor.attacked(raw,actor.king(raw,side),1-side) for side in (0,1)):
   counts['king_check_reject']+=1;continue
  moves=[actor.moves(tuple(board)+(side,)) for side in (0,1)]
  if any(len(x)<4 for x in moves):counts['legal_count_reject']+=1;continue
  if not all({'R','N'}<=targets(actor,raw,x) for x in moves):counts['legal_capture_reject']+=1;continue
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
   actual={uci(a) for a in s.legal_actions()};assert actual=={a for a,_ in actor.moves(raw)} and {'R','N'}<=targets(actor,raw,[(a,None) for a in actual])
   qualified.append(dict(family=i,phase='CONFIRM',setup=s.to_record().initial_setup_key,root=list(raw),state_sha=hashlib.sha256(repr(s.state).encode()).hexdigest(),legal=len(actual)))
  with (OUT/'rules.json').open('x',encoding='utf-8') as f:f.write(text)
 write('feasibility.json',dict(status='FULL_16_INPUTS' if len(roots)==16 else 'PARTIAL_OR_EMPTY_FILTER_RESULT',roots=qualified,counts=dict(counts),generation_seconds=elapsed,seconds=time.perf_counter()-beg,native_go=0,games=0,proof_calls=0,prices_or_WDL_filter=False,scope=plan['decision']))
 print(json.dumps(dict(accepted=len(roots),counts=dict(counts),seconds=time.perf_counter()-beg)))
if __name__=='__main__':run()
