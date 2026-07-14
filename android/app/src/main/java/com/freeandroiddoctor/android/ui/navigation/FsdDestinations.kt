package com.freeandroiddoctor.android.ui.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Apps
import androidx.compose.material.icons.filled.CleaningServices
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.GridView
import androidx.compose.material.icons.filled.PieChart
import androidx.compose.ui.graphics.vector.ImageVector
import com.freeandroiddoctor.android.R

enum class FsdDestination(
    val route: String,
    val labelRes: Int,
    val icon: ImageVector,
) {
    DASHBOARD("dashboard", R.string.nav_dashboard, Icons.Filled.Dashboard),
    CLEANER("cleaner", R.string.nav_cleaner, Icons.Filled.CleaningServices),
    APPS("apps", R.string.nav_apps, Icons.Filled.Apps),
    TOOLS("tools", R.string.nav_tools, Icons.Filled.GridView),
    STORAGE("storage", R.string.nav_storage, Icons.Filled.PieChart),
}

const val ROUTE_SETTINGS = "settings"
const val ROUTE_ONBOARDING = "onboarding"
const val ROUTE_PRO = "pro"

/** Leaf routes opened from the Tools hub (not shown in the bottom bar). */
object ToolRoutes {
    const val DUPLICATES = "tool/duplicates"
    const val LARGE_FILES = "tool/large_files"
    const val STORAGE_TYPES = "tool/storage_types"
    const val APP_USAGE = "tool/app_usage"
    const val RARELY_USED = "tool/rarely_used"
    const val PERMISSIONS = "tool/permissions"
    const val APK_EXTRACTOR = "tool/apk"
    const val CLIPBOARD = "tool/clipboard"
    const val SCHEDULE = "tool/schedule"
    const val ASSISTANT = "tool/assistant"
    const val FILES = "tool/files"
    const val DATA_USAGE = "tool/data_usage"
    const val DEVICE_INFO = "tool/device"
    const val SHREDDER = "tool/shredder"
    const val TWEAKS = "tool/tweaks"
    const val SIMILAR_PHOTOS = "tool/similar_photos"
    const val PHOTO_REVIEW = "tool/photo_review"
    const val COMPRESS = "tool/compress"
    const val WIFI = "tool/wifi"
    const val NOTIFICATIONS = "tool/notifications"
    const val SPEED_TEST = "tool/speed_test"
    const val BATTERY = "tool/battery"
    const val MEMORY = "tool/memory"
    const val BACKUP = "tool/backup"
    const val RECYCLE_BIN = "tool/recycle_bin"
    const val HIDDEN_CACHE = "tool/hidden_cache"
    const val APP_VAULT = "tool/app_vault"
    const val BATTERY_ALARMS = "tool/battery_alarms"
    const val APP_INSIGHTS = "tool/app_insights"
    const val APP_RESOURCE = "tool/app_resource"
    const val STORAGE_FORECAST = "tool/storage_forecast"
    const val FOCUS = "tool/focus"
    const val APP_LOCK = "tool/app_lock"
    const val CLOUD_BACKUP = "tool/cloud_backup"
    const val RESTORE_WIZARD = "tool/restore_wizard"
    const val GAME_BOOST = "tool/game_boost"
    const val CLEANING_HISTORY = "tool/cleaning_history"
    const val CORPSE_FINDER = "tool/corpse_finder"
    const val APP_DEEP_CLEAN = "tool/app_deep_clean"
    const val APP_CLEANERS_HUB = "tool/app_cleaners_hub"
    const val APP_CLEANER_WHATSAPP = "tool/app_cleaner_whatsapp"
    const val APP_CLEANER_TELEGRAM = "tool/app_cleaner_telegram"
    const val APP_CLEANER_DISCORD = "tool/app_cleaner_discord"
    const val APP_CLEANER_TIKTOK = "tool/app_cleaner_tiktok"
    const val BATTERY_HEALTH = "tool/battery_health"
    const val CHARGING_LOG = "tool/charging_log"
    const val BATTERY_DRAIN = "tool/battery_drain"
    const val STORAGE_TREEMAP = "tool/storage_treemap"
    const val NOTIFICATION_STATS = "tool/notification_stats"

    // Update 14: Privacy, Modes & Auto-Rules
    const val PRIVACY_AUDIT = "tool/privacy_audit"
    const val PRIVACY_PROFILES = "tool/privacy_profiles"
    const val BROWSER_DATA = "tool/browser_data"
    const val MODES = "tool/modes"
    const val AUTO_RULES = "tool/auto_rules"
}
