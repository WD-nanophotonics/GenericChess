"""Verify compact published evidence without private graph caches or new fitness."""
import argparse,gzip,hashlib,json,sys,time
from collections import defaultdict
from copy import copy,deepcopy
from dataclasses import replace
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_from_dict
from generic_chess.core.pieces import Piece
from generic_chess.core.attacks import is_in_check
from generic_chess.core.transition import legal_successors
from scripts.leaper_retrograde import fresh_state

def verify_proof(c,row):
 s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])));tree=defaultdict(set);leaves=set()
 for raw in row['leaf_paths']:
  path=tuple(action_from_dict(x)for x in raw);leaves.add(path)
  for n,a in enumerate(path):tree[path[:n]].add(a)
 todo=[(s,())];nodes=0
 while todo:
  session,path=todo.pop();nodes+=1
  if session.state.terminal_status.is_terminal:
   assert path in leaves and session.state.terminal_status.winner==row['winner'];continue
  chosen=tree[path];legal=set(session.legal_actions());assert chosen and chosen<=legal
  if session.state.position.side_to_move==row['winner']:assert len(chosen)==1
  else:assert chosen==legal
  for a in chosen:
   child=copy(session);child.submit(a);todo.append((child,path+(a,)))
 assert nodes==row['nodes'];return nodes

def verify(directory):
 start=time.perf_counter();m=json.loads((directory/'manifest.json').read_text());blob=(directory/m['file']).read_bytes();assert len(blob)==m['bytes']and hashlib.sha256(blob).hexdigest()==m['sha256'];raw=gzip.decompress(blob);assert len(raw)==m['uncompressed_bytes'];p=json.loads(raw)
 c={fp:compile_rule(ruleset_from_dict(r))for fp,r in p['rules'].items()};assert all(x.ruleset_fingerprint==fp for fp,x in c.items());nodes=sum(verify_proof(c[r['record']['ruleset_fingerprint']],r)for r in p['proofs']);assert nodes==1847 and len(p['proofs'])==83
 negative=0
 for kind in('wrongwinner','missingbranch'):
  row=deepcopy(next(r for r in p['proofs']if len(r['leaf_paths'])>1))
  if kind=='wrongwinner':row['winner']=1-row['winner']
  else:row['leaf_paths'].pop()
  try:verify_proof(c[row['record']['ruleset_fingerprint']],row)
  except(AssertionError,KeyError):negative+=1
  else:raise AssertionError('corrupted proof accepted')
 king_states=0;king_edges=0
 for fp,compiled in c.items():
  rule=ruleset_from_dict(p['rules'][fp]);assert compiled.max_ply==128 and compiled.repetition_limit==4 and compiled.repetition_policy=='draw';assert rule.capture_disposition=='remove_from_game';assert not rule.promotion_allowed and not rule.promotion_forced;assert all(not t.is_promotable for t in rule.piece_types);assert all(not any(mask)for masks in rule.drop_allowed.values()for mask in masks)
  template=GameSession(compiled).state.position;positions=set()
  for a in range(16):
   for b in range(16):
    if a==b:continue
    board=[None]*16;board[a]=Piece(0,'K','K');board[b]=Piece(1,'K','K')
    for side in(0,1):
     pos=replace(template,board=tuple(board),side_to_move=side)
     if not any(is_in_check(pos,who,compiled)for who in(0,1)):positions.add(pos)
  assert len(positions)==312
  for pos in positions:
   state=fresh_state(pos,compiled);assert state.terminal_status.winner is None;king_states+=1
   for a,ch in legal_successors(state,compiled):assert ch.position in positions and ch.terminal_status.winner is None;king_edges+=1
 assert king_states==2496 and king_edges==9216
 assert p['lowmaterial']['rows']==2784 and p['lowmaterial']['totals']['structural_draw']==2697 and len(p['true_forks'])==34
 assert p['bare_terminal']['nodes']==2000000 and p['bare_terminal']['rows']==179 and p['bare_terminal']['planned']==208
 assert p['clock_control']['matches']==96 and p['fresh_verification']['checked']==192
 assert len(p['positive_queries'])==271 and p['positive_prices']['missing']==1
 for n,s in p['sources'].items():
  # Keep original byte provenance and separately verify normalized source text.
  assert s['sha256']and hashlib.sha256(s['text'].encode()).hexdigest()==s['text_sha256']
 return dict(status='COMPLETE',proofs=83,proof_Core_nodes=nodes,negative_controls=negative,two_K_positions=king_states,two_K_Core_edges=king_edges,seconds=time.perf_counter()-start,scope='Packetalone plus sharedCore;no privategraph/fullrawproducer/fitness/training invoked. Local graph,census and aggregate research claims retain source qualifications.')

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path,nargs='?',default=Path(__file__).resolve().parent);args=parser.parse_args();print(json.dumps(verify(args.directory),indent=2))
