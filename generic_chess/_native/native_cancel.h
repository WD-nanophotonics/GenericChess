#ifndef GENERIC_CHESS_NATIVE_CANCEL_H
#define GENERIC_CHESS_NATIVE_CANCEL_H

#include <stdatomic.h>
#include <stdint.h>

typedef struct {
    atomic_uint cancelled;
} GCCancelFlag;

GCCancelFlag *gc_cancel_flag_create(void);
void gc_cancel_flag_request(GCCancelFlag *flag);
int gc_cancel_flag_is_requested(const GCCancelFlag *flag);
void gc_cancel_flag_destroy(GCCancelFlag *flag);

#endif /* GENERIC_CHESS_NATIVE_CANCEL_H */
