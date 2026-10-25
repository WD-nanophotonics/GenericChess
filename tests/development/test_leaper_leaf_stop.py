from scripts.leaper_selected_leaf_reference import LocalStop

def test_transport_polled_at_most_once_per_quarter_second():
    t=[0.];calls=[];c=LocalStop(10,clock=lambda:t[0],stop=lambda:(calls.append(1),False)[1])
    for _ in range(1000):assert not c.is_cancelled()
    assert len(calls)==1
    t[0]=.25;assert not c.is_cancelled()and len(calls)==2

def test_role_stop_observed_at_next_bounded_poll():
    t=[0.];stop=[False];c=LocalStop(10,clock=lambda:t[0],stop=lambda:stop[0]);assert not c.is_cancelled()
    stop[0]=True;t[0]=.251;assert c.is_cancelled()
