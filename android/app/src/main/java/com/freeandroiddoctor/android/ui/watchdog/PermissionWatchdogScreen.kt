package com.freeandroiddoctor.android.ui.watchdog

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.NewReleases
import androidx.compose.material.icons.filled.Update
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.engine.watchdog.PermChange
import com.freeandroiddoctor.android.ui.components.InfoBanner

@Composable
fun PermissionWatchdogScreen(
    modifier: Modifier = Modifier,
    viewModel: PermissionWatchdogViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LazyColumn(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item("note") { InfoBanner(stringResource(R.string.watchdog_note)) }

        item("scan") {
            Button(
                onClick = viewModel::scan,
                enabled = !state.scanning,
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (state.scanning) {
                    CircularProgressIndicator(
                        modifier = Modifier.padding(end = 8.dp).size(18.dp),
                        strokeWidth = 2.dp,
                    )
                }
                Text(stringResource(R.string.watchdog_scan))
            }
        }

        if (state.scanning) {
            item("scanning") {
                Text(
                    stringResource(R.string.watchdog_scanning),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }

        if (state.scanned && !state.scanning) {
            when {
                state.firstRun -> item("baseline") {
                    ResultBanner(
                        stringResource(R.string.watchdog_baseline_title),
                        stringResource(R.string.watchdog_baseline_body, state.scannedApps),
                    )
                }
                state.changes.isEmpty() -> item("noChanges") {
                    ResultBanner(
                        stringResource(R.string.watchdog_none_title),
                        stringResource(R.string.watchdog_none_body, state.scannedApps),
                    )
                }
                else -> {
                    item("changesHeader") {
                        Text(
                            stringResource(R.string.watchdog_changes, state.changes.size),
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.primary,
                        )
                    }
                    items(state.changes, key = { it.pkg }) { change ->
                        ChangeCard(change, modifier = Modifier.animateItem())
                    }
                }
            }
        }
    }
}

@Composable
private fun ResultBanner(title: String, body: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(Modifier.padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            Text(
                body,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 4.dp),
            )
        }
    }
}

@Composable
private fun ChangeCard(change: PermChange, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    if (change.isNewApp) Icons.Filled.NewReleases else Icons.Filled.Update,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(end = 8.dp).size(20.dp),
                )
                Column(Modifier.weight(1f)) {
                    Text(
                        change.label,
                        style = MaterialTheme.typography.titleSmall,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        when {
                            change.isNewApp -> stringResource(R.string.watchdog_new_app)
                            change.versionBumped -> stringResource(R.string.watchdog_after_update)
                            else -> stringResource(R.string.watchdog_newly_granted)
                        },
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            change.addedPermissions.forEach { perm ->
                Text(
                    "+ $perm",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
        }
    }
}
