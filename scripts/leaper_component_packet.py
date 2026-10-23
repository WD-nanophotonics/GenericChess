"""Data-only reader for the component-history/policy evidence packet.

No capsule imports, source execution, Player queries or candidate search.
"""
import argparse,gzip,hashlib,json,time
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_component_paths import replay,neighbours
from scripts.leaper_rule_coordinates import physical_action
from scripts.leaper_component_qualify import analyze,qualify_game
from tools.local_agent.common import write_json

def read(packet,manifest,output):
    tick=time.perf_counter();m=L.load(manifest);assert L.sha(packet)==m['packet_sha256']
    raw=json.loads(gzip.decompress(packet.read_bytes()));docs=raw['documents_utf8'];assert set(docs)==set(m['documents'])
    for key,text in docs.items():
        b=text.encode('utf-8');assert len(b)==m['documents'][key]['bytes'] and hashlib.sha256(b).hexdigest()==m['documents'][key]['sha256']
    load=lambda k:json.loads(docs[k]);inputs=load('inputs.json');reg=load('registration.json')
    assert hashlib.sha256(docs['inputs.json'].encode()).hexdigest()==reg['input_sha256']
    result=analyze(reg,inputs['worlds'][1],load('forward/results.json'),lambda name:load('forward/'+name))
    candidate=load('cooperation/result.json');proof=replay(inputs['worlds'][1],[tuple(a)for a in candidate['path']]);stored=load('cooperation/replay.json')
    assert proof==stored and proof['plies']==11
    pilot={p:qualify_game(inputs['worlds'][1],load('pilot/'+p+'.json'))for p in ('UNIT65536','UNIT512','FLOOR')}
    fronts=[]
    for prefix,bits,key in [('bilateral',(0,1,3,4),'coefficients_on_base4'),('defender_quantity',(0,2,3,4),'coefficients_on_base2')]:
        group=load(prefix+'/returns.json')['rows'];closed=load(prefix+'/result.json')
        assert len(group)==16 and closed['status']=='PASS' and {r['subset']for r in group}==set(range(16))
        f={r['subset']:r['width2']for r in group};coeff={}
        for mask in range(16):
            value=sum((-1)**(mask.bit_count()-t.bit_count())*f[t]for t in range(16)if t&mask==t)
            if value:coeff[','.join(str(bits[j])for j in range(4)if mask>>j&1)]=value
        assert coeff==closed[key]
        assert sum(f.values())==closed['Core_second_edges']
        fronts.extend(group)
    count=0
    for row in fronts:
        n=row['rule']['board_size'];c=L.compile_rule(L.ruleset_from_dict(row['rule']));ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(row['initial_record'])))
        assert L.record_value(ss.state)==row['full_initial_state']
        first={physical_action(L.record_value(a),n):(a,ch)for a,ch in L.legal_successors(ss.state,c)}
        assert len(first)==row['root_branch'] and len(row['first'])==row['root_branch']
        assert set(first)=={physical_action(a['action'],n)for a in row['first']}
        width=0
        for a in row['first']:
            _,ch=first[physical_action(a['action'],n)];assert L.record_value(ch)==a['state']
            second=[] if ch.terminal_status.is_terminal else L.legal_successors(ch,c)
            width+=len(second)
            expect={physical_action(z['action'],n):z for z in a['second']};assert len(second)==len(expect)
            for b,cc in second:
                z=expect[physical_action(L.record_value(b),n)];assert L.state_sha(cc)==z['state_sha256'] and L.record_value(cc.terminal_status)==z['terminal'];count+=1
        assert width==row['width2']
    assert count==3632
    next_data=load('next/results.json');next_inputs=load('next/inputs.json');next_pvs=0
    for query in next_data['rows']:
        world=next(w for w in next_inputs['worlds']if w['seed']==query['seed'])
        root=next(r for r in world['roots']if r['target']==query['prefix'])
        c=L.compile_rule(L.ruleset_from_dict(world['rule']));ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(root['record'])))
        decision=query['decision'];assert decision['action'] in [L.record_value(a)for a in ss.legal_actions()]
        for a in decision['principal_variation']:ss.submit(L.match_action(ss,a));next_pvs+=1
    assert len(next_data['rows'])==2 and not next_data['missing_slots'] and not next_data['failures']
    out=dict(status='PASS',documents=len(docs),forward=result,cooperative_path_plies=proof['plies'],quantity_Core_second_edges=count,pilot_games=len(pilot),next_default_calls=2,next_default_PV_plies=next_pvs,seconds=time.perf_counter()-tick,Player_queries_issued=0,source_capsules_executed=0,scope='Exact original byte checks and full Core/RNG/FLOOR/PV replay, shared Core not independent WDL engine. Capsule strings are data only.')
    write_json(output,out);return out

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--packet',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();r=read(a.packet,a.manifest,a.output);print(json.dumps({k:v for k,v in r.items()if k!='forward'}))
