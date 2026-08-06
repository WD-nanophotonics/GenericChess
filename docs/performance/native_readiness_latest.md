# GenericChess Native-Readiness Audit

## 1. 环境

* os: win32
* python: 3.13.2 (tags/v3.13.2:4f8bb39, Feb  4 2025, 15:23:48) [MSC v.1942 64 bit (AMD64)]
* cpu: ARMv8 (64-bit) Family 8 Model 1 Revision 201, Qualcomm Technologies Inc
* logical_cpus: 10
* commit: 0824ddba211be04f8842fd0bfe6aeb0a41c4baa2
* debug_build: False

## 2. Suite

* suite version: standard-v1
* RuleSet 数: 29
* position 数: 15
* 棋盘尺寸: [4, 6, 8]
* movement 分桶: ['forward_asymmetric', 'high_direction', 'leap_heavy', 'mixed', 'ray_heavy', 'short_range', 'symmetric']
* promotion 分桶: ['forced', 'multi_target', 'no_promotion', 'single_target', 'voluntary']
* drop 分桶: ['drop_all', 'drop_restricted', 'multi_type_drop']
* 已覆盖 categories: ['high_branching', 'immediate_capture', 'in_check', 'midgame', 'opening']
* 未覆盖 categories: ['endgame', 'multi_evasion', 'low_anchor_escape', 'immediate_promotion', 'near_repetition', 'low_branching', 'drop_available', 'checking_drop', 'nonchecking_drop']

## 3. 总体性能（node budget）

### 10000 nodes（fixtures: 15，runs: 15）

* NPS median/min/max: {'count': 15, 'max': 1474.9, 'median': 83.6, 'min': 2.3}
* completed depth median: 3.0
* qnode ratio median: 2.888
* TT hit rate median: 0.12004662004662005
* fallback runs: 0
* by board size: {'4': {'count': 3, 'max': 1474.9, 'median': 331.1, 'min': 85.0}, '6': {'count': 6, 'max': 862.5, 'median': 242.45000000000002, 'min': 2.3}, '8': {'count': 6, 'max': 766.8, 'median': 36.75, 'min': 7.8}}
* by movement bucket: {'forward_asymmetric': {'count': 14, 'max': 1474.9, 'median': 72.1, 'min': 2.3}, 'high_direction': {'count': 13, 'max': 1474.9, 'median': 83.6, 'min': 2.3}, 'leap_heavy': {'count': 7, 'max': 1474.9, 'median': 60.6, 'min': 6.7}, 'mixed': {'count': 10, 'max': 1474.9, 'median': 36.75, 'min': 2.3}, 'ray_heavy': {'count': 8, 'max': 766.8, 'median': 208.05, 'min': 2.3}, 'short_range': {'count': 1, 'max': 83.6, 'median': 83.6, 'min': 83.6}, 'symmetric': {'count': 1, 'max': 766.8, 'median': 766.8, 'min': 766.8}}

### 100000 nodes（fixtures: 6，runs: 6）

* NPS median/min/max: {'count': 6, 'max': 835.4, 'median': 23.299999999999997, 'min': 2.2}
* completed depth median: 3.0
* qnode ratio median: 41.4525
* TT hit rate median: 0.1380952380952381
* fallback runs: 0
* by board size: {'4': {'count': 2, 'max': 83.8, 'median': 63.8, 'min': 43.8}, '6': {'count': 4, 'max': 835.4, 'median': 2.8, 'min': 2.2}}
* by movement bucket: {'forward_asymmetric': {'count': 6, 'max': 835.4, 'median': 23.299999999999997, 'min': 2.2}, 'high_direction': {'count': 5, 'max': 83.8, 'median': 2.8, 'min': 2.2}, 'leap_heavy': {'count': 1, 'max': 835.4, 'median': 835.4, 'min': 835.4}, 'mixed': {'count': 4, 'max': 835.4, 'median': 2.8, 'min': 2.2}, 'ray_heavy': {'count': 5, 'max': 83.8, 'median': 2.8, 'min': 2.2}}

