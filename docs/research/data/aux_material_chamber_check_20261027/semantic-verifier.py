"""Replay only the finite saved PVs through the committed semantic adapter."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution,compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.search_runtime import _plain_leaper_hash_patterns

def physical(s):
 p=s.state.position
 return (p.board,p.hands,p.side_to_move,p.ruleset_fingerprint,p.aux_state,p.board_shape,s.state.ply_count,s.state.terminal_status,s.result)

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--data',type=Path,required=True)
 args=parser.parse_args(); path=args.data
 plan=json.loads((path/'plan.json').read_bytes())
 b=Path(plan['input']).read_bytes()
 assert sha256(b).hexdigest()==plan['input_sha256']
 worlds=json.loads(b); rows=[json.loads(x) for x in (path/'queries.jsonl').read_bytes().splitlines()]
 cache={}; output=[]
 for row in rows:
  w=worlds[row['world']]
  if row['world'] not in cache:
   rule=ruleset_from_dict(w['rule'])
   old=compile_ruleset_for_execution(rule);new=compile_legacy_ruleset_for_semantic_execution(rule)
   assert old.ruleset_fingerprint==new.ruleset_fingerprint==w['fingerprint']
   assert semantic_engine_for(old) is None and semantic_engine_for(new) is not None
   assert _plain_leaper_hash_patterns(old) is None
   certificate=_plain_leaper_hash_patterns(new)
   assert certificate
   cache[row['world']]=(old,new,len(certificate))
  old,new,n=cache[row['world']]
  record=dict(w['initial_record'])
  record['actions']=list(record['actions'])+[c['action'] for c in row['pv']]
  parsed=deserialize_game_record(json.dumps(record))
  a=GameSession.replay(old,parsed);b=GameSession.replay(new,parsed)
  assert physical(a)==physical(b)
  # External key equality is observed, never forced or copied into the other run.
  output.append(dict(world=row['world'],depth=row['depth'],B=row['B'],physical_equal=True,record_equal=a.to_record()==b.to_record(),position_equal=a.state.position==b.state.position,history_equal=a.state.history==b.state.history,repetition_counts_equal=a.state.repetition_counts==b.state.repetition_counts,raw_dimensions=[list((a.state.position.board_width,a.state.position.board_height)),list((b.state.position.board_width,b.state.position.board_height))],terminal_status=dict(status=a.state.terminal_status.status.value,winner=a.state.terminal_status.winner),certificate_pairs=n))
 result=dict(scope='Replay of original120returned PVs only; no new Player/game/training/solver/Native build or Native call',source='shared compiler/execution/Core infrastructure at current own1aa70fd8 and committed sandbox92f51dd1 with no runtime delta',pv_count=len(output),plies=sum(len(r['pv']) for r in rows),semantic_product='ExecutableSemanticRuleset via explicit shared adapter; raw default remains CompiledRuleSet',native='ir.capability is not an actual provider execution or speed result',certificate='Existing two-cell hash-footprint certificate only, NOT attack/legality certificate',rows=output,verifier_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
 (path/'semantic-pv-parity.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 (path/'semantic-verifier.py').write_bytes(Path(__file__).read_bytes())
 print(json.dumps(dict(PVs=len(output),plies=result['plies'],physical_equal=sum(r['physical_equal'] for r in output),record_equal=sum(r['record_equal'] for r in output),history_equal=sum(r['history_equal'] for r in output),position_equal=sum(r['position_equal'] for r in output),repetition_counts_equal=sum(r['repetition_counts_equal'] for r in output),certificate_pairs={str(k):v[2] for k,v in cache.items()})))
if __name__=='__main__': main()
