package com.freesystemdoctor.android.ui.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Apps
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CleaningServices
import androidx.compose.material.icons.filled.Dashboard
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
    ASSISTANT("assistant", R.string.nav_assistant, Icons.Filled.AutoAwesome),
}

const val ROUTE_SETTINGS = "settings"
const val ROUTE_ONBOARDING = "onboarding"
