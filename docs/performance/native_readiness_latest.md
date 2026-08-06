# GenericChess Native-Readiness Audit

## 1. 环境

* os: win32
* python: 3.13.2 (tags/v3.13.2:4f8bb39, Feb  4 2025, 15:23:48) [MSC v.1942 64 bit (AMD64)]
* cpu: ARMv8 (64-bit) Family 8 Model 1 Revision 201, Qualcomm Technologies Inc
* logical_cpus: 10
* commit: 6f9019aab0527282ea629075446b25fe540cfd44
* debug_build: False

## 2. Suite

* suite version: standard-v1
* manifest RuleSet 数: 43
* manifest position 数: 122
* executed RuleSet 数: 15
* executed position 数: 15
* requested budget tiers: [10000, 100000]
* completed budget tiers: [10000, 100000]
* skipped/timeout/failed runs: 0/0/0
* 棋盘尺寸: [4, 6, 8]
* movement 分桶: ['forward_asymmetric', 'high_direction', 'leap_heavy', 'long_ray', 'low_direction', 'mixed', 'ray_heavy', 'short_range', 'symmetric']
* promotion 分桶: ['forced', 'multi_target', 'no_promotion', 'single_target', 'voluntary']
* drop 分桶: ['drop_all', 'drop_restricted', 'multi_type_drop', 'no_drop']
* 已覆盖 categories: ['high_branching', 'immediate_capture', 'in_check', 'midgame', 'opening']
* 未覆盖 categories: ['endgame', 'multi_evasion', 'low_anchor_escape', 'immediate_promotion', 'near_repetition', 'low_branching', 'drop_available', 'checking_drop', 'nonchecking_drop']

## 3. 总体性能（node budget）

### 10000 nodes（fixtures: 15，runs: 15）

* total_nps median/min/max: {'count': 15, 'max': 1686.8, 'median': 302.2, 'min': 100.8}
* main_nps median: 38.7
* q_nps median: 164.4
* completed depth median: 2.0
* qnode ratio median: 20.786
* qnode share median: 0.954
* TT hit rate median: 0.08823529411764706
* fallback runs: 0
* by board size: {'4': {'count': 3, 'max': 1686.8, 'median': 843.8, 'min': 340.1}, '6': {'count': 7, 'max': 1527.3, 'median': 318.0, 'min': 280.1}, '8': {'count': 5, 'max': 267.1, 'median': 123.1, 'min': 100.8}}
* by board size (total_nps): {'4': {'count': 3, 'max': 1686.8, 'median': 843.8, 'min': 340.1}, '6': {'count': 7, 'max': 1527.3, 'median': 318.0, 'min': 280.1}, '8': {'count': 5, 'max': 267.1, 'median': 123.1, 'min': 100.8}}
* by movement bucket: {'forward_asymmetric': {'count': 15, 'max': 1686.8, 'median': 302.2, 'min': 100.8}, 'high_direction': {'count': 13, 'max': 1686.8, 'median': 302.2, 'min': 100.8}, 'leap_heavy': {'count': 7, 'max': 1686.8, 'median': 280.1, 'min': 123.1}, 'long_ray': {'count': 10, 'max': 1527.3, 'median': 298.29999999999995, 'min': 100.8}, 'mixed': {'count': 11, 'max': 1686.8, 'median': 302.2, 'min': 100.8}, 'ray_heavy': {'count': 8, 'max': 965.7, 'median': 329.05, 'min': 100.8}, 'short_range': {'count': 1, 'max': 267.1, 'median': 267.1, 'min': 267.1}}
* by movement bucket (total_nps): {'forward_asymmetric': {'count': 15, 'max': 1686.8, 'median': 302.2, 'min': 100.8}, 'high_direction': {'count': 13, 'max': 1686.8, 'median': 302.2, 'min': 100.8}, 'leap_heavy': {'count': 7, 'max': 1686.8, 'median': 280.1, 'min': 123.1}, 'long_ray': {'count': 10, 'max': 1527.3, 'median': 298.29999999999995, 'min': 100.8}, 'mixed': {'count': 11, 'max': 1686.8, 'median': 302.2, 'min': 100.8}, 'ray_heavy': {'count': 8, 'max': 965.7, 'median': 329.05, 'min': 100.8}, 'short_range': {'count': 1, 'max': 267.1, 'median': 267.1, 'min': 267.1}}

