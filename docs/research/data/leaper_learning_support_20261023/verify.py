"""Read-only full history/PV/TD arithmetic check,no Player calls."""
import sys,json,math,time,gzip,hashlib,itertools,importlib.util
from dataclasses import replace
from collections import deque
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from scripts.leaper_design import compile_rule,ruleset_from_dict,GameSession,state_sha
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model
from generic_chess.core.actions import action_to_dict
BASE=Path(__file__).resolve().parent
blob=(BASE/'evidence.json.gz').read_bytes();packet=json.loads(gzip.decompress(blob))
assert packet['format']=='GenericChess-AUX-learning-support-v1'
cohort=packet['cohort'];pilot=packet['pilot'];worlds=[cohort['episodes'][2*i]for i in range(8)];compiled={fp:compile_rule(ruleset_from_dict(r))for fp,r in packet['rules'].items()};assert all(c.ruleset_fingerprint==fp for fp,c in compiled.items());counts=Counter();began=time.perf_counter();checks=[];chain={};epochs=Counter()
def push(env,raw):
 assert raw['kind']=='ACTION'and raw['declaration_id']is None
 choices=[x for x in env.actions()if x.kind=='ACTION'and action_to_dict(x.action)==raw['action']];assert len(choices)==1;env.push(choices[0])
def verify(d,w,training):
 c=compiled[w['fingerprint']];env=FixedScaleSessionEnv(GameSession.replay(c,deserialize_game_record(json.dumps(w['initial_record']))),unit_type='A');model=Model(d['models_before']);foe=Model(d['foe']);rows=[]
 for q in d['queries']:
  assert state_sha(env.session.state)==q['state_sha256']and q['actor']==env.player();m=model if q['actor']==d['learner_color']else foe
  assert q['usable'] # actual census assertion,doesnotdefine consumer
  leaf=FixedScaleSessionEnv(env.session,unit_type='A')
  for raw in q['PV']:push(leaf,raw);counts['pv_edges']+=1
  t=leaf.terminal()
  if q['pv_terminal']:assert t is not None and q['value']==1000000*t and q['pv_phi']is None;grad=[0.]*len(m.weights)
  else:assert t is None and tuple(q['pv_phi'])==leaf.features()and math.isclose(q['value'],m.raw(leaf.features()),abs_tol=1e-10);grad=list(m.gradient(leaf.features()))
  assert grad==q['gradient']and q['PV'][0]==q['action'];assert q['completed_depth']==4
  if q['actor']==d['learner_color']:rows.append((math.tanh(q['value']/10),grad))
  push(env,q['action']);counts['queries']+=1;counts['nodes']+=q['nodes']
 assert env.record()==d['final_record']and state_sha(env.session.state)==d['final_state_sha256'];env.replay();assert env.terminal()==d['result']['outcome'];assert sum(q['nodes']for q in d['queries'])==d['result']['nodes'];assert len(d['queries'])==d['result']['queries']
 delta=[0.]*len(model.weights);elig=delta[:];loss=terminal=0.;terms=0
 if training:
  for i,(pred,grad)in enumerate(rows):
   target=rows[i+1][0]if i+1<len(rows)else env.terminal()
   if target is None:break
   elig=[.95*e+g for e,g in zip(elig,grad)];error=target-pred;loss+=error*error/2;terms+=1;delta=[x+error*e for x,e in zip(delta,elig)]
   if i+1==len(rows):terminal=sum(abs(error*e)for e in elig)
  stats=d['result']['update'];assert stats['samples']==terms and stats['observed_searches']==len(rows)and stats['changed']==any(delta)
  assert math.isclose(stats['loss'],loss/max(1,terms),abs_tol=1e-13)and math.isclose(stats['terminal_credit_l1'],terminal,abs_tol=1e-13)
  counts['training']+=1;counts['changed']+=stats['changed'];counts['terminal_credit_nonzero']+=terminal!=0
 else:assert d['result']['update']is None
 after=[v+.05*x for v,x in zip(model.weights,delta)];after[0]=1.;assert all(math.isclose(a,b,abs_tol=1e-13)for a,b in zip(after,d['models_after']))
 counts['episodes']+=1
 return dict(outcome=env.terminal(),terminal=env.session.result.status.value,queries=len(d['queries']),nodes=d['result']['nodes'])
