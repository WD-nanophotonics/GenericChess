"""Verify the scoped E0 publication copy; no Player, learner or H6 solver."""
import argparse,gzip,hashlib,json,itertools,time
from pathlib import Path
from datetime import datetime,timezone
from scripts import leaper_design as L
from scripts.leaper_parity_scope import semantic_qualification,bind_histories
from scripts.leaper_single_entity_scope import qualify_local_packet
from scripts.verify_leaper_h6_e0 import qualify as qualify_h6
from tools.local_agent.common import write_json
from tools.local_agent.slack_transport import save_plugin_original

def recover_original_json(value,expected,path):
    # This is deterministic recovery of byte-exact scientific JSON, NOT a
    # reconstruction of a lost Slack/tool wrapper. Match the saved SHA first.
    for sorted_keys,ascii_text,indent,crlf in itertools.product((True,False),(False,True),(2,None),(False,True)):
        raw=(json.dumps(value,sort_keys=sorted_keys,ensure_ascii=ascii_text,indent=indent)+'\n').encode()
        if crlf:raw=raw.replace(b'\n',b'\r\n')
        if hashlib.sha256(raw).hexdigest()==expected:
            save_plugin_original(path,raw);return path
    raise ValueError('cannot recover claimed original JSON bytes: '+path.name)

def verify(bundle,output):
    assert not output.exists();output.mkdir(parents=True)
    root=Path.cwd().resolve();assert output.resolve().is_relative_to(root/'.local_agent')
    start=datetime.now(timezone.utc).isoformat();tick=time.perf_counter();manifest=L.load(bundle.parent/'manifest.json');raw=bundle.read_bytes();assert hashlib.sha256(raw).hexdigest()==manifest['compressed_sha256'];body=gzip.decompress(raw);assert hashlib.sha256(body).hexdigest()==manifest['decoded_sha256'];p=json.loads(body);assert p['schema']=='genericchess.scope_e0.evidence.v1'
    restored={}
    for key,data in p['files'].items():
        logical=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest();assert logical==p['logical_document_sha256'][key]
        restored[key]=recover_original_json(data,p['original_file_sha256'][key],output/(key+'.json'))
    parity=semantic_qualification(restored['parity_census'],restored['mask_capacity'],output/'parity-reader.json');assert parity['counts']==p['files']['parity_semantic_qualification']['counts']
    old=Path('docs/research/data/leaper_e0_20261023');bound=bind_histories(old/'e0-and-interrupted-panel.json.gz',old/'truth-handoff.json',output/'48-bindings.json',restored['parity_census']);assert bound['counts']==p['files']['structural_48']['counts']
    for actual,expected in zip(bound['rows'],p['files']['structural_48']['rows'],strict=True):
        for key in ('world','mask','state_sha256','full_record','full_rule','status','proposed_cooperative_scoring_reachability','proposed_WDL_for_side_to_move'):assert actual[key]==expected[key]
    singleton=qualify_local_packet(restored['single_entity_local'],restored['single_entity_rule'],output/'single-entity-reader.json')
    h6=qualify_h6(restored['h6'],restored['h6_analysis'],output/'H6-reader.json')
    # The next step's facts must use the same primitive returned children.
    index=p['files']['h6_next_fork_index'];sources={r['state_sha256']:r for r in p['files']['h6']['rows']};forks={True:0,False:0,None:0}
    for r in index['rows']:
        source=sources[r['id']];assert source['fingerprint']==r['fingerprint']
        terms=[x['terminal'] for x in source['actions'] if x['terminal']['status']!='ongoing'];values={0 if x['winner'] is None else 1 if x['winner']==0 else -1 for x in terms}
        truth=True if len(values)>1 else False if len(source['actions'])==1 or len(terms)==len(source['actions']) else None
        assert truth is r['fork_candidate'];forks[truth]+=1
    assert [forks[True],forks[False],forks[None]]==[232,488,2896]
    records=p['files']['single_entity_records'];c=L.compile_rule(L.ruleset_from_dict(p['files']['single_entity_rule']));plies=0
    for g in records['rows']:
        ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(g['full_record'])));assert L.record_value(ss.state)==g['full_state'] and L.record_value(ss.result)==g['terminal'];plies+=len(ss.to_record().actions)
    assert plies==433
    out={'status':'PASS','started_at':start,'ended_at':datetime.now(timezone.utc).isoformat(),'seconds':time.perf_counter()-tick,'bundle_sha256':L.sha(bundle),'recovered_original_scientific_JSON':len(restored),'parity_counts':parity['counts'],'single_entity_sources':singleton['rows'],'single_entity_applied_actions':singleton['literal_applied_actions'],'validation_full_records':len(records['rows']),'validation_plies':plies,'H6_roots':h6['roots'],'H6_oneply_edges':h6['public_Core_applied_edges'],'next_literal_fork':[forks[True],forks[False],forks[None]],'source_sha256':L.sha(Path(__file__)),'limitation':'Publication-copy/sourcebinding anddistinctpublicCoreAPIroutes, not independentengine/H6solver/oracle/calibration ordelivery proof; no newPlayer/fitness/training.'};write_json(output/'qualification.json',out);print(out);return out

if __name__=='__main__':
 p=argparse.ArgumentParser(__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.bundle,a.output)
