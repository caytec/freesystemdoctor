package com.freeandroiddoctor.android.ui.corpse

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
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.util.ByteFormatter
import com.freeandroiddoctor.android.engine.corpse.CorpseEntry
import com.freeandroiddoctor.android.engine.corpse.CorpseRisk
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.ShimmerList

@Composable
fun CorpseFinderScreen(
    modifier: Modifier = Modifier,
    viewModel: CorpseFinderViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val pickRoot = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocumentTree(),
    ) { uri -> uri?.let(viewModel::onRootGranted) }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoBanner(stringResource(R.string.corpse_finder_note))

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

        if (state.report.androidDataBlocked) {
            InfoBanner(stringResource(R.string.corpse_finder_scan_blocked_android_data))
        }

        val entries = state.report.entries
        when {
            state.scanning -> ShimmerList()
            state.rootUri == null -> Text(
                stringResource(R.string.storage_treemap_grant),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            entries.isEmpty() -> Text(
                stringResource(R.string.corpse_finder_empty),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            else -> {
                Text(
                    stringResource(
                        R.string.corpse_finder_count,
                        entries.size,
                        ByteFormatter.format(state.report.totalBytes),
                    ),
                    style = MaterialTheme.typography.titleSmall,
                )
                Button(onClick = viewModel::deleteAll) {
                    Text(stringResource(R.string.corpse_finder_delete_all))
                }
                LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(entries, key = { it.folderUri.toString() }) { entry ->
                        CorpseRow(
                            entry = entry,
                            onDelete = { viewModel.delete(listOf(entry)) },
                            modifier = Modifier.animateItem(),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun CorpseRow(
    entry: CorpseEntry,
    onDelete: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    RiskBadge(entry.risk)
                    Text(entry.displayName, style = MaterialTheme.typography.titleSmall)
                }
                Text(
                    entry.packageName,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    ByteFormatter.format(entry.sizeBytes),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
            OutlinedButton(onClick = onDelete, enabled = entry.deletable) {
                Text(stringResource(R.string.action_delete))
            }
        }
    }
}

@Composable
private fun RiskBadge(risk: CorpseRisk) {
    val (label, color) = when (risk) {
        CorpseRisk.HIGH -> stringResource(R.string.corpse_finder_risk_high) to MaterialTheme.colorScheme.error
        CorpseRisk.MEDIUM -> stringResource(R.string.corpse_finder_risk_medium) to MaterialTheme.colorScheme.tertiary
        CorpseRisk.LOW -> stringResource(R.string.corpse_finder_risk_low) to MaterialTheme.colorScheme.outline
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
