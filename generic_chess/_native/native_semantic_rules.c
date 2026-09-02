/* Phase 1.9C-1 C-owned semantic rules capsule (ADR-017).
 *
 * Compile-only contract: parses the deterministic numeric payload,
 * owns it in C memory, and reconstructs the exact normalized payload.
 * No semantic position/execution is implemented here. */

#include <Python.h>

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "native_semantic_rules.h"

/* ------------------------------------------------------------------ helpers */

static int sem_get_list(PyObject *dict, const char *key, PyObject **out) {
    *out = PyDict_GetItemString(dict, key);
    if (*out == NULL || !PyList_Check(*out)) {
        PyErr_SetString(PyExc_ValueError, "expected a list field");
        return 0;
    }
    return 1;
}

/* ------------------------------------------------------------------ strict
 * Phase 1.9C-1 Review R1: validation-before-cast numeric readers.
 * Range/domain checks happen in a wide representation first; the narrowing
 * cast happens only after the value is proven representable.  Unknown enum
 * codes, out-of-range identities and oversized list counts fail closed. */

static int sem_int_read(PyObject *obj, int64_t *out) {
    if (obj == NULL || obj == Py_None || !PyLong_Check(obj)) {
        PyErr_SetString(PyExc_ValueError, "expected an integer");
        return 0;
    }
    int overflow = 0;
    long long v = PyLong_AsLongLongAndOverflow(obj, &overflow);
    if (overflow) {
        PyErr_SetString(PyExc_ValueError, "integer out of range");
        return 0;
    }
    *out = (int64_t)v;
    return 1;
}

static int sem_u8(PyObject *obj, uint8_t *out) {
    int64_t v;
    if (!sem_int_read(obj, &v)) {
        return 0;
    }
    if (v < 0 || v > 0xFF) {
        PyErr_SetString(PyExc_ValueError, "u8 value out of range");
        return 0;
    }
    *out = (uint8_t)v;
    return 1;
}

static int sem_u16(PyObject *obj, uint16_t *out) {
    int64_t v;
    if (!sem_int_read(obj, &v)) {
        return 0;
    }
    if (v < 0 || v > 0xFFFF) {
        PyErr_SetString(PyExc_ValueError, "u16 value out of range");
        return 0;
    }
    *out = (uint16_t)v;
    return 1;
}

static int sem_u32(PyObject *obj, uint32_t *out) {
    if (obj == NULL || !PyLong_Check(obj)) {
        PyErr_SetString(PyExc_ValueError, "expected unsigned 32-bit integer");
        return 0;
    }
    unsigned long long value = PyLong_AsUnsignedLongLong(obj);
    if (PyErr_Occurred() || value > 0xFFFFFFFFULL) {
        PyErr_Clear();
        PyErr_SetString(PyExc_ValueError, "unsigned 32-bit integer out of range");
        return 0;
    }
    *out = (uint32_t)value;
    return 1;
}

static int sem_i16(PyObject *obj, int16_t *out) {
    int64_t v;
    if (!sem_int_read(obj, &v)) {
        return 0;
    }
    if (v < INT16_MIN || v > INT16_MAX) {
        PyErr_SetString(PyExc_ValueError, "i16 value out of range");
        return 0;
    }
    *out = (int16_t)v;
    return 1;
}

static int sem_i32(PyObject *obj, int32_t *out) {
    int64_t v;
    if (!sem_int_read(obj, &v)) {
        return 0;
    }
    if (v < INT32_MIN || v > INT32_MAX) {
        PyErr_SetString(PyExc_ValueError, "i32 value out of range");
        return 0;
    }
    *out = (int32_t)v;
    return 1;
}

static int sem_u64(PyObject *obj, uint64_t *out) {
    if (obj == NULL || !PyLong_Check(obj)) {
        PyErr_SetString(PyExc_ValueError, "expected an integer");
        return 0;
    }
    PyObject *zero = PyLong_FromLong(0);
    if (zero == NULL) {
        return 0;
    }
    int negative = PyObject_RichCompareBool(obj, zero, Py_LT);
    Py_DECREF(zero);
    if (negative < 0) {
        return 0;
    }
    if (negative) {
        PyErr_SetString(PyExc_ValueError, "u64 value out of range (negative)");
        return 0;
    }
    unsigned long long v = PyLong_AsUnsignedLongLong(obj);
    if (v == (unsigned long long)-1 && PyErr_Occurred()) {
        PyErr_Clear();
        PyErr_SetString(PyExc_ValueError, "u64 value out of range");
        return 0;
    }
    *out = (uint64_t)v;
    return 1;
}

static int sem_enum(PyObject *obj, int lo, int hi, uint8_t *out) {
    int64_t v;
    if (!sem_int_read(obj, &v)) {
        return 0;
    }
    if (v < lo || v > hi) {
        PyErr_SetString(PyExc_ValueError, "enum code out of allowed domain");
        return 0;
    }
    *out = (uint8_t)v;
    return 1;
}

static int sem_opt_u16(PyObject *dict, const char *key, uint8_t *has,
                       uint16_t *out) {
    PyObject *v = PyDict_GetItemString(dict, key);
    if (v == NULL) {
        PyErr_SetString(PyExc_ValueError, "missing optional field");
        return 0;
    }
    if (v == Py_None) {
        *has = 0;
        *out = 0;
        return 1;
    }
    if (!sem_u16(v, out)) {
        return 0;
    }
    *has = 1;
    return 1;
}

static int sem_opt_i16(PyObject *dict, const char *key, uint8_t *has,
                       int16_t *out) {
    PyObject *v = PyDict_GetItemString(dict, key);
    if (v == NULL) {
        PyErr_SetString(PyExc_ValueError, "missing optional field");
        return 0;
    }
    if (v == Py_None) {
        *has = 0;
        *out = 0;
        return 1;
    }
    if (!sem_i16(v, out)) {
        return 0;
    }
    *has = 1;
    return 1;
}

static int sem_opt_i32(PyObject *dict, const char *key, uint8_t *has,
                       int32_t *out) {
    PyObject *v = PyDict_GetItemString(dict, key);
    if (v == NULL) {
        PyErr_SetString(PyExc_ValueError, "missing optional field");
        return 0;
    }
    if (v == Py_None) {
        *has = 0;
        *out = 0;
        return 1;
    }
    if (!sem_i32(v, out)) {
        return 0;
    }
    *has = 1;
    return 1;
}

static int sem_opt_enum(PyObject *dict, const char *key, int lo, int hi,
                        uint8_t *has, uint8_t *out) {
    PyObject *v = PyDict_GetItemString(dict, key);
    if (v == NULL) {
        PyErr_SetString(PyExc_ValueError, "missing optional field");
        return 0;
    }
    if (v == Py_None) {
        *has = 0;
        *out = 0;
        return 1;
    }
    if (!sem_enum(v, lo, hi, out)) {
        return 0;
    }
    *has = 1;
    return 1;
}

static int sem_list_len(PyObject *list, int64_t max, uint64_t *out) {
    Py_ssize_t n = PyList_Size(list);
    if (n < 0) {
        return 0;
    }
    if ((uint64_t)n > (uint64_t)max) {
        PyErr_SetString(PyExc_ValueError, "list count exceeds capacity");
        return 0;
    }
    *out = (uint64_t)n;
    return 1;
}

static int sem_parse_square_ref(PyObject *d, GCSemSquareRef *out,
                                const GCSemanticRules *rules) {
    memset(out, 0, sizeof(*out));
    uint8_t kind, own;
    if (!sem_enum(PyDict_GetItemString(d, "kind"), 0, 6, &kind)) {
        return 0;
    }
    if (!sem_u8(PyDict_GetItemString(d, "owner_relative"), &own)) {
        return 0;
    }
    if (own > 1) {
        PyErr_SetString(PyExc_ValueError, "owner_relative must be 0/1");
        return 0;
    }
    out->kind = kind;
    out->owner_relative = own;

    uint16_t square;
    if (!sem_opt_u16(d, "square", &out->has_square, &square)) {
        return 0;
    }
    if (out->has_square) {
        uint32_t board_squares = (uint32_t)rules->board_size * rules->board_size;
        if (square >= board_squares) {
            PyErr_SetString(PyExc_ValueError,
                            "fixed square index out of board range");
            return 0;
        }
        out->square = square;
    }

    PyObject *off = PyDict_GetItemString(d, "offset");
    if (off == NULL) {
        PyErr_SetString(PyExc_ValueError, "missing offset field");
        return 0;
    }
    if (off != Py_None) {
        if (!PyList_Check(off) || PyList_Size(off) != 2) {
            PyErr_SetString(PyExc_ValueError, "offset must be a pair");
            return 0;
        }
        int16_t df, dr;
        if (!sem_i16(PyList_GetItem(off, 0), &df) ||
            !sem_i16(PyList_GetItem(off, 1), &dr)) {
            return 0;
        }
        out->has_offset = 1;
        out->offset_df = df;
        out->offset_dr = dr;
    }

    uint16_t step, slot;
    if (!sem_opt_u16(d, "step", &out->has_step, &step)) {
        return 0;
    }
    if (out->has_step) {
        out->step = step;
    }
    if (!sem_opt_u16(d, "slot_id", &out->has_slot, &slot)) {
        return 0;
    }
    if (out->has_slot) {
        /* slot_id must reference an existing canonical aux slot */
        uint8_t found = 0;
        for (uint8_t a = 0; a < rules->aux_slot_count; a++) {
            if (rules->aux_slots[a].slot_id == slot) {
                found = 1;
                break;
            }
        }
        if (!found) {
            PyErr_SetString(PyExc_ValueError,
                            "square_ref slot_id references unknown aux slot");
            return 0;
        }
        out->slot_id = slot;
    }
    /* structural operand consistency per square_ref kind (R2) */
    switch (out->kind) {
        case 0:  /* source */
        case 1:  /* target */
            if (out->has_square || out->has_offset || out->has_step ||
                out->has_slot) {
                PyErr_SetString(PyExc_ValueError,
                                "source/target square_ref must not carry operands");
                return 0;
            }
            break;
        case 2:  /* fixed */
            if (!out->has_square || out->has_offset || out->has_step ||
                out->has_slot) {
                PyErr_SetString(PyExc_ValueError,
                                "fixed square_ref requires only a square");
                return 0;
            }
            break;
        case 3:  /* offset_from_source */
        case 4:  /* offset_from_target */
            if (out->has_square || !out->has_offset || out->has_step ||
                out->has_slot) {
                PyErr_SetString(PyExc_ValueError,
                                "offset square_ref requires only an offset");
                return 0;
            }
            break;
        case 5:  /* path_step */
            if (out->has_square || out->has_offset || !out->has_step ||
                out->has_slot) {
                PyErr_SetString(PyExc_ValueError,
                                "path_step square_ref requires only a step");
                return 0;
            }
            break;
        case 6:  /* aux_slot_square */
            if (out->has_square || out->has_offset || out->has_step ||
                !out->has_slot) {
                PyErr_SetString(PyExc_ValueError,
                                "aux_slot_square square_ref requires only a slot_id");
                return 0;
            }
            break;
        default:
            PyErr_SetString(PyExc_ValueError,
                            "invalid square_ref kind");
            return 0;
    }
    return 1;
}

static int sem_parse_type_ref(PyObject *d, GCSemTypeRef *out,
                              const GCSemanticRules *rules) {
    memset(out, 0, sizeof(*out));
    uint8_t kind;
    if (!sem_enum(PyDict_GetItemString(d, "kind"), 0, 3, &kind)) {
        return 0;
    }
    out->kind = kind;
    PyObject *ti_obj = PyDict_GetItemString(d, "type_index");
    if (ti_obj == NULL) {
        PyErr_SetString(PyExc_ValueError, "missing type_index");
        return 0;
    }
    if (ti_obj == Py_None) {
        if (kind == 2) {  /* explicit requires an index */
            PyErr_SetString(PyExc_ValueError,
                            "explicit type_ref requires type_index");
            return 0;
        }
        out->has_type = 0;
        return 1;
    }
    uint16_t ti;
    if (!sem_u16(ti_obj, &ti)) {
        return 0;
    }
    if (kind != 2) {  /* non-explicit must not carry an index */
        PyErr_SetString(PyExc_ValueError,
                        "non-explicit type_ref must not carry type_index");
        return 0;
    }
    if (ti >= rules->type_count) {
        PyErr_SetString(PyExc_ValueError, "type_ref index out of range");
        return 0;
    }
    out->has_type = 1;
    out->type_index = ti;
    return 1;
}

