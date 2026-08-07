package com.freeandroiddoctor.android.ui.regression

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
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
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.ShimmerList
import com.freeandroiddoctor.android.ui.theme.GoodGreen
import java.text.DateFormat
import java.util.Date

private enum class RegressionScreenState { LOADING, GATHERING, CLEAN, CONTENT }

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

        item("body") {
            val report = state.report
            val screenState = when {
                state.loading || report == null -> RegressionScreenState.LOADING
                report.state == RegressionReport.State.GATHERING -> RegressionScreenState.GATHERING
                report.regressions.isEmpty() -> RegressionScreenState.CLEAN
                else -> RegressionScreenState.CONTENT
            }
            AnimatedContent(
                targetState = screenState,
                transitionSpec = {
                    slideInVertically(tween(260)) { -it / 2 } + fadeIn(tween(260)) togetherWith
                        slideOutVertically(tween(180)) { it / 2 } + fadeOut(tween(180))
                },
                label = "regressionState",
            ) { s ->
                when (s) {
                    RegressionScreenState.LOADING -> ShimmerList(rows = 4)

                    RegressionScreenState.GATHERING -> {
                        val r = requireNotNull(state.report)
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
                                            r.snapshotCount,
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

                    RegressionScreenState.CLEAN -> {
                        val r = requireNotNull(state.report)
                        Text(
                            stringResource(R.string.regress_none, r.snapshotCount),
                            color = GoodGreen,
                            style = MaterialTheme.typography.bodyMedium,
                        )
                    }

                    RegressionScreenState.CONTENT -> {
                        val r = requireNotNull(state.report)
                        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            Text(
                                stringResource(R.string.regress_header, r.regressions.size),
                                style = MaterialTheme.typography.titleMedium,
                            )
                            r.regressions.forEachIndexed { index, reg ->
                                Appear(index = index) { RegressionCard(reg) }
                            }
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
