"""Lossless JSON for observed research records, including terminal enums."""
from dataclasses import asdict,is_dataclass
from enum import Enum
from fractions import Fraction
import json
import os
from pathlib import Path
import tempfile
import time

def record_value(value):
    if is_dataclass(value) and not isinstance(value,type):return record_value(asdict(value))
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
