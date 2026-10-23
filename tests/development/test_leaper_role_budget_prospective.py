from scripts import leaper_design as L
from scripts.leaper_role_budget_prospective import analyze


def test_prospective_cost_uses_total_main_plus_q_budget(tmp_path):
    # SearchLimits explicitly counts nodes+qnodes. Main-only would pass3/4;
    # the actual total below fails, so this checks a scientific decision boundary.
    worlds={'worlds':[{'world':0,'code_world':0,'placement_index':0,'prefix_index':0,'initial_terminal':{'status':'ongoing'}}]}
    L.write_record(tmp_path/'inputs.json',worlds)
    slots=[]
    for pair,main,q,utility in [('LL',10,5,[0,0]),('HL',20,0,[0,0]),('LH',20,5,[-1,-1])]:
        fn=pair+'.json';L.write_record(tmp_path/fn,{'queries':[{'actor':0,'decision':{'nodes':main,'qnodes':q}}],'seconds':1})
        slots.append({'world':0,'pair':pair,'status':'finished','utility':utility,'receipt':fn})
    L.write_record(tmp_path/'results.json',{'status':'CLOSED','slots':slots})
    L.write_record(tmp_path/'prospective-plan-before-prefix-generation.json',{'min_adaptive_minus_high':'-1/48','min_adaptive_minus_low':'1/24','max_node_ratio':'3/4'})
    analyze(tmp_path);a=L.load(tmp_path/'assessment.json')
    assert a['derived_serving_cost']['nodes']['adaptive']==40
    assert a['derived_serving_cost']['nodes']['always_high']==45
    assert not a['hypothesis_supported']
    assert a['rows'][0]['costs']['LL']['qnodes']==5