static int sem_parse_square_refs(PyObject *list, GCSemSquareRef **out,
                                 uint16_t *count, int max,
                                 const GCSemanticRules *rules) {
    Py_ssize_t n = PyList_Size(list);
    if (n > max) {
        PyErr_SetString(PyExc_ValueError, "too many square refs");
        return 0;
    }
    if (n == 0) {
        *out = NULL;
        *count = 0;
        return 1;
    }
    GCSemSquareRef *refs = (GCSemSquareRef *)calloc((size_t)n, sizeof(GCSemSquareRef));
    if (refs == NULL) {
        PyErr_NoMemory();
        return 0;
    }
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *item = PyList_GetItem(list, i);
        if (!PyDict_Check(item) ||
            !sem_parse_square_ref(item, &refs[i], rules)) {
            free(refs);
            return 0;
        }
    }
    *out = refs;
    *count = (uint16_t)n;
    return 1;
}

static int sem_parse_spatial(PyObject *d, GCSemSpatial *out,
                             const GCSemanticRules *rules) {
    memset(out, 0, sizeof(*out));
    uint8_t kind;
    if (!sem_enum(PyDict_GetItemString(d, "kind"), 0, 5, &kind)) {
        return 0;
    }
    out->kind = kind;
    PyObject *refs = NULL;
    if (!sem_get_list(d, "refs", &refs)) {
        return 0;
    }
    if (!sem_parse_square_refs(refs, &out->refs, &out->refs_count, 2, rules)) {
        return 0;
    }
    switch (out->kind) {
        case 0:  /* same_file */
        case 1:  /* same_rank */
        case 2:  /* exact */
        case 3:  /* adjacent */
            if (out->refs_count != 1) {
                PyErr_SetString(PyExc_ValueError,
                                "spatial selector requires exactly 1 ref");
                return 0;
            }
            break;
        case 4:  /* path_between */
            if (out->refs_count != 2) {
                PyErr_SetString(PyExc_ValueError,
                                "path_between requires exactly 2 refs");
                return 0;
            }
            break;
        case 5:  /* zone */
            if (out->refs_count != 0) {
                PyErr_SetString(PyExc_ValueError,
                                "zone spatial selector must not carry refs");
                return 0;
            }
            break;
        default:
            PyErr_SetString(PyExc_ValueError, "invalid spatial kind");
            return 0;
    }
    uint16_t zid;
    if (!sem_opt_u16(d, "zone_index", &out->has_zone, &zid)) {
        return 0;
    }
    if (out->has_zone) {
        if (kind != 5) {  /* zone spatial requires kind=zone */
            PyErr_SetString(PyExc_ValueError,
                            "zone_index present on non-zone spatial");
            return 0;
        }
        if (zid >= rules->zone_count) {
            PyErr_SetString(PyExc_ValueError, "zone index out of range");
            return 0;
        }
        out->zone_index = zid;
    } else if (kind == 5) {
        PyErr_SetString(PyExc_ValueError,
                        "zone spatial requires zone_index");
        return 0;
    }
    return 1;
}

static int sem_parse_state_guard(PyObject *d, GCSemStateGuard *out,
                                 const GCSemanticRules *rules) {
    memset(out, 0, sizeof(*out));
    if (!sem_enum(PyDict_GetItemString(d, "aggregation"), 0, 1,
                  &out->aggregation) ||
        !sem_enum(PyDict_GetItemString(d, "owner"), 0, 2, &out->owner) ||
        !sem_enum(PyDict_GetItemString(d, "compare_field"), 0, 1,
                  &out->compare_field) ||
        !sem_enum(PyDict_GetItemString(d, "promoted"), 0, 2, &out->promoted) ||
        !sem_enum(PyDict_GetItemString(d, "location"), 0, 1, &out->location) ||
        !sem_enum(PyDict_GetItemString(d, "comparison"), 0, 5,
                  &out->comparison)) {
        return 0;
    }
    if (out->location != 0) {
        /* hand predicates are compile-time fail-closed; board=0 only */
        PyErr_SetString(PyExc_ValueError,
                        "state guard location must be board(0)");
        return 0;
    }
    PyObject *subject = PyDict_GetItemString(d, "subject_ref");
    if (subject != NULL && subject != Py_None) {
        if (!PyDict_Check(subject) ||
            !sem_parse_square_ref(subject, &out->subject_ref, rules)) {
            return 0;
        }
        out->has_subject_ref = 1;
    }
    PyObject *tr = PyDict_GetItemString(d, "type_ref");
    if (tr == NULL || !PyDict_Check(tr) ||
        !sem_parse_type_ref(tr, &out->type_ref, rules)) {
        return 0;
    }
    PyObject *sp = PyDict_GetItemString(d, "spatial");
    if (sp == NULL || !PyDict_Check(sp) ||
        !sem_parse_spatial(sp, &out->spatial, rules)) {
        return 0;
    }
    int32_t value;
    if (!sem_i32(PyDict_GetItemString(d, "value"), &value)) {
        return 0;
    }
    out->value = value;
    return 1;
}

static int sem_parse_slot_guard(PyObject *d, GCSemSlotGuard *out,
                                const GCSemanticRules *rules) {
    memset(out, 0, sizeof(*out));
    uint16_t sid;
    if (!sem_u16(PyDict_GetItemString(d, "slot_id"), &sid)) {
        return 0;
    }
    uint8_t found = 0;
    uint8_t slot_value_kind = 0xFF;
    for (uint8_t a = 0; a < rules->aux_slot_count; a++) {
        if (rules->aux_slots[a].slot_id == sid) {
            found = 1;
            slot_value_kind = rules->aux_slots[a].value_kind;
            break;
        }
    }
    if (!found) {
        PyErr_SetString(PyExc_ValueError,
                        "slot guard references unknown aux slot");
        return 0;
    }
    out->slot_id = sid;
    if (!sem_enum(PyDict_GetItemString(d, "comparison"), 0, 5,
                  &out->comparison)) {
        return 0;
    }
    int32_t value;
    if (!sem_opt_i32(d, "value", &out->has_value, &value)) {
        return 0;
    }
    if (out->has_value) {
        out->value = value;
    }
    PyObject *sr = PyDict_GetItemString(d, "square_ref");
    if (sr == NULL) {
        PyErr_SetString(PyExc_ValueError, "missing square_ref");
        return 0;
    }
    if (sr != Py_None) {
        if (!PyDict_Check(sr) ||
            !sem_parse_square_ref(sr, &out->square_ref, rules)) {
            return 0;
        }
        out->has_square_ref = 1;
    }
    if (slot_value_kind == 0) {  /* bool slot */
        if (!out->has_value || (out->value != 0 && out->value != 1)) {
            PyErr_SetString(PyExc_ValueError,
                            "bool slot guard requires value 0/1");
            return 0;
        }
        if (out->has_square_ref) {
            PyErr_SetString(PyExc_ValueError,
                            "bool slot guard must not carry square_ref");
            return 0;
        }
    } else {  /* square_or_none slot */
        if (!out->has_square_ref &&
            out->comparison != 0 && out->comparison != 1) {
            PyErr_SetString(PyExc_ValueError,
                            "square slot guard with None requires eq/ne");
            return 0;
        }
    }
    return 1;
}

static int sem_parse_effect(PyObject *d, GCSemEffect *out,
                            const GCSemanticRules *rules) {
    memset(out, 0, sizeof(*out));
    uint8_t kind;
    if (!sem_enum(PyDict_GetItemString(d, "kind"), 0, 9, &kind)) {
        return 0;
    }
    out->kind = kind;
    if (!sem_enum(PyDict_GetItemString(d, "piece_owner"), 0, 2,
                  &out->piece_owner)) {
        return 0;
    }
    uint16_t count;
    if (!sem_u16(PyDict_GetItemString(d, "count"), &count)) {
        return 0;
    }
    if (count > 0xFF) {
        PyErr_SetString(PyExc_ValueError, "effect count exceeds u8");
        return 0;
    }
    out->count = (uint8_t)count;
    uint16_t slot;
    if (!sem_opt_u16(d, "slot_id", &out->has_slot, &slot)) {
        return 0;
    }
    if (out->has_slot) {
        uint8_t found = 0;
        for (uint8_t a = 0; a < rules->aux_slot_count; a++) {
            if (rules->aux_slots[a].slot_id == slot) {
                found = 1;
                break;
            }
        }
        if (!found) {
            PyErr_SetString(PyExc_ValueError,
                            "effect slot_id references unknown aux slot");
            return 0;
        }
        out->slot_id = slot;
    }
    uint8_t disp;
    if (!sem_opt_enum(d, "disposition", 0, 1, &out->has_disposition, &disp)) {
        return 0;
    }
    if (out->has_disposition) {
        out->disposition = disp;
    }
    int32_t value;
    if (!sem_opt_i32(d, "value", &out->has_value, &value)) {
        return 0;
    }
    if (out->has_value) {
        out->value = value;
    }

#define SEM_OPT_REF(key, has_field, ref_field) \
    do { \
        PyObject *o = PyDict_GetItemString(d, key); \
        if (o == NULL) { \
            PyErr_SetString(PyExc_ValueError, "missing " key); \
            return 0; \
        } \
        if (o != Py_None) { \
            if (!PyDict_Check(o) || \
                !sem_parse_square_ref(o, &out->ref_field, rules)) { \
                return 0; \
            } \
            out->has_field = 1; \
        } \
    } while (0)
    SEM_OPT_REF("from_ref", has_from, from_ref);
    SEM_OPT_REF("to_ref", has_to, to_ref);
    SEM_OPT_REF("square_ref", has_square, square_ref);
#undef SEM_OPT_REF

#define SEM_OPT_TREF(key, has_field, ref_field) \
    do { \
        PyObject *o = PyDict_GetItemString(d, key); \
        if (o == NULL) { \
            PyErr_SetString(PyExc_ValueError, "missing " key); \
            return 0; \
        } \
        if (o != Py_None) { \
            if (!PyDict_Check(o) || \
                !sem_parse_type_ref(o, &out->ref_field, rules)) { \
                return 0; \
            } \
            out->has_field = 1; \
        } \
    } while (0)
    SEM_OPT_TREF("piece_type_ref", has_piece_type_ref, piece_type_ref);
    SEM_OPT_TREF("type_ref", has_type_ref, type_ref);
#undef SEM_OPT_TREF

    /* structural well-formedness mirroring the frozen IR effect contract */
    if (out->count != 1) {
        PyErr_SetString(PyExc_ValueError,
                        "effect count must be 1");
        return 0;
    }
    uint8_t slot_kind = 0xFF;
    if (out->has_slot) {
        for (uint8_t a = 0; a < rules->aux_slot_count; a++) {
            if (rules->aux_slots[a].slot_id == out->slot_id) {
                slot_kind = rules->aux_slots[a].value_kind;
                break;
            }
        }
    }
    switch (out->kind) {
        case 0:  /* move */
        case 9:  /* shift */
            if (!out->has_from || !out->has_to ||
                out->has_disposition || out->has_type_ref) {
                PyErr_SetString(PyExc_ValueError,
                                "move/shift requires from+to and no "
                                "disposition/type_ref");
                return 0;
            }
            break;
        case 1:  /* remove */
            if (!out->has_square || !out->has_disposition ||
                out->has_from || out->has_to) {
                PyErr_SetString(PyExc_ValueError,
                                "remove requires square_ref+disposition");
                return 0;
            }
            break;
        case 2:  /* remove_from_hand */
            if (!out->has_piece_type_ref || out->has_from || out->has_to ||
                out->has_square || out->has_disposition) {
                PyErr_SetString(PyExc_ValueError,
                                "remove_from_hand requires piece_type_ref only");
                return 0;
            }
            break;
        case 3:  /* place */
            if (!out->has_to || !out->has_piece_type_ref ||
                out->has_from || out->has_square || out->has_disposition) {
                PyErr_SetString(PyExc_ValueError,
                                "place requires to_ref+piece_type_ref");
                return 0;
            }
            break;
        case 4:  /* set_current_type */
            if (!out->has_square || !out->has_type_ref ||
                out->has_from || out->has_to || out->has_disposition) {
                PyErr_SetString(PyExc_ValueError,
                                "set_current_type requires square_ref+type_ref");
                return 0;
            }
            break;
        case 5:  /* set_bool */
            if (!out->has_slot || !out->has_value || slot_kind != 0 ||
                (out->value != 0 && out->value != 1) ||
                out->has_square || out->has_type_ref ||
                out->has_disposition || out->has_from || out->has_to) {
                PyErr_SetString(PyExc_ValueError,
                                "set_bool requires a bool slot and value 0/1");
                return 0;
            }
            break;
        case 6:  /* clear_right */
            if (!out->has_slot || slot_kind != 0 ||
                out->has_square || out->has_type_ref || out->has_disposition) {
                PyErr_SetString(PyExc_ValueError,
                                "clear_right requires a bool slot");
                return 0;
            }
            break;
        case 7:  /* set_token */
            if (!out->has_slot || !out->has_square || slot_kind != 1 ||
                out->has_type_ref || out->has_disposition) {
                PyErr_SetString(PyExc_ValueError,
                                "set_token requires a square_or_none slot");
                return 0;
            }
            break;
        case 8:  /* clear_token */
            if (!out->has_slot || slot_kind != 1 ||
                out->has_square || out->has_type_ref || out->has_disposition) {
                PyErr_SetString(PyExc_ValueError,
                                "clear_token requires a square_or_none slot");
                return 0;
            }
            break;
        default:
            PyErr_SetString(PyExc_ValueError, "invalid effect kind");
            return 0;
    }
    return 1;
}

