from scripts.verify_leaper_new_family_pvs import endpoint

def games():
 result=[]
 for f in range(6):
  for layout in (0,1):
   for seat in (0,1):
    result.append(dict(game_id=len(result),case_id=f'f{f}h{layout}',family=f,layout=layout,fingerprint=f'fp{f}h{layout}',initial_record=dict(actions=[],history='complete'),on_seat=seat,status='TERMINAL',timing_eligible=True,Core_terminal=dict(status='max_ply',winner=None)))
 return result

def test_draws_are_known_but_do_not_establish_positive_quality():
 r=endpoint(games());assert r['raw']['known']==24 and r['raw']['mean_bounds']==[.5,.5]
 assert r['all24eligible'] and not r['amended_exploratory_screen'] and r['positive_eligible_families']==0

def test_overtime_preserves_actual_win_and_marks_both_seat_partners_unknown():
 gs=games();gs[0]['Core_terminal']=dict(status='checkmate',winner=0);gs[0]['timing_eligible']=False
 r=endpoint(gs);assert r['raw']['known']==24 and r['raw']['score_sum_known']==12.5
 assert r['timing_games']['missing']==1 and r['timing_pairs']['missing']==2
 assert r['timing_pairs']['planned']==24 and not r['all24eligible'] and not r['amended_exploratory_screen']

def test_missing_is_not_draw_and_swap_perspective_cannot_change_denominator():
 gs=games();gs[1].update(status='UNFINISHED',Core_terminal=dict(status='ongoing',winner=None))
 gs[0]['Core_terminal']=dict(status='checkmate',winner=1) # ON seat0 actually LOST
 r=endpoint(gs);assert r['raw']['missing']==1 and r['raw']['score_sum_known']==11
 assert r['raw']['mean_bounds']==[11/24,12/24]
 assert r['timing_pairs']['missing']==2 and not r['amended_exploratory_screen']

def test_three_positive_families_required_not_three_dependent_games():
 gs=games()
 for i in (0,1,2):gs[i]['Core_terminal']=dict(status='checkmate',winner=gs[i]['on_seat'])
 assert not endpoint(gs)['amended_exploratory_screen']
 for i in (4,8):gs[i]['Core_terminal']=dict(status='checkmate',winner=gs[i]['on_seat'])
 r=endpoint(gs);assert r['amended_exploratory_screen'] and r['positive_eligible_families']==3
 assert r['original_registration_gate'].startswith('FAILED')


def test_mechanism_comparison_stops_at_first_action_divergence():
 from scripts.verify_leaper_new_family_pvs import matched_prefixes
 import copy,pytest
 def q(a,h):return dict(record_before_sha256=h,decision=dict(action=a,score=0,completed_depth=2,nodes=3,qnodes=4))
 pair=games()[:2]
 pair[0]['queries']=[q('same','root'),q('left','shared-prefix'),q('later','different-left')]
 pair[1]['queries']=[q('same','root'),q('right','shared-prefix'),q('later','different-right')]
 r=matched_prefixes(pair)[0];assert not r['first_action_differs'] and r['first_divergent_relative_ply']==1 and not r['common_complete_path']
 pair[1]['queries'][1]['record_before_sha256']='other-history'
 with pytest.raises(AssertionError):matched_prefixes(pair)
