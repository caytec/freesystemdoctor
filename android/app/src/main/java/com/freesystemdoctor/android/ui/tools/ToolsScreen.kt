package com.freesystemdoctor.android.ui.tools

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Analytics
import androidx.compose.material.icons.filled.Apps
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Backup
import androidx.compose.material.icons.filled.BatteryAlert
import androidx.compose.material.icons.filled.BatteryChargingFull
import androidx.compose.material.icons.filled.BlurOn
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material.icons.filled.Compress
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.ContentPaste
import androidx.compose.material.icons.filled.Assessment
import androidx.compose.material.icons.filled.DeleteForever
import androidx.compose.material.icons.filled.DeleteSweep
import androidx.compose.material.icons.filled.DoNotDisturbOn
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Insights
import androidx.compose.material.icons.filled.SportsEsports
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.NetworkCell
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.ShieldMoon
import androidx.compose.material.icons.filled.TrendingDown
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Timelapse
import androidx.compose.material.icons.filled.Tune
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.ui.components.Appear
import com.freesystemdoctor.android.ui.components.LocalUnlockController
import com.freesystemdoctor.android.ui.components.SectionHeader
import com.freesystemdoctor.android.ui.components.bounceClick
import com.freesystemdoctor.android.ui.navigation.ToolRoutes

private data class Tool(
    val labelRes: Int,
    val icon: ImageVector,
    val route: String,
    val advanced: Boolean = false,
)

private data class ToolGroup(val titleRes: Int, val tools: List<Tool>)

private val toolGroups = listOf(
    ToolGroup(
        R.string.tools_group_files,
        listOf(
            Tool(R.string.tool_duplicates, Icons.Filled.ContentCopy, ToolRoutes.DUPLICATES),
            Tool(R.string.tool_large_files, Icons.Filled.Folder, ToolRoutes.LARGE_FILES),
            Tool(R.string.tool_storage_types, Icons.Filled.Analytics, ToolRoutes.STORAGE_TYPES),
            Tool(R.string.tool_files, Icons.Filled.Folder, ToolRoutes.FILES),
            Tool(R.string.tool_recycle_bin, Icons.Filled.DeleteSweep, ToolRoutes.RECYCLE_BIN),
            Tool(R.string.tool_hidden_cache, Icons.Filled.Folder, ToolRoutes.HIDDEN_CACHE),
            Tool(R.string.tool_storage_forecast, Icons.Filled.TrendingDown, ToolRoutes.STORAGE_FORECAST),
            Tool(R.string.tool_shredder, Icons.Filled.DeleteForever, ToolRoutes.SHREDDER, advanced = true),
            Tool(R.string.tool_cleaning_history, Icons.Filled.History, ToolRoutes.CLEANING_HISTORY),
        ),
    ),
    ToolGroup(
        R.string.tools_group_photos,
        listOf(
            Tool(R.string.tool_similar, Icons.Filled.PhotoLibrary, ToolRoutes.SIMILAR_PHOTOS),
            Tool(R.string.tool_photo_review, Icons.Filled.BlurOn, ToolRoutes.PHOTO_REVIEW),
            Tool(R.string.tool_compress, Icons.Filled.Compress, ToolRoutes.COMPRESS),
        ),
    ),
    ToolGroup(
        R.string.tools_group_apps,
        listOf(
            Tool(R.string.tool_app_usage, Icons.Filled.Timelapse, ToolRoutes.APP_USAGE),
            Tool(R.string.tool_rarely_used, Icons.Filled.Apps, ToolRoutes.RARELY_USED),
            Tool(R.string.tool_permissions, Icons.Filled.Security, ToolRoutes.PERMISSIONS),
            Tool(R.string.tool_apk, Icons.Filled.Backup, ToolRoutes.APK_EXTRACTOR),
            Tool(R.string.tool_backup, Icons.Filled.CloudUpload, ToolRoutes.BACKUP, advanced = true),
            Tool(R.string.tool_app_insights, Icons.Filled.Insights, ToolRoutes.APP_INSIGHTS, advanced = true),
            Tool(R.string.tool_app_vault, Icons.Filled.Lock, ToolRoutes.APP_VAULT, advanced = true),
            Tool(R.string.tool_app_resource, Icons.Filled.Assessment, ToolRoutes.APP_RESOURCE),
            Tool(R.string.tool_app_lock, Icons.Filled.ShieldMoon, ToolRoutes.APP_LOCK, advanced = true),
            Tool(R.string.tool_cloud_backup, Icons.Filled.CloudUpload, ToolRoutes.CLOUD_BACKUP, advanced = true),
        ),
    ),
    ToolGroup(
        R.string.tools_group_system,
        listOf(
            Tool(R.string.tool_memory, Icons.Filled.Memory, ToolRoutes.MEMORY),
            Tool(R.string.tool_battery, Icons.Filled.BatteryChargingFull, ToolRoutes.BATTERY),
            Tool(R.string.tool_battery_alarms, Icons.Filled.BatteryAlert, ToolRoutes.BATTERY_ALARMS, advanced = true),
            Tool(R.string.tool_focus, Icons.Filled.DoNotDisturbOn, ToolRoutes.FOCUS),
            Tool(R.string.tool_game_boost, Icons.Filled.SportsEsports, ToolRoutes.GAME_BOOST, advanced = true),
            Tool(R.string.tool_speed, Icons.Filled.Speed, ToolRoutes.SPEED_TEST),
            Tool(R.string.tool_data_usage, Icons.Filled.NetworkCell, ToolRoutes.DATA_USAGE),
            Tool(R.string.tool_device_info, Icons.Filled.PhoneAndroid, ToolRoutes.DEVICE_INFO),
            Tool(R.string.tool_clipboard, Icons.Filled.ContentPaste, ToolRoutes.CLIPBOARD),
            Tool(R.string.tool_schedule, Icons.Filled.Schedule, ToolRoutes.SCHEDULE, advanced = true),
            Tool(R.string.nav_assistant, Icons.Filled.AutoAwesome, ToolRoutes.ASSISTANT),
            Tool(R.string.tool_wifi, Icons.Filled.Wifi, ToolRoutes.WIFI, advanced = true),
            Tool(R.string.tool_notifications, Icons.Filled.Notifications, ToolRoutes.NOTIFICATIONS, advanced = true),
            Tool(R.string.tool_tweaks, Icons.Filled.Tune, ToolRoutes.TWEAKS, advanced = true),
        ),
    ),
)

