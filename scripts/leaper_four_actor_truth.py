"""Consume one fixed four-actor input and build one bounded physical closure.

Shared Core generates every edge; the existing physical attractor implements
WDL. Full-history/clock labels are separately qualified after closure.
"""
from pathlib import Path
import argparse,json
from scripts import leaper_design as L
from scripts.leaper_two_type_packet import read_packet
from scripts.leaper_ab_learner_exposure import write
from scripts import leaper_ab_odd_component as physical

SOURCE='fcd2021cc751736ab0f7166ce24a74d95632863e'
DIRECTORY=Path('docs/research/data/leaper_default_conversion_20261024')

def plan(output):
    output.mkdir(parents=True,exist_ok=False)
    docs=read_packet(DIRECTORY/'packet.json.gz',DIRECTORY/'manifest.json')
    world=json.loads(docs['next/inputs.json'])
    selected=world['roots'][0]
    spec=dict(source=SOURCE,input_source='56560fb3e24102792f72a005c5c5bdb52526943f',
        input_packet_sha256=L.sha(DIRECTORY/'packet.json.gz'),rule=world['rule'],
        selected=dict(record=selected['record'],state_sha256=selected['state_sha256'],index=selected['index']),
        producer_sha256=L.sha(Path(physical.__file__)),driver_sha256=L.sha(Path(__file__)),
        question='Does the complete reachable physical game support strategic forks/winning regions and history-qualified useful decisions on the single observed original-mu learner trajectory?',
        selection='Original root0 of all8frozen safe starts, before physical labels; one connected closure including actual captures. Truth is posthoc only, never selects or labels experiential training.',
        states_cap=750000,expansion_seconds=1500,expected_seconds=900,qualification_expected_seconds=1200,
        budget='One bounded new four-actor closure expected900s; complete Core frontier qualification1200s and finite-clock/posthoc/mechanism analysis1800s estimated total3900s, under120min. Expansion1500s ceiling, no cap extension/refill. No second physical graph. Reuse established Core/attractor; not PRIMARY generation/forward campaign.',
        scope='Exact full fixedRuleSet, physical no-prehistory positions only during expansion. No product defaults, Player/training calls or oracle starts. Missing closure remainsUNKNOWN. Actual full-history labels require independently checked fingerprint, fullfrontier, repetition-identity, finite clock and incoming-history conditions.')
    write(output/'spec.json',spec);return spec

def run(output):
    spec=json.loads((output/'spec.json').read_bytes())
    assert spec['driver_sha256']==L.sha(Path(__file__))
    assert spec['input_packet_sha256']==L.sha(DIRECTORY/'packet.json.gz')
    return physical.run(output)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('plan','run'));ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();globals()[a.mode](a.output)

