"""Posthoc full-history truth/credit attribution on CLOSED learning episodes.

Truth never chooses an experience root or enters a TD target. Strategic DRAW
is minimax safety, not zero expected payoff versus Uniform. Only a complete
no-mate closure is universal DRAW under every continuation in this scope.
"""
from pathlib import Path
from collections import Counter,defaultdict
from copy import copy
from math import tanh
import argparse,gzip,json,time,hashlib
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import restore,write
from scripts.leaper_cooperative_certificate import encode_position,decode_position
from generic_chess.core.identity import repetition_identity_key


def tables(group,c,graphs,receipts):
    lookup={};positive_keys={};proofs=[]
    for domain,swap,path,receipt_path in receipts:
        g=graphs[domain];receipt=json.loads(receipt_path.read_bytes())
        if {w for w in g['terminals'].values()if w is not None}-{0}:raise ValueError('clock/rank lift requires the admitted single winning seat')
        if not receipt['verified']or receipt['sha256']!=L.sha(path):raise ValueError('unqualified truth source')
        if receipt.get('target_fingerprint',c.ruleset_fingerprint)!=c.ruleset_fingerprint or receipt.get('owner_swap',False)!=swap:raise ValueError('target rule/owner qualification differs')
        raw=g['positions'];translation=str.maketrans('0123456','0456123')
        if swap:raw=[[1-p[0],p[1].translate(translation)]for p in raw]
        values=g['relative_values'];ranks=g['ranks'];seen=set();positive={}
        for i,r in enumerate(raw):
            p=decode_position(r,c.initial_position);key=repetition_identity_key(p,c)
            if key in seen:raise ValueError('noninjective repetition identities')
            seen.add(key);v=values[str(i)]*(1 if r[0]==0 else-1);rank=ranks.get(str(i))
            if v:positive[key]=(rank,v)
            encoded=(r[0],r[1]);entry=(v,rank,receipt['universal_draw'],len(proofs))
            if encoded in lookup and lookup[encoded][0]!=v:raise ValueError('overlapping complete proofs disagree')
            if encoded not in lookup or receipt['universal_draw']:lookup[encoded]=entry
        positive_keys[len(proofs)]=positive;proofs.append(dict(group=group,domain=domain,swapped=swap,vertices=len(raw),injective_keys=len(seen),receipt_sha256=L.sha(receipt_path),graph_sha256=L.sha(path)))
    return lookup,positive_keys,proofs


def classify(s,c,lookup,positive_keys):
    if s.state.terminal_status.is_terminal:return (0 if s.result.winner is None else 1 if s.result.winner==0 else-1),'actual_terminal'
    encoded=encode_position(s.state.position,c.initial_position);entry=lookup.get((encoded[0],encoded[1]))
    if entry is None:return None,'outside_qualified_domain'
    value,rank,universal,proof=entry
    if value==0:return 0,'universal_DRAW'if universal else'strategic_DRAW_safety'
    # Every decisive terminal in these qualified AB/bare-K domains belongs
    # to the same seat. Independent finite-horizon Bellman verification binds
    # the complete rank cutoff: if even the no-repeat-stop game cannot force
    # that seat's win before the clock, adding draw stops cannot create it.
    if rank>64-s.state.ply_count:return 0,'clock_cutoff_DRAW'
    # The strictly decreasing future rank cannot revisit this or any higher
    # rank. Outside-domain keys cannot be future arrivals by closure. Lower
    # count3 barriers need a separate strategy check and remain UNKNOWN here.
    for key,count in s.state.repetition_counts:
        if count>=3 and key in positive_keys[proof]:
            previous_rank,previous_value=positive_keys[proof][key]
            if previous_value==value and previous_rank<rank:return None,'lower_rank_history_barrier'
    return value,'rank_clock_history_'+('WIN0'if value==1 else'WIN1')


