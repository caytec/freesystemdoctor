package com.freesystemdoctor.android.ui.battery

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.ui.components.Appear
import com.freesystemdoctor.android.ui.components.InfoBanner
import java.util.Locale

@Composable
fun BatteryScreen(
    modifier: Modifier = Modifier,
    viewModel: BatteryViewModel = viewModel(),
) {
    val context = LocalContext.current
    val info = remember { viewModel.read() }
    val ignoring = remember { mutableStateOf(viewModel.isIgnoringOptimization()) }

    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        val rows = buildList {
            add(stringResource(R.string.battery_level_label) to "${info.levelPercent}%")
            add(
                stringResource(R.string.battery_status) to
                    if (info.isCharging) stringResource(R.string.battery_charging)
                    else stringResource(R.string.battery_discharging),
            )
            add(
                stringResource(R.string.battery_temp_label) to
                    String.format(Locale.US, "%.1f °C", info.temperatureCelsius),
            )
            add(
                stringResource(R.string.battery_voltage) to
                    String.format(Locale.US, "%.2f V", info.voltageVolts),
            )
            if (info.technology.isNotBlank()) {
                add(stringResource(R.string.battery_technology) to info.technology)
            }
            info.chargeCounterMah?.let {
                add(stringResource(R.string.battery_charge_counter) to "$it mAh")
            }
        }

        Appear {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
                shape = MaterialTheme.shapes.medium,
            ) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    rows.forEach { (label, value) ->
                        Column {
                            Text(
                                label,
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                            Text(value, style = MaterialTheme.typography.titleMedium)
                        }
                    }
                }
            }
        }

        InfoBanner(stringResource(R.string.battery_no_wear))

        if (!ignoring.value) {
            OutlinedButton(onClick = {
                runCatching { context.startActivity(viewModel.ignoreBatteryIntent()) }
            }) { Text(stringResource(R.string.tweak_battery)) }
        } else {
            Text(
                stringResource(R.string.battery_opt_ignored),
                color = MaterialTheme.colorScheme.secondary,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}
