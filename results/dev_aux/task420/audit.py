from pathlib import Path
import sys
R=Path.cwd();s=(R/'results/dev_aux/task407/audit.py').read_text(encoding='utf-8')
for task,arm in [(418,'unit'),(419,'random')]:
 code=s.replace("task405","task417").replace("task406",f"task{task}").replace("task407","task420")
 code=code.replace("(O/('partial.json' if partial else 'result.json'))","(O/('partial-'+str("+str(task)+")+'.json' if partial else '"+arm+".json'))")
 exec(compile(code,'task420/'+arm,'exec'))
