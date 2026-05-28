package com.freesystemdoctor.android.ui.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Apps
import androidx.compose.material.icons.filled.CleaningServices
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.GridView
import androidx.compose.material.icons.filled.PieChart
import androidx.compose.ui.graphics.vector.ImageVector
import com.freesystemdoctor.android.R

enum class FsdDestination(
    val route: String,
    val labelRes: Int,
    val icon: ImageVector,
) {
    DASHBOARD("dashboard", R.string.nav_dashboard, Icons.Filled.Dashboard),
    CLEANER("cleaner", R.string.nav_cleaner, Icons.Filled.CleaningServices),
    STORAGE("storage", R.string.nav_storage, Icons.Filled.PieChart),
    APPS("apps", R.string.nav_apps, Icons.Filled.Apps),
    TOOLS("tools", R.string.nav_tools, Icons.Filled.GridView),
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
}
