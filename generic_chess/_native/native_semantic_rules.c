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

static int sem_read_long(PyObject *obj, long *out) {
    if (obj == NULL) {
        PyErr_SetString(PyExc_ValueError, "missing integer field");
        return 0;
    }
    long v = PyLong_AsLong(obj);
    if (v == -1 && PyErr_Occurred()) {
        return 0;
    }
    *out = v;
    return 1;
}

static int sem_optional_long(PyObject *dict, const char *key,
                             uint8_t *has, long *out) {
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
    if (!sem_read_long(v, out)) {
        return 0;
    }
    *has = 1;
    return 1;
}

static int sem_get_list(PyObject *dict, const char *key, PyObject **out) {
    *out = PyDict_GetItemString(dict, key);
    if (*out == NULL || !PyList_Check(*out)) {
        PyErr_SetString(PyExc_ValueError, "expected a list field");
        return 0;
    }
    return 1;
}

static int sem_parse_square_ref(PyObject *d, GCSemSquareRef *out) {
    memset(out, 0, sizeof(*out));
    long kind, own;
    if (!sem_read_long(PyDict_GetItemString(d, "kind"), &kind)) {
        return 0;
    }
    if (!sem_read_long(PyDict_GetItemString(d, "owner_relative"), &own)) {
        return 0;
    }
    out->kind = (uint8_t)kind;
    out->owner_relative = (uint8_t)own;

    long square;
    if (!sem_optional_long(d, "square", &out->has_square, &square)) {
        return 0;
    }
    if (out->has_square) {
        out->square = (uint16_t)square;
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
        long df, dr;
        if (!sem_read_long(PyList_GetItem(off, 0), &df) ||
            !sem_read_long(PyList_GetItem(off, 1), &dr)) {
            return 0;
        }
        out->has_offset = 1;
        out->offset_df = (int16_t)df;
        out->offset_dr = (int16_t)dr;
    }

    long step, slot;
    if (!sem_optional_long(d, "step", &out->has_step, &step)) {
        return 0;
    }
    if (out->has_step) {
        out->step = (uint16_t)step;
    }
    if (!sem_optional_long(d, "slot_id", &out->has_slot, &slot)) {
        return 0;
    }
    if (out->has_slot) {
        out->slot_id = (uint16_t)slot;
    }
    return 1;
}

static int sem_parse_type_ref(PyObject *d, GCSemTypeRef *out) {
    memset(out, 0, sizeof(*out));
    long kind, ti;
    if (!sem_read_long(PyDict_GetItemString(d, "kind"), &kind)) {
        return 0;
    }
    out->kind = (uint8_t)kind;
    if (!sem_optional_long(d, "type_index", &out->has_type, &ti)) {
        return 0;
    }
    if (out->has_type) {
        out->type_index = (uint16_t)ti;
    }
    return 1;
}

static int sem_parse_square_refs(PyObject *list, GCSemSquareRef **out,
                                 uint16_t *count, int max) {
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
            !sem_parse_square_ref(item, &refs[i])) {
            free(refs);
            return 0;
        }
    }
    *out = refs;
    *count = (uint16_t)n;
    return 1;
}

static int sem_parse_spatial(PyObject *d, GCSemSpatial *out) {
    memset(out, 0, sizeof(*out));
    long kind;
    if (!sem_read_long(PyDict_GetItemString(d, "kind"), &kind)) {
        return 0;
    }
    out->kind = (uint8_t)kind;
    PyObject *refs = NULL;
    if (!sem_get_list(d, "refs", &refs)) {
        return 0;
    }
    if (!sem_parse_square_refs(refs, &out->refs, &out->refs_count, 2)) {
        return 0;
    }
    long zid;
    if (!sem_optional_long(d, "zone_index", &out->has_zone, &zid)) {
        return 0;
    }
    if (out->has_zone) {
        out->zone_index = (uint16_t)zid;
    }
    return 1;
}

