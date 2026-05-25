package com.freesystemdoctor.android.ui.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.util.ByteFormatter
import com.freesystemdoctor.android.ui.components.StatCard
import java.util.Locale

@Composable
fun DashboardScreen(
    modifier: Modifier = Modifier,
    viewModel: DashboardViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        StatCard(
            title = stringRes(R.string.health_score),
            value = "${state.healthScore}/100",
        )
        state.volume?.let { v ->
            StatCard(
                title = stringRes(R.string.dashboard_storage),
                value = ByteFormatter.format(v.usedBytes),
                subtitle = formatRes(
                    R.string.storage_used_of,
                    ByteFormatter.format(v.usedBytes),
                    ByteFormatter.format(v.totalBytes),
                ),
                progress = v.usedFraction,
            )
        }
        state.memory?.let { m ->
            StatCard(
                title = stringRes(R.string.dashboard_memory),
                value = ByteFormatter.format(m.usedBytes),
                subtitle = formatRes(
                    R.string.ram_used_of,
                    ByteFormatter.format(m.usedBytes),
                    ByteFormatter.format(m.totalBytes),
                ),
                progress = m.usedFraction,
            )
        }
        state.battery?.let { b ->
            StatCard(
                title = stringRes(R.string.dashboard_battery),
                value = formatRes(R.string.battery_level, b.levelPercent),
                subtitle = formatRes(
                    R.string.battery_temp,
                    String.format(Locale.US, "%.1f°C", b.temperatureCelsius),
                ),
            )
        }
        state.device?.let { d ->
            StatCard(
                title = stringRes(R.string.dashboard_device),
                value = "${d.manufacturer} ${d.model}",
                subtitle = "Android ${d.androidVersion} (API ${d.sdkInt}) · ${d.cpuCores} cores",
            )
        }
    }
}

@Composable
private fun stringRes(id: Int): String =
    androidx.compose.ui.platform.LocalContext.current.getString(id)

@Composable
private fun formatRes(id: Int, vararg args: Any): String =
    androidx.compose.ui.platform.LocalContext.current.getString(id, *args)
