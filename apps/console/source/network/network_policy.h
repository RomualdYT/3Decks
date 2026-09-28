#pragma once
#include <stdbool.h>

#define CONNECT_TIMEOUT_SECONDS 8.0
#define HELLO_TIMEOUT_SECONDS 8.0
#define HEARTBEAT_INTERVAL_SECONDS 5.0
#define HEARTBEAT_TIMEOUT_SECONDS 15.0

/* Absolute monotonic timestamps, independent of animation frame clamping. */
static inline bool deadline_reached(double now, double deadline)
{
    return now >= deadline;
}
static inline double network_retry_delay(int attempt)
{
    static const double delays[] = {2.0, 4.0, 8.0, 15.0, 30.0};
    return delays[attempt < 0 ? 0 : attempt > 4 ? 4 : attempt];
}