static int sem_parse_state_guard(PyObject *d, GCSemStateGuard *out) {
    memset(out, 0, sizeof(*out));
    long v;
#define SEM_GUARD_LONG(key, field) \
    if (!sem_read_long(PyDict_GetItemString(d, key), &v)) { return 0; } \
    out->field = (uint8_t)v;
    SEM_GUARD_LONG("aggregation", aggregation);
    SEM_GUARD_LONG("owner", owner);
    SEM_GUARD_LONG("compare_field", compare_field);
    SEM_GUARD_LONG("promoted", promoted);
    SEM_GUARD_LONG("location", location);
    SEM_GUARD_LONG("comparison", comparison);
#undef SEM_GUARD_LONG
    PyObject *tr = PyDict_GetItemString(d, "type_ref");
    if (tr == NULL || !PyDict_Check(tr) ||
        !sem_parse_type_ref(tr, &out->type_ref)) {
        return 0;
    }
    PyObject *sp = PyDict_GetItemString(d, "spatial");
    if (sp == NULL || !PyDict_Check(sp) ||
        !sem_parse_spatial(sp, &out->spatial)) {
        return 0;
    }
    if (!sem_read_long(PyDict_GetItemString(d, "value"), &v)) {
        return 0;
    }
    out->value = (int32_t)v;
    return 1;
}

static int sem_parse_slot_guard(PyObject *d, GCSemSlotGuard *out) {
    memset(out, 0, sizeof(*out));
    long v;
    if (!sem_read_long(PyDict_GetItemString(d, "slot_id"), &v)) {
        return 0;
    }
    out->slot_id = (uint16_t)v;
    if (!sem_read_long(PyDict_GetItemString(d, "comparison"), &v)) {
        return 0;
    }
    out->comparison = (uint8_t)v;
    if (!sem_optional_long(d, "value", &out->has_value, &v)) {
        return 0;
    }
    if (out->has_value) {
        out->value = (int32_t)v;
    }
    PyObject *sr = PyDict_GetItemString(d, "square_ref");
    if (sr == NULL) {
        PyErr_SetString(PyExc_ValueError, "missing square_ref");
        return 0;
    }
    if (sr != Py_None) {
        if (!PyDict_Check(sr) || !sem_parse_square_ref(sr, &out->square_ref)) {
            return 0;
        }
        out->has_square_ref = 1;
    }
    return 1;
}

