package com.freeandroiddoctor.android.ui.tools

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.service.MonitorService
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner

@Composable
fun SystemTweaksScreen(
    modifier: Modifier = Modifier,
    viewModel: SystemTweaksViewModel = viewModel(),
) {
    val context = LocalContext.current
    val monitorEnabled by viewModel.monitorEnabled.collectAsStateWithLifecycle()

    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear { InfoBanner(stringResource(R.string.tweaks_note)) }

        Appear(index = 1) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
                shape = MaterialTheme.shapes.medium,
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f).padding(end = 12.dp)) {
                        Text(stringResource(R.string.monitor_toggle), style = MaterialTheme.typography.titleMedium)
                        Text(
                            stringResource(R.string.monitor_desc),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    Switch(
                        checked = monitorEnabled,
                        onCheckedChange = { enabled ->
                            viewModel.setMonitorPref(enabled)
                            if (enabled) MonitorService.start(context) else MonitorService.stop(context)
                        },
                    )
                }
            }
        }

        TweakButton(
            index = 2,
            title = stringResource(R.string.tweak_battery),
            desc = stringResource(R.string.tweak_battery_desc),
            action = stringResource(R.string.tweak_open),
        ) { runCatching { context.startActivity(viewModel.ignoreBatteryIntent()) } }

        TweakButton(
            index = 3,
            title = stringResource(R.string.tweak_data),
            desc = stringResource(R.string.tweak_data_desc),
            action = stringResource(R.string.tweak_open),
        ) { runCatching { context.startActivity(viewModel.dataUsageIntent()) } }

        TweakButton(
            index = 4,
            title = stringResource(R.string.tweak_autostart),
            desc = stringResource(R.string.tweak_autostart_desc),
            action = stringResource(R.string.tweak_open),
        ) { runCatching { context.startActivity(viewModel.autostartIntent()) } }
    }
}

@Composable
private fun TweakButton(
    index: Int,
    title: String,
    desc: String,
    action: String,
    onClick: () -> Unit,
) {
    Appear(index = index) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
            shape = MaterialTheme.shapes.medium,
        ) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f).padding(end = 12.dp)) {
                    Text(title, style = MaterialTheme.typography.titleMedium)
                    Text(
                        desc,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                OutlinedButton(onClick = onClick) { Text(action) }
            }
        }
    }
}
