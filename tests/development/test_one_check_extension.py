"""Independent abstract-tree contracts; these are NOT legal Leaper witnesses."""
from types import SimpleNamespace as NS
from dataclasses import replace
import pytest
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable,BoundType
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits

@pytest.fixture
def tree(monkeypatch):
    scores={'C':7,'E':-10,'L':-5}
    edges={'C':[('e','E')],'E':[('r','L')]}
    checked={'C'}; qvisited=[]
    def state(name):return NS(name=name,terminal_status=NS(is_terminal=False),position=NS(side_to_move=0),ply_count=0)
    monkeypatch.setattr(S,'semantic_engine_for',lambda c:None)
    monkeypatch.setattr(S,'is_in_check',lambda pos,side,c:pos.name in checked)
    def node(name):
        n=state(name);n.position.name=name;return n
    monkeypatch.setattr(S,'legal_successors',lambda n,c:[(a,node(ch)) for a,ch in edges.get(n.name,[])])
    monkeypatch.setattr(S,'_declaration_options',lambda *a:[])
    monkeypatch.setattr(S,'_tt_key',lambda n,c:('FULL_HISTORY_AND_CLOCK',n.name))
    def q(n,a,b,p,qd,ctx):ctx.stats.qnodes+=1;qvisited.append(n.name);return scores.get(n.name,0)
    monkeypatch.setattr(S,'quiescence',q)
    def ctx(tt=None,pvs=False):
        return S._Context(NS(),NS(evaluate=lambda n:scores.get(n.name,0)),tt if tt is not None else TranspositionTable(),SearchStatistics(),S._Budget(SearchLimits(max_nodes=10000),None),SearchTuning(use_one_check_extension=True,use_pvs=pvs),True,False,4,8,None)
    return NS(scores=scores,edges=edges,checked=checked,qvisited=qvisited,node=node,ctx=ctx)

def test_positive_d1_extends_to_quiet_opponent_response_but_d0_does_not(tree):
    a=tree.ctx();assert S.negamax(tree.node('C'),1,-S.INF,S.INF,0,a,remaining_extensions=0).score==10
    assert tree.qvisited==['E'];tree.qvisited.clear()
    b=tree.ctx();r=S.negamax(tree.node('C'),1,-S.INF,S.INF,0,b,remaining_extensions=1)
    assert r.score==-5 and r.pv==('e','r') and tree.qvisited==['L']
    assert b.stats.main_check_extensions==1 and b.stats.main_extension_max_path==1 and b.stats.main_search_max_ply==2
    for e in (0,1):
        c=tree.ctx();assert S.negamax(tree.node('C'),0,-S.INF,S.INF,0,c,remaining_extensions=e).score==7
        assert c.stats.main_check_extensions==0

@pytest.mark.parametrize('warm_e',[0,1])
@pytest.mark.parametrize('window',[(-S.INF,S.INF),(-20,0),(0,20)])
def test_cross_bank_exact_and_bound_warmup_cannot_poison_other_policy(tree,warm_e,window):
    shared=TranspositionTable();warm=tree.ctx(shared)
    S.negamax(tree.node('C'),1,*window,0,warm,remaining_extensions=warm_e)
    other=1-warm_e;hot=tree.ctx(shared);cold=tree.ctx();no=tree.ctx();no.use_tt=False
    values=[S.negamax(tree.node('C'),1,-S.INF,S.INF,0,c,remaining_extensions=other).score for c in (hot,cold,no)]
    assert values==[10 if other==0 else -5]*3
    keys=list(shared._data);assert any(k[1]==0 for k in keys) and any(k[1]==1 for k in keys)
    assert all(k[0]=='main-check-extension/v1' for k in keys)
    assert all(e.depth==1 for e in shared._data.values()) # nominal, not d+extension

def test_one_extension_per_path_not_one_shared_global_credit(tree):
    tree.edges.update(R=[('a','C'),('b','D')],D=[('e2','E2')],E2=[('r2','L2')])
    tree.scores.update(E2=20,L2=-20);tree.checked.add('D')
    for pvs in (False,True):
        c=tree.ctx(pvs=pvs);r=S.negamax(tree.node('R'),2,-S.INF,S.INF,0,c)
        assert c.stats.main_extension_max_path==1 and c.stats.main_check_extensions>=2
        assert r.score==20 and r.best_action=='b'
        if pvs:assert c.stats.pvs_null_window_searches>0 and c.stats.pvs_researches>0
    chain=tree.ctx();tree.checked.update(('E','L'));tree.edges['L']=[('s','M')];tree.scores['M']=3
    S.negamax(tree.node('C'),2,-S.INF,S.INF,0,chain)
    assert chain.stats.main_check_extensions==1 and chain.stats.main_extension_max_path==1

def test_terminal_and_winning_declaration_precede_extension(tree,monkeypatch):
    c=tree.ctx();n=tree.node('C');n.terminal_status=NS(is_terminal=True,winner=0)
    assert S.negamax(n,3,-S.INF,S.INF,0,c).score==S.MATE_SCORE
    assert c.stats.main_check_extensions==0
    win=NS(outcome='WIN');monkeypatch.setattr(S,'_declaration_options',lambda *a:[win]);d=tree.ctx()
    assert S.negamax(tree.node('C'),3,-S.INF,S.INF,0,d).declaration is win
    assert d.stats.main_check_extensions==0

def test_default_off_keeps_plain_tt_keys_and_tree(tree):
    c=tree.ctx();c.tuning=SearchTuning();r=S.negamax(tree.node('C'),1,-S.INF,S.INF,0,c)
    assert r.score==10 and all(k[0]=='FULL_HISTORY_AND_CLOCK' for k in c.tt._data)
    assert c.stats.main_check_extensions==c.stats.main_search_max_ply==0


def test_existing_positional_tuning_argument_is_still_pvs():
    assert SearchTuning(True).use_pvs is True
    assert SearchTuning(True).use_one_check_extension is False


def test_aspiration_research_resets_root_path_bank_and_tt_return_not_new_extension(tree):
    cold=tree.ctx();r=S.negamax(tree.node('C'),1,-S.INF,S.INF,0,cold)
    warm=tree.ctx(cold.tt);again=S.negamax(tree.node('C'),1,-S.INF,S.INF,0,warm)
    assert again.score==r.score and warm.stats.main_check_extensions==0
    c=tree.ctx();c.tuning=replace(c.tuning,use_aspiration=True,aspiration_delta=1)
    got=S._aspiration_iteration(tree.node('C'),1,100,c)
    assert got.score==-5 and c.stats.aspiration_researches>0 and c.stats.main_extension_max_path<=1


def test_disabled_hot_path_never_calls_extension_helpers(tree,monkeypatch):
    ctx=tree.ctx();ctx.tuning=SearchTuning()
    def forbidden(*a,**kw):pytest.fail('disabled policy must not enter extension helpers')
    for name in ('_extension_bank','_check_extension_delta','_policy_tt_key'):monkeypatch.setattr(S,name,forbidden)
    assert S.negamax(tree.node('C'),1,-S.INF,S.INF,0,ctx).score==10
