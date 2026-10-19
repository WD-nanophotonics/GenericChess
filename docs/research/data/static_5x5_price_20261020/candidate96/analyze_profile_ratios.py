from __future__ import annotations
import hashlib, json, math
from pathlib import Path
from statistics import median

base = Path(__file__).resolve().parent
repo = base.parents[4]
inputs = sorted(base.glob('profile-*.json'))
expected = [f'profile-{seed}.json' for seed in range(522001, 522009)]
if [p.name for p in inputs] != expected:
    raise SystemExit(f'expected exactly {expected}, got {[p.name for p in inputs]}')
rows=[]
for path in inputs:
    data=json.loads(path.read_text(encoding='utf-8'))
    pieces=data['piece_profiles']
    values={}
    semantics={}
    for tid in ('P','B','A'):
        item=pieces[tid]
        board=float(item['normalized_board_value'])
        hand=float(item['normalized_hand_value'])
        raw=float(item['raw_capability_score'])
        if not all(math.isfinite(x) for x in (board,hand,raw)) or board <= 0 or hand <= 0:
            raise SystemExit(f'invalid finite positive value in {path.name}/{tid}')
        values[tid]={'board':board,'hand':hand,'raw_capability_score':raw}
        signature=item['movement_signature'].encode('utf-8')
        semantics[tid]={'is_promotable':bool(item['is_promotable']),
                        'movement_signature_sha256':hashlib.sha256(signature).hexdigest()}
    def rank(field: str) -> str:
        return '>'.join(sorted(('P','B','A'),key=lambda t:values[t][field],reverse=True))
    rows.append({'seed':path.stem.removeprefix('profile-'), 'values':values,
                 'within_profile_rank':{'board':rank('board'),'hand':rank('hand')},
                 'ratios_to_B':{'P_board':values['P']['board']/values['B']['board'],
                                'A_board':values['A']['board']/values['B']['board'],
                                'P_hand':values['P']['hand']/values['B']['hand'],
                                'A_hand':values['A']['hand']/values['B']['hand']},
                 'type_id_semantics':semantics})
summary={}
for key in ('P_board','A_board','P_hand','A_hand'):
    nums=[row['ratios_to_B'][key] for row in rows]
    summary[key]={'min':min(nums),'median':median(nums),'max':max(nums)}
rank_counts={field:{r:sum(row['within_profile_rank'][field]==r for row in rows)
                    for r in sorted({row['within_profile_rank'][field] for row in rows})}
             for field in ('board','hand')}
label_semantics={}
for tid in ('P','B','A'):
    items=[row['type_id_semantics'][tid] for row in rows]
    label_semantics[tid]={'distinct_movement_signatures':len({x['movement_signature_sha256'] for x in items}),
                          'promotable_profiles':sum(x['is_promotable'] for x in items),
                          'profiles':len(items)}
result={'schema':'primary-candidate96-profile-ratio-audit-v1',
        'inputs':[{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in inputs],
        'scope':'Recompute descriptive within-profile P/B/A ranks and P:B/A:B ratios from eight frozen candidate96 profile JSON files only; no games/search/training.',
        'per_seed':rows,'ratio_summary':summary,'within_profile_rank_counts':rank_counts,
        'type_id_semantic_variation':label_semantics,
        'interpretation':'P/B/A are generated type IDs, not homologous cross-seed piece classes: each ID has varying movement signatures and promotion status. Pooled label ratios are descriptive across these eight profiles only, not transferable piece-price estimates or a policy/default decision.'}
out=base/'profile_ratio_summary.json'
out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
report=repo/'docs/research/STATIC_5X5_PRICE_TRANSFER_20261020.md'
text=report.read_text(encoding='utf-8')
marker='## Candidate96 profile-ratio audit — 2026-10-20'
section='''\n\n## Candidate96 profile-ratio audit — 2026-10-20\n\nA read-only reproducible audit recomputed within-profile ranks and P:B/A:B\nratios from the eight saved candidate96 profile JSONs (seeds 522001–522008);\nno games, search, or training ran. Board-value rank counts were A>B>P: 1,\nP>A>B: 3, B>P>A: 3, B>A>P: 1; hand-value ranks matched. Board P:B ranged\n0.1591–3.7937 (median 0.8190), and A:B 0.1357–2.4272 (median 1.0614).\nHand ratios were nearly identical (P:B 0.1591–3.7925; A:B 0.1358–2.4259).\n\nThese are descriptive within-profile calculations, not cross-seed price\ntransfer evidence: A/B/P are generated type IDs, and their movement signatures\nand promotion status vary across the eight rules. Thus no common piece class is\nidentified by those letters. The audit does not change the scoped candidate96\nresult or justify a universal vector/default. Reproducer and exact per-seed\nvalues: `data/static_5x5_price_20261020/candidate96/analyze_profile_ratios.py`\nand `data/static_5x5_price_20261020/candidate96/profile_ratio_summary.json`.\n'''
if marker not in text: report.write_text(text.rstrip()+section,encoding='utf-8')
main=repo/'docs/research/LOCAL_MAINLINE.md'
text=main.read_text(encoding='utf-8')
marker='## Candidate96 profile-ratio range audit — 2026-10-20'
section='''\n\n## Candidate96 profile-ratio range audit — 2026-10-20\n\nRecomputed board/hand P:B and A:B ratios and within-profile ranks from the eight\nfrozen candidate96 profile files only. Board ranks were A>B>P once, P>A>B three\ntimes, B>P>A three times and B>A>P once; hand ranks matched. Board P:B range\nwas 0.1591–3.7937 (median 0.8190), A:B 0.1357–2.4272 (median 1.0614). The\nletters are generated type IDs, not homologous piece classes: signatures and\npromotion status differ across seeds. Therefore this descriptive spread does\nnot support transfer of a shared P/B/A price vector or a policy/default change.\nNo games, search or training ran. Reproducer and full source hashes are in\n`STATIC_5X5_PRICE_TRANSFER_20261020.md` and its `candidate96/profile_ratio_summary.json`.\n\nClose the label-ratio transfer question: it is not a common-piece comparison.\nResume unfamiliar-rule search with one concrete current public caller versus\nits tested invariant; if existing coverage fully closes it, select a different\nnew issue rather than adding infrastructure or reopening the saved panels.\n'''
if marker not in text: main.write_text(text.rstrip()+section,encoding='utf-8')
print(json.dumps({'profiles':len(rows),'rank_counts':rank_counts,'ratio_summary':summary,'type_semantic_variation':label_semantics,'output':str(out.relative_to(repo))},sort_keys=True))
