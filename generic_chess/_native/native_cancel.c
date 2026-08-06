#include "native_cancel.h"

#include <stdlib.h>

GCCancelFlag *gc_cancel_flag_create(void) {
    GCCancelFlag *flag = (GCCancelFlag *)calloc(1, sizeof(GCCancelFlag));
    if (flag == NULL) {
        return NULL;
    }
    atomic_init(&flag->cancelled, 0u);
    return flag;
}

void gc_cancel_flag_request(GCCancelFlag *flag) {
    if (flag == NULL) {
        return;
    }
    atomic_store(&flag->cancelled, 1u);
}

int gc_cancel_flag_is_requested(const GCCancelFlag *flag) {
    if (flag == NULL) {
        return 0;
    }
    return atomic_load(&flag->cancelled) != 0u;
}

void gc_cancel_flag_destroy(GCCancelFlag *flag) {
    free(flag);
}
