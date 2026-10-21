#ifndef GC_NATIVE_PAYLOAD_H
#define GC_NATIVE_PAYLOAD_H
#include <Python.h>
/* Borrowed Python-owned names; no module/position/history cache or C globals. */
PyObject *gc_semantic_core_payload(PyObject *, PyObject *);
#endif
