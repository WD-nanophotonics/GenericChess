"""Saved fresh use evidence only; no producer or outcome-source reruns."""
import hashlib
import json
from fractions import Fraction as F
from pathlib import Path
from types import SimpleNamespace as NS
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.terminal import TerminalStatus,TerminalResult
from scripts.contact_rb_choice import rb_contact_choice

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'docs/research/data/chess_contact_scoped_use_20261005.json'


def test_frozen_population_prelabel_checkpoint_and_budget():
    r=json.loads(RAW.read_text())
    assert r['complete'] and 'error' not in r and len(r['rows'])==4
    assert (r['proposals'],r['public_transitions'],r['enumerated'],r['outer_probe_calls'])==(14,20,121,10)
    assert r['all_selections_frozen_before_probes'] and r['external_sources_unchanged']
    assert r['working_tables_unchanged'] and r['source_hashes_unchanged']
    freeze=RAW.with_suffix('.selections.json')
    assert hashlib.sha256(freeze.read_bytes()).hexdigest()==r['prelabel_freeze_sha256']
    before=json.loads(freeze.read_text())
    assert all(not row['selected_goal_evidence'] and not row['paired_margins'] for row in before)
    for old,new in zip(before,r['rows']):
        assert old['selections_before_labels']==new['selections_before_labels']
        assert old['all_children']==new['all_children']
        key=' '.join(new['root_request']['fen'].split()[:4])
        assert key not in r['excluded_current_fens']
        assert new['weight']=='1/4' and new['complete_choice_count']==5
    for p,h in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h


def test_saved_family_selection_and_all_unknown_quiet_mass():
    r=json.loads(RAW.read_text())
    class Game:
        def terminal(self,c):
            return c.terminal
    for row in r['rows']:
        children={}
        for key,packet in row['all_children'].items():
            s=packet['state'];p=s['position'];t=s['terminal_status']
            children[key]=NS(position=NS(board=[Piece(**x) if x else None for x in p['board']],
                                         hands=tuple(Hands() for _ in p['hands'])),
                             terminal=TerminalResult(TerminalStatus[t['status'].split('.')[1]],t['winner']))
        replay=rb_contact_choice(children,Game(),owner=row['owner'],complete=True)
        assert replay['selected']==row['selections_before_labels']['contact_family']['selected']
        zero=row['selections_before_labels']['zero']['selected']
        assert 'quiet' in zero and row['selected_goal_evidence'][zero]['interval']==[-1,1]
        assert row['selected_goal_evidence'][replay['selected']]['interval']==[0,0]
    assert r['mean_paired_margins']=={'unit':['1/4','1/4'],'zero':['-1','1']}
    assert F(r['mean_paired_margins']['unit'][0])>=F(1,10)
    assert F(r['mean_paired_margins']['zero'][0])<F(1,10)<F(r['mean_paired_margins']['zero'][1])