private const val GROUP_ALL = -1

@Composable
fun ToolsScreen(
    onOpen: (String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ToolsViewModel = viewModel(),
) {
    val advanced by viewModel.advancedUnlocked.collectAsStateWithLifecycle()
    val unlocks by viewModel.unlocks.collectAsStateWithLifecycle()
    val activity = androidx.compose.ui.platform.LocalContext.current as? android.app.Activity
    val unlockController = LocalUnlockController.current

    var query by remember { mutableStateOf("") }
    var selectedGroup by remember { mutableIntStateOf(GROUP_ALL) }
    val context = androidx.compose.ui.platform.LocalContext.current

    val filteredGroups = remember(query, selectedGroup) {
        val groupsToSearch = if (selectedGroup == GROUP_ALL) toolGroups
        else listOf(toolGroups.getOrNull(selectedGroup) ?: return@remember emptyList())
        if (query.isBlank()) {
            groupsToSearch
        } else {
            val q = query.trim().lowercase()
            listOf(
                ToolGroup(
                    R.string.tools_search_results,
                    groupsToSearch.flatMap { it.tools }
                        .filter { tool ->
                            context.getString(tool.labelRes).lowercase().contains(q)
                        },
                ),
            ).filter { it.tools.isNotEmpty() }
        }
    }

    Column(modifier = modifier.fillMaxSize()) {
        // Search + filter bar
        Column(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            OutlinedTextField(
                value = query,
                onValueChange = { query = it },
                placeholder = { Text(stringResource(R.string.tools_search_hint)) },
                leadingIcon = { Icon(Icons.Filled.Search, contentDescription = null) },
                trailingIcon = if (query.isNotEmpty()) {
                    {
                        androidx.compose.material3.IconButton(onClick = { query = "" }) {
                            Icon(Icons.Filled.Close, contentDescription = null)
                        }
                    }
                } else null,
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                shape = MaterialTheme.shapes.large,
                colors = OutlinedTextFieldDefaults.colors(
                    unfocusedBorderColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.4f),
                ),
            )
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                contentPadding = PaddingValues(horizontal = 0.dp),
            ) {
                item {
                    FilterChip(
                        selected = selectedGroup == GROUP_ALL,
                        onClick = { selectedGroup = GROUP_ALL },
                        label = { Text(stringResource(R.string.tools_filter_all)) },
                    )
                }
                toolGroups.forEachIndexed { idx, group ->
                    item {
                        FilterChip(
                            selected = selectedGroup == idx,
                            onClick = { selectedGroup = if (selectedGroup == idx) GROUP_ALL else idx },
                            label = { Text(stringResource(group.titleRes)) },
                        )
                    }
                }
            }
        }

        // Tool grid
        Appear {
            LazyVerticalGrid(
                columns = GridCells.Adaptive(minSize = 150.dp),
                modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                contentPadding = PaddingValues(vertical = 8.dp),
            ) {
                filteredGroups.forEachIndexed { groupIndex, group ->
                    item(span = { GridItemSpan(maxLineSpan) }, key = "header_${group.titleRes}") {
                        Appear(index = groupIndex * 2) {
                            SectionHeader(stringResource(group.titleRes))
                        }
                    }
                    items(group.tools, key = { it.route }) { tool ->
                        val now = System.currentTimeMillis()
                        val perToolUnlocked = (unlocks[tool.route] ?: 0L) > now
                        val unlocked = !tool.advanced || advanced || perToolUnlocked
                        ToolCard(tool = tool, locked = !unlocked, modifier = Modifier.animateItem(), onClick = {
                            if (!unlocked) {
                                unlockController.request(tool.route, tool.labelRes)
                            } else {
                                val isPerToolRewarded = (unlocks[tool.route] ?: 0L) > System.currentTimeMillis()
                                if (tool.advanced && !isPerToolRewarded) {
                                    activity?.let {
                                        com.freesystemdoctor.android.core.di.ServiceLocator.adsController.maybeShowInterstitial(it)
                                    }
                                }
                                onOpen(tool.route)
                            }
                        })
                    }
                }
            }
        }
    }
}

