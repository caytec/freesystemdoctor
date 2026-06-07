package com.freesystemdoctor.android.engine.battery

data class BatteryHealthReport(
    /** Median measured capacity in mAh; null if too few qualifying sessions. */
    val measuredCapacityMah: Int?,
    /** Reference capacity used for "% of new" (largest observed if no design hint). */
    val referenceCapacityMah: Int?,
    val healthPercent: Int?,
    val sampleCount: Int,
)

/**
 * Estimates battery wear from real charging-session data. Per session,
 *   measuredCapacity ≈ estMahAdded / ((toPct - fromPct) / 100)
 * Only sessions with at least 40% delta are kept (smaller deltas amplify noise).
 * Sessions where current samples were obviously bogus (|currentMa| > 8000) are
 * rejected at sampling time, not here.
 *
 * Returns null when fewer than 3 qualifying sessions exist — never guess.
 */
class BatteryHealthEngine(
    private val sessionEngine: ChargingSessionEngine,
    private val batteryEngine: BatteryEngine,
) {

    suspend fun compute(): BatteryHealthReport {
        val all = sessionEngine.sessions()
        val qualifying = all.filter {
            (it.toPct - it.fromPct) >= MIN_DELTA_PCT && it.estMahAdded > 0
        }
        if (qualifying.size < MIN_SAMPLES) {
            return BatteryHealthReport(null, null, null, qualifying.size)
        }
        val measured = qualifying.map { s ->
            (s.estMahAdded.toDouble() / ((s.toPct - s.fromPct) / 100.0)).toInt()
        }.sorted()
        val median = measured[measured.size / 2]
        // Reference: try the BatteryManager design counter; otherwise use the largest measured value.
        val designHint = batteryEngine.read().chargeCounterMah?.takeIf { it > median }
        val reference = designHint ?: measured.maxOrNull() ?: median
        val healthPct = ((median.toDouble() / reference) * 100).toInt().coerceIn(0, 100)
        return BatteryHealthReport(
            measuredCapacityMah = median,
            referenceCapacityMah = reference,
            healthPercent = healthPct,
            sampleCount = qualifying.size,
        )
    }

    private companion object {
        const val MIN_DELTA_PCT = 40
        const val MIN_SAMPLES = 3
    }
}
