package com.freeandroiddoctor.android.ui.device

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
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.SectionHeader

@Composable
fun DeviceInfoScreen(
    modifier: Modifier = Modifier,
    viewModel: DeviceInfoViewModel = viewModel(),
) {
    val details by viewModel.details.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { viewModel.load() }

    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        val d = details ?: return@Column
        val rows = listOf(
            stringResource(R.string.device_manufacturer) to "${d.manufacturer} ${d.model}",
            stringResource(R.string.device_codename) to "${d.device} / ${d.board}",
            stringResource(R.string.device_hardware) to d.hardware,
            stringResource(R.string.device_android) to "${d.androidVersion} (API ${d.sdkInt})",
            stringResource(R.string.device_patch) to d.securityPatch,
            stringResource(R.string.device_kernel) to d.kernel,
            stringResource(R.string.device_cpu) to buildString {
                append("${d.cpuCores} cores")
                d.cpuMaxFreqMhz?.let { append(" · ${it} MHz") }
            },
            stringResource(R.string.device_abis) to d.supportedAbis.joinToString(", "),
        )

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
                            Text(value, style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }
            }
        }

        SectionHeader(stringResource(R.string.device_sensors, d.sensors.size))
        Appear(index = 1) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
                shape = MaterialTheme.shapes.medium,
            ) {
                Column(Modifier.padding(16.dp)) {
                    d.sensors.forEach { sensor ->
                        Text(
                            sensor,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(vertical = 2.dp),
                        )
                    }
                }
            }
        }
    }
}
