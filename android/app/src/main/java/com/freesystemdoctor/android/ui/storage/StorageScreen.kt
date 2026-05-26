package com.freesystemdoctor.android.ui.storage

import android.content.Context
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PieChart
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.core.util.ByteFormatter
import com.freesystemdoctor.android.ui.components.Appear
import com.freesystemdoctor.android.ui.components.PermissionGate
import com.freesystemdoctor.android.ui.components.SectionHeader
import com.freesystemdoctor.android.ui.components.StatCard

@Composable
fun StorageScreen(
    modifier: Modifier = Modifier,
    viewModel: StorageViewModel = viewModel(),
) {
    val context = LocalContext.current
    val state by viewModel.state.collectAsStateWithLifecycle()

    com.freesystemdoctor.android.ui.components.OnResume { viewModel.load() }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        state.volume?.let { v ->
            Appear {
                StatCard(
                    title = stringResource(R.string.storage_title),
                    value = ByteFormatter.format(v.freeBytes),
                    subtitle = stringResource(
                        R.string.storage_used_of,
                        ByteFormatter.format(v.usedBytes),
                        ByteFormatter.format(v.totalBytes),
                    ),
                    progress = v.usedFraction,
                    icon = Icons.Filled.PieChart,
                )
            }
        }

        if (!state.hasUsageAccess) {
            Appear(index = 1) {
                PermissionGate(
                    message = stringResource(R.string.storage_need_usage_access),
                    actionLabel = stringResource(R.string.perm_grant),
                    onAction = { openUsageAccess(context) },
                )
            }
        } else {
            SectionHeader(stringResource(R.string.storage_breakdown))
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                itemsIndexed(state.apps) { index, app ->
                    Appear(index = index) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceContainer,
                        ),
                        shape = MaterialTheme.shapes.small,
                    ) {
                        Column(Modifier.padding(12.dp)) {
                            Text(app.label, style = MaterialTheme.typography.titleMedium)
                            Text(
                                ByteFormatter.format(app.totalBytes),
                                color = MaterialTheme.colorScheme.primary,
                            )
                            Text(
                                stringResource(
                                    R.string.storage_app_size,
                                    ByteFormatter.format(app.appBytes),
                                    ByteFormatter.format(app.dataBytes),
                                    ByteFormatter.format(app.cacheBytes),
                                ),
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                    }
                }
            }
        }
    }
}

private fun openUsageAccess(context: Context) {
    context.startActivity(ServiceLocator.permissionManager.usageAccessSettingsIntent())
}
