"""Unknown-aware WDL selector and shared TC episodic mechanics."""
from results.dev_aux.task2568.train import improvement,proposal,initial
from results.dev_aux.task2566.tc import TCEpisode
from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2492.episode import TDLeafEpisode

def rows(values):return[dict(variant=v,color=c,outcome=z)for(v,c),z in zip([('incumbent',0),('proposal',0),('proposal',1),('incumbent',1)],values)]
def test_unknown_not_draw():assert improvement(rows([0,None,0,0]))==[-.5,.5]
def test_pair_colors():assert improvement(rows([-1,1,-1,1]))==[2.,2.]
def test_missing_no_accept():assert improvement(rows([0,1,0,0])[:3])is None
def test_equal_no_accept():assert improvement(rows([1,1,-1,-1]))==[0.,0.]
def test_proposal_anchor():
 w=initial(1977);v=proposal(w,1977,3);assert v[0]==1 and sum(a!=b for a,b in zip(w,v))==1

def test_tc_persists_between_episodes():
 from types import SimpleNamespace
 t=TCEpisode(5);m=Model([1]*5)
 def receipt(value,phi):return SimpleNamespace(complete=True,value=value,pv_terminal=False,pv_phi=phi)
 t.observe(m,receipt(1,[0,1,0,0,0]));r=t.finish(m,1);old=list(t.tc.absolute);assert old[1]>0
 t.observe(m,receipt(-1,[0,1,0,0,0]));r=t.finish(m,-1);assert t.tc.absolute[1]>old[1]and r['rates_before'][1]==1 and r['rates_after'][1]<1

def test_first_tc_equals_td():
 from types import SimpleNamespace
 a,b=Model([1]*5),Model([1]*5);t,u=TCEpisode(5),TDLeafEpisode()
 for value,phi in [(1,[0,1,0,0,0]),(2,[0,2,0,0,0])]:
  r=SimpleNamespace(complete=True,value=value,pv_terminal=False,pv_phi=phi);t.observe(a,r);u.observe(b,r)
 t.finish(a,1);u.finish(b,1);assert a.weights==b.weights
