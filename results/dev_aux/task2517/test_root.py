import math
import pytest
from results.dev_aux.task2492.learning import Model,Sample,Receipt
from results.dev_aux.task2517.calibrate import RootStrap,factor

def test_rootstrap_uses_root_static_gradient_not_pv_or_other_node():
 model=Model([1,1]);samples=(Sample((0.,-3.),-4.,-4.,1),Sample((0.,2.),5.,5.,2));receipt=Receipt(None,5.,(0.,-9.),False,samples,20,True,0,.01,'complete');before=list(model.weights);pred=model.prediction((0.,2.));grad=model.gradient((0.,2.))[1];stats=RootStrap(.05).update(model,receipt)
 assert stats['samples']==1 and model.weights[0]==1 and model.weights[1]==pytest.approx(before[1]+.05*(math.tanh(.5)-pred)*grad)

def test_single_rms_factor_includes_zeros_and_rejects_zero_signal():
 result=factor([[0.,.5],[0.,0.]],[[0.,2.],[0.,0.]])
 assert result['factor']==pytest.approx(.25)and result['tree_RMS']==pytest.approx(math.sqrt(.25/2))and result['root_RMS']*result['factor']==pytest.approx(result['tree_RMS'])
 assert factor([[0.,.5]],[[0.,0.]])['factor']is None
 assert factor([[0.,0.]],[[0.,2.]])['gate']=='INSUFFICIENT_INITIAL_GRADIENT_SIGNAL'
