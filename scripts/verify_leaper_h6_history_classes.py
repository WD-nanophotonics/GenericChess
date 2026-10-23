"""Full public-Session replay of the fixed H6 visited-set equivalence classes.

Only the exact admitted H6/repeat2 templates are supported. One actual full
source prefix represents each (Position,remaining,prior-visited-set) class;
the complete rule admission makes order irrelevant in precisely this scope.
No source Position domain is expanded and no Player or training is called.
"""
from collections import Counter,deque
from copy import copy
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import argparse,hashlib,json,time
from scripts.leaper_explorer_truth import load,digest
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_h6_headroom import evaluate
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_microgames import role_stop_requested
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.core.transition import legal_successors
from generic_chess.core.actions import action_to_dict
from generic_chess.learning.incremental import FixedScaleSessionEnv,MATE


def verify(directory,output,*,seconds=900):
    directory=Path(directory);output=Path(output);output.mkdir(exist_ok=False);tick=time.perf_counter()
    inputs=load(directory/'inputs.json.gz');source=load(directory/'truth.json.gz');adj=load(directory/'adjacent-pairs.json.gz');src={r['id']:r for r in source['roots']}
    plan=dict(question='Does each fixed-mu H6 history class preserve actual Session legality, terminals, features and nominal headroom?',
        inputs_digest=digest(inputs),truth_digest=digest(source),adjacency_digest=digest(adj),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        caps=dict(seconds=seconds,classes=200000,Core_edges=1200000),
        scope='Oneactuallegalfullprefixperequivalenceclass, all128originalstarts/rule, alllegalchildren. Fixedtemplateadmissionprovesvisited-set/remaining/Positionissufficienthere; notothergeneratedsemantics. IndependentactualSessionterminal/submit/featurechecks,noPlayer/newrules/closureexpansion/training/oldcaprefill.')
    (output/'plan.json').write_text(json.dumps(plan,indent=2));counts=Counter();rows=[]
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds or counts['classes']>=200000 or counts['Core_edges']>=1200000:raise RuntimeError('H6_CLASS_READER_CAP_UNKNOWN_NO_REFILL')
    for pair in adj['pairs']:
      for tag,key in(('left_family','left_id'),('right_family','right_id')):
        family=next(f for f in inputs['families']if f['family']==pair[tag]);first=next(r for r in inputs['rows']if r['family']==family['family']);c=admit(family,first);d=load(directory/f"domain{family['family']}.json.gz")
        receipt=next(r for r in load(directory/'summary.json')['families']if r['family']==family['family'])
        if digest(d)!=receipt['domain_digest']:raise ValueError('frozen domain differs')
        positions=[decode_position(p,c.initial_position)for p in d['positions']];indices={p:i for i,p in enumerate(positions)};terms={int(i):v for i,v in d['terminals'].items()};sides=[p.side_to_move for p in positions]
        features=[]
        for p in positions:features.append((sum(z is not None and(z.owner,z.current_type_id)==(0,'A')for z in p.board),-sum(z is not None and(z.owner,z.current_type_id)==(1,'B')for z in p.board)))
        ended,oldtruth,oldnominal,olddecision,oldcalls=evaluate(d['edges'],terms,sides,features,guard)
        todo=deque();keys=[];ids={};children=[];terminal=[];phis=[];actors=[];frontier=hashlib.sha256();local=Counter()
        def add(s,i,h,prior):
            kk=i,h,prior
            if kk not in ids:
                ids[kk]=len(keys);keys.append(kk);children.append(None);terminal.append(None);phis.append(None);actors.append(s.state.position.side_to_move);todo.append((s,kk))
            return ids[kk]
        for rr in pair['rows']:
            sr=src[rr[key]];s=GameSession.replay(c,deserialize_game_record(json.dumps(sr['record'])));i=indices[s.state.position]
            if s.state.ply_count!=0 or max(n for _,n in s.state.repetition_counts)!=1:raise ValueError('source not fresh')
            if i!=sr['root_index']:raise ValueError('source root differs')
            add(s,i,6,0)
        while todo:
            if counts['classes']%128==0:guard()
            s,(i,h,prior)=todo.popleft();number=ids[i,h,prior]
            if s.state.position!=positions[i]or s.state.ply_count!=6-h:raise ValueError('actual class/clock differs')
            # Fresh public replay independently binds the representative history.
            wire=serialize_game_record(s.to_record())
            decoded=deserialize_game_record(wire)
            if serialize_game_record(decoded)!=wire:raise ValueError('noncanonical full-history JSON roundtrip')
            replay=GameSession.replay(c,decoded);local['record_replays']+=1;local['JSON_record_roundtrips']+=1
            if replay.state!=s.state or replay.result!=s.result:raise ValueError('actual record replay differs')
            is_end=s.result.status.value!='ongoing';expected=ended(i,h,prior)
            if is_end!=expected:raise ValueError('Session/visited-set terminal differs')
            value=None
            if is_end:
                value=0 if s.result.winner is None else 1 if s.result.winner==0 else-1
                if value!=oldtruth(i,h,prior):raise ValueError('literal terminal label differs')
                terminal[number]=value;children[number]=[];phis[number]=None;local['terminal_'+s.result.status.value]+=1
            else:
                phi=FixedScaleSessionEnv(s,unit_type='A').features()
                if list(phi)!=[*features[i],0,0]:raise ValueError('actual material feature differs')
                phis[number]=tuple(phi);ee=[];actual_actions=[];actual_targets=[];pp=prior|1<<i
                for action,ch in legal_successors(s.state,c):
                    if ch.position not in indices:raise ValueError('actual child outside frozen domain')
                    j=indices[ch.position];child=copy(s);child.submit(action)
                    if child.state!=ch:raise ValueError('Session submit/Core successor differs')
                    actual_actions.append(action_to_dict(action));actual_targets.append(j);ee.append(add(child,j,h-1,pp));counts['Core_edges']+=1
                if actual_actions!=d['actions'][i]or actual_targets!=d['edges'][i]:raise ValueError('actual full-history frontier differs')
                children[number]=ee
            frontier.update(json.dumps([number,[i,h,hex(prior)],children[number],value,phis[number]],separators=(',',':')).encode());frontier.update(b'\n')
            counts['classes']+=1;local['classes']+=1
            if counts['classes']%8192==0:print(dict(family=family['family'],**counts,seconds=time.perf_counter()-tick),flush=True)
        values={}
        for number in sorted(range(len(keys)),key=lambda k:keys[k][1]):
            i,h,prior=keys[number]
            if terminal[number]is not None:values[number]=terminal[number]
            else:values[number]=(max if actors[number]==0 else min)(values[j]for j in children[number])
            if values[number]!=oldtruth(i,h,prior):raise ValueError('all-actual class Bellman label differs')
        @lru_cache(None)
        def nominal(number,depth,price):
            if terminal[number]is not None:return MATE*terminal[number]
            if depth==0:return phis[number][0]+price*phis[number][1]
            return(max if actors[number]==0 else min)(nominal(j,depth-1,price)for j in children[number])
        diag=Counter()
        for number,(i,h,prior)in enumerate(keys):
            if terminal[number]is not None or actors[number]!=0:continue
            diag['seat0_ongoing_classes']+=1
            for depth in(1,2,3):
              for price in(F(1,2),F(1),F(2)):
                vals=[nominal(j,depth-1,price)for j in children[number]];best=max(vals);selected=tuple(k for k,x in enumerate(vals)if x==best)
                expected=olddecision(i,h,prior,depth,price)
                if selected!=expected['chosen']:raise ValueError('actual-feature nominal action set differs')
                bad=sum(values[children[number][k]]!=values[number]for k in selected)
                if F(bad,len(selected))!=expected['error']:raise ValueError('actual class nominal quality differs')
                diag[f'D{depth}_B{price}_any_bad_classes']+=bad>0
        rows.append(dict(family=family['family'],counts=dict(local),diagnostic=dict(diag),actual_class_frontier_sha256=frontier.hexdigest()))
        (output/'partial.json').write_text(json.dumps(dict(rows=rows,counts=dict(counts),seconds=time.perf_counter()-tick),indent=2))
    result=dict(verified=True,plan=plan,rows=rows,counts=dict(counts),seconds=time.perf_counter()-tick)
    (output/'result.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(a.directory,a.output);print({k:v for k,v in r.items()if k not in('rows','plan')})