### 100000 nodes（fixtures: 4，runs: 4）

* total_nps median/min/max: {'count': 4, 'max': 1025.9, 'median': 568.05, 'min': 293.6}
* main_nps median: 20.1
* q_nps median: 448.15
* completed depth median: 3.0
* qnode ratio median: 99.686
* qnode share median: 0.974
* TT hit rate median: 0.15092592592592594
* fallback runs: 0
* by board size: {'4': {'count': 1, 'max': 835.5, 'median': 835.5, 'min': 835.5}, '6': {'count': 3, 'max': 1025.9, 'median': 300.6, 'min': 293.6}}
* by board size (total_nps): {'4': {'count': 1, 'max': 835.5, 'median': 835.5, 'min': 835.5}, '6': {'count': 3, 'max': 1025.9, 'median': 300.6, 'min': 293.6}}
* by movement bucket: {'forward_asymmetric': {'count': 4, 'max': 1025.9, 'median': 568.05, 'min': 293.6}, 'high_direction': {'count': 3, 'max': 835.5, 'median': 300.6, 'min': 293.6}, 'leap_heavy': {'count': 1, 'max': 1025.9, 'median': 1025.9, 'min': 1025.9}, 'long_ray': {'count': 3, 'max': 1025.9, 'median': 300.6, 'min': 293.6}, 'mixed': {'count': 3, 'max': 1025.9, 'median': 300.6, 'min': 293.6}, 'ray_heavy': {'count': 3, 'max': 835.5, 'median': 300.6, 'min': 293.6}}
* by movement bucket (total_nps): {'forward_asymmetric': {'count': 4, 'max': 1025.9, 'median': 568.05, 'min': 293.6}, 'high_direction': {'count': 3, 'max': 835.5, 'median': 300.6, 'min': 293.6}, 'leap_heavy': {'count': 1, 'max': 1025.9, 'median': 1025.9, 'min': 1025.9}, 'long_ray': {'count': 3, 'max': 1025.9, 'median': 300.6, 'min': 293.6}, 'mixed': {'count': 3, 'max': 1025.9, 'median': 300.6, 'min': 293.6}, 'ray_heavy': {'count': 3, 'max': 835.5, 'median': 300.6, 'min': 293.6}}

## 4. 子系统占比（instrumented）

Phase inclusive shares（quiescence 为整棵 qsearch 调用树）:
* main_search: 2.68%
* quiescence: 97.32%
Direct-measured subsystem shares（仅 main search 中被包裹的函数调用）:
* evaluation: 0.03%
* move_generation: 2.35%
* ordering: 0.09%
* position_key: 0.05%
* tt: 0.01%

* gen_bilateral_random_6_201:high_branching: wall=34.082s nodes=109 qnodes=9891 phase={'main_search': 0.097779, 'quiescence': 33.984579}
* gen_bilateral_random_6_201:opening: wall=33.262s nodes=79 qnodes=9921 phase={'main_search': 0.051338, 'quiescence': 33.210339}
* gen_classic_like_4_101:opening: wall=11.825s nodes=406 qnodes=9594 phase={'main_search': 0.259826, 'quiescence': 11.565019}
* hb_forced_promo:immediate_capture: wall=9.229s nodes=3213 qnodes=6787 phase={'main_search': 1.958008, 'quiescence': 7.27133}

## 5. Core 微基准（每调用中位数，秒）

### gen_bilateral_random_6_201:high_branching (legal=35, pseudo/legal=1.114)
* drop_action_generation: 5.9e-05s
* is_in_check: 6.72e-05s
* legal_successors: 0.01515s
* legality_filter_per_action: 7.37e-05s
* mechanical_transition: 7.2e-06s
* move_generation_legal: 0.003067s
* position_key: 4.99e-05s
* pseudo_action_expansion: 0.00015s
* pseudo_action_generation: 6.38e-05s
* pseudo_attacks_owner0: 5.51e-05s
* pseudo_attacks_owner1: 6.26e-05s
* repetition_update: 2.5e-06s
* terminal_detection: 0.0001538s

