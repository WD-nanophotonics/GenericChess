from pathlib import Path
import json
R=Path.cwd();P=R/'results/dev_aux/task1643';P.mkdir(exist_ok=False);old=json.loads((R/'results/dev_aux/task1640/plan.json').read_bytes());selection=json.loads((R/'results/dev_aux/task1641/selection.json').read_bytes())['selected'];prices=sorted({tuple(x) for x in selection.values()}|{(720,720,720),(720,720,360),(1440,720,720)})
plan={'status':'FROZEN_PHYSICAL_CONVERSION_CONTROL_BEFORE_NEWQUERIES','source_study':'task1640','families':[f for f in old['families'] if f['phase']=='DEV'],'profiles':prices,'H':48,'seeds':4,'H96_families':16,'H96_profiles':[(720,720,720),selection['POOLED']],'primary':'Physicalwinwithin48-minusphysicallosswithin48; unresolvednotDraw orfullWDL. Bothperfect4controlandnativeconversion trajectories retained, primaryprofiles fixedfromTRAIN notDEV.','secondary':'Knownphysicalnet plus/minusUNRESOLVED bounds for infinitefuturepayoff, not mateScore/quantity. No automatic horizonextension.','single_seconds':1200,'max_new_go':90000,'binary':old['binary'],'binary_sha256':old['binary_sha256'],'variant_ini':old['variant_ini'],'opponent':'Uniformlegalrandomforwholegame, samefamily/seed quantiles, candidateactualcold64 all stocks, nooraclehandoff, nohistorydraw shortcut.'}
(P/'plan.json').write_text(json.dumps(plan,indent=2))
s=(R/'results/dev_aux/task1639/learn.py').read_text(encoding='utf-8-sig').replace("task1641'","task1644'").replace("task1640/plan.json","task1643/plan.json").replace('deadline=start+600','deadline=start+1200').replace('queries<70000','queries<90000').replace("'seconds_cap':600,'max_go':70000","'seconds_cap':1200,'max_go':90000")
s=s.replace("sorted((R/'results/dev_aux/task1634').glob('*choices.jsonl'))","sorted((R/'results/dev_aux/task1634').glob('*choices.jsonl'))+sorted((R/'results/dev_aux/task1641').glob('*choices.jsonl'))")
s=s.replace("     if sum(x!=16 for x in s[:8])<=4:payoff=value[ix[s]]*(1 if s[8]==c else -1);category='PERFECT4_HANDOFF';break\n","")
s=s.replace("'upper':sum(x['upper'] for x in rows)/len(rows)","'upper':sum(x['upper'] for x in rows)/len(rows),'finite_net':sum(x['payoff'] or 0 for x in rows)/len(rows)")
start=s.index(" for phase in ['TRAIN1','TRAIN2']:")
end=s.index("except BaseException",start)
s=s[:start]+""" for price in map(tuple,plan['profiles']):dev.append(evaluate(price,'PHYSICAL48',plan['families'],4,48))
 for price in map(tuple,plan['H96_profiles']):diagnostics.append(evaluate(price,'PHYSICAL96',plan['families'][:16],4,96))
"""+s[end:]
s=s.replace("plan['opponent']+'; '+plan['labels']","plan['opponent']+'; '+plan['primary']")
(R/'results/dev_aux/task1639/physical_control.py').write_text(s,encoding='utf8')
print('FROZEN_PHYSICAL_CONTROL',len(plan['families']),prices)

