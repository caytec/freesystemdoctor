package com.freeandroiddoctor.android.ui.freedom

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
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
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
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.ShimmerList
import com.freeandroiddoctor.android.ui.components.StatCard
import com.freeandroiddoctor.android.ui.theme.BadRed
import com.freeandroiddoctor.android.ui.theme.GoodGreen
import com.freeandroiddoctor.android.ui.theme.WarnAmber
import java.util.concurrent.TimeUnit
import kotlin.math.roundToInt

@Composable
fun BatteryFreedomScreen(
    modifier: Modifier = Modifier,
    viewModel: BatteryFreedomViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    LaunchedEffect(Unit) { viewModel.load() }

    LazyColumn(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item("note") { InfoBanner(stringResource(R.string.freedom_note)) }

        val report = state.report
        if (state.loading || report == null) {
            item("loading") { ShimmerList(rows = 5) }
        } else {
            item("sleep") {
                val awakePct = (report.awakeFraction * 100).roundToInt()
                StatCard(
                    title = stringResource(R.string.freedom_awake_title),
                    value = "$awakePct%",
                    subtitle = stringResource(
                        R.string.freedom_awake_subtitle,
                        TimeUnit.MILLISECONDS.toHours(report.deepSleepMillis).toInt(),
                        TimeUnit.MILLISECONDS.toHours(report.uptimeMillis).toInt(),
                    ),
                    accent = when {
                        awakePct <= 35 -> GoodGreen
                        awakePct <= 60 -> WarnAmber
                        else -> BadRed
                    },
                )
            }

            item("header") {
                Text(
                    stringResource(R.string.freedom_header, report.unrestricted.size),
                    style = MaterialTheme.typography.titleMedium,
                )
            }

            if (report.unrestricted.isEmpty()) {
                item("empty") {
                    Text(
                        stringResource(R.string.freedom_empty),
                        color = GoodGreen,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            } else {
                itemsIndexed(report.unrestricted, key = { _, app -> app.packageName }) { index, app ->
                    Appear(index = index) {
                        Card(
                            modifier = Modifier.fillMaxWidth().animateItem(),
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.surfaceContainer,
                            ),
                            shape = MaterialTheme.shapes.medium,
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(14.dp),
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
                                TextButton(onClick = {
                                    runCatching {
                                        context.startActivity(
                                            viewModel.appDetailsIntent(app.packageName),
                                        )
                                    }
                                }) { Text(stringResource(R.string.freedom_fix)) }
                            }
                        }
                    }
                }
                item("systemScreen") {
                    OutlinedButton(
                        onClick = {
                            runCatching {
                                context.startActivity(viewModel.batteryOptimizationIntent())
                            }
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text(stringResource(R.string.freedom_open_system)) }
                }
            }

            item("limits") {
                Text(
                    stringResource(R.string.freedom_limits),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