static int sem_parse_invariant(PyObject *d, GCSemInvariant *out,
                               const GCSemanticRules *rules) {
    memset(out, 0, sizeof(*out));
    uint8_t kind;
    if (!sem_enum(PyDict_GetItemString(d, "kind"), 0, 1, &kind)) {
        return 0;
    }
    out->kind = kind;
    PyObject *refs = NULL;
    if (!sem_get_list(d, "square_refs", &refs)) {
        return 0;
    }
    if (!sem_parse_square_refs(refs, &out->refs, &out->refs_count,
                               GC_SEM_MAX_INVARIANT_REFS, rules)) {
        return 0;
    }
    if (out->kind == 1) {  /* squares_not_attacked */
        if (out->refs_count < 1) {
            PyErr_SetString(PyExc_ValueError,
                            "squares_not_attacked requires at least 1 ref");
            return 0;
        }
    } else if (out->refs_count != 0) {
        PyErr_SetString(PyExc_ValueError,
                        "own_anchor_safe must not carry square refs");
        return 0;
    }
    return 1;
}

static int sem_parse_postcondition(PyObject *d, GCSemPostcondition *out) {
    memset(out, 0, sizeof(*out));
    uint8_t kind;
    if (!sem_enum(PyDict_GetItemString(d, "kind"), 0, 2, &kind)) {
        return 0;
    }
    uint8_t stratum;
    if (!sem_enum(PyDict_GetItemString(d, "max_stratum"), 0, 5, &stratum)) {
        return 0;
    }
    if (stratum > 3) {  /* no_legal_reply probe must be <= S3 */
        PyErr_SetString(PyExc_ValueError,
                        "postcondition probe stratum exceeds S3");
        return 0;
    }
    out->kind = kind;
    out->max_stratum = stratum;
    return 1;
}

static int sem_parse_path_predicate(PyObject *d, GCSemPathPredicate *out) {
    memset(out, 0, sizeof(*out));
    uint8_t kind;
    if (!sem_enum(PyDict_GetItemString(d, "kind"), 0, 4, &kind)) {
        return 0;
    }
    if (!sem_enum(PyDict_GetItemString(d, "owner_filter"), 0, 2,
                  &out->owner_filter)) {
        return 0;
    }
    out->kind = kind;
    int32_t v32;
    if (!sem_opt_i32(d, "count", &out->has_count, &v32)) {
        return 0;
    }
    if (out->has_count) {
        out->count = v32;
    }
    if (!sem_opt_i32(d, "lo", &out->has_lo, &v32)) {
        return 0;
    }
    if (out->has_lo) {
        out->lo = v32;
    }
    if (!sem_opt_i32(d, "hi", &out->has_hi, &v32)) {
        return 0;
    }
    if (out->has_hi) {
        out->hi = v32;
    }
    return 1;
}

/* ------------------------------------------------------------------ compile */

static int sem_alloc_uint16_list(PyObject *list, uint16_t **out,
                                 uint16_t *count, int max) {
    uint64_t n64;
    if (!sem_list_len(list, max, &n64)) {
        PyErr_SetString(PyExc_ValueError, "list exceeds capacity");
        return 0;
    }
    uint16_t n = (uint16_t)n64;
    if (n == 0) {
        *out = NULL;
        *count = 0;
        return 1;
    }
    uint16_t *arr = (uint16_t *)calloc((size_t)n, sizeof(uint16_t));
    if (arr == NULL) {
        PyErr_NoMemory();
        return 0;
    }
    for (Py_ssize_t i = 0; i < n; i++) {
        uint16_t v;
        if (!sem_u16(PyList_GetItem(list, i), &v)) {
            free(arr);
            return 0;
        }
        arr[i] = v;
    }
    *out = arr;
    *count = (uint16_t)n;
    return 1;
}

static int sem_alloc_uint32_list(PyObject *list, uint32_t **out,
                                 uint16_t *count) {
    uint64_t n64;
    if (!sem_list_len(list, 0xFFFF, &n64)) {
        PyErr_SetString(PyExc_ValueError, "list exceeds capacity");
        return 0;
    }
    uint16_t n = (uint16_t)n64;
    if (n == 0) {
        *out = NULL;
        *count = 0;
        return 1;
    }
    uint32_t *arr = (uint32_t *)calloc((size_t)n, sizeof(uint32_t));
    if (arr == NULL) {
        PyErr_NoMemory();
        return 0;
    }
    for (Py_ssize_t i = 0; i < n; i++) {
        uint64_t v;
        if (!sem_u64(PyList_GetItem(list, i), &v) || v > 0xFFFFFFFFULL) {
            free(arr);
            return 0;
        }
        arr[i] = (uint32_t)v;
    }
    *out = arr;
    *count = (uint16_t)n;
    return 1;
}

