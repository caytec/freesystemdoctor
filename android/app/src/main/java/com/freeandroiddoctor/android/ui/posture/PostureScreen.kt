package com.freeandroiddoctor.android.ui.posture

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.engine.privacy.PostureCheck
import com.freeandroiddoctor.android.engine.privacy.PowerfulApp
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.ShimmerList
import com.freeandroiddoctor.android.ui.components.StatCard
import com.freeandroiddoctor.android.ui.theme.BadRed
import com.freeandroiddoctor.android.ui.theme.GoodGreen
import com.freeandroiddoctor.android.ui.theme.WarnAmber

@Composable
fun PostureScreen(
    modifier: Modifier = Modifier,
    viewModel: PostureViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    LaunchedEffect(Unit) { viewModel.load() }

    LazyColumn(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item("note") { InfoBanner(stringResource(R.string.posture_note)) }

        val report = state.report
        if (state.loading || report == null) {
            item("loading") { ShimmerList(rows = 6) }
        } else {
            item("score") {
                StatCard(
                    title = stringResource(R.string.posture_score_title),
                    value = "${report.score}/100",
                    subtitle = stringResource(
                        R.string.posture_score_subtitle,
                        report.androidVersion,
                        report.patchDate.ifBlank { "?" },
                    ),
                    accent = statusColor(
                        when {
                            report.score >= 80 -> PostureCheck.Status.OK
                            report.score >= 55 -> PostureCheck.Status.WARN
                            else -> PostureCheck.Status.FAIL
                        },
                    ),
                )
            }

            item("checksHeader") {
                Text(
                    stringResource(R.string.posture_checks_header),
                    style = MaterialTheme.typography.titleMedium,
                )
            }
            itemsIndexed(report.checks, key = { _, check -> check.id.name }) { index, check ->
                Appear(index = index) { CheckRow(check) }
            }

            item("powerHeader") {
                Text(
                    stringResource(R.string.posture_power_header, report.powerfulApps.size),
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
            item("powerNote") {
                Text(
                    stringResource(R.string.posture_power_note),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (report.powerfulApps.isEmpty()) {
                item("powerEmpty") {
                    Text(
                        stringResource(R.string.posture_power_empty),
                        color = GoodGreen,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            } else {
                itemsIndexed(
                    report.powerfulApps,
                    key = { _, app -> app.packageName + app.kind.name },
                ) { index, app ->
                    Appear(index = index) {
                        PowerfulAppRow(
                            app = app,
                            onManage = {
                                runCatching {
                                    context.startActivity(viewModel.appDetailsIntent(app.packageName))
                                }
                            },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun CheckRow(check: PostureCheck) {
    val color = statusColor(check.status)
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.small,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                when (check.status) {
                    PostureCheck.Status.OK -> "✓"
                    PostureCheck.Status.WARN -> "!"
                    PostureCheck.Status.FAIL -> "✕"
                },
                color = color,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(end = 12.dp),
            )
            Text(
                stringResource(checkLabel(check), check.detail),
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun PowerfulAppRow(app: PowerfulApp, onManage: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.small,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    app.label,
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    stringResource(kindLabel(app.kind)),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }
            TextButton(onClick = onManage) { Text(stringResource(R.string.posture_manage)) }
        }
    }
}

private fun checkLabel(check: PostureCheck): Int = when (check.id) {
    PostureCheck.Id.SECURITY_PATCH -> R.string.posture_check_patch
    PostureCheck.Id.OS_VERSION -> R.string.posture_check_os
    PostureCheck.Id.SCREEN_LOCK ->
        if (check.status == PostureCheck.Status.OK) {
            R.string.posture_check_lock_ok
        } else {
            R.string.posture_check_lock_fail
        }
    PostureCheck.Id.BIOMETRICS ->
        if (check.status == PostureCheck.Status.OK) {
            R.string.posture_check_biometric_ok
        } else {
            R.string.posture_check_biometric_warn
        }
    PostureCheck.Id.ADB_ENABLED ->
        if (check.status == PostureCheck.Status.OK) {
            R.string.posture_check_adb_ok
        } else {
            R.string.posture_check_adb_warn
        }
    PostureCheck.Id.DEVELOPER_OPTIONS ->
        if (check.status == PostureCheck.Status.OK) {
            R.string.posture_check_devopts_ok
        } else {
            R.string.posture_check_devopts_warn
        }
    PostureCheck.Id.UNKNOWN_SOURCES_APPS -> R.string.posture_check_sideloaded
}

private fun kindLabel(kind: PowerfulApp.Kind): Int = when (kind) {
    PowerfulApp.Kind.ACCESSIBILITY -> R.string.posture_kind_accessibility
    PowerfulApp.Kind.NOTIFICATION_LISTENER -> R.string.posture_kind_notifications
    PowerfulApp.Kind.OVERLAY -> R.string.posture_kind_overlay
    PowerfulApp.Kind.ALL_FILES_ACCESS -> R.string.posture_kind_all_files
}

private fun statusColor(status: PostureCheck.Status): Color = when (status) {
    PostureCheck.Status.OK -> GoodGreen
    PostureCheck.Status.WARN -> WarnAmber
    PostureCheck.Status.FAIL -> BadRed
}
