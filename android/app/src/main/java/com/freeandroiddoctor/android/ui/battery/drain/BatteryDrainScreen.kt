package com.freeandroiddoctor.android.ui.battery.drain

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
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.battery.DrainEstimate
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import java.util.Locale

@Composable
fun BatteryDrainScreen(modifier: Modifier = Modifier) {
    // null = loading, so the "no data" message doesn't flash before compute() returns.
    var rows by remember { mutableStateOf<List<DrainEstimate>?>(null) }
    LaunchedEffect(Unit) { rows = ServiceLocator.batteryDrainEngine.compute() }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoBanner(stringResource(R.string.battery_drain_note))
        val current = rows
        val phase = when {
            current == null -> "loading"
            current.isEmpty() -> "empty"
            else -> "content"
        }
        AnimatedContent(
            targetState = phase,
            transitionSpec = {
                slideInVertically(tween(260)) { -it / 2 } + fadeIn(tween(260)) togetherWith
                    slideOutVertically(tween(180)) { it / 2 } + fadeOut(tween(180))
            },
            label = "batteryDrainPhase",
        ) { targetPhase ->
            when (targetPhase) {
                "loading" -> com.freeandroiddoctor.android.ui.components.ShimmerList(rows = 5)
                "empty" -> Text(
                    stringResource(R.string.battery_drain_empty),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                else -> {
                    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        itemsIndexed(current.orEmpty(), key = { _, r -> r.packageName }) { index, r ->
                            Appear(index = index) {
                                Card(
                                    modifier = Modifier.fillMaxWidth().animateItem(),
                                    colors = CardDefaults.cardColors(
                                        containerColor = MaterialTheme.colorScheme.surfaceContainer,
                                    ),
                                    shape = MaterialTheme.shapes.medium,
                                ) {
                                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                        Text(r.label, style = MaterialTheme.typography.titleSmall)
                                        Text(
                                            stringResource(
                                                R.string.battery_drain_row,
                                                r.foregroundMinutes,
                                                String.format(Locale.US, "%.1f", r.weight),
                                            ),
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
        }
    }
}
