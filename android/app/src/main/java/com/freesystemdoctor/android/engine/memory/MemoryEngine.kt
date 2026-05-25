package com.freesystemdoctor.android.engine.memory

import android.app.ActivityManager
import android.content.Context

data class MemoryInfo(
    val totalBytes: Long,
    val availableBytes: Long,
    val lowMemory: Boolean,
) {
    val usedBytes: Long get() = (totalBytes - availableBytes).coerceAtLeast(0)
    val usedFraction: Float
        get() = if (totalBytes <= 0) 0f else (usedBytes.toFloat() / totalBytes).coerceIn(0f, 1f)
}

/**
 * Reports real RAM usage. We intentionally do NOT ship a "RAM booster": on modern
 * Android killing background processes is ineffective (the system re-spawns them and
 * apps reload), so we only surface honest numbers.
 */
class MemoryEngine(private val context: Context) {

    fun read(): MemoryInfo {
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val info = ActivityManager.MemoryInfo()
        am.getMemoryInfo(info)
        return MemoryInfo(
            totalBytes = info.totalMem,
            availableBytes = info.availMem,
            lowMemory = info.lowMemory,
        )
    }
}