static int sem_parse_effect(PyObject *d, GCSemEffect *out) {
    memset(out, 0, sizeof(*out));
    long v;
    if (!sem_read_long(PyDict_GetItemString(d, "kind"), &v)) {
        return 0;
    }
    out->kind = (uint8_t)v;
    if (!sem_read_long(PyDict_GetItemString(d, "piece_owner"), &v)) {
        return 0;
    }
    out->piece_owner = (uint8_t)v;
    if (!sem_read_long(PyDict_GetItemString(d, "count"), &v)) {
        return 0;
    }
    out->count = (uint8_t)v;
    if (!sem_optional_long(d, "slot_id", &out->has_slot, &v)) {
        return 0;
    }
    if (out->has_slot) {
        out->slot_id = (uint16_t)v;
    }
    if (!sem_optional_long(d, "disposition", &out->has_disposition, &v)) {
        return 0;
    }
    if (out->has_disposition) {
        out->disposition = (uint8_t)v;
    }
    if (!sem_optional_long(d, "value", &out->has_value, &v)) {
        return 0;
    }
    if (out->has_value) {
        out->value = (int32_t)v;
    }

#define SEM_OPT_REF(key, has_field, ref_field) \
    do { \
        PyObject *o = PyDict_GetItemString(d, key); \
        if (o == NULL) { \
            PyErr_SetString(PyExc_ValueError, "missing " key); \
            return 0; \
        } \
        if (o != Py_None) { \
            if (!PyDict_Check(o) || !sem_parse_square_ref(o, &out->ref_field)) { \
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
            if (!PyDict_Check(o) || !sem_parse_type_ref(o, &out->ref_field)) { \
                return 0; \
            } \
            out->has_field = 1; \
        } \
    } while (0)
    SEM_OPT_TREF("piece_type_ref", has_piece_type_ref, piece_type_ref);
    SEM_OPT_TREF("type_ref", has_type_ref, type_ref);
#undef SEM_OPT_TREF
    return 1;
}

static int sem_parse_invariant(PyObject *d, GCSemInvariant *out) {
    memset(out, 0, sizeof(*out));
    long kind;
    if (!sem_read_long(PyDict_GetItemString(d, "kind"), &kind)) {
        return 0;
    }
    out->kind = (uint8_t)kind;
    PyObject *refs = NULL;
    if (!sem_get_list(d, "square_refs", &refs)) {
        return 0;
    }
    if (!sem_parse_square_refs(refs, &out->refs, &out->refs_count,
                               GC_SEM_MAX_INVARIANT_REFS)) {
        return 0;
    }
    return 1;
}

static int sem_parse_postcondition(PyObject *d, GCSemPostcondition *out) {
    memset(out, 0, sizeof(*out));
    long kind, stratum;
    if (!sem_read_long(PyDict_GetItemString(d, "kind"), &kind)) {
        return 0;
    }
    if (!sem_read_long(PyDict_GetItemString(d, "max_stratum"), &stratum)) {
        return 0;
    }
    out->kind = (uint8_t)kind;
    if (stratum > 3) {  /* probe must be <= S3 (ADR-017 section 13) */
        PyErr_SetString(PyExc_ValueError,
                        "postcondition probe stratum exceeds S3");
        return 0;
    }
    out->max_stratum = (uint8_t)stratum;
    return 1;
}

static int sem_parse_path_predicate(PyObject *d, GCSemPathPredicate *out) {
    memset(out, 0, sizeof(*out));
    long v;
    if (!sem_read_long(PyDict_GetItemString(d, "kind"), &v)) {
        return 0;
    }
    out->kind = (uint8_t)v;
    if (!sem_read_long(PyDict_GetItemString(d, "owner_filter"), &v)) {
        return 0;
    }
    out->owner_filter = (uint8_t)v;
    if (!sem_optional_long(d, "count", &out->has_count, &v)) {
        return 0;
    }
    if (out->has_count) {
        out->count = (int32_t)v;
    }
    if (!sem_optional_long(d, "lo", &out->has_lo, &v)) {
        return 0;
    }
    if (out->has_lo) {
        out->lo = (int32_t)v;
    }
    if (!sem_optional_long(d, "hi", &out->has_hi, &v)) {
        return 0;
    }
    if (out->has_hi) {
        out->hi = (int32_t)v;
    }
    return 1;
}

/* ------------------------------------------------------------------ compile */

static int sem_alloc_uint16_list(PyObject *list, uint16_t **out,
                                 uint16_t *count, int max) {
    Py_ssize_t n = PyList_Size(list);
    if (n > max) {
        PyErr_SetString(PyExc_ValueError, "list exceeds capacity");
        return 0;
    }
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
        long v;
        if (!sem_read_long(PyList_GetItem(list, i), &v) || v < 0 || v > 0xFFFF) {
            free(arr);
            return 0;
        }
        arr[i] = (uint16_t)v;
    }
    *out = arr;
    *count = (uint16_t)n;
    return 1;
}

