package com.freeandroiddoctor.android.ui.trackers

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.engine.privacy.AppTrackers
import com.freeandroiddoctor.android.engine.privacy.TrackerCategory
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.StatCard

@Composable
fun TrackerScannerScreen(
    modifier: Modifier = Modifier,
    viewModel: TrackerScannerViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current

    LazyColumn(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item("note") { InfoBanner(stringResource(R.string.trackers_note)) }

        item("scan") {
            Button(
                onClick = viewModel::scan,
                enabled = !state.scanning,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(stringResource(R.string.trackers_scan)) }
        }

        if (state.scanning) {
            item("progress") {
                val frac by animateFloatAsState(
                    targetValue = if (state.total == 0) 0f else state.progress.toFloat() / state.total,
                    animationSpec = tween(300, easing = FastOutSlowInEasing),
                    label = "trackerScan",
                )
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    LinearProgressIndicator(progress = { frac }, modifier = Modifier.fillMaxWidth())
                    Text(
                        stringResource(R.string.trackers_scanning, state.progress, state.total),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }

        val report = state.report
        if (state.scanned && report != null) {
            item("summary") {
                StatCard(
                    title = stringResource(R.string.trackers_summary_title),
                    value = stringResource(R.string.trackers_summary_value, report.appsWithTrackers),
                    subtitle = stringResource(R.string.trackers_summary_subtitle, report.scannedApps),
                )
            }

            if (report.topTrackers.isNotEmpty()) {
                item("topHeader") {
                    Text(
                        stringResource(R.string.trackers_top_header),
                        style = MaterialTheme.typography.titleMedium,
                    )
                }
                item("top") {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceContainer,
                        ),
                        shape = MaterialTheme.shapes.medium,
                    ) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            report.topTrackers.take(8).forEach { (sig, count) ->
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                ) {
                                    Text(sig.name, style = MaterialTheme.typography.bodyMedium)
                                    Text(
                                        stringResource(R.string.trackers_in_apps, count),
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.primary,
                                    )
                                }
                            }
                        }
                    }
                }
            }

            if (report.apps.isEmpty()) {
                item("empty") {
                    Text(
                        stringResource(R.string.trackers_none),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            } else {
                item("appsHeader") {
                    Text(
                        stringResource(R.string.trackers_apps_header),
                        style = MaterialTheme.typography.titleMedium,
                    )
                }
                items(report.apps, key = { it.packageName }) { app ->
                    AppTrackerCard(
                        app = app,
                        onManage = {
                            runCatching {
                                context.startActivity(viewModel.appDetailsIntent(app.packageName))
                            }
                        },
                        modifier = Modifier.animateItem(),
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun AppTrackerCard(
    app: AppTrackers,
    onManage: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    app.label,
                    style = MaterialTheme.typography.titleSmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f).padding(end = 8.dp),
                )
                Text(
                    stringResource(R.string.trackers_count, app.count),
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
            FlowRow(
                modifier = Modifier.fillMaxWidth().padding(top = 6.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                app.trackers.forEach { sig ->
                    AssistChip(
                        onClick = {},
                        enabled = false,
                        label = { Text(sig.name, style = MaterialTheme.typography.labelSmall) },
                        colors = AssistChipDefaults.assistChipColors(
                            disabledLabelColor = categoryColor(sig.category),
                        ),
                    )
                }
            }
            TextButton(onClick = onManage, modifier = Modifier.padding(top = 4.dp)) {
                Text(stringResource(R.string.trackers_manage))
            }
        }
    }
}

@Composable
private fun categoryColor(category: TrackerCategory) = when (category) {
    TrackerCategory.ADVERTISING -> MaterialTheme.colorScheme.error
    TrackerCategory.PROFILING -> MaterialTheme.colorScheme.error
    TrackerCategory.ANALYTICS -> MaterialTheme.colorScheme.tertiary
    TrackerCategory.ATTRIBUTION -> MaterialTheme.colorScheme.tertiary
    TrackerCategory.CRASH_REPORTING -> MaterialTheme.colorScheme.onSurfaceVariant
}
