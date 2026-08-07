package com.freeandroiddoctor.android.ui.organizer

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Apps
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.Forum
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material.icons.filled.Newspaper
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material.icons.filled.SportsEsports
import androidx.compose.material.icons.filled.WorkOutline
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.engine.organizer.AppCategory
import com.freeandroiddoctor.android.engine.organizer.CategoryGroup
import com.freeandroiddoctor.android.engine.organizer.OrganizedApp
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.ShimmerList
import com.freeandroiddoctor.android.ui.components.bounceClick
import androidx.compose.foundation.layout.fillMaxSize

private fun categoryLabelRes(category: AppCategory): Int = when (category) {
    AppCategory.GAMES -> R.string.organizer_cat_games
    AppCategory.SOCIAL -> R.string.organizer_cat_social
    AppCategory.PHOTO_VIDEO -> R.string.organizer_cat_photo_video
    AppCategory.MUSIC_AUDIO -> R.string.organizer_cat_music_audio
    AppCategory.NEWS -> R.string.organizer_cat_news
    AppCategory.MAPS -> R.string.organizer_cat_maps
    AppCategory.PRODUCTIVITY -> R.string.organizer_cat_productivity
    AppCategory.TOOLS -> R.string.organizer_cat_tools
    AppCategory.OTHER -> R.string.organizer_cat_other
}

private fun categoryIcon(category: AppCategory): ImageVector = when (category) {
    AppCategory.GAMES -> Icons.Filled.SportsEsports
    AppCategory.SOCIAL -> Icons.Filled.Forum
    AppCategory.PHOTO_VIDEO -> Icons.Filled.PhotoLibrary
    AppCategory.MUSIC_AUDIO -> Icons.Filled.MusicNote
    AppCategory.NEWS -> Icons.Filled.Newspaper
    AppCategory.MAPS -> Icons.Filled.Map
    AppCategory.PRODUCTIVITY -> Icons.Filled.WorkOutline
    AppCategory.TOOLS -> Icons.Filled.Build
    AppCategory.OTHER -> Icons.Filled.Apps
}

@Composable
private fun categoryLabel(category: AppCategory): String = stringResource(categoryLabelRes(category))

@Composable
fun OrganizerScreen(
    modifier: Modifier = Modifier,
    initialCategory: String? = null,
    viewModel: OrganizerViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current

    LaunchedEffect(initialCategory) {
        initialCategory?.let { runCatching { AppCategory.valueOf(it) }.getOrNull() }
            ?.let(viewModel::expandOnly)
    }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear { InfoBanner(stringResource(R.string.organizer_note)) }

        val report = state.report
        when {
            state.loading -> ShimmerList()
            report == null || report.groups.isEmpty() -> Text(stringResource(R.string.empty))
            else -> {
                LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    itemsIndexed(report.groups, key = { _, g -> g.category.name }) { index, group ->
                        Appear(index = index) {
                            CategoryFolderCard(
                                group = group,
                                expanded = group.category in state.expanded,
                                pinSupported = state.pinSupported,
                                onToggle = { viewModel.toggleExpanded(group.category) },
                                onPin = {
                                    val label = context.getString(categoryLabelRes(group.category))
                                    viewModel.pinShortcut(group.category, label)
                                },
                                onLaunch = { pkg ->
                                    viewModel.launchIntent(pkg)?.let { runCatching { context.startActivity(it) } }
                                },
                                onChangeCategory = { pkg, cat -> viewModel.setCategory(pkg, cat) },
                            )
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun CategoryFolderCard(
    group: CategoryGroup,
    expanded: Boolean,
    pinSupported: Boolean,
    onToggle: () -> Unit,
    onPin: () -> Unit,
    onLaunch: (String) -> Unit,
    onChangeCategory: (String, AppCategory?) -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth().bounceClick(haptic = false, onClick = onToggle),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(categoryIcon(group.category), contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                    Column(Modifier.padding(start = 12.dp)) {
                        Text(categoryLabel(group.category), style = MaterialTheme.typography.titleMedium)
                        Text(
                            stringResource(R.string.organizer_app_count, group.apps.size),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
                Icon(
                    if (expanded) Icons.Filled.ExpandLess else Icons.Filled.ExpandMore,
                    contentDescription = null,
                )
            }

            AnimatedVisibility(visible = expanded) {
                Column {
                    FlowRow(
                        modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        group.apps.forEach { app ->
                            AppChip(
                                app = app,
                                onLaunch = { onLaunch(app.packageName) },
                                onChangeCategory = { onChangeCategory(app.packageName, it) },
                            )
                        }
                    }
                    if (pinSupported) {
                        OutlinedButton(
                            onClick = onPin,
                            modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                        ) { Text(stringResource(R.string.organizer_pin)) }
                    } else {
                        Text(
                            stringResource(R.string.organizer_pin_unsupported),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(top = 12.dp),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun AppChip(
    app: OrganizedApp,
    onLaunch: () -> Unit,
    onChangeCategory: (AppCategory?) -> Unit,
) {
    var menuOpen by remember { mutableStateOf(false) }
    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(20.dp))
            .background(MaterialTheme.colorScheme.surfaceContainerHigh)
            .bounceClick { onLaunch() }
            .padding(start = 12.dp, end = 2.dp, top = 4.dp, bottom = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            app.label,
            style = MaterialTheme.typography.bodyMedium,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.widthIn(max = 140.dp),
        )
        Box {
            IconButton(onClick = { menuOpen = true }, modifier = Modifier.size(32.dp)) {
                Icon(
                    Icons.Filled.MoreVert,
                    contentDescription = stringResource(R.string.organizer_change_category),
                    modifier = Modifier.size(18.dp),
                )
            }
            DropdownMenu(expanded = menuOpen, onDismissRequest = { menuOpen = false }) {
                AppCategory.entries.forEach { cat ->
                    DropdownMenuItem(
                        text = { Text(categoryLabel(cat)) },
                        onClick = { menuOpen = false; onChangeCategory(cat) },
                        leadingIcon = if (cat == app.category) {
                            { Icon(Icons.Filled.Check, contentDescription = null) }
                        } else {
                            null
                        },
                    )
                }
                if (app.isManualOverride) {
                    DropdownMenuItem(
                        text = { Text(stringResource(R.string.organizer_reset_category)) },
                        onClick = { menuOpen = false; onChangeCategory(null) },
                    )
                }
            }
        }
    }
}
