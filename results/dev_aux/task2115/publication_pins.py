"""Transparent publication-only source projection, STRICT by default.

Scientific original byte pins are never rewritten. A caller may explicitly
verify a documented unused-file privacy projection; reports retain that weaker
byte-identity scope. All executed dependencies still require original hashes.
"""
from pathlib import Path
import json,hashlib,sys

def verify_publication_pins(pins,projection=None):
 allowed={}if projection is None else json.loads(Path(projection).read_text(encoding='utf-8'))['files'];exact=0;projected=[]
 for name,expected in pins.items():
  actual=hashlib.sha256(Path(name).read_bytes()).hexdigest();normal=name.replace('\\','/')
  if actual==expected:exact+=1;continue
  assert normal in allowed,'unexplainedsourcehashdifference:'+normal
  item=allowed[normal];assert expected==item['original_sha256']and actual==item['published_sha256']and item['must_not_import']not in sys.modules
  projected.append(normal)
 return dict(original_byte_exact_files=exact,published_unused_privacy_projections=projected,full_original_byte_identity=not projected,scope='Nooriginalpinreset; projectionexplicitlyweakerthanfulloriginalbytecheck. Consumerassertsunusedmodulenotloadedbefore/after.')
