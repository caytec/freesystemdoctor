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
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BatteryFull
import androidx.compose.material.icons.filled.CleaningServices
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material.icons.filled.ShieldMoon
import androidx.compose.material.icons.filled.Storage
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.util.ByteFormatter
import com.freesystemdoctor.android.ui.components.Appear
import com.freesystemdoctor.android.ui.components.GlassCard
import com.freesystemdoctor.android.ui.components.HealthGauge
import com.freesystemdoctor.android.ui.components.Refreshable
import com.freesystemdoctor.android.ui.components.SectionHeader
import com.freesystemdoctor.android.ui.components.StatCard
import com.freesystemdoctor.android.ui.components.bounceClick
import com.freesystemdoctor.android.ui.navigation.ToolRoutes
import com.freesystemdoctor.android.ui.theme.Coral
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
    onNavigate: (String) -> Unit = {},
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
        state.networkPrivacy?.let { net ->
            add {
                val score = net.score
                val accent = when {
                    score >= 75 -> GoodGreen
                    score >= 50 -> WarnAmber
                    else -> BadRed
                }
                StatCard(
                    title = stringRes(R.string.dashboard_privacy_score),
                    value = "$score",
                    subtitle = stringRes(R.string.dashboard_privacy_subtitle),
                    progress = score / 100f,
                    icon = Icons.Filled.ShieldMoon,
                    accent = accent,
                    modifier = Modifier.bounceClick { onNavigate(ToolRoutes.PRIVACY_AUDIT) },
                )
            }
        }
    }

    BoxWithConstraints(modifier = modifier.fillMaxSize()) {
        val columns = if (maxWidth >= 600.dp) 2 else 1
        val isWide = maxWidth >= 600.dp
        val scroll = rememberScrollState()
        Refreshable(isRefreshing = state.loading, onRefresh = viewModel::refresh) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(scroll)
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Appear {
                    GlassCard(modifier = Modifier
                        .fillMaxWidth()
                        .graphicsLayer { translationY = scroll.value * 0.3f }) {
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

                if (!isWide) {
                    Appear(index = 1) {
                        QuickActionsRow(onNavigate = onNavigate)
                    }
                }

                SectionHeader(stringRes(R.string.dashboard_overview))

                cards.chunked(columns).forEachIndexed { rowIndex, row ->
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        row.forEachIndexed { colIndex, card ->
                            Box(Modifier.weight(1f)) {
                                Appear(index = rowIndex * columns + colIndex + 2) { card() }
                            }
                        }
                        repeat(columns - row.size) { Spacer(Modifier.weight(1f)) }
                    }
                }
            }
        }
    }
}

@Composable
private fun QuickActionsRow(onNavigate: (String) -> Unit) {
    data class QuickAction(val labelRes: Int, val icon: ImageVector, val route: String, val accent: Color)
    val actions = listOf(
        QuickAction(R.string.nav_cleaner, Icons.Filled.CleaningServices, "cleaner", Coral),
        QuickAction(R.string.tool_duplicates, Icons.Filled.ContentCopy, ToolRoutes.DUPLICATES, Violet),
        QuickAction(R.string.tool_battery, Icons.Filled.BatteryFull, ToolRoutes.BATTERY, GoodGreen),
    )
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        actions.forEach { action ->
            GlassCard(
                modifier = Modifier.weight(1f).height(88.dp).bounceClick { onNavigate(action.route) },
            ) {
                Column(
                    modifier = Modifier.fillMaxSize().padding(12.dp),
                    verticalArrangement = Arrangement.SpaceBetween,
                ) {
                    Box(
                        modifier = Modifier
                            .size(36.dp)
                            .background(
                                action.accent.copy(alpha = 0.18f),
                                shape = androidx.compose.foundation.shape.RoundedCornerShape(10.dp),
                            ),
                        contentAlignment = Alignment.Center,
                    ) {
                        androidx.compose.material3.Icon(
                            action.icon,
                            contentDescription = null,
                            tint = action.accent,
                            modifier = Modifier.size(20.dp),
                        )
                    }
                    Text(
                        stringRes(action.labelRes),
                        style = MaterialTheme.typography.labelSmall,
                        maxLines = 1,
                        overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
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
