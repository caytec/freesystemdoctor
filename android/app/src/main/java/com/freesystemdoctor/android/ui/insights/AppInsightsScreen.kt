package com.freesystemdoctor.android.ui.insights

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.ui.components.Appear
import com.freesystemdoctor.android.ui.components.InfoBanner
import com.freesystemdoctor.android.ui.components.PermissionGate
import com.freesystemdoctor.android.ui.components.SectionHeader
import com.freesystemdoctor.android.ui.components.ShimmerList
import java.text.DateFormat
import java.util.Date
import java.util.concurrent.TimeUnit

@Composable
fun AppInsightsScreen(
    modifier: Modifier = Modifier,
    viewModel: AppInsightsViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (state.needsUsageAccess) {
            PermissionGate(
                message = stringResource(R.string.app_usage_need_access),
                actionLabel = stringResource(R.string.perm_grant),
                onAction = {
                    runCatching { context.startActivity(viewModel.usageAccessIntent()) }
                },
            )
        }

        when {
            state.loading -> ShimmerList()
            state.report == null -> Text(stringResource(R.string.empty))
            else -> {
                val report = state.report!!
                Appear { InfoBanner(stringResource(R.string.app_insights_note)) }

                Appear(index = 1) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceContainer,
                        ),
                        shape = MaterialTheme.shapes.medium,
                    ) {
                        Column(Modifier.padding(16.dp)) {
                            Text(
                                stringResource(R.string.app_insights_weekly_total),
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                            Text(
                                formatHours(report.weeklyTotalMillis),
                                style = MaterialTheme.typography.headlineSmall,
                            )
                            WeeklyChart(
                                values = report.perDay.map { it.foregroundMillis },
                                labels = report.perDay.map { it.dayLabel },
                                modifier = Modifier.fillMaxWidth().height(140.dp).padding(top = 12.dp),
                            )
                        }
                    }
                }

                SectionHeader(stringResource(R.string.app_insights_recent))
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                    modifier = Modifier.height(220.dp),
                ) {
                    items(report.recentlyInstalled, key = { it.packageName + it.timestamp }) { ev ->
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.surfaceContainer,
                            ),
                            shape = MaterialTheme.shapes.small,
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth()
                                    .padding(horizontal = 12.dp, vertical = 8.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                Column(Modifier.weight(1f)) {
                                    Text(
                                        ev.label,
                                        style = MaterialTheme.typography.bodyMedium,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                    Text(
                                        if (ev.isInstall) {
                                            stringResource(R.string.app_insights_installed)
                                        } else {
                                            stringResource(R.string.app_insights_updated)
                                        },
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                                Text(
                                    DateFormat.getDateInstance(DateFormat.SHORT)
                                        .format(Date(ev.timestamp)),
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        }
                    }
                }

                if (report.hiddenApps.isNotEmpty()) {
                    SectionHeader(stringResource(R.string.app_insights_hidden))
                    LazyColumn(
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                        modifier = Modifier.height(220.dp),
                    ) {
                        items(report.hiddenApps, key = { it.packageName }) { hidden ->
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                colors = CardDefaults.cardColors(
                                    containerColor = MaterialTheme.colorScheme.surfaceContainer,
                                ),
                                shape = MaterialTheme.shapes.small,
                            ) {
                                Column(Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
                                    Text(
                                        hidden.label,
                                        style = MaterialTheme.typography.bodyMedium,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                    Text(
                                        hidden.packageName,
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun WeeklyChart(
    values: List<Long>,
    labels: List<String>,
    modifier: Modifier = Modifier,
) {
    val max = (values.maxOrNull() ?: 0L).coerceAtLeast(1L)
    val barColor = MaterialTheme.colorScheme.primary
    val labelColor = MaterialTheme.colorScheme.onSurfaceVariant
    Column(modifier) {
        Box(
            modifier = Modifier.fillMaxWidth().weight(1f),
            contentAlignment = Alignment.BottomStart,
        ) {
            Canvas(modifier = Modifier.fillMaxSize()) {
                if (values.isEmpty()) return@Canvas
                val gap = 8.dp.toPx()
                val barWidth = (size.width - gap * (values.size - 1)) / values.size
                values.forEachIndexed { i, v ->
                    val h = (v.toFloat() / max.toFloat()) * size.height
                    val left = i * (barWidth + gap)
                    drawRect(
                        color = barColor.copy(alpha = 0.85f),
                        topLeft = androidx.compose.ui.geometry.Offset(left, size.height - h),
                        size = androidx.compose.ui.geometry.Size(barWidth, h),
                    )
                }
            }
        }
        Row(Modifier.fillMaxWidth().padding(top = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
            labels.forEach { label ->
                Text(label, style = MaterialTheme.typography.labelSmall, color = labelColor)
            }
        }
    }
}

private fun formatHours(ms: Long): String {
    if (ms <= 0) return "0m"
    val h = TimeUnit.MILLISECONDS.toHours(ms)
    val m = TimeUnit.MILLISECONDS.toMinutes(ms) % 60
    return if (h > 0) "${h}h ${m}m" else "${m}m"
}
