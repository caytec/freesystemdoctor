package com.freeandroiddoctor.android.ui.growth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.util.ByteFormatter
import com.freeandroiddoctor.android.engine.forecast.AppGrowth
import com.freeandroiddoctor.android.engine.forecast.GrowthReport
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.ShimmerList

@Composable
fun AppGrowthScreen(
    modifier: Modifier = Modifier,
    viewModel: AppGrowthViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { viewModel.load() }

    LazyColumn(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item("note") { InfoBanner(stringResource(R.string.growth_note)) }

        val report = state.report
        when {
            state.loading -> item("loading") { ShimmerList(rows = 5) }

            report == null || report.state == GrowthReport.State.GATHERING -> item("gathering") {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceContainer,
                        ),
                        shape = MaterialTheme.shapes.medium,
                    ) {
                        Column(Modifier.padding(16.dp)) {
                            Text(
                                stringResource(R.string.growth_gathering_title),
                                style = MaterialTheme.typography.titleSmall,
                            )
                            Text(
                                stringResource(R.string.growth_gathering_body),
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.padding(top = 4.dp),
                            )
                        }
                    }
                    OutlinedButton(
                        onClick = viewModel::snapshotNow,
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text(stringResource(R.string.growth_snapshot_now)) }
                }
            }

            report.growth.isEmpty() -> item("stable") {
                Text(
                    stringResource(R.string.growth_stable, report.windowDays),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            else -> {
                item("header") {
                    Text(
                        stringResource(R.string.growth_header, report.windowDays),
                        style = MaterialTheme.typography.titleMedium,
                    )
                }
                itemsIndexed(report.growth, key = { _, g -> g.packageName }) { index, g ->
                    Appear(index = index) {
                        GrowthCard(g, modifier = Modifier.animateItem())
                    }
                }
            }
        }
    }
}

@Composable
private fun GrowthCard(item: AppGrowth, modifier: Modifier = Modifier) {
    val grew = item.deltaBytes > 0
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(14.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f).padding(end = 8.dp)) {
                Text(
                    item.label,
                    style = MaterialTheme.typography.titleSmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    stringResource(R.string.growth_current, ByteFormatter.format(item.currentBytes)),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Text(
                (if (grew) "+" else "−") + ByteFormatter.format(
                    if (grew) item.deltaBytes else -item.deltaBytes,
                ),
                style = MaterialTheme.typography.titleSmall,
                color = if (grew) {
                    MaterialTheme.colorScheme.error
                } else {
                    MaterialTheme.colorScheme.secondary
                },
            )
        }
    }
}
