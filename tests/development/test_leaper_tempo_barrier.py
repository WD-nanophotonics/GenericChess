"""Keep protected-tempo NOT-WIN distinct from a cooperative DRAW trace."""
from pathlib import Path
from copy import deepcopy
import gzip,json,hashlib
import pytest
from scripts.verify_leaper_delayed_capture import load
from scripts.leaper_tempo_barrier import qualify

DATA=Path(__file__).resolve().parents[2]/'docs/research/data/leaper_support_and_delayed_win_20261024'

def packet():return load(DATA/'tempo-registration.json'),load(DATA/'tempo.json.gz')


def test_tempo_upper_certificate_covers_all_white_choices_without_draw_imputation():
    reg,m=packet();q=qualify(reg,m,DATA)
    assert q['certificate']=='NOT_WHITE_WIN'and q['all_white_first_entries_checked']==8
    assert q['exact_White_WDL'].startswith('UNKNOWN')
    assert q['literal_trace_result']=='repetitionDRAWply6'


def test_missing_white_first_choice_cannot_support_an_all_choice_policy(tmp_path):
    reg,m=packet();parent=load(DATA/'entry-square.json.gz')
    next(r for r in parent['rows']if r['mask']==22)['children'].pop()
    raw=gzip.compress(json.dumps(parent).encode(),mtime=0)
    (tmp_path/'entry-square.json.gz').write_bytes(raw);reg['parent_sha256']=hashlib.sha256(raw).hexdigest()
    with pytest.raises(AssertionError):qualify(reg,m,tmp_path)


def test_dabbaba_cannot_be_removed_from_the_claimed_shuttle_policy():
    reg,m=packet();reg['plan']['policy']['B_shuttle_squares']=[1,5]
    with pytest.raises(AssertionError):qualify(reg,m,DATA)
