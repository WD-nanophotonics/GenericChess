#include "native_clock.h"

#ifdef _WIN32
#include <windows.h>
#else
#include <time.h>
#endif

uint64_t gc_monotonic_ns(void) {
#ifdef _WIN32
    static LARGE_INTEGER freq;
    static int init = 0;
    LARGE_INTEGER now;
    if (!init) {
        QueryPerformanceFrequency(&freq);
        init = 1;
    }
    QueryPerformanceCounter(&now);
    if (freq.QuadPart > 0) {
        return (uint64_t)(now.QuadPart * 1000000000LL / freq.QuadPart);
    }
    return 0;
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
#endif
}

uint64_t gc_deadline_after(uint64_t now_ns, uint64_t duration_ns) {
    if (duration_ns > UINT64_MAX - now_ns) {
        return UINT64_MAX;
    }
    return now_ns + duration_ns;
}
