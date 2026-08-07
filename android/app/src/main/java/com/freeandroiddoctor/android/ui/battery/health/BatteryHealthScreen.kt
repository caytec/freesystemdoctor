package com.freeandroiddoctor.android.ui.battery.health

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.battery.BatteryHealthReport
import com.freeandroiddoctor.android.ui.components.InfoBanner
import kotlinx.coroutines.launch

@Composable
fun BatteryHealthScreen(modifier: Modifier = Modifier) {
    val scope = rememberCoroutineScope()
    var report by remember { mutableStateOf<BatteryHealthReport?>(null) }
    LaunchedEffect(Unit) {
        scope.launch { report = ServiceLocator.batteryHealthEngine.compute() }
    }

    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoBanner(stringResource(R.string.battery_health_note))

        val r = report
        val phase = when {
            r == null -> "loading"
            r.measuredCapacityMah == null -> "empty"
            else -> "content"
        }
        AnimatedContent(
            targetState = phase,
            transitionSpec = {
                slideInVertically(tween(260)) { -it / 2 } + fadeIn(tween(260)) togetherWith
                    slideOutVertically(tween(180)) { it / 2 } + fadeOut(tween(180))
            },
            label = "batteryHealthPhase",
        ) { targetPhase ->
            when (targetPhase) {
                "loading" -> Text(stringResource(R.string.loading))
                "empty" -> Text(
                    stringResource(R.string.battery_health_not_enough_data),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                else -> {
                    val rr = r!!
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
                        shape = MaterialTheme.shapes.medium,
                    ) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text(
                                stringResource(R.string.battery_health_percent, rr.healthPercent ?: 0),
                                style = MaterialTheme.typography.headlineSmall,
                                color = MaterialTheme.colorScheme.primary,
                            )
                            Text(
                                "${stringResource(R.string.battery_health_capacity)}: ${rr.measuredCapacityMah} mAh",
                                style = MaterialTheme.typography.bodyMedium,
                            )
                            rr.referenceCapacityMah?.let { ref ->
                                Text(
                                    "${stringResource(R.string.battery_health_design)}: $ref mAh",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            Text(
                                stringResource(R.string.battery_health_sample_count, rr.sampleCount),
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