## 4. 子系统占比（instrumented）

* evaluation: 0.02%
* move_gen: 1.20%
* ordering: 0.03%
* other: 0.08%
* quiescence: 98.64%
* tt_key: 0.02%
* tt_probe_store: 0.01%

* gen_classic_like_4_101:opening: wall=10.679s nodes=465 qnodes=7392
* gen_classic_like_4_101:immediate_capture: wall=14.693s nodes=1220 qnodes=8780
* gen_bilateral_random_6_201:opening: wall=42.438s nodes=94 qnodes=9906
* gen_bilateral_random_6_201:high_branching: wall=52.888s nodes=142 qnodes=9858

## 5. Core 微基准（每调用中位数，秒）

### gen_classic_like_4_101:opening (legal=4, pseudo/legal=1.0)
* drop_action_generation: 8e-07s
* is_in_check: 4.05e-05s
* legal_successors: 0.001037s
* legality_filter_per_action: 4.56e-05s
* mechanical_transition: 7.4e-06s
* move_generation_legal: 0.0001721s
* position_key: 3.68e-05s
* pseudo_action_expansion: 3.14e-05s
* pseudo_action_generation: 3.7e-05s
* pseudo_attacks_owner0: 3.7e-05s
* pseudo_attacks_owner1: 3.75e-05s
* repetition_update: 1.9e-06s
* terminal_detection: 9.18e-05s

### gen_classic_like_4_101:immediate_capture (legal=5, pseudo/legal=1.0)
* drop_action_generation: 5e-07s
* is_in_check: 3.84e-05s
* legal_successors: 0.001313s
* legality_filter_per_action: 2.75e-05s
* mechanical_transition: 4.7e-06s
* move_generation_legal: 0.0001911s
* position_key: 2.42e-05s
* pseudo_action_expansion: 2.66e-05s
* pseudo_action_generation: 2.56e-05s
* pseudo_attacks_owner0: 3.41e-05s
* pseudo_attacks_owner1: 3.45e-05s
* repetition_update: 1.7e-06s
* terminal_detection: 5.48e-05s

### gen_bilateral_random_6_201:opening (legal=20, pseudo/legal=1.0)
* drop_action_generation: 8e-07s
* is_in_check: 7.33e-05s
* legal_successors: 0.007336s
* legality_filter_per_action: 4.99e-05s
* mechanical_transition: 7.3e-06s
* move_generation_legal: 0.001703s
* position_key: 4.79e-05s
* pseudo_action_expansion: 0.0001185s
* pseudo_action_generation: 7.52e-05s
* pseudo_attacks_owner0: 6.94e-05s
* pseudo_attacks_owner1: 6.88e-05s
* repetition_update: 1.9e-06s
* terminal_detection: 0.0001709s

### gen_bilateral_random_6_201:high_branching (legal=35, pseudo/legal=1.114)
* drop_action_generation: 5.89e-05s
* is_in_check: 6.7e-05s
* legal_successors: 0.01609s
* legality_filter_per_action: 7.31e-05s
* mechanical_transition: 7.1e-06s
* move_generation_legal: 0.003054s
* position_key: 4.84e-05s
* pseudo_action_expansion: 0.0001502s
* pseudo_action_generation: 6.32e-05s
* pseudo_attacks_owner0: 5.47e-05s
* pseudo_attacks_owner1: 6.35e-05s
* repetition_update: 2.5e-06s
* terminal_detection: 0.0001554s

## 6. Cache

* 9b1e5e1b6930: cold=0.014s warm=0.000s disk=0.003s serialized=1863B
* 888f110e93ae: cold=0.101s warm=0.000s disk=0.029s serialized=2292B
* b6f8d41e0cfd: cold=0.017s warm=0.000s disk=0.022s serialized=1461B

## 7. Profiler

