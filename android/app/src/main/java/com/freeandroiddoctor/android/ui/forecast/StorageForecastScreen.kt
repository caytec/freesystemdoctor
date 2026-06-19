package com.freeandroiddoctor.android.ui.forecast

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.util.ByteFormatter
import com.freeandroiddoctor.android.engine.forecast.ForecastResult
import com.freeandroiddoctor.android.engine.forecast.Snapshot
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.ShimmerList

@Composable
fun StorageForecastScreen(
    modifier: Modifier = Modifier,
    viewModel: StorageForecastViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear { InfoBanner(stringResource(R.string.storage_forecast_note)) }

        when {
            state.loading -> ShimmerList()
            state.result == null -> Text(stringResource(R.string.empty))
            else -> {
                val result = state.result!!
                Appear(index = 1) { BigNumberCard(result) }
                if (result.snapshots.size >= 2) {
                    Appear(index = 2) { TrendChart(result.snapshots) }
                }
                Appear(index = 3) {
                    OutlinedButton(
                        onClick = {
                            runCatching {
                                val intent = context.packageManager
                                    .getLaunchIntentForPackage(context.packageName)
                                intent?.let { context.startActivity(it) }
                            }
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text(stringResource(R.string.storage_forecast_open_cleaner)) }
                }
                Text(
                    stringResource(R.string.storage_forecast_disclaimer),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun BigNumberCard(result: ForecastResult) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(Modifier.padding(20.dp)) {
            val headline = when (result.state) {
                ForecastResult.State.GATHERING ->
                    stringResource(R.string.storage_forecast_gathering, 7 - result.snapshots.size)
                ForecastResult.State.NO_TREND -> stringResource(R.string.storage_forecast_no_trend)
                ForecastResult.State.OVER_YEAR -> stringResource(R.string.storage_forecast_over_year)
                ForecastResult.State.COUNTDOWN ->
                    stringResource(R.string.storage_forecast_days_left, (result.daysUntilFull ?: 0L).toInt())
            }
            Text(headline, style = MaterialTheme.typography.headlineSmall)
            Text(
                stringResource(R.string.storage_forecast_free_now, ByteFormatter.format(result.freeNowBytes)),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 6.dp),
            )
        }
    }
}

@Composable
private fun TrendChart(snapshots: List<Snapshot>) {
    val color = MaterialTheme.colorScheme.primary
    val grid = MaterialTheme.colorScheme.outlineVariant
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Box(
            modifier = Modifier.fillMaxWidth().padding(16.dp).height(160.dp),
            contentAlignment = Alignment.Center,
        ) {
            Canvas(modifier = Modifier.fillMaxSize()) {
                if (snapshots.size < 2) return@Canvas
                val tsRange = snapshots.last().timestamp - snapshots.first().timestamp
                val minY = snapshots.minOf { it.freeBytes }
                val maxY = snapshots.maxOf { it.freeBytes }
                val yRange = (maxY - minY).coerceAtLeast(1)

                // Grid baseline.
                drawLine(
                    color = grid,
                    start = Offset(0f, size.height - 1f),
                    end = Offset(size.width, size.height - 1f),
                    strokeWidth = 1f,
                )

                val path = Path()
                snapshots.forEachIndexed { i, s ->
                    val x = if (tsRange == 0L) 0f
                    else (s.timestamp - snapshots.first().timestamp).toFloat() / tsRange * size.width
                    val y = size.height - ((s.freeBytes - minY).toFloat() / yRange) * size.height
                    if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
                }
                drawPath(
                    path = path,
                    color = color,
                    style = Stroke(width = 4f, cap = StrokeCap.Round),
                )
                snapshots.forEach { s ->
                    val x = if (tsRange == 0L) 0f
                    else (s.timestamp - snapshots.first().timestamp).toFloat() / tsRange * size.width
                    val y = size.height - ((s.freeBytes - minY).toFloat() / yRange) * size.height
                    drawCircle(color = color, radius = 4f, center = Offset(x, y))
                }
            }
            if (snapshots.isEmpty()) {
                Text("—", color = Color.Gray)
            }
        }
    }
}