### gen_bilateral_random_6_201:opening (legal=20, pseudo/legal=1.0)
* drop_action_generation: 7e-07s
* is_in_check: 5.12e-05s
* legal_successors: 0.007239s
* legality_filter_per_action: 7.84e-05s
* mechanical_transition: 7e-06s
* move_generation_legal: 0.001721s
* position_key: 4.98e-05s
* pseudo_action_expansion: 0.000117s
* pseudo_action_generation: 7.39e-05s
* pseudo_attacks_owner0: 4.95e-05s
* pseudo_attacks_owner1: 4.97e-05s
* repetition_update: 1.9e-06s
* terminal_detection: 0.0001701s

### gen_classic_like_4_101:opening (legal=4, pseudo/legal=1.0)
* drop_action_generation: 7e-07s
* is_in_check: 4.14e-05s
* legal_successors: 0.00102s
* legality_filter_per_action: 4.63e-05s
* mechanical_transition: 7.2e-06s
* move_generation_legal: 0.0002354s
* position_key: 3.73e-05s
* pseudo_action_expansion: 4.38e-05s
* pseudo_action_generation: 3.68e-05s
* pseudo_attacks_owner0: 3.73e-05s
* pseudo_attacks_owner1: 3.71e-05s
* repetition_update: 1.9e-06s
* terminal_detection: 9.1e-05s

### hb_forced_promo:immediate_capture (legal=9, pseudo/legal=1.333)
* drop_action_generation: 8e-07s
* is_in_check: 2.35e-05s
* legal_successors: 0.001413s
* legality_filter_per_action: 2.75e-05s
* mechanical_transition: 4.8e-06s
* move_generation_legal: 0.000347s
* position_key: 2.9e-05s
* pseudo_action_expansion: 3.78e-05s
* pseudo_action_generation: 2.95e-05s
* pseudo_attacks_owner0: 1.85e-05s
* pseudo_attacks_owner1: 1.78e-05s
* repetition_update: 5.2e-06s
* terminal_detection: 6.5e-05s

## 6. Cache

* 9b1e5e1b6930: cold=0.012s warm=0.000s disk=0.003s serialized=1863B
* 888f110e93ae: cold=0.105s warm=0.000s disk=0.002s serialized=2292B
* b6f8d41e0cfd: cold=0.013s warm=0.000s disk=0.002s serialized=1461B

## 7. Profiler

### cProfile gen_bilateral_random_6_201:high_branching
```
         10870038 function calls (10852155 primitive calls) in 14.969 seconds

   Ordered by: cumulative time
   List reduced from 101 to 12 due to restriction <12>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000   16.591   16.591 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\player.py:72(choose_action)
        1    0.000    0.000   16.591   16.591 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\search.py:524(run_root_search)
      5/1    0.000    0.000   16.467   16.467 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\search.py:144(negamax)
   1460/3    0.033    0.000   16.415    5.472 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\search.py:349(quiescence)
      530    0.009    0.000   13.316    0.025 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:61(legal_successors)
    50057    4.459    0.000   11.572    0.000 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\attacks.py:34(pseudo_attacks)
    47927    0.190    0.000   11.365    0.000 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\attacks.py:58(is_square_attacked)
    38317    0.124    0.000   10.395    0.000 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\movegen.py:193(_is_legal)
      531    0.071    0.000    7.461    0.014 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\movegen.py:202(legal_actions_from_position)
     5949    0.009    0.000    5.858    0.001 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:78(<genexpr>)
     5419    0.052    0.000    5.849    0.001 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:28(_transition)
     5419    0.028    0.000    4.975    0.001 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\terminal.py:45(_terminal_from_parts)



```
### cProfile gen_classic_like_4_101:opening
```
         3464099 function calls (3447898 primitive calls) in 5.129 seconds

   Ordered by: cumulative time
   List reduced from 108 to 12 due to restriction <12>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    5.686    5.686 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\player.py:72(choose_action)
        1    0.000    0.000    5.686    5.686 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\search.py:524(run_root_search)
     35/3    0.002    0.000    5.677    1.892 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\search.py:144(negamax)
  1461/25    0.027    0.000    5.632    0.225 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\search.py:349(quiescence)
      687    0.008    0.000    3.735    0.005 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:61(legal_successors)
    26116    1.328    0.000    3.290    0.000 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\attacks.py:34(pseudo_attacks)
    23876    0.082    0.000    3.139    0.000 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\attacks.py:58(is_square_attacked)
    14351    0.047    0.000    2.312    0.000 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\movegen.py:193(_is_legal)
     4781    0.007    0.000    2.199    0.000 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:78(<genexpr>)
     4094    0.038    0.000    2.192    0.001 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:28(_transition)
     4094    0.021    0.000    1.690    0.000 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\terminal.py:45(_terminal_from_parts)
     4094    0.032    0.000    1.613    0.000 C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\movegen.py:221(has_legal_action)



```
### tracemalloc gen_bilateral_random_6_201:high_branching peak=233215
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\repetition.py:12: 28816B x 447
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:78: 7096B x 93
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\position.py:49: 4696B x 84
* <string>:5: 3352B x 53
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:40: 3168B x 44
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\position.py:40: 1800B x 30
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\keys.py:30: 1176B x 21
* C:\Users\icywo\AppData\Local\Programs\Python\Python313\Lib\json\encoder.py:252: 896B x 8
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\movegen.py:183: 840B x 15
* <string>:39: 728B x 13
### tracemalloc gen_classic_like_4_101:opening peak=79948
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\repetition.py:12: 19360B x 229
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:78: 16960B x 135
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\transition.py:40: 3240B x 45
* C:\Users\icywo\AppData\Local\Programs\Python\Python313\Lib\json\encoder.py:252: 2128B x 19
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\keys.py:39: 1260B x 12
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\position.py:40: 1160B x 22
* C:\Users\icywo\AppData\Local\Programs\Python\Python313\Lib\json\__init__.py:234: 1040B x 10
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\ai\alphabeta\transposition.py:107: 768B x 7
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\movegen.py:186: 672B x 4
* C:\Users\icywo\PycharmProjects\GenericChess\generic_chess\core\movegen.py:164: 616B x 11

