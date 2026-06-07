package com.freesystemdoctor.android.ui.appdeep

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.util.ByteFormatter
import com.freesystemdoctor.android.engine.appdeep.AppGroup
import com.freesystemdoctor.android.engine.appdeep.DeepHit
import com.freesystemdoctor.android.engine.appdeep.Safety
import com.freesystemdoctor.android.ui.components.InfoBanner
import com.freesystemdoctor.android.ui.components.ShimmerList

@Composable
fun AppDeepCleanScreen(
    modifier: Modifier = Modifier,
    viewModel: AppDeepCleanViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val pickRoot = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocumentTree(),
    ) { uri -> uri?.let(viewModel::onRootGranted) }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoBanner(stringResource(R.string.app_deep_clean_note))

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { pickRoot.launch(null) }) {
                Text(stringResource(R.string.corpse_finder_pick))
            }
            if (state.rootUri != null) {
                OutlinedButton(onClick = viewModel::scan, enabled = !state.scanning) {
                    Text(stringResource(R.string.action_scan))
                }
            }
        }

        if (state.freedBytes > 0) {
            Text(
                stringResource(R.string.cleaner_freed, ByteFormatter.format(state.freedBytes)),
                color = MaterialTheme.colorScheme.secondary,
                style = MaterialTheme.typography.bodyMedium,
            )
        }

        val groups = state.report.perApp.values.toList()
        when {
            state.scanning -> ShimmerList()
            state.rootUri == null -> Text(
                stringResource(R.string.storage_treemap_grant),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            groups.isEmpty() -> Text(
                stringResource(R.string.app_deep_clean_empty),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            else -> {
                if (state.selected.isNotEmpty()) {
                    Button(onClick = viewModel::cleanSelected) {
                        Text(stringResource(R.string.app_deep_clean_run))
                    }
                }
                LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    items(groups, key = { it.packageName }) { group ->
                        GroupCard(
                            group = group,
                            selected = state.selected,
                            onToggle = viewModel::toggle,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun GroupCard(group: AppGroup, selected: Set<String>, onToggle: (DeepHit) -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(group.appLabel, style = MaterialTheme.typography.titleSmall)
            Text(
                stringResource(R.string.app_deep_clean_bytes, ByteFormatter.format(group.totalBytes)),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.primary,
            )
            group.hits.forEach { hit ->
                HitRow(
                    hit = hit,
                    checked = hit.folderUri.toString() in selected,
                    onToggle = { onToggle(hit) },
                )
            }
        }
    }
}

@Composable
private fun HitRow(hit: DeepHit, checked: Boolean, onToggle: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Row(
            modifier = Modifier.weight(1f),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Checkbox(checked = checked, onCheckedChange = { onToggle() })
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    SafetyBadge(hit.rule.safety)
                    Text(hit.rule.label, style = MaterialTheme.typography.bodyMedium)
                }
                Text(
                    hit.rule.relPath,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        Text(
            ByteFormatter.format(hit.sizeBytes),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.primary,
        )
    }
}

@Composable
private fun SafetyBadge(safety: Safety) {
    val (label, color) = when (safety) {
        Safety.SAFE -> stringResource(R.string.app_deep_clean_safety_safe) to MaterialTheme.colorScheme.secondary
        Safety.CAUTIOUS -> stringResource(R.string.app_deep_clean_safety_cautious) to MaterialTheme.colorScheme.tertiary
        Safety.OPT_IN -> stringResource(R.string.app_deep_clean_safety_optin) to MaterialTheme.colorScheme.outline
    }
    Box(
        modifier = Modifier
            .clip(MaterialTheme.shapes.extraSmall)
            .background(color.copy(alpha = 0.18f))
            .padding(horizontal = 6.dp, vertical = 2.dp),
    ) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = color)
    }
}
