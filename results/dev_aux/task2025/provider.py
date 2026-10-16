"""Explicit isolated KRNB6 legality extension; original KRN provider unchanged."""
from results.dev_aux.task1866.unit_panel import UnitProvider
from scripts.generic_win_proof import _same_state
from scripts.generic_proof_rnb_bridge import actor_state,uci
from generic_chess.session.session import GameSession
class KRNB6UnitProvider(UnitProvider):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  from scripts.generic_royal_actor import RoyalActor
  self.actor=RoyalActor(6)
 def position_command(self,session,state):
  if not _same_state(session.state,state):raise ValueError('fullstate mismatch')
  c=session.compiled
  if c.ruleset_fingerprint!=self.plan['fingerprint']or c.board_size!=6 or c.declarations or c.no_progress_draw is not None or c.capture_disposition!='remove_from_game' or {p.type_id for p in c.piece_types}!={'K','R','N','B'}:
   raise ValueError('outside explicit pinned KRNB6 qualification')
  raw=actor_state(state);actual={uci(a):a for a in session.legal_actions()}
  if set(actual)!=set(dict(self.actor.moves(raw))):raise ValueError('Core/literal KRNB frontier mismatch')
  record=session.to_record();root=GameSession(c,record.initial_setup_key);path=[uci(a)for a in record.actions]
  return 'position fen '+self.actor.fen(actor_state(root.state))+(' moves '+' '.join(path)if path else''),actual

 def profile(self,values):
  values=tuple(values);r,n,b,p=values
  name=self.plan['variant_names'][str(values)];self.e.send('setoption name UCI_Variant value '+name);raw=self.e.ready()
  assert any(x.startswith(f'info string variant {name} files 6 ranks 6 ') for x in raw)
  self.e.send('devauxleafrnbp '+' '.join(map(str,values)));ack=self.e.ready()
  expected=f'info string DEV_AUX leafRNBP {r} {n} {b} {p} nativeP {p} nativeR {r} nativeN {n} nativeB {b} captureP {p} captureR {r} captureN {n} captureB {b}'
  assert expected in ack;self.log('PROFILE',values=values,raw=raw,ack=ack);self.current=values
  self.e.send('ucinewgame');self.log('CLEAR',values=values,raw=self.e.ready())
