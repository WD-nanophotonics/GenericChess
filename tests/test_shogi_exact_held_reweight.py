import hashlib,json
from fractions import Fraction as F
from pathlib import Path
from scripts.shogi_exact_twenty_family import exact_twenty_intervals
from scripts.shogi_complete_board_intervals import moment
from scripts.shogi_exact_contact_family import exact_board_means
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'docs/research/data'
def test_full_mass_unchanged_prefix_and_unrestricted_shift_law():
    raw=json.loads((DATA/'shogi_exact_held_reweight_20261005.json').read_text())
    old=json.loads((DATA/'shogi_random_deployment_20261005.json').read_text());old={row['type']:row for row in old['rows']}
    board=json.loads((DATA/'shogi_full_contact_distance_20261005.json').read_text());board={row['profile']['current']:row for row in board['rows']}
    assert raw['complete'] and raw['blockers_completed']==81 and raw['empty_drop_frames']==0
    for row in raw['rows']:
        masses={int(t):F(v) for t,v in row['masses'].items()}
        assert sum(masses.values())==1
        assert [masses.get(t,F(0)) for t in (2,3,0)]==[F(old[row['type']]['masses'][key]) for key in ('direct','second','zero')]
        for law in ('geometric_half','linear_mixture'):
            mean=sum(value*moment(law,t) for t,value in masses.items() if t)
            assert mean==F(row['means'][law])
            if row['type'] in ('S','G','B','R'):
                expected=sum(F(n)*moment(law,int(t)+1) for t,n in board[row['type']]['histogram'].items())/511920
                assert mean==expected

def test_exact_twenty_common_scale_and_every_native_board_hand_gap():
    for law in ('geometric_half','linear_mixture'):
        boxes=exact_twenty_intervals(law)
        assert len(boxes)==20 and all(0<lo==hi<=1 for lo,hi in boxes.values())
        assert boxes['board','TR']==(1,1)
        for mode in 'PLNSGBR':assert boxes['board',mode][0]>boxes['hand',mode][0]
    raw=json.loads((DATA/'shogi_exact_held_reweight_20261005.json').read_text())
    assert raw['public_transitions']==raw['source_queries']==0 and raw['seconds']<15
    for name,pin in raw['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==pin
