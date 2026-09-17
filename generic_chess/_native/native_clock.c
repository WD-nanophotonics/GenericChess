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
        /* Keep the intermediate multiplication below UINT64_MAX.  QPC ticks
         * are already large on long-lived Windows processes, so multiplying
         * the full counter by 1e9 first can wrap and produce bogus telemetry.
         */
        uint64_t ticks = (uint64_t)now.QuadPart;
        uint64_t frequency = (uint64_t)freq.QuadPart;
        return (ticks / frequency) * 1000000000ull +
               ((ticks % frequency) * 1000000000ull) / frequency;
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
