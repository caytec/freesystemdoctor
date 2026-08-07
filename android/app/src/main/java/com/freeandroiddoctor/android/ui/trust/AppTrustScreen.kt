package com.freeandroiddoctor.android.ui.trust

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.util.ByteFormatter
import com.freeandroiddoctor.android.engine.trust.AppTrust
import com.freeandroiddoctor.android.engine.trust.TrustDeduction
import com.freeandroiddoctor.android.engine.trust.TrustProgress
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.StatCard
import com.freeandroiddoctor.android.ui.theme.BadRed
import com.freeandroiddoctor.android.ui.theme.GoodGreen
import com.freeandroiddoctor.android.ui.theme.WarnAmber

@Composable
fun AppTrustScreen(
    modifier: Modifier = Modifier,
    viewModel: AppTrustViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current

    LazyColumn(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item("note") { InfoBanner(stringResource(R.string.trust_note)) }

        item("scan") {
            Button(
                onClick = viewModel::scan,
                enabled = !state.scanning,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(stringResource(R.string.trust_scan)) }
        }

        if (state.scanning) {
            item("progress") {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                    Text(
                        stringResource(phaseLabel(state.phase)),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }

        val report = state.report
        if (state.scanned && report != null) {
            item("avg") {
                StatCard(
                    title = stringResource(R.string.trust_average_title),
                    value = "${report.averageScore}/100",
                    subtitle = stringResource(R.string.trust_average_subtitle, report.apps.size),
                    accent = scoreColor(report.averageScore),
                )
            }
            if (report.apps.isEmpty()) {
                item("empty") {
                    Text(
                        stringResource(R.string.trust_empty),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            } else {
                item("header") {
                    Text(
                        stringResource(R.string.trust_least_header),
                        style = MaterialTheme.typography.titleMedium,
                    )
                }
                items(report.leastTrusted, key = { it.packageName }) { app ->
                    TrustCard(
                        app = app,
                        onManage = {
                            runCatching {
                                context.startActivity(viewModel.appDetailsIntent(app.packageName))
                            }
                        },
                        modifier = Modifier.animateItem(),
                    )
                }
            }
        }
    }
}

@Composable
private fun TrustCard(
    app: AppTrust,
    onManage: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val color = scoreColor(app.score)
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(44.dp)
                        .clip(CircleShape)
                        .background(color.copy(alpha = 0.18f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        app.grade.name,
                        style = MaterialTheme.typography.titleMedium,
                        color = color,
                        fontWeight = FontWeight.Bold,
                    )
                }
                Column(Modifier.weight(1f).padding(start = 12.dp)) {
                    Text(
                        app.label,
                        style = MaterialTheme.typography.titleSmall,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        stringResource(R.string.trust_score_of, app.score),
                        style = MaterialTheme.typography.bodySmall,
                        color = color,
                    )
                }
            }

            // The whole point: every deduction is spelled out.
            app.deductions.forEach { d ->
                Text(
                    "−${d.points}  " + stringResource(deductionLabel(d), d.detail),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
            if (app.deductions.isEmpty()) {
                Text(
                    stringResource(R.string.trust_no_findings),
                    style = MaterialTheme.typography.bodySmall,
                    color = GoodGreen,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
            if (app.backgroundBytes > 0) {
                Text(
                    stringResource(
                        R.string.trust_background_detail,
                        ByteFormatter.format(app.backgroundBytes),
                    ),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
            TextButton(onClick = onManage, modifier = Modifier.padding(top = 4.dp)) {
                Text(stringResource(R.string.trust_manage))
            }
        }
    }
}

private fun deductionLabel(d: TrustDeduction): Int = when (d.kind) {
    TrustDeduction.Kind.TRACKERS -> R.string.trust_reason_trackers
    TrustDeduction.Kind.DANGEROUS_PERMISSIONS -> R.string.trust_reason_permissions
    TrustDeduction.Kind.RISK_SIGNALS -> R.string.trust_reason_risk
    TrustDeduction.Kind.BACKGROUND_TRAFFIC -> R.string.trust_reason_traffic
}

private fun phaseLabel(phase: TrustProgress.Phase?): Int = when (phase) {
    TrustProgress.Phase.TRACKERS -> R.string.trust_phase_trackers
    TrustProgress.Phase.PERMISSIONS -> R.string.trust_phase_permissions
    TrustProgress.Phase.RISK -> R.string.trust_phase_risk
    TrustProgress.Phase.NETWORK -> R.string.trust_phase_network
    else -> R.string.trust_phase_combining
}

private fun scoreColor(score: Int): Color = when {
    score >= 70 -> GoodGreen
    score >= 45 -> WarnAmber
    else -> BadRed
}
