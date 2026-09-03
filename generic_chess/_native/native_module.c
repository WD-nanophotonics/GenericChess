#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <stdlib.h>
#include <string.h>
#include <limits.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <time.h>
#endif

#include "native_types.h"
#include "native_attack.h"
#include "native_cancel.h"
#include "native_clock.h"
#include "native_eval.h"
#include "native_hash.h"
#include "native_movegen.h"
#include "native_perft.h"
#include "native_rules.h"
#include "native_search.h"
#include "native_state.h"
#include "native_tt.h"
#include "native_semantic_rules.h"
#include "native_semantic_state.h"
#include "native_semantic_key.h"
#include "native_semantic_runtime.h"
#include "native_sha256.h"

#define GC_RULES_CAPSULE "generic_chess._native_core.gc_rules"
#define GC_POSITION_CAPSULE "generic_chess._native_core.gc_position"
#define GC_EVAL_CAPSULE "generic_chess._native_core.gc_eval"
#define GC_ENGINE_CAPSULE "generic_chess._native_core.gc_engine"
#define GC_CANCEL_CAPSULE "generic_chess._native_core.gc_cancel"
#define GC_SEM_RULES_CAPSULE "generic_chess._native_core.gc_semantic_rules"
#define GC_SEM_POSITION_CAPSULE "generic_chess._native_core.gc_semantic_position"

static PyObject *gc_native_error = NULL;

static int gc_semantic_require_matching_rules(const GCSemanticRules *rules,
                                              const GCSemanticPosition *position) {
    if (gc_semantic_position_matches_rules(position, rules)) return 1;
    PyErr_SetString(PyExc_ValueError,
                    "semantic position ruleset fingerprint does not match rules capsule");
    return 0;
}

typedef struct {
    GCRules *rules;
    GCEvaluationTables *eval;
    GCTable *tt;
    int busy;
} GCSearchEngine;

static void gc_rules_capsule_free(PyObject *capsule) {
    GCRules *rules = (GCRules *)PyCapsule_GetPointer(capsule, GC_RULES_CAPSULE);
    if (rules != NULL) {
        gc_rules_free(rules);
    }
}

static void gc_position_capsule_free(PyObject *capsule) {
    GCPosition *pos = (GCPosition *)PyCapsule_GetPointer(capsule,
                                                         GC_POSITION_CAPSULE);
    if (pos != NULL) {
        free(pos);
    }
}

static void gc_eval_capsule_free(PyObject *capsule) {
    GCEvaluationTables *eval = (GCEvaluationTables *)PyCapsule_GetPointer(
        capsule, GC_EVAL_CAPSULE);
    if (eval != NULL) {
        gc_eval_free(eval);
    }
}

static void gc_engine_capsule_free(PyObject *capsule) {
    GCSearchEngine *engine = (GCSearchEngine *)PyCapsule_GetPointer(
        capsule, GC_ENGINE_CAPSULE);
    if (engine != NULL) {
        gc_tt_free(engine->tt);
        free(engine);
    }
}

static void gc_cancel_capsule_free(PyObject *capsule) {
    GCCancelFlag *flag = (GCCancelFlag *)PyCapsule_GetPointer(
        capsule, GC_CANCEL_CAPSULE);
    if (flag != NULL) {
        gc_cancel_flag_destroy(flag);
    }
}

static void gc_semantic_rules_capsule_free(PyObject *capsule) {
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(
        capsule, GC_SEM_RULES_CAPSULE);
    if (rules != NULL) {
        gc_semantic_rules_free(rules);
    }
}

static void gc_semantic_position_capsule_free(PyObject *capsule) {
    GCSemanticPosition *pos = (GCSemanticPosition *)PyCapsule_GetPointer(
        capsule, GC_SEM_POSITION_CAPSULE);
    if (pos != NULL) free(pos);
}

static uint64_t gc_py_long_as_u64(PyObject *obj, int *ok) {
    unsigned long long value = PyLong_AsUnsignedLongLong(obj);
    if (value == (unsigned long long)-1 && PyErr_Occurred()) {
        *ok = 0;
        return 0;
    }
    return (uint64_t)value;
}

static long gc_py_long_as_long(PyObject *obj, int *ok) {
    long value = PyLong_AsLong(obj);
    if (value == -1 && PyErr_Occurred()) {
        *ok = 0;
        return 0;
    }
    return value;
}

static PyObject *gc_native_available(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    Py_RETURN_TRUE;
}

static PyObject *gc_native_version(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    return PyUnicode_FromString("0.5.0");
}

static const char *gc_status_name(int status) {
    switch (status) {
        case GC_STATUS_HISTORY_FULL: return "history_full";
        case GC_STATUS_HAND_OVERFLOW: return "hand_overflow";
        case GC_STATUS_ACTION_INVALID_KIND: return "invalid_kind";
        case GC_STATUS_ACTION_RESERVED_BITS: return "reserved_bits";
        case GC_STATUS_ACTION_TO_OUT_OF_RANGE: return "to_out_of_range";
        case GC_STATUS_ACTION_FROM_OUT_OF_RANGE: return "from_out_of_range";
        case GC_STATUS_ACTION_FROM_NOT_SENTINEL: return "from_not_sentinel";
        case GC_STATUS_ACTION_BASE_OUT_OF_RANGE: return "base_out_of_range";
        case GC_STATUS_ACTION_PROMO_OUT_OF_RANGE: return "promo_out_of_range";
        case GC_STATUS_ACTION_PROMO_SENTINEL_INVALID: return "promo_sentinel_invalid";
        case GC_STATUS_ACTION_NOT_LEGAL: return "not_legal";
        case GC_STATUS_ACTION_NO_MOVER: return "no_mover";
        case GC_STATUS_ACTION_WRONG_OWNER: return "wrong_owner";
        case GC_STATUS_ACTION_BASE_MISMATCH: return "base_mismatch";
        case GC_STATUS_ACTION_TARGET_FRIENDLY: return "target_friendly";
        case GC_STATUS_ACTION_CAPTURE_ANCHOR: return "capture_anchor";
        case GC_STATUS_ACTION_DROP_NO_HAND: return "drop_no_hand";
        case GC_STATUS_ACTION_DROP_OCCUPIED: return "drop_occupied";
        case GC_STATUS_ACTION_DROP_MASK: return "drop_mask";
        case GC_STATUS_ACTION_PROMO_NOT_CANDIDATE: return "promo_not_candidate";
        case GC_STATUS_ACTION_PROMO_PAIR_INVALID: return "promo_pair_invalid";
        case GC_STATUS_ACTION_PROMO_FORCED_OMITTED: return "promo_forced_omitted";
        case GC_STATUS_ACTION_ALREADY_PROMOTED: return "already_promoted";
        case GC_STATUS_ACTION_SELF_CHECK: return "self_check";
        case GC_STATUS_MEMORY: return "memory";
        default: return "ok";
    }
}

static PyObject *gc_action_error(GCPackedAction action, const GCRules *rules,
                                 int status, int ply) {
    PyObject *dict = PyDict_New();
    if (dict == NULL) {
        return NULL;
    }
    PyObject *value;
#define GC_SET_ERR_ITEM(name, obj) \
    do { \
        if ((obj) == NULL || PyDict_SetItemString(dict, (name), (obj)) != 0) { \
            Py_XDECREF(obj); \
            Py_DECREF(dict); \
            return NULL; \
        } \
        Py_DECREF(obj); \
    } while (0)
    value = PyLong_FromLong(status);
    GC_SET_ERR_ITEM("status", value);
    value = PyLong_FromUnsignedLongLong(action);
    GC_SET_ERR_ITEM("packed", value);
    value = PyLong_FromLong((long)GC_ACTION_KIND(action));
    GC_SET_ERR_ITEM("kind", value);
    value = PyLong_FromLong((long)GC_ACTION_FROM(action));
    GC_SET_ERR_ITEM("from", value);
    value = PyLong_FromLong((long)GC_ACTION_TO(action));
    GC_SET_ERR_ITEM("to", value);
    value = PyLong_FromLong((long)GC_ACTION_BASE(action));
    GC_SET_ERR_ITEM("base", value);
    value = PyLong_FromLong((long)GC_ACTION_PROMO(action));
    GC_SET_ERR_ITEM("promo", value);
    value = PyUnicode_FromString(rules->fingerprint);
    GC_SET_ERR_ITEM("fingerprint", value);
    value = PyUnicode_FromString(gc_status_name(status));
    GC_SET_ERR_ITEM("reason", value);
    value = PyLong_FromLong(ply);
    GC_SET_ERR_ITEM("ply", value);
#undef GC_SET_ERR_ITEM
    PyErr_SetObject(gc_native_error, dict);
    Py_DECREF(dict);
    return NULL;
}

static void gc_move_list_error(const GCRules *rules, const GCPosition *pos,
                               const GCMoveList *list) {
    if (list->error == GC_MOVE_ERROR_TRUSTED_MAKE) {
        PyObject *dict = PyDict_New();
        if (dict == NULL) {
            return;
        }
        PyObject *value;
#define GC_SET_ERR2(name, obj) \
    do { \
        if ((obj) == NULL || PyDict_SetItemString(dict, (name), (obj)) != 0) { \
            Py_XDECREF(obj); \
            Py_DECREF(dict); \
            PyErr_SetString(PyExc_RuntimeError, \
                            "trusted make failed during legal move generation"); \
            return; \
        } \
        Py_DECREF(obj); \
    } while (0)
        value = PyLong_FromUnsignedLongLong(list->failed_action);
        GC_SET_ERR2("packed", value);
        value = PyLong_FromLong(list->trusted_status);
        GC_SET_ERR2("status", value);
        value = PyUnicode_FromString(gc_status_name(list->trusted_status));
        GC_SET_ERR2("reason", value);
        value = PyLong_FromLong(pos->ply);
        GC_SET_ERR2("ply", value);
        value = PyLong_FromLong(pos->side_to_move);
        GC_SET_ERR2("side", value);
        value = PyUnicode_FromString(rules->fingerprint);
        GC_SET_ERR2("fingerprint", value);
        PyObject *hands = PyList_New(2);
        if (hands == NULL) {
            Py_DECREF(dict);
            return;
        }
        int owner;
        for (owner = 0; owner < 2; owner++) {
            PyObject *counts = PyList_New(rules->type_count);
            int t;
            for (t = 0; t < rules->type_count; t++) {
                PyList_SET_ITEM(counts, t,
                                PyLong_FromLong(pos->hand_counts[owner][t]));
            }
            PyList_SET_ITEM(hands, owner, counts);
        }
        PyDict_SetItemString(dict, "hand_counts", hands);
        Py_DECREF(hands);
#undef GC_SET_ERR2
        PyErr_SetObject(PyExc_RuntimeError, dict);
        Py_DECREF(dict);
        return;
    }
    PyErr_SetString(PyExc_MemoryError,
                    list->error == GC_MOVE_ERROR_OVERFLOW
                        ? "native move list overflow"
                        : "native move list allocation failed");
}

static PyObject *gc_native_capabilities(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    PyObject *dict = PyDict_New();
    if (dict == NULL) {
        return NULL;
    }
    PyObject *value;
    value = PyUnicode_FromString("C17 + CPython C API (zig cc x86_64-windows-gnu build)");
    PyDict_SetItemString(dict, "binding", value);
    Py_DECREF(value);
    value = PyLong_FromLong(GC_MAX_SQUARES);
    PyDict_SetItemString(dict, "max_squares", value);
    Py_DECREF(value);
    value = PyLong_FromLong(GC_MAX_TYPES);
    PyDict_SetItemString(dict, "max_types", value);
    Py_DECREF(value);
    value = PyLong_FromLong(GC_MAX_ACTIONS);
    PyDict_SetItemString(dict, "legacy_max_actions", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "make_unmake", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "native_perft", value);
    Py_DECREF(value);
    value = PyUnicode_FromString("native-0.5.0");
    PyDict_SetItemString(dict, "native_schema", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "semantic_ir_v2_compile", value);
    Py_DECREF(value);
    value = PyLong_FromLong(GC_SEMANTIC_PAYLOAD_VERSION);
    PyDict_SetItemString(dict, "semantic_payload_version", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "semantic_exact_action_identity", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "semantic_position_state", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "semantic_s0_s4_executor", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "hash_includes_base_type", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "complete_history_replay", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "checked_public_actions", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "dynamic_move_lists", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "fixed_depth_alphabeta", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "repetition_context_hash", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "transposition_table", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "iterative_deepening", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "node_budget", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "monotonic_time_budget", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "native_cancellation", value);
    Py_DECREF(value);
    value = PyBool_FromLong(0);
    PyDict_SetItemString(dict, "native_qsearch", value);
    Py_DECREF(value);
    value = PyBool_FromLong(0);
    PyDict_SetItemString(dict, "production_dynamic_evaluator", value);
    Py_DECREF(value);
    value = PyBool_FromLong(0);
    PyDict_SetItemString(dict, "production_search_backend", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "semantic_terminal", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "semantic_fixed_depth_search", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "semantic_material_evaluator", value);
    Py_DECREF(value);
    return dict;
}

/* ------------------------------------------------------------ rules compile */

