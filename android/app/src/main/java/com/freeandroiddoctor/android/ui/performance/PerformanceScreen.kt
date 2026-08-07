package com.freeandroiddoctor.android.ui.performance

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.util.ByteFormatter
import com.freeandroiddoctor.android.engine.performance.Bottleneck
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.ShimmerList
import com.freeandroiddoctor.android.ui.components.StatCard
import com.freeandroiddoctor.android.ui.theme.BadRed
import com.freeandroiddoctor.android.ui.theme.GoodGreen
import com.freeandroiddoctor.android.ui.theme.WarnAmber

@Composable
fun PerformanceScreen(
    modifier: Modifier = Modifier,
    viewModel: PerformanceViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { viewModel.load() }

    LazyColumn(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item("note") { InfoBanner(stringResource(R.string.perf_note)) }

        val report = state.report
        if (state.loading || report == null) {
            item("loading") { ShimmerList(rows = 5) }
        } else {
            item("summary") {
                StatCard(
                    title = stringResource(R.string.perf_summary_title),
                    value = if (report.healthy) {
                        stringResource(R.string.perf_summary_healthy)
                    } else {
                        stringResource(R.string.perf_summary_issues, report.bottlenecks.size)
                    },
                    subtitle = report.thermalHeadroom?.let {
                        stringResource(R.string.perf_headroom, (it * 100).toInt())
                    } ?: stringResource(R.string.perf_headroom_unavailable),
                    accent = if (report.healthy) GoodGreen else WarnAmber,
                )
            }

            if (report.bottlenecks.isEmpty()) {
                item("clean") {
                    Text(
                        stringResource(R.string.perf_nothing_found),
                        color = GoodGreen,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            } else {
                items(report.bottlenecks, key = { it.kind.name }) { b ->
                    BottleneckCard(b, modifier = Modifier.animateItem())
                }
            }

            // Cache reclamation is storage, never speed — the copy says so explicitly.
            item("cache") {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surfaceContainer,
                    ),
                    shape = MaterialTheme.shapes.medium,
                ) {
                    Column(Modifier.padding(14.dp)) {
                        Text(
                            stringResource(R.string.perf_cache_title),
                            style = MaterialTheme.typography.titleSmall,
                        )
                        Text(
                            stringResource(
                                R.string.perf_cache_body,
                                ByteFormatter.format(report.reclaimableCacheBytes),
                            ),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(top = 4.dp),
                        )
                        OutlinedButton(
                            onClick = viewModel::reclaimCache,
                            enabled = !state.reclaiming,
                            modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                        ) { Text(stringResource(R.string.perf_cache_action)) }

                        state.lastReclaimedBytes?.let { freed ->
                            Text(
                                stringResource(
                                    R.string.perf_cache_result,
                                    ByteFormatter.format(freed),
                                ),
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.secondary,
                                modifier = Modifier.padding(top = 6.dp),
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun BottleneckCard(b: Bottleneck, modifier: Modifier = Modifier) {
    val color = severityColor(b.severity)
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(14.dp),
            verticalAlignment = Alignment.Top,
        ) {
            Text(
                when (b.severity) {
                    Bottleneck.Severity.CRITICAL -> "!!"
                    Bottleneck.Severity.WARN -> "!"
                    Bottleneck.Severity.INFO -> "i"
                },
                color = color,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(end = 12.dp),
            )
            Column {
                Text(
                    stringResource(titleFor(b.kind)),
                    style = MaterialTheme.typography.titleSmall,
                )
                Text(
                    stringResource(bodyFor(b.kind), b.detail),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 2.dp),
                )
            }
        }
    }
}

private fun titleFor(kind: Bottleneck.Kind): Int = when (kind) {
    Bottleneck.Kind.THERMAL_THROTTLING -> R.string.perf_thermal_title
    Bottleneck.Kind.STORAGE_CRITICAL -> R.string.perf_storage_critical_title
    Bottleneck.Kind.STORAGE_LOW -> R.string.perf_storage_low_title
    Bottleneck.Kind.BATTERY_EXEMPTIONS -> R.string.perf_exemptions_title
    Bottleneck.Kind.LOW_DEEP_SLEEP -> R.string.perf_sleep_title
    Bottleneck.Kind.BACKGROUND_TALKERS -> R.string.perf_talkers_title
    Bottleneck.Kind.MEMORY_PRESSURE -> R.string.perf_memory_title
    Bottleneck.Kind.LONG_UPTIME -> R.string.perf_uptime_title
}

private fun bodyFor(kind: Bottleneck.Kind): Int = when (kind) {
    Bottleneck.Kind.THERMAL_THROTTLING -> R.string.perf_thermal_body
    Bottleneck.Kind.STORAGE_CRITICAL -> R.string.perf_storage_critical_body
    Bottleneck.Kind.STORAGE_LOW -> R.string.perf_storage_low_body
    Bottleneck.Kind.BATTERY_EXEMPTIONS -> R.string.perf_exemptions_body
    Bottleneck.Kind.LOW_DEEP_SLEEP -> R.string.perf_sleep_body
    Bottleneck.Kind.BACKGROUND_TALKERS -> R.string.perf_talkers_body
    Bottleneck.Kind.MEMORY_PRESSURE -> R.string.perf_memory_body
    Bottleneck.Kind.LONG_UPTIME -> R.string.perf_uptime_body
}

private fun severityColor(s: Bottleneck.Severity): Color = when (s) {
    Bottleneck.Severity.CRITICAL -> BadRed
    Bottleneck.Severity.WARN -> WarnAmber
    Bottleneck.Severity.INFO -> GoodGreen
}
