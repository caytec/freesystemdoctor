package com.freeandroiddoctor.android.ui.resource

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.core.util.ByteFormatter
import com.freeandroiddoctor.android.engine.resource.AppResourceRow
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.LocalUnlockController
import com.freeandroiddoctor.android.ui.components.PermissionGate
import com.freeandroiddoctor.android.ui.components.ShimmerList
import com.freeandroiddoctor.android.ui.navigation.ToolRoutes
import com.freeandroiddoctor.android.ui.tools.ToolsViewModel
import java.text.DateFormat
import java.util.Date
import java.util.concurrent.TimeUnit

@Composable
fun AppResourceScreen(
    modifier: Modifier = Modifier,
    viewModel: AppResourceViewModel = viewModel(),
    toolsViewModel: ToolsViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val advanced by toolsViewModel.advancedUnlocked.collectAsStateWithLifecycle()
    val unlockController = LocalUnlockController.current

    val csvLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("text/csv"),
    ) { uri -> uri?.let(viewModel::exportCsv) }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear { InfoBanner(stringResource(R.string.app_resource_note)) }

        val report = state.report
        when {
            state.loading -> ShimmerList()
            report == null -> Text(stringResource(R.string.empty))
            report.needsUsageAccess -> PermissionGate(
                message = stringResource(R.string.app_resource_empty),
                actionLabel = stringResource(R.string.perm_grant),
                onAction = {
                    runCatching { context.startActivity(viewModel.usageAccessIntent()) }
                },
            )
            else -> {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = viewModel::refresh) {
                        Text(stringResource(R.string.refresh))
                    }
                    OutlinedButton(onClick = {
                        if (advanced) {
                            csvLauncher.launch("fsd-resources.csv")
                        } else {
                            unlockController.request(ToolRoutes.APP_RESOURCE, R.string.tool_app_resource)
                        }
                    }) {
                        Text(stringResource(R.string.app_resource_export_csv))
                    }
                }

                Text(
                    stringResource(R.string.app_resource_disclaimer),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )

                LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(report.rows, key = { it.packageName }) { row ->
                        ResourceRow(
                            row = row,
                            modifier = Modifier.animateItem(),
                            onSettings = {
                                runCatching { context.startActivity(viewModel.openAppSettings(row.packageName)) }
                            },
                            onUninstall = {
                                runCatching { context.startActivity(viewModel.uninstallIntent(row.packageName)) }
                            },
                            onStop = { viewModel.tryStop(row.packageName) },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ResourceRow(
    row: AppResourceRow,
    modifier: Modifier = Modifier,
    onSettings: () -> Unit,
    onUninstall: () -> Unit,
    onStop: () -> Unit,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        row.label,
                        style = MaterialTheme.typography.titleSmall,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        row.packageName,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Text(
                    "${row.score}",
                    style = MaterialTheme.typography.headlineSmall,
                    color = MaterialTheme.colorScheme.primary,
                )
            }

            Row(
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Stat(stringResource(R.string.app_resource_storage), ByteFormatter.format(row.storageBytes))
                Stat(stringResource(R.string.app_resource_cache), ByteFormatter.format(row.cacheBytes))
                Stat(stringResource(R.string.app_resource_data), ByteFormatter.format(row.data30dBytes))
            }
            Row(
                modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                val minutes = TimeUnit.MILLISECONDS.toMinutes(row.screenTime7dMillis)
                Stat(stringResource(R.string.app_resource_screentime), "${minutes}m")
                Stat(
                    stringResource(R.string.app_resource_last_used),
                    if (row.lastUsed <= 0) stringResource(R.string.app_resource_never)
                    else DateFormat.getDateInstance(DateFormat.SHORT).format(Date(row.lastUsed)),
                )
            }
            Row(
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                TextButton(onClick = onSettings) { Text(stringResource(R.string.app_resource_action_settings)) }
                TextButton(onClick = onStop) { Text(stringResource(R.string.app_resource_action_stop)) }
                TextButton(onClick = onUninstall) { Text(stringResource(R.string.app_resource_action_uninstall)) }
            }
        }
    }
}

@Composable
private fun Stat(label: String, value: String) {
    Column {
        Text(
            label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(value, style = MaterialTheme.typography.bodyMedium)
    }
}
