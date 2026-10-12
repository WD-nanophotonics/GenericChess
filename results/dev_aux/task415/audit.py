from pathlib import Path
import json,hashlib,re
R=Path.cwd();O=R/'results/dev_aux/task415';d=json.loads((O/'declaration.json').read_text(encoding='utf-8'));B=R/'.local_agent/yaneura27/source';old=R/'.local_agent/yaneura26/source';diff=[]
base=json.loads((R/'results/dev_aux/task399/build_summary.json').read_text(encoding='utf-8'));expected={r['path']:r['base_patched_sha256'] for r in base['base_sources']};expected['aux_material.h']=base['added_header_sha256'];expected['engine/yaneuraou-engine/yaneuraou-search.cpp']=base['new_search_sha256'];assert {r['path']:r['sha256'] for r in d['base_sources']}==expected
for row in d['base_sources']:
 p=B/row['path'];q=old/row['path'];assert hashlib.sha256(q.read_bytes()).hexdigest()==row['sha256']
 if p.read_bytes()!=q.read_bytes():diff.append(row['path'])
assert diff==['position.cpp']
s=(old/'position.cpp').read_text(encoding='utf-8');changed=(B/'position.cpp').read_text(encoding='utf-8');start=s.index('    int swap = PieceValue[piece_on(to)] - threshold;');end=s.index('        if (selected == KNIGHT)',start);replay=s[start:end]
for x in d['changes']:assert replay.count(x['old'])==1;replay=replay.replace(x['old'],x['new'])
assert changed==s[:start]+replay+s[end:];assert changed.count('DEV_AUX_HAND_SEE')==3
# With compileguard false exactly retain the old recurrence: strip guarded branches.
strip=changed
pattern=r'#if defined\(DEV_AUX_HAND_SEE\) && defined\(EVAL_MATERIAL\) && MATERIAL_LEVEL == 1\n(.*?)#else\n(.*?)#endif'
strip,n=re.subn(pattern,lambda m:m[2].rstrip('\n'),strip,flags=re.S);assert n==3
# The LVA alias substitutes the original table; comment/alias declaration is only cosmetic.
strip=strip.replace('        const auto& aux_see_prices = PieceValue;\n','').replace('aux_see_prices','PieceValue')
assert strip==s
proof=dict(status='PASS',files_verified=len(d['base_sources']),changed_only=diff,exact_patch_replay=True,disabled_guard_exact_original=True,formula='initial gain = w[captured_type] + w[demoted_captured_base] + first_promotion_delta; nextcapturecost = w[currentactor_after_first_promotion] + w[demoted_actor_base]. Transfer to hand keeps captured identity base value; initial promotion delta may be negative under frozen arbitraryvectors. LVA prices are fullcapturecost, later recapturepromotion remainsomitted.',scope='translation/source equivalence and finite416literal trajectory tests, no all-defense SEE, latepromotion, pin/king orglobalsearch guarantee',source_sha256=hashlib.sha256((B/'position.cpp').read_bytes()).hexdigest());(O/'source_audit.json').write_text(json.dumps(proof,indent=2),encoding='utf-8');print(proof)