static PyObject *gc_compile_rules(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *payload;
    if (!PyArg_ParseTuple(args, "O", &payload)) {
        return NULL;
    }
    if (!PyDict_Check(payload)) {
        PyErr_SetString(PyExc_TypeError, "compile_rules expects a dict payload");
        return NULL;
    }
    int ok = 1;
    PyObject *fingerprint = PyDict_GetItemString(payload, "fingerprint");
    PyObject *width_obj = PyDict_GetItemString(payload, "width");
    PyObject *height_obj = PyDict_GetItemString(payload, "height");
    PyObject *repetition_obj = PyDict_GetItemString(payload, "repetition_limit");
    PyObject *max_ply_obj = PyDict_GetItemString(payload, "max_ply");
    PyObject *types = PyDict_GetItemString(payload, "types");
    if (!fingerprint || !width_obj || !height_obj || !repetition_obj ||
        !max_ply_obj || !types || !PyList_Check(types)) {
        PyErr_SetString(PyExc_ValueError, "compile_rules payload missing fields");
        return NULL;
    }

    GCCompiledPayload cp;
    memset(&cp, 0, sizeof(cp));
    const char *fp = PyUnicode_AsUTF8(fingerprint);
    if (fp == NULL) {
        return NULL;
    }
    strncpy(cp.fingerprint, fp, 64);
    cp.fingerprint[64] = '\0';
    cp.width = (int)gc_py_long_as_long(width_obj, &ok);
    cp.height = (int)gc_py_long_as_long(height_obj, &ok);
    cp.repetition_limit = (int)gc_py_long_as_long(repetition_obj, &ok);
    cp.max_ply = (int)gc_py_long_as_long(max_ply_obj, &ok);
    if (!ok) {
        return NULL;
    }
    cp.type_count = (int)PyList_Size(types);
    if (cp.type_count <= 0 || cp.type_count > GC_MAX_TYPES) {
        PyErr_SetString(PyExc_ValueError, "type_count out of range");
        return NULL;
    }
    if (cp.width <= 0 || cp.height <= 0 ||
        cp.width * cp.height > GC_MAX_SQUARES) {
        PyErr_SetString(PyExc_ValueError, "board dimensions out of range");
        return NULL;
    }
    if (cp.max_ply <= 0 || cp.max_ply > GC_MAX_PLY) {
        PyErr_SetString(PyExc_ValueError, "max_ply out of native range");
        return NULL;
    }

    int t;
    for (t = 0; t < cp.type_count; t++) {
        PyObject *type_dict = PyList_GetItem(types, t);
        if (!PyDict_Check(type_dict)) {
            gc_payload_free_pairs(&cp);
            PyErr_SetString(PyExc_TypeError, "type entry must be a dict");
            return NULL;
        }
        PyObject *anchor = PyDict_GetItemString(type_dict, "is_anchor");
        PyObject *promotable = PyDict_GetItemString(type_dict, "is_promotable");
        PyObject *atoms = PyDict_GetItemString(type_dict, "atoms");
        PyObject *promo_targets = PyDict_GetItemString(type_dict, "promo_targets");
        PyObject *promo_allowed = PyDict_GetItemString(type_dict, "promo_allowed");
        PyObject *promo_forced = PyDict_GetItemString(type_dict, "promo_forced");
        PyObject *alive_promo = PyDict_GetItemString(type_dict, "alive_promo");
        PyObject *drop_mask = PyDict_GetItemString(type_dict, "drop_mask");
        if (!anchor || !promotable || !atoms || !promo_targets ||
            !promo_allowed || !promo_forced || !alive_promo || !drop_mask ||
            !PyList_Check(atoms) || !PyList_Check(promo_targets) ||
            !PyList_Check(promo_allowed) || !PyList_Check(promo_forced) ||
            !PyList_Check(alive_promo) || !PyList_Check(drop_mask)) {
            gc_payload_free_pairs(&cp);
            PyErr_SetString(PyExc_ValueError, "type entry missing fields");
            return NULL;
        }
        cp.is_anchor[t] = (uint8_t)(PyObject_IsTrue(anchor));
        cp.is_promotable[t] = (uint8_t)(PyObject_IsTrue(promotable));
        cp.atom_count[t] = (uint8_t)PyList_Size(atoms);
        if (cp.atom_count[t] > GC_MAX_ATOMS) {
            gc_payload_free_pairs(&cp);
            PyErr_SetString(PyExc_ValueError, "too many atoms per type");
            return NULL;
        }
        int a;
        for (a = 0; a < cp.atom_count[t]; a++) {
            PyObject *atom_dict = PyList_GetItem(atoms, a);
            PyObject *kind = PyDict_GetItemString(atom_dict, "kind");
            PyObject *df = PyDict_GetItemString(atom_dict, "df");
            PyObject *dr = PyDict_GetItemString(atom_dict, "dr");
            PyObject *max_steps = PyDict_GetItemString(atom_dict, "max_steps");
            if (!kind || !df || !dr || !max_steps) {
                gc_payload_free_pairs(&cp);
                PyErr_SetString(PyExc_ValueError, "atom entry incomplete");
                return NULL;
            }
            if (PyObject_IsTrue(kind)) {
                cp.atoms[t][a].kind = 1;
            } else {
                cp.atoms[t][a].kind = 0;
            }
            cp.atoms[t][a].vec.df = (int16_t)gc_py_long_as_long(df, &ok);
            cp.atoms[t][a].vec.dr = (int16_t)gc_py_long_as_long(dr, &ok);
            if (max_steps == Py_None) {
                cp.atoms[t][a].max_steps = 0;
            } else {
                cp.atoms[t][a].max_steps =
                    (uint8_t)gc_py_long_as_long(max_steps, &ok);
            }
            if (!ok) {
                gc_payload_free_pairs(&cp);
                return NULL;
            }
        }
        cp.promo_target_count[t] = (uint8_t)PyList_Size(promo_targets);
        if (cp.promo_target_count[t] > GC_MAX_PROMO_TARGETS) {
            gc_payload_free_pairs(&cp);
            PyErr_SetString(PyExc_ValueError, "too many promotion targets");
            return NULL;
        }
        int pt;
        for (pt = 0; pt < cp.promo_target_count[t]; pt++) {
            cp.promo_targets[t][pt] =
                (GCTypeIndex)gc_py_long_as_long(
                    PyList_GetItem(promo_targets, pt), &ok);
        }
        if (!ok) {
            gc_payload_free_pairs(&cp);
            return NULL;
        }
        int owner;
        for (owner = 0; owner < 2; owner++) {
            PyObject *pairs = PyList_GetItem(promo_allowed, owner);
            PyObject *forced = PyList_GetItem(promo_forced, owner);
            PyObject *alive = PyList_GetItem(alive_promo, owner);
            PyObject *drop = PyList_GetItem(drop_mask, owner);
            cp.promo_pair_count[t][owner] = (uint32_t)PyList_Size(pairs);
            uint32_t n_pairs = cp.promo_pair_count[t][owner];
            if (n_pairs > 0) {
                cp.promo_pairs[t][owner] = (uint32_t *)malloc(
                    n_pairs * sizeof(uint32_t));
                if (cp.promo_pairs[t][owner] == NULL) {
                    gc_payload_free_pairs(&cp);
                    PyErr_NoMemory();
                    return NULL;
                }
                uint32_t i;
                for (i = 0; i < n_pairs; i++) {
                    cp.promo_pairs[t][owner][i] =
                        (uint32_t)gc_py_long_as_u64(
                            PyList_GetItem(pairs, (Py_ssize_t)i), &ok);
                }
            }
            Py_ssize_t forced_len = PyList_Size(forced);
            Py_ssize_t fi;
            for (fi = 0; fi < forced_len; fi++) {
                long idx = gc_py_long_as_long(PyList_GetItem(forced, fi), &ok);
                if (idx >= 0 && idx < GC_MAX_SQUARES) {
                    cp.promo_forced[t][owner][idx / 64] |=
                        (uint64_t)1 << (idx % 64);
                }
            }
            Py_ssize_t drop_len = PyList_Size(drop);
            Py_ssize_t di;
            for (di = 0; di < drop_len; di++) {
                long idx = gc_py_long_as_long(PyList_GetItem(drop, di), &ok);
                if (idx >= 0 && idx < GC_MAX_SQUARES) {
                    cp.drop_mask[t][owner][idx / 64] |=
                        (uint64_t)1 << (idx % 64);
                }
            }
            Py_ssize_t alive_len = PyList_Size(alive);
            Py_ssize_t sq;
            for (sq = 0; sq < alive_len && sq < GC_MAX_SQUARES; sq++) {
                cp.alive_promo[t][owner][sq] = gc_py_long_as_u64(
                    PyList_GetItem(alive, sq), &ok);
            }
            if (!ok) {
                gc_payload_free_pairs(&cp);
                return NULL;
            }
        }
    }

    GCRules *rules = gc_rules_compile(&cp);
    gc_payload_free_pairs(&cp);
    if (rules == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    return PyCapsule_New(rules, GC_RULES_CAPSULE, gc_rules_capsule_free);
}

static GCRules *gc_get_rules(PyObject *capsule) {
    if (!PyCapsule_CheckExact(capsule)) {
        PyErr_SetString(PyExc_TypeError, "expected a native rules capsule");
        return NULL;
    }
    return (GCRules *)PyCapsule_GetPointer(capsule, GC_RULES_CAPSULE);
}

static GCPosition *gc_get_position(PyObject *capsule) {
    if (!PyCapsule_CheckExact(capsule)) {
        PyErr_SetString(PyExc_TypeError, "expected a native position capsule");
        return NULL;
    }
    return (GCPosition *)PyCapsule_GetPointer(capsule, GC_POSITION_CAPSULE);
}

static GCEvaluationTables *gc_get_eval(PyObject *capsule) {
    if (!PyCapsule_CheckExact(capsule)) {
        PyErr_SetString(PyExc_TypeError, "expected a native evaluation capsule");
        return NULL;
    }
    return (GCEvaluationTables *)PyCapsule_GetPointer(capsule, GC_EVAL_CAPSULE);
}

/* ----------------------------------------------------------- board payload */

static int gc_parse_board_payload(GCRules *rules, PyObject *payload,
                                  GCBoardPayload *bp, int *ply_out) {
    int ok = 1;
    PyObject *side_obj = PyDict_GetItemString(payload, "side");
    PyObject *ply_obj = PyDict_GetItemString(payload, "ply");
    PyObject *board = PyDict_GetItemString(payload, "board");
    PyObject *hands = PyDict_GetItemString(payload, "hands");
    if (!side_obj || !ply_obj || !board || !hands ||
        !PyList_Check(board) || !PyList_Check(hands)) {
        PyErr_SetString(PyExc_ValueError, "pack payload missing fields");
        return 0;
    }
    memset(bp, 0, sizeof(*bp));
    bp->side_to_move = (uint8_t)gc_py_long_as_long(side_obj, &ok);
    bp->ply = (uint16_t)gc_py_long_as_long(ply_obj, &ok);
    *ply_out = (int)bp->ply;
    if (!ok) {
        return 0;
    }
    if (bp->side_to_move > 1) {
        PyErr_SetString(PyExc_ValueError, "side_to_move must be 0 or 1");
        return 0;
    }
    if (bp->ply > GC_MAX_PLY) {
        PyErr_SetString(PyExc_ValueError, "ply exceeds native max_ply");
        return 0;
    }
    Py_ssize_t board_len = PyList_Size(board);
    if (board_len != (Py_ssize_t)rules->squares) {
        PyErr_SetString(PyExc_ValueError, "board payload length mismatch");
        return 0;
    }
    Py_ssize_t sq;
    for (sq = 0; sq < board_len; sq++) {
        PyObject *cell = PyList_GetItem(board, sq);
        if (cell == Py_None) {
            continue;
        }
        if (!PyList_Check(cell) || PyList_Size(cell) != 4) {
            PyErr_SetString(PyExc_ValueError,
                            "board cell must be None or [base,current,owner,promoted]");
            return 0;
        }
        GCPiece *piece = &bp->board[sq];
        piece->base_type = (GCTypeIndex)gc_py_long_as_long(
            PyList_GetItem(cell, 0), &ok);
        piece->current_type = (GCTypeIndex)gc_py_long_as_long(
            PyList_GetItem(cell, 1), &ok);
        piece->owner = (uint8_t)gc_py_long_as_long(
            PyList_GetItem(cell, 2), &ok);
        piece->promoted = (uint8_t)gc_py_long_as_long(
            PyList_GetItem(cell, 3), &ok);
        if (!ok) {
            return 0;
        }
        if (piece->base_type >= rules->type_count ||
            piece->current_type >= rules->type_count) {
            PyErr_SetString(PyExc_ValueError,
                            "piece type index out of range in board payload");
            return 0;
        }
        if (piece->owner > 1 || piece->promoted > 1) {
            PyErr_SetString(PyExc_ValueError,
                            "piece owner/promoted must be 0 or 1");
            return 0;
        }
        piece->occupied = 1;
    }
    if (PyList_Size(hands) != 2) {
        PyErr_SetString(PyExc_ValueError, "hands payload must have two owners");
        return 0;
    }
    int owner;
    for (owner = 0; owner < 2; owner++) {
        PyObject *counts = PyList_GetItem(hands, owner);
        Py_ssize_t len = PyList_Size(counts);
        if (len != (Py_ssize_t)rules->type_count) {
            PyErr_SetString(PyExc_ValueError,
                            "hands payload length must equal type_count");
            return 0;
        }
        Py_ssize_t t;
        for (t = 0; t < len; t++) {
            long count = gc_py_long_as_long(PyList_GetItem(counts, t), &ok);
            if (!ok) {
                return 0;
            }
            if (count < 0 || count > GC_MAX_HAND) {
                PyErr_SetString(PyExc_ValueError,
                                "hand count exceeds native GC_MAX_HAND");
                return 0;
            }
            bp->hand_counts[owner][t] = (uint16_t)count;
        }
    }
    return 1;
}

static PyObject *gc_native_rules_info(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule;
    if (!PyArg_ParseTuple(args, "O", &rules_capsule)) {
        return NULL;
    }
    GCRules *rules = gc_get_rules(rules_capsule);
    if (rules == NULL) {
        return NULL;
    }
    PyObject *dict = PyDict_New();
    if (dict == NULL) {
        return NULL;
    }
    PyObject *value;
    value = PyLong_FromLong(rules->type_count);
    PyDict_SetItemString(dict, "type_count", value);
    Py_DECREF(value);
    value = PyLong_FromLong(rules->squares);
    PyDict_SetItemString(dict, "squares", value);
    Py_DECREF(value);
    value = PyLong_FromLong(rules->max_ply);
    PyDict_SetItemString(dict, "max_ply", value);
    Py_DECREF(value);
    PyObject *types = PyList_New(rules->type_count);
    int t;
    for (t = 0; t < rules->type_count; t++) {
        PyObject *entry = PyDict_New();
        PyObject *atom_count = PyLong_FromLong(rules->atom_count[t]);
        PyDict_SetItemString(entry, "atom_count", atom_count);
        Py_DECREF(atom_count);
        PyObject *atoms = PyList_New(rules->atom_count[t]);
        int a;
        for (a = 0; a < rules->atom_count[t]; a++) {
            PyObject *atom = Py_BuildValue(
                "(iii)", rules->atoms[t][a].kind, rules->atoms[t][a].vec.df,
                rules->atoms[t][a].vec.dr);
            PyList_SET_ITEM(atoms, a, atom);
        }
        PyDict_SetItemString(entry, "atoms", atoms);
        Py_DECREF(atoms);
        PyList_SET_ITEM(types, t, entry);
    }
    PyDict_SetItemString(dict, "types", types);
    Py_DECREF(types);
    return dict;
}

static PyObject *gc_pack_position(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule;
    PyObject *payload;
    if (!PyArg_ParseTuple(args, "OO", &rules_capsule, &payload)) {
        return NULL;
    }
    GCRules *rules = gc_get_rules(rules_capsule);
    if (rules == NULL) {
        return NULL;
    }
    if (!PyDict_Check(payload)) {
        PyErr_SetString(PyExc_TypeError, "pack_position expects a dict payload");
        return NULL;
    }
    GCBoardPayload bp;
    int ply = 0;
    if (!gc_parse_board_payload(rules, payload, &bp, &ply)) {
        return NULL;
    }
    PyObject *root_count_obj = PyDict_GetItemString(payload, "root_hash_count");
    if (root_count_obj == NULL) {
        PyErr_SetString(PyExc_ValueError, "pack_position missing root_hash_count");
        return NULL;
    }
    int ok = 1;
    bp.root_hash_count = (uint16_t)gc_py_long_as_long(root_count_obj, &ok);
    if (!ok) {
        return NULL;
    }
    GCPosition *pos = (GCPosition *)malloc(sizeof(GCPosition));
    if (pos == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    if (!gc_position_pack(pos, rules, &bp)) {
        free(pos);
        PyErr_SetString(PyExc_RuntimeError, "gc_position_pack failed");
        return NULL;
    }
    return PyCapsule_New(pos, GC_POSITION_CAPSULE, gc_position_capsule_free);
}

/* ------------------------------------------------------ move list results */

static PyObject *gc_list_to_tuple(GCMoveList *list) {
    PyObject *result = PyTuple_New((Py_ssize_t)list->count);
    if (result == NULL) {
        return NULL;
    }
    size_t i;
    for (i = 0; i < list->count; i++) {
        PyObject *value = PyLong_FromUnsignedLongLong(list->data[i]);
        if (value == NULL) {
            Py_DECREF(result);
            return NULL;
        }
        PyTuple_SET_ITEM(result, (Py_ssize_t)i, value);
    }
    return result;
}

static PyObject *gc_native_legal_actions(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule;
    PyObject *pos_capsule;
    if (!PyArg_ParseTuple(args, "OO", &rules_capsule, &pos_capsule)) {
        return NULL;
    }
    GCRules *rules = gc_get_rules(rules_capsule);
    GCPosition *pos = gc_get_position(pos_capsule);
    if (rules == NULL || pos == NULL) {
        return NULL;
    }
    GCMoveList list;
    gc_move_list_init(&list);
    if (!gc_legal_actions(rules, pos, &list)) {
        gc_move_list_error(rules, pos, &list);
        gc_move_list_destroy(&list);
        return NULL;
    }
    PyObject *result = gc_list_to_tuple(&list);
    gc_move_list_destroy(&list);
    return result;
}

static PyObject *gc_native_pseudo_actions(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule;
    PyObject *pos_capsule;
    if (!PyArg_ParseTuple(args, "OO", &rules_capsule, &pos_capsule)) {
        return NULL;
    }
    GCRules *rules = gc_get_rules(rules_capsule);
    GCPosition *pos = gc_get_position(pos_capsule);
    if (rules == NULL || pos == NULL) {
        return NULL;
    }
    GCMoveList list;
    gc_move_list_init(&list);
    if (!gc_pseudo_actions(rules, pos, &list)) {
        gc_move_list_error(rules, pos, &list);
        gc_move_list_destroy(&list);
        return NULL;
    }
    PyObject *result = gc_list_to_tuple(&list);
    gc_move_list_destroy(&list);
    return result;
}

static PyObject *gc_native_attack_map(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule;
    PyObject *pos_capsule;
    int by_owner;
    if (!PyArg_ParseTuple(args, "OOi", &rules_capsule, &pos_capsule,
                          &by_owner)) {
        return NULL;
    }
    GCRules *rules = gc_get_rules(rules_capsule);
    GCPosition *pos = gc_get_position(pos_capsule);
    if (rules == NULL || pos == NULL) {
        return NULL;
    }
    PyObject *result = PyTuple_New(0);
    int sq;
    for (sq = 0; sq < rules->squares; sq++) {
        if (gc_is_square_attacked(rules, pos, (GCSquare)sq,
                                  (uint8_t)by_owner)) {
            PyObject *value = PyLong_FromLong(sq);
            PyObject *list = PyList_New(1);
            PyList_SET_ITEM(list, 0, value);
            PyObject *tuple = PyList_AsTuple(list);
            Py_DECREF(list);
            PyObject *joined = PySequence_Concat(result, tuple);
            Py_DECREF(result);
            Py_DECREF(tuple);
            result = joined;
        }
    }
    return result;
}

static PyObject *gc_native_terminal(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule;
    PyObject *pos_capsule;
    if (!PyArg_ParseTuple(args, "OO", &rules_capsule, &pos_capsule)) {
        return NULL;
    }
    GCRules *rules = gc_get_rules(rules_capsule);
    GCPosition *pos = gc_get_position(pos_capsule);
    if (rules == NULL || pos == NULL) {
        return NULL;
    }
    GCMoveList legal;
    gc_move_list_init(&legal);
    GCTerminal term = gc_terminal(rules, pos, &legal);
    gc_move_list_destroy(&legal);
    if (term == (GCTerminal)-1) {
        PyErr_SetString(PyExc_MemoryError, "native move list allocation failed");
        return NULL;
    }
    switch (term) {
        case GC_TERM_CHECKMATE:
            return PyUnicode_FromString("checkmate");
        case GC_TERM_STALEMATE:
            return PyUnicode_FromString("stalemate");
        case GC_TERM_REPETITION:
            return PyUnicode_FromString("repetition");
        case GC_TERM_MAX_PLY:
            return PyUnicode_FromString("max_ply");
        default:
            return PyUnicode_FromString("ongoing");
    }
}

static PyObject *gc_build_snapshot(const GCRules *rules, const GCPosition *pos,
                                   GCTerminal term) {
    PyObject *dict = PyDict_New();
    if (dict == NULL) {
        return NULL;
    }
    PyObject *value;
    value = PyLong_FromLong(pos->side_to_move);
    PyDict_SetItemString(dict, "side_to_move", value);
    Py_DECREF(value);
    value = PyLong_FromLong(pos->ply);
    PyDict_SetItemString(dict, "ply", value);
    Py_DECREF(value);
    value = PyLong_FromUnsignedLongLong(pos->hash_lo);
    PyDict_SetItemString(dict, "hash_lo", value);
    Py_DECREF(value);
    value = PyLong_FromUnsignedLongLong(pos->hash_hi);
    PyDict_SetItemString(dict, "hash_hi", value);
    Py_DECREF(value);
    value = PyLong_FromLong(gc_repetition_count(rules, pos));
    PyDict_SetItemString(dict, "repetition_count", value);
    Py_DECREF(value);
    value = PyLong_FromUnsignedLongLong(pos->repetition_context_lo);
    PyDict_SetItemString(dict, "repetition_context_lo", value);
    Py_DECREF(value);
    value = PyLong_FromUnsignedLongLong(pos->repetition_context_hi);
    PyDict_SetItemString(dict, "repetition_context_hi", value);
    Py_DECREF(value);
    value = PyLong_FromLong(pos->history_complete);
    PyDict_SetItemString(dict, "history_complete", value);
    Py_DECREF(value);
    const char *terminal_name = "ongoing";
    switch (term) {
        case GC_TERM_CHECKMATE: terminal_name = "checkmate"; break;
        case GC_TERM_STALEMATE: terminal_name = "stalemate"; break;
        case GC_TERM_REPETITION: terminal_name = "repetition"; break;
        case GC_TERM_MAX_PLY: terminal_name = "max_ply"; break;
        default: break;
    }
    value = PyUnicode_FromString(terminal_name);
    PyDict_SetItemString(dict, "terminal", value);
    Py_DECREF(value);

    PyObject *board = PyList_New(rules->squares);
    PyObject *hands = PyList_New(2);
    if (board == NULL || hands == NULL) {
        Py_XDECREF(board);
        Py_XDECREF(hands);
        Py_DECREF(dict);
        return NULL;
    }
    GCSquare sq;
    for (sq = 0; sq < rules->squares; sq++) {
        const GCPiece *piece = &pos->board[sq];
        if (!piece->occupied) {
            Py_INCREF(Py_None);
            PyList_SET_ITEM(board, sq, Py_None);
        } else {
            PyObject *cell = Py_BuildValue("(iiii)", piece->base_type,
                                           piece->current_type, piece->owner,
                                           piece->promoted);
            PyList_SET_ITEM(board, sq, cell);
        }
    }
    int owner;
    for (owner = 0; owner < 2; owner++) {
        PyObject *counts = PyList_New(rules->type_count);
        int t;
        for (t = 0; t < rules->type_count; t++) {
            PyObject *count = PyLong_FromLong(pos->hand_counts[owner][t]);
            PyList_SET_ITEM(counts, t, count);
        }
        PyList_SET_ITEM(hands, owner, counts);
    }
    PyDict_SetItemString(dict, "board", board);
    PyDict_SetItemString(dict, "hands", hands);
    Py_DECREF(board);
    Py_DECREF(hands);
    return dict;
}

static PyObject *gc_native_child_snapshot(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule;
    PyObject *pos_capsule;
    unsigned long long action;
    if (!PyArg_ParseTuple(args, "OOK", &rules_capsule, &pos_capsule, &action)) {
        return NULL;
    }
    GCRules *rules = gc_get_rules(rules_capsule);
    GCPosition *pos = gc_get_position(pos_capsule);
    if (rules == NULL || pos == NULL) {
        return NULL;
    }
    GCPosition copy;
    memcpy(&copy, pos, sizeof(GCPosition));
    GCUndo undo;
    if (gc_make_move_verify(&copy, rules, (GCPackedAction)action, &undo) != 1) {
        PyErr_SetString(PyExc_ValueError, "native make failed for action");
        return NULL;
    }
    GCMoveList legal;
    gc_move_list_init(&legal);
    GCTerminal term = gc_terminal(rules, &copy, &legal);
    gc_move_list_destroy(&legal);
    if (term == (GCTerminal)-1) {
        PyErr_SetString(PyExc_MemoryError, "native move list allocation failed");
        return NULL;
    }
    PyObject *snapshot = gc_build_snapshot(rules, &copy, term);
    gc_unmake_move(&copy, rules, &undo);
    return snapshot;
}

static PyObject *gc_native_snapshot(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule;
    PyObject *pos_capsule;
    if (!PyArg_ParseTuple(args, "OO", &rules_capsule, &pos_capsule)) {
        return NULL;
    }
    GCRules *rules = gc_get_rules(rules_capsule);
    GCPosition *pos = gc_get_position(pos_capsule);
    if (rules == NULL || pos == NULL) {
        return NULL;
    }
    GCMoveList legal;
    gc_move_list_init(&legal);
    GCTerminal term = gc_terminal(rules, pos, &legal);
    gc_move_list_destroy(&legal);
    if (term == (GCTerminal)-1) {
        PyErr_SetString(PyExc_MemoryError, "native move list allocation failed");
        return NULL;
    }
    return gc_build_snapshot(rules, pos, term);
}

static PyObject *gc_native_make_unmake_roundtrip(PyObject *self,
                                                 PyObject *args) {
    (void)self;
    PyObject *rules_capsule;
    PyObject *pos_capsule;
    unsigned long long action;
    if (!PyArg_ParseTuple(args, "OOK", &rules_capsule, &pos_capsule,
                          &action)) {
        return NULL;
    }
    GCRules *rules = gc_get_rules(rules_capsule);
    GCPosition *pos = gc_get_position(pos_capsule);
    if (rules == NULL || pos == NULL) {
        return NULL;
    }
    GCPosition copy;
    memcpy(&copy, pos, sizeof(GCPosition));
    GCUndo undo;
    if (!gc_make_move_verify(&copy, rules, (GCPackedAction)action, &undo)) {
        PyErr_SetString(PyExc_ValueError, "native make failed for action");
        return NULL;
    }
    int hash_after_make = gc_hash_verify(rules, &copy);
    gc_unmake_move(&copy, rules, &undo);
    int hash_restored = gc_hash_verify(rules, &copy);
    int same = copy.side_to_move == pos->side_to_move &&
               copy.ply == pos->ply &&
               copy.hash_lo == pos->hash_lo &&
               copy.hash_hi == pos->hash_hi &&
               copy.repetition_context_lo == pos->repetition_context_lo &&
               copy.repetition_context_hi == pos->repetition_context_hi &&
               copy.history_len == pos->history_len &&
               memcmp(copy.board, pos->board,
                      sizeof(GCPiece) * rules->squares) == 0 &&
               memcmp(copy.hand_counts, pos->hand_counts,
                      sizeof(pos->hand_counts)) == 0 &&
               memcmp(copy.history_lo, pos->history_lo,
                      sizeof(uint64_t) * copy.history_len) == 0 &&
               memcmp(copy.history_hi, pos->history_hi,
                      sizeof(uint64_t) * copy.history_len) == 0;
    return Py_BuildValue("{s:i,s:i,s:i,s:i}", "make_ok", 1,
                         "hash_after_make_ok", hash_after_make,
                         "hash_restored_ok", hash_restored,
                         "state_restored", same);
}

static PyObject *gc_native_long_make_unmake_roundtrip(PyObject *self,
                                                      PyObject *args) {
    (void)self;
    PyObject *rules_capsule;
    PyObject *payload;
    PyObject *actions;
    if (!PyArg_ParseTuple(args, "OOO", &rules_capsule, &payload, &actions)) {
        return NULL;
    }
    GCRules *rules = gc_get_rules(rules_capsule);
    if (rules == NULL) {
        return NULL;
    }
    if (!PyDict_Check(payload) || !PyTuple_Check(actions)) {
        PyErr_SetString(PyExc_TypeError,
                        "long_make_unmake expects (payload, actions tuple)");
        return NULL;
    }
    GCBoardPayload bp;
    int ply = 0;
    if (!gc_parse_board_payload(rules, payload, &bp, &ply)) {
        return NULL;
    }
    bp.root_hash_count = 0;
    GCPosition pos;
    if (!gc_position_pack(&pos, rules, &bp)) {
        PyErr_SetString(PyExc_RuntimeError, "gc_position_pack failed");
        return NULL;
    }
    GCPosition initial = pos;
    Py_ssize_t n = PyTuple_Size(actions);
    GCUndo *undo_stack = (GCUndo *)PyMem_Malloc(
        n > 0 ? (size_t)n * sizeof(GCUndo) : 1);
    if (undo_stack == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    int hash_verified = 1;
    Py_ssize_t i;
    for (i = 0; i < n; i++) {
        int ok = 1;
        uint64_t action = gc_py_long_as_u64(PyTuple_GetItem(actions, i), &ok);
        if (!ok) {
            PyMem_Free(undo_stack);
            return NULL;
        }
        int status = gc_make_move_checked(&pos, rules, (GCPackedAction)action,
                                          &undo_stack[i]);
        if (status != GC_STATUS_OK) {
            gc_action_error((GCPackedAction)action, rules, status, (int)i);
            PyMem_Free(undo_stack);
            return NULL;
        }
        if (!gc_hash_verify(rules, &pos)) {
            hash_verified = 0;
            break;
        }
        {
            uint64_t ctx_lo = pos.repetition_context_lo;
            uint64_t ctx_hi = pos.repetition_context_hi;
            gc_repetition_context_rebuild(&pos);
            if (pos.repetition_context_lo != ctx_lo ||
                pos.repetition_context_hi != ctx_hi) {
                hash_verified = 0;
                break;
            }
            pos.repetition_context_lo = ctx_lo;
            pos.repetition_context_hi = ctx_hi;
        }
    }
    int ok_all = 1;
    if (hash_verified) {
        for (i = n - 1; i >= 0; i--) {
            gc_unmake_move(&pos, rules, &undo_stack[i]);
        }
        ok_all = pos.side_to_move == initial.side_to_move &&
                 pos.ply == initial.ply &&
                 pos.hash_lo == initial.hash_lo &&
                 pos.hash_hi == initial.hash_hi &&
                 pos.repetition_context_lo == initial.repetition_context_lo &&
                 pos.repetition_context_hi == initial.repetition_context_hi &&
                 pos.history_len == initial.history_len &&
                 memcmp(pos.board, initial.board,
                        sizeof(GCPiece) * rules->squares) == 0 &&
                 memcmp(pos.hand_counts, initial.hand_counts,
                        sizeof(pos.hand_counts)) == 0 &&
                 memcmp(pos.history_lo, initial.history_lo,
                        sizeof(uint64_t) * pos.history_len) == 0 &&
                 memcmp(pos.history_hi, initial.history_hi,
                        sizeof(uint64_t) * pos.history_len) == 0;
    }
    PyMem_Free(undo_stack);
    return Py_BuildValue("{s:i,s:i,s:i,s:i}", "steps", (int)n,
                         "hash_verified", hash_verified,
                         "state_restored", ok_all,
                         "ok", hash_verified && ok_all);
}

/* -------------------------------------------------- checked public actions */

static PyObject *gc_native_make_checked(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule;
    PyObject *pos_capsule;
    unsigned long long action;
    if (!PyArg_ParseTuple(args, "OOK", &rules_capsule, &pos_capsule,
                          &action)) {
        return NULL;
    }
    GCRules *rules = gc_get_rules(rules_capsule);
    GCPosition *pos = gc_get_position(pos_capsule);
    if (rules == NULL || pos == NULL) {
        return NULL;
    }
    GCPosition copy;
    memcpy(&copy, pos, sizeof(GCPosition));
    GCUndo undo;
    int status = gc_make_move_checked(&copy, rules, (GCPackedAction)action,
                                      &undo);
    if (status != GC_STATUS_OK) {
        return gc_action_error((GCPackedAction)action, rules, status,
                               pos->ply);
    }
    GCMoveList legal;
    gc_move_list_init(&legal);
    GCTerminal term = gc_terminal(rules, &copy, &legal);
    gc_move_list_destroy(&legal);
    if (term == (GCTerminal)-1) {
        PyErr_SetString(PyExc_MemoryError, "native move list allocation failed");
        return NULL;
    }
    PyObject *snapshot = gc_build_snapshot(rules, &copy, term);
    gc_unmake_move(&copy, rules, &undo);
    return snapshot;
}

/* -------------------------------------------------------- history replay */

static PyObject *gc_native_replay_position(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule;
    PyObject *payload;
    PyObject *actions;
    if (!PyArg_ParseTuple(args, "OOO", &rules_capsule, &payload, &actions)) {
        return NULL;
    }
    GCRules *rules = gc_get_rules(rules_capsule);
    if (rules == NULL) {
        return NULL;
    }
    if (!PyDict_Check(payload) || !PyTuple_Check(actions)) {
        PyErr_SetString(PyExc_TypeError,
                        "replay_position expects (payload dict, actions tuple)");
        return NULL;
    }
    GCBoardPayload bp;
    int ply = 0;
    if (!gc_parse_board_payload(rules, payload, &bp, &ply)) {
        return NULL;
    }
    bp.root_hash_count = 0; /* full replay owns the whole history */
    GCPosition *pos = (GCPosition *)malloc(sizeof(GCPosition));
    if (pos == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    if (!gc_position_pack(pos, rules, &bp)) {
        free(pos);
        PyErr_SetString(PyExc_RuntimeError, "gc_position_pack failed");
        return NULL;
    }
    Py_ssize_t n = PyTuple_Size(actions);
    Py_ssize_t i;
    for (i = 0; i < n; i++) {
        int ok = 1;
        uint64_t action = gc_py_long_as_u64(PyTuple_GetItem(actions, i), &ok);
        if (!ok) {
            free(pos);
            return NULL;
        }
        GCUndo undo;
        int status = gc_make_move_checked(pos, rules, (GCPackedAction)action,
                                          &undo);
        if (status != GC_STATUS_OK) {
            gc_action_error((GCPackedAction)action, rules, status, (int)i);
            free(pos);
            return NULL;
        }
        if (!gc_hash_verify(rules, pos)) {
            gc_action_error((GCPackedAction)action, rules,
                            GC_STATUS_ACTION_NOT_LEGAL, (int)i);
            free(pos);
            return NULL;
        }
        {
            uint64_t ctx_lo = pos->repetition_context_lo;
            uint64_t ctx_hi = pos->repetition_context_hi;
            gc_repetition_context_rebuild(pos);
            if (pos->repetition_context_lo != ctx_lo ||
                pos->repetition_context_hi != ctx_hi) {
                PyErr_SetString(
                    PyExc_RuntimeError,
                    "repetition context mismatch during history replay");
                free(pos);
                return NULL;
            }
            pos->repetition_context_lo = ctx_lo;
            pos->repetition_context_hi = ctx_hi;
        }
    }
    return PyCapsule_New(pos, GC_POSITION_CAPSULE, gc_position_capsule_free);
}

/* -------------------------------------------------------------- perft */

static PyObject *gc_native_perft(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule;
    PyObject *pos_capsule;
    int depth;
    int divide = 0;
    if (!PyArg_ParseTuple(args, "OOi|p", &rules_capsule, &pos_capsule, &depth,
                          &divide)) {
        return NULL;
    }
    GCRules *rules = gc_get_rules(rules_capsule);
    GCPosition *pos = gc_get_position(pos_capsule);
    if (rules == NULL || pos == NULL) {
        return NULL;
    }
    if (depth < 0) {
        PyErr_SetString(PyExc_ValueError, "perft depth must be >= 0");
        return NULL;
    }
#ifdef _WIN32
    LARGE_INTEGER freq, t0;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&t0);
#else
    struct timespec t0;
    clock_gettime(CLOCK_MONOTONIC, &t0);
#endif

    GCPerftScratch scratch;
    gc_perft_scratch_init(&scratch);
    uint64_t total = 0;
    PyObject *divide_dict = NULL;
    int failed = 0;
    if (divide) {
        GCMoveList probe;
        gc_move_list_init(&probe);
        if (!gc_legal_actions(rules, pos, &probe)) {
            failed = 1;
        }
        size_t n = probe.count;
        gc_move_list_destroy(&probe);
        if (!failed) {
            uint64_t *counts = (uint64_t *)PyMem_Malloc(
                n > 0 ? n * sizeof(uint64_t) : 1);
            GCMoveList root_moves;
            gc_move_list_init(&root_moves);
            if (counts == NULL ||
                !gc_perft_divide(rules, pos, depth, &scratch, &root_moves,
                                 counts, &total)) {
                failed = 1;
            } else {
                divide_dict = PyDict_New();
                if (divide_dict == NULL) {
                    failed = 1;
                } else {
                    size_t k;
                    for (k = 0; k < root_moves.count; k++) {
                        PyObject *key = PyLong_FromUnsignedLongLong(
                            root_moves.data[k]);
                        PyObject *value = PyLong_FromUnsignedLongLong(
                            counts[k]);
                        PyDict_SetItem(divide_dict, key, value);
                        Py_DECREF(key);
                        Py_DECREF(value);
                    }
                }
            }
            gc_move_list_destroy(&root_moves);
            PyMem_Free(counts);
        }
    } else {
        if (!gc_perft(rules, pos, depth, &scratch, &total)) {
            failed = 1;
        }
    }
    if (failed) {
        Py_XDECREF(divide_dict);
        const GCMoveList *err_list = NULL;
        int li;
        for (li = 0; li < 2; li++) {
            if (scratch.legal[li].error != GC_MOVE_ERROR_NONE) {
                err_list = &scratch.legal[li];
                break;
            }
        }
        if (err_list == NULL) {
            for (li = 0; li < 2; li++) {
                if (scratch.pseudo[li].error != GC_MOVE_ERROR_NONE) {
                    err_list = &scratch.pseudo[li];
                    break;
                }
            }
        }
        gc_perft_scratch_destroy(&scratch);
        if (err_list != NULL) {
            gc_move_list_error(rules, pos, err_list);
        } else {
            PyErr_SetString(PyExc_MemoryError,
                            "native perft move list failure");
        }
        return NULL;
    }
    gc_perft_scratch_destroy(&scratch);

#ifdef _WIN32
    LARGE_INTEGER t1;
    QueryPerformanceCounter(&t1);
    double elapsed = (double)(t1.QuadPart - t0.QuadPart) / (double)freq.QuadPart;
#else
    struct timespec t1;
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double elapsed = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;
#endif

    PyObject *result = PyDict_New();
    if (result == NULL) {
        Py_XDECREF(divide_dict);
        return NULL;
    }
    PyObject *value;
    value = PyLong_FromLong(depth);
    PyDict_SetItemString(result, "depth", value);
    Py_DECREF(value);
    value = PyLong_FromUnsignedLongLong(total);
    PyDict_SetItemString(result, "nodes", value);
    Py_DECREF(value);
    value = PyFloat_FromDouble(elapsed);
    PyDict_SetItemString(result, "elapsed_seconds", value);
    Py_DECREF(value);
    value = PyFloat_FromDouble(elapsed > 0 ? (double)total / elapsed : 0.0);
    PyDict_SetItemString(result, "nodes_per_second", value);
    Py_DECREF(value);
    if (divide_dict != NULL) {
        PyDict_SetItemString(result, "divide", divide_dict);
        Py_DECREF(divide_dict);
    }
    return result;
}

/* -------------------------------------------------- evaluation tables */

static PyObject *gc_compile_evaluation(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule;
    PyObject *payload;
    if (!PyArg_ParseTuple(args, "OO", &rules_capsule, &payload)) {
        return NULL;
    }
    GCRules *rules = gc_get_rules(rules_capsule);
    if (rules == NULL) {
        return NULL;
    }
    if (!PyDict_Check(payload)) {
        PyErr_SetString(PyExc_TypeError,
                        "compile_evaluation expects a dict payload");
        return NULL;
    }
    int ok = 1;
    PyObject *type_count_obj = PyDict_GetItemString(payload, "type_count");
    PyObject *mate_obj = PyDict_GetItemString(payload, "mate_score");
    PyObject *threshold_obj = PyDict_GetItemString(payload, "mate_threshold");
    PyObject *max_eval_obj = PyDict_GetItemString(payload, "max_static_eval");
    PyObject *config_hash_obj = PyDict_GetItemString(payload, "config_hash");
    PyObject *version_obj = PyDict_GetItemString(payload, "evaluator_version");
    PyObject *board_values = PyDict_GetItemString(payload, "board_value");
    PyObject *hand_values = PyDict_GetItemString(payload, "hand_value");
    PyObject *promo_gains = PyDict_GetItemString(payload, "promotion_gain");
    if (!type_count_obj || !mate_obj || !threshold_obj || !max_eval_obj ||
        !config_hash_obj || !version_obj || !board_values || !hand_values ||
        !promo_gains || !PyList_Check(board_values) ||
        !PyList_Check(hand_values) || !PyList_Check(promo_gains)) {
        PyErr_SetString(PyExc_ValueError, "evaluation payload missing fields");
        return NULL;
    }
    long type_count = gc_py_long_as_long(type_count_obj, &ok);
    if (!ok) {
        return NULL;
    }
    if (type_count != (long)rules->type_count ||
        PyList_Size(board_values) != type_count ||
        PyList_Size(hand_values) != type_count ||
        PyList_Size(promo_gains) != type_count) {
        PyErr_SetString(PyExc_ValueError,
                        "evaluation table length does not match rules type_count");
        return NULL;
    }
    const char *config_hash = PyUnicode_AsUTF8(config_hash_obj);
    const char *version = PyUnicode_AsUTF8(version_obj);
    if (config_hash == NULL || version == NULL) {
        return NULL;
    }
    GCEvalPayload ep;
    memset(&ep, 0, sizeof(ep));
    ep.type_count = (int)type_count;
    ep.mate_score = (int32_t)gc_py_long_as_long(mate_obj, &ok);
    ep.mate_threshold = (int32_t)gc_py_long_as_long(threshold_obj, &ok);
    ep.max_static_eval = (int32_t)gc_py_long_as_long(max_eval_obj, &ok);
    if (!ok) {
        return NULL;
    }
    strncpy(ep.config_hash, config_hash, 64);
    ep.config_hash[64] = '\0';
    strncpy(ep.evaluator_version, version, 64);
    ep.evaluator_version[64] = '\0';
    Py_ssize_t t;
    for (t = 0; t < type_count; t++) {
        ep.board_value[t] = (int32_t)gc_py_long_as_long(
            PyList_GetItem(board_values, t), &ok);
        ep.hand_value[t] = (int32_t)gc_py_long_as_long(
            PyList_GetItem(hand_values, t), &ok);
        ep.promotion_gain[t] = (int32_t)gc_py_long_as_long(
            PyList_GetItem(promo_gains, t), &ok);
        if (!ok) {
            return NULL;
        }
    }
    GCEvaluationTables *eval = gc_eval_compile(&ep);
    if (eval == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    return PyCapsule_New(eval, GC_EVAL_CAPSULE, gc_eval_capsule_free);
}

/* --------------------------------------------------- fixed-depth search */

static PyObject *gc_run_fixed_depth_search(GCRules *rules,
                                           GCEvaluationTables *eval,
                                           GCPosition *pos, int depth,
                                           GCTable *tt) {
    if (depth < 0 || depth > GC_MAX_PLY) {
        PyErr_SetString(PyExc_ValueError,
                        "search depth must be in [0, GC_MAX_PLY]");
        return NULL;
    }
    GCPosition copy;
    memcpy(&copy, pos, sizeof(GCPosition));
    GCSearchContext ctx;
    if (!gc_search_context_alloc(&ctx, rules, eval, tt, (uint32_t)depth)) {
        PyErr_SetString(PyExc_ValueError,
                        "search context allocation failed (depth or memory)");
        return NULL;
    }
    GCFixedSearchResult result;
    int search_ok = 1;
    Py_BEGIN_ALLOW_THREADS
    search_ok = gc_fixed_depth_search(&ctx, &copy, (uint32_t)depth, &result);
    Py_END_ALLOW_THREADS
    PyObject *result_dict = NULL;
    PyObject *pv = NULL;
    PyObject *value = NULL;
    int success = 0;
    if (!search_ok) {
        PyErr_SetString(PyExc_RuntimeError, "native fixed-depth search failed");
        goto cleanup;
    }
    int restored = gc_hash_verify(rules, &copy) &&
                   memcmp(copy.board, pos->board,
                          sizeof(GCPiece) * rules->squares) == 0 &&
                   copy.side_to_move == pos->side_to_move &&
                   copy.ply == pos->ply &&
                   copy.history_len == pos->history_len &&
                   memcmp(copy.hand_counts, pos->hand_counts,
                          sizeof(pos->hand_counts)) == 0;
    if (!restored) {
        PyErr_SetString(PyExc_RuntimeError,
                        "native search did not restore the root position");
        goto cleanup;
    }

    result_dict = PyDict_New();
    if (result_dict == NULL) {
        goto cleanup;
    }
    value = PyLong_FromLong(result.score);
    if (value == NULL ||
        PyDict_SetItemString(result_dict, "score", value) != 0) {
        goto cleanup;
    }
    Py_CLEAR(value);
    if (result.has_action) {
        value = PyLong_FromUnsignedLongLong(result.best_action);
    } else {
        value = Py_None;
        Py_INCREF(value);
    }
    if (value == NULL ||
        PyDict_SetItemString(result_dict, "best_action", value) != 0) {
        goto cleanup;
    }
    Py_CLEAR(value);
    value = PyLong_FromUnsignedLongLong(result.nodes);
    if (value == NULL ||
        PyDict_SetItemString(result_dict, "nodes", value) != 0) {
        goto cleanup;
    }
    Py_CLEAR(value);
    value = PyLong_FromLong(result.completed_depth);
    if (value == NULL ||
        PyDict_SetItemString(result_dict, "completed_depth", value) != 0) {
        goto cleanup;
    }
    Py_CLEAR(value);
    value = PyUnicode_FromString(result.terminated ? "terminal"
                                                   : "completed_depth");
    if (value == NULL ||
        PyDict_SetItemString(result_dict, "termination_reason", value) != 0) {
        goto cleanup;
    }
    Py_CLEAR(value);
    value = PyLong_FromUnsignedLongLong(ctx.tt_probes);
    if (value == NULL ||
        PyDict_SetItemString(result_dict, "tt_probes", value) != 0) {
        goto cleanup;
    }
    Py_CLEAR(value);
    value = PyLong_FromUnsignedLongLong(ctx.tt_hits);
    if (value == NULL ||
        PyDict_SetItemString(result_dict, "tt_hits", value) != 0) {
        goto cleanup;
    }
    Py_CLEAR(value);
    value = PyLong_FromUnsignedLongLong(ctx.tt_cutoffs);
    if (value == NULL ||
        PyDict_SetItemString(result_dict, "tt_cutoffs", value) != 0) {
        goto cleanup;
    }
    Py_CLEAR(value);
    value = PyLong_FromUnsignedLongLong(ctx.tt_stores);
    if (value == NULL ||
        PyDict_SetItemString(result_dict, "tt_stores", value) != 0) {
        goto cleanup;
    }
    Py_CLEAR(value);
    value = PyLong_FromUnsignedLongLong(ctx.tt_replacements);
    if (value == NULL ||
        PyDict_SetItemString(result_dict, "tt_replacements", value) != 0) {
        goto cleanup;
    }
    Py_CLEAR(value);
    value = PyLong_FromUnsignedLongLong(ctx.beta_cutoffs);
    if (value == NULL ||
        PyDict_SetItemString(result_dict, "beta_cutoffs", value) != 0) {
        goto cleanup;
    }
    Py_CLEAR(value);
    value = PyLong_FromUnsignedLongLong(ctx.selective_depth);
    if (value == NULL ||
        PyDict_SetItemString(result_dict, "selective_depth", value) != 0) {
        goto cleanup;
    }
    Py_CLEAR(value);
    pv = PyTuple_New((Py_ssize_t)ctx.pv_length[0]);
    if (pv == NULL) {
        goto cleanup;
    }
    size_t k;
    for (k = 0; k < ctx.pv_length[0]; k++) {
        PyObject *item = PyLong_FromUnsignedLongLong(ctx.pv_table[k]);
        if (item == NULL) {
            goto cleanup;
        }
        PyTuple_SET_ITEM(pv, (Py_ssize_t)k, item);
    }
    if (PyDict_SetItemString(result_dict, "principal_variation", pv) != 0) {
        goto cleanup;
    }
    success = 1;

cleanup:
    Py_XDECREF(value);
    Py_XDECREF(pv);
    if (!success) {
        Py_XDECREF(result_dict);
        result_dict = NULL;
    }
    gc_search_context_free(&ctx);
    return result_dict;
}

static PyObject *gc_native_fixed_depth_search(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule;
    PyObject *eval_capsule;
    PyObject *pos_capsule;
    int depth;
    if (!PyArg_ParseTuple(args, "OOOi", &rules_capsule, &eval_capsule,
                          &pos_capsule, &depth)) {
        return NULL;
    }
    GCRules *rules = gc_get_rules(rules_capsule);
    GCEvaluationTables *eval = gc_get_eval(eval_capsule);
    GCPosition *pos = gc_get_position(pos_capsule);
    if (rules == NULL || eval == NULL || pos == NULL) {
        return NULL;
    }
    return gc_run_fixed_depth_search(rules, eval, pos, depth, NULL);
}

/* ---------------------------------------------------- search engine */

static GCSearchEngine *gc_get_engine(PyObject *capsule) {
    if (!PyCapsule_CheckExact(capsule)) {
        PyErr_SetString(PyExc_TypeError, "expected a native engine capsule");
        return NULL;
    }
    return (GCSearchEngine *)PyCapsule_GetPointer(capsule, GC_ENGINE_CAPSULE);
}

static PyObject *gc_create_search_engine(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule;
    PyObject *eval_capsule;
    long tt_megabytes;
    if (!PyArg_ParseTuple(args, "OOl", &rules_capsule, &eval_capsule,
                          &tt_megabytes)) {
        return NULL;
    }
    GCRules *rules = gc_get_rules(rules_capsule);
    GCEvaluationTables *eval = gc_get_eval(eval_capsule);
    if (rules == NULL || eval == NULL) {
        return NULL;
    }
    if (tt_megabytes < 0 || tt_megabytes > 1024) {
        PyErr_SetString(PyExc_ValueError,
                        "tt_megabytes must be in [0, 1024]");
        return NULL;
    }
    GCSearchEngine *engine = (GCSearchEngine *)calloc(1, sizeof(GCSearchEngine));
    if (engine == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    engine->rules = rules;
    engine->eval = eval;
    if (tt_megabytes > 0) {
        size_t requested = (size_t)tt_megabytes * 1024 * 1024;
        size_t allocated = 0;
        engine->tt = gc_tt_create(requested, &allocated);
        if (engine->tt == NULL) {
            free(engine);
            PyErr_NoMemory();
            return NULL;
        }
    }
    return PyCapsule_New(engine, GC_ENGINE_CAPSULE, gc_engine_capsule_free);
}

static PyObject *gc_search_engine_clear_tt(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *engine_capsule;
    if (!PyArg_ParseTuple(args, "O", &engine_capsule)) {
        return NULL;
    }
    GCSearchEngine *engine = gc_get_engine(engine_capsule);
    if (engine == NULL) {
        return NULL;
    }
    gc_tt_clear(engine->tt);
    Py_RETURN_NONE;
}

static PyObject *gc_search_engine_tt_info(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *engine_capsule;
    if (!PyArg_ParseTuple(args, "O", &engine_capsule)) {
        return NULL;
    }
    GCSearchEngine *engine = gc_get_engine(engine_capsule);
    if (engine == NULL) {
        return NULL;
    }
    PyObject *dict = PyDict_New();
    if (dict == NULL) {
        return NULL;
    }
    PyObject *value;
    if (engine->tt == NULL) {
        value = PyLong_FromLong(0);
        PyDict_SetItemString(dict, "requested_bytes", value);
        Py_DECREF(value);
        value = PyLong_FromLong(0);
        PyDict_SetItemString(dict, "allocated_bytes", value);
        Py_DECREF(value);
        value = PyLong_FromLong(0);
        PyDict_SetItemString(dict, "bucket_count", value);
        Py_DECREF(value);
        value = PyLong_FromLong(0);
        PyDict_SetItemString(dict, "entry_capacity", value);
        Py_DECREF(value);
        value = PyLong_FromLong((long)sizeof(GCTTEntry));
        PyDict_SetItemString(dict, "entry_size", value);
        Py_DECREF(value);
        value = PyLong_FromLong(0);
        PyDict_SetItemString(dict, "generation", value);
        Py_DECREF(value);
        value = PyLong_FromLong(0);
        PyDict_SetItemString(dict, "occupied_entries", value);
        Py_DECREF(value);
        return dict;
    }
    value = PyLong_FromUnsignedLongLong(engine->tt->requested_bytes);
    PyDict_SetItemString(dict, "requested_bytes", value);
    Py_DECREF(value);
    value = PyLong_FromUnsignedLongLong(engine->tt->allocated_bytes);
    PyDict_SetItemString(dict, "allocated_bytes", value);
    Py_DECREF(value);
    value = PyLong_FromUnsignedLongLong(engine->tt->bucket_count);
    PyDict_SetItemString(dict, "bucket_count", value);
    Py_DECREF(value);
    value = PyLong_FromUnsignedLongLong(
        engine->tt->bucket_count * GC_TT_WAYS);
    PyDict_SetItemString(dict, "entry_capacity", value);
    Py_DECREF(value);
    value = PyLong_FromLong((long)sizeof(GCTTEntry));
    PyDict_SetItemString(dict, "entry_size", value);
    Py_DECREF(value);
    value = PyLong_FromUnsignedLongLong(engine->tt->generation);
    PyDict_SetItemString(dict, "generation", value);
    Py_DECREF(value);
    value = PyLong_FromUnsignedLongLong(engine->tt->occupied_entries);
    PyDict_SetItemString(dict, "occupied_entries", value);
    Py_DECREF(value);
    return dict;
}

static PyObject *gc_engine_fixed_depth_search(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *engine_capsule;
    PyObject *pos_capsule;
    int depth;
    if (!PyArg_ParseTuple(args, "OOi", &engine_capsule, &pos_capsule,
                          &depth)) {
        return NULL;
    }
    GCSearchEngine *engine = gc_get_engine(engine_capsule);
    GCPosition *pos = gc_get_position(pos_capsule);
    if (engine == NULL || pos == NULL) {
        return NULL;
    }
    if (engine->busy) {
        PyErr_SetString(PyExc_RuntimeError, "search engine is busy");
        return NULL;
    }
    engine->busy = 1;
    PyObject *result = gc_run_fixed_depth_search(
        engine->rules, engine->eval, pos, depth, engine->tt);
    engine->busy = 0;
    return result;
}

static GCCancelFlag *gc_get_cancel(PyObject *capsule) {
    if (!PyCapsule_CheckExact(capsule)) {
        PyErr_SetString(PyExc_TypeError, "expected a native cancel capsule");
        return NULL;
    }
    return (GCCancelFlag *)PyCapsule_GetPointer(capsule, GC_CANCEL_CAPSULE);
}

static PyObject *gc_create_cancel_flag(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    GCCancelFlag *flag = gc_cancel_flag_create();
    if (flag == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    return PyCapsule_New(flag, GC_CANCEL_CAPSULE, gc_cancel_capsule_free);
}

static PyObject *gc_request_cancel(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *cancel_capsule;
    if (!PyArg_ParseTuple(args, "O", &cancel_capsule)) {
        return NULL;
    }
    GCCancelFlag *flag = gc_get_cancel(cancel_capsule);
    if (flag == NULL) {
        return NULL;
    }
    gc_cancel_flag_request(flag);
    Py_RETURN_NONE;
}

static PyObject *gc_native_iterative_search(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *engine_capsule;
    PyObject *pos_capsule;
    PyObject *cancel_capsule;
    int max_depth;
    PyObject *max_nodes_obj;
    PyObject *max_time_obj;
    if (!PyArg_ParseTuple(args, "OOiOOO", &engine_capsule, &pos_capsule,
                          &max_depth, &max_nodes_obj, &max_time_obj,
                          &cancel_capsule)) {
        return NULL;
    }
    GCSearchEngine *engine = gc_get_engine(engine_capsule);
    GCPosition *pos = gc_get_position(pos_capsule);
    if (engine == NULL || pos == NULL) {
        return NULL;
    }
    GCCancelFlag *cancel = NULL;
    if (cancel_capsule != Py_None) {
        cancel = gc_get_cancel(cancel_capsule);
        if (cancel == NULL) {
            return NULL;
        }
    }
    if (engine->busy) {
        PyErr_SetString(PyExc_RuntimeError, "search engine is busy");
        return NULL;
    }
    if (max_depth < 0 || max_depth > GC_MAX_PLY) {
        PyErr_SetString(PyExc_ValueError,
                        "max_depth must be in [0, GC_MAX_PLY]");
        return NULL;
    }
    int ok = 1;
    uint64_t max_nodes = GC_NODES_UNLIMITED;
    uint64_t max_time_ns = GC_TIME_UNLIMITED;
    if (max_nodes_obj != Py_None) {
        long long v = PyLong_AsLongLong(max_nodes_obj);
        if (v == -1 && PyErr_Occurred()) {
            return NULL;
        }
        if (v < 0) {
            PyErr_SetString(PyExc_ValueError, "max_nodes must be >= 0");
            return NULL;
        }
        max_nodes = (uint64_t)v;
    }
    if (max_time_obj != Py_None) {
        double seconds = PyFloat_AsDouble(max_time_obj);
        if (PyErr_Occurred()) {
            return NULL;
        }
        if (seconds < 0 || seconds != seconds || seconds > 1e12) {
            PyErr_SetString(PyExc_ValueError,
                            "max_time_seconds must be a finite "
                            "non-negative number");
            return NULL;
        }
        max_time_ns = (uint64_t)(seconds * 1e9);
    }
    if (pos->history_complete != 1) {
        PyErr_SetString(
            PyExc_ValueError,
            "iterative native search requires full GameSession history replay");
        return NULL;
    }
    if (!gc_hash_verify(engine->rules, pos)) {
        PyErr_SetString(PyExc_RuntimeError, "root hash verification failed");
        return NULL;
    }

    engine->busy = 1;
    GCPosition copy;
    memcpy(&copy, pos, sizeof(GCPosition));
    GCSearchContext ctx;
    PyObject *result_dict = NULL;
    PyObject *pv = NULL;
    PyObject *value = NULL;
    int success = 0;
    if (!gc_search_context_alloc(&ctx, engine->rules, engine->eval,
                                 engine->tt, (uint32_t)max_depth)) {
        engine->busy = 0;
        PyErr_SetString(PyExc_ValueError,
                        "search context allocation failed (depth or memory)");
        return NULL;
    }
    uint64_t start_ns = gc_monotonic_ns();
    GCFixedSearchResult result;
    int search_ok = 1;
    Py_BEGIN_ALLOW_THREADS
    search_ok = gc_iterative_search(&ctx, &copy, (uint32_t)max_depth,
                                    max_nodes, max_time_ns, cancel, &result);
    Py_END_ALLOW_THREADS
    uint64_t elapsed_ns = gc_monotonic_ns() - start_ns;
    engine->busy = 0;
    if (!search_ok) {
        PyErr_SetString(PyExc_RuntimeError, "native iterative search failed");
        goto cleanup;
    }
    {
        int restored = gc_hash_verify(engine->rules, &copy) &&
                       copy.side_to_move == pos->side_to_move &&
                       copy.ply == pos->ply &&
                       copy.history_len == pos->history_len &&
                       memcmp(copy.board, pos->board,
                              sizeof(GCPiece) * engine->rules->squares) == 0 &&
                       memcmp(copy.hand_counts, pos->hand_counts,
                              sizeof(pos->hand_counts)) == 0;
        if (!restored) {
            PyErr_SetString(PyExc_RuntimeError,
                            "native search did not restore the root position");
            goto cleanup;
        }
    }

    result_dict = PyDict_New();
    if (result_dict == NULL) {
        goto cleanup;
    }
#define GC_SET_RESULT(name, obj) \
    do { \
        if ((obj) == NULL || PyDict_SetItemString(result_dict, (name), (obj)) != 0) { \
            goto cleanup; \
        } \
        Py_CLEAR(value); \
    } while (0)
    value = PyLong_FromLong(result.score);
    GC_SET_RESULT("score", value);
    if (result.has_action) {
        value = PyLong_FromUnsignedLongLong(result.best_action);
    } else {
        value = Py_None;
        Py_INCREF(value);
    }
    GC_SET_RESULT("best_action", value);
    value = PyLong_FromUnsignedLongLong(result.nodes);
    GC_SET_RESULT("nodes", value);
    value = PyLong_FromLong(result.completed_depth);
    GC_SET_RESULT("completed_depth", value);
    value = PyLong_FromUnsignedLongLong(ctx.selective_depth);
    GC_SET_RESULT("selective_depth", value);
    value = PyLong_FromLong(0);
    GC_SET_RESULT("qnodes", value);
    value = PyFloat_FromDouble((double)elapsed_ns / 1e9);
    GC_SET_RESULT("elapsed_seconds", value);
    value = PyBool_FromLong(result.used_fallback);
    GC_SET_RESULT("used_fallback", value);
    {
        const char *reason = "internal_error";
        if (result.terminated) {
            reason = "terminal_position";
        } else if (result.used_fallback) {
            switch (ctx.control) {
                case GC_SEARCH_ABORT_NODE_LIMIT: reason = "node_limit"; break;
                case GC_SEARCH_ABORT_TIME_LIMIT: reason = "time_limit"; break;
                case GC_SEARCH_ABORT_CANCELLED: reason = "cancelled"; break;
                default: reason = "internal_error"; break;
            }
        } else if (ctx.final_control != GC_SEARCH_CONTINUE) {
            switch (ctx.final_control) {
                case GC_SEARCH_ABORT_NODE_LIMIT: reason = "node_limit"; break;
                case GC_SEARCH_ABORT_TIME_LIMIT: reason = "time_limit"; break;
                case GC_SEARCH_ABORT_CANCELLED: reason = "cancelled"; break;
                default: reason = "internal_error"; break;
            }
        } else {
            reason = "completed_depth";
        }
        value = PyUnicode_FromString(reason);
        GC_SET_RESULT("termination_reason", value);
    }
    value = PyLong_FromUnsignedLongLong(ctx.tt_probes);
    GC_SET_RESULT("tt_probes", value);
    value = PyLong_FromUnsignedLongLong(ctx.tt_hits);
    GC_SET_RESULT("tt_hits", value);
    value = PyLong_FromUnsignedLongLong(ctx.tt_cutoffs);
    GC_SET_RESULT("tt_cutoffs", value);
    value = PyLong_FromUnsignedLongLong(ctx.tt_stores);
    GC_SET_RESULT("tt_stores", value);
    value = PyLong_FromUnsignedLongLong(ctx.tt_replacements);
    GC_SET_RESULT("tt_replacements", value);
    value = PyLong_FromUnsignedLongLong(ctx.beta_cutoffs);
    GC_SET_RESULT("beta_cutoffs", value);
#undef GC_SET_RESULT
    pv = PyTuple_New((Py_ssize_t)result.pv_length);
    if (pv == NULL) {
        goto cleanup;
    }
    size_t k;
    for (k = 0; k < result.pv_length; k++) {
        PyObject *item = PyLong_FromUnsignedLongLong(result.pv[k]);
        if (item == NULL) {
            goto cleanup;
        }
        PyTuple_SET_ITEM(pv, (Py_ssize_t)k, item);
    }
    if (PyDict_SetItemString(result_dict, "principal_variation", pv) != 0) {
        goto cleanup;
    }
    success = 1;

cleanup:
    Py_XDECREF(value);
    Py_XDECREF(pv);
    if (!success) {
        Py_XDECREF(result_dict);
        result_dict = NULL;
    }
    gc_search_context_free(&ctx);
    return result_dict;
}

/* ------------------------------------------------------- semantic payload */

static PyObject *gc_semantic_pack_position(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule, *payload;
    if (!PyArg_ParseTuple(args, "OO", &rules_capsule, &payload)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(
        rules_capsule, GC_SEM_RULES_CAPSULE);
    if (rules == NULL || !PyDict_Check(payload)) {
        if (rules == NULL) return NULL;
        PyErr_SetString(PyExc_TypeError, "semantic_pack_position expects dict payload");
        return NULL;
    }
    PyObject *board = PyDict_GetItemString(payload, "board");
    PyObject *hands = PyDict_GetItemString(payload, "hands");
    PyObject *side_obj = PyDict_GetItemString(payload, "side");
    PyObject *ply_obj = PyDict_GetItemString(payload, "ply");
    if (!PyList_Check(board) || !PyList_Check(hands) || !side_obj || !ply_obj) {
        PyErr_SetString(PyExc_ValueError, "semantic position payload missing fields");
        return NULL;
    }
    GCSemanticBoardPayload bp;
    memset(&bp, 0, sizeof(bp));
    bp.history_exact = 1;
    int ok = 1;
    bp.side_to_move = (uint8_t)gc_py_long_as_long(side_obj, &ok);
    bp.ply = (uint16_t)gc_py_long_as_long(ply_obj, &ok);
    const uint16_t squares = (uint16_t)(rules->board_size * rules->board_size);
    if (!ok || bp.side_to_move > 1 || bp.ply > rules->max_ply ||
        PyList_Size(board) != squares || PyList_Size(hands) != 2) {
        PyErr_SetString(PyExc_ValueError, "invalid semantic position scalar or board shape");
        return NULL;
    }
    for (uint16_t sq = 0; sq < squares; sq++) {
        PyObject *cell = PyList_GetItem(board, sq);
        if (cell == Py_None) continue;
        if (!PyList_Check(cell) || PyList_Size(cell) != 4) {
            PyErr_SetString(PyExc_ValueError, "semantic board cell must be None or [base,current,owner,promoted]");
            return NULL;
        }
        GCPiece *piece = &bp.board[sq];
        piece->base_type = (uint16_t)gc_py_long_as_long(PyList_GetItem(cell, 0), &ok);
        piece->current_type = (uint16_t)gc_py_long_as_long(PyList_GetItem(cell, 1), &ok);
        piece->owner = (uint8_t)gc_py_long_as_long(PyList_GetItem(cell, 2), &ok);
        piece->promoted = (uint8_t)gc_py_long_as_long(PyList_GetItem(cell, 3), &ok);
        piece->occupied = 1;
        if (!ok || piece->base_type >= rules->type_count || piece->current_type >= rules->type_count || piece->owner > 1 || piece->promoted > 1) {
            PyErr_SetString(PyExc_ValueError, "invalid semantic board piece");
            return NULL;
        }
    }
    for (uint8_t owner = 0; owner < 2; owner++) {
        PyObject *counts = PyList_GetItem(hands, owner);
        if (!PyList_Check(counts) || PyList_Size(counts) != rules->type_count) {
            PyErr_SetString(PyExc_ValueError, "semantic hand shape mismatch");
            return NULL;
        }
        for (uint16_t t = 0; t < rules->type_count; t++) {
            long count = gc_py_long_as_long(PyList_GetItem(counts, t), &ok);
            if (!ok || count < 0 || count > GC_MAX_HAND) {
                PyErr_SetString(PyExc_ValueError, "invalid semantic hand count");
                return NULL;
            }
            bp.hand_counts[owner][t] = (uint16_t)count;
        }
    }
    PyObject *aux = PyDict_GetItemString(payload, "aux");
    if (aux != NULL) {
        if (!PyList_Check(aux)) { PyErr_SetString(PyExc_ValueError, "semantic aux must be a list"); return NULL; }
        for (Py_ssize_t i = 0; i < PyList_Size(aux); i++) {
            PyObject *entry = PyList_GetItem(aux, i);
            if (!PyList_Check(entry) || PyList_Size(entry) != 3) { PyErr_SetString(PyExc_ValueError, "semantic aux entry shape invalid"); return NULL; }
            long slot = gc_py_long_as_long(PyList_GetItem(entry, 0), &ok);
            long owner = gc_py_long_as_long(PyList_GetItem(entry, 1), &ok);
            if (!ok || slot < 0 || slot >= rules->aux_slot_count || owner < -1 || owner > 1) { PyErr_SetString(PyExc_ValueError, "semantic aux slot/owner invalid"); return NULL; }
            GCSemAuxValue *value = &bp.aux[slot][owner < 0 ? 0 : owner + 1];
            PyObject *raw = PyList_GetItem(entry, 2);
            value->kind = rules->aux_slots[slot].value_kind;
            if (raw == Py_None) { value->has_value = 0; continue; }
            if (value->kind == 0) {
                long flag = gc_py_long_as_long(raw, &ok);
                if (!ok || (flag != 0 && flag != 1)) { PyErr_SetString(PyExc_ValueError, "semantic bool aux invalid"); return NULL; }
                value->has_value = 1; value->bool_value = (int32_t)flag;
            } else {
                if (!PyList_Check(raw) || PyList_Size(raw) != 2) { PyErr_SetString(PyExc_ValueError, "semantic square aux invalid"); return NULL; }
                long file = gc_py_long_as_long(PyList_GetItem(raw, 0), &ok); long rank = gc_py_long_as_long(PyList_GetItem(raw, 1), &ok);
                if (!ok || file < 0 || rank < 0 || file >= rules->board_size || rank >= rules->board_size) { PyErr_SetString(PyExc_ValueError, "semantic aux square out of range"); return NULL; }
                value->has_value = 1; value->square = (uint16_t)(rank * rules->board_size + file);
            }
        }
    }
    PyObject *history = PyDict_GetItemString(payload, "history");
    int history_events_complete = 1;
    if (history != NULL) {
        if (!PyList_Check(history) || PyList_Size(history) > GC_SEM_MAX_PLY + 1) {
            PyErr_SetString(PyExc_ValueError, "semantic history must be a bounded list");
            return NULL;
        }
        bp.history_len = (uint16_t)PyList_Size(history);
        for (Py_ssize_t i = 0; i < PyList_Size(history); i++) {
            PyObject *entry = PyList_GetItem(history, i);
            if (!PyList_Check(entry) && !PyTuple_Check(entry)) {
                PyErr_SetString(PyExc_ValueError, "semantic history entry must be [lo, hi]");
                return NULL;
            }
            Py_ssize_t word_count = PySequence_Size(entry);
            if (word_count != 2 && word_count != 4 && word_count != 6) {
                PyErr_SetString(PyExc_ValueError, "semantic history entry must have two, four, or six words");
                return NULL;
            }
            if (word_count == 2) bp.history_exact = 0;
            if (word_count != 6) history_events_complete = 0;
            for (Py_ssize_t word = 0; word < word_count; word++) {
                PyObject *value = PySequence_GetItem(entry, word);
                unsigned long long raw = PyLong_AsUnsignedLongLong(value);
                Py_DECREF(value);
                if (PyErr_Occurred()) {
                    PyErr_SetString(PyExc_ValueError, "semantic history words must be unsigned 64-bit values");
                    return NULL;
                }
                if (word < 2) {
                    if (word == 0) bp.history_lo[i] = (uint64_t)raw;
                    else bp.history_hi[i] = (uint64_t)raw;
                }
                if (word < 4) bp.history_digest[i][word] = (uint64_t)raw;
                else if (word == 4) bp.history_actor[i] = (uint8_t)raw;
                else bp.history_gave_check[i] = (uint8_t)raw;
            }
            if (word_count == 6) {
                if ((bp.history_actor[i] > 1 &&
                     !(i == 0 && bp.history_actor[i] == 255)) ||
                    bp.history_gave_check[i] > 1) {
                    PyErr_SetString(PyExc_ValueError, "semantic history actor/check flag invalid");
                    return NULL;
                }
            }
        }
        bp.history_events_exact = history_events_complete ? 1 : 0;
    }
    PyObject *history_events = PyDict_GetItemString(payload, "history_events");
    if (history_events != NULL) {
        if (!PyList_Check(history_events) || PyList_Size(history_events) != bp.history_len) {
            PyErr_SetString(PyExc_ValueError, "semantic history_events length mismatch");
            return NULL;
        }
        for (Py_ssize_t i = 0; i < PyList_Size(history_events); i++) {
            PyObject *event = PyList_GetItem(history_events, i);
            if ((!PyList_Check(event) && !PyTuple_Check(event)) || PySequence_Size(event) != 2) {
                PyErr_SetString(PyExc_ValueError, "semantic history event must be [actor, gave_check]");
                return NULL;
            }
            int event_ok = 1;
            PyObject *actor_obj = PySequence_GetItem(event, 0);
            PyObject *gave_obj = PySequence_GetItem(event, 1);
            long actor = gc_py_long_as_long(actor_obj, &event_ok);
            long gave = gc_py_long_as_long(gave_obj, &event_ok);
            Py_XDECREF(actor_obj);
            Py_XDECREF(gave_obj);
            if (!event_ok || (actor < 0 || (actor > 1 && actor != 255)) || gave < 0 || gave > 1) {
                PyErr_SetString(PyExc_ValueError, "semantic history event is outside domain");
                return NULL;
            }
            bp.history_actor[i] = (uint8_t)actor;
            bp.history_gave_check[i] = (uint8_t)gave;
        }
        bp.history_events_exact = 1;
    }
    if (bp.history_events_exact && bp.history_len > 0 &&
        bp.history_actor[0] != 255) {
        /* A complete event stream must identify history[0] as the initial
         * sentinel.  Keep the import usable for ordinary repetition, but
         * fail closed for continuous-check/automatic adjudication. */
        bp.history_events_exact = 0;
    }
    GCSemanticPosition *pos = (GCSemanticPosition *)malloc(sizeof(*pos));
    if (pos == NULL) { PyErr_NoMemory(); return NULL; }
    if (!gc_semantic_position_pack(pos, rules, &bp)) {
        free(pos); PyErr_SetString(PyExc_ValueError, "semantic position pack rejected payload"); return NULL;
    }
    if (pos->history_len == 0) {
        char digest[65];
        if (!gc_semantic_position_key_digest(rules, pos, digest)) {
            free(pos); PyErr_SetString(PyExc_ValueError, "fresh semantic position cannot be canonically keyed"); return NULL;
        }
        uint64_t words[4] = {0, 0, 0, 0};
        for (int w = 0; w < 4; w++) for (int j = 0; j < 16; j++) {
            char c = digest[w * 16 + j];
            uint8_t n = (uint8_t)(c >= '0' && c <= '9' ? c - '0' : c - 'a' + 10);
            words[w] = (words[w] << 4) | n;
        }
        pos->history_lo[0] = words[0];
        pos->history_hi[0] = words[1];
        memcpy(pos->history_digest[0], words, sizeof(words));
        pos->history_actor[0] = 255;
        pos->history_gave_check[0] = 0;
        pos->history_len = 1;
        pos->history_events_exact = 1;
    }
    return PyCapsule_New(pos, GC_SEM_POSITION_CAPSULE, gc_semantic_position_capsule_free);
}

static PyObject *gc_semantic_position_snapshot(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule, *pos_capsule;
    if (!PyArg_ParseTuple(args, "OO", &rules_capsule, &pos_capsule)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(rules_capsule, GC_SEM_RULES_CAPSULE);
    GCSemanticPosition *pos = (GCSemanticPosition *)PyCapsule_GetPointer(pos_capsule, GC_SEM_POSITION_CAPSULE);
    if (rules == NULL || pos == NULL) return NULL;
    if (!gc_semantic_require_matching_rules(rules, pos)) return NULL;
    PyObject *out = Py_BuildValue("{s:i,s:i}", "side", pos->side_to_move, "ply", pos->ply);
    PyObject *board = PyList_New(rules->board_size * rules->board_size);
    for (uint16_t sq = 0; sq < rules->board_size * rules->board_size; sq++) {
        GCPiece *p = &pos->board[sq];
        PyObject *cell = p->occupied ? Py_BuildValue("(iiii)", p->base_type, p->current_type, p->owner, p->promoted) : Py_None;
        if (!p->occupied) Py_INCREF(Py_None);
        PyList_SET_ITEM(board, sq, cell);
    }
    PyDict_SetItemString(out, "board", board); Py_DECREF(board);
    PyObject *hands = PyList_New(2);
    for (uint8_t owner = 0; owner < 2; owner++) {
        PyObject *counts = PyList_New(rules->type_count);
        for (uint16_t t = 0; t < rules->type_count; t++) PyList_SET_ITEM(counts, t, PyLong_FromUnsignedLong(pos->hand_counts[owner][t]));
        PyList_SET_ITEM(hands, owner, counts);
    }
    PyDict_SetItemString(out, "hands", hands); Py_DECREF(hands);
    PyObject *aux = PyList_New(0);
    for (uint8_t slot = 0; slot < rules->aux_slot_count; slot++) {
        const GCSemAuxSlot *meta = &rules->aux_slots[slot];
        uint8_t first = meta->scope == 1 ? 1 : 0;
        uint8_t last = meta->scope == 1 ? 2 : 0;
        for (uint8_t idx = first; idx <= last; idx++) {
            const GCSemAuxValue *value = &pos->aux[slot][idx];
            long owner = meta->scope == 1 ? (long)idx - 1 : -1;
            PyObject *raw = Py_None; Py_INCREF(Py_None);
            if (value->has_value) {
                Py_DECREF(raw);
                if (value->kind == 0) raw = PyLong_FromLong(value->bool_value);
                else raw = Py_BuildValue("(ii)", value->square % rules->board_size,
                                         value->square / rules->board_size);
            }
            PyObject *entry = Py_BuildValue("(iiO)", meta->slot_id, owner, raw);
            Py_DECREF(raw);
            if (entry == NULL || PyList_Append(aux, entry) != 0) { Py_XDECREF(entry); Py_DECREF(aux); Py_DECREF(out); return NULL; }
            Py_DECREF(entry);
        }
    }
    PyDict_SetItemString(out, "aux_state", aux); Py_DECREF(aux);
    PyObject *history = PyList_New(pos->history_len);
    if (history == NULL) { Py_DECREF(out); return NULL; }
    for (uint16_t i = 0; i < pos->history_len; i++) {
        PyObject *entry = pos->history_exact
            ? Py_BuildValue("(KKKK)",
                            (unsigned long long)pos->history_digest[i][0],
                            (unsigned long long)pos->history_digest[i][1],
                            (unsigned long long)pos->history_digest[i][2],
                            (unsigned long long)pos->history_digest[i][3])
            : Py_BuildValue("(KK)",
                            (unsigned long long)pos->history_lo[i],
                            (unsigned long long)pos->history_hi[i]);
        if (entry == NULL) { Py_DECREF(history); Py_DECREF(out); return NULL; }
        PyList_SET_ITEM(history, i, entry);
    }
    PyDict_SetItemString(out, "history", history); Py_DECREF(history);
    PyObject *events = PyList_New(pos->history_len);
    if (events == NULL) { Py_DECREF(out); return NULL; }
    for (uint16_t i = 0; i < pos->history_len; i++) {
        PyObject *event = Py_BuildValue("(ii)", (int)pos->history_actor[i],
                                        (int)pos->history_gave_check[i]);
        if (event == NULL) { Py_DECREF(events); Py_DECREF(out); return NULL; }
        PyList_SET_ITEM(events, i, event);
    }
    PyDict_SetItemString(out, "history_events", events); Py_DECREF(events);
    PyObject *history_exact = PyLong_FromLong(pos->history_exact);
    PyObject *history_events_exact = PyLong_FromLong(pos->history_events_exact);
    if (!history_exact || !history_events_exact ||
        PyDict_SetItemString(out, "history_exact", history_exact) != 0 ||
        PyDict_SetItemString(out, "history_events_exact", history_events_exact) != 0) {
        Py_XDECREF(history_exact); Py_XDECREF(history_events_exact);
        Py_DECREF(out); return NULL;
    }
    Py_DECREF(history_exact); Py_DECREF(history_events_exact);
    uint64_t current_digest[4] = {0, 0, 0, 0};
    if (pos->history_len > 0) memcpy(current_digest, pos->history_digest[pos->history_len - 1], sizeof(current_digest));
    unsigned long occurrences = 0;
    for (uint16_t i = 0; i < pos->history_len; i++) {
        if (pos->history_exact) {
            if (memcmp(pos->history_digest[i], current_digest, sizeof(current_digest)) == 0) occurrences++;
        } else if (pos->history_lo[i] == current_digest[0] && pos->history_hi[i] == current_digest[1]) occurrences++;
    }
    PyObject *occ = PyLong_FromUnsignedLong(occurrences);
    if (occ == NULL) { Py_DECREF(out); return NULL; }
    PyDict_SetItemString(out, "history_occurrences", occ); Py_DECREF(occ);
    return out;
}

static PyObject *gc_semantic_position_key(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule, *pos_capsule;
    if (!PyArg_ParseTuple(args, "OO", &rules_capsule, &pos_capsule)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(rules_capsule, GC_SEM_RULES_CAPSULE);
    GCSemanticPosition *pos = (GCSemanticPosition *)PyCapsule_GetPointer(pos_capsule, GC_SEM_POSITION_CAPSULE);
    if (rules == NULL || pos == NULL) return NULL;
    if (!gc_semantic_require_matching_rules(rules, pos)) return NULL;
    char digest[65];
    if (!gc_semantic_position_key_digest(rules, pos, digest)) {
        PyErr_SetString(PyExc_ValueError, "semantic position cannot be canonically keyed");
        return NULL;
    }
    return PyUnicode_FromString(digest);
}

static PyObject *gc_sha256_hex_api(PyObject *self, PyObject *args) {
    (void)self;
    const char *data = NULL;
    Py_ssize_t length = 0;
    if (!PyArg_ParseTuple(args, "y#", &data, &length)) return NULL;
    GCSha256 ctx; uint8_t digest[32]; char hex[65];
    gc_sha256_init(&ctx);
    gc_sha256_update(&ctx, (const uint8_t *)data, (size_t)length);
    gc_sha256_final(&ctx, digest);
    gc_sha256_hex(digest, hex);
    return PyUnicode_FromString(hex);
}

static PyObject *gc_semantic_action_pack(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *fields;
    if (!PyArg_ParseTuple(args, "O", &fields) || !PyDict_Check(fields)) {
        PyErr_SetString(PyExc_TypeError, "semantic_action_pack expects a dict");
        return NULL;
    }
    const char *names[] = {"to", "from", "promotion", "base", "kind", "pattern", "geometry", "actor_current"};
    long v[8]; int ok = 1;
    for (int i = 0; i < 8; i++) {
        PyObject *obj = PyDict_GetItemString(fields, names[i]);
        if (!obj) { PyErr_Format(PyExc_ValueError, "semantic action missing %s", names[i]); return NULL; }
        v[i] = gc_py_long_as_long(obj, &ok);
        if (!ok) { PyErr_Format(PyExc_ValueError, "semantic action field %s is not an integer", names[i]); return NULL; }
    }
    if (v[0] < 0 || v[0] > 255 || v[1] < 0 || v[1] > 255 ||
        v[2] < 0 || v[2] > 255 || v[3] < 0 || v[3] > 255 ||
        (v[4] != GC_ACTION_KIND_SEMANTIC_BOARD && v[4] != GC_ACTION_KIND_SEMANTIC_DROP) ||
        v[5] < 0 || v[5] >= GC_ACTION_MAX_PATTERNS ||
        v[6] < 0 || v[6] >= GC_ACTION_MAX_GEOMETRIES || v[7] < 0 || v[7] > 255 ||
        (v[4] == GC_ACTION_KIND_SEMANTIC_DROP && v[1] != 255)) {
        PyErr_SetString(PyExc_ValueError, "semantic action field outside frozen layout domain");
        return NULL;
    }
    uint64_t action = ((uint64_t)v[0]) | ((uint64_t)v[1] << 8) |
        ((uint64_t)v[2] << 16) | ((uint64_t)v[3] << 24) |
        ((uint64_t)v[4] << 32) | ((uint64_t)v[5] << 36) |
        ((uint64_t)v[6] << 44) | ((uint64_t)v[7] << 56);
    return PyLong_FromUnsignedLongLong(action);
}

static PyObject *gc_semantic_action_unpack(PyObject *self, PyObject *args) {
    (void)self;
    unsigned long long raw;
    if (!PyArg_ParseTuple(args, "K", &raw)) return NULL;
    uint64_t action = (uint64_t)raw;
    uint64_t known = 0xFFFFFFFFFull | (GC_ACTION_PATTERN_MASK << GC_ACTION_PATTERN_SHIFT) |
        (GC_ACTION_GEOMETRY_MASK << GC_ACTION_GEOMETRY_SHIFT) |
        (GC_ACTION_ACTOR_CURRENT_MASK << GC_ACTION_ACTOR_CURRENT_SHIFT);
    if (action & ~known) { PyErr_SetString(PyExc_ValueError, "semantic action has reserved bits set"); return NULL; }
    uint64_t kind = (action >> GC_ACTION_KIND_SHIFT) & GC_ACTION_KIND_MASK;
    if (kind != GC_ACTION_KIND_SEMANTIC_BOARD && kind != GC_ACTION_KIND_SEMANTIC_DROP) {
        PyErr_SetString(PyExc_ValueError, "semantic action kind is not semantic"); return NULL;
    }
    if (kind == GC_ACTION_KIND_SEMANTIC_DROP && ((action >> 8) & 0xFFull) != 255ull) {
        PyErr_SetString(PyExc_ValueError, "semantic drop action requires the from-square sentinel"); return NULL;
    }
    return Py_BuildValue("{s:K,s:K,s:K,s:K,s:K,s:K,s:K,s:K}",
        "to", action & 0xFFull, "from", (action >> 8) & 0xFFull,
        "promotion", (action >> 16) & 0xFFull, "base", (action >> 24) & 0xFFull,
        "kind", kind, "pattern", (action >> 36) & 0xFFull,
        "geometry", (action >> 44) & 0xFFFull, "actor_current", (action >> 56) & 0xFFull);
}

static int gc_semantic_target_holds(uint8_t target_kind, const GCPiece *cell, uint8_t side) {
    if (target_kind == 0) return !cell->occupied;
    if (target_kind == 1) return cell->occupied && cell->owner != side;
    if (target_kind == 2) return cell->occupied && cell->owner == side;
    return target_kind == 3;
}

static int gc_semantic_path_holds(const GCSemPattern *pattern,
                                  const GCSemPathEntry *entry, uint16_t target_index,
                                  const GCSemanticPosition *pos, uint8_t side) {
    uint16_t occupied = 0;
    int first_owner = -1, last_owner = -1;
    for (uint16_t i = 0; i < target_index; i++) {
        const GCPiece *piece = &pos->board[entry->squares[i]];
        if (!piece->occupied) continue;
        occupied++;
        if (first_owner < 0) first_owner = piece->owner == side ? 0 : 1;
        last_owner = piece->owner == side ? 0 : 1;
    }
    for (uint8_t i = 0; i < pattern->path_count; i++) {
        const GCSemPathPredicate *predicate = &pattern->path[i];
        if (predicate->kind == 0 && occupied != 0) return 0;
        if (predicate->kind == 1 && (!predicate->has_count || occupied != predicate->count)) return 0;
        if (predicate->kind == 2 && ((!predicate->has_lo || occupied < predicate->lo) || (!predicate->has_hi || occupied > predicate->hi))) return 0;
        if (predicate->kind == 3 && predicate->owner_filter != 2 && first_owner != (int)predicate->owner_filter) return 0;
        if (predicate->kind == 4 && predicate->owner_filter != 2 && last_owner != (int)predicate->owner_filter) return 0;
    }
    return 1;
}

typedef struct {
    uint64_t *data;
    size_t count;
    size_t capacity;
} GCSemanticActionBuffer;

static void gc_semantic_action_buffer_init(GCSemanticActionBuffer *buffer) {
    buffer->data = NULL;
    buffer->count = 0;
    buffer->capacity = 0;
}

static void gc_semantic_action_buffer_free(GCSemanticActionBuffer *buffer) {
    free(buffer->data);
    buffer->data = NULL;
    buffer->count = 0;
    buffer->capacity = 0;
}

static int gc_semantic_action_buffer_append(GCSemanticActionBuffer *buffer, uint64_t action) {
    if (buffer->count == buffer->capacity) {
        size_t next = buffer->capacity ? buffer->capacity * 2 : 64;
        if (next < buffer->capacity || next > (size_t)-1 / sizeof(*buffer->data)) return 0;
        uint64_t *data = (uint64_t *)realloc(buffer->data, next * sizeof(*buffer->data));
        if (!data) return 0;
        buffer->data = data;
        buffer->capacity = next;
    }
    buffer->data[buffer->count++] = action;
    return 1;
}

static int gc_semantic_append_board_actions(GCSemanticActionBuffer *out,
                                            const GCSemanticRules *rules,
                                            const GCSemPattern *pattern,
                                            uint8_t side,
                                            const GCPiece *piece,
                                            uint16_t source,
                                            uint16_t target,
                                            uint16_t pattern_index,
                                            uint16_t geometry_index) {
    uint16_t promotions[GC_MAX_PROMO_TARGETS + 1];
    uint8_t promotion_count = 0;
    if (pattern->promotion_mode == 0) {
        promotions[promotion_count++] = 255;
    } else if (pattern->promotion_mode == 2) {
        if (!pattern->has_explicit_promotion) return 0;
        promotions[promotion_count++] = pattern->explicit_promotion_type;
    } else if (pattern->promotion_mode == 1) {
        /* Promotion is a one-way transition.  An already-promoted actor may
         * keep its current movement geometry, but never receives another
         * promotion variant merely because its base type has masks. */
        if (piece->promoted) {
            promotions[promotion_count++] = 255;
        } else {
            int allowed = 0;
            uint32_t pair = ((uint32_t)source << 16) | target;
            const GCSemPairList *pairs = &rules->promo_allowed[piece->base_type][side];
            for (uint16_t i = 0; i < pairs->count; i++) if (pairs->pairs[i] == pair) { allowed = 1; break; }
            if (!allowed || !rules->types[piece->base_type].is_promotable) {
            promotions[promotion_count++] = 255;
            } else {
                int forced = 0;
                const GCSemSquareList *forced_squares = &rules->promo_forced[piece->base_type][side];
                for (uint16_t i = 0; i < forced_squares->count; i++) if (forced_squares->squares[i] == target) { forced = 1; break; }
                if (!forced) promotions[promotion_count++] = 255;
                uint64_t alive = rules->alive_promo[piece->base_type][side][target];
                for (uint8_t i = 0; i < rules->types[piece->base_type].promo_target_count; i++)
                    if (alive & (1ull << i)) promotions[promotion_count++] = rules->types[piece->base_type].promo_targets[i];
            }
        }
    } else return 0;
    for (uint8_t i = 0; i < promotion_count; i++) {
        uint64_t action = ((uint64_t)target) | ((uint64_t)source << 8) |
            ((uint64_t)promotions[i] << 16) | ((uint64_t)piece->base_type << 24) |
            ((uint64_t)GC_ACTION_KIND_SEMANTIC_BOARD << 32) |
            ((uint64_t)pattern_index << 36) | ((uint64_t)geometry_index << 44) |
            ((uint64_t)piece->current_type << 56);
        if (!gc_semantic_action_buffer_append(out, action)) return 0;
    }
    return 1;
}

static int gc_semantic_generate_candidate_buffer(const GCSemanticRules *rules,
                                                 const GCSemanticPosition *pos,
                                                 GCSemanticActionBuffer *buffer) {
    uint8_t side = pos->side_to_move;
    for (uint16_t pi = 0; pi < rules->pattern_count; pi++) {
        const GCSemPattern *pattern = &rules->patterns[pi];
        for (uint8_t gi = 0; gi < pattern->geometry_count; gi++) {
            uint16_t gid = pattern->geometry_indices[gi];
            if (gid >= rules->geometry_count) {
                PyErr_SetString(PyExc_ValueError, "semantic pattern geometry out of range");
                return 0;
            }
            const GCSemGeometry *geo = &rules->geometries[gid];
            if (geo->kind == 2) {
                for (uint8_t ti = 0; ti < pattern->type_count; ti++) {
                    uint16_t tid = pattern->type_indices[ti];
                    if (tid >= rules->type_count || pos->hand_counts[side][tid] == 0) continue;
                    const GCSemSquareList *mask = &rules->drop_mask[tid][side];
                    for (uint16_t mi = 0; mi < mask->count; mi++) {
                        uint16_t target = mask->squares[mi];
                        if (target >= rules->board_size * rules->board_size || pos->board[target].occupied) continue;
                        uint64_t action = ((uint64_t)target) | (255ull << 8) |
                            (255ull << 16) | ((uint64_t)tid << 24) |
                            ((uint64_t)GC_ACTION_KIND_SEMANTIC_DROP << 32) |
                            ((uint64_t)pi << 36) | ((uint64_t)gid << 44) |
                            ((uint64_t)tid << 56);
                        if (!gc_semantic_action_buffer_append(buffer, action)) {
                            PyErr_NoMemory();
                            return 0;
                        }
                    }
                }
                continue;
            }
            const GCSemPathOwner *paths = &geo->paths[side];
            for (uint16_t source = 0; source < rules->board_size * rules->board_size; source++) {
                const GCPiece *piece = &pos->board[source];
                if (!piece->occupied || piece->owner != side) continue;
                int actor_match = 0;
                for (uint8_t ti = 0; ti < pattern->type_count; ti++) if (pattern->type_indices[ti] == piece->current_type) { actor_match = 1; break; }
                if (!actor_match || (geo->has_atom_source && geo->atom_source_type != piece->current_type)) continue;
                for (uint16_t ei = 0; ei < paths->count; ei++) {
                    if (paths->entries[ei].source != source) continue;
                    const GCSemPathEntry *entry = &paths->entries[ei];
                    uint16_t start = geo->min_steps > 0 ? (uint16_t)(geo->min_steps - 1) : 0;
                    for (uint16_t si = start; si < entry->count; si++) {
                        uint16_t target = entry->squares[si];
                        if (target >= rules->board_size * rules->board_size || !gc_semantic_target_holds(pattern->target, &pos->board[target], side)) continue;
                        if (!gc_semantic_path_holds(pattern, entry, si, pos, side)) continue;
                        if (!gc_semantic_append_board_actions(buffer, rules, pattern, side, piece, source, target, pi, gid)) {
                            PyErr_SetString(PyExc_ValueError, "semantic promotion action construction failed");
                            return 0;
                        }
                    }
                }
            }
        }
    }
    return 1;
}

static PyObject *gc_semantic_candidate_actions(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule, *pos_capsule;
    if (!PyArg_ParseTuple(args, "OO", &rules_capsule, &pos_capsule)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(rules_capsule, GC_SEM_RULES_CAPSULE);
    GCSemanticPosition *pos = (GCSemanticPosition *)PyCapsule_GetPointer(pos_capsule, GC_SEM_POSITION_CAPSULE);
    if (!rules || !pos) return NULL;
    if (!gc_semantic_require_matching_rules(rules, pos)) return NULL;
    GCSemanticActionBuffer buffer;
    gc_semantic_action_buffer_init(&buffer);
    if (!gc_semantic_generate_candidate_buffer(rules, pos, &buffer)) {
        gc_semantic_action_buffer_free(&buffer);
        return NULL;
    }
    if (buffer.count > (size_t)PY_SSIZE_T_MAX) {
        gc_semantic_action_buffer_free(&buffer);
        PyErr_SetString(PyExc_OverflowError, "semantic action list is too large");
        return NULL;
    }
    PyObject *out = PyTuple_New((Py_ssize_t)buffer.count);
    if (!out) {
        gc_semantic_action_buffer_free(&buffer);
        return NULL;
    }
    for (size_t i = 0; i < buffer.count; i++) {
        PyObject *value = PyLong_FromUnsignedLongLong(buffer.data[i]);
        if (!value) {
            Py_DECREF(out);
            gc_semantic_action_buffer_free(&buffer);
            return NULL;
        }
        PyTuple_SET_ITEM(out, (Py_ssize_t)i, value);
    }
    gc_semantic_action_buffer_free(&buffer);
    return out;
}

static PyObject *gc_semantic_history_occurrences(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *pos_capsule;
    unsigned long long lo, hi;
    if (!PyArg_ParseTuple(args, "OKK", &pos_capsule, &lo, &hi)) return NULL;
    GCSemanticPosition *pos = (GCSemanticPosition *)PyCapsule_GetPointer(pos_capsule, GC_SEM_POSITION_CAPSULE);
    if (!pos) return NULL;
    unsigned long count = 0;
    for (uint16_t i = 0; i < pos->history_len; i++)
        if (pos->history_lo[i] == (uint64_t)lo && pos->history_hi[i] == (uint64_t)hi) count++;
    return PyLong_FromUnsignedLong(count);
}

static PyObject *gc_semantic_make_checked(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule, *pos_capsule;
    unsigned long long action;
    if (!PyArg_ParseTuple(args, "OOK", &rules_capsule, &pos_capsule, &action)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(rules_capsule, GC_SEM_RULES_CAPSULE);
    GCSemanticPosition *parent = (GCSemanticPosition *)PyCapsule_GetPointer(pos_capsule, GC_SEM_POSITION_CAPSULE);
    if (!rules || !parent) return NULL;
    if (!gc_semantic_require_matching_rules(rules, parent)) return NULL;
    GCSemanticPosition *child = (GCSemanticPosition *)malloc(sizeof(*child));
    if (!child) { PyErr_NoMemory(); return NULL; }
    if (!gc_semantic_runtime_make_checked(child, rules, parent, (uint64_t)action)) {
        free(child);
        PyErr_SetString(PyExc_ValueError, "semantic action is not valid for the current position");
        return NULL;
    }
    return PyCapsule_New(child, GC_SEM_POSITION_CAPSULE, gc_semantic_position_capsule_free);
}

static PyObject *gc_semantic_action_delivers_check_debug(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule, *pos_capsule;
    unsigned long long action;
    if (!PyArg_ParseTuple(args, "OOK", &rules_capsule, &pos_capsule, &action)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(rules_capsule, GC_SEM_RULES_CAPSULE);
    GCSemanticPosition *parent = (GCSemanticPosition *)PyCapsule_GetPointer(pos_capsule, GC_SEM_POSITION_CAPSULE);
    if (!rules || !parent) return NULL;
    if (!gc_semantic_require_matching_rules(rules, parent)) return NULL;
    return PyBool_FromLong(gc_semantic_runtime_action_delivers_check_debug(
        rules, parent, (uint64_t)action));
}

static PyObject *gc_semantic_is_square_attacked(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule, *pos_capsule;
    Py_ssize_t square;
    int by_owner;
    if (!PyArg_ParseTuple(args, "OOnI", &rules_capsule, &pos_capsule, &square, &by_owner)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(rules_capsule, GC_SEM_RULES_CAPSULE);
    GCSemanticPosition *position = (GCSemanticPosition *)PyCapsule_GetPointer(pos_capsule, GC_SEM_POSITION_CAPSULE);
    if (!rules || !position) return NULL;
    if (!gc_semantic_require_matching_rules(rules, position)) return NULL;
    if (square < 0 || square >= (Py_ssize_t)(rules->board_size * rules->board_size)) {
        PyErr_SetString(PyExc_ValueError, "semantic square is outside board");
        return NULL;
    }
    if (by_owner > 1) {
        PyErr_SetString(PyExc_ValueError, "semantic attacker owner must be 0 or 1");
        return NULL;
    }
    return PyBool_FromLong(gc_semantic_runtime_is_square_attacked(
        rules, position, (uint16_t)square, (uint8_t)by_owner));
}

static PyObject *gc_semantic_in_check(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule, *pos_capsule;
    int side;
    if (!PyArg_ParseTuple(args, "OOi", &rules_capsule, &pos_capsule, &side)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(rules_capsule, GC_SEM_RULES_CAPSULE);
    GCSemanticPosition *position = (GCSemanticPosition *)PyCapsule_GetPointer(pos_capsule, GC_SEM_POSITION_CAPSULE);
    if (!rules || !position) return NULL;
    if (!gc_semantic_require_matching_rules(rules, position)) return NULL;
    if (side < 0 || side > 1) {
        PyErr_SetString(PyExc_ValueError, "semantic side must be 0 or 1");
        return NULL;
    }
    return PyBool_FromLong(gc_semantic_runtime_in_check(
        rules, position, (uint8_t)side));
}

static PyObject *gc_semantic_make_unmake_roundtrip(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule, *pos_capsule;
    unsigned long long action;
    if (!PyArg_ParseTuple(args, "OOK", &rules_capsule, &pos_capsule, &action)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(rules_capsule, GC_SEM_RULES_CAPSULE);
    GCSemanticPosition *pos = (GCSemanticPosition *)PyCapsule_GetPointer(pos_capsule, GC_SEM_POSITION_CAPSULE);
    if (!rules || !pos) return NULL;
    if (!gc_semantic_require_matching_rules(rules, pos)) return NULL;
    GCSemanticPosition work = *pos, before = *pos;
    GCSemanticUndo undo;
    int make_ok = gc_semantic_runtime_make_trusted(&work, rules, (uint64_t)action, &undo);
    int restored = 0;
    if (make_ok) {
        gc_semantic_runtime_unmake(&work, &undo);
        restored = memcmp(&work, &before, sizeof(work)) == 0;
    }
    return Py_BuildValue("{s:i,s:i,s:i}", "make_ok", make_ok, "unmake_ok", make_ok && restored, "restored", restored);
}

static PyObject *gc_semantic_candidate_tuple_native(const GCSemanticRules *rules, const GCSemanticPosition *position) {
    PyObject *rules_capsule = PyCapsule_New((void *)rules, GC_SEM_RULES_CAPSULE, NULL);
    PyObject *position_capsule = PyCapsule_New((void *)position, GC_SEM_POSITION_CAPSULE, NULL);
    if (!rules_capsule || !position_capsule) { Py_XDECREF(rules_capsule); Py_XDECREF(position_capsule); return NULL; }
    PyObject *call_args = PyTuple_Pack(2, rules_capsule, position_capsule);
    Py_DECREF(rules_capsule); Py_DECREF(position_capsule);
    if (!call_args) return NULL;
    PyObject *actions = gc_semantic_candidate_actions(NULL, call_args);
    Py_DECREF(call_args);
    return actions;
}

static PyObject *gc_semantic_guarded_actions(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule, *position_capsule;
    if (!PyArg_ParseTuple(args, "OO", &rules_capsule, &position_capsule)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(rules_capsule, GC_SEM_RULES_CAPSULE);
    GCSemanticPosition *position = (GCSemanticPosition *)PyCapsule_GetPointer(position_capsule, GC_SEM_POSITION_CAPSULE);
    if (!rules || !position) return NULL;
    if (!gc_semantic_require_matching_rules(rules, position)) return NULL;
    PyObject *candidates = gc_semantic_candidate_tuple_native(rules, position);
    if (!candidates) return NULL;
    PyObject *guarded = PyList_New(0);
    if (!guarded) { Py_DECREF(candidates); return NULL; }
    Py_ssize_t count = PyTuple_Size(candidates);
    for (Py_ssize_t i=0; i<count; i++) {
        unsigned long long raw = PyLong_AsUnsignedLongLong(PyTuple_GetItem(candidates, i));
        if (PyErr_Occurred()) { Py_DECREF(candidates); Py_DECREF(guarded); return NULL; }
        GCSemanticPosition child;
        if (!gc_semantic_runtime_make_checked(&child, rules, position, (uint64_t)raw)) continue;
        PyObject *value = PyLong_FromUnsignedLongLong(raw);
        if (!value || PyList_Append(guarded, value) != 0) { Py_XDECREF(value); Py_DECREF(candidates); Py_DECREF(guarded); return NULL; }
        Py_DECREF(value);
    }
    Py_DECREF(candidates);
    PyObject *result = PySequence_Tuple(guarded);
    Py_DECREF(guarded);
    return result;
}

static PyObject *gc_semantic_guarded_actions_audit(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule, *position_capsule;
    if (!PyArg_ParseTuple(args, "OO", &rules_capsule, &position_capsule)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(rules_capsule, GC_SEM_RULES_CAPSULE);
    GCSemanticPosition *position = (GCSemanticPosition *)PyCapsule_GetPointer(position_capsule, GC_SEM_POSITION_CAPSULE);
    if (!rules || !position) return NULL;
    if (!gc_semantic_require_matching_rules(rules, position)) return NULL;
    GCSemanticActionBuffer candidates;
    gc_semantic_action_buffer_init(&candidates);
    if (!gc_semantic_generate_candidate_buffer(rules, position, &candidates)) {
        gc_semantic_action_buffer_free(&candidates);
        return NULL;
    }
    GCSemanticRuntimeAudit audit = {0};
    audit.candidate_count = (unsigned long long)candidates.count;
    gc_semantic_runtime_audit_start(&audit);
    PyObject *actions = gc_semantic_guarded_actions(self, args);
    gc_semantic_runtime_audit_stop();
    gc_semantic_action_buffer_free(&candidates);
    if (!actions) return NULL;
    PyObject *out = PyDict_New();
    if (!out) { Py_DECREF(actions); return NULL; }
    PyObject *value = PyLong_FromUnsignedLongLong(audit.candidate_count);
    if (!value || PyDict_SetItemString(out, "candidate_count", value) != 0) goto audit_error;
    Py_DECREF(value); value = PyLong_FromUnsignedLongLong(audit.s3_trial_count);
    if (!value || PyDict_SetItemString(out, "s3_trial_count", value) != 0) goto audit_error;
    Py_DECREF(value); value = PyLong_FromUnsignedLongLong(audit.s4_count);
    if (!value || PyDict_SetItemString(out, "s4_count", value) != 0) goto audit_error;
    Py_DECREF(value); value = PyLong_FromUnsignedLongLong(audit.nested_reply_count);
    if (!value || PyDict_SetItemString(out, "nested_reply_count", value) != 0) goto audit_error;
    Py_DECREF(value); value = PyLong_FromUnsignedLongLong(audit.child_canonical_key_computations);
    if (!value || PyDict_SetItemString(out, "child_canonical_key_computations", value) != 0) goto audit_error;
    Py_DECREF(value); value = PyLong_FromUnsignedLongLong(audit.history_appends);
    if (!value || PyDict_SetItemString(out, "history_appends", value) != 0) goto audit_error;
    Py_DECREF(value); value = PyLong_FromUnsignedLongLong(audit.attack_check_calls);
    if (!value || PyDict_SetItemString(out, "attack_check_calls", value) != 0) goto audit_error;
    Py_DECREF(value);
    if (PyDict_SetItemString(out, "actions", actions) != 0) goto audit_error_no_value;
    Py_DECREF(actions);
    return out;
audit_error:
    Py_XDECREF(value);
audit_error_no_value:
    Py_DECREF(actions);
    Py_DECREF(out);
    return NULL;
}

static PyObject *gc_semantic_transient_legal_actions_impl(
    PyObject *self, PyObject *args, GCSemanticRuntimeAudit *audit_out) {
    (void)self;
    PyObject *rules_capsule, *position_capsule;
    if (!PyArg_ParseTuple(args, "OO", &rules_capsule, &position_capsule)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(rules_capsule, GC_SEM_RULES_CAPSULE);
    GCSemanticPosition *position = (GCSemanticPosition *)PyCapsule_GetPointer(position_capsule, GC_SEM_POSITION_CAPSULE);
    if (!rules || !position) return NULL;
    if (!gc_semantic_require_matching_rules(rules, position)) return NULL;
    GCSemanticActionBuffer candidates;
    gc_semantic_action_buffer_init(&candidates);
    if (!gc_semantic_generate_candidate_buffer(rules, position, &candidates)) {
        gc_semantic_action_buffer_free(&candidates);
        return NULL;
    }
    GCSemanticRuntimeAudit local_audit = {0};
    if (audit_out) {
        local_audit.candidate_count = (unsigned long long)candidates.count;
        gc_semantic_runtime_audit_start(&local_audit);
    }
    gc_semantic_runtime_history_mode_start();
    PyObject *out = PyList_New(0);
    if (out) {
        for (size_t i = 0; i < candidates.count; i++) {
            GCSemanticPosition child;
            if (!gc_semantic_runtime_make_checked(&child, rules, position, candidates.data[i])) continue;
            PyObject *value = PyLong_FromUnsignedLongLong(candidates.data[i]);
            if (!value) { Py_DECREF(out); out = NULL; break; }
            if (PyList_Append(out, value) != 0) { Py_DECREF(value); Py_DECREF(out); out = NULL; break; }
            Py_DECREF(value);
        }
    }
    gc_semantic_runtime_history_mode_stop();
    if (audit_out) gc_semantic_runtime_audit_stop();
    gc_semantic_action_buffer_free(&candidates);
    if (!out) return NULL;
    PyObject *tuple = PySequence_Tuple(out);
    Py_DECREF(out);
    if (!tuple) return NULL;
    if (audit_out) *audit_out = local_audit;
    return tuple;
}

static PyObject *gc_semantic_transient_legal_actions(PyObject *self, PyObject *args) {
    return gc_semantic_transient_legal_actions_impl(self, args, NULL);
}

static PyObject *gc_semantic_transient_legal_actions_audit(PyObject *self, PyObject *args) {
    GCSemanticRuntimeAudit audit = {0};
    PyObject *actions = gc_semantic_transient_legal_actions_impl(self, args, &audit);
    if (!actions) return NULL;
    PyObject *out = PyDict_New();
    if (!out) { Py_DECREF(actions); return NULL; }
    const char *names[] = {
        "candidate_count", "s3_trial_count", "s4_count", "nested_reply_count",
        "child_canonical_key_computations", "history_appends", "attack_check_calls"
    };
    unsigned long long values[] = {
        audit.candidate_count, audit.s3_trial_count, audit.s4_count, audit.nested_reply_count,
        audit.child_canonical_key_computations, audit.history_appends, audit.attack_check_calls
    };
    for (int i = 0; i < 7; i++) {
        PyObject *value = PyLong_FromUnsignedLongLong(values[i]);
        if (!value || PyDict_SetItemString(out, names[i], value) != 0) {
            Py_XDECREF(value); Py_DECREF(actions); Py_DECREF(out); return NULL;
        }
        Py_DECREF(value);
    }
    if (PyDict_SetItemString(out, "actions", actions) != 0) {
        Py_DECREF(actions); Py_DECREF(out); return NULL;
    }
    Py_DECREF(actions);
    return out;
}

static int gc_semantic_has_guarded_action(const GCSemanticRules *rules,
                                          const GCSemanticPosition *position,
                                          int *ok) {
    GCSemanticActionBuffer candidates;
    gc_semantic_action_buffer_init(&candidates);
    if (!gc_semantic_generate_candidate_buffer(rules, position, &candidates)) {
        gc_semantic_action_buffer_free(&candidates);
        *ok = 0;
        return 0;
    }
    for (size_t i = 0; i < candidates.count; i++) {
        uint64_t raw = candidates.data[i];
        GCSemanticPosition probe = *position;
        /* Terminal authority checks legal-action availability independently of
         * the max-ply/repetition-history cutoff, matching SemanticEngine. */
        probe.ply = 0;
        probe.history_len = 0;
        probe.history_exact = 1;
        GCSemanticPosition child;
        if (gc_semantic_runtime_make_checked(&child, rules, &probe, (uint64_t)raw)) {
            gc_semantic_action_buffer_free(&candidates);
            return 1;
        }
    }
    gc_semantic_action_buffer_free(&candidates);
    return 0;
}

static int gc_semantic_repetition_count(const GCSemanticRules *rules,
                                        const GCSemanticPosition *position,
                                        unsigned long *count_out) {
    if (position->history_len > 0 && !position->history_exact) return -1;
    char digest[65];
    if (!gc_semantic_position_key_digest(rules, position, digest)) return -1;
    uint64_t words[4] = {0, 0, 0, 0};
    for (int w = 0; w < 4; w++) for (int i = 0; i < 16; i++) {
        char c = digest[w * 16 + i];
        uint8_t n = (uint8_t)(c >= '0' && c <= '9' ? c - '0' : c - 'a' + 10);
        words[w] = (words[w] << 4) | n;
    }
    unsigned long count = 0;
    for (uint16_t i = 0; i < position->history_len; i++)
        if (memcmp(position->history_digest[i], words, sizeof(words)) == 0) count++;
    *count_out = count;
    return 1;
}

static int gc_semantic_require_exact_history(const GCSemanticPosition *position) {
    if (position->history_len > 0 && !position->history_exact) {
        PyErr_SetString(PyExc_ValueError,
                        "semantic runtime requires exact full history");
        return 0;
    }
    return 1;
}

static const char *gc_semantic_declaration_outcome_name(uint8_t outcome) {
    static const char *names[] = {"WIN", "LOSS", "RESTART", "NO_CONTEST"};
    return outcome < 4 ? names[outcome] : "LOSS";
}

static PyObject *gc_semantic_declaration_result(
    const GCSemanticDeclarationAssessment *assessment,
    const char *declaration_id, uint8_t actor) {
    PyObject *out = Py_BuildValue(
        "{s:s,s:i,s:s}", "declaration_id", declaration_id,
        "actor", (int)actor,
        "outcome", gc_semantic_declaration_outcome_name(assessment->outcome));
    if (!out) return NULL;
    PyObject *score = assessment->has_weighted_score
        ? PyLong_FromLongLong(assessment->weighted_score) : Py_NewRef(Py_None);
    if (!score || PyDict_SetItemString(out, "weighted_score", score) != 0) {
        Py_XDECREF(score); Py_DECREF(out); return NULL;
    }
    Py_DECREF(score);
    return out;
}

static PyObject *gc_semantic_assess_declaration(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule, *position_capsule;
    const char *declaration_id;
    if (!PyArg_ParseTuple(args, "OOs", &rules_capsule, &position_capsule,
                          &declaration_id)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(
        rules_capsule, GC_SEM_RULES_CAPSULE);
    GCSemanticPosition *position = (GCSemanticPosition *)PyCapsule_GetPointer(
        position_capsule, GC_SEM_POSITION_CAPSULE);
    if (!rules || !position || !gc_semantic_require_matching_rules(rules, position))
        return NULL;
    GCSemanticDeclarationAssessment assessment;
    int status = gc_semantic_runtime_assess_declaration(
        rules, position, declaration_id, &assessment);
    if (status == -1) {
        PyErr_Format(PyExc_ValueError, "unknown declaration ID %R",
                     PyUnicode_FromString(declaration_id));
        return NULL;
    }
    if (status == -2) {
        PyErr_Format(PyExc_ValueError,
                     "declaration %s belongs to the other player",
                     declaration_id);
        return NULL;
    }
    if (status <= 0) {
        PyErr_SetString(PyExc_ValueError, "declaration assessment failed closed");
        return NULL;
    }
    return gc_semantic_declaration_result(&assessment, declaration_id,
                                          position->side_to_move);
}

static PyObject *gc_semantic_available_declarations(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule, *position_capsule;
    if (!PyArg_ParseTuple(args, "OO", &rules_capsule, &position_capsule)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(
        rules_capsule, GC_SEM_RULES_CAPSULE);
    GCSemanticPosition *position = (GCSemanticPosition *)PyCapsule_GetPointer(
        position_capsule, GC_SEM_POSITION_CAPSULE);
    if (!rules || !position || !gc_semantic_require_matching_rules(rules, position))
        return NULL;
    PyObject *out = PyTuple_New(0);
    if (!out) return NULL;
    for (uint8_t i = 0; i < rules->declaration_count; i++) {
        GCSemDeclaration *declaration = &rules->declarations[i];
        if (declaration->owner != position->side_to_move) continue;
        GCSemanticDeclarationAssessment assessment;
        int status = gc_semantic_runtime_assess_declaration(
            rules, position, declaration->declaration_id, &assessment);
        if (status <= 0) { Py_DECREF(out); PyErr_SetString(PyExc_ValueError, "declaration assessment failed closed"); return NULL; }
        if (assessment.outcome == 1) continue;
        PyObject *item = gc_semantic_declaration_result(
            &assessment, declaration->declaration_id, position->side_to_move);
        if (!item) { Py_DECREF(out); return NULL; }
        PyObject *next = PySequence_Concat(out, PyTuple_Pack(1, item));
        Py_DECREF(item);
        Py_DECREF(out);
        out = next;
        if (!out) return NULL;
    }
    return out;
}

static int gc_semantic_continuous_check_winner(const GCSemanticRules *rules,
                                               const GCSemanticPosition *position,
                                               int *winner_out) {
    if (rules->repetition_limit < 1 || !position->history_events_exact ||
        position->history_len == 0) return 0;
    char digest[65];
    if (!gc_semantic_position_key_digest(rules, position, digest)) return -1;
    uint64_t words[4] = {0, 0, 0, 0};
    for (int w = 0; w < 4; w++) for (int i = 0; i < 16; i++) {
        char c = digest[w * 16 + i];
        uint8_t n = (uint8_t)(c >= '0' && c <= '9' ? c - '0' : c - 'a' + 10);
        words[w] = (words[w] << 4) | n;
    }
    uint16_t occurrences[GC_SEM_MAX_PLY + 1];
    uint16_t count = 0;
    for (uint16_t i = 0; i < position->history_len; i++) {
        if (memcmp(position->history_digest[i], words, sizeof(words)) == 0)
            occurrences[count++] = i;
    }
    if (count < rules->repetition_limit) return 0;
    uint16_t start = occurrences[count - rules->repetition_limit];
    uint16_t end = occurrences[count - 1];
    if (start >= end) return 0;
    int seen[2] = {0, 0};
    int all_checks[2] = {1, 1};
    for (uint16_t i = (uint16_t)(start + 1); i <= end; i++) {
        uint8_t actor = position->history_actor[i];
        if (actor == 255) continue;
        if (actor > 1) return 0;
        seen[actor] = 1;
        if (!position->history_gave_check[i]) all_checks[actor] = 0;
    }
    int checking_side = -1;
    for (int actor = 0; actor < 2; actor++) {
        if (seen[actor] && all_checks[actor]) {
            if (checking_side >= 0) return 0;
            checking_side = actor;
        }
    }
    if (checking_side < 0 || !seen[0] || !seen[1]) return 0;
    if (winner_out) *winner_out = 1 - checking_side;
    return 1;
}

/* Return 0 for no automatic result, 1 for pending continuation, 2 for the
 * configured terminal outcome, and -1 when the authoritative history is
 * incomplete or the record cannot be interpreted safely. */
static int gc_semantic_automatic_status(const GCSemanticRules *rules,
                                        const GCSemanticPosition *position) {
    for (uint8_t a = 0; a < rules->automatic_adjudication_count; a++) {
        const GCSemAutomaticAdjudication *record =
            &rules->automatic_adjudications[a];
        if (position->ply < record->trigger_ply) continue;
        if (!position->history_events_exact ||
            position->history_len != position->ply + 1 ||
            position->history_len == 0 || position->history_actor[0] != 255)
            return -1;
        for (uint16_t i = 1; i < position->history_len; i++)
            if (position->history_actor[i] > 1) return -1;
        if (record->trigger_ply >= position->history_len) return -1;
        if (record->continuation_policy != 0) return -1;
        uint8_t checker = position->history_actor[record->trigger_ply];
        if (!position->history_gave_check[record->trigger_ply]) return 2;
        for (uint16_t i = record->trigger_ply + 1;
             i < position->history_len; i++) {
            if (position->history_actor[i] == checker &&
                !position->history_gave_check[i]) return 2;
        }
        return 1;
    }
    return 0;
}

static int gc_semantic_terminal_status(const GCSemanticRules *rules,
                                       const GCSemanticPosition *position,
                                       int *winner_out) {
    int ok = 1;
    int has_action = gc_semantic_has_guarded_action(rules, position, &ok);
    if (!ok) return -1;
    if (!has_action) {
        if (gc_semantic_runtime_in_check(rules, position, position->side_to_move)) {
            if (winner_out) *winner_out = 1 - position->side_to_move;
            return 1; /* checkmate */
        }
        /* No-legal-action states have checkmate/stalemate precedence. */
        return 2; /* stalemate */
    }
    unsigned long repetitions = 0;
    if (gc_semantic_repetition_count(rules, position, &repetitions) < 0) return -1;
    if (rules->repetition_policy == 1) {
        int perpetual_winner = -1;
        int perpetual = gc_semantic_continuous_check_winner(rules, position, &perpetual_winner);
        if (perpetual < 0) return -1;
        if (perpetual > 0) {
            if (winner_out) *winner_out = perpetual_winner;
            return 5;
        }
    }
    if (repetitions >= rules->repetition_limit) return 3; /* repetition */
    int automatic = gc_semantic_automatic_status(rules, position);
    if (automatic < 0) return -1;
    if (automatic == 2 && rules->automatic_adjudication_count > 0 &&
        rules->automatic_adjudications[0].outcome == 3) return 6;
    if (position->ply >= rules->max_ply) return 4; /* max ply */
    return 0; /* ongoing */
}

static PyObject *gc_semantic_terminal(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule, *position_capsule;
    if (!PyArg_ParseTuple(args, "OO", &rules_capsule, &position_capsule)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(rules_capsule, GC_SEM_RULES_CAPSULE);
    GCSemanticPosition *position = (GCSemanticPosition *)PyCapsule_GetPointer(position_capsule, GC_SEM_POSITION_CAPSULE);
    if (!rules || !position) return NULL;
    if (!gc_semantic_require_matching_rules(rules, position)) return NULL;
    if (!gc_semantic_require_exact_history(position)) return NULL;
    int winner = -1;
    int status = gc_semantic_terminal_status(rules, position, &winner);
    if (status < 0) {
        if (!PyErr_Occurred()) PyErr_SetString(PyExc_ValueError, "semantic terminal requires exact full history");
        return NULL;
    }
    const char *names[] = {"ongoing", "checkmate", "stalemate", "repetition", "max_ply", "perpetual_check", "no_contest"};
    PyObject *out = Py_BuildValue("{s:s}", "status", names[status]);
    if (!out) return NULL;
    if (winner >= 0) {
        PyObject *value = PyLong_FromLong(winner);
        if (!value || PyDict_SetItemString(out, "winner", value) != 0) { Py_XDECREF(value); Py_DECREF(out); return NULL; }
        Py_DECREF(value);
    } else if (PyDict_SetItemString(out, "winner", Py_None) != 0) {
        Py_DECREF(out); return NULL;
    }
    return out;
}

static unsigned long long gc_semantic_perft_rec(const GCSemanticRules *rules, const GCSemanticPosition *position, unsigned int depth, int *ok) {
    if (!*ok) return 0;
    if (depth == 0) return 1;
    int winner = -1;
    int terminal = gc_semantic_terminal_status(rules, position, &winner);
    if (terminal < 0) { *ok = 0; return 0; }
    if (terminal == 3 || terminal == 4) return 1;
    if (terminal == 1 || terminal == 2) return 0;
    GCSemanticActionBuffer actions;
    gc_semantic_action_buffer_init(&actions);
    if (!gc_semantic_generate_candidate_buffer(rules, position, &actions)) {
        gc_semantic_action_buffer_free(&actions);
        *ok = 0;
        return 0;
    }
    unsigned long long total = 0;
    for (size_t i = 0; i < actions.count; i++) {
        uint64_t raw = actions.data[i];
        GCSemanticPosition work = *position;
        GCSemanticUndo undo;
        if (!gc_semantic_runtime_make_trusted(&work, rules, (uint64_t)raw, &undo)) continue;
        unsigned long long branch = gc_semantic_perft_rec(rules, &work, depth - 1, ok);
        gc_semantic_runtime_unmake(&work, &undo);
        if (ULLONG_MAX - total < branch) { *ok = 0; break; }
        total += branch;
    }
    gc_semantic_action_buffer_free(&actions);
    return total;
}

typedef struct {
    int score;
    uint64_t best_action;
    int has_best;
    unsigned int pv_len;
    uint64_t pv[GC_MAX_PLY + 1];
    unsigned long long nodes;
} GCSemanticProbeSearch;

typedef struct {
    int board[GC_MAX_TYPES];
    int hand[GC_MAX_TYPES];
    int supplied;
} GCSemanticProbeProfile;

#define GC_SEMANTIC_PROBE_INF 1000000000

static int gc_semantic_probe_material(const GCSemanticRules *rules, const GCSemanticPosition *position, const GCSemanticProbeProfile *profile) {
    int score = 0;
    for (uint16_t sq = 0; sq < rules->board_size * rules->board_size; sq++) {
        const GCPiece *piece = &position->board[sq];
        if (!piece->occupied) continue;
        int value = profile && profile->supplied ? profile->board[piece->current_type] : (int)piece->current_type + 1;
        score += piece->owner == position->side_to_move ? value : -value;
    }
    for (uint8_t owner = 0; owner < 2; owner++) {
        for (uint16_t type = 0; type < rules->type_count; type++) {
            int value = profile && profile->supplied ? profile->hand[type] : (int)type + 1;
            int hand_score = (int)position->hand_counts[owner][type] * value;
            score += owner == position->side_to_move ? hand_score : -hand_score;
        }
    }
    return score;
}

static GCSemanticProbeSearch gc_semantic_probe_negamax(const GCSemanticRules *rules,
                                                        const GCSemanticPosition *position,
                                                        unsigned int depth,
                                                        int alpha,
                                                        int beta,
                                                        const GCSemanticProbeProfile *profile,
                                                        int *ok) {
    GCSemanticProbeSearch result;
    memset(&result, 0, sizeof(result));
    if (!*ok) return result;
    result.score = gc_semantic_probe_material(rules, position, profile);
    result.nodes = 1;
    int winner = -1;
    int terminal = gc_semantic_terminal_status(rules, position, &winner);
    if (terminal < 0) {
        *ok = 0;
        return result;
    }
    if (terminal == 1) { result.score = -1000000; return result; }
    if (terminal != 0) { result.score = 0; return result; }
    if (depth == 0) return result;
    GCSemanticActionBuffer actions;
    gc_semantic_action_buffer_init(&actions);
    if (!gc_semantic_generate_candidate_buffer(rules, position, &actions)) {
        gc_semantic_action_buffer_free(&actions);
        return result;
    }
    int found = 0;
    int best_score = -GC_SEMANTIC_PROBE_INF;
    for (size_t i = 0; i < actions.count; i++) {
        uint64_t raw = actions.data[i];
        if (raw == 0) continue;
        GCSemanticPosition work = *position;
        GCSemanticUndo undo;
        if (!gc_semantic_runtime_make_trusted(&work, rules, (uint64_t)raw, &undo)) continue;
        GCSemanticProbeSearch branch = gc_semantic_probe_negamax(rules, &work, depth - 1, -beta, -alpha, profile, ok);
        if (!*ok) {
            gc_semantic_runtime_unmake(&work, &undo);
            gc_semantic_action_buffer_free(&actions);
            return result;
        }
        gc_semantic_runtime_unmake(&work, &undo);
        result.nodes += branch.nodes;
        int score = -branch.score;
        if (!found || score > best_score || (score == best_score && raw < result.best_action)) {
            found = 1;
            best_score = score;
            result.score = score;
            result.best_action = (uint64_t)raw;
            result.has_best = 1;
            result.pv_len = branch.pv_len + 1;
            result.pv[0] = (uint64_t)raw;
            for (unsigned int j = 0; j < branch.pv_len && j + 1 < GC_MAX_PLY + 1; j++) result.pv[j + 1] = branch.pv[j];
        }
        if (score > alpha) alpha = score;
        if (alpha >= beta) break;
    }
    gc_semantic_action_buffer_free(&actions);
    return result;
}

static PyObject *gc_semantic_probe_search(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule, *position_capsule, *board_values = NULL, *hand_values = NULL;
    unsigned int depth;
    if (!PyArg_ParseTuple(args, "OOI|OO", &rules_capsule, &position_capsule, &depth, &board_values, &hand_values)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(rules_capsule, GC_SEM_RULES_CAPSULE);
    GCSemanticPosition *position = (GCSemanticPosition *)PyCapsule_GetPointer(position_capsule, GC_SEM_POSITION_CAPSULE);
    if (!rules || !position || depth > GC_MAX_PLY) return NULL;
    if (!gc_semantic_require_matching_rules(rules, position)) return NULL;
    if (!gc_semantic_require_exact_history(position)) return NULL;
    GCSemanticProbeProfile profile;
    memset(&profile, 0, sizeof(profile));
    if ((board_values == NULL) != (hand_values == NULL)) {
        PyErr_SetString(PyExc_ValueError, "semantic probe board/hand profile must be supplied together");
        return NULL;
    }
    if (board_values != NULL) {
        if ((!PyList_Check(board_values) && !PyTuple_Check(board_values)) ||
            (!PyList_Check(hand_values) && !PyTuple_Check(hand_values)) ||
            PySequence_Size(board_values) != rules->type_count ||
            PySequence_Size(hand_values) != rules->type_count) {
            PyErr_SetString(PyExc_ValueError, "semantic probe profile length must match type_count");
            return NULL;
        }
        for (uint16_t type = 0; type < rules->type_count; type++) {
            PyObject *bv = PySequence_GetItem(board_values, type);
            PyObject *hv = PySequence_GetItem(hand_values, type);
            long b = PyLong_AsLong(bv), h = PyLong_AsLong(hv);
            Py_DECREF(bv); Py_DECREF(hv);
            if (PyErr_Occurred() || b < -1000000 || b > 1000000 || h < -1000000 || h > 1000000) {
                PyErr_SetString(PyExc_ValueError, "semantic probe profile values must be bounded integers");
                return NULL;
            }
            profile.board[type] = (int)b;
            profile.hand[type] = (int)h;
        }
        profile.supplied = 1;
    }
    int ok = 1;
    GCSemanticProbeSearch result = gc_semantic_probe_negamax(rules, position, depth, -GC_SEMANTIC_PROBE_INF, GC_SEMANTIC_PROBE_INF, &profile, &ok);
    if (!ok) {
        if (!PyErr_Occurred()) {
            PyErr_SetString(PyExc_RuntimeError,
                            "semantic fixed-depth search failed during terminal evaluation");
        }
        return NULL;
    }
    if (PyErr_Occurred()) return NULL;
    PyObject *pv = PyTuple_New((Py_ssize_t)result.pv_len);
    if (!pv) return NULL;
    for (unsigned int i = 0; i < result.pv_len; i++) {
        PyObject *value = PyLong_FromUnsignedLongLong(result.pv[i]);
        if (!value) { Py_DECREF(pv); return NULL; }
        PyTuple_SET_ITEM(pv, (Py_ssize_t)i, value);
    }
    PyObject *out = Py_BuildValue("{s:i,s:K,s:i,s:O}",
                                  "score", result.score,
                                  "nodes", result.nodes,
                                  "has_best", result.has_best,
                                  "principal_variation", pv);
    Py_DECREF(pv);
    if (!out) return NULL;
    if (result.has_best) {
        PyObject *best = PyLong_FromUnsignedLongLong(result.best_action);
        if (!best || PyDict_SetItemString(out, "best_action", best) != 0) { Py_XDECREF(best); Py_DECREF(out); return NULL; }
        Py_DECREF(best);
    } else if (PyDict_SetItemString(out, "best_action", Py_None) != 0) { Py_DECREF(out); return NULL; }
    return out;
}

typedef struct {
    const GCSemanticRules *rules;
    GCSemanticProbeProfile profile;
    GCSemanticPosition *stack;
    uint64_t *pv_table;
    uint16_t *pv_length;
    uint32_t max_depth;
    uint32_t pv_stride;
    uint64_t nodes;
    uint64_t max_nodes;
    uint64_t deadline_ns;
    uint64_t last_time_check_nodes;
    GCCancelFlag *cancel;
    int control; /* 0 continue, 1 node, 2 time, 3 cancellation, 4 error */
    uint32_t selective_depth;
    uint64_t legal_generation_count;
    uint64_t transition_count;
    uint64_t beta_cutoffs;
    uint64_t tt_probes;
    uint64_t tt_hits;
    uint64_t tt_exact_hits;
    uint64_t tt_cutoffs;
    uint64_t tt_stores;
    uint64_t tt_replacements;
    uint64_t tt_collisions;
    uint64_t tt_previous_iteration_hits;
    uint64_t tt_current_iteration_hits;
    uint32_t tt_iteration_generation;
    GCSemanticTable *tt;
    uint64_t history_context[GC_SEM_MAX_PLY + 2][4];
    uint32_t root_ply_offset;
} GCSemanticIterativeContext;

static int gc_semantic_iterative_check_budget(GCSemanticIterativeContext *ctx,
                                               int force) {
    if (ctx->cancel != NULL && gc_cancel_flag_is_requested(ctx->cancel)) {
        ctx->control = 3;
        return 0;
    }
    if (ctx->max_nodes != UINT64_MAX && ctx->nodes >= ctx->max_nodes) {
        ctx->control = 1;
        return 0;
    }
    if (ctx->deadline_ns != UINT64_MAX &&
        (force || ctx->nodes >= ctx->last_time_check_nodes + 128)) {
        ctx->last_time_check_nodes = ctx->nodes;
        if (gc_monotonic_ns() >= ctx->deadline_ns) {
            ctx->control = 2;
            return 0;
        }
    }
    return 1;
}

static int gc_semantic_iterative_terminal_score(int winner,
                                                uint8_t side_to_move,
                                                int ply) {
    if (winner >= 0)
        return winner == side_to_move ? 100000000 - ply : -100000000 + ply;
    return 0;
}

static uint64_t gc_semantic_context_mix(uint64_t x) {
    x ^= x >> 30;
    x *= 0xBF58476D1CE4E5B9ull;
    x ^= x >> 27;
    x *= 0x94D049BB133111EBull;
    return x ^ (x >> 31);
}

static void gc_semantic_context_step(const uint64_t parent[4],
                                     const uint64_t position_digest[4],
                                     uint8_t actor, uint8_t gave_check,
                                     uint16_t history_index,
                                     uint64_t out[4]) {
    uint64_t event = ((uint64_t)actor << 8) | (uint64_t)gave_check;
    for (int i = 0; i < 4; i++) {
        uint64_t x = parent[i] ^ position_digest[i] ^ event ^
                     ((uint64_t)history_index * 0x9E3779B97F4A7C15ull) ^
                     ((uint64_t)(i + 1) * 0xD6E8FEB86659FD93ull);
        out[i] = gc_semantic_context_mix(x + parent[(i + 1) & 3]);
    }
}

static void gc_semantic_context_seed(const GCSemanticPosition *position,
                                     uint64_t out[4]) {
    memset(out, 0, sizeof(uint64_t) * 4);
    for (uint16_t i = 0; i < position->history_len; i++) {
        uint64_t next[4];
        gc_semantic_context_step(out, position->history_digest[i],
                                 position->history_actor[i],
                                 position->history_gave_check[i], i, next);
        memcpy(out, next, sizeof(next));
    }
}

static int32_t gc_semantic_score_to_tt(int32_t score, uint32_t ply) {
    if (score > 90000000) return score + (int32_t)ply;
    if (score < -90000000) return score - (int32_t)ply;
    return score;
}

static int32_t gc_semantic_score_from_tt(int32_t score, uint32_t ply) {
    if (score > 90000000) return score - (int32_t)ply;
    if (score < -90000000) return score + (int32_t)ply;
    return score;
}

static void gc_semantic_tt_store_node(GCSemanticIterativeContext *ctx,
                                      GCSemanticPosition *position,
                                      uint32_t ply, int depth, int score,
                                      int alpha_original, int beta_original,
                                      uint64_t best_action, int has_action) {
    if (ctx->tt == NULL) return;
    GCTTBound bound = GC_TT_BOUND_EXACT;
    if (score <= alpha_original) bound = GC_TT_BOUND_UPPER;
    else if (score >= beta_original) bound = GC_TT_BOUND_LOWER;
    uint64_t replaced = 0;
    if (gc_semantic_tt_store(
            ctx->tt, position, ctx->history_context[ply], depth,
            gc_semantic_score_to_tt(score, ctx->root_ply_offset + ply), bound,
            best_action, has_action,
            &ctx->pv_table[(size_t)ply * ctx->pv_stride],
            ctx->pv_length[ply], &replaced)) {
        ctx->tt_stores++;
        ctx->tt_replacements += replaced;
    }
}

static int gc_semantic_iterative_negamax(GCSemanticIterativeContext *ctx,
                                         uint32_t ply, uint32_t depth,
                                         int alpha, int beta, int pv_node,
                                         int pv_replay) {
    if (!gc_semantic_iterative_check_budget(ctx, 0)) return 0;
    ctx->nodes++;
    if (ply > ctx->selective_depth) ctx->selective_depth = ply;
    ctx->pv_length[ply] = 0;

    GCSemanticPosition *position = &ctx->stack[ply];
    int alpha_original = alpha;
    int beta_original = beta;
    uint64_t tt_action = 0;
    int tt_has_action = 0;
    int winner = -1;
    int terminal = gc_semantic_terminal_status(ctx->rules, position, &winner);
    if (terminal < 0) {
        ctx->control = 4;
        return 0;
    }
    if (terminal != 0) {
        int score = gc_semantic_iterative_terminal_score(
            winner, position->side_to_move,
            (int)(ctx->root_ply_offset + ply));
        gc_semantic_tt_store_node(ctx, position, ply, depth, score,
                                  alpha_original, beta_original, 0, 0);
        return score;
    }
    if (ctx->tt != NULL && !pv_replay) {
        ctx->tt_probes++;
        int32_t stored_score = 0;
        int stored_depth = 0;
        uint8_t stored_bound = GC_TT_BOUND_NONE;
        uint32_t stored_generation = 0;
        uint64_t collisions = 0;
        GCPackedAction stored_pv[GC_SEM_TT_PV_MAX_DEPTH];
        uint16_t stored_pv_length = 0;
        if (gc_semantic_tt_probe(
                ctx->tt, position, ctx->history_context[ply], depth,
                &stored_score, &tt_action, &tt_has_action,
                &stored_depth, &stored_bound, &stored_generation,
                &collisions, stored_pv, &stored_pv_length)) {
            ctx->tt_hits++;
            uint16_t pv_copy_length = stored_pv_length;
            if (pv_copy_length > ctx->pv_stride) pv_copy_length = ctx->pv_stride;
            if (pv_copy_length != 0) {
                memcpy(&ctx->pv_table[(size_t)ply * ctx->pv_stride],
                       stored_pv, sizeof(GCPackedAction) * pv_copy_length);
                ctx->pv_length[ply] = pv_copy_length;
            }
            if (stored_generation < ctx->tt_iteration_generation)
                ctx->tt_previous_iteration_hits++;
            else
                ctx->tt_current_iteration_hits++;
            if (!pv_node && stored_depth >= (int)depth) {
                int score = gc_semantic_score_from_tt(
                    stored_score, ctx->root_ply_offset + ply);
                if (stored_bound == GC_TT_BOUND_EXACT) {
                    ctx->tt_exact_hits++;
                    ctx->tt_cutoffs++;
                    return score;
                }
                if (stored_bound == GC_TT_BOUND_LOWER && score > alpha)
                    alpha = score;
                else if (stored_bound == GC_TT_BOUND_UPPER && score < beta)
                    beta = score;
                if (alpha >= beta) {
                    ctx->tt_cutoffs++;
                    return score;
                }
            }
        }
        ctx->tt_collisions += collisions;
    }
    if (depth == 0) {
        int score = gc_semantic_probe_material(ctx->rules, position, &ctx->profile);
        gc_semantic_tt_store_node(ctx, position, ply, depth, score,
                                  alpha_original, beta_original, 0, 0);
        return score;
    }

    GCSemanticActionBuffer actions;
    gc_semantic_action_buffer_init(&actions);
    if (!gc_semantic_generate_candidate_buffer(ctx->rules, position, &actions)) {
        gc_semantic_action_buffer_free(&actions);
        ctx->control = 4;
        return 0;
    }
    ctx->legal_generation_count++;
    int best = -GC_SEMANTIC_PROBE_INF;
    uint64_t best_action = 0;
    int found = 0;
    if (!pv_node && tt_has_action) {
        for (size_t j = 0; j < actions.count; j++) {
            if (actions.data[j] == tt_action) {
                uint64_t first = actions.data[0];
                actions.data[0] = actions.data[j];
                actions.data[j] = first;
                break;
            }
        }
    }
    size_t i;
    for (i = 0; i < actions.count; i++) {
        if (!gc_semantic_iterative_check_budget(ctx, 1)) break;
        GCSemanticPosition *child = &ctx->stack[ply + 1];
        uint64_t action = actions.data[i];
        if (!gc_semantic_runtime_make_checked(child, ctx->rules, position, action)) continue;
        ctx->transition_count++;
        gc_semantic_context_step(
            ctx->history_context[ply],
            child->history_digest[child->history_len - 1],
            child->history_actor[child->history_len - 1],
            child->history_gave_check[child->history_len - 1],
            child->history_len - 1,
            ctx->history_context[ply + 1]);
        int child_pv = ply == 0 ? 1 : (pv_node && i == 0);
        int child_alpha = pv_node || ply == 0
            ? -GC_SEMANTIC_PROBE_INF : -beta;
        int child_beta = pv_node || ply == 0
            ? GC_SEMANTIC_PROBE_INF : -alpha;
        int branch = gc_semantic_iterative_negamax(
            ctx, ply + 1, depth - 1, child_alpha, child_beta, child_pv,
            pv_replay);
        if (ctx->control != 0) break;
        int score = -branch;
        if (!found || score > best || (score == best && action < best_action)) {
            found = 1;
            best = score;
            best_action = action;
            ctx->pv_table[(size_t)ply * ctx->pv_stride] = action;
            uint16_t child_len = ctx->pv_length[ply + 1];
            ctx->pv_length[ply] = (uint16_t)(1 + child_len);
            if (child_len > 0) {
                memcpy(&ctx->pv_table[(size_t)ply * ctx->pv_stride + 1],
                       &ctx->pv_table[(size_t)(ply + 1) * ctx->pv_stride],
                       sizeof(uint64_t) * child_len);
            }
        }
        if (score > alpha) alpha = score;
        if (alpha >= beta) {
            ctx->beta_cutoffs++;
            break;
        }
    }
    gc_semantic_action_buffer_free(&actions);
    if (ctx->control != 0) return 0;
    if (ctx->tt != NULL && !pv_replay && pv_node && found) {
        /* Re-search the selected branch with a full PV window so TT ordering
         * cannot change the deterministic principal line. */
        GCSemanticPosition *best_child = &ctx->stack[ply + 1];
        if (!gc_semantic_runtime_make_checked(
                best_child, ctx->rules, position, best_action)) {
            ctx->control = 4;
            return 0;
        }
        gc_semantic_context_step(
            ctx->history_context[ply],
            best_child->history_digest[best_child->history_len - 1],
            best_child->history_actor[best_child->history_len - 1],
            best_child->history_gave_check[best_child->history_len - 1],
            best_child->history_len - 1,
            ctx->history_context[ply + 1]);
        int branch = gc_semantic_iterative_negamax(
            ctx, ply + 1, depth - 1, -GC_SEMANTIC_PROBE_INF,
            GC_SEMANTIC_PROBE_INF, 1, 1);
        if (ctx->control != 0) return 0;
        /* Keep the already selected score/bound.  This pass is solely to
         * materialize the canonical PV for the selected action; the main
         * alpha-beta result remains authoritative. */
        (void)branch;
        ctx->pv_table[(size_t)ply * ctx->pv_stride] = best_action;
        uint16_t child_len = ctx->pv_length[ply + 1];
        ctx->pv_length[ply] = (uint16_t)(1 + child_len);
        if (child_len > 0) {
            memcpy(&ctx->pv_table[(size_t)ply * ctx->pv_stride + 1],
                   &ctx->pv_table[(size_t)(ply + 1) * ctx->pv_stride],
                   sizeof(uint64_t) * child_len);
        }
    }
    if (found) {
        gc_semantic_tt_store_node(ctx, position, ply, depth, best,
                                  alpha_original, beta_original,
                                  best_action, 1);
    } else {
        gc_semantic_tt_store_node(ctx, position, ply, depth, 0,
                                  alpha_original, beta_original, 0, 0);
    }
    return found ? best : 0;
}

static int gc_semantic_iterative_fallback(GCSemanticIterativeContext *ctx,
                                          uint64_t *action_out) {
    GCSemanticActionBuffer actions;
    gc_semantic_action_buffer_init(&actions);
    if (!gc_semantic_generate_candidate_buffer(ctx->rules, &ctx->stack[0], &actions)) {
        gc_semantic_action_buffer_free(&actions);
        return 0;
    }
    uint64_t best = 0;
    int found = 0;
    size_t i;
    for (i = 0; i < actions.count; i++) {
        if (gc_semantic_runtime_make_checked(&ctx->stack[1], ctx->rules,
                                             &ctx->stack[0], actions.data[i])) {
            if (!found || actions.data[i] < best) {
                best = actions.data[i];
                found = 1;
            }
        }
    }
    gc_semantic_action_buffer_free(&actions);
    if (found && action_out != NULL) *action_out = best;
    return found;
}

static int gc_semantic_parse_profile(PyObject *board_values,
                                     PyObject *hand_values,
                                     const GCSemanticRules *rules,
                                     GCSemanticProbeProfile *profile) {
    memset(profile, 0, sizeof(*profile));
    if (board_values == Py_None) board_values = NULL;
    if (hand_values == Py_None) hand_values = NULL;
    if ((board_values == NULL) != (hand_values == NULL)) {
        PyErr_SetString(PyExc_ValueError,
                        "semantic evaluator board/hand profile must be supplied together");
        return 0;
    }
    if (board_values == NULL) return 1;
    if ((!PyList_Check(board_values) && !PyTuple_Check(board_values)) ||
        (!PyList_Check(hand_values) && !PyTuple_Check(hand_values)) ||
        PySequence_Size(board_values) != rules->type_count ||
        PySequence_Size(hand_values) != rules->type_count) {
        PyErr_SetString(PyExc_ValueError,
                        "semantic evaluator profile length must match type_count");
        return 0;
    }
    for (uint16_t type = 0; type < rules->type_count; type++) {
        PyObject *bv = PySequence_GetItem(board_values, type);
        PyObject *hv = PySequence_GetItem(hand_values, type);
        long b = PyLong_AsLong(bv), h = PyLong_AsLong(hv);
        Py_DECREF(bv); Py_DECREF(hv);
        if (PyErr_Occurred() || b < -1000000 || b > 1000000 ||
            h < -1000000 || h > 1000000) {
            PyErr_SetString(PyExc_ValueError,
                            "semantic evaluator values must be bounded integers");
            return 0;
        }
        profile->board[type] = (int)b;
        profile->hand[type] = (int)h;
    }
    profile->supplied = 1;
    return 1;
}

static PyObject *gc_semantic_iterative_search(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule, *position_capsule;
    PyObject *max_nodes_obj = Py_None, *max_time_obj = Py_None;
    PyObject *cancel_capsule = Py_None, *board_values = NULL, *hand_values = NULL;
    unsigned int max_depth;
    unsigned int root_ply_offset = 0;
    unsigned int tt_megabytes = 0;
    if (!PyArg_ParseTuple(args, "OOI|OOOOOII", &rules_capsule, &position_capsule,
                          &max_depth, &max_nodes_obj, &max_time_obj,
                          &cancel_capsule, &board_values, &hand_values,
                          &root_ply_offset, &tt_megabytes)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(
        rules_capsule, GC_SEM_RULES_CAPSULE);
    GCSemanticPosition *position = (GCSemanticPosition *)PyCapsule_GetPointer(
        position_capsule, GC_SEM_POSITION_CAPSULE);
    if (!rules || !position) return NULL;
    if (max_depth > GC_SEM_MAX_PLY) {
        PyErr_SetString(PyExc_ValueError, "semantic max_depth exceeds GC_SEM_MAX_PLY");
        return NULL;
    }
    if (root_ply_offset > 1) {
        PyErr_SetString(PyExc_ValueError, "semantic root ply offset must be 0 or 1");
        return NULL;
    }
    if (tt_megabytes > 1024) {
        PyErr_SetString(PyExc_ValueError, "semantic tt_megabytes must be in [0, 1024]");
        return NULL;
    }
    if (!gc_semantic_require_matching_rules(rules, position) ||
        !gc_semantic_require_exact_history(position)) return NULL;
    if (rules->declaration_count != 0) {
        PyErr_SetString(PyExc_ValueError,
                        "semantic iterative search does not support declaration-bearing rulesets");
        return NULL;
    }
    GCSemanticProbeProfile profile;
    if (!gc_semantic_parse_profile(board_values, hand_values, rules, &profile)) return NULL;
    GCCancelFlag *cancel = NULL;
    if (cancel_capsule != Py_None) {
        cancel = gc_get_cancel(cancel_capsule);
        if (!cancel) return NULL;
    }
    uint64_t max_nodes = UINT64_MAX;
    if (max_nodes_obj != Py_None) {
        long long value = PyLong_AsLongLong(max_nodes_obj);
        if (value == -1 && PyErr_Occurred()) return NULL;
        if (value < 0) {
            PyErr_SetString(PyExc_ValueError, "semantic max_nodes must be >= 0");
            return NULL;
        }
        max_nodes = (uint64_t)value;
    }
    uint64_t max_time_ns = UINT64_MAX;
    if (max_time_obj != Py_None) {
        double seconds = PyFloat_AsDouble(max_time_obj);
        if (PyErr_Occurred() || seconds < 0 || seconds != seconds || seconds > 1e12) {
            PyErr_SetString(PyExc_ValueError,
                            "semantic max_time_seconds must be finite and non-negative");
            return NULL;
        }
        max_time_ns = (uint64_t)(seconds * 1e9);
    }
    GCSemanticIterativeContext ctx;
    memset(&ctx, 0, sizeof(ctx));
    ctx.rules = rules;
    ctx.profile = profile;
    ctx.max_depth = max_depth;
    ctx.root_ply_offset = root_ply_offset;
    ctx.pv_stride = max_depth + 1;
    ctx.max_nodes = max_nodes;
    ctx.cancel = cancel;
    ctx.deadline_ns = max_time_ns == UINT64_MAX
        ? UINT64_MAX : gc_deadline_after(gc_monotonic_ns(), max_time_ns);
    if (tt_megabytes != 0) {
        size_t requested_bytes = (size_t)tt_megabytes * (size_t)1024 * (size_t)1024;
        ctx.tt = gc_semantic_tt_create(requested_bytes, NULL);
        if (ctx.tt == NULL) {
            PyErr_NoMemory();
            return NULL;
        }
    }
    /* Keep one spare semantic position for the deterministic root fallback. */
    size_t levels = (size_t)max_depth + 2;
    size_t position_bytes = 0, pv_bytes = 0, length_bytes = 0;
    if (!gc_checked_size_mul(levels, sizeof(GCSemanticPosition), &position_bytes) ||
        !gc_checked_size_mul(levels, levels, &pv_bytes) ||
        !gc_checked_size_mul(pv_bytes, sizeof(uint64_t), &pv_bytes) ||
        !gc_checked_size_mul(levels, sizeof(uint16_t), &length_bytes)) {
        PyErr_SetString(PyExc_OverflowError, "semantic search state size overflow");
        gc_semantic_tt_free(ctx.tt);
        return NULL;
    }
    ctx.stack = (GCSemanticPosition *)calloc(1, position_bytes);
    ctx.pv_table = (uint64_t *)calloc(1, pv_bytes);
    ctx.pv_length = (uint16_t *)calloc(1, length_bytes);
    if (!ctx.stack || !ctx.pv_table || !ctx.pv_length) {
        free(ctx.stack); free(ctx.pv_table); free(ctx.pv_length);
        gc_semantic_tt_free(ctx.tt);
        PyErr_NoMemory();
        return NULL;
    }
    memcpy(&ctx.stack[0], position, sizeof(GCSemanticPosition));
    gc_semantic_context_seed(position, ctx.history_context[0]);
    uint64_t completed_pv[GC_SEM_MAX_PLY + 1];
    uint16_t completed_len = 0;
    uint64_t completed_action = 0;
    int completed_has_action = 0;
    int completed_score = 0;
    uint32_t completed_depth = 0;
    int completed_iteration = 0;
    int used_fallback = 0;
    uint64_t start_ns = gc_monotonic_ns();
    Py_BEGIN_ALLOW_THREADS
    for (uint32_t depth = 1; depth <= max_depth; depth++) {
        if (!gc_semantic_iterative_check_budget(&ctx, 1)) break;
        ctx.tt_iteration_generation = gc_semantic_tt_next_generation(ctx.tt);
        int score = gc_semantic_iterative_negamax(&ctx, 0, depth,
                                                  -GC_SEMANTIC_PROBE_INF,
                                                  GC_SEMANTIC_PROBE_INF, 1, 0);
        if (ctx.control != 0) break;
        completed_score = score;
        completed_depth = depth;
        completed_iteration = 1;
        completed_len = ctx.pv_length[0];
        completed_has_action = completed_len > 0;
        completed_action = completed_has_action ? ctx.pv_table[0] : 0;
        if (completed_len > GC_SEM_MAX_PLY + 1) completed_len = GC_SEM_MAX_PLY + 1;
        memcpy(completed_pv, ctx.pv_table,
               sizeof(uint64_t) * completed_len);
    }
    if (!completed_iteration) {
        uint64_t fallback = 0;
        if (gc_semantic_iterative_fallback(&ctx, &fallback)) {
            completed_action = fallback;
            completed_has_action = 1;
            used_fallback = 1;
        }
    }
    Py_END_ALLOW_THREADS
    const char *reason = "completed";
    if (ctx.control == 1) reason = "node_budget";
    else if (ctx.control == 2) reason = "time_budget";
    else if (ctx.control == 3) reason = "cancelled";
    else if (ctx.control == 4) reason = "internal_error";
    uint64_t elapsed_ns = gc_monotonic_ns() - start_ns;
    PyObject *pv = PyTuple_New((Py_ssize_t)completed_len);
    if (!pv) {
        free(ctx.stack); free(ctx.pv_table); free(ctx.pv_length);
        gc_semantic_tt_free(ctx.tt);
        return NULL;
    }
    for (uint16_t i = 0; i < completed_len; i++) {
        PyObject *value = PyLong_FromUnsignedLongLong(completed_pv[i]);
        if (!value) {
            Py_DECREF(pv); free(ctx.stack); free(ctx.pv_table); free(ctx.pv_length);
            gc_semantic_tt_free(ctx.tt);
            return NULL;
        }
        PyTuple_SET_ITEM(pv, (Py_ssize_t)i, value);
    }
    PyObject *best_action_obj = completed_has_action
        ? PyLong_FromUnsignedLongLong(completed_action) : Py_NewRef(Py_None);
    if (!best_action_obj) {
        Py_DECREF(pv); free(ctx.stack); free(ctx.pv_table); free(ctx.pv_length);
        gc_semantic_tt_free(ctx.tt);
        return NULL;
    }
    PyObject *out = Py_BuildValue(
        "{s:i,s:O,s:K,s:I,s:I,s:O,s:K,s:K,s:K,s:K,s:K,s:s,s:i,s:s,"
        "s:K,s:K,s:K,s:K,s:K,s:K,s:K,s:K,s:K,s:K,s:K,s:K}",
        "score", completed_score,
        "best_action", best_action_obj,
        "nodes", ctx.nodes,
        "completed_depth", completed_depth,
        "selective_depth", ctx.selective_depth,
        "principal_variation", pv,
        "elapsed_nanoseconds", elapsed_ns,
        "legal_generation_count", ctx.legal_generation_count,
        "transition_count", ctx.transition_count,
        "beta_cutoffs", ctx.beta_cutoffs,
        "qnodes", (uint64_t)0,
        "termination_reason", reason,
        "used_fallback", used_fallback,
        "tt_status", ctx.tt == NULL ? "NOT_STARTED" : "ENABLED",
        "tt_probes", ctx.tt_probes,
        "tt_hits", ctx.tt_hits,
        "tt_exact_hits", ctx.tt_exact_hits,
        "tt_stores", ctx.tt_stores,
        "tt_replacements", ctx.tt_replacements,
        "tt_collisions", ctx.tt_collisions,
        "tt_cutoffs", ctx.tt_cutoffs,
        "tt_previous_iteration_hits", ctx.tt_previous_iteration_hits,
        "tt_current_iteration_hits", ctx.tt_current_iteration_hits,
        "tt_allocated_bytes", ctx.tt == NULL ? (uint64_t)0 : (uint64_t)ctx.tt->allocated_bytes,
        "tt_occupied_entries", ctx.tt == NULL ? (uint64_t)0 : ctx.tt->occupied_entries,
        "tt_entry_bytes", ctx.tt == NULL ? (uint64_t)0 : (uint64_t)gc_semantic_tt_entry_bytes());
    Py_DECREF(best_action_obj);
    Py_DECREF(pv);
    free(ctx.stack); free(ctx.pv_table); free(ctx.pv_length);
    gc_semantic_tt_free(ctx.tt);
    if (!out) return NULL;
    return out;
}

static PyObject *gc_semantic_search_runtime_sizes(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    return Py_BuildValue("{s:n,s:n,s:n}",
                         "position_bytes", (Py_ssize_t)sizeof(GCSemanticPosition),
                         "undo_bytes", (Py_ssize_t)sizeof(GCSemanticUndo),
                         "max_ply", (Py_ssize_t)GC_SEM_MAX_PLY);
}

static PyObject *gc_semantic_perft(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *rules_capsule, *position_capsule;
    unsigned int depth;
    if (!PyArg_ParseTuple(args, "OOI", &rules_capsule, &position_capsule, &depth)) return NULL;
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(rules_capsule, GC_SEM_RULES_CAPSULE);
    GCSemanticPosition *position = (GCSemanticPosition *)PyCapsule_GetPointer(position_capsule, GC_SEM_POSITION_CAPSULE);
    if (!rules || !position) return NULL;
    if (!gc_semantic_require_matching_rules(rules, position)) return NULL;
    int ok = 1;
    unsigned long long nodes = gc_semantic_perft_rec(rules, position, depth, &ok);
    if (!ok) { if (!PyErr_Occurred()) PyErr_SetString(PyExc_RuntimeError, "semantic perft failed"); return NULL; }
    return PyLong_FromUnsignedLongLong(nodes);
}

static PyObject *gc_compile_semantic_rules(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *payload;
    if (!PyArg_ParseTuple(args, "O", &payload)) {
        return NULL;
    }
    if (!PyDict_Check(payload)) {
        PyErr_SetString(PyExc_TypeError,
                        "compile_semantic_rules expects a dict payload");
        return NULL;
    }
    GCSemanticRules *rules = gc_semantic_rules_compile(payload);
    if (rules == NULL) {
        return NULL;
    }
    return PyCapsule_New(rules, GC_SEM_RULES_CAPSULE,
                         gc_semantic_rules_capsule_free);
}

static PyObject *gc_semantic_rules_info(PyObject *self, PyObject *args) {
    (void)self;
    PyObject *capsule;
    if (!PyArg_ParseTuple(args, "O", &capsule)) {
        return NULL;
    }
    GCSemanticRules *rules = (GCSemanticRules *)PyCapsule_GetPointer(
        capsule, GC_SEM_RULES_CAPSULE);
    if (rules == NULL) {
        return NULL;
    }
    return gc_semantic_rules_build_info(rules);
}

static PyObject *gc_semantic_action_layout(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    return Py_BuildValue(
        "{s:i,s:i,s:i,s:i,"
         "s:i,s:i,s:i,s:i,s:i,"
         "s:i,s:i,s:i,"
         "s:i,s:i,s:i,"
         "s:i,s:i}",
        "legacy_board_kind", (int)GC_ACTION_KIND_BOARD,
        "legacy_drop_kind", (int)GC_ACTION_KIND_DROP,
        "semantic_board_kind", (int)GC_ACTION_KIND_SEMANTIC_BOARD,
        "semantic_drop_kind", (int)GC_ACTION_KIND_SEMANTIC_DROP,
        "to_shift", (int)GC_ACTION_TO_SHIFT,
        "from_shift", (int)GC_ACTION_FROM_SHIFT,
        "promo_shift", (int)GC_ACTION_PROMO_SHIFT,
        "base_shift", (int)GC_ACTION_BASE_SHIFT,
        "kind_shift", (int)GC_ACTION_KIND_SHIFT,
        "pattern_shift", (int)GC_ACTION_PATTERN_SHIFT,
        "geometry_shift", (int)GC_ACTION_GEOMETRY_SHIFT,
        "actor_current_shift", (int)GC_ACTION_ACTOR_CURRENT_SHIFT,
        "pattern_bits", 8,
        "geometry_bits", 12,
        "actor_current_bits", 8,
        "max_patterns", (int)GC_ACTION_MAX_PATTERNS,
        "max_geometries", (int)GC_ACTION_MAX_GEOMETRIES);
}

static PyMethodDef gc_methods[] = {
    {"native_available", gc_native_available, METH_NOARGS,
     "Return True (the native kernel is built)."},
    {"native_version", gc_native_version, METH_NOARGS,
     "Return the native kernel version string."},
    {"native_capabilities", gc_native_capabilities, METH_NOARGS,
     "Return capability metadata."},
    {"native_rules_info", gc_native_rules_info, METH_VARARGS,
     "native_rules_info(rules) -> debugging dump of compiled rules"},
    {"compile_rules", gc_compile_rules, METH_VARARGS,
     "compile_rules(payload) -> rules capsule"},
    {"pack_position", gc_pack_position, METH_VARARGS,
     "pack_position(rules, payload) -> position capsule"},
    {"replay_position", gc_native_replay_position, METH_VARARGS,
     "replay_position(rules, payload, actions) -> position capsule with full history"},
    {"native_legal_actions", gc_native_legal_actions, METH_VARARGS,
     "native_legal_actions(rules, position) -> tuple of packed actions"},
    {"native_pseudo_actions", gc_native_pseudo_actions, METH_VARARGS,
     "native_pseudo_actions(rules, position) -> tuple of packed pseudo actions"},
    {"native_attack_map", gc_native_attack_map, METH_VARARGS,
     "native_attack_map(rules, position, by_owner) -> tuple of attacked squares"},
    {"native_terminal", gc_native_terminal, METH_VARARGS,
     "native_terminal(rules, position) -> terminal status string"},
    {"native_child_snapshot", gc_native_child_snapshot, METH_VARARGS,
     "native_child_snapshot(rules, position, action) -> snapshot dict"},
    {"native_snapshot", gc_native_snapshot, METH_VARARGS,
     "native_snapshot(rules, position) -> snapshot dict of the current position"},
    {"native_make_unmake_roundtrip", gc_native_make_unmake_roundtrip,
     METH_VARARGS,
     "native_make_unmake_roundtrip(rules, position, action) -> make/unmake check dict"},
    {"native_long_make_unmake_roundtrip", gc_native_long_make_unmake_roundtrip,
     METH_VARARGS,
     "native_long_make_unmake_roundtrip(rules, payload, actions) -> full replay/unmake check dict"},
    {"native_make_checked", gc_native_make_checked, METH_VARARGS,
     "native_make_checked(rules, position, action) -> child snapshot or NativeActionError"},
    {"native_perft", gc_native_perft, METH_VARARGS,
     "native_perft(rules, position, depth, divide=False) -> result dict"},
    {"compile_evaluation", gc_compile_evaluation, METH_VARARGS,
     "compile_evaluation(rules, payload) -> evaluation tables capsule"},
    {"native_fixed_depth_search", gc_native_fixed_depth_search, METH_VARARGS,
     "native_fixed_depth_search(rules, eval, position, depth) -> result dict"},
    {"create_search_engine", gc_create_search_engine, METH_VARARGS,
     "create_search_engine(rules, eval, tt_megabytes) -> engine capsule"},
    {"search_engine_clear_tt", gc_search_engine_clear_tt, METH_VARARGS,
     "search_engine_clear_tt(engine) -> None"},
    {"search_engine_tt_info", gc_search_engine_tt_info, METH_VARARGS,
     "search_engine_tt_info(engine) -> dict"},
    {"engine_fixed_depth_search", gc_engine_fixed_depth_search, METH_VARARGS,
     "engine_fixed_depth_search(engine, position, depth) -> result dict (TT on)"},
    {"create_cancel_flag", gc_create_cancel_flag, METH_NOARGS,
     "create_cancel_flag() -> cancel capsule"},
    {"request_cancel", gc_request_cancel, METH_VARARGS,
     "request_cancel(cancel) -> None"},
    {"native_iterative_search", gc_native_iterative_search, METH_VARARGS,
     "native_iterative_search(engine, position, max_depth, max_nodes, "
     "max_time_seconds, cancel) -> result dict"},
    {"compile_semantic_rules", gc_compile_semantic_rules, METH_VARARGS,
     "compile_semantic_rules(payload) -> semantic rules capsule (compile only)"},
    {"semantic_rules_info", gc_semantic_rules_info, METH_VARARGS,
     "semantic_rules_info(capsule) -> reconstructed normalized payload dict"},
    {"semantic_action_layout", gc_semantic_action_layout, METH_NOARGS,
     "semantic_action_layout() -> exact 64-bit semantic action identity layout"},
    {"semantic_pack_position", gc_semantic_pack_position, METH_VARARGS,
     "semantic_pack_position(rules, payload) -> semantic position capsule"},
    {"semantic_position_snapshot", gc_semantic_position_snapshot, METH_VARARGS,
     "semantic_position_snapshot(rules, position) -> canonical board snapshot"},
    {"semantic_position_key", gc_semantic_position_key, METH_VARARGS,
     "semantic_position_key(rules, position) -> SHA-256 hex digest"},
    {"sha256_hex", gc_sha256_hex_api, METH_VARARGS,
     "sha256_hex(bytes) -> lowercase SHA-256 digest"},
    {"semantic_action_pack", gc_semantic_action_pack, METH_VARARGS,
     "semantic_action_pack(fields) -> exact 64-bit semantic action"},
    {"semantic_action_unpack", gc_semantic_action_unpack, METH_VARARGS,
     "semantic_action_unpack(action) -> exact semantic action fields"},
    {"semantic_candidate_actions", gc_semantic_candidate_actions, METH_VARARGS,
     "semantic_candidate_actions(rules, position) -> exact candidate actions"},
    {"semantic_history_occurrences", gc_semantic_history_occurrences, METH_VARARGS,
     "semantic_history_occurrences(position, lo, hi) -> occurrence count"},
    {"semantic_make_checked", gc_semantic_make_checked, METH_VARARGS,
     "semantic_make_checked(rules, position, action) -> child position capsule"},
    {"semantic_is_square_attacked", gc_semantic_is_square_attacked, METH_VARARGS,
     "semantic_is_square_attacked(rules, position, square, by_owner) -> bool"},
    {"semantic_in_check", gc_semantic_in_check, METH_VARARGS,
     "semantic_in_check(rules, position, side) -> bool"},
    {"semantic_assess_declaration", gc_semantic_assess_declaration, METH_VARARGS,
     "semantic_assess_declaration(rules, position, declaration_id) -> result"},
    {"semantic_available_declarations", gc_semantic_available_declarations, METH_VARARGS,
     "semantic_available_declarations(rules, position) -> tuple of results"},
    {"_semantic_action_delivers_check_debug", gc_semantic_action_delivers_check_debug, METH_VARARGS,
     "test-only semantic action witness inspection; not a production API"},
    {"semantic_make_unmake_roundtrip", gc_semantic_make_unmake_roundtrip, METH_VARARGS,
     "semantic_make_unmake_roundtrip(rules, position, action) -> roundtrip result"},
    {"semantic_candidate_perft", gc_semantic_perft, METH_VARARGS,
     "semantic_candidate_perft(rules, position, depth) -> recursive guarded candidate node count"},
    {"semantic_guarded_actions", gc_semantic_guarded_actions, METH_VARARGS,
     "semantic_guarded_actions(rules, position) -> exact guarded action set"},
    {"semantic_guarded_actions_audit", gc_semantic_guarded_actions_audit, METH_VARARGS,
     "test-only guarded action counters and exact action set"},
    {"semantic_transient_legal_actions", gc_semantic_transient_legal_actions, METH_VARARGS,
     "semantic_transient_legal_actions(rules, position) -> ordered legal action set without history"},
    {"semantic_transient_legal_actions_audit", gc_semantic_transient_legal_actions_audit, METH_VARARGS,
     "test-only transient legality counters and exact action set"},
    {"semantic_terminal", gc_semantic_terminal, METH_VARARGS,
     "semantic_terminal(rules, position) -> exact terminal status"},
    {"semantic_probe_search", gc_semantic_probe_search, METH_VARARGS,
     "semantic_probe_search(rules, position, depth) -> bounded generic AlphaBeta probe"},
    {"semantic_iterative_search", gc_semantic_iterative_search, METH_VARARGS,
     "semantic_iterative_search(rules, position, max_depth[, max_nodes, max_time_seconds, cancel, board_values, hand_values]) -> no-TT iterative result"},
    {"semantic_search_runtime_sizes", gc_semantic_search_runtime_sizes, METH_NOARGS,
     "semantic_search_runtime_sizes() -> semantic search state byte sizes"},
    {"semantic_fixed_depth_search", gc_semantic_probe_search, METH_VARARGS,
     "semantic_fixed_depth_search(rules, position, depth[, board_values, hand_values]) -> fixed-depth semantic AlphaBeta"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef gc_module = {
    PyModuleDef_HEAD_INIT,
    "_native_core",
    "GenericChess native rule kernel (hardening + fixed-depth search).",
    -1,
    gc_methods
};

PyMODINIT_FUNC PyInit__native_core(void) {
    gc_native_error = PyErr_NewException("_native_core.NativeActionError",
                                         PyExc_ValueError, NULL);
    if (gc_native_error == NULL) {
        return NULL;
    }
    PyObject *module = PyModule_Create(&gc_module);
    if (module == NULL) {
        return NULL;
    }
    Py_INCREF(gc_native_error);
    PyModule_AddObject(module, "NativeActionError", gc_native_error);
    return module;
}
