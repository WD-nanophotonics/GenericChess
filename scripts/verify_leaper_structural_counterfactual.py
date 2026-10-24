"""Reproduce the published structural join and literal witnesses; no solver."""
from pathlib import Path
from collections import Counter
import argparse,gzip,hashlib,json,time
from scripts import leaper_design as L
from scripts.leaper_structural_counterfactual import analyze,documents
from scripts.leaper_absorption_witness import analyze as witnesses
from tools.local_agent.common import write_json

def verify(directory,output):
    assert not output.exists();tick=time.perf_counter();m=L.load(directory/'manifest.json');d={}
    for name,meta in m['files'].items():
        raw=(directory/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==meta['sha256'];body=gzip.decompress(raw)if name.endswith('.gz')else raw;assert hashlib.sha256(body).hexdigest()==meta['decoded_sha256'];d[name]=json.loads(body)
    for name,sha in m['maintained_source_LF_sha256'].items():assert hashlib.sha256(Path(name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==sha
    primary=Path('docs/research/data/leaper_forward_width_20261024');r=analyze(documents(primary/'screen-evidence.json.gz',primary/'screen-manifest.json'),d['roots.json.gz'],d['costs.json.gz']);old=d['paired.json.gz']
    for key in r:
        if key!='seconds':assert r[key]==old[key],key
    w=witnesses(d['roots.json.gz'],r);saved=d['absorption.json.gz']
    for key in w:assert w[key]==saved[key],key
    same=[x for x in r['rows']if x['H']==64 and x['static_capacity'][0]==x['static_capacity'][1]];s=d['summary.json'];assert s['paired_rows']==len(r['rows'])and s['same_capacity_H64_rows']==len(same)and s['same_capacity_H64_shared_revaluation_roots']==sum(bool(x['shared_value_mechanisms'])for x in same)
    mechanism=Counter(str((tuple(z['values']),tuple(z['immediate_terminals'])))for x in same for z in x['shared_value_mechanisms']);assert dict(mechanism)==s['shared_action_occurrence_mechanisms']
    assert s['same_capacity_fork_change_roots']==sum(x['fork'][0]!=x['fork'][1]for x in same)and s['fork_change_with_shared_revaluation']==sum(x['fork'][0]!=x['fork'][1]and bool(x['shared_value_mechanisms'])for x in same)
    assert s['added_drawing_actions']==w['added_draw_actions']and s['added_draw_legal_capture_A_reply']==sum(bool(x['capture_A_defense_indices'])for x in w['added_draw_witnesses'])
    next_input=d['next-H6.json.gz'];cs={f['family']:L.compile_rule(L.ruleset_from_dict(f['rule']))for f in next_input['families']};next_roots=0
    for pair in next_input['roots']:
        boards=[]
        for row in pair['roots']:
            c=cs[row['family']];ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(row['record'])));assert ss.state.ply_count==0 and not ss.state.terminal_status.is_terminal and L.state_sha(ss.state)==row['state_sha256'];assert L.record_value(ss.legal_actions())==row['legal_actions'];boards.append(ss.state.position.board);next_roots+=1
        assert boards[0]==boards[1]
    assert next_roots==next_input['Core_initial_replays']==256 and next_input['new_Player_queries']==next_input['new_solver_calls']==0
    out=dict(status='PASS',paired_rows=len(r['rows']),Core_roots=r['Core_roots'],Core_oneply_edges=r['Core_oneply_edges'],source_cost_rows=r['source_cost_rows'],shared_revaluation_action_occurrences=w['shared_revaluation_action_occurrences'],added_draw_actions=w['added_draw_actions'],scoring_reference_and_new_children=2*w['new_scoring_rule_children'],prepared_next_Core_roots=next_roots,new_Player_queries=0,new_solver_calls=0,source_capsule_executions=0,seconds=time.perf_counter()-tick,scope=r['scope']);write_json(output,out);print('PASS',out);return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.directory,a.output)
