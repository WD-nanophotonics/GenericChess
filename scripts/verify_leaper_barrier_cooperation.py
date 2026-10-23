"""Literal positive path supplement; never turns cooperation into a win label."""
import argparse,json,time
from pathlib import Path
from scripts.leaper_explorer_truth import load
from scripts.verify_leaper_twoa_safety import admission,SOURCE
from scripts.leaper_design import state_sha
from scripts.research_record import record_value
from generic_chess.core.actions import action_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record


def verify(result,barrier,source):
    tick=time.perf_counter();c,_=admission(barrier,source)
    if result['rule']!=barrier['rule']or result['record']!=barrier['roots'][0]['record']:raise ValueError('supplement history/rule differs')
    s=GameSession.replay(c,deserialize_game_record(json.dumps(result['record'])))
    if s.result.status.value!='ongoing'or state_sha(s.state)!=result['source_state_sha']or 64-s.state.ply_count!=result['remaining']:raise ValueError('literal incoming state differs')
    if result['cooperative']is not True or not result['path']:raise ValueError('positive path required')
    for a in result['path']:s.submit(action_from_dict(a))
    if s.result.status.value!='checkmate'or s.result.winner!=0 or state_sha(s.state)!=result['final_state_sha']or record_value(s.to_record())!=result['final_record']:raise ValueError('literal cooperative mate differs')
    if result['terminal']!=dict(status=s.result.status.value,winner=s.result.winner)or result['distance']!=len(result['path']):raise ValueError('cooperative path metadata differs')
    return dict(verified=True,Core_path_edges=len(result['path']),seconds=time.perf_counter()-tick,
        scope='Actualcomplete26plyhistorypluspositive5plycooperativemate. Notashortestpathcertificate,noforcedWIN; independentDRAWsafetycertificateunchanged. NewmeasurementdoesnotrewriteearlierUNMEASUREDreceipt.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(load(a.directory/'barrier-cooperation.json'),load(a.directory/'twoa-barrier-safety.json.gz'),load(SOURCE));a.output.write_text(json.dumps(r,indent=2));print(r)
