"""Unknown-sided interaction and fixed-price model binding controls."""
from results.dev_aux.task2577.analyze import effect_of_matching
from results.dev_aux.task2568.summary import contrast
def make(rewards):
 labels=("TD_q2|q2","TD_plain|q2","TD_q2|plain","TD_plain|plain")
 return {(0,1977,501001,0,l,"unit"):dict(reward=v,record={})for l,v in zip(labels,rewards)},[[0,1977,501001,0,l,"unit"]for l in labels]
def test_exact_matching_positive():
 r,s=make([1,-1,-1,1]);assert effect_of_matching(r,s)["bounds"]==[4,4]
def test_preserve_known_sides_of_U():
 r,s=make([None,-1,-1,1]);assert effect_of_matching(r,s)["bounds"]==[2,4]
def test_missing_same_interval_as_U_not_draw():
 r,s=make([0,0,0,1]);del r[tuple(s[0])];assert effect_of_matching(r,s)["bounds"]==[0,2]
def test_true_draw_is_point_not_unknown():
 r,s=make([0,0,0,0]);assert effect_of_matching(r,s)["bounds"]==[0,0]
def test_contrast_orientation_and_known_side():
 r,s=make([None,-1,0,0]);x=contrast(r,s,"TD_q2|q2","TD_plain|q2");assert x["bounds"]==[0,2]and x["counts"]["paired_U"]==1
