package com.freesystemdoctor.android.ui.notifications

import android.content.Intent
import android.provider.Settings
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.app.NotificationManagerCompat
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.service.ActiveNotification
import com.freesystemdoctor.android.service.FsdNotificationListener

import com.freesystemdoctor.android.ui.components.PermissionGate

@Composable
fun NotificationCleanerScreen(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val enabled = NotificationManagerCompat.getEnabledListenerPackages(context)
        .contains(context.packageName)
    var items by remember { mutableStateOf<List<ActiveNotification>>(emptyList()) }
    var refreshTick by remember { mutableStateOf(0) }

    fun refresh() {
        items = FsdNotificationListener.instance?.snapshot().orEmpty()
        refreshTick++
    }
    com.freesystemdoctor.android.ui.components.OnResume { refresh() }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (!enabled) {
            PermissionGate(
                message = stringResource(R.string.notif_need_access),
                actionLabel = stringResource(R.string.perm_grant),
                onAction = {
                    context.startActivity(
                        Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
                            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                    )
                },
            )
            return@Column
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { refresh() }) { Text(stringResource(R.string.notif_refresh)) }
            OutlinedButton(onClick = {
                FsdNotificationListener.instance?.dismissAll()
                refresh()
            }) { Text(stringResource(R.string.notif_clear_all)) }
        }

        Text(
            stringResource(R.string.notif_count, items.size),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        com.freesystemdoctor.android.ui.components.Refreshable(
            isRefreshing = false,
            onRefresh = { refresh() },
        ) {
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(items, key = { it.key }) { n ->
                Card(
                    modifier = Modifier.fillMaxWidth().animateItem(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surfaceContainer,
                    ),
                    shape = MaterialTheme.shapes.small,
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 10.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(Modifier.weight(1f)) {
                            Text(
                                n.title,
                                style = MaterialTheme.typography.titleSmall,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                            Text(
                                n.text,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                        TextButton(onClick = {
                            FsdNotificationListener.instance?.dismiss(n.key)
                            refresh()
                        }) { Text(stringResource(R.string.notif_dismiss)) }
                    }
                }
            }
        }
        }
    }
}
