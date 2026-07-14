package com.freeandroiddoctor.android.ui.privacy

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.data.quota.DailyQuotaStore
import com.freeandroiddoctor.android.engine.privacy.ApkRiskReport
import com.freeandroiddoctor.android.engine.privacy.NetworkPrivacyReport
import com.freeandroiddoctor.android.engine.privacy.PrivacyDot
import com.freeandroiddoctor.android.engine.privacy.RiskSignal
import com.freeandroiddoctor.android.ui.components.QuotaGatedButton
import com.freeandroiddoctor.android.ui.components.SectionHeader
import com.freeandroiddoctor.android.ui.navigation.ToolRoutes
import com.freeandroiddoctor.android.ui.theme.BadRed
import com.freeandroiddoctor.android.ui.theme.GoodGreen
import com.freeandroiddoctor.android.ui.theme.WarnAmber

@Composable
fun PrivacyAuditScreen(viewModel: PrivacyAuditViewModel = viewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LazyColumn(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 12.dp),
    ) {
        item {
            ScoreCard(
                privacyScore = state.report?.privacyScore ?: state.network?.score ?: 0,
                networkScore = state.network?.score ?: 0,
                running = state.running,
            )
        }
        item { state.network?.let { NetworkRow(it) } }
        item {
            QuotaGatedButton(
                text = if (state.running) {
                    stringResource(R.string.privacy_running)
                } else if (state.report == null) {
                    stringResource(R.string.privacy_run_scan)
                } else {
                    stringResource(R.string.privacy_run_scan_again)
                },
                quotaKey = DailyQuotaStore.Key.PRIVACY_DEEP_AUDIT,
                unlockRoute = ToolRoutes.PRIVACY_AUDIT,
                enabled = !state.running,
                onConsume = { viewModel.runAudit() },
            )
        }
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Switch(checked = state.includeSystem, onCheckedChange = viewModel::setIncludeSystem)
                Text(
                    text = stringResource(R.string.privacy_include_system),
                    modifier = Modifier.padding(start = 8.dp),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
        state.report?.apps?.takeIf { it.isNotEmpty() }?.let { apps ->
            item {
                SectionHeader(text = stringResource(R.string.privacy_apps_header, apps.size))
            }
            items(apps, key = { it.packageName }) { app ->
                RiskAppRow(app, modifier = Modifier.animateItem())
            }
        }
    }
}

@Composable
private fun ScoreCard(privacyScore: Int, networkScore: Int, running: Boolean) {
    val color = when {
        privacyScore >= 80 -> GoodGreen
        privacyScore >= 50 -> WarnAmber
        else -> BadRed
    }
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        shape = MaterialTheme.shapes.large,
    ) {
        Column(Modifier.padding(20.dp)) {
            Text(
                text = stringResource(R.string.privacy_score_title),
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                text = "$privacyScore",
                style = MaterialTheme.typography.displayMedium,
                color = color,
            )
            Text(
                text = if (running) stringResource(R.string.privacy_running)
                else stringResource(R.string.privacy_score_subtitle, networkScore),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun NetworkRow(report: NetworkPrivacyReport) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                text = stringResource(R.string.privacy_network_header),
                style = MaterialTheme.typography.titleSmall,
            )
            DotRow(stringResource(R.string.privacy_dot_vpn), report.vpnActive)
            DotRow(stringResource(R.string.privacy_dot_dns), report.privateDns)
            DotRow(stringResource(R.string.privacy_dot_wifi), report.wifiSecurity)
            DotRow(stringResource(R.string.privacy_dot_captive), report.captivePortal)
            DotRow(stringResource(R.string.privacy_dot_ipv6), report.ipv6)
        }
    }
}

@Composable
private fun DotRow(label: String, dot: PrivacyDot) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier.size(12.dp).clip(CircleShape).background(dot.color()),
        )
        Text(
            label,
            modifier = Modifier.padding(start = 12.dp),
            style = MaterialTheme.typography.bodyMedium,
        )
    }
}

private fun PrivacyDot.color(): Color = when (this) {
    PrivacyDot.GOOD -> GoodGreen
    PrivacyDot.WARN -> WarnAmber
    PrivacyDot.BAD -> BadRed
    PrivacyDot.UNKNOWN -> Color.Gray
}

@Composable
private fun RiskAppRow(app: ApkRiskReport, modifier: Modifier = Modifier) {
    val color = when {
        app.riskScore >= 70 -> BadRed
        app.riskScore >= 40 -> WarnAmber
        else -> GoodGreen
    }
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier.size(40.dp).clip(CircleShape).background(color.copy(alpha = 0.18f)),
                contentAlignment = Alignment.Center,
            ) {
                Text(text = "${app.riskScore}", style = MaterialTheme.typography.titleSmall, color = color)
            }
            Column(Modifier.padding(start = 12.dp).fillMaxWidth().weight(1f)) {
                Text(text = app.label, style = MaterialTheme.typography.bodyMedium)
                Text(
                    text = app.signals.joinToString { it.localize() },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

private fun RiskSignal.localize(): String = when (this) {
    RiskSignal.ACCESSIBILITY_SERVICE -> "Accessibility"
    RiskSignal.DEVICE_ADMIN -> "Device Admin"
    RiskSignal.DANGEROUS_PERM_HEAVY -> "Many perms"
    RiskSignal.UNKNOWN_INSTALLER -> "Sideloaded"
    RiskSignal.OUTDATED_TARGET_SDK -> "Outdated"
    RiskSignal.DEBUG_SIGNED -> "Debug build"
    RiskSignal.SUSPICIOUS_PACKAGE -> "Suspicious"
}
