#include "monotonic.h"
#include <3ds.h>
double monotonic_seconds(void)
{
    return (double)svcGetSystemTick() / (double)SYSCLOCK_ARM11;
}
