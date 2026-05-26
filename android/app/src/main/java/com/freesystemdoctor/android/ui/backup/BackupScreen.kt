package com.freesystemdoctor.android.ui.backup

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.ui.components.Appear
import com.freesystemdoctor.android.ui.components.InfoBanner
import com.freesystemdoctor.android.ui.components.PermissionGate
import com.freesystemdoctor.android.ui.components.SectionHeader

@Composable
fun BackupScreen(
    modifier: Modifier = Modifier,
    viewModel: BackupViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { viewModel.refresh() }

    val contactsLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { viewModel.refresh() }
    val smsLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { viewModel.refresh() }

    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear { InfoBanner(stringResource(R.string.backup_note)) }

        SectionHeader(stringResource(R.string.backup_contacts))
        if (!state.hasContacts) {
            PermissionGate(
                message = stringResource(R.string.backup_contacts_need),
                actionLabel = stringResource(R.string.perm_grant),
                onAction = { contactsLauncher.launch(Manifest.permission.READ_CONTACTS) },
            )
        } else {
            Button(
                onClick = viewModel::exportContacts,
                enabled = !state.working,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(stringResource(R.string.backup_export_contacts)) }

            if (state.duplicates.isNotEmpty()) {
                Appear {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceContainer,
                        ),
                        shape = MaterialTheme.shapes.medium,
                    ) {
                        Column(Modifier.padding(14.dp)) {
                            Text(
                                stringResource(R.string.backup_duplicates, state.duplicates.size),
                                style = MaterialTheme.typography.titleSmall,
                                color = MaterialTheme.colorScheme.primary,
                            )
                            state.duplicates.take(20).forEach { d ->
                                Text(
                                    "${d.displayName} ×${d.count}",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        }
                    }
                }
            }
        }

        SectionHeader(stringResource(R.string.backup_sms))
        if (!state.hasSms) {
            PermissionGate(
                message = stringResource(R.string.backup_sms_need),
                actionLabel = stringResource(R.string.perm_grant),
                onAction = { smsLauncher.launch(Manifest.permission.READ_SMS) },
            )
        } else {
            OutlinedButton(
                onClick = viewModel::exportSms,
                enabled = !state.working,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(stringResource(R.string.backup_export_sms)) }
        }

        state.message?.let {
            Text(
                if (state.isError) stringResource(R.string.backup_error)
                else stringResource(R.string.backup_saved, it),
                color = if (state.isError) MaterialTheme.colorScheme.error
                else MaterialTheme.colorScheme.secondary,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}
