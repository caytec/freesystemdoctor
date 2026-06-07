package com.freesystemdoctor.android.ui.memory

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.IconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.util.ByteFormatter
import com.freesystemdoctor.android.ui.components.Appear
import com.freesystemdoctor.android.ui.components.InfoBanner
import com.freesystemdoctor.android.ui.components.StatCard
import com.freesystemdoctor.android.ui.components.UninstallPreviewSheet

@Composable
fun MemoryScreen(
    modifier: Modifier = Modifier,
    viewModel: MemoryViewModel = viewModel(),
) {
    val context = LocalContext.current
    val state by viewModel.state.collectAsStateWithLifecycle()
    val uninstallSheet = UninstallPreviewSheet.use(context)
    LaunchedEffect(Unit) { viewModel.load() }

    LazyColumn(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item("stat") {
            state.info?.let { m ->
                Appear {
                    StatCard(
                        title = stringResource(R.string.dashboard_memory),
                        value = ByteFormatter.format(m.usedBytes),
                        subtitle = stringResource(
                            R.string.ram_used_of,
                            ByteFormatter.format(m.usedBytes),
                            ByteFormatter.format(m.totalBytes),
                        ),
                        progress = m.usedFraction,
                    )
                }
            }
        }

        item("note") { InfoBanner(stringResource(R.string.memory_note)) }

        item("free-btn") {
            Button(
                onClick = viewModel::freeBackground,
                enabled = !state.working,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(stringResource(R.string.memory_free)) }
        }

        state.lastFreedBytes?.let { freed ->
            item("freed-text") {
                Text(
                    stringResource(R.string.memory_freed, ByteFormatter.format(freed)),
                    color = MaterialTheme.colorScheme.secondary,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }

        item("apps-header") {
            Column {
                Text(
                    stringResource(R.string.memory_largest_apps_title),
                    style = MaterialTheme.typography.titleMedium,
                )
                Text(
                    stringResource(R.string.memory_largest_apps_hint),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }

        if (state.largeApps.isEmpty() && state.loadingApps) {
            item("apps-loading") {
                Text(
                    stringResource(R.string.memory_largest_apps_loading),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }

        items(state.largeApps, key = { it.packageName }) { app ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceContainer,
                ),
                shape = MaterialTheme.shapes.medium,
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(start = 14.dp, end = 4.dp, top = 6.dp, bottom = 6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(modifier = Modifier.weight(1f).padding(vertical = 8.dp)) {
                        Text(app.label, style = MaterialTheme.typography.titleSmall)
                        Text(
                            app.packageName,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        if (app.totalBytes > 0) {
                            Text(
                                ByteFormatter.format(app.totalBytes),
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.primary,
                            )
                        }
                    }
                    IconButton(onClick = { uninstallSheet.requestUninstall(app.packageName) }) {
                        Icon(
                            Icons.Filled.Delete,
                            contentDescription = stringResource(R.string.apps_uninstall),
                            tint = MaterialTheme.colorScheme.error,
                        )
                    }
                }
            }
        }
    }
}
