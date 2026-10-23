"""Exact finite Brier partition; diagnostic test-bin fits are never deployed."""
from collections import defaultdict
from fractions import Fraction as F
from pathlib import Path
import argparse
from scripts import leaper_design as L


def partition(d):
 a=L.load(d/'e0-analysis.json');r=L.load(d/'registration.json');rows=a['world_predictions'];assert all(w['label_any_role_nonzero_interaction'] is not None for w in rows);n=len(rows);q=F(sum(w['label_any_role_nonzero_interaction'] for w in rows),n)
 probs={False:F(r['calibration']['bins']['False']['positive']+1,r['calibration']['bins']['False']['n']+2),True:F(r['calibration']['bins']['True']['positive']+1,r['calibration']['bins']['True']['n']+2)};baseline=F(8,25);groups=defaultdict(list)
 for w in rows:groups['terminal' if w['terminal_at_start'] else str(w['positive_feature'])].append(w)
 uncertainty=q*(1-q);reliability=resolution=score=F(0);grows=[]
 for k,ww in groups.items():
  p=F(0) if k=='terminal' else probs[k=='True'];freq=F(sum(w['label_any_role_nonzero_interaction'] for w in ww),len(ww));weight=F(len(ww),n);reliability+=weight*(p-freq)**2;resolution+=weight*(freq-q)**2;score+=sum((p-w['label_any_role_nonzero_interaction'])**2 for w in ww)/n;grows.append({'bin':k,'n':len(ww),'positives':sum(w['label_any_role_nonzero_interaction'] for w in ww),'frozen_probability':str(p),'observed_event_fraction':str(freq)})
 assert score==uncertainty+reliability-resolution
 ongoing=[w for w in rows if not w['terminal_at_start']];freq=F(sum(w['label_any_role_nonzero_interaction'] for w in ongoing),len(ongoing));oracle_constant=sum((freq-w['label_any_role_nonzero_interaction'])**2 for w in ongoing)/n;oracle_bins=uncertainty-resolution;bound=oracle_constant-oracle_bins
 out={'status':'PASS','groups':grows,'finite_event_frequency':str(q),'Brier_mean':str(score),'uncertainty':str(uncertainty),'reliability':str(reliability),'resolution':str(resolution),'identity_exact':True,'test_oracle_constant_minimum_score':str(oracle_constant),'test_oracle_same_bins_minimum_score':str(oracle_bins),'test_in_sample_extra_resolution_bound':str(bound),'test_in_sample_extra_resolution_bound_float':float(bound),'new_Player_calls':0,'new_fitted_predictor':False,'scope':'Exactalgebra onthe96finite labels, noIID/population/reliabilityestimate. Testoracle probabilities are diagnostic lowerbounds ONLY, never adopted/refit/compared asprospectivepredictors. Bound covers fixedbinaryfeature partition onthiscohort, NOTallfeatures/learners/rules.'};L.write_record(d/'finite-score-partition.json',out);print(out);return out


def main():
 p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();partition(a.output)
if __name__=='__main__':main()
