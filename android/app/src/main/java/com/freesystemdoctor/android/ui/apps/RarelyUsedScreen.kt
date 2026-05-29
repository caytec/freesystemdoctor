package com.freesystemdoctor.android.ui.apps

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
import com.freesystemdoctor.android.R

import com.freesystemdoctor.android.ui.components.PermissionGate
import java.text.DateFormat
import java.util.Date

@Composable
fun RarelyUsedScreen(
    modifier: Modifier = Modifier,
    viewModel: RarelyUsedViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    com.freesystemdoctor.android.ui.components.OnResume { viewModel.load() }

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
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.End,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            TextButton(onClick = {
                                context.startActivity(viewModel.appDetailsIntent(app.packageName))
                            }) { Text(stringResource(R.string.apps_details)) }
                            OutlinedButton(onClick = {
                                context.startActivity(viewModel.uninstallIntent(app.packageName))
                            }) { Text(stringResource(R.string.apps_uninstall)) }
                        }
                    }
                }
            }
        }
    }
}
