"""Incremental publicSession submit, with exact full-record comparison andfinalpublicreplay."""
import json
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record

def advance(session,record,complete):
 before=session.to_record();target=deserialize_game_record(json.dumps(record))
 assert target.resigned_by is None and target.declaration is None,'Scopedordinarymoveaudit rejectsnonmoveendings'
 assert target.actions[:len(before.actions)]==before.actions
 if complete:
  assert len(target.actions)==len(before.actions)+1;session.submit(target.actions[-1])
 else:assert target.actions==before.actions
 assert session.to_record()==target
 assert json.loads(serialize_game_record(session.to_record()))==record
 return session
