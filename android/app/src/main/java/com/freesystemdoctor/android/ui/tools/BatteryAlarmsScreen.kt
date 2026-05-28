package com.freesystemdoctor.android.ui.tools

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.ui.components.Appear
import com.freesystemdoctor.android.ui.components.InfoBanner

@Composable
fun BatteryAlarmsScreen(
    modifier: Modifier = Modifier,
    viewModel: BatteryAlarmsViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Appear { InfoBanner(stringResource(R.string.battery_alarms_note)) }

        Appear(index = 1) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f).padding(end = 12.dp)) {
                    Text(
                        stringResource(R.string.battery_alarms_toggle),
                        style = MaterialTheme.typography.titleMedium,
                    )
                    Text(
                        stringResource(R.string.battery_alarms_subtitle),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Switch(checked = state.enabled, onCheckedChange = viewModel::setEnabled)
            }
        }

        Appear(index = 2) {
            Column {
                Text(
                    stringResource(R.string.battery_alarm_low_threshold, state.low),
                    style = MaterialTheme.typography.titleSmall,
                )
                Slider(
                    value = state.low.toFloat(),
                    onValueChange = { viewModel.setThresholds(it.toInt(), state.full) },
                    valueRange = 5f..50f,
                    steps = 8,
                )
            }
        }

        Appear(index = 3) {
            Column {
                Text(
                    stringResource(R.string.battery_alarm_full_threshold, state.full),
                    style = MaterialTheme.typography.titleSmall,
                )
                Slider(
                    value = state.full.toFloat(),
                    onValueChange = { viewModel.setThresholds(state.low, it.toInt()) },
                    valueRange = 50f..100f,
                    steps = 9,
                )
            }
        }
    }
}
