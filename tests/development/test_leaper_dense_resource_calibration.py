from scripts import leaper_dense_resource_calibration as producer
from scripts.verify_leaper_dense_resource_calibration import summarize
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint


def games():
 return [dict(game_id=2*f+i,family=f,long_seat=i,status='TERMINAL',timing_eligible=True,Core_terminal=dict(status='checkmate',winner=i)) for f in range(6) for i in (0,1)]


def test_missing_slot_never_passes_complete_screen():
 a=games();assert summarize(a)['screen_pass']
 a[0].update(status='FAILED',timing_eligible=False)
 r=summarize(a)
 assert not r['screen_pass'] and r['actual']['missing']==1
 assert r['actual']['mean_bounds']==[11/12,1]
 assert r['families'][0]['timing_pair']['missing']==2


def test_color_only_wins_do_not_become_resource_gain():
 a=games()
 for g in a:g['Core_terminal']['winner']=0
 r=summarize(a)
 assert not r['screen_pass'] and r['positive_eligible_families']==0
 assert all(f['long_net_actual']==0 for f in r['families'])


def test_equal_utc_is_uncredited_but_other_intervals_forward(monkeypatch):
 calls=[]
 monkeypatch.setattr(producer,'_record_work',lambda *a:calls.append(a))
 start='2026-10-27T06:40:00+00:00';end='2026-10-27T06:40:01+00:00'
 assert producer.record_work(start,start,'validation','subresolution')['uncredited']
 assert not calls
 producer.record_work(start,end,'validation','real')
 assert calls==[(start,end,'validation','real')]
 # Nonidentical invalid intervals must still reach the strict session validator.
 producer.record_work(end,start,'validation','backwards')
 assert calls[-1]==(end,start,'validation','backwards')


def test_literal_dense_family_contracts_and_full_rule_identity():
 rows=producer.inputs()['rows'];assert len(rows)==6
 assert len({r['fingerprint'] for r in rows})==6
 for row in rows:
  r=row['RuleSet'];assert row['record']['actions']==[]
  assert r['max_ply']==128 and r['repetition_limit']==4 and r['board_size']==5
  assert r['capture_disposition']=='remove_from_game'
  pieces=[p for rank in r['initial_position'] for p in rank if p]
  assert len(pieces)==12
  assert sorted(p['current_type_id'] for p in pieces if p['owner']==0)==['A','A','B','B','C','K']
  assert row['fingerprint']==compute_fingerprint(ruleset_from_dict(r))
  for typ in r['piece_types']:
   assert not typ['is_promotable'] and not typ['promotion_target_ids']
   offsets={tuple(a['offset']) for a in typ['movement_atoms']}
   assert (0,0) not in offsets and {(-x,-y) for x,y in offsets}==offsets
   assert all(a['kind']=='leap' for a in typ['movement_atoms'])