### cProfile gen_bilateral_random_6_201:high_branching
```
         15835859 function calls (15793288 primitive calls) in 24.941 seconds

   Ordered by: cumulative time
   List reduced from 103 to 12 due to restriction <12>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000   27.949   27.949 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\player.py:72(choose_action)
        1    0.001    0.001   27.949   27.949 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\search.py:464(run_root_search)
     39/2    0.002    0.000   27.808   13.904 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\search.py:140(negamax)
  1426/36    0.051    0.000   27.648    0.768 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\search.py:293(quiescence)
      432    0.017    0.000   24.176    0.056 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:61(legal_successors)
    68685    6.494    0.000   17.004    0.000 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\attacks.py:34(pseudo_attacks)
    15015    0.026    0.000   17.003    0.001 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:78(<genexpr>)
    14583    0.150    0.000   16.977    0.001 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:28(_transition)
    66083    0.295    0.000   16.795    0.000 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\attacks.py:58(is_square_attacked)
    56709    0.206    0.000   16.595    0.000 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\movegen.py:193(_is_legal)
    14583    0.080    0.000   14.486    0.001 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\terminal.py:45(_terminal_from_parts)
    14583    0.146    0.000   14.146    0.001 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\movegen.py:221(has_legal_action)



```
### cProfile gen_classic_like_4_101:immediate_capture
```
         4162737 function calls (4141915 primitive calls) in 6.763 seconds

   Ordered by: cumulative time
   List reduced from 109 to 12 due to restriction <12>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    7.526    7.526 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\player.py:72(choose_action)
        1    0.001    0.001    7.525    7.525 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\search.py:464(run_root_search)
    132/3    0.006    0.000    7.513    2.504 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\search.py:140(negamax)
  1363/98    0.032    0.000    7.242    0.074 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\search.py:293(quiescence)
      617    0.009    0.000    5.681    0.009 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:61(legal_successors)
    33199    1.613    0.000    4.035    0.000 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\attacks.py:34(pseudo_attacks)
    30931    0.114    0.000    3.936    0.000 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\attacks.py:58(is_square_attacked)
     6745    0.011    0.000    3.720    0.001 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:78(<genexpr>)
     6128    0.057    0.000    3.708    0.001 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:28(_transition)
    21737    0.076    0.000    3.509    0.000 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\movegen.py:193(_is_legal)
     6128    0.033    0.000    2.901    0.000 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\terminal.py:45(_terminal_from_parts)
     6128    0.052    0.000    2.754    0.000 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\movegen.py:221(has_legal_action)



```
### tracemalloc gen_bilateral_random_6_201:high_branching peak=432165
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\repetition.py:12: 89272B x 1503
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\position.py:49: 16512B x 294
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:78: 11416B x 180
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\movegen.py:183: 5488B x 98
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\position.py:40: 2760B x 48
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\keys.py:30: 952B x 17
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:40: 720B x 10
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\movegen.py:164: 672B x 12
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\movegen.py:185: 360B x 5
* C:\Users\icywo\AppData\Local\Programs\Python\Python313\Lib\json\encoder.py:261: 336B x 6
### tracemalloc gen_classic_like_4_101:immediate_capture peak=125862
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:78: 27472B x 177
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\repetition.py:12: 20576B x 194
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\keys.py:39: 5880B x 56
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\movegen.py:186: 5040B x 30
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\transposition.py:107: 3792B x 34
* <string>:4: 2368B x 37
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:40: 2016B x 28
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\search.py:133: 1856B x 29
* C:\Users\icywo\AppData\Local\Programs\Python\Python313\Lib\json\encoder.py:252: 1456B x 13
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\coordinates.py:61: 1296B x 27

## 8. 结论

* instrumented_subsystem_shares: {'evaluation': 0.0002, 'move_gen': 0.012, 'ordering': 0.0003, 'other': 0.0008, 'quiescence': 0.9864, 'tt_key': 0.0002, 'tt_probe_store': 0.0001}
* position_key_to_successors_ratio: 0.0159
* recommendation: see report: share evidence determines native boundary

* 说明：node-budget 结果受单机环境影响；子系统占比用于定位瓶颈，不代表正常运行的绝对 NPS。