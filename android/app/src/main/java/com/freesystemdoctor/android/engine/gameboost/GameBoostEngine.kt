package com.freesystemdoctor.android.engine.gameboost

import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Build
import android.os.PowerManager
import com.freesystemdoctor.android.engine.cache.JunkScannerEngine
import com.freesystemdoctor.android.engine.memory.MemoryEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class InstalledGame(
    val packageName: String,
    val label: String,
)

data class BoostResult(
    val ramFreedBytes: Long,
    val cacheFreedBytes: Long,
    val dndApplied: Boolean,
    val gameLaunched: Boolean,
    val sustainedPerformanceSupported: Boolean,
)

/**
 * Orchestrates a one-tap "Game Boost": free background RAM, purge own cache, optionally enter
 * DND, optionally launch a game. All steps return *real measured* numbers — no fake FPS or
 * inflated boost percentages (honest brand). DND is owned by [FocusEngine]; the session
 * lifecycle (notification + DND restore on end) is owned by [GameBoostService].
 *
 * What we deliberately do NOT do (Android limits without root): change CPU governor, raise
 * clocks, set thermal mode beyond the app's own window, or "boost FPS".
 */
class GameBoostEngine(
    private val context: Context,
    private val memory: MemoryEngine,
    private val junk: JunkScannerEngine,
) {

    suspend fun listInstalledGames(): List<InstalledGame> = withContext(Dispatchers.IO) {
        val pm = context.packageManager
        val seen = mutableSetOf<String>()
        val games = mutableListOf<InstalledGame>()

        // 1) Apps that declare themselves as games (Android 8+).
        pm.getInstalledApplications(0).forEach { ai ->
            if (ai.packageName == context.packageName) return@forEach
            val isGame = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                ai.category == ApplicationInfo.CATEGORY_GAME
            } else {
                @Suppress("DEPRECATION")
                (ai.flags and ApplicationInfo.FLAG_IS_GAME) != 0
            }
            if (isGame && seen.add(ai.packageName)) {
                val label = runCatching { pm.getApplicationLabel(ai).toString() }
                    .getOrDefault(ai.packageName)
                games.add(InstalledGame(ai.packageName, label))
            }
        }
        games.sortedBy { it.label.lowercase() }
    }

    suspend fun listAllInstalledApps(): List<InstalledGame> = withContext(Dispatchers.IO) {
        val pm = context.packageManager
        pm.getInstalledApplications(0)
            .asSequence()
            .filter { it.packageName != context.packageName }
            .filter { pm.getLaunchIntentForPackage(it.packageName) != null }
            .map { ai ->
                val label = runCatching { pm.getApplicationLabel(ai).toString() }
                    .getOrDefault(ai.packageName)
                InstalledGame(ai.packageName, label)
            }
            .sortedBy { it.label.lowercase() }
            .toList()
    }

    /**
     * Performs the boost. Caller is responsible for DND (via [GameBoostService]) — this
     * engine only frees RAM + purges this-app cache and returns honest deltas.
     */
    suspend fun runBoost(): BoostResult = withContext(Dispatchers.IO) {
        val ramFreed = runCatching { memory.freeBackground() }.getOrDefault(0L)
        val cacheFreed = runCatching { junk.cleanAppCache().bytesFreed }.getOrDefault(0L)
        BoostResult(
            ramFreedBytes = ramFreed,
            cacheFreedBytes = cacheFreed,
            dndApplied = false,
            gameLaunched = false,
            sustainedPerformanceSupported = sustainedPerformanceSupported(),
        )
    }

    fun sustainedPerformanceSupported(): Boolean {
        val pm = context.getSystemService(Context.POWER_SERVICE) as? PowerManager ?: return false
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            pm.isSustainedPerformanceModeSupported
        } else false
    }

    fun launchIntent(packageName: String): Intent? =
        context.packageManager.getLaunchIntentForPackage(packageName)
            ?.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
}