def run(directory,domain_directory,proof_directory,output):
    began=time.perf_counter();cfg=json.loads((directory/'plan.json').read_bytes());result=json.loads((directory/'result.json').read_bytes());graphs={i:json.loads(gzip.decompress((domain_directory/f'domain-{i}.json.gz').read_bytes()))for i in range(3)};rows=[];proofs=[];unique=defaultdict(lambda:defaultdict(set))
    clock=json.loads((proof_directory/'clock-rank-dp.json').read_bytes())
    if not clock['verified']or clock['graph_sha256']!=L.sha(domain_directory/'domain-0.json.gz'):raise ValueError('independent complete clock/rank DP missing')
    for group,world in cfg['worlds'].items():
        c=L.compile_rule(L.ruleset_from_dict(world['rule']));paths=[]
        for i in range(3):
            name=f'domain-{i}-verification.json'if group=='contact'else f'quiet-domain-{i}-verification.json'
            paths.append((i,False,domain_directory/f'domain-{i}.json.gz',proof_directory/name))
        name='swapped-contact-domain-0-verification.json'if group=='contact'else'swapped-quiet-domain-0-verification.json'
        paths.append((0,True,domain_directory/'domain-0.json.gz',proof_directory/name))
        lookup,key_ranks,qualified=tables(group,c,graphs,paths);proofs+=qualified
        for entry in result['rows']:
            slot=entry['slot']
            if slot['group']!=group:continue
            row=json.loads((directory/f"game-{slot['id']:03d}.json").read_bytes());s=restore(c,world['roots'][slot['root']]['record']);events={e['state_sha256']:e for e in row['events']if e['kind']=='candidate'};counts=Counter();own=[];examples={}
            for action in L.deserialize_game_record(json.dumps(row['final_record'])).actions:
                event=events.get(L.state_sha(s.state))
                if event is not None:
                    r=event['receipt'];root_value,root_basis=classify(s,c,lookup,key_ranks);counts['root_'+root_basis]+=1
                    cohort=str((group,slot['phase'],slot['arm']));hid=L.state_sha(s.state)
                    if root_value is not None:
                        unique[cohort]['known_full_histories'].add(hid);unique[cohort]['known_physical_positions'].add(repetition_identity_key(s.state.position,c))
                        if root_value*(1 if s.state.position.side_to_move==0 else-1)==1:
                            counts['available_forced_WIN']+=1;unique[cohort]['available_WIN_histories'].add(hid)
                    child_values=[];chosen=None
                    for a in s.legal_actions():
                        ch=copy(s);ch.submit(a);v,b=classify(ch,c,lookup,key_ranks);child_values.append(v)
                        if a==action:chosen=v
                    if root_value is not None and all(v is not None for v in child_values):
                        optimum=(max if s.state.position.side_to_move==0 else min)(child_values)
                        if optimum!=root_value:raise ValueError('actual history truth Bellman relation differs')
                        fork=len(set(child_values))>1;bad=chosen!=root_value
                        counts['complete_known_frontiers']+=1;counts['forced_WDL_forks']+=int(fork)
                        counts['chosen_forced_WDL_suboptimal']+=int(bad)
                        if fork:unique[cohort]['fork_full_histories'].add(hid)
                        if bad:unique[cohort]['suboptimal_full_histories'].add(hid)
                    if r['complete']:
                        leaf=copy(s)
                        for choice in r['pv_choices']:leaf.submit(L.match_action(leaf,choice['action']))
                        leaf_value,leaf_basis=classify(leaf,c,lookup,key_ranks);counts['PV_'+leaf_basis]+=1
                        active=not r['pv_terminal']and r['pv_phi'][1]!=0
                        if active:counts['active_B_PV_'+leaf_basis]+=1
                        own.append(r)
                        if active and leaf_basis not in examples:examples[leaf_basis]=dict(ply=s.state.ply_count,state_sha256=L.state_sha(s.state),PV=r['pv_choices'],phi=r['pv_phi'],forced_value=leaf_value)
                s.submit(action)
            credit=defaultdict(float);credit_terms=Counter();elig=[0.]*4;predictions=[tanh(r['value']/10)for r in own]
            if slot['phase']=='train':
                for i,r in enumerate(own):
                    target=predictions[i+1]if i+1<len(own)else row['result']['outcome']
                    if target is None:break
                    pred=predictions[i];grad=[0.]*4 if r['pv_terminal']else[x*(1-pred*pred)/10 for x in r['pv_phi']];grad[0]=0.;elig=[.95*a+b for a,b in zip(elig,grad)]
                    kind='actual_final_target'if i+1==len(own)else'next_literal_search_terminal'if own[i+1]['pv_terminal']else'next_material_search'
                    delta=.05*(target-pred)*elig[1];credit[kind]+=delta;credit_terms[kind]+=1
                if abs(sum(credit.values())-(row['after'][1]-row['before'][1]))>1e-12:raise ValueError('B credit attribution does not sum to actual update')
            rows.append(dict(slot=slot,counts=dict(counts),B_update_by_target_kind=dict(credit),target_kind_terms=dict(credit_terms),examples=examples))
    distinct={cohort:{name:dict(count=len(values),sha256=hashlib.sha256(json.dumps(sorted(values),separators=(',',':')).encode()).hexdigest())for name,values in groups.items()}for cohort,groups in unique.items()}
    out=dict(verified=True,rows=rows,proofs=proofs,distinct_actual_contexts=distinct,clock_proof_sha256=L.sha(proof_directory/'clock-rank-dp.json'),seconds=time.perf_counter()-began,
        scope='POSTHOC actual committed learning/evaluation histories only. Forced-WDL and universal deadzone distinctions do not replace Uniform-opponent expected return. No oracle targets/start filtering or new Player calls; unqualified rosters/history barriers stay UNKNOWN.')
    write(output,out);return out


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--domain-directory',type=Path,required=True);ap.add_argument('--proof-directory',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();run(a.directory,a.domain_directory,a.proof_directory,a.output)
