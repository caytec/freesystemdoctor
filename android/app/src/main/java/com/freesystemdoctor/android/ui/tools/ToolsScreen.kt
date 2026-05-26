package com.freesystemdoctor.android.ui.tools

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
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
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.ContentPaste
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Timelapse
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.ui.components.SectionHeader
import com.freesystemdoctor.android.ui.navigation.ToolRoutes

private data class Tool(val labelRes: Int, val icon: ImageVector, val route: String)
private data class ToolGroup(val titleRes: Int, val tools: List<Tool>)

private val toolGroups = listOf(
    ToolGroup(
        R.string.tools_group_files,
        listOf(
            Tool(R.string.tool_duplicates, Icons.Filled.ContentCopy, ToolRoutes.DUPLICATES),
            Tool(R.string.tool_large_files, Icons.Filled.Folder, ToolRoutes.LARGE_FILES),
            Tool(R.string.tool_storage_types, Icons.Filled.Analytics, ToolRoutes.STORAGE_TYPES),
        ),
    ),
    ToolGroup(
        R.string.tools_group_apps,
        listOf(
            Tool(R.string.tool_app_usage, Icons.Filled.Timelapse, ToolRoutes.APP_USAGE),
            Tool(R.string.tool_rarely_used, Icons.Filled.Apps, ToolRoutes.RARELY_USED),
            Tool(R.string.tool_permissions, Icons.Filled.Security, ToolRoutes.PERMISSIONS),
            Tool(R.string.tool_apk, Icons.Filled.Backup, ToolRoutes.APK_EXTRACTOR),
        ),
    ),
    ToolGroup(
        R.string.tools_group_system,
        listOf(
            Tool(R.string.tool_clipboard, Icons.Filled.ContentPaste, ToolRoutes.CLIPBOARD),
            Tool(R.string.tool_schedule, Icons.Filled.Schedule, ToolRoutes.SCHEDULE),
            Tool(R.string.nav_assistant, Icons.Filled.AutoAwesome, ToolRoutes.ASSISTANT),
        ),
    ),
)

@Composable
fun ToolsScreen(
    onOpen: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyVerticalGrid(
        columns = GridCells.Adaptive(minSize = 150.dp),
        modifier = modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 16.dp),
    ) {
        toolGroups.forEach { group ->
            item(span = { GridItemSpan(maxLineSpan) }) {
                SectionHeader(stringResource(group.titleRes))
            }
            items(group.tools, key = { it.route }) { tool ->
                ToolCard(tool = tool, onClick = { onOpen(tool.route) })
            }
        }
    }
}

@Composable
private fun ToolCard(tool: Tool, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().height(120.dp).clickable(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(
            modifier = Modifier.fillMaxSize().padding(14.dp),
            verticalArrangement = Arrangement.SpaceBetween,
        ) {
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(RoundedCornerShape(14.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    tool.icon,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(28.dp),
                )
            }
            Text(
                stringResource(tool.labelRes),
                style = MaterialTheme.typography.titleSmall,
                textAlign = TextAlign.Start,
            )
        }
    }
}
