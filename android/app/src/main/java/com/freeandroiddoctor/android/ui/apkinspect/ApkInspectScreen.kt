package com.freeandroiddoctor.android.ui.apkinspect

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.util.ByteFormatter
import com.freeandroiddoctor.android.engine.privacy.ApkInspection
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.StatCard

@Composable
fun ApkInspectScreen(
    modifier: Modifier = Modifier,
    viewModel: ApkInspectViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    val picker = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri -> uri?.let(viewModel::inspect) }

    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear { InfoBanner(stringResource(R.string.apkinspect_note)) }

        Button(
            onClick = {
                viewModel.reset()
                // Some providers report APKs as octet-stream, so accept both.
                picker.launch(
                    arrayOf("application/vnd.android.package-archive", "application/octet-stream"),
                )
            },
            enabled = !state.working,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(stringResource(R.string.apkinspect_pick)) }

        if (state.working) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                CircularProgressIndicator()
                Text(
                    stringResource(R.string.apkinspect_working),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }

        if (state.done && state.failed) {
            Text(
                stringResource(R.string.apkinspect_failed),
                color = MaterialTheme.colorScheme.error,
            )
        }

        state.inspection?.let { Appear(index = 1) { Result(it) } }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun Result(apk: ApkInspection) {
    // Warnings first — these are the reasons not to install.
    if (apk.signatureMismatch) {
        WarningCard(
            stringResource(R.string.apkinspect_warn_signature_title),
            stringResource(R.string.apkinspect_warn_signature_body),
        )
    }
    if (apk.debugSigned) {
        WarningCard(
            stringResource(R.string.apkinspect_warn_debug_title),
            stringResource(R.string.apkinspect_warn_debug_body),
        )
    }

    StatCard(
        title = apk.label,
        value = stringResource(R.string.apkinspect_version, apk.versionName, apk.versionCode),
        subtitle = apk.packageName + " · " + ByteFormatter.format(apk.sizeBytes),
    )

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                stringResource(R.string.apkinspect_sdk, apk.minSdk, apk.targetSdk),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                stringResource(
                    if (apk.alreadyInstalled) {
                        R.string.apkinspect_installed_yes
                    } else {
                        R.string.apkinspect_installed_no
                    },
                ),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }

    Text(
        stringResource(R.string.apkinspect_trackers_header, apk.trackers.size),
        style = MaterialTheme.typography.titleSmall,
    )
    if (apk.trackers.isEmpty()) {
        Text(
            stringResource(R.string.apkinspect_trackers_none),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    } else {
        FlowRow(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            apk.trackers.forEachIndexed { index, t ->
                Appear(index = index) {
                    AssistChip(
                        onClick = {},
                        enabled = false,
                        label = { Text(t.name, style = MaterialTheme.typography.labelSmall) },
                    )
                }
            }
        }
    }

    Text(
        stringResource(R.string.apkinspect_perms_header, apk.dangerousPermissions.size),
        style = MaterialTheme.typography.titleSmall,
    )
    if (apk.dangerousPermissions.isEmpty()) {
        Text(
            stringResource(R.string.apkinspect_perms_none),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    } else {
        apk.dangerousPermissions.forEachIndexed { index, p ->
            Appear(index = index) {
                Text(
                    "• $p",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun WarningCard(title: String, body: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.error.copy(alpha = 0.12f),
        ),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(Modifier.padding(14.dp)) {
            Text(
                title,
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.error,
                fontWeight = FontWeight.Bold,
            )
            Text(
                body,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.padding(top = 4.dp),
            )
        }
    }
}
