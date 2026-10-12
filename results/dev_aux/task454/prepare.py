from pathlib import Path
R=Path.cwd();s=(R/'results/dev_aux/task442/analyze.py').read_text(encoding='utf-8').replace('task442','task454').replace('task441','task451').replace("[('mixed',439),('terminal_only',440)]","[('terminal_only',449),('fast_terminal',450)]").replace('task439','task449').replace('task440','task450').replace('Actualmixed-vs-pureterminal interventions','Actualpure-vs-fastterminal interventions')
# Different accepted paths imply differentcandidateprices/trajectories: compare labels only if samecell counts, don't assert identicallength.
s=s.replace("assert len(g['queries'])==len(h['queries'])","semantic_equal &= len(g['queries'])==len(h['queries'])")
s=s.replace("paired_physical_fitgames=count","paired_physical_fitgames=count")
O=R/'results/dev_aux/task454';O.mkdir(exist_ok=True);(O/'analyze.py').write_text(s,encoding='utf-8')