@Composable
private fun ToolCard(tool: Tool, locked: Boolean, modifier: Modifier = Modifier, onClick: () -> Unit) {
    val tint = if (locked) MaterialTheme.colorScheme.onSurfaceVariant
    else MaterialTheme.colorScheme.primary
    Card(
        modifier = modifier.fillMaxWidth().height(120.dp).bounceClick(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
    ) {
        Box(Modifier.fillMaxSize()) {
            Column(
                modifier = Modifier.fillMaxSize().padding(14.dp),
                verticalArrangement = Arrangement.SpaceBetween,
            ) {
                Box(
                    modifier = Modifier
                        .size(44.dp)
                        .clip(RoundedCornerShape(14.dp))
                        .background(tint.copy(alpha = 0.14f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        tool.icon,
                        contentDescription = null,
                        tint = tint,
                        modifier = Modifier.size(26.dp),
                    )
                }
                Text(
                    stringResource(tool.labelRes),
                    style = MaterialTheme.typography.titleSmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            if (locked) {
                Box(
                    modifier = Modifier
                        .padding(10.dp)
                        .size(22.dp)
                        .clip(RoundedCornerShape(11.dp))
                        .background(MaterialTheme.colorScheme.surface)
                        .align(Alignment.TopEnd),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        Icons.Filled.Lock,
                        contentDescription = stringResource(R.string.unlock_locked_cd),
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(14.dp),
                    )
                }
            }
        }
    }
}
