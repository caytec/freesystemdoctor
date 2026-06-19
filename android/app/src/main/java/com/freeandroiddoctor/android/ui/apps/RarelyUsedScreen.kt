package com.freeandroiddoctor.android.ui.apps

import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
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

import com.freeandroiddoctor.android.ui.components.PermissionGate
import com.freeandroiddoctor.android.ui.components.UninstallPreviewSheet
import java.text.DateFormat
import java.util.Date

private fun forceStop(context: Context, pkg: String) {
    val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
    runCatching { am.killBackgroundProcesses(pkg) }
    Toast.makeText(
        context,
        context.getString(R.string.rarely_used_force_stop_done),
        Toast.LENGTH_SHORT,
    ).show()
}

private fun openAppDetails(context: Context, pkg: String) {
    val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
        data = Uri.parse("package:$pkg")
        flags = Intent.FLAG_ACTIVITY_NEW_TASK
    }
    runCatching { context.startActivity(intent) }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun RarelyUsedScreen(
    modifier: Modifier = Modifier,
    viewModel: RarelyUsedViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    com.freeandroiddoctor.android.ui.components.OnResume { viewModel.load() }
    val previewSheet = UninstallPreviewSheet.use(context)

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (!state.hasUsageAccess) {
            PermissionGate(
                message = stringResource(R.string.app_usage_need_access),
                actionLabel = stringResource(R.string.perm_grant),
                onAction = { context.startActivity(viewModel.usageAccessIntent()) },
            )
            return@Column
        }

        Text(
            stringResource(R.string.rarely_used_subtitle),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            itemsIndexed(state.apps, key = { _, app -> app.packageName }) { _, app ->
                Card(
                    modifier = Modifier.fillMaxWidth().animateItem(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surfaceContainer,
                    ),
                    shape = MaterialTheme.shapes.small,
                ) {
                    Column(Modifier.padding(12.dp)) {
                        Text(
                            app.label,
                            style = MaterialTheme.typography.titleSmall,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        Text(
                            if (app.neverUsed) {
                                stringResource(R.string.rarely_used_never)
                            } else {
                                stringResource(
                                    R.string.rarely_used_last,
                                    DateFormat.getDateInstance().format(Date(app.lastUsed)),
                                )
                            },
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        FlowRow(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(4.dp),
                            verticalArrangement = Arrangement.spacedBy(4.dp),
                        ) {
                            TextButton(onClick = {
                                context.startActivity(viewModel.appDetailsIntent(app.packageName))
                            }) { Text(stringResource(R.string.apps_details)) }
                            TextButton(onClick = { forceStop(context, app.packageName) }) {
                                Text(stringResource(R.string.rarely_used_force_stop))
                            }
                            TextButton(onClick = { openAppDetails(context, app.packageName) }) {
                                Text(stringResource(R.string.rarely_used_restrict_bg))
                            }
                            OutlinedButton(onClick = {
                                previewSheet.requestUninstall(app.packageName)
                            }) { Text(stringResource(R.string.apps_uninstall)) }
                        }
                    }
                }
            }
        }
    }
}
