package com.freeandroiddoctor.android.engine.organizer

import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Build
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.io.File
import kotlin.coroutines.coroutineContext

/**
 * Auto-detected (or manually overridden) grouping bucket for an installed app. Deliberately
 * limited to what Android actually signals — [ApplicationInfo.category] and the standard
 * `Intent.CATEGORY_APP_*` "default app" probes — no hardcoded package-name guesswork.
 */
enum class AppCategory {
    GAMES, SOCIAL, PHOTO_VIDEO, MUSIC_AUDIO, NEWS, MAPS, PRODUCTIVITY, TOOLS, OTHER
}

data class OrganizedApp(
    val packageName: String,
    val label: String,
    val category: AppCategory,
    val isManualOverride: Boolean,
)

data class CategoryGroup(val category: AppCategory, val apps: List<OrganizedApp>)

data class OrganizerReport(val groups: List<CategoryGroup>)

@Serializable
private data class OverridesFile(val overrides: Map<String, String> = emptyMap())

/**
 * Groups installed apps into folder-like categories inside the app — the only place a
 * "folder" concept can honestly exist, since no third-party app can read or edit the real
 * home-screen launcher's layout. See OrganizerScreen for the pinned-shortcut companion
 * feature, which is the one legitimate way to put anything derived from this on the actual
 * home screen.
 */
class AppOrganizerEngine(private val context: Context) {

    private val dir = File(context.filesDir, "organizer").apply { mkdirs() }
    private val file = File(dir, "overrides.json")
    private val json = Json { ignoreUnknownKeys = true }
    private val mutex = Mutex()

    suspend fun organize(includeSystem: Boolean = false): OrganizerReport = withContext(Dispatchers.IO) {
        val pm = context.packageManager
        val overrides = mutex.withLock { read().overrides }
        val intentCategoryPackages = detectIntentCategoryPackages(pm)

        val installed = pm.getInstalledApplications(PackageManager.GET_META_DATA)
        val apps = ArrayList<OrganizedApp>(installed.size)
        installed.forEach { ai ->
            coroutineContext.ensureActive()
            if (ai.packageName == context.packageName) return@forEach
            val isSystem = (ai.flags and ApplicationInfo.FLAG_SYSTEM) != 0
            if (!includeSystem && isSystem) return@forEach
            if (pm.getLaunchIntentForPackage(ai.packageName) == null) return@forEach

            val override = overrides[ai.packageName]
                ?.let { runCatching { AppCategory.valueOf(it) }.getOrNull() }
            val category = override ?: categorize(ai, intentCategoryPackages)
            apps += OrganizedApp(
                packageName = ai.packageName,
                label = runCatching { pm.getApplicationLabel(ai).toString() }.getOrDefault(ai.packageName),
                category = category,
                isManualOverride = override != null,
            )
        }

        val groups = apps.groupBy { it.category }
            .map { (category, group) -> CategoryGroup(category, group.sortedBy { it.label.lowercase() }) }
            .sortedByDescending { it.apps.size }

        OrganizerReport(groups)
    }

    /** `null` clears the override and lets the app fall back to auto-detection. */
    suspend fun setManualCategory(packageName: String, category: AppCategory?) {
        withContext(Dispatchers.IO) {
            mutex.withLock {
                val current = read().overrides.toMutableMap()
                if (category == null) current.remove(packageName) else current[packageName] = category.name
                write(OverridesFile(current))
            }
        }
    }

    fun launchIntent(packageName: String): Intent? =
        context.packageManager.getLaunchIntentForPackage(packageName)

    private fun categorize(ai: ApplicationInfo, intentCategoryPackages: Map<String, AppCategory>): AppCategory {
        intentCategoryPackages[ai.packageName]?.let { return it }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            when (ai.category) {
                ApplicationInfo.CATEGORY_GAME -> return AppCategory.GAMES
                ApplicationInfo.CATEGORY_SOCIAL -> return AppCategory.SOCIAL
                ApplicationInfo.CATEGORY_IMAGE, ApplicationInfo.CATEGORY_VIDEO -> return AppCategory.PHOTO_VIDEO
                ApplicationInfo.CATEGORY_AUDIO -> return AppCategory.MUSIC_AUDIO
                ApplicationInfo.CATEGORY_NEWS -> return AppCategory.NEWS
                ApplicationInfo.CATEGORY_MAPS -> return AppCategory.MAPS
                ApplicationInfo.CATEGORY_PRODUCTIVITY -> return AppCategory.PRODUCTIVITY
            }
        } else {
            @Suppress("DEPRECATION")
            if ((ai.flags and ApplicationInfo.FLAG_IS_GAME) != 0) return AppCategory.GAMES
        }
        return AppCategory.OTHER
    }

    /**
     * Probes Android's standard "default app" intent categories (API 15+) — a real signal
     * declared in each app's own manifest, not a hardcoded package list. Covers common apps
     * (browsers, calculators, calendars...) that don't set [ApplicationInfo.category].
     */
    private fun detectIntentCategoryPackages(pm: PackageManager): Map<String, AppCategory> {
        val probes = listOf(
            Intent.CATEGORY_APP_BROWSER to AppCategory.TOOLS,
            Intent.CATEGORY_APP_CALCULATOR to AppCategory.TOOLS,
            Intent.CATEGORY_APP_CALENDAR to AppCategory.PRODUCTIVITY,
            Intent.CATEGORY_APP_CONTACTS to AppCategory.PRODUCTIVITY,
            Intent.CATEGORY_APP_EMAIL to AppCategory.PRODUCTIVITY,
            Intent.CATEGORY_APP_GALLERY to AppCategory.PHOTO_VIDEO,
            Intent.CATEGORY_APP_MAPS to AppCategory.MAPS,
            Intent.CATEGORY_APP_MESSAGING to AppCategory.SOCIAL,
            Intent.CATEGORY_APP_MUSIC to AppCategory.MUSIC_AUDIO,
        )
        val result = mutableMapOf<String, AppCategory>()
        probes.forEach { (intentCategory, category) ->
            val intent = Intent(Intent.ACTION_MAIN).addCategory(intentCategory)
            runCatching { pm.queryIntentActivities(intent, PackageManager.MATCH_DEFAULT_ONLY) }
                .getOrDefault(emptyList())
                .forEach { resolveInfo ->
                    val pkg = resolveInfo.activityInfo?.packageName ?: return@forEach
                    // First matching probe wins for a package — list order above is priority.
                    result.putIfAbsent(pkg, category)
                }
        }
        return result
    }

    private fun read(): OverridesFile =
        if (!file.exists()) {
            OverridesFile()
        } else {
            runCatching { json.decodeFromString<OverridesFile>(file.readText()) }.getOrElse { OverridesFile() }
        }

    private fun write(data: OverridesFile) {
        runCatching { file.writeText(json.encodeToString(OverridesFile.serializer(), data)) }
    }
}
