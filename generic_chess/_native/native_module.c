#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <stdlib.h>
#include <string.h>
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

#define GC_RULES_CAPSULE "generic_chess._native_core.gc_rules"
#define GC_POSITION_CAPSULE "generic_chess._native_core.gc_position"
#define GC_EVAL_CAPSULE "generic_chess._native_core.gc_eval"
#define GC_ENGINE_CAPSULE "generic_chess._native_core.gc_engine"
#define GC_CANCEL_CAPSULE "generic_chess._native_core.gc_cancel"

static PyObject *gc_native_error = NULL;

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
    return PyUnicode_FromString("0.3.0");
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
    value = PyUnicode_FromString("native-0.3.0");
    PyDict_SetItemString(dict, "native_schema", value);
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
