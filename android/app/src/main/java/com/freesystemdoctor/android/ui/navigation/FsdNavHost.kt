package com.freesystemdoctor.android.ui.navigation

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.res.stringResource
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.ui.apps.AppUsageScreen
import com.freesystemdoctor.android.ui.apps.ApkExtractorScreen
import com.freesystemdoctor.android.ui.apps.AppsScreen
import com.freesystemdoctor.android.ui.apps.PermissionAuditScreen
import com.freesystemdoctor.android.ui.apps.RarelyUsedScreen
import com.freesystemdoctor.android.ui.assistant.AssistantScreen
import com.freesystemdoctor.android.ui.cleaner.CleanerScreen
import com.freesystemdoctor.android.ui.dashboard.DashboardScreen
import com.freesystemdoctor.android.ui.duplicates.DuplicatesScreen
import com.freesystemdoctor.android.ui.largefiles.LargeFilesScreen
import com.freesystemdoctor.android.ui.settings.SettingsScreen
import com.freesystemdoctor.android.ui.storage.StorageByTypeScreen
import com.freesystemdoctor.android.ui.storage.StorageScreen
import com.freesystemdoctor.android.ui.system.ClipboardScreen
import com.freesystemdoctor.android.ui.tools.ScheduleScreen
import com.freesystemdoctor.android.ui.tools.ToolsScreen
import com.freesystemdoctor.android.ui.theme.appBackgroundBrush

private val toolTitles: Map<String, Int> = mapOf(
    ToolRoutes.DUPLICATES to R.string.tool_duplicates,
    ToolRoutes.LARGE_FILES to R.string.tool_large_files,
    ToolRoutes.STORAGE_TYPES to R.string.tool_storage_types,
    ToolRoutes.APP_USAGE to R.string.tool_app_usage,
    ToolRoutes.RARELY_USED to R.string.tool_rarely_used,
    ToolRoutes.PERMISSIONS to R.string.tool_permissions,
    ToolRoutes.APK_EXTRACTOR to R.string.tool_apk,
    ToolRoutes.CLIPBOARD to R.string.tool_clipboard,
    ToolRoutes.SCHEDULE to R.string.tool_schedule,
    ToolRoutes.ASSISTANT to R.string.nav_assistant,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScaffold() {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route
    val dark = MaterialTheme.colorScheme.background.luminance() < 0.5f
    val isLeaf = currentRoute == ROUTE_SETTINGS || currentRoute?.startsWith("tool/") == true

    val title = when {
        currentRoute == ROUTE_SETTINGS -> stringResource(R.string.settings_title)
        currentRoute != null && toolTitles.containsKey(currentRoute) ->
            stringResource(toolTitles.getValue(currentRoute))
        else -> FsdDestination.entries.firstOrNull { it.route == currentRoute }
            ?.let { stringResource(it.labelRes) }
            ?: stringResource(R.string.app_name)
    }

    Scaffold(
        containerColor = Color.Transparent,
        modifier = Modifier.background(appBackgroundBrush(dark)),
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text(title) },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = Color.Transparent,
                    titleContentColor = MaterialTheme.colorScheme.onBackground,
                ),
                navigationIcon = {
                    if (isLeaf) {
                        IconButton(onClick = { navController.popBackStack() }) {
                            Icon(
                                Icons.AutoMirrored.Filled.ArrowBack,
                                contentDescription = stringResource(R.string.action_back),
                            )
                        }
                    }
                },
                actions = {
                    IconButton(onClick = { navController.navigate(ROUTE_SETTINGS) }) {
                        Icon(Icons.Filled.Settings, contentDescription = stringResource(R.string.nav_settings))
                    }
                },
            )
        },
        bottomBar = {
            if (!isLeaf || currentRoute?.startsWith("tool/") == true) {
                NavigationBar(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.92f)) {
                    val destination = backStackEntry?.destination
                    FsdDestination.entries.forEach { dest ->
                        val selected = destination?.hierarchy?.any { it.route == dest.route } == true
                        val iconScale by animateFloatAsState(
                            targetValue = if (selected) 1.15f else 1f,
                            animationSpec = tween(260),
                            label = "navIcon",
                        )
                        NavigationBarItem(
                            selected = selected,
                            onClick = {
                                navController.navigate(dest.route) {
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = {
                                Icon(
                                    dest.icon,
                                    contentDescription = stringResource(dest.labelRes),
                                    modifier = Modifier.scale(iconScale),
                                )
                            },
                            label = { Text(stringResource(dest.labelRes)) },
                            colors = NavigationBarItemDefaults.colors(
                                selectedIconColor = MaterialTheme.colorScheme.primary,
                                selectedTextColor = MaterialTheme.colorScheme.primary,
                                indicatorColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.16f),
                            ),
                        )
                    }
                }
            }
        },
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = FsdDestination.DASHBOARD.route,
            modifier = Modifier.fillMaxSize().padding(innerPadding),
            enterTransition = { fadeIn(tween(300)) + slideInHorizontally(tween(320)) { it / 12 } },
            exitTransition = { fadeOut(tween(200)) + slideOutHorizontally(tween(320)) { -it / 12 } },
            popEnterTransition = { fadeIn(tween(300)) + slideInHorizontally(tween(320)) { -it / 12 } },
            popExitTransition = { fadeOut(tween(200)) + slideOutHorizontally(tween(320)) { it / 12 } },
        ) {
            composable(FsdDestination.DASHBOARD.route) { DashboardScreen() }
            composable(FsdDestination.CLEANER.route) { CleanerScreen() }
            composable(FsdDestination.STORAGE.route) { StorageScreen() }
            composable(FsdDestination.APPS.route) { AppsScreen() }
            composable(FsdDestination.TOOLS.route) {
                ToolsScreen(onOpen = { navController.navigate(it) })
            }
            composable(ROUTE_SETTINGS) { SettingsScreen() }

            composable(ToolRoutes.DUPLICATES) { DuplicatesScreen() }
            composable(ToolRoutes.LARGE_FILES) { LargeFilesScreen() }
            composable(ToolRoutes.STORAGE_TYPES) { StorageByTypeScreen() }
            composable(ToolRoutes.APP_USAGE) { AppUsageScreen() }
            composable(ToolRoutes.RARELY_USED) { RarelyUsedScreen() }
            composable(ToolRoutes.PERMISSIONS) { PermissionAuditScreen() }
            composable(ToolRoutes.APK_EXTRACTOR) { ApkExtractorScreen() }
            composable(ToolRoutes.CLIPBOARD) { ClipboardScreen() }
            composable(ToolRoutes.SCHEDULE) { ScheduleScreen() }
            composable(ToolRoutes.ASSISTANT) { AssistantScreen() }
        }
    }
}
