#pragma once

#if defined(CCTBX_FAST_LINALG_USES_OPENBLAS)
#include <openblas/cblas.h>
#else
#error No CBLAS has been configured
#endif
