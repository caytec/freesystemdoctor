package com.freeandroiddoctor.android.ui.regression

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.util.ByteFormatter
import com.freeandroiddoctor.android.engine.performance.Regression
import com.freeandroiddoctor.android.engine.performance.RegressionReport
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.ShimmerList
import com.freeandroiddoctor.android.ui.theme.GoodGreen
import java.text.DateFormat
import java.util.Date

@Composable
fun RegressionScreen(
    modifier: Modifier = Modifier,
    viewModel: RegressionViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { viewModel.load() }

    LazyColumn(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item("note") { InfoBanner(stringResource(R.string.regress_note)) }

        val report = state.report
        when {
            state.loading || report == null -> item("loading") { ShimmerList(rows = 4) }

            report.state == RegressionReport.State.GATHERING -> item("gathering") {
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
                                stringResource(R.string.regress_gathering_title),
                                style = MaterialTheme.typography.titleSmall,
                            )
                            Text(
                                stringResource(
                                    R.string.regress_gathering_body,
                                    report.snapshotCount,
                                ),
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.padding(top = 4.dp),
                            )
                        }
                    }
                    OutlinedButton(
                        onClick = viewModel::sampleNow,
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text(stringResource(R.string.regress_sample_now)) }
                }
            }

            report.regressions.isEmpty() -> item("clean") {
                Text(
                    stringResource(R.string.regress_none, report.snapshotCount),
                    color = GoodGreen,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }

            else -> {
                item("header") {
                    Text(
                        stringResource(R.string.regress_header, report.regressions.size),
                        style = MaterialTheme.typography.titleMedium,
                    )
                }
                items(report.regressions, key = { it.packageName }) { r ->
                    RegressionCard(r, modifier = Modifier.animateItem())
                }
                item("disclaimer") {
                    Text(
                        stringResource(R.string.regress_disclaimer),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}

@Composable
private fun RegressionCard(r: Regression, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(Modifier.padding(14.dp)) {
            Text(
                r.label,
                style = MaterialTheme.typography.titleSmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                stringResource(
                    if (r.wasInstall) R.string.regress_since_install else R.string.regress_since_update,
                    DateFormat.getDateInstance(DateFormat.MEDIUM).format(Date(r.eventAt)),
                ),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (r.awakeDeltaPoints > 0) {
                Text(
                    stringResource(R.string.regress_awake, r.awakeDeltaPoints),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.padding(top = 6.dp),
                )
            }
            if (r.backgroundDeltaBytes > 0) {
                Text(
                    stringResource(
                        R.string.regress_background,
                        ByteFormatter.format(r.backgroundDeltaBytes),
                    ),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.padding(top = 2.dp),
                )
            }
        }
    }
}
