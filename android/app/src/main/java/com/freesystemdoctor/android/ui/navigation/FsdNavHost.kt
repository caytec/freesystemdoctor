package com.freesystemdoctor.android.ui.navigation

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.WorkspacePremium
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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.sp
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
import com.freesystemdoctor.android.ui.backup.BackupScreen
import com.freesystemdoctor.android.ui.battery.BatteryScreen
import com.freesystemdoctor.android.ui.cache.HiddenCacheScreen
import com.freesystemdoctor.android.ui.cleaner.CleanerScreen
import com.freesystemdoctor.android.ui.cloudbackup.CloudBackupScreen
import com.freesystemdoctor.android.ui.cloudbackup.RestoreWizardScreen
import com.freesystemdoctor.android.ui.focus.FocusScreen
import com.freesystemdoctor.android.ui.forecast.StorageForecastScreen
import com.freesystemdoctor.android.ui.appcleaners.AppCleanersHubScreen
import com.freesystemdoctor.android.ui.appcleaners.DiscordCleanerScreen
import com.freesystemdoctor.android.ui.appcleaners.TelegramCleanerScreen
import com.freesystemdoctor.android.ui.appcleaners.TikTokCleanerScreen
import com.freesystemdoctor.android.ui.appcleaners.WhatsAppCleanerScreen
import com.freesystemdoctor.android.ui.appdeep.AppDeepCleanScreen
import com.freesystemdoctor.android.ui.battery.charging.ChargingLogScreen
import com.freesystemdoctor.android.ui.battery.drain.BatteryDrainScreen
import com.freesystemdoctor.android.ui.battery.health.BatteryHealthScreen
import com.freesystemdoctor.android.ui.corpse.CorpseFinderScreen
import com.freesystemdoctor.android.ui.gameboost.GameBoostScreen
import com.freesystemdoctor.android.ui.history.CleaningHistoryScreen
import com.freesystemdoctor.android.ui.notifications.stats.NotificationStatsScreen
import com.freesystemdoctor.android.ui.storage.treemap.StorageTreemapScreen
import com.freesystemdoctor.android.ui.insights.AppInsightsScreen
import com.freesystemdoctor.android.ui.lock.AppLockScreen
import com.freesystemdoctor.android.ui.resource.AppResourceScreen
import com.freesystemdoctor.android.ui.tools.BatteryAlarmsScreen
import com.freesystemdoctor.android.ui.trash.TrashScreen
import com.freesystemdoctor.android.ui.vault.VaultScreen
import com.freesystemdoctor.android.ui.memory.MemoryScreen
import com.freesystemdoctor.android.ui.dashboard.DashboardScreen
import com.freesystemdoctor.android.ui.device.DeviceInfoScreen
import com.freesystemdoctor.android.ui.duplicates.DuplicatesScreen
import com.freesystemdoctor.android.ui.files.FolderToolsScreen
import com.freesystemdoctor.android.ui.files.ShredderScreen
import com.freesystemdoctor.android.ui.largefiles.LargeFilesScreen
import com.freesystemdoctor.android.ui.network.DataUsageScreen
import com.freesystemdoctor.android.ui.network.SpeedTestScreen
import com.freesystemdoctor.android.ui.network.WifiScreen
import com.freesystemdoctor.android.ui.notifications.NotificationCleanerScreen
import com.freesystemdoctor.android.ui.photos.CompressScreen
import com.freesystemdoctor.android.ui.photos.PhotoReviewScreen
import com.freesystemdoctor.android.ui.photos.SimilarPhotosScreen
import com.freesystemdoctor.android.ui.components.AnimatedBackdrop
import com.freesystemdoctor.android.ui.components.BannerAd
import com.freesystemdoctor.android.ui.components.UnlockSheetHost
import com.freesystemdoctor.android.ui.pro.ProScreen
import com.freesystemdoctor.android.ui.settings.SettingsScreen
import com.freesystemdoctor.android.ui.storage.StorageByTypeScreen
import com.freesystemdoctor.android.ui.storage.StorageScreen
import com.freesystemdoctor.android.ui.system.ClipboardScreen
import com.freesystemdoctor.android.ui.tools.ScheduleScreen
import com.freesystemdoctor.android.ui.tools.SystemTweaksScreen
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
    ToolRoutes.FILES to R.string.tool_files,
    ToolRoutes.DATA_USAGE to R.string.tool_data_usage,
    ToolRoutes.DEVICE_INFO to R.string.tool_device_info,
    ToolRoutes.SHREDDER to R.string.tool_shredder,
    ToolRoutes.TWEAKS to R.string.tool_tweaks,
    ToolRoutes.SIMILAR_PHOTOS to R.string.tool_similar,
    ToolRoutes.PHOTO_REVIEW to R.string.tool_photo_review,
    ToolRoutes.COMPRESS to R.string.tool_compress,
    ToolRoutes.WIFI to R.string.tool_wifi,
    ToolRoutes.NOTIFICATIONS to R.string.tool_notifications,
    ToolRoutes.SPEED_TEST to R.string.tool_speed,
    ToolRoutes.BATTERY to R.string.tool_battery,
    ToolRoutes.MEMORY to R.string.tool_memory,
    ToolRoutes.BACKUP to R.string.tool_backup,
    ToolRoutes.RECYCLE_BIN to R.string.tool_recycle_bin,
    ToolRoutes.HIDDEN_CACHE to R.string.tool_hidden_cache,
    ToolRoutes.APP_VAULT to R.string.tool_app_vault,
    ToolRoutes.BATTERY_ALARMS to R.string.tool_battery_alarms,
    ToolRoutes.APP_INSIGHTS to R.string.tool_app_insights,
    ToolRoutes.APP_RESOURCE to R.string.tool_app_resource,
    ToolRoutes.STORAGE_FORECAST to R.string.tool_storage_forecast,
    ToolRoutes.FOCUS to R.string.tool_focus,
    ToolRoutes.APP_LOCK to R.string.tool_app_lock,
    ToolRoutes.CLOUD_BACKUP to R.string.tool_cloud_backup,
    ToolRoutes.RESTORE_WIZARD to R.string.restore_title,
    ToolRoutes.GAME_BOOST to R.string.tool_game_boost,
    ToolRoutes.CLEANING_HISTORY to R.string.tool_cleaning_history,
    ToolRoutes.CORPSE_FINDER to R.string.tool_corpse_finder,
    ToolRoutes.APP_DEEP_CLEAN to R.string.tool_app_deep_clean,
    ToolRoutes.APP_CLEANERS_HUB to R.string.tool_app_cleaners,
    ToolRoutes.APP_CLEANER_WHATSAPP to R.string.app_cleaner_whatsapp_title,
    ToolRoutes.APP_CLEANER_TELEGRAM to R.string.app_cleaner_telegram_title,
    ToolRoutes.APP_CLEANER_DISCORD to R.string.app_cleaner_discord_title,
    ToolRoutes.APP_CLEANER_TIKTOK to R.string.app_cleaner_tiktok_title,
    ToolRoutes.BATTERY_HEALTH to R.string.tool_battery_health,
    ToolRoutes.CHARGING_LOG to R.string.tool_charging_log,
    ToolRoutes.BATTERY_DRAIN to R.string.tool_battery_drain,
    ToolRoutes.STORAGE_TREEMAP to R.string.tool_storage_treemap,
    ToolRoutes.NOTIFICATION_STATS to R.string.tool_notification_stats,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScaffold() {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route
    val dark = MaterialTheme.colorScheme.background.luminance() < 0.5f
    val isLeaf = currentRoute == ROUTE_SETTINGS || currentRoute == ROUTE_PRO ||
        currentRoute?.startsWith("tool/") == true
    val showBottomNav = currentRoute != ROUTE_SETTINGS && currentRoute != ROUTE_PRO

    val title = when {
        currentRoute == ROUTE_SETTINGS -> stringResource(R.string.settings_title)
        currentRoute == ROUTE_PRO -> stringResource(R.string.pro_title)
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
                    IconButton(onClick = { navController.navigate(ROUTE_PRO) }) {
                        Icon(
                            Icons.Filled.WorkspacePremium,
                            contentDescription = stringResource(R.string.nav_pro),
                            tint = MaterialTheme.colorScheme.primary,
                        )
                    }
                    IconButton(onClick = { navController.navigate(ROUTE_SETTINGS) }) {
                        Icon(Icons.Filled.Settings, contentDescription = stringResource(R.string.nav_settings))
                    }
                },
            )
        },
        bottomBar = {
            Column {
                if (currentRoute != ROUTE_PRO && currentRoute != ROUTE_SETTINGS) BannerAd()
                if (showBottomNav) {
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
                            label = {
                                Text(
                                    stringResource(dest.labelRes),
                                    maxLines = 1,
                                    softWrap = false,
                                    overflow = TextOverflow.Visible,
                                    fontSize = 10.sp,
                                )
                            },
                            colors = NavigationBarItemDefaults.colors(
                                selectedIconColor = MaterialTheme.colorScheme.primary,
                                selectedTextColor = MaterialTheme.colorScheme.primary,
                                indicatorColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.16f),
                            ),
                        )
                    }
                }
                }
            }
        },
    ) { innerPadding ->
        AnimatedBackdrop()
        UnlockSheetHost(navigateToPro = { navController.navigate(ROUTE_PRO) }) {
        NavHost(
            navController = navController,
            startDestination = FsdDestination.DASHBOARD.route,
            modifier = Modifier.fillMaxSize().padding(innerPadding),
            enterTransition = { fadeIn(tween(280)) + scaleIn(tween(320), initialScale = 0.92f) },
            exitTransition = { fadeOut(tween(180)) + scaleOut(tween(320), targetScale = 1.05f) },
            popEnterTransition = { fadeIn(tween(280)) + scaleIn(tween(320), initialScale = 1.05f) },
            popExitTransition = { fadeOut(tween(180)) + scaleOut(tween(320), targetScale = 0.92f) },
        ) {
            composable(FsdDestination.DASHBOARD.route) {
                DashboardScreen(onNavigate = { navController.navigate(it) })
            }
            composable(FsdDestination.CLEANER.route) { CleanerScreen() }
            composable(FsdDestination.STORAGE.route) { StorageScreen() }
            composable(FsdDestination.APPS.route) { AppsScreen() }
            composable(FsdDestination.TOOLS.route) {
                ToolsScreen(onOpen = { navController.navigate(it) })
            }
            composable(ROUTE_SETTINGS) { SettingsScreen(onNavigate = { navController.navigate(it) }) }
            composable(ROUTE_PRO) { ProScreen() }

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
            composable(ToolRoutes.FILES) { FolderToolsScreen() }
            composable(ToolRoutes.DATA_USAGE) { DataUsageScreen() }
            composable(ToolRoutes.DEVICE_INFO) { DeviceInfoScreen() }
            composable(ToolRoutes.SHREDDER) { ShredderScreen() }
            composable(ToolRoutes.TWEAKS) { SystemTweaksScreen() }
            composable(ToolRoutes.SIMILAR_PHOTOS) { SimilarPhotosScreen() }
            composable(ToolRoutes.PHOTO_REVIEW) { PhotoReviewScreen() }
            composable(ToolRoutes.COMPRESS) { CompressScreen() }
            composable(ToolRoutes.WIFI) { WifiScreen() }
            composable(ToolRoutes.NOTIFICATIONS) { NotificationCleanerScreen() }
            composable(ToolRoutes.SPEED_TEST) { SpeedTestScreen() }
            composable(ToolRoutes.BATTERY) { BatteryScreen() }
            composable(ToolRoutes.MEMORY) { MemoryScreen() }
            composable(ToolRoutes.BACKUP) { BackupScreen() }
            composable(ToolRoutes.RECYCLE_BIN) { TrashScreen() }
            composable(ToolRoutes.HIDDEN_CACHE) { HiddenCacheScreen() }
            composable(ToolRoutes.APP_VAULT) { VaultScreen() }
            composable(ToolRoutes.BATTERY_ALARMS) { BatteryAlarmsScreen() }
            composable(ToolRoutes.APP_INSIGHTS) { AppInsightsScreen() }
            composable(ToolRoutes.APP_RESOURCE) { AppResourceScreen() }
            composable(ToolRoutes.STORAGE_FORECAST) { StorageForecastScreen() }
            composable(ToolRoutes.FOCUS) { FocusScreen() }
            composable(ToolRoutes.APP_LOCK) { AppLockScreen() }
            composable(ToolRoutes.CLOUD_BACKUP) {
                CloudBackupScreen(onOpenRestore = { navController.navigate(ToolRoutes.RESTORE_WIZARD) })
            }
            composable(ToolRoutes.RESTORE_WIZARD) { RestoreWizardScreen() }
            composable(ToolRoutes.GAME_BOOST) { GameBoostScreen() }
            composable(ToolRoutes.CLEANING_HISTORY) { CleaningHistoryScreen() }
            composable(ToolRoutes.CORPSE_FINDER) { CorpseFinderScreen() }
            composable(ToolRoutes.APP_DEEP_CLEAN) { AppDeepCleanScreen() }
            composable(ToolRoutes.APP_CLEANERS_HUB) {
                AppCleanersHubScreen(onOpen = { navController.navigate(it) })
            }
            composable(ToolRoutes.APP_CLEANER_WHATSAPP) { WhatsAppCleanerScreen() }
            composable(ToolRoutes.APP_CLEANER_TELEGRAM) { TelegramCleanerScreen() }
            composable(ToolRoutes.APP_CLEANER_DISCORD) { DiscordCleanerScreen() }
            composable(ToolRoutes.APP_CLEANER_TIKTOK) { TikTokCleanerScreen() }
            composable(ToolRoutes.BATTERY_HEALTH) { BatteryHealthScreen() }
            composable(ToolRoutes.CHARGING_LOG) { ChargingLogScreen() }
            composable(ToolRoutes.BATTERY_DRAIN) { BatteryDrainScreen() }
            composable(ToolRoutes.STORAGE_TREEMAP) { StorageTreemapScreen() }
            composable(ToolRoutes.NOTIFICATION_STATS) { NotificationStatsScreen() }
        }
        }
    }
}
