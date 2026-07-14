package com.freeandroiddoctor.android.ui.modes

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.Flight
import androidx.compose.material.icons.filled.Save
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.SportsEsports
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.data.modes.AppMode
import com.freeandroiddoctor.android.data.quota.DailyQuotaStore
import com.freeandroiddoctor.android.ui.components.QuotaGatedButton
import com.freeandroiddoctor.android.ui.components.SectionHeader
import com.freeandroiddoctor.android.ui.navigation.ToolRoutes

@Composable
fun ModesScreen(viewModel: ModesViewModel = viewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LazyColumn(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        contentPadding = PaddingValues(vertical = 12.dp),
    ) {
        item {
            ActiveBanner(activeId = state.active?.activeModeId, onDeactivate = viewModel::deactivate)
        }
        item { SectionHeader(text = stringResource(R.string.modes_builtin)) }
        items(state.builtIn, key = { it.id }) { mode ->
            ModeRow(
                mode = mode,
                active = state.active?.activeModeId == mode.id,
                modifier = Modifier.animateItem(),
                onActivate = { viewModel.activate(mode) },
            )
        }
        if (state.custom.isNotEmpty()) {
            item { SectionHeader(text = stringResource(R.string.modes_custom)) }
            items(state.custom, key = { it.id }) { mode ->
                ModeRow(
                    mode = mode,
                    active = state.active?.activeModeId == mode.id,
                    modifier = Modifier.animateItem(),
                    onActivate = { viewModel.activate(mode) },
                )
            }
        }
    }
}

@Composable
private fun ActiveBanner(activeId: String?, onDeactivate: () -> Unit) {
    if (activeId == null) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
            shape = MaterialTheme.shapes.medium,
        ) {
            Text(
                text = stringResource(R.string.modes_none_active),
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(16.dp),
            )
        }
    } else {
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.14f),
            ),
            shape = MaterialTheme.shapes.medium,
        ) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(16.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        text = stringResource(R.string.modes_active_label),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        text = activeId.localizeMode(),
                        style = MaterialTheme.typography.titleMedium,
                    )
                }
                OutlinedButton(onClick = onDeactivate) {
                    Text(stringResource(R.string.modes_deactivate))
                }
            }
        }
    }
}

@Composable
private fun ModeRow(
    mode: AppMode,
    active: Boolean,
    onActivate: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(mode.icon(), contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                Text(
                    text = mode.id.localizeMode(),
                    style = MaterialTheme.typography.titleSmall,
                    modifier = Modifier.padding(start = 12.dp).weight(1f),
                )
            }
            Text(
                text = mode.summary(),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 4.dp),
            )
            QuotaGatedButton(
                text = if (active) stringResource(R.string.modes_already_active)
                else stringResource(R.string.modes_activate),
                quotaKey = DailyQuotaStore.Key.MODE_SWITCH,
                unlockRoute = ToolRoutes.MODES,
                enabled = !active,
                modifier = Modifier.padding(top = 8.dp),
                onConsume = { onActivate() },
            )
        }
    }
}

@Composable
private fun String.localizeMode(): String = when (this) {
    "game" -> stringResource(R.string.mode_game)
    "travel" -> stringResource(R.string.mode_travel)
    "focus" -> stringResource(R.string.mode_focus)
    "privacy" -> stringResource(R.string.mode_privacy)
    "storage_saver" -> stringResource(R.string.mode_storage_saver)
    else -> this
}

private fun AppMode.icon(): ImageVector = when (id) {
    "game" -> Icons.Filled.SportsEsports
    "travel" -> Icons.Filled.Flight
    "focus" -> Icons.Filled.VisibilityOff
    "privacy" -> Icons.Filled.Shield
    "storage_saver" -> Icons.Filled.Save
    else -> Icons.Filled.Bolt
}

@Composable
private fun AppMode.summary(): String {
    val parts = buildList {
        if (snoozeAllNotifications) add(stringResource(R.string.mode_summary_notifications))
        if (pauseScheduledClean) add(stringResource(R.string.mode_summary_pause_clean))
        applyDarkTheme?.let { add(if (it) stringResource(R.string.mode_summary_dark) else stringResource(R.string.mode_summary_light)) }
        privacyProfileId?.let { add(stringResource(R.string.mode_summary_privacy)) }
        if (suggestPrivateDns) add(stringResource(R.string.mode_summary_dns))
    }
    return parts.joinToString(", ").ifEmpty { stringResource(R.string.mode_summary_minimal) }
}
