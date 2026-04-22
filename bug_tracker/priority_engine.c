/*
 * priority_engine.c  —  Bug Priority Scoring Engine
 * ===================================================
 * Compiled as a shared library and called from Python via ctypes.
 *
 * Compile (Windows — MinGW-w64):
 *     gcc -shared -o priority_engine.dll priority_engine.c -lm
 *
 * Compile (Linux / macOS):
 *     gcc -shared -fPIC -o priority_engine.so priority_engine.c -lm
 *
 * Score formula  (max = 100.0):
 *     score = (severity_weight × 40)
 *           + (age_factor      × 35)
 *           + (freq_factor     × 25)
 *
 *   severity_weight = severity / 4.0         → contributes  0 – 40 pts
 *   age_factor      = min(age_days/30, 1.0)  → contributes  0 – 35 pts (cap at 30 days)
 *   freq_factor     = min(related/5,   1.0)  → contributes  0 – 25 pts (cap at 5 bugs)
 *
 * Cyclomatic complexity  V(G) = 2  (one decision: guard clause for invalid input).
 */

#include <math.h>   /* fmin() */

/**
 * calculate_priority – Compute a weighted urgency score for a bug report.
 *
 * @severity:      Severity level.  Valid range: 1 (Low) … 4 (Critical).
 * @age_days:      Days elapsed since the bug was first reported.  Must be ≥ 0.
 * @related_count: Number of related / duplicate bugs linked to this report.  Must be ≥ 0.
 *
 * Return:
 *   A double in [0.0, 100.0].  Higher = more urgent.
 *   Returns 0.0 for any out-of-range argument (safe failure).
 *
 * Examples:
 *   calculate_priority(4, 30, 5)  →  100.0   (worst case)
 *   calculate_priority(3, 15, 2)  →   57.50
 *   calculate_priority(1,  0, 0)  →   10.0   (best case, just reported)
 */
double calculate_priority(int severity, int age_days, int related_count)
{
    /* Guard: return 0.0 for invalid inputs instead of producing garbage */
    if (severity < 1 || severity > 4 || age_days < 0 || related_count < 0) {
        return 0.0;
    }

    double severity_weight = severity / 4.0;              /* 0.25 – 1.0  */
    double age_factor      = fmin(age_days / 30.0, 1.0); /* 0.0  – 1.0  */
    double freq_factor     = fmin(related_count / 5.0, 1.0); /* 0.0  – 1.0  */

    return (severity_weight * 40.0)
         + (age_factor      * 35.0)
         + (freq_factor     * 25.0);
}
