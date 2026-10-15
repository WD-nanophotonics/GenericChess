from pathlib import Path
import json,re,collections,time
R=Path.cwd();O=R/'results/dev_aux/task1717';raw=json.loads((R/'results/dev_aux/task1716/records.json').read_bytes());cases=json.loads((R/'results/dev_aux/task1716/frozen_cases.json').read_bytes())['cases'];assert len(raw)==64;counts=collections.Counter();zeros=0
clean=lambda a:[re.sub(r'\b(?:time|nps) \d+','TIME_OR_NPS',x) for x in a]
for i,case in enumerate(cases):
 pp={x['arm']:x for x in raw if x['case']==i};assert set(pp)=={'ORIGINAL','ONE_CLEAR'}
 for arm,r in pp.items():
  assert r['raw'][-1].split()[1]==case['choice']['move'] and clean(r['raw'][:-1])==clean(case['choice']['uci_info']);assert r['actual_clear_commands']==(2 if arm=='ORIGINAL' else 1);counts[arm+'_clears']+=r['actual_clear_commands'];zeros+=r['seconds']==0
 assert clean(pp['ORIGINAL']['raw'])==clean(pp['ONE_CLEAR']['raw'])
(R/'results/dev_aux/task1716/failure.json').write_text(json.dumps({'status':'POSTQUERY_ANALYSIS_FAILURE_PRESERVED','actual_completed_go':64,'cause':'Atleastoneoriginalqueryelapsed0 underobservedmonotonic clock; ratio divisionbyzero AFTERallqueries/e.close/recordssaved. Noqueryrerun orrawrewrite.','correction':'task1717 validatesallsavedpairs, makesnoclockspeedclaim','engine_exit_code':'Notpersistedbeforepostprocesserror; e.close completed inproducerfinally, noexit0claim.'},indent=2))
out={'status':'PASS_ALL64_PROTOCOL_RECORDS_ZERO_TICK_SAFE_POSTAUDIT','actual_go':64,'actual_query_pairs':32,'counts':dict(counts),'zero_tick_durations':zeros,'timing_claim':'NONE: clockzero samples meanratio comparison inappropriate; noendtoendtrainingtimegainmeasured.','wall_clock_info':str(time.get_clock_info('monotonic')),'semantic':'Allbestmoves andallUCIinfoexcepttime,nps matchbotharmsandsavedhistoricalsource; old2Sclear/query vsnew1, supportedbyactualsourcehandlers andclearbody. Exact32sample scope, noexistingproducerchanged.','exit_code':None};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
