from pathlib import Path
import subprocess,hashlib,json
R=Path.cwd();p=R/'docs/research/LOCAL_MAINLINE.md';current=p.read_bytes();marker=b'# Current local research mainline';i=current.index(marker)
old=subprocess.check_output(['git','show','e3c51455b800a58d82ce7837bce09ee801b9a2f0:docs/research/LOCAL_MAINLINE.md'],cwd=R);j=old.index(marker)
before=current[i:];after=old[j:];p.write_bytes(current[:i]+after)
record=dict(correction='PreviousauxmetadatawriterusedWindowsdefaultcp1252read_textonUTF8pinnedbackground, causingmojibake. Restoreonlypinnedbackground exactbytesfromownGit e3c51455; retaincurrentAUXprefix; no primaryfile reads/writes, no scienceartifactchanges.',original_background_sha256=hashlib.sha256(after).hexdigest(),previous_misdecoded_background_sha256=hashlib.sha256(before).hexdigest(),verified=p.read_bytes()[i:]==after)
out=R/'results/dev_aux/task154';out.mkdir(exist_ok=True);(out/'encoding_correction.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record))