GCSemanticRules *gc_semantic_rules_compile(PyObject *payload) {
    if (!PyDict_Check(payload)) {
        PyErr_SetString(PyExc_TypeError,
                        "compile_semantic_rules expects a dict payload");
        return NULL;
    }
    GCSemanticRules *rules = (GCSemanticRules *)calloc(1, sizeof(GCSemanticRules));
    if (rules == NULL) {
        PyErr_NoMemory();
        return NULL;
    }

    /* v1 remains compile-only compatible; v2 adds the type IDs required by
     * the independent semantic position-key runtime. */
    uint8_t payload_version;
    if (!sem_u8(PyDict_GetItemString(payload, "semantic_payload_version"),
                &payload_version)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    if (payload_version != 1 && payload_version != 2 && payload_version != 3) {
        PyErr_SetString(PyExc_ValueError,
                        "unsupported semantic_payload_version");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->semantic_payload_version = payload_version;

    uint16_t board_size;
    if (!sem_u16(PyDict_GetItemString(payload, "board_size"), &board_size)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    if (board_size < 1 || board_size > 16 ||
        (uint32_t)board_size * board_size > GC_MAX_SQUARES) {
        PyErr_SetString(PyExc_ValueError, "semantic board size out of range");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->board_size = (uint8_t)board_size;

    uint32_t repetition_limit;
    if (!sem_u32(PyDict_GetItemString(payload, "repetition_limit"),
                 &repetition_limit)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    if (repetition_limit < 1) {
        PyErr_SetString(PyExc_ValueError,
                        "semantic repetition_limit must be positive");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->repetition_limit = repetition_limit;

    uint8_t repetition_policy = 0;
    PyObject *policy_obj = PyDict_GetItemString(payload, "repetition_policy");
    if (policy_obj != NULL && !sem_u8(policy_obj, &repetition_policy)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    if (repetition_policy > 1) {
        PyErr_SetString(PyExc_ValueError, "semantic repetition_policy out of range");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->repetition_policy = repetition_policy;

    uint16_t automatic_ply = 0;
    PyObject *automatic_obj = PyDict_GetItemString(payload, "automatic_adjudication_ply");
    if (automatic_obj != NULL && automatic_obj != Py_None &&
        !sem_u16(automatic_obj, &automatic_ply)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->automatic_adjudication_ply = automatic_ply;

    uint16_t max_ply;
    if (!sem_u16(PyDict_GetItemString(payload, "max_ply"), &max_ply)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    if (max_ply < 1 || max_ply > GC_SEM_MAX_PLY) {
        PyErr_SetString(PyExc_ValueError, "semantic max_ply out of range");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->max_ply = max_ply;

    PyObject *fp = PyDict_GetItemString(payload, "fingerprint");
    if (fp == NULL || !PyUnicode_Check(fp)) {
        PyErr_SetString(PyExc_ValueError, "missing fingerprint");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    const char *fp_c = PyUnicode_AsUTF8(fp);
    if (fp_c == NULL || strlen(fp_c) >= 65) {
        PyErr_SetString(PyExc_ValueError, "fingerprint too long");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    strcpy(rules->fingerprint, fp_c);

    PyObject *list_obj = NULL;
    if (!sem_get_list(payload, "types", &list_obj)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    uint64_t type_count64;
    if (!sem_list_len(list_obj, GC_MAX_TYPES, &type_count64)) {
        PyErr_SetString(PyExc_ValueError, "too many semantic types");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->type_count = (uint16_t)type_count64;
    if (rules->type_count < 1) {
        PyErr_SetString(PyExc_ValueError, "semantic type list is empty");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    if (payload_version >= 2) {
        PyObject *type_ids = NULL;
        if (!sem_get_list(payload, "type_ids", &type_ids) ||
            PyList_Size(type_ids) != rules->type_count) {
            PyErr_SetString(PyExc_ValueError,
                            "semantic v2 type_ids must match types");
            gc_semantic_rules_free(rules);
            return NULL;
        }
        rules->type_ids = (char **)calloc(rules->type_count, sizeof(char *));
        if (rules->type_ids == NULL) {
            PyErr_NoMemory();
            gc_semantic_rules_free(rules);
            return NULL;
        }
        for (uint16_t t = 0; t < rules->type_count; t++) {
            PyObject *item = PyList_GetItem(type_ids, t);
            if (!PyUnicode_Check(item)) {
                PyErr_SetString(PyExc_ValueError,
                                "semantic v2 type_id must be a string");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            Py_ssize_t text_len = 0;
            const char *text = PyUnicode_AsUTF8AndSize(item, &text_len);
            if (text == NULL || text_len <= 0 ||
                memchr(text, '\0', (size_t)text_len) != NULL) {
                PyErr_SetString(PyExc_ValueError,
                                "semantic v2 type_id must be non-empty UTF-8 without NUL");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            for (uint16_t prior = 0; prior < t; prior++) {
                if (strcmp(rules->type_ids[prior], text) == 0) {
                    PyErr_SetString(PyExc_ValueError,
                                    "semantic v2 type_ids must be unique");
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
            size_t size = (size_t)text_len + 1;
            rules->type_ids[t] = (char *)malloc(size);
            if (rules->type_ids[t] == NULL) {
                PyErr_NoMemory();
                gc_semantic_rules_free(rules);
                return NULL;
            }
            memcpy(rules->type_ids[t], text, (size_t)text_len);
            rules->type_ids[t][text_len] = '\0';
        }
    }
    for (uint16_t t = 0; t < rules->type_count; t++) {
        PyObject *td = PyList_GetItem(list_obj, t);
        if (!PyDict_Check(td)) {
            PyErr_SetString(PyExc_ValueError, "type entry must be a dict");
            gc_semantic_rules_free(rules);
            return NULL;
        }
        uint8_t anchor, promotable;
        if (!sem_u8(PyDict_GetItemString(td, "is_anchor"), &anchor) ||
            !sem_u8(PyDict_GetItemString(td, "is_promotable"), &promotable)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        if (anchor > 1 || promotable > 1) {
            PyErr_SetString(PyExc_ValueError,
                            "type is_anchor/is_promotable must be 0/1");
            gc_semantic_rules_free(rules);
            return NULL;
        }
        rules->types[t].is_anchor = anchor;
        rules->types[t].is_promotable = promotable;
        PyObject *targets = NULL;
        if (!sem_get_list(td, "promo_targets", &targets)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        uint64_t tc64;
        if (!sem_list_len(targets, GC_MAX_PROMO_TARGETS, &tc64)) {
            PyErr_SetString(PyExc_ValueError, "too many promotion targets");
            gc_semantic_rules_free(rules);
            return NULL;
        }
        uint8_t tc = (uint8_t)tc64;
        rules->types[t].promo_target_count = tc;
        for (uint8_t i = 0; i < tc; i++) {
            uint16_t ti;
            if (!sem_u16(PyList_GetItem(targets, i), &ti)) {
                gc_semantic_rules_free(rules);
                return NULL;
            }
            if (ti >= rules->type_count) {
                PyErr_SetString(PyExc_ValueError,
                                "promotion target type index out of range");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            rules->types[t].promo_targets[i] = (GCTypeIndex)ti;
        }
    }

#define SEM_OWNER_LISTS_START(strkey) \
    PyObject *top_##strkey = NULL; \
    if (!sem_get_list(payload, #strkey, &top_##strkey)) { \
        gc_semantic_rules_free(rules); \
        return NULL; \
    } \
    if (PyList_Size(top_##strkey) != rules->type_count) { \
        PyErr_SetString(PyExc_ValueError, "per-type list count mismatch"); \
        gc_semantic_rules_free(rules); \
        return NULL; \
    } \
    for (uint16_t t = 0; t < rules->type_count; t++) { \
        PyObject *owners = PyList_GetItem(top_##strkey, t); \
        if (!PyList_Check(owners) || PyList_Size(owners) != 2) { \
            PyErr_SetString(PyExc_ValueError, "expected two owner lists"); \
            gc_semantic_rules_free(rules); \
            return NULL; \
        } \
        for (int o = 0; o < 2; o++) {

#define SEM_OWNER_LISTS_END() \
        } \
    }

    SEM_OWNER_LISTS_START(promo_allowed)
    if (!sem_alloc_uint32_list(PyList_GetItem(owners, o),
                               &rules->promo_allowed[t][o].pairs,
                               &rules->promo_allowed[t][o].count)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    SEM_OWNER_LISTS_END()

    SEM_OWNER_LISTS_START(promo_forced)
    if (!sem_alloc_uint16_list(PyList_GetItem(owners, o),
                               &rules->promo_forced[t][o].squares,
                               &rules->promo_forced[t][o].count, 0xFFFF)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    SEM_OWNER_LISTS_END()

    SEM_OWNER_LISTS_START(drop_mask)
    if (!sem_alloc_uint16_list(PyList_GetItem(owners, o),
                               &rules->drop_mask[t][o].squares,
                               &rules->drop_mask[t][o].count, 0xFFFF)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    SEM_OWNER_LISTS_END()

#undef SEM_OWNER_LISTS_START
#undef SEM_OWNER_LISTS_END

    /* cross-reference validation for promotion/drop data */
    uint16_t squares =
        (uint16_t)(rules->board_size * rules->board_size);
    for (uint16_t t = 0; t < rules->type_count; t++) {
        for (int o = 0; o < 2; o++) {
            for (uint16_t i = 0; i < rules->promo_forced[t][o].count; i++) {
                if (rules->promo_forced[t][o].squares[i] >= squares) {
                    PyErr_SetString(PyExc_ValueError,
                                    "promo_forced square out of board range");
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
            for (uint16_t i = 0; i < rules->drop_mask[t][o].count; i++) {
                if (rules->drop_mask[t][o].squares[i] >= squares) {
                    PyErr_SetString(PyExc_ValueError,
                                    "drop_mask square out of board range");
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
            for (uint16_t i = 0; i < rules->promo_allowed[t][o].count; i++) {
                uint32_t pair = rules->promo_allowed[t][o].pairs[i];
                uint16_t from_sq = (uint16_t)(pair >> 16);
                uint16_t to_sq = (uint16_t)(pair & 0xFFFF);
                if (from_sq >= squares || to_sq >= squares) {
                    PyErr_SetString(PyExc_ValueError,
                                    "promo_allowed pair square out of board range");
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
        }
    }

    if (!sem_get_list(payload, "alive_promo", &list_obj)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    if (PyList_Size(list_obj) != rules->type_count) {
        PyErr_SetString(PyExc_ValueError, "alive_promo count mismatch");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    for (uint16_t t = 0; t < rules->type_count; t++) {
        PyObject *owners = PyList_GetItem(list_obj, t);
        if (!PyList_Check(owners) || PyList_Size(owners) != 2) {
            PyErr_SetString(PyExc_ValueError, "expected two owner lists");
            gc_semantic_rules_free(rules);
            return NULL;
        }
        for (int o = 0; o < 2; o++) {
            PyObject *masks = PyList_GetItem(owners, o);
            if (!PyList_Check(masks) || PyList_Size(masks) != squares) {
                PyErr_SetString(PyExc_ValueError, "alive_promo square count mismatch");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            for (uint16_t sq = 0; sq < squares; sq++) {
                uint64_t mask;
                if (!sem_u64(PyList_GetItem(masks, sq), &mask)) {
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
                rules->alive_promo[t][o][sq] = mask;
            }
        }
    }
    /* alive_promo bits must lie within the type's promotion-target domain */
    for (uint16_t t = 0; t < rules->type_count; t++) {
        uint8_t k = rules->types[t].promo_target_count;
        uint64_t allowed = (k == 0) ? 0 : ((1ULL << k) - 1ULL);
        for (int o = 0; o < 2; o++) {
            for (uint16_t sq = 0; sq < squares; sq++) {
                if (rules->alive_promo[t][o][sq] & ~allowed) {
                    PyErr_SetString(PyExc_ValueError,
                                    "alive_promo mask has bits outside the "
                                    "promotion-target domain");
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
        }
    }

    /* geometries */
    if (!sem_get_list(payload, "geometries", &list_obj)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    uint64_t geometry_count64;
    if (!sem_list_len(list_obj, GC_SEM_MAX_GEOMETRIES, &geometry_count64)) {
        PyErr_SetString(PyExc_ValueError, "too many semantic geometries");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->geometry_count = (uint16_t)geometry_count64;
    if (rules->geometry_count > 0) {
        rules->geometries = (GCSemGeometry *)calloc(
            rules->geometry_count, sizeof(GCSemGeometry));
        if (rules->geometries == NULL) {
            PyErr_NoMemory();
            gc_semantic_rules_free(rules);
            return NULL;
        }
    }
    for (uint16_t g = 0; g < rules->geometry_count; g++) {
        PyObject *gd = PyList_GetItem(list_obj, g);
        if (!PyDict_Check(gd)) {
            PyErr_SetString(PyExc_ValueError, "geometry entry must be a dict");
            gc_semantic_rules_free(rules);
            return NULL;
        }
        uint8_t kind;
        if (!sem_enum(PyDict_GetItemString(gd, "kind"), 0, 2, &kind)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        rules->geometries[g].kind = kind;
        int16_t min_steps;
        if (!sem_opt_i16(gd, "min_steps",
                         &rules->geometries[g].has_min_steps, &min_steps)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        if (rules->geometries[g].has_min_steps) {
            rules->geometries[g].min_steps = min_steps;
        }
        PyObject *asrc = PyDict_GetItemString(gd, "atom_source");
        if (asrc == NULL) {
            PyErr_SetString(PyExc_ValueError, "missing atom_source");
            gc_semantic_rules_free(rules);
            return NULL;
        }
        if (asrc != Py_None) {
            if (!PyList_Check(asrc) || PyList_Size(asrc) != 2) {
                PyErr_SetString(PyExc_ValueError, "atom_source must be a pair");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            uint16_t ti, ai;
            if (!sem_u16(PyList_GetItem(asrc, 0), &ti) ||
                !sem_u16(PyList_GetItem(asrc, 1), &ai)) {
                gc_semantic_rules_free(rules);
                return NULL;
            }
            if (ti >= rules->type_count) {
                PyErr_SetString(PyExc_ValueError,
                                "geometry atom_source type index out of range");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            rules->geometries[g].has_atom_source = 1;
            rules->geometries[g].atom_source_type = ti;
            rules->geometries[g].atom_source_index = ai;
        }
        PyObject *paths = PyDict_GetItemString(gd, "paths");
        if (paths == NULL || !PyList_Check(paths) || PyList_Size(paths) != 2) {
            PyErr_SetString(PyExc_ValueError, "paths must be a two-owner list");
            gc_semantic_rules_free(rules);
            return NULL;
        }
        for (int o = 0; o < 2; o++) {
            PyObject *owner_entries = PyList_GetItem(paths, o);
            if (!PyList_Check(owner_entries)) {
                PyErr_SetString(PyExc_ValueError, "owner path list expected");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            uint64_t n64;
            if (!sem_list_len(owner_entries, 0xFFFF, &n64)) {
                PyErr_SetString(PyExc_ValueError, "owner path list too large");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            uint16_t n = (uint16_t)n64;
            if (n > 0) {
                rules->geometries[g].paths[o].entries =
                    (GCSemPathEntry *)calloc((size_t)n, sizeof(GCSemPathEntry));
                if (rules->geometries[g].paths[o].entries == NULL) {
                    PyErr_NoMemory();
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
                rules->geometries[g].paths[o].count = n;
            }
            for (uint16_t i = 0; i < n; i++) {
                PyObject *entry = PyList_GetItem(owner_entries, i);
                if (!PyList_Check(entry) || PyList_Size(entry) != 2) {
                    PyErr_SetString(PyExc_ValueError,
                                    "path entry must be [source, squares]");
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
                uint16_t source;
                if (!sem_u16(PyList_GetItem(entry, 0), &source)) {
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
                if (source >= squares) {
                    PyErr_SetString(PyExc_ValueError,
                                    "geometry path source out of board range");
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
                GCSemPathEntry *pe = &rules->geometries[g].paths[o].entries[i];
                pe->source = source;
                PyObject *sqs = PyList_GetItem(entry, 1);
                if (!sem_alloc_uint16_list(sqs, &pe->squares, &pe->count, 0xFFFF)) {
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
                for (uint16_t q = 0; q < pe->count; q++) {
                    if (pe->squares[q] >= squares) {
                        PyErr_SetString(PyExc_ValueError,
                                        "geometry path square out of board range");
                        gc_semantic_rules_free(rules);
                        return NULL;
                    }
                }
            }
        }
    }

    /* zones */
    if (!sem_get_list(payload, "zones", &list_obj)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    uint64_t zone_count64;
    if (!sem_list_len(list_obj, 0xFFFF, &zone_count64)) {
        PyErr_SetString(PyExc_ValueError, "too many semantic zones");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->zone_count = (uint16_t)zone_count64;
    if (rules->zone_count > 0) {
        rules->zones = (GCSemZone *)calloc(rules->zone_count, sizeof(GCSemZone));
        if (rules->zones == NULL) {
            PyErr_NoMemory();
            gc_semantic_rules_free(rules);
            return NULL;
        }
    }
    for (uint16_t z = 0; z < rules->zone_count; z++) {
        PyObject *zd = PyList_GetItem(list_obj, z);
        PyObject *squares_list = NULL;
        if (!PyDict_Check(zd) || !sem_get_list(zd, "squares", &squares_list)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        if (!sem_alloc_uint16_list(squares_list, &rules->zones[z].squares,
                                   &rules->zones[z].count, 0xFFFF)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        for (uint16_t q = 0; q < rules->zones[z].count; q++) {
            if (rules->zones[z].squares[q] >= squares) {
                PyErr_SetString(PyExc_ValueError,
                                "zone square out of board range");
                gc_semantic_rules_free(rules);
                return NULL;
            }
        }
    }

    /* aux slots */
    if (!sem_get_list(payload, "aux_slots", &list_obj)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    uint64_t aux_count64;
    if (!sem_list_len(list_obj, GC_SEM_MAX_AUX_SLOTS, &aux_count64)) {
        PyErr_SetString(PyExc_ValueError, "too many semantic aux slots");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->aux_slot_count = (uint8_t)aux_count64;
    if (rules->aux_slot_count > 0) {
        rules->aux_slots = (GCSemAuxSlot *)calloc(
            rules->aux_slot_count, sizeof(GCSemAuxSlot));
        if (rules->aux_slots == NULL) {
            PyErr_NoMemory();
            gc_semantic_rules_free(rules);
            return NULL;
        }
    }
    for (uint8_t a = 0; a < rules->aux_slot_count; a++) {
        PyObject *ad = PyList_GetItem(list_obj, a);
        uint16_t sid;
        if (!PyDict_Check(ad) ||
            !sem_u16(PyDict_GetItemString(ad, "slot_id"), &sid) ||
            !sem_enum(PyDict_GetItemString(ad, "value_kind"), 0, 1,
                      &rules->aux_slots[a].value_kind) ||
            !sem_enum(PyDict_GetItemString(ad, "scope"), 0, 1,
                      &rules->aux_slots[a].scope) ||
            !sem_enum(PyDict_GetItemString(ad, "lifetime"), 0, 1,
                      &rules->aux_slots[a].lifetime)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        rules->aux_slots[a].slot_id = sid;
        PyObject *init = PyDict_GetItemString(ad, "initial");
        if (init == NULL) {
            PyErr_SetString(PyExc_ValueError, "missing aux initial");
            gc_semantic_rules_free(rules);
            return NULL;
        }
        if (init == Py_None) {
            if (rules->aux_slots[a].value_kind != 1) {
                PyErr_SetString(PyExc_ValueError,
                                "bool aux slot must not have None initial");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            rules->aux_slots[a].initial_kind = 0;
        } else if (PyLong_Check(init)) {
            int32_t iv;
            if (!sem_i32(init, &iv)) {
                gc_semantic_rules_free(rules);
                return NULL;
            }
            if (rules->aux_slots[a].value_kind != 0) {
                PyErr_SetString(PyExc_ValueError,
                                "non-bool aux slot must not have int initial");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            if (iv != 0 && iv != 1) {
                PyErr_SetString(PyExc_ValueError,
                                "bool aux initial must be 0/1");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            rules->aux_slots[a].initial_kind = 1;
            rules->aux_slots[a].initial_int = iv;
        } else if (PyList_Check(init) && PyList_Size(init) == 2) {
            uint16_t f, r;
            if (!sem_u16(PyList_GetItem(init, 0), &f) ||
                !sem_u16(PyList_GetItem(init, 1), &r)) {
                gc_semantic_rules_free(rules);
                return NULL;
            }
            if (rules->aux_slots[a].value_kind != 1) {
                PyErr_SetString(PyExc_ValueError,
                                "bool aux slot must not have square initial");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            if (f >= rules->board_size || r >= rules->board_size) {
                PyErr_SetString(PyExc_ValueError,
                                "aux square initial out of board range");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            rules->aux_slots[a].initial_kind = 2;
            rules->aux_slots[a].initial_file = f;
            rules->aux_slots[a].initial_rank = r;
        } else {
            PyErr_SetString(PyExc_ValueError, "invalid aux initial");
            gc_semantic_rules_free(rules);
            return NULL;
        }
    }
    /* aux slot ids are canonical compiled identities: unique required */
    for (uint8_t a = 0; a < rules->aux_slot_count; a++) {
        for (uint8_t b = (uint8_t)(a + 1); b < rules->aux_slot_count; b++) {
            if (rules->aux_slots[a].slot_id == rules->aux_slots[b].slot_id) {
                PyErr_SetString(PyExc_ValueError,
                                "duplicate aux slot_id");
                gc_semantic_rules_free(rules);
                return NULL;
            }
        }
    }

    /* triggers */
    if (!sem_get_list(payload, "triggers", &list_obj)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    uint64_t trigger_count64;
    if (!sem_list_len(list_obj, 0xFFFF, &trigger_count64)) {
        PyErr_SetString(PyExc_ValueError, "too many semantic triggers");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->trigger_count = (uint16_t)trigger_count64;
    if (rules->trigger_count > 0) {
        rules->triggers = (GCSemTrigger *)calloc(
            rules->trigger_count, sizeof(GCSemTrigger));
        if (rules->triggers == NULL) {
            PyErr_NoMemory();
            gc_semantic_rules_free(rules);
            return NULL;
        }
    }
    for (uint16_t t = 0; t < rules->trigger_count; t++) {
        PyObject *td = PyList_GetItem(list_obj, t);
        uint16_t sid;
        if (!PyDict_Check(td) ||
            !sem_u16(PyDict_GetItemString(td, "slot_id"), &sid) ||
            !sem_enum(PyDict_GetItemString(td, "event"), 0, 1,
                      &rules->triggers[t].event) ||
            !sem_enum(PyDict_GetItemString(td, "owner"), 0, 2,
                      &rules->triggers[t].owner)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        uint8_t found = 0;
        for (uint8_t a = 0; a < rules->aux_slot_count; a++) {
            if (rules->aux_slots[a].slot_id == sid) {
                found = 1;
                break;
            }
        }
        if (!found) {
            PyErr_SetString(PyExc_ValueError,
                            "trigger slot_id references unknown aux slot");
            gc_semantic_rules_free(rules);
            return NULL;
        }
        rules->triggers[t].slot_id = sid;
        PyObject *sr = PyDict_GetItemString(td, "square_ref");
        if (!PyDict_Check(sr) ||
            !sem_parse_square_ref(sr, &rules->triggers[t].square_ref, rules)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
    }

    /* patterns */
    if (!sem_get_list(payload, "patterns", &list_obj)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    uint64_t pattern_count64;
    if (!sem_list_len(list_obj, GC_SEM_MAX_PATTERNS, &pattern_count64)) {
        PyErr_SetString(PyExc_ValueError, "too many semantic patterns");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->pattern_count = (uint16_t)pattern_count64;
    if (rules->pattern_count > 0) {
        rules->patterns = (GCSemPattern *)calloc(
            rules->pattern_count, sizeof(GCSemPattern));
        if (rules->patterns == NULL) {
            PyErr_NoMemory();
            gc_semantic_rules_free(rules);
            return NULL;
        }
    }
    for (uint16_t p = 0; p < rules->pattern_count; p++) {
        PyObject *pd = PyList_GetItem(list_obj, p);
        if (!PyDict_Check(pd)) {
            PyErr_SetString(PyExc_ValueError, "pattern entry must be a dict");
            gc_semantic_rules_free(rules);
            return NULL;
        }
        GCSemPattern *pat = &rules->patterns[p];
        PyObject *sub = NULL;
        uint16_t type_count16, geometry_count16;
        if (!sem_get_list(pd, "type_indices", &sub) ||
            !sem_alloc_uint16_list(sub, &pat->type_indices, &type_count16, 0xFF)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        pat->type_count = (uint8_t)type_count16;
        if (pat->type_count < 1) {
            PyErr_SetString(PyExc_ValueError,
                            "pattern type_indices must be non-empty");
            gc_semantic_rules_free(rules);
            return NULL;
        }
        for (uint8_t i = 0; i < pat->type_count; i++) {
            if (pat->type_indices[i] >= rules->type_count) {
                PyErr_SetString(PyExc_ValueError,
                                "pattern type index out of range");
                gc_semantic_rules_free(rules);
                return NULL;
            }
        }
        if (!sem_get_list(pd, "geometry_indices", &sub) ||
            !sem_alloc_uint16_list(sub, &pat->geometry_indices,
                                   &geometry_count16, 0xFF)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        pat->geometry_count = (uint8_t)geometry_count16;
        if (pat->geometry_count < 1) {
            PyErr_SetString(PyExc_ValueError,
                            "pattern geometry_indices must be non-empty");
            gc_semantic_rules_free(rules);
            return NULL;
        }
        for (uint8_t i = 0; i < pat->geometry_count; i++) {
            if (pat->geometry_indices[i] >= rules->geometry_count) {
                PyErr_SetString(PyExc_ValueError,
                                "pattern geometry index out of range");
                gc_semantic_rules_free(rules);
                return NULL;
            }
        }
        if (!sem_enum(PyDict_GetItemString(pd, "target"), 0, 3,
                      &pat->target) ||
            !sem_enum(PyDict_GetItemString(pd, "promotion_mode"), 0, 2,
                      &pat->promotion_mode) ||
            !sem_enum(PyDict_GetItemString(pd, "cost"), 0, 4, &pat->cost) ||
            !sem_enum(PyDict_GetItemString(pd, "stratum"), 0, 5,
                      &pat->stratum)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        uint16_t ept;
        if (!sem_opt_u16(pd, "explicit_promotion_type",
                         &pat->has_explicit_promotion, &ept)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        if (pat->has_explicit_promotion) {
            if (ept >= rules->type_count) {
                PyErr_SetString(PyExc_ValueError,
                                "explicit promotion type index out of range");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            pat->explicit_promotion_type = ept;
        }
        if (pat->promotion_mode == 2) {  /* explicit */
            if (!pat->has_explicit_promotion) {
                PyErr_SetString(PyExc_ValueError,
                                "explicit promotion mode requires "
                                "explicit_promotion_type");
                gc_semantic_rules_free(rules);
                return NULL;
            }
        } else if (pat->has_explicit_promotion) {
            PyErr_SetString(PyExc_ValueError,
                            "non-explicit promotion mode must not carry "
                            "explicit_promotion_type");
            gc_semantic_rules_free(rules);
            return NULL;
        }

        /* path / guards / slot_guards / effects / invariants / postconditions */
        if (!sem_get_list(pd, "path", &sub)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        {
            uint64_t n64;
            if (!sem_list_len(sub, 0xFF, &n64)) {
                PyErr_SetString(PyExc_ValueError, "pattern path too large");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            uint8_t n = (uint8_t)n64;
            pat->path_count = n;
            if (n > 0) {
                pat->path = (GCSemPathPredicate *)calloc((size_t)n, sizeof(GCSemPathPredicate));
                if (pat->path == NULL) {
                    PyErr_NoMemory();
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
            for (uint8_t i = 0; i < n; i++) {
                if (!sem_parse_path_predicate(PyList_GetItem(sub, i), &pat->path[i])) {
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
        }
        if (!sem_get_list(pd, "guards", &sub)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        {
            uint64_t n64;
            if (!sem_list_len(sub, 0xFF, &n64)) {
                PyErr_SetString(PyExc_ValueError, "pattern guards too large");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            uint8_t n = (uint8_t)n64;
            pat->guard_count = n;
            if (n > 0) {
                pat->guards = (GCSemStateGuard *)calloc((size_t)n, sizeof(GCSemStateGuard));
                if (pat->guards == NULL) {
                    PyErr_NoMemory();
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
            for (uint8_t i = 0; i < n; i++) {
                if (!sem_parse_state_guard(PyList_GetItem(sub, i),
                                           &pat->guards[i], rules)) {
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
        }
        if (!sem_get_list(pd, "slot_guards", &sub)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        {
            uint64_t n64;
            if (!sem_list_len(sub, 0xFF, &n64)) {
                PyErr_SetString(PyExc_ValueError, "pattern slot_guards too large");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            uint8_t n = (uint8_t)n64;
            pat->slot_guard_count = n;
            if (n > 0) {
                pat->slot_guards = (GCSemSlotGuard *)calloc((size_t)n, sizeof(GCSemSlotGuard));
                if (pat->slot_guards == NULL) {
                    PyErr_NoMemory();
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
            for (uint8_t i = 0; i < n; i++) {
                if (!sem_parse_slot_guard(PyList_GetItem(sub, i),
                                          &pat->slot_guards[i], rules)) {
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
        }
        if (!sem_get_list(pd, "effects", &sub)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        {
            uint64_t n64;
            if (!sem_list_len(sub, GC_SEM_MAX_EFFECTS, &n64)) {
                PyErr_SetString(PyExc_ValueError, "pattern effects exceed 4");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            uint8_t n = (uint8_t)n64;
            pat->effect_count = n;
            if (n > 0) {
                pat->effects = (GCSemEffect *)calloc((size_t)n, sizeof(GCSemEffect));
                if (pat->effects == NULL) {
                    PyErr_NoMemory();
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
            for (uint8_t i = 0; i < n; i++) {
                if (!sem_parse_effect(PyList_GetItem(sub, i),
                                      &pat->effects[i], rules)) {
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
        }
        if (!sem_get_list(pd, "invariants", &sub)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        {
            uint64_t n64;
            if (!sem_list_len(sub, 0xFF, &n64)) {
                PyErr_SetString(PyExc_ValueError, "pattern invariants too large");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            uint8_t n = (uint8_t)n64;
            pat->invariant_count = n;
            if (n > 0) {
                pat->invariants = (GCSemInvariant *)calloc((size_t)n, sizeof(GCSemInvariant));
                if (pat->invariants == NULL) {
                    PyErr_NoMemory();
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
            for (uint8_t i = 0; i < n; i++) {
                if (!sem_parse_invariant(PyList_GetItem(sub, i),
                                         &pat->invariants[i], rules)) {
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
        }
        if (!sem_get_list(pd, "postconditions", &sub)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        {
            uint64_t n64;
            if (!sem_list_len(sub, 2, &n64)) {
                PyErr_SetString(PyExc_ValueError, "pattern postconditions too large");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            uint8_t n = (uint8_t)n64;
            pat->postcondition_count = n;
            if (n > 0) {
                pat->postconditions = (GCSemPostcondition *)calloc(
                    (size_t)n, sizeof(GCSemPostcondition));
                if (pat->postconditions == NULL) {
                    PyErr_NoMemory();
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
            for (uint8_t i = 0; i < n; i++) {
                if (!sem_parse_postcondition(PyList_GetItem(sub, i),
                                             &pat->postconditions[i])) {
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
        }
    }

    return rules;
}

/* ------------------------------------------------------------------ free */

void gc_semantic_rules_free(GCSemanticRules *rules) {
    if (rules == NULL) {
        return;
    }
    if (rules->patterns != NULL) {
        for (uint16_t p = 0; p < rules->pattern_count; p++) {
            GCSemPattern *pat = &rules->patterns[p];
            free(pat->type_indices);
            free(pat->geometry_indices);
            free(pat->path);
            if (pat->guards != NULL) {
                for (uint8_t g = 0; g < pat->guard_count; g++) {
                    free(pat->guards[g].spatial.refs);
                }
            }
            free(pat->guards);
            free(pat->slot_guards);
            free(pat->effects);
            if (pat->invariants != NULL) {
                for (uint8_t i = 0; i < pat->invariant_count; i++) {
                    free(pat->invariants[i].refs);
                }
            }
            free(pat->invariants);
            free(pat->postconditions);
        }
        free(rules->patterns);
    }
    if (rules->geometries != NULL) {
        for (uint16_t g = 0; g < rules->geometry_count; g++) {
            for (int o = 0; o < 2; o++) {
                for (uint16_t e = 0; e < rules->geometries[g].paths[o].count; e++) {
                    free(rules->geometries[g].paths[o].entries[e].squares);
                }
                free(rules->geometries[g].paths[o].entries);
            }
        }
        free(rules->geometries);
    }
    if (rules->zones != NULL) {
        for (uint16_t z = 0; z < rules->zone_count; z++) {
            free(rules->zones[z].squares);
        }
        free(rules->zones);
    }
    if (rules->type_ids != NULL) {
        for (uint16_t t = 0; t < rules->type_count; t++) {
            free(rules->type_ids[t]);
        }
        free(rules->type_ids);
    }
    free(rules->aux_slots);
    free(rules->triggers);
    for (uint16_t t = 0; t < rules->type_count; t++) {
        for (int o = 0; o < 2; o++) {
            free(rules->promo_allowed[t][o].pairs);
            free(rules->promo_forced[t][o].squares);
            free(rules->drop_mask[t][o].squares);
        }
    }
    free(rules);
}

/* ------------------------------------------------------------------ info */

static PyObject *sem_info_long_list(const uint16_t *arr, uint16_t count) {
    PyObject *out = PyList_New(count);
    if (out == NULL) {
        return NULL;
    }
    for (uint16_t i = 0; i < count; i++) {
        PyObject *v = PyLong_FromUnsignedLong(arr[i]);
        if (v == NULL) {
            Py_DECREF(out);
            return NULL;
        }
        PyList_SET_ITEM(out, i, v);
    }
    return out;
}

static PyObject *sem_info_uint32_list(const uint32_t *arr, uint16_t count) {
    PyObject *out = PyList_New(count);
    if (out == NULL) {
        return NULL;
    }
    for (uint16_t i = 0; i < count; i++) {
        PyObject *v = PyLong_FromUnsignedLong(arr[i]);
        if (v == NULL) {
            Py_DECREF(out);
            return NULL;
        }
        PyList_SET_ITEM(out, i, v);
    }
    return out;
}

static PyObject *sem_info_square_ref(const GCSemSquareRef *ref) {
    PyObject *d = PyDict_New();
    if (d == NULL) {
        return NULL;
    }
#define SEM_DICT_SET(key, obj) \
    do { \
        if (PyDict_SetItemString(d, (key), (obj)) != 0) { \
            Py_DECREF(obj); \
            Py_DECREF(d); \
            return NULL; \
        } \
        Py_DECREF(obj); \
    } while (0)
    PyObject *v = PyLong_FromUnsignedLong(ref->kind);
    SEM_DICT_SET("kind", v);
    v = ref->has_square ? PyLong_FromUnsignedLong(ref->square) : Py_NewRef(Py_None);
    SEM_DICT_SET("square", v);
    if (ref->has_offset) {
        PyObject *pair = Py_BuildValue("[ii]", ref->offset_df, ref->offset_dr);
        if (pair == NULL) {
            Py_DECREF(d);
            return NULL;
        }
        SEM_DICT_SET("offset", pair);
    } else {
        v = Py_NewRef(Py_None);
        SEM_DICT_SET("offset", v);
    }
    v = PyLong_FromUnsignedLong(ref->owner_relative);
    SEM_DICT_SET("owner_relative", v);
    v = ref->has_step ? PyLong_FromUnsignedLong(ref->step) : Py_NewRef(Py_None);
    SEM_DICT_SET("step", v);
    v = ref->has_slot ? PyLong_FromUnsignedLong(ref->slot_id) : Py_NewRef(Py_None);
    SEM_DICT_SET("slot_id", v);
#undef SEM_DICT_SET
    return d;
}

static PyObject *sem_info_type_ref(const GCSemTypeRef *ref) {
    PyObject *d = PyDict_New();
    if (d == NULL) {
        return NULL;
    }
    PyObject *v = PyLong_FromUnsignedLong(ref->kind);
    if (PyDict_SetItemString(d, "kind", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    v = ref->has_type ? PyLong_FromUnsignedLong(ref->type_index) : Py_NewRef(Py_None);
    if (PyDict_SetItemString(d, "type_index", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    return d;
}

static PyObject *sem_info_square_ref_list(const GCSemSquareRef *refs,
                                          uint16_t count) {
    PyObject *out = PyList_New(count);
    if (out == NULL) {
        return NULL;
    }
    for (uint16_t i = 0; i < count; i++) {
        PyObject *item = sem_info_square_ref(&refs[i]);
        if (item == NULL) {
            Py_DECREF(out);
            return NULL;
        }
        PyList_SET_ITEM(out, i, item);
    }
    return out;
}

static PyObject *sem_info_spatial(const GCSemSpatial *sp) {
    PyObject *d = PyDict_New();
    if (d == NULL) {
        return NULL;
    }
    PyObject *v = PyLong_FromUnsignedLong(sp->kind);
    if (PyDict_SetItemString(d, "kind", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    PyObject *refs = sem_info_square_ref_list(sp->refs, sp->refs_count);
    if (refs == NULL || PyDict_SetItemString(d, "refs", refs) != 0) {
        Py_XDECREF(refs);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(refs);
    v = sp->has_zone ? PyLong_FromUnsignedLong(sp->zone_index) : Py_NewRef(Py_None);
    if (PyDict_SetItemString(d, "zone_index", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    return d;
}

static PyObject *sem_info_state_guard(const GCSemStateGuard *g) {
    PyObject *d = PyDict_New();
    if (d == NULL) {
        return NULL;
    }
    PyObject *tr = sem_info_type_ref(&g->type_ref);
    PyObject *sp = sem_info_spatial(&g->spatial);
    PyObject *sr = g->has_subject_ref ? sem_info_square_ref(&g->subject_ref) : Py_NewRef(Py_None);
    if (tr == NULL || sp == NULL || sr == NULL) {
        Py_XDECREF(tr);
        Py_XDECREF(sp);
        Py_XDECREF(sr);
        Py_DECREF(d);
        return NULL;
    }
    PyObject *items[] = {
        PyLong_FromUnsignedLong(g->aggregation),
        PyLong_FromUnsignedLong(g->owner),
        tr,
        PyLong_FromUnsignedLong(g->compare_field),
        PyLong_FromUnsignedLong(g->promoted),
        PyLong_FromUnsignedLong(g->location),
        sr,
        sp,
        PyLong_FromUnsignedLong(g->comparison),
        PyLong_FromLong(g->value),
    };
    const char *keys[] = {
        "aggregation", "owner", "type_ref", "compare_field", "promoted",
        "location", "subject_ref", "spatial", "comparison", "value",
    };
    for (int i = 0; i < 10; i++) {
        if (items[i] == NULL ||
            PyDict_SetItemString(d, keys[i], items[i]) != 0) {
            for (int j = 0; j < 10; j++) {
                Py_XDECREF(items[j]);
            }
            Py_DECREF(d);
            return NULL;
        }
        Py_DECREF(items[i]);
    }
    return d;
}

static PyObject *sem_info_slot_guard(const GCSemSlotGuard *g) {
    PyObject *d = PyDict_New();
    if (d == NULL) {
        return NULL;
    }
    PyObject *v = PyLong_FromUnsignedLong(g->slot_id);
    if (PyDict_SetItemString(d, "slot_id", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    v = PyLong_FromUnsignedLong(g->comparison);
    if (PyDict_SetItemString(d, "comparison", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    v = g->has_value ? PyLong_FromLong(g->value) : Py_NewRef(Py_None);
    if (PyDict_SetItemString(d, "value", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    PyObject *sr = g->has_square_ref ? sem_info_square_ref(&g->square_ref)
                                     : Py_NewRef(Py_None);
    if (sr == NULL || PyDict_SetItemString(d, "square_ref", sr) != 0) {
        Py_XDECREF(sr);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(sr);
    return d;
}

static PyObject *sem_info_effect(const GCSemEffect *e) {
    PyObject *d = PyDict_New();
    if (d == NULL) {
        return NULL;
    }
    PyObject *v = PyLong_FromUnsignedLong(e->kind);
    if (PyDict_SetItemString(d, "kind", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);

#define SEM_EFFECT_REF(key, has_field, ref_field) \
    do { \
        PyObject *o = e->has_field ? sem_info_square_ref(&e->ref_field) \
                                   : Py_NewRef(Py_None); \
        if (o == NULL || PyDict_SetItemString(d, key, o) != 0) { \
            Py_XDECREF(o); \
            Py_DECREF(d); \
            return NULL; \
        } \
        Py_DECREF(o); \
    } while (0)
    SEM_EFFECT_REF("from_ref", has_from, from_ref);
    SEM_EFFECT_REF("to_ref", has_to, to_ref);
    SEM_EFFECT_REF("square_ref", has_square, square_ref);
#undef SEM_EFFECT_REF

    v = PyLong_FromUnsignedLong(e->piece_owner);
    if (PyDict_SetItemString(d, "piece_owner", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);

#define SEM_EFFECT_TREF(key, has_field, ref_field) \
    do { \
        PyObject *o = e->has_field ? sem_info_type_ref(&e->ref_field) \
                                   : Py_NewRef(Py_None); \
        if (o == NULL || PyDict_SetItemString(d, key, o) != 0) { \
            Py_XDECREF(o); \
            Py_DECREF(d); \
            return NULL; \
        } \
        Py_DECREF(o); \
    } while (0)
    SEM_EFFECT_TREF("piece_type_ref", has_piece_type_ref, piece_type_ref);

    v = e->has_disposition ? PyLong_FromUnsignedLong(e->disposition)
                           : Py_NewRef(Py_None);
    if (PyDict_SetItemString(d, "disposition", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    v = e->has_slot ? PyLong_FromUnsignedLong(e->slot_id) : Py_NewRef(Py_None);
    if (PyDict_SetItemString(d, "slot_id", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    SEM_EFFECT_TREF("type_ref", has_type_ref, type_ref);
#undef SEM_EFFECT_TREF
    v = PyLong_FromUnsignedLong(e->count);
    if (PyDict_SetItemString(d, "count", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    v = e->has_value ? PyLong_FromLong(e->value) : Py_NewRef(Py_None);
    if (PyDict_SetItemString(d, "value", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    return d;
}

static PyObject *sem_info_invariant(const GCSemInvariant *inv) {
    PyObject *d = PyDict_New();
    if (d == NULL) {
        return NULL;
    }
    PyObject *v = PyLong_FromUnsignedLong(inv->kind);
    if (PyDict_SetItemString(d, "kind", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    PyObject *refs = sem_info_square_ref_list(inv->refs, inv->refs_count);
    if (refs == NULL || PyDict_SetItemString(d, "square_refs", refs) != 0) {
        Py_XDECREF(refs);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(refs);
    return d;
}

static PyObject *sem_info_postcondition(const GCSemPostcondition *pc) {
    return Py_BuildValue("{s:i,s:i}", "kind", (int)pc->kind,
                         "max_stratum", (int)pc->max_stratum);
}

static PyObject *sem_info_path_predicate(const GCSemPathPredicate *pp) {
    PyObject *d = PyDict_New();
    if (d == NULL) {
        return NULL;
    }
    PyObject *v = PyLong_FromUnsignedLong(pp->kind);
    if (PyDict_SetItemString(d, "kind", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    v = pp->has_count ? PyLong_FromLong(pp->count) : Py_NewRef(Py_None);
    if (PyDict_SetItemString(d, "count", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    v = pp->has_lo ? PyLong_FromLong(pp->lo) : Py_NewRef(Py_None);
    if (PyDict_SetItemString(d, "lo", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    v = pp->has_hi ? PyLong_FromLong(pp->hi) : Py_NewRef(Py_None);
    if (PyDict_SetItemString(d, "hi", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    v = PyLong_FromUnsignedLong(pp->owner_filter);
    if (PyDict_SetItemString(d, "owner_filter", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    return d;
}

static PyObject *sem_info_pattern(const GCSemPattern *pat) {
    PyObject *d = PyDict_New();
    if (d == NULL) {
        return NULL;
    }
    PyObject *type_indices = sem_info_long_list(pat->type_indices, pat->type_count);
    PyObject *geometry_indices = sem_info_long_list(pat->geometry_indices,
                                                    pat->geometry_count);
    if (type_indices == NULL || geometry_indices == NULL) {
        Py_XDECREF(type_indices);
        Py_XDECREF(geometry_indices);
        Py_DECREF(d);
        return NULL;
    }
    if (PyDict_SetItemString(d, "type_indices", type_indices) != 0 ||
        PyDict_SetItemString(d, "geometry_indices", geometry_indices) != 0) {
        Py_DECREF(type_indices);
        Py_DECREF(geometry_indices);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(type_indices);
    Py_DECREF(geometry_indices);

    PyObject *path = PyList_New(pat->path_count);
    if (path == NULL) {
        Py_DECREF(d);
        return NULL;
    }
    for (uint8_t i = 0; i < pat->path_count; i++) {
        PyObject *item = sem_info_path_predicate(&pat->path[i]);
        if (item == NULL) {
            Py_DECREF(path);
            Py_DECREF(d);
            return NULL;
        }
        PyList_SET_ITEM(path, i, item);
    }
    if (PyDict_SetItemString(d, "path", path) != 0) {
        Py_DECREF(path);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(path);

    PyObject *guards = PyList_New(pat->guard_count);
    if (guards == NULL) {
        Py_DECREF(d);
        return NULL;
    }
    for (uint8_t i = 0; i < pat->guard_count; i++) {
        PyObject *item = sem_info_state_guard(&pat->guards[i]);
        if (item == NULL) {
            Py_DECREF(guards);
            Py_DECREF(d);
            return NULL;
        }
        PyList_SET_ITEM(guards, i, item);
    }
    if (PyDict_SetItemString(d, "guards", guards) != 0) {
        Py_DECREF(guards);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(guards);

    PyObject *slot_guards = PyList_New(pat->slot_guard_count);
    if (slot_guards == NULL) {
        Py_DECREF(d);
        return NULL;
    }
    for (uint8_t i = 0; i < pat->slot_guard_count; i++) {
        PyObject *item = sem_info_slot_guard(&pat->slot_guards[i]);
        if (item == NULL) {
            Py_DECREF(slot_guards);
            Py_DECREF(d);
            return NULL;
        }
        PyList_SET_ITEM(slot_guards, i, item);
    }
    if (PyDict_SetItemString(d, "slot_guards", slot_guards) != 0) {
        Py_DECREF(slot_guards);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(slot_guards);

    PyObject *effects = PyList_New(pat->effect_count);
    if (effects == NULL) {
        Py_DECREF(d);
        return NULL;
    }
    for (uint8_t i = 0; i < pat->effect_count; i++) {
        PyObject *item = sem_info_effect(&pat->effects[i]);
        if (item == NULL) {
            Py_DECREF(effects);
            Py_DECREF(d);
            return NULL;
        }
        PyList_SET_ITEM(effects, i, item);
    }
    if (PyDict_SetItemString(d, "effects", effects) != 0) {
        Py_DECREF(effects);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(effects);

    PyObject *invariants = PyList_New(pat->invariant_count);
    if (invariants == NULL) {
        Py_DECREF(d);
        return NULL;
    }
    for (uint8_t i = 0; i < pat->invariant_count; i++) {
        PyObject *item = sem_info_invariant(&pat->invariants[i]);
        if (item == NULL) {
            Py_DECREF(invariants);
            Py_DECREF(d);
            return NULL;
        }
        PyList_SET_ITEM(invariants, i, item);
    }
    if (PyDict_SetItemString(d, "invariants", invariants) != 0) {
        Py_DECREF(invariants);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(invariants);

    PyObject *postconditions = PyList_New(pat->postcondition_count);
    if (postconditions == NULL) {
        Py_DECREF(d);
        return NULL;
    }
    for (uint8_t i = 0; i < pat->postcondition_count; i++) {
        PyObject *item = sem_info_postcondition(&pat->postconditions[i]);
        if (item == NULL) {
            Py_DECREF(postconditions);
            Py_DECREF(d);
            return NULL;
        }
        PyList_SET_ITEM(postconditions, i, item);
    }
    if (PyDict_SetItemString(d, "postconditions", postconditions) != 0) {
        Py_DECREF(postconditions);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(postconditions);

    PyObject *v = PyLong_FromUnsignedLong(pat->target);
    if (PyDict_SetItemString(d, "target", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    v = PyLong_FromUnsignedLong(pat->promotion_mode);
    if (PyDict_SetItemString(d, "promotion_mode", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    v = pat->has_explicit_promotion
            ? PyLong_FromUnsignedLong(pat->explicit_promotion_type)
            : Py_NewRef(Py_None);
    if (PyDict_SetItemString(d, "explicit_promotion_type", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    v = PyLong_FromUnsignedLong(pat->cost);
    if (PyDict_SetItemString(d, "cost", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    v = PyLong_FromUnsignedLong(pat->stratum);
    if (PyDict_SetItemString(d, "stratum", v) != 0) {
        Py_DECREF(v);
        Py_DECREF(d);
        return NULL;
    }
    Py_DECREF(v);
    return d;
}

PyObject *gc_semantic_rules_build_info(const GCSemanticRules *rules) {
    PyObject *payload = PyDict_New();
    if (payload == NULL) {
        return NULL;
    }

#define SEM_INFO_SET(key, obj) \
    do { \
        if ((obj) == NULL || PyDict_SetItemString(payload, (key), (obj)) != 0) { \
            Py_XDECREF(obj); \
            Py_DECREF(payload); \
            return NULL; \
        } \
        Py_DECREF(obj); \
    } while (0)

    SEM_INFO_SET("semantic_payload_version",
                 PyLong_FromUnsignedLong(rules->semantic_payload_version));
    SEM_INFO_SET("fingerprint", PyUnicode_FromString(rules->fingerprint));
    SEM_INFO_SET("board_size", PyLong_FromUnsignedLong(rules->board_size));
    SEM_INFO_SET("repetition_limit", PyLong_FromUnsignedLong(rules->repetition_limit));
    SEM_INFO_SET("repetition_policy", PyLong_FromUnsignedLong(rules->repetition_policy));
    SEM_INFO_SET("automatic_adjudication_ply",
                 rules->automatic_adjudication_ply
                     ? PyLong_FromUnsignedLong(rules->automatic_adjudication_ply)
                     : Py_NewRef(Py_None));
    SEM_INFO_SET("max_ply", PyLong_FromUnsignedLong(rules->max_ply));
    if (rules->semantic_payload_version >= 2) {
        PyObject *type_ids = PyList_New(rules->type_count);
        if (type_ids == NULL) {
            Py_DECREF(payload);
            return NULL;
        }
        for (uint16_t t = 0; t < rules->type_count; t++) {
            PyObject *item = PyUnicode_FromString(rules->type_ids[t]);
            if (item == NULL) {
                Py_DECREF(type_ids);
                Py_DECREF(payload);
                return NULL;
            }
            PyList_SET_ITEM(type_ids, t, item);
        }
        SEM_INFO_SET("type_ids", type_ids);
    }

    PyObject *types = PyList_New(rules->type_count);
    if (types == NULL) {
        Py_DECREF(payload);
        return NULL;
    }
    for (uint16_t t = 0; t < rules->type_count; t++) {
        PyObject *td = PyDict_New();
        if (td == NULL) {
            Py_DECREF(types);
            Py_DECREF(payload);
            return NULL;
        }
        PyObject *anchor = PyLong_FromUnsignedLong(rules->types[t].is_anchor);
        PyObject *promotable = PyLong_FromUnsignedLong(rules->types[t].is_promotable);
        PyObject *targets = sem_info_long_list(
            (const uint16_t *)rules->types[t].promo_targets,
            rules->types[t].promo_target_count);
        if (anchor == NULL || promotable == NULL || targets == NULL ||
            PyDict_SetItemString(td, "is_anchor", anchor) != 0 ||
            PyDict_SetItemString(td, "is_promotable", promotable) != 0 ||
            PyDict_SetItemString(td, "promo_targets", targets) != 0) {
            Py_XDECREF(anchor);
            Py_XDECREF(promotable);
            Py_XDECREF(targets);
            Py_DECREF(td);
            Py_DECREF(types);
            Py_DECREF(payload);
            return NULL;
        }
        Py_DECREF(anchor);
        Py_DECREF(promotable);
        Py_DECREF(targets);
        PyList_SET_ITEM(types, t, td);
    }
    SEM_INFO_SET("types", types);

#define SEM_INFO_OWNER_LISTS(strkey, field, data_field, list_fn) \
    do { \
        PyObject *top = PyList_New(rules->type_count); \
        if (top == NULL) { \
            Py_DECREF(payload); \
            return NULL; \
        } \
        for (uint16_t t = 0; t < rules->type_count; t++) { \
            PyObject *owners = PyList_New(2); \
            if (owners == NULL) { \
                Py_DECREF(top); \
                Py_DECREF(payload); \
                return NULL; \
            } \
            for (int o = 0; o < 2; o++) { \
                PyObject *lst = list_fn(rules->field[t][o].data_field, \
                                        rules->field[t][o].count); \
                if (lst == NULL) { \
                    Py_DECREF(owners); \
                    Py_DECREF(top); \
                    Py_DECREF(payload); \
                    return NULL; \
                } \
                PyList_SET_ITEM(owners, o, lst); \
            } \
            PyList_SET_ITEM(top, t, owners); \
        } \
        SEM_INFO_SET(strkey, top); \
    } while (0)

    SEM_INFO_OWNER_LISTS("promo_allowed", promo_allowed, pairs, sem_info_uint32_list);
    SEM_INFO_OWNER_LISTS("promo_forced", promo_forced, squares, sem_info_long_list);
    SEM_INFO_OWNER_LISTS("drop_mask", drop_mask, squares, sem_info_long_list);
#undef SEM_INFO_OWNER_LISTS

    PyObject *alive = PyList_New(rules->type_count);
    if (alive == NULL) {
        Py_DECREF(payload);
        return NULL;
    }
    uint16_t squares = (uint16_t)(rules->board_size * rules->board_size);
    for (uint16_t t = 0; t < rules->type_count; t++) {
        PyObject *owners = PyList_New(2);
        if (owners == NULL) {
            Py_DECREF(alive);
            Py_DECREF(payload);
            return NULL;
        }
        for (int o = 0; o < 2; o++) {
            PyObject *masks = PyList_New(squares);
            if (masks == NULL) {
                Py_DECREF(owners);
                Py_DECREF(alive);
                Py_DECREF(payload);
                return NULL;
            }
            for (uint16_t sq = 0; sq < squares; sq++) {
                PyObject *m = PyLong_FromUnsignedLongLong(
                    rules->alive_promo[t][o][sq]);
                if (m == NULL) {
                    Py_DECREF(masks);
                    Py_DECREF(owners);
                    Py_DECREF(alive);
                    Py_DECREF(payload);
                    return NULL;
                }
                PyList_SET_ITEM(masks, sq, m);
            }
            PyList_SET_ITEM(owners, o, masks);
        }
        PyList_SET_ITEM(alive, t, owners);
    }
    SEM_INFO_SET("alive_promo", alive);

    PyObject *geometries = PyList_New(rules->geometry_count);
    if (geometries == NULL) {
        Py_DECREF(payload);
        return NULL;
    }
    for (uint16_t g = 0; g < rules->geometry_count; g++) {
        const GCSemGeometry *geo = &rules->geometries[g];
        PyObject *gd = PyDict_New();
        if (gd == NULL) {
            Py_DECREF(geometries);
            Py_DECREF(payload);
            return NULL;
        }
        PyObject *kind = PyLong_FromUnsignedLong(geo->kind);
        PyObject *min_steps = geo->has_min_steps
                                  ? PyLong_FromLong(geo->min_steps)
                                  : Py_NewRef(Py_None);
        PyObject *asrc = geo->has_atom_source
                             ? Py_BuildValue("[ii]", (int)geo->atom_source_type,
                                             (int)geo->atom_source_index)
                             : Py_NewRef(Py_None);
        if (kind == NULL || min_steps == NULL || asrc == NULL) {
            Py_XDECREF(kind);
            Py_XDECREF(min_steps);
            Py_XDECREF(asrc);
            Py_DECREF(gd);
            Py_DECREF(geometries);
            Py_DECREF(payload);
            return NULL;
        }
        PyObject *paths = PyList_New(2);
        if (paths == NULL) {
            Py_DECREF(kind);
            Py_DECREF(min_steps);
            Py_DECREF(asrc);
            Py_DECREF(gd);
            Py_DECREF(geometries);
            Py_DECREF(payload);
            return NULL;
        }
        for (int o = 0; o < 2; o++) {
            const GCSemPathOwner *po = &geo->paths[o];
            PyObject *entries = PyList_New(po->count);
            if (entries == NULL) {
                Py_DECREF(paths);
                Py_DECREF(kind);
                Py_DECREF(min_steps);
                Py_DECREF(asrc);
                Py_DECREF(gd);
                Py_DECREF(geometries);
                Py_DECREF(payload);
                return NULL;
            }
            for (uint16_t e = 0; e < po->count; e++) {
                const GCSemPathEntry *pe = &po->entries[e];
                PyObject *squares_list = sem_info_long_list(pe->squares, pe->count);
                if (squares_list == NULL) {
                    Py_DECREF(entries);
                    Py_DECREF(paths);
                    Py_DECREF(kind);
                    Py_DECREF(min_steps);
                    Py_DECREF(asrc);
                    Py_DECREF(gd);
                    Py_DECREF(geometries);
                    Py_DECREF(payload);
                    return NULL;
                }
                PyObject *entry = Py_BuildValue("[iO]", (int)pe->source,
                                                squares_list);
                Py_DECREF(squares_list);
                if (entry == NULL) {
                    Py_DECREF(entries);
                    Py_DECREF(paths);
                    Py_DECREF(kind);
                    Py_DECREF(min_steps);
                    Py_DECREF(asrc);
                    Py_DECREF(gd);
                    Py_DECREF(geometries);
                    Py_DECREF(payload);
                    return NULL;
                }
                PyList_SET_ITEM(entries, e, entry);
            }
            PyList_SET_ITEM(paths, o, entries);
        }
        if (PyDict_SetItemString(gd, "kind", kind) != 0 ||
            PyDict_SetItemString(gd, "min_steps", min_steps) != 0 ||
            PyDict_SetItemString(gd, "atom_source", asrc) != 0 ||
            PyDict_SetItemString(gd, "paths", paths) != 0) {
            Py_DECREF(kind);
            Py_DECREF(min_steps);
            Py_DECREF(asrc);
            Py_DECREF(paths);
            Py_DECREF(gd);
            Py_DECREF(geometries);
            Py_DECREF(payload);
            return NULL;
        }
        Py_DECREF(kind);
        Py_DECREF(min_steps);
        Py_DECREF(asrc);
        Py_DECREF(paths);
        PyList_SET_ITEM(geometries, g, gd);
    }
    SEM_INFO_SET("geometries", geometries);

    PyObject *zones = PyList_New(rules->zone_count);
    if (zones == NULL) {
        Py_DECREF(payload);
        return NULL;
    }
    for (uint16_t z = 0; z < rules->zone_count; z++) {
        PyObject *zd = PyDict_New();
        if (zd == NULL) {
            Py_DECREF(zones);
            Py_DECREF(payload);
            return NULL;
        }
        PyObject *sqs = sem_info_long_list(rules->zones[z].squares,
                                           rules->zones[z].count);
        if (sqs == NULL || PyDict_SetItemString(zd, "squares", sqs) != 0) {
            Py_XDECREF(sqs);
            Py_DECREF(zd);
            Py_DECREF(zones);
            Py_DECREF(payload);
            return NULL;
        }
        Py_DECREF(sqs);
        PyList_SET_ITEM(zones, z, zd);
    }
    SEM_INFO_SET("zones", zones);

    PyObject *aux = PyList_New(rules->aux_slot_count);
    if (aux == NULL) {
        Py_DECREF(payload);
        return NULL;
    }
    for (uint8_t a = 0; a < rules->aux_slot_count; a++) {
        const GCSemAuxSlot *slot = &rules->aux_slots[a];
        PyObject *ad = PyDict_New();
        if (ad == NULL) {
            Py_DECREF(aux);
            Py_DECREF(payload);
            return NULL;
        }
        PyObject *init;
        if (slot->initial_kind == 0) {
            init = Py_NewRef(Py_None);
        } else if (slot->initial_kind == 1) {
            init = PyLong_FromLong(slot->initial_int);
        } else {
            init = Py_BuildValue("[ii]", (int)slot->initial_file,
                                 (int)slot->initial_rank);
        }
        if (init == NULL) {
            Py_DECREF(ad);
            Py_DECREF(aux);
            Py_DECREF(payload);
            return NULL;
        }
        if (PyDict_SetItemString(ad, "slot_id",
                                 PyLong_FromUnsignedLong(slot->slot_id)) != 0 ||
            PyDict_SetItemString(ad, "value_kind",
                                 PyLong_FromUnsignedLong(slot->value_kind)) != 0 ||
            PyDict_SetItemString(ad, "scope",
                                 PyLong_FromUnsignedLong(slot->scope)) != 0 ||
            PyDict_SetItemString(ad, "lifetime",
                                 PyLong_FromUnsignedLong(slot->lifetime)) != 0 ||
            PyDict_SetItemString(ad, "initial", init) != 0) {
            Py_DECREF(init);
            Py_DECREF(ad);
            Py_DECREF(aux);
            Py_DECREF(payload);
            return NULL;
        }
        Py_DECREF(init);
        PyList_SET_ITEM(aux, a, ad);
    }
    SEM_INFO_SET("aux_slots", aux);

    PyObject *triggers = PyList_New(rules->trigger_count);
    if (triggers == NULL) {
        Py_DECREF(payload);
        return NULL;
    }
    for (uint16_t t = 0; t < rules->trigger_count; t++) {
        const GCSemTrigger *tr = &rules->triggers[t];
        PyObject *sr = sem_info_square_ref(&tr->square_ref);
        if (sr == NULL) {
            Py_DECREF(triggers);
            Py_DECREF(payload);
            return NULL;
        }
        PyObject *td = Py_BuildValue("{s:i,s:i,s:N,s:i}",
                                     "slot_id", (int)tr->slot_id,
                                     "event", (int)tr->event,
                                     "square_ref", sr,
                                     "owner", (int)tr->owner);
        if (td == NULL) {
            Py_DECREF(sr);
            Py_DECREF(triggers);
            Py_DECREF(payload);
            return NULL;
        }
        PyList_SET_ITEM(triggers, t, td);
    }
    SEM_INFO_SET("triggers", triggers);

    PyObject *patterns = PyList_New(rules->pattern_count);
    if (patterns == NULL) {
        Py_DECREF(payload);
        return NULL;
    }
    for (uint16_t p = 0; p < rules->pattern_count; p++) {
        PyObject *pd = sem_info_pattern(&rules->patterns[p]);
        if (pd == NULL) {
            Py_DECREF(patterns);
            Py_DECREF(payload);
            return NULL;
        }
        PyList_SET_ITEM(patterns, p, pd);
    }
    SEM_INFO_SET("patterns", patterns);
#undef SEM_INFO_SET
    return payload;
}
