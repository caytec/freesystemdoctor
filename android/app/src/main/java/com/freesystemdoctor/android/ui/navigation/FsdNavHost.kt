package com.freesystemdoctor.android.ui.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.ui.apps.AppsScreen
import com.freesystemdoctor.android.ui.assistant.AssistantScreen
import com.freesystemdoctor.android.ui.cleaner.CleanerScreen
import com.freesystemdoctor.android.ui.dashboard.DashboardScreen
import com.freesystemdoctor.android.ui.settings.SettingsScreen
import com.freesystemdoctor.android.ui.storage.StorageScreen

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScaffold() {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route

    val title = when (currentRoute) {
        ROUTE_SETTINGS -> stringResource(R.string.settings_title)
        else -> FsdDestination.entries.firstOrNull { it.route == currentRoute }
            ?.let { stringResource(it.labelRes) }
            ?: stringResource(R.string.app_name)
    }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text(title) },
                actions = {
                    IconButton(onClick = { navController.navigate(ROUTE_SETTINGS) }) {
                        Icon(Icons.Filled.Settings, contentDescription = stringResource(R.string.nav_settings))
                    }
                },
            )
        },
        bottomBar = {
            NavigationBar {
                val destination = backStackEntry?.destination
                FsdDestination.entries.forEach { dest ->
                    val selected = destination?.hierarchy?.any { it.route == dest.route } == true
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
                        icon = { Icon(dest.icon, contentDescription = stringResource(dest.labelRes)) },
                        label = { Text(stringResource(dest.labelRes)) },
                    )
                }
            }
        },
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = FsdDestination.DASHBOARD.route,
            modifier = Modifier.padding(innerPadding),
        ) {
            composable(FsdDestination.DASHBOARD.route) { DashboardScreen() }
            composable(FsdDestination.CLEANER.route) { CleanerScreen() }
            composable(FsdDestination.STORAGE.route) { StorageScreen() }
            composable(FsdDestination.APPS.route) { AppsScreen() }
            composable(FsdDestination.ASSISTANT.route) { AssistantScreen() }
            composable(ROUTE_SETTINGS) { SettingsScreen() }
        }
    }
}
