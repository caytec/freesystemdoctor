package com.freeandroiddoctor.android.engine.memory

import android.app.ActivityManager
import android.content.Context
import android.content.pm.ApplicationInfo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

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

    /**
     * Asks the system to drop cached background processes for third-party apps.
     * Honest note: on modern Android the OS re-spawns/re-caches apps quickly, so the
     * reclaimed amount is usually small and temporary — we report the real delta, not
     * an inflated "boosted" number. Returns bytes that became available (may be 0).
     */
    suspend fun freeBackground(): Long = withContext(Dispatchers.IO) {
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val before = read().availableBytes
        runCatching {
            context.packageManager.getInstalledApplications(0)
                .asSequence()
                .filter { (it.flags and ApplicationInfo.FLAG_SYSTEM) == 0 }
                .filter { it.packageName != context.packageName }
                .forEach { am.killBackgroundProcesses(it.packageName) }
        }
        (read().availableBytes - before).coerceAtLeast(0)
    }
}
