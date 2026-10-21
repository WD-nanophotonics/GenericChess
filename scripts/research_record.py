"""Lossless JSON for observed research records, including terminal enums."""
from dataclasses import fields,is_dataclass
from enum import Enum
from fractions import Fraction
import json
import os
import sys
from pathlib import Path
import tempfile
import time
from generic_chess.core.actions import PassAction, action_to_dict
from generic_chess.session.record import GameRecord

def record_value(value):
    # Research producers already load numpy. Convert scalar metadata without
    # making numpy a dependency for stdlib-only record consumers; arrays stay
    # explicit NPZ data rather than silently expanding into JSON.
    numpy = sys.modules.get('numpy')
    if numpy is not None and isinstance(value, numpy.generic):
        return record_value(value.item())
    # PassAction has no dataclass fields. Generic dataclass conversion used to
    # turn it into {}, losing its identity in a recorded decision/PV.
    if isinstance(value, PassAction):return action_to_dict(value)
    # A GameRecord is a replay boundary, not a generic dataclass dump.
    # Action kinds and version-specific declaration/setup fields matter.
    # Standalone action/PlayerDecision diagnostic shapes stay unchanged.
    if isinstance(value, GameRecord):
        from generic_chess.session.serialization import serialize_game_record
        return json.loads(serialize_game_record(value))
    if is_dataclass(value) and not isinstance(value,type):
        return {item.name: record_value(getattr(value, item.name))
                for item in fields(value)}
    if isinstance(value,Enum):return record_value(value.value)
    if isinstance(value,Fraction):return str(value)
    if isinstance(value,dict):
        converted={str(k):record_value(v) for k,v in value.items()}
        if len(converted)!=len(value):raise ValueError('record key collision')
        return converted
    if isinstance(value,(list,tuple)):return [record_value(v) for v in value]
    if value is None or type(value) in (str,int,float,bool):return value
    raise TypeError(f'unsupported research record: {type(value).__name__}')

def write_record(path,value,*,indent=2):
    # Finish conversion BEFORE opening the evidence file. Producers persist
    # initial/all-action/progress records before advancing to another event.
    body=json.dumps(record_value(value),indent=indent,allow_nan=False)+'\n'
    path=Path(path)
    temporary=None
    try:
        # Same-directory replacement keeps readers on either complete frontier.
        # Close the temporary handle before replacement on Windows. Failure
        # leaves the previous record intact; no new format/history protocol.
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',newline='\n',
                dir=path.parent,prefix='.'+path.name+'.',suffix='.tmp',delete=False) as f:
            temporary=Path(f.name)
            f.write(body)
            f.flush()
            os.fsync(f.fileno())
        for attempt in range(3):
            try:
                os.replace(temporary,path)
                break
            except PermissionError as exc:
                # Observed Windows scanner/sharing races can briefly block
                # replacement after fsync. Retry only that same closed file;
                # permanent/other errors still preserve the prior frontier.
                if getattr(exc, 'winerror', None) not in (5, 32, 33) or attempt == 2:
                    raise
                time.sleep(0.01 * (attempt + 1))
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
