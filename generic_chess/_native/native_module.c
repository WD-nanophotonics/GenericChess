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
#include "native_hash.h"
#include "native_movegen.h"
#include "native_perft.h"
#include "native_rules.h"
#include "native_state.h"

#define GC_RULES_CAPSULE "generic_chess._native_core.gc_rules"
#define GC_POSITION_CAPSULE "generic_chess._native_core.gc_position"

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
    return PyUnicode_FromString("0.1.0");
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
    PyDict_SetItemString(dict, "max_actions", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "make_unmake", value);
    Py_DECREF(value);
    value = PyBool_FromLong(1);
    PyDict_SetItemString(dict, "native_perft", value);
    Py_DECREF(value);
    return dict;
}

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
    int ok = 1;
    PyObject *side_obj = PyDict_GetItemString(payload, "side");
    PyObject *ply_obj = PyDict_GetItemString(payload, "ply");
    PyObject *root_count_obj = PyDict_GetItemString(payload, "root_hash_count");
    PyObject *board = PyDict_GetItemString(payload, "board");
    PyObject *hands = PyDict_GetItemString(payload, "hands");
    if (!side_obj || !ply_obj || !root_count_obj || !board || !hands ||
        !PyList_Check(board) || !PyList_Check(hands)) {
        PyErr_SetString(PyExc_ValueError, "pack_position payload missing fields");
        return NULL;
    }
    GCBoardPayload bp;
    memset(&bp, 0, sizeof(bp));
    bp.side_to_move = (uint8_t)gc_py_long_as_long(side_obj, &ok);
    bp.ply = (uint16_t)gc_py_long_as_long(ply_obj, &ok);
    bp.root_hash_count = (uint16_t)gc_py_long_as_long(root_count_obj, &ok);
    Py_ssize_t board_len = PyList_Size(board);
    if (board_len != (Py_ssize_t)rules->squares) {
        PyErr_SetString(PyExc_ValueError, "board payload length mismatch");
        return NULL;
    }
    Py_ssize_t sq;
    for (sq = 0; sq < board_len; sq++) {
        PyObject *cell = PyList_GetItem(board, sq);
        if (cell == Py_None) {
            continue;
        }
        if (!PyList_Check(cell) || PyList_Size(cell) != 4) {
            PyErr_SetString(PyExc_ValueError, "board cell must be None or [base,current,owner,promoted]");
            return NULL;
        }
        GCPiece *piece = &bp.board[sq];
        piece->base_type = (GCTypeIndex)gc_py_long_as_long(
            PyList_GetItem(cell, 0), &ok);
        piece->current_type = (GCTypeIndex)gc_py_long_as_long(
            PyList_GetItem(cell, 1), &ok);
        piece->owner = (uint8_t)gc_py_long_as_long(
            PyList_GetItem(cell, 2), &ok);
        piece->promoted = (uint8_t)gc_py_long_as_long(
            PyList_GetItem(cell, 3), &ok);
        piece->occupied = 1;
    }
    if (PyList_Size(hands) != 2) {
        PyErr_SetString(PyExc_ValueError, "hands payload must have two owners");
        return NULL;
    }
    int owner;
    for (owner = 0; owner < 2; owner++) {
        PyObject *counts = PyList_GetItem(hands, owner);
        Py_ssize_t len = PyList_Size(counts);
        Py_ssize_t t;
        for (t = 0; t < len && t < GC_MAX_TYPES; t++) {
            bp.hand_counts[owner][t] =
                (uint16_t)gc_py_long_as_long(PyList_GetItem(counts, t), &ok);
        }
    }
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
    GCPackedAction actions[GC_MAX_ACTIONS];
    int n = gc_legal_actions(rules, pos, actions, GC_MAX_ACTIONS);
    PyObject *result = PyTuple_New(n);
    if (result == NULL) {
        return NULL;
    }
    int i;
    for (i = 0; i < n; i++) {
        PyObject *value = PyLong_FromUnsignedLongLong(actions[i]);
        if (value == NULL) {
            Py_DECREF(result);
            return NULL;
        }
        PyTuple_SET_ITEM(result, i, value);
    }
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
    GCPackedAction actions[GC_MAX_ACTIONS];
    int n = gc_pseudo_actions(rules, pos, actions, GC_MAX_ACTIONS);
    PyObject *result = PyTuple_New(n);
    if (result == NULL) {
        return NULL;
    }
    int i;
    for (i = 0; i < n; i++) {
        PyObject *value = PyLong_FromUnsignedLongLong(actions[i]);
        if (value == NULL) {
            Py_DECREF(result);
            return NULL;
        }
        PyTuple_SET_ITEM(result, i, value);
    }
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
    GCTerminal term = gc_terminal(rules, pos);
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
    if (!gc_make_move_verify(&copy, rules, (GCPackedAction)action, &undo)) {
        PyErr_SetString(PyExc_ValueError, "native make failed for action");
        return NULL;
    }
    GCTerminal term = gc_terminal(rules, &copy);
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
    GCTerminal term = gc_terminal(rules, pos);
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

    uint64_t total = 0;
    PyObject *divide_dict = NULL;
    if (divide) {
        GCPackedAction actions[GC_MAX_ACTIONS];
        uint64_t counts[GC_MAX_ACTIONS];
        int n = 0;
        gc_perft_divide(rules, pos, depth, actions, counts, &n, &total);
        divide_dict = PyDict_New();
        if (divide_dict == NULL) {
            return NULL;
        }
        int i;
        for (i = 0; i < n; i++) {
            PyObject *key = PyLong_FromUnsignedLongLong(actions[i]);
            PyObject *value = PyLong_FromUnsignedLongLong(counts[i]);
            PyDict_SetItem(divide_dict, key, value);
            Py_DECREF(key);
            Py_DECREF(value);
        }
    } else {
        total = gc_perft(rules, pos, depth);
    }

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
    {"native_perft", gc_native_perft, METH_VARARGS,
     "native_perft(rules, position, depth, divide=False) -> result dict"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef gc_module = {
    PyModuleDef_HEAD_INIT,
    "_native_core",
    "GenericChess Native Phase 1 rule kernel.",
    -1,
    gc_methods
};

PyMODINIT_FUNC PyInit__native_core(void) {
    return PyModule_Create(&gc_module);
}
