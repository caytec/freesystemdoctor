package com.freesystemdoctor.android.ui.battery.health

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
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.battery.BatteryHealthReport
import com.freesystemdoctor.android.ui.components.InfoBanner
import kotlinx.coroutines.launch

@Composable
fun BatteryHealthScreen(modifier: Modifier = Modifier) {
    val scope = rememberCoroutineScope()
    var report by remember { mutableStateOf<BatteryHealthReport?>(null) }
    LaunchedEffect(Unit) {
        scope.launch { report = ServiceLocator.batteryHealthEngine.compute() }
    }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoBanner(stringResource(R.string.battery_health_note))

        val r = report
        when {
            r == null -> Text(stringResource(R.string.loading))
            r.measuredCapacityMah == null -> Text(
                stringResource(R.string.battery_health_not_enough_data),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            else -> {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
                    shape = MaterialTheme.shapes.medium,
                ) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(
                            stringResource(R.string.battery_health_percent, r.healthPercent ?: 0),
                            style = MaterialTheme.typography.headlineSmall,
                            color = MaterialTheme.colorScheme.primary,
                        )
                        Text(
                            "${stringResource(R.string.battery_health_capacity)}: ${r.measuredCapacityMah} mAh",
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        r.referenceCapacityMah?.let { ref ->
                            Text(
                                "${stringResource(R.string.battery_health_design)}: $ref mAh",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                        Text(
                            stringResource(R.string.battery_health_sample_count, r.sampleCount),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }
    }
}