for slot in range(304):
 d=pilot['episodes'][slot];assert d['slot']==slot;w=worlds[d['world']];assert d['fingerprint']==w['fingerprint'];k=d['world'],d['init'];training=d['phase']=='train'
 if training:
  before=chain.get(k,w['models_before'][0 if d['init']=='unit'else 1]);assert d['models_before']==before;assert d['epoch']==epochs[k]+1;assert d['learner_color']==epochs[k]%2
  chain[k]=d['models_after'];epochs[k]+=1
 if d['phase']=='eval':assert epochs[k]==16 and d['models_before']==chain[k]
 r=verify(d,w,training);checks.append(dict(slot=slot,**r))
 assert d['foe']==w['models_before'][1]
assert len(epochs)==16 and all(v==16 for v in epochs.values())
for slot in range(16):
 old=cohort['episodes'][slot];d=dict(old,models_before=old['models_before'][0],models_after=old['models_after'][0],foe=old['models_before'][1]);verify(d,worlds[slot//2],False)
episode_counts=dict(counts)
print('EPISODES',json.dumps(episode_counts),flush=True)
from generic_chess.core.pieces import Piece
from generic_chess.core.attacks import is_in_check
from generic_chess.core.transition import legal_successors
from scripts.leaper_retrograde import fresh_state
from scripts.research_record import record_value

def physical(p,name):
    k0=next(i for i,x in enumerate(p.board)if x and x.current_type_id=='K'and x.owner==0)
    k1=next(i for i,x in enumerate(p.board)if x and x.current_type_id=='K'and x.owner==1)
    xs=[(i,x.owner)for i,x in enumerate(p.board)if x and x.current_type_id==name]
    assert len(xs)<=1 and all(x is None or x.current_type_id in ('K',name)for x in p.board)
    return k0,k1,-1 if not xs else xs[0][1],-1 if not xs else xs[0][0],p.side_to_move

support_maps={};support_terminals={};support_counts=Counter()
for cert in packet['support_certificates']:
    width,mask,name,fp=cert['width'],cert['mask'],cert['type'],cert['fingerprint'];c=compiled[fp];raw=packet['rules'][fp]
    assert raw['board_size']==width and raw['capture_disposition']=='remove_from_game'
    assert not raw.get('promotion_allowed')and not raw.get('promotion_forced')
    assert all(not any(m)for masks in raw['drop_allowed'].values()for m in masks)
    assert set(raw)<=set(('board_size','capture_disposition','drop_allowed','initial_position','max_ply','metadata','piece_types','promotion_allowed','promotion_forced','repetition_limit','schema_version','stalemate_result'))
    assert c.repetition_limit==4 and c.repetition_policy=='draw'and c.max_ply==128
    verts=cert['vertices'];index={tuple(v[:5]):i for i,v in enumerate(verts)};assert len(index)==len(verts)
    base=GameSession(c).state.position;n=width*width;positions=[]
    def position(key):
        k0,k1,owner,ix,side=key;b=[None]*n;b[k0]=Piece(0,'K','K');b[k1]=Piece(1,'K','K')
        if owner>=0:b[ix]=Piece(owner,name,name)
        return replace(base,board=tuple(b),side_to_move=side)
    admitted=set()
    for k0,k1 in itertools.permutations(range(n),2):
        for owner,ix in [(-1,-1)]+[(owner,ix)for ix in range(n)if ix not in(k0,k1)for owner in(0,1)]:
            for side in (0,1):
                key=k0,k1,owner,ix,side;p=position(key)
                if not is_in_check(p,1-side,c):admitted.add(key)
    assert admitted==set(index)
    positions=[position(v[:5])for v in verts];edges=[];terminals={};mc={0:Counter(),1:Counter()}
    for i,(p,v)in enumerate(zip(positions,verts)):
        s=fresh_state(p,c);value,rank=v[5:];assert value in(-1,0,1)
        if rank is not None:assert type(rank)is int and 0<=rank<=128
        if s.terminal_status.is_terminal:
            winner=s.terminal_status.winner;terminals[i]=winner;expected=0 if winner is None else 1 if winner==p.side_to_move else-1
            assert value==expected and rank==(0 if expected else None);children=()
        else:
            children=tuple(index[physical(ch.position,name)]for ac,ch in legal_successors(s,c));assert children
            child_values=[verts[j][5]for j in children]
            if value==1:
                losing=[verts[j][6]for j in children if verts[j][5]==-1];assert losing and rank==1+min(losing)
            elif value==-1:assert all(x==1 for x in child_values)and rank==1+max(verts[j][6]for j in children)
            else:assert -1 not in child_values and 0 in child_values and rank is None
        edges.append(children);owner=v[2];m=mc[int(owner>=0)];m['states']+=1;m['mate_terminals']+=i in terminals and terminals[i]is not None;m['draw_terminals']+=i in terminals and terminals[i]is None
        if i not in terminals:
            xv=0 if owner<0 else value*(1 if p.side_to_move==owner else-1)
            m['nonterminal']+=1;m['X_win']+=xv==1;m['X_loss']+=xv==-1;m['draw']+=xv==0;m['X_to_move']+=owner==p.side_to_move if owner>=0 else 0
            if xv==1:m['X_turn_win']+=owner==p.side_to_move;m['weak_turn_X_win']+=owner!=p.side_to_move
    # Independent backward reachability of ANY decisive terminal, not a minimax draw test.
    parents=[[]for _ in verts]
    for i,es in enumerate(edges):
        for j in es:parents[j].append(i)
    reachable={i for i,w in terminals.items()if w is not None};pending=deque(reachable)
    while pending:
        for i in parents[pending.popleft()]:
            if i not in reachable:reachable.add(i);pending.append(i)
    for i,v in enumerate(verts):mc[int(v[2]>=0)]['structural_dead']+=i not in reachable
    summary=next(r for r in packet['support'][str(width)]['summary']['results']if r['mask']==mask)
    assert len(verts)==summary['states']and sum(map(len,edges))==summary['edges']
    for material in (0,1):
        want=summary['material_counts'][str(material)]
        assert all(mc[material][k]==v for k,v in want.items())
    support_maps[width,mask]={tuple(v[:5]):v for v in verts};support_terminals[width,mask]={tuple(verts[i][:5]):w for i,w in terminals.items()};support_counts['cases']+=1;support_counts['vertices']+=len(verts);support_counts['edges']+=sum(map(len,edges))
    print('SUPPORT',width,mask,len(verts),flush=True)

inclusion=Counter()
for pair in packet['inclusion']['pairs']:
    before=support_maps[4,pair['mask']];after=support_maps[4,pair['superset']];cnt=Counter()
    for k in set(before)&set(after):
        if k[2]<0:continue
        x,y=before[k],after[k];vx=x[5]*(1 if k[4]==k[2]else-1);vy=y[5]*(1 if k[4]==k[2]else-1);cnt['common']+=1;cnt['improve']+=vx<vy
        if vx>vy:
            cnt['worsen']+=1
            ta=support_terminals[4,pair['mask']];tb=support_terminals[4,pair['superset']]
            cnt['new_stalemate'if k in tb and tb[k]is None else'both_ongoing'if k not in ta and k not in tb else'other']+=1
    assert cnt['common']==pair['counts']['common']and cnt['improve']==pair['counts'].get('improve',0)and cnt['worsen']==pair['counts'].get('worsen',0)
    assert all(cnt[k]==v for k,v in pair['counts'].items())
    inclusion.update(cnt)
assert all(inclusion[k]==packet['inclusion']['totals'][k]for k in('common','improve','worsen'))

spec=importlib.util.spec_from_file_location('argmax_reader',ROOT/'docs/research/data/leaper_argmax_exposure_20261023/verify.py');ar=importlib.util.module_from_spec(spec);spec.loader.exec_module(ar)
from fractions import Fraction as F
argmax_visits=0
for r in pilot['argmax']['rows']:
    c=compiled[r['record']['ruleset_fingerprint']];s=GameSession.replay(c,deserialize_game_record(json.dumps(r['record'])));branches={json.dumps(b['action'],sort_keys=True):b for b in r['branches']};prices=tuple(F(x)for x in r['prices'])
    for ac,ch in legal_successors(s.state,c):
        scores,n=ar.exact_scores(c,ch,3,prices,1);argmax_visits+=n
        assert [str(-v)for v in scores]==branches[json.dumps(action_to_dict(ac),sort_keys=True)]['scores']
    support=[[i for i,b in enumerate(r['branches'])if F(b['scores'][j])==max(F(x['scores'][j])for x in r['branches'])]for j in(0,1)]
    assert support==r['support']and set(support[1])<set(support[0])

natural_bindings=0
for rows in packet['natural5']['labels'].values():
    for r in rows:
        c=compiled[r['record']['ruleset_fingerprint']];s=GameSession.replay(c,deserialize_game_record(json.dumps(r['record'])));assert state_sha(s.state)==r['id']
        expected={json.dumps(action_to_dict(a),sort_keys=True)for a,ch in legal_successors(s.state,c)};assert expected=={json.dumps(b['action'],sort_keys=True)for b in r['branches']}
        assert r['WDL']==max(b['WDL']for b in r['branches']);natural_bindings+=1
for w in packet['natural5']['cooperative']['rows']:
    c=compiled[w['fingerprint']];s=GameSession.replay(c,deserialize_game_record(json.dumps(w['initial_record'])))
    for step in w['extension']:
        assert s.state.position.side_to_move==step['actor'];choices=[a for a in s.legal_actions()if action_to_dict(a)==step['action']];assert len(choices)==1;s.submit(choices[0])
    assert record_value(s.to_record())==w['final_record']and record_value(s.state)==w['final_state']and record_value(s.result)==w['final_result']
    assert s.result.status.value=='checkmate'and sum(x is not None for x in s.state.position.board)==4
from scripts.generic_session_certificate_json import decode_session_certificate
from scripts.generic_session_win_proof import verify_session_certificate
positive=positive_nodes=0
for r in packet['natural5']['positive_bounds']['results']:
    if not r.get('verification',{}).get('verified'):continue
    payload=r['certificate'];s,cert=decode_session_certificate(compiled[payload['ruleset_fingerprint']],payload,max_nodes=30000)
    check=verify_session_certificate(s,cert,max_nodes=30000,seconds=30);assert check['verified'];positive+=1;positive_nodes+=check['nodes']
assert positive==packet['natural5']['positive_bounds']['summary']['verified_positive']
receipt=dict(status='PASS',sha256=hashlib.sha256(blob).hexdigest(),scope='SharedCore;all320episode/PV/TD checks,36globalKXsolvedcertificates via independent Bellman/ranks andactualCore closure. Natural4actor graph labels checked for fullroot/action binding ONLY,notindependentWDLproof;separatepositiveSessioncertificatesverified. Cooperativeextensions verified,not forcedwins from theirDRAWroots.',episode_counts=episode_counts,support=dict(support_counts),inclusion=dict(inclusion),argmax_visits=argmax_visits,natural4_root_bindings=natural_bindings,positive_session_certificates=positive,positive_certificate_nodes=positive_nodes,seconds=time.perf_counter()-began)
(BASE/'verification.json').write_text(json.dumps(receipt,indent=2));print('FINAL',json.dumps(receipt),flush=True)
