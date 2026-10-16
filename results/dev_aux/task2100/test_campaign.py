from results.dev_aux.task2100.campaign import selector,reuse_role

def test_flat_training_retains_both_distinct_starts():
 grid=[.25,.5,1.,2.,4.];rows=[dict(ratio=r,score=0)for r in grid]
 assert selector(rows,.25,grid)['selected']==.25
 assert selector(rows,4.,grid)['selected']==4.

def test_strict_local_hill_is_not_development_or_global_picker():
 grid=[.25,.5,1.,2.,4.];scores=[0,1,0,2,1];rows=[dict(ratio=r,score=s)for r,s in zip(grid,scores)]
 assert selector(rows,.25,grid)['trace']==[.25,.5]
 assert selector(rows,4.,grid)['trace']==[4.,2.]

def test_reused_physical_record_role_sign_and_unknown():
 for outcome,winner,expected in [('WIN',0,-1),('DRAW',None,0),('UNKNOWN',None,None)]:
  old=dict(logical_slot=0,result=dict(winner=winner),outcome=outcome,physical_id=7,record={'exact':'preserved'})
  row=reuse_role(old,1,1)
  assert row['score']==expected and row['physical_id']==7 and row['reused_from']==0 and row['record']==old['record']
  assert old['logical_slot']==0 and 'reused_from'not in old