static int sem_alloc_uint32_list(PyObject *list, uint32_t **out,
                                 uint16_t *count) {
    Py_ssize_t n = PyList_Size(list);
    if (n > 0xFFFF) {
        PyErr_SetString(PyExc_ValueError, "list exceeds capacity");
        return 0;
    }
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
        long v;
        if (!sem_read_long(PyList_GetItem(list, i), &v) || v < 0 ||
            (unsigned long)v > 0xFFFFFFFFUL) {
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

    long v;
#define SEM_TOP_LONG(key, field) \
    if (!sem_read_long(PyDict_GetItemString(payload, key), &v)) { \
        gc_semantic_rules_free(rules); \
        return NULL; \
    } \
    rules->field = (uint16_t)v;
    if (!sem_read_long(PyDict_GetItemString(payload, "board_size"), &v)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->board_size = (uint8_t)v;
    SEM_TOP_LONG("repetition_limit", repetition_limit);
    SEM_TOP_LONG("max_ply", max_ply);
#undef SEM_TOP_LONG
    if (rules->board_size < 1 ||
        (uint32_t)rules->board_size * rules->board_size > GC_MAX_SQUARES) {
        PyErr_SetString(PyExc_ValueError, "semantic board size out of range");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    if (rules->max_ply > GC_MAX_PLY) {
        PyErr_SetString(PyExc_ValueError, "semantic max_ply out of range");
        gc_semantic_rules_free(rules);
        return NULL;
    }

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
    rules->type_count = (uint16_t)PyList_Size(list_obj);
    if (rules->type_count > GC_MAX_TYPES) {
        PyErr_SetString(PyExc_ValueError, "too many semantic types");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    for (uint16_t t = 0; t < rules->type_count; t++) {
        PyObject *td = PyList_GetItem(list_obj, t);
        if (!PyDict_Check(td)) {
            PyErr_SetString(PyExc_ValueError, "type entry must be a dict");
            gc_semantic_rules_free(rules);
            return NULL;
        }
        long anchor, promotable;
        if (!sem_read_long(PyDict_GetItemString(td, "is_anchor"), &anchor) ||
            !sem_read_long(PyDict_GetItemString(td, "is_promotable"), &promotable)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        rules->types[t].is_anchor = (uint8_t)anchor;
        rules->types[t].is_promotable = (uint8_t)promotable;
        PyObject *targets = NULL;
        if (!sem_get_list(td, "promo_targets", &targets)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        Py_ssize_t tc = PyList_Size(targets);
        if (tc > GC_MAX_PROMO_TARGETS) {
            PyErr_SetString(PyExc_ValueError, "too many promotion targets");
            gc_semantic_rules_free(rules);
            return NULL;
        }
        rules->types[t].promo_target_count = (uint8_t)tc;
        for (Py_ssize_t i = 0; i < tc; i++) {
            long ti;
            if (!sem_read_long(PyList_GetItem(targets, i), &ti)) {
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

    if (!sem_get_list(payload, "alive_promo", &list_obj)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    if (PyList_Size(list_obj) != rules->type_count) {
        PyErr_SetString(PyExc_ValueError, "alive_promo count mismatch");
        gc_semantic_rules_free(rules);
        return NULL;
    }
    uint16_t squares = (uint16_t)(rules->board_size * rules->board_size);
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
                long mask;
                if (!sem_read_long(PyList_GetItem(masks, sq), &mask)) {
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
                rules->alive_promo[t][o][sq] = (uint64_t)mask;
            }
        }
    }

    /* geometries */
    if (!sem_get_list(payload, "geometries", &list_obj)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->geometry_count = (uint16_t)PyList_Size(list_obj);
    if (rules->geometry_count > GC_SEM_MAX_GEOMETRIES) {
        PyErr_SetString(PyExc_ValueError, "too many semantic geometries");
        gc_semantic_rules_free(rules);
        return NULL;
    }
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
        long kind, min_steps;
        if (!sem_read_long(PyDict_GetItemString(gd, "kind"), &kind)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        rules->geometries[g].kind = (uint8_t)kind;
        if (!sem_optional_long(gd, "min_steps", &rules->geometries[g].has_min_steps,
                               &min_steps)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        if (rules->geometries[g].has_min_steps) {
            rules->geometries[g].min_steps = (int16_t)min_steps;
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
            long ti, ai;
            if (!sem_read_long(PyList_GetItem(asrc, 0), &ti) ||
                !sem_read_long(PyList_GetItem(asrc, 1), &ai)) {
                gc_semantic_rules_free(rules);
                return NULL;
            }
            rules->geometries[g].has_atom_source = 1;
            rules->geometries[g].atom_source_type = (uint16_t)ti;
            rules->geometries[g].atom_source_index = (uint16_t)ai;
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
            Py_ssize_t n = PyList_Size(owner_entries);
            if (n > 0) {
                rules->geometries[g].paths[o].entries =
                    (GCSemPathEntry *)calloc((size_t)n, sizeof(GCSemPathEntry));
                if (rules->geometries[g].paths[o].entries == NULL) {
                    PyErr_NoMemory();
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
                rules->geometries[g].paths[o].count = (uint16_t)n;
            }
            for (Py_ssize_t i = 0; i < n; i++) {
                PyObject *entry = PyList_GetItem(owner_entries, i);
                if (!PyList_Check(entry) || PyList_Size(entry) != 2) {
                    PyErr_SetString(PyExc_ValueError,
                                    "path entry must be [source, squares]");
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
                long source;
                if (!sem_read_long(PyList_GetItem(entry, 0), &source)) {
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
                GCSemPathEntry *pe = &rules->geometries[g].paths[o].entries[i];
                pe->source = (uint16_t)source;
                PyObject *sqs = PyList_GetItem(entry, 1);
                if (!sem_alloc_uint16_list(sqs, &pe->squares, &pe->count, 0xFFFF)) {
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
        }
    }

    /* zones */
    if (!sem_get_list(payload, "zones", &list_obj)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->zone_count = (uint16_t)PyList_Size(list_obj);
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
    }

    /* aux slots */
    if (!sem_get_list(payload, "aux_slots", &list_obj)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->aux_slot_count = (uint8_t)PyList_Size(list_obj);
    if (rules->aux_slot_count > GC_SEM_MAX_AUX_SLOTS) {
        PyErr_SetString(PyExc_ValueError, "too many semantic aux slots");
        gc_semantic_rules_free(rules);
        return NULL;
    }
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
        long sid, vk, sc, lt;
        if (!PyDict_Check(ad) ||
            !sem_read_long(PyDict_GetItemString(ad, "slot_id"), &sid) ||
            !sem_read_long(PyDict_GetItemString(ad, "value_kind"), &vk) ||
            !sem_read_long(PyDict_GetItemString(ad, "scope"), &sc) ||
            !sem_read_long(PyDict_GetItemString(ad, "lifetime"), &lt)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        rules->aux_slots[a].slot_id = (uint16_t)sid;
        rules->aux_slots[a].value_kind = (uint8_t)vk;
        rules->aux_slots[a].scope = (uint8_t)sc;
        rules->aux_slots[a].lifetime = (uint8_t)lt;
        PyObject *init = PyDict_GetItemString(ad, "initial");
        if (init == NULL) {
            PyErr_SetString(PyExc_ValueError, "missing aux initial");
            gc_semantic_rules_free(rules);
            return NULL;
        }
        if (init == Py_None) {
            rules->aux_slots[a].initial_kind = 0;
        } else if (PyLong_Check(init)) {
            long iv;
            if (!sem_read_long(init, &iv)) {
                gc_semantic_rules_free(rules);
                return NULL;
            }
            rules->aux_slots[a].initial_kind = 1;
            rules->aux_slots[a].initial_int = (int32_t)iv;
        } else if (PyList_Check(init) && PyList_Size(init) == 2) {
            long f, r;
            if (!sem_read_long(PyList_GetItem(init, 0), &f) ||
                !sem_read_long(PyList_GetItem(init, 1), &r)) {
                gc_semantic_rules_free(rules);
                return NULL;
            }
            rules->aux_slots[a].initial_kind = 2;
            rules->aux_slots[a].initial_file = (uint16_t)f;
            rules->aux_slots[a].initial_rank = (uint16_t)r;
        } else {
            PyErr_SetString(PyExc_ValueError, "invalid aux initial");
            gc_semantic_rules_free(rules);
            return NULL;
        }
    }

    /* triggers */
    if (!sem_get_list(payload, "triggers", &list_obj)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->trigger_count = (uint16_t)PyList_Size(list_obj);
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
        long sid, ev, own;
        if (!PyDict_Check(td) ||
            !sem_read_long(PyDict_GetItemString(td, "slot_id"), &sid) ||
            !sem_read_long(PyDict_GetItemString(td, "event"), &ev) ||
            !sem_read_long(PyDict_GetItemString(td, "owner"), &own)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        rules->triggers[t].slot_id = (uint16_t)sid;
        rules->triggers[t].event = (uint8_t)ev;
        rules->triggers[t].owner = (uint8_t)own;
        PyObject *sr = PyDict_GetItemString(td, "square_ref");
        if (!PyDict_Check(sr) ||
            !sem_parse_square_ref(sr, &rules->triggers[t].square_ref)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
    }

    /* patterns */
    if (!sem_get_list(payload, "patterns", &list_obj)) {
        gc_semantic_rules_free(rules);
        return NULL;
    }
    rules->pattern_count = (uint16_t)PyList_Size(list_obj);
    if (rules->pattern_count > GC_SEM_MAX_PATTERNS) {
        PyErr_SetString(PyExc_ValueError, "too many semantic patterns");
        gc_semantic_rules_free(rules);
        return NULL;
    }
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
        if (!sem_get_list(pd, "type_indices", &sub) ||
            !sem_alloc_uint16_list(sub, &pat->type_indices, &pat->type_count, 0xFF)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        if (!sem_get_list(pd, "geometry_indices", &sub) ||
            !sem_alloc_uint16_list(sub, &pat->geometry_indices,
                                   &pat->geometry_count, 0xFF)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        long target, pmode, cost, stratum;
        if (!sem_read_long(PyDict_GetItemString(pd, "target"), &target) ||
            !sem_read_long(PyDict_GetItemString(pd, "promotion_mode"), &pmode) ||
            !sem_read_long(PyDict_GetItemString(pd, "cost"), &cost) ||
            !sem_read_long(PyDict_GetItemString(pd, "stratum"), &stratum)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        pat->target = (uint8_t)target;
        pat->promotion_mode = (uint8_t)pmode;
        pat->cost = (uint8_t)cost;
        pat->stratum = (uint8_t)stratum;
        if (!sem_optional_long(pd, "explicit_promotion_type",
                               &pat->has_explicit_promotion, &v)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        if (pat->has_explicit_promotion) {
            pat->explicit_promotion_type = (uint16_t)v;
        }

        /* path / guards / slot_guards / effects / invariants / postconditions */
        if (!sem_get_list(pd, "path", &sub)) {
            gc_semantic_rules_free(rules);
            return NULL;
        }
        {
            Py_ssize_t n = PyList_Size(sub);
            if (n > 0xFF) {
                PyErr_SetString(PyExc_ValueError, "pattern path too large");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            pat->path_count = (uint8_t)n;
            if (n > 0) {
                pat->path = (GCSemPathPredicate *)calloc((size_t)n, sizeof(GCSemPathPredicate));
                if (pat->path == NULL) {
                    PyErr_NoMemory();
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
            for (Py_ssize_t i = 0; i < n; i++) {
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
            Py_ssize_t n = PyList_Size(sub);
            if (n > 0xFF) {
                PyErr_SetString(PyExc_ValueError, "pattern guards too large");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            pat->guard_count = (uint8_t)n;
            if (n > 0) {
                pat->guards = (GCSemStateGuard *)calloc((size_t)n, sizeof(GCSemStateGuard));
                if (pat->guards == NULL) {
                    PyErr_NoMemory();
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
            for (Py_ssize_t i = 0; i < n; i++) {
                if (!sem_parse_state_guard(PyList_GetItem(sub, i), &pat->guards[i])) {
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
            Py_ssize_t n = PyList_Size(sub);
            if (n > 0xFF) {
                PyErr_SetString(PyExc_ValueError, "pattern slot_guards too large");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            pat->slot_guard_count = (uint8_t)n;
            if (n > 0) {
                pat->slot_guards = (GCSemSlotGuard *)calloc((size_t)n, sizeof(GCSemSlotGuard));
                if (pat->slot_guards == NULL) {
                    PyErr_NoMemory();
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
            for (Py_ssize_t i = 0; i < n; i++) {
                if (!sem_parse_slot_guard(PyList_GetItem(sub, i), &pat->slot_guards[i])) {
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
            Py_ssize_t n = PyList_Size(sub);
            if (n > GC_SEM_MAX_EFFECTS) {
                PyErr_SetString(PyExc_ValueError, "pattern effects exceed 4");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            pat->effect_count = (uint8_t)n;
            if (n > 0) {
                pat->effects = (GCSemEffect *)calloc((size_t)n, sizeof(GCSemEffect));
                if (pat->effects == NULL) {
                    PyErr_NoMemory();
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
            for (Py_ssize_t i = 0; i < n; i++) {
                if (!sem_parse_effect(PyList_GetItem(sub, i), &pat->effects[i])) {
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
            Py_ssize_t n = PyList_Size(sub);
            if (n > 0xFF) {
                PyErr_SetString(PyExc_ValueError, "pattern invariants too large");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            pat->invariant_count = (uint8_t)n;
            if (n > 0) {
                pat->invariants = (GCSemInvariant *)calloc((size_t)n, sizeof(GCSemInvariant));
                if (pat->invariants == NULL) {
                    PyErr_NoMemory();
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
            for (Py_ssize_t i = 0; i < n; i++) {
                if (!sem_parse_invariant(PyList_GetItem(sub, i), &pat->invariants[i])) {
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
            Py_ssize_t n = PyList_Size(sub);
            if (n > 0xFF) {
                PyErr_SetString(PyExc_ValueError, "pattern postconditions too large");
                gc_semantic_rules_free(rules);
                return NULL;
            }
            pat->postcondition_count = (uint8_t)n;
            if (n > 0) {
                pat->postconditions = (GCSemPostcondition *)calloc(
                    (size_t)n, sizeof(GCSemPostcondition));
                if (pat->postconditions == NULL) {
                    PyErr_NoMemory();
                    gc_semantic_rules_free(rules);
                    return NULL;
                }
            }
            for (Py_ssize_t i = 0; i < n; i++) {
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
    if (tr == NULL || sp == NULL) {
        Py_XDECREF(tr);
        Py_XDECREF(sp);
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
        sp,
        PyLong_FromUnsignedLong(g->comparison),
        PyLong_FromLong(g->value),
    };
    const char *keys[] = {
        "aggregation", "owner", "type_ref", "compare_field", "promoted",
        "location", "spatial", "comparison", "value",
    };
    for (int i = 0; i < 9; i++) {
        if (items[i] == NULL ||
            PyDict_SetItemString(d, keys[i], items[i]) != 0) {
            for (int j = 0; j < 9; j++) {
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

    SEM_INFO_SET("semantic_payload_version", PyLong_FromLong(1));
    SEM_INFO_SET("fingerprint", PyUnicode_FromString(rules->fingerprint));
    SEM_INFO_SET("board_size", PyLong_FromUnsignedLong(rules->board_size));
    SEM_INFO_SET("repetition_limit", PyLong_FromUnsignedLong(rules->repetition_limit));
    SEM_INFO_SET("max_ply", PyLong_FromUnsignedLong(rules->max_ply));

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
