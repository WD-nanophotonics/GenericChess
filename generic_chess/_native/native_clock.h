#ifndef GENERIC_CHESS_NATIVE_CLOCK_H
#define GENERIC_CHESS_NATIVE_CLOCK_H

#include <stdint.h>

/* Monotonic clock in nanoseconds (Windows QPC / POSIX CLOCK_MONOTONIC).
 * Never wall-clock or CPU time. */
uint64_t gc_monotonic_ns(void);

/* Saturation-safe deadline addition. */
uint64_t gc_deadline_after(uint64_t now_ns, uint64_t duration_ns);

#endif /* GENERIC_CHESS_NATIVE_CLOCK_H */
