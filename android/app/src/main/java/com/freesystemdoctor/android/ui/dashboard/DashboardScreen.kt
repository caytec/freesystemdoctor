package com.freesystemdoctor.android.ui.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BatteryFull
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material.icons.filled.Storage
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.util.ByteFormatter
import com.freesystemdoctor.android.ui.components.Appear
import com.freesystemdoctor.android.ui.components.GlassCard
import com.freesystemdoctor.android.ui.components.HealthGauge
import com.freesystemdoctor.android.ui.components.SectionHeader
import com.freesystemdoctor.android.ui.components.StatCard
import com.freesystemdoctor.android.ui.theme.GoodGreen
import com.freesystemdoctor.android.ui.theme.SkyBlue
import com.freesystemdoctor.android.ui.theme.Violet
import com.freesystemdoctor.android.ui.theme.WarnAmber
import com.freesystemdoctor.android.ui.theme.BadRed
import com.freesystemdoctor.android.ui.theme.accentGlow
import com.freesystemdoctor.android.ui.theme.heroGradient
import androidx.compose.ui.graphics.Color
import java.util.Locale

private fun scoreGlow(score: Int): Color = when {
    score >= 80 -> GoodGreen
    score >= 50 -> WarnAmber
    else -> BadRed
}

@Composable
fun DashboardScreen(
    modifier: Modifier = Modifier,
    viewModel: DashboardViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    val cards = buildList<@Composable () -> Unit> {
        state.volume?.let { v ->
            add {
                StatCard(
                    title = stringRes(R.string.dashboard_storage),
                    value = ByteFormatter.format(v.usedBytes),
                    subtitle = formatRes(
                        R.string.storage_used_of,
                        ByteFormatter.format(v.usedBytes),
                        ByteFormatter.format(v.totalBytes),
                    ),
                    progress = v.usedFraction,
                    icon = Icons.Filled.Storage,
                    accent = SkyBlue,
                )
            }
        }
        state.memory?.let { m ->
            add {
                StatCard(
                    title = stringRes(R.string.dashboard_memory),
                    value = ByteFormatter.format(m.usedBytes),
                    subtitle = formatRes(
                        R.string.ram_used_of,
                        ByteFormatter.format(m.usedBytes),
                        ByteFormatter.format(m.totalBytes),
                    ),
                    progress = m.usedFraction,
                    icon = Icons.Filled.Memory,
                    accent = Violet,
                )
            }
        }
        state.battery?.let { b ->
            add {
                StatCard(
                    title = stringRes(R.string.dashboard_battery),
                    value = formatRes(R.string.battery_level, b.levelPercent),
                    subtitle = formatRes(
                        R.string.battery_temp,
                        String.format(Locale.US, "%.1f°C", b.temperatureCelsius),
                    ),
                    progress = b.levelPercent / 100f,
                    icon = Icons.Filled.BatteryFull,
                    accent = GoodGreen,
                )
            }
        }
        state.device?.let { d ->
            add {
                StatCard(
                    title = stringRes(R.string.dashboard_device),
                    value = "${d.manufacturer} ${d.model}",
                    subtitle = "Android ${d.androidVersion} (API ${d.sdkInt}) · ${d.cpuCores} cores",
                    icon = Icons.Filled.PhoneAndroid,
                )
            }
        }
    }

    BoxWithConstraints(modifier = modifier.fillMaxSize()) {
        val columns = if (maxWidth >= 600.dp) 2 else 1
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Appear {
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Box(
                        Modifier
                            .fillMaxWidth()
                            .background(heroGradient())
                            .padding(vertical = 16.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        Box(
                            Modifier
                                .size(220.dp)
                                .background(accentGlow(scoreGlow(state.healthScore))),
                            contentAlignment = Alignment.Center,
                        ) {
                            HealthGauge(
                                score = state.healthScore,
                                label = stringRes(R.string.health_score),
                            )
                        }
                    }
                }
            }

            SectionHeader(stringRes(R.string.dashboard_overview))

            cards.chunked(columns).forEachIndexed { rowIndex, row ->
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    row.forEachIndexed { colIndex, card ->
                        Box(Modifier.weight(1f)) {
                            Appear(index = rowIndex * columns + colIndex + 1) { card() }
                        }
                    }
                    repeat(columns - row.size) { Spacer(Modifier.weight(1f)) }
                }
            }
        }
    }
}

@Composable
private fun stringRes(id: Int): String =
    androidx.compose.ui.platform.LocalContext.current.getString(id)

@Composable
private fun formatRes(id: Int, vararg args: Any): String =
    androidx.compose.ui.platform.LocalContext.current.getString(id, *args)
