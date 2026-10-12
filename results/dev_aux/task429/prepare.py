from pathlib import Path
R=Path.cwd();s=(R/'results/dev_aux/task426/audit.py').read_text(encoding='utf-8').replace('task426','task429').replace('task425','task428')
s=s.replace("r['new_games']==len(games)==32 and r['new_go']==len(raw)==562 and r['cache_hits']==64","r['new_games']==len(games)==96 and r['new_go']==len(raw)==1643 and r['cache_hits']==0").replace("exact_cache_hits=64","exact_cache_hits=0")
s=s.replace("no re-executed games","newdeclared8192games, old1024outputs preserved")
O=R/'results/dev_aux/task429';O.mkdir(exist_ok=True);(O/'audit.py').write_text(s,encoding='utf-8')