## 8. 结论

* instrumented_subsystem_shares: {'evaluation': 0.0003, 'move_generation': 0.0235, 'ordering': 0.0009, 'position_key': 0.0005, 'tt': 0.0001}
* legal_successors_to_movegen_ratio: 4.39
* phase_inclusive_shares: {'main_search': 0.0268, 'quiescence': 0.9732}
* position_key_to_successors_ratio: 0.0168
* qsearch_gross_share: 0.9732
* recommendation: qsearch 占 instrumented 时间主导（>50%）：先处理 qsearch 节点爆炸与 per-child 构造成本，再做 native；建议完整 NativeSearchBackend 而非单函数 FFI。

## 9. 定向 fixture 覆盖

* targeted_multi_evasion: ['multi_evasion']
* targeted_near_repetition: ['near_repetition']
* targeted_checking_drop: ['checking_drop']
* targeted_nonchecking_drop: ['nonchecking_drop']
* targeted_low_anchor_escape: ['low_anchor_escape']
* targeted_low_branching: ['low_branching']
* 仍缺失类别: []

## 10. qsearch 修改前后（同一命令，10k nodes, 1 warm-up + 3 repeats）

| fixture | baseline wall (s) | after wall (s) | wall ratio | baseline nodes | after nodes |
| --- | ---: | ---: | ---: | ---: | ---: |
| gen_bilateral_random_6_201:high_branching | 51.886 | 32.872 | 0.634 | 10000 | 10000 |
| gen_classic_like_4_101:opening | 10.382 | 11.838 | 1.14 | 7857 | 10000 |
| gen_hybrid:high_branching | 182.969 | 8.258 | 0.045 | 10000 | 1047 |
| gen_leap_heavy:opening | 28.401 | 38.457 | 1.354 | 10000 | 10000 |
| hb_forced_promo:endgame | 6.573 | 7.362 | 1.12 | 10000 | 10000 |
| hb_multi_promo:immediate_capture | 12.068 | 10.501 | 0.87 | 10000 | 10000 |

## 11. Lazy successor 实验（eager vs lazy, 10k nodes）

| fixture | action/depth equal | eager total_nps | lazy total_nps | lazy materialized |
| --- | --- | ---: | ---: | ---: |
| gen_bilateral_random_6_201:high_branching | True | 303.5 | 298.0 | 72 |
| gen_classic_like_4_101:opening | True | 872.0 | 862.6 | 398 |
| hb_forced_promo:endgame | True | 1401.5 | 1643.8 | 5405 |
| hb_multi_promo:immediate_capture | True | 963.4 | 1180.8 | 3277 |

* 说明：node-budget 结果受单机环境影响；子系统占比用于定位瓶颈，不代表正常运行的绝对 NPS。