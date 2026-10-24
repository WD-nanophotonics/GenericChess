"""Public gzip packets and observed failure contracts, no search queries."""
from pathlib import Path
import gzip,json,shutil
import pytest
from scripts.verify_leaper_qorder_prospective import qualify as qqual
from scripts.verify_leaper_clock_completion import qualify as cqual
from scripts.verify_leaper_rule_clock_cap import qualify as capqual
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'docs/research/data/leaper_clock_horizon_20261025'
I=ROOT/'docs/research/data/leaper_ordering_diagnosis_20261025/next-default-panel-inputs.json.gz'

def test_public_gzip_cost_panel_keeps_trivial_roots_out_of_parity():
    r=qqual(P/'qorder');assert r['queries']==32 and not r['parity_mismatches']and len(r['no_common'])==5
    assert sum(x['WDL_quality']=='IMMEDIATE_CORE_WIN_VERIFIED'for x in r['pairs'])==5


def test_public_clock_completion_cannot_be_reported_as_quality_improvement():
    r=cqual(P/'completion-quality',I)
    assert r['baseline_correct']==16 and r['completion_correct']==15 and r['regressions']==['next-role-p53']and not r['repairs']


def test_public_clock_cap_has_eight_completions_and_two_budget_limited():
    r=capqual(P/'clock-cap',P/'completion-quality',I)
    assert r['complete_clock_cases']==8 and len(r['budget_limited'])==2
    assert all(x['shared_prefix_exact']and x['correct']for x in r['cases'])


def test_clock_cap_changed_prefix_is_rejected(tmp_path):
    d=tmp_path/'cap';d.mkdir()
    for f in('plan.json','receipt.json'):(d/f).write_bytes((P/'clock-cap'/f).read_bytes())
    rows=[json.loads(x)for x in gzip.decompress((P/'clock-cap/queries.jsonl.gz').read_bytes()).splitlines()]
    rows[0]['iterations'][0]['score']+=1
    (d/'queries.jsonl').write_text(''.join(json.dumps(x)+'\n'for x in rows),encoding='utf-8')
    with pytest.raises(AssertionError):capqual(d,P/'completion-quality',I)
