"""Existing play_game/RunConfig, old/new exact-map work under equal move time."""
from pathlib import Path
from unittest.mock import patch
import json,time,hashlib,argparse
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.search_performance_study import gate,stamp
from scripts.search_snapshot_ab import legacy_items
from generic_chess.core.search_runtime import RuntimeCountsSnapshot
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.benchmark.runner import play_game,RunConfig
from generic_chess.ai.benchmark.profiles import PROFILES
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped

class Arm:
    def __init__(self,player,method,plan,path,label):self.player=player;self.method=method;self.plan=plan;self.path=path;self.label=label
    def choose_action(self,session,limits):
        gate(self.plan);
        if stopped():raise RuntimeError('PRIMARY user stop persists')
        self.last_session=session;start=stamp();cp=time.process_time();t=time.perf_counter()
        with patch.object(RuntimeCountsSnapshot,'items',self.method):dec=self.player.choose_action(session,limits)
        row=dict(arm=self.label,started_at=start,ended_at=stamp(),cpu_seconds=time.process_time()-cp,wall_seconds=time.perf_counter()-t,before_record=L.record_value(session.to_record()),decision=L.record_value(dec))
        with self.path.open('a',encoding='utf-8')as f:f.write(json.dumps(row)+'\n')
        return dec

def run(d,remaining=False):
    plan=json.loads((d/'plan.json').read_text());reg=json.loads((d/'games-plan.json').read_text());allcases=json.loads((d/'inputs.json').read_text())['cases']+json.loads((d/'transfer-inputs.json').read_text())['cases'];current=RuntimeCountsSnapshot.items;start=stamp();tick=time.perf_counter();cpu=time.process_time();out=d/'games.jsonl'
    if out.exists() and not remaining:raise ValueError('explicit remaining-only continuation required')
    completed_ids={json.loads(line)['game'] for line in out.read_text().splitlines()} if out.exists() else set()
    completed_now=0
    for key in reg['cases']:
      case=next(x for x in allcases if x['key']==key);c=(compile_ruleset if case.get('execution_api')=='compile_ruleset' else L.compile_rule)(L.ruleset_from_dict(case['rule']));record=deserialize_game_record(json.dumps(case['record']));opening=record.actions
      assert record.initial_setup_key is None,'play_game defaultsetup boundary'
      for color in (0,1):
        gate(plan);game=key+'-candidate'+str(color)
        if game in completed_ids:continue
        raw=d/(game+'-turns.jsonl');assert not raw.exists()
        candidate=Arm(AlphaBetaPlayer(c,use_disk_cache=False),current,plan,raw,'new');control=Arm(AlphaBetaPlayer(c,use_disk_cache=False),legacy_items,plan,raw,'old')
        outcome,events=play_game(c,opening,key,game,color,candidate,control,RunConfig(PROFILES['baseline'],PROFILES['baseline'],(),seconds=reg['seconds_per_move'],nodes=None,max_plies=reg['caller_max_plies']))
        finished=getattr(candidate,'last_session',getattr(control,'last_session',None))
        row=dict(final_record=L.record_value(finished.to_record()) if finished is not None else case['record'],game=game,input_sha256=case['input_sha256'],outcome=L.record_value(outcome),events=L.record_value(events),eligible=outcome.eligible,rule_max_ply=L.ruleset_from_dict(case['rule']).max_ply,caller_cap=reg['caller_max_plies'])
        with out.open('a',encoding='utf-8')as f:f.write(json.dumps(row)+'\n')
        completed_now+=1
        print(game,outcome.result,'plies',outcome.plies,'eligible',outcome.eligible,flush=True)
    write_json(d/('games-continuation-receipt.json' if remaining else 'games-receipt.json'),dict(started_at=start,ended_at=stamp(),wall_seconds=time.perf_counter()-tick,cpu_seconds=time.process_time()-cpu,games=completed_now,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',type=Path,required=True);a.add_argument('--remaining',action='store_true');v=a.parse_args();run(v.directory,v.remaining)
