package com.freeandroiddoctor.android.ui.backup

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.engine.contacts.SmsBackupEngine
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.PermissionGate
import com.freeandroiddoctor.android.ui.components.SectionHeader

private const val MIN_PASSPHRASE = 8

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

    // Passphrase captured in the dialog, held only until the file picker returns.
    var armed by remember { mutableStateOf<Pair<ExportKind, CharArray>?>(null) }

    val createFileLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument(SmsBackupEngine.MIME_TYPE),
    ) { uri ->
        val pending = armed
        armed = null
        if (uri != null && pending != null) {
            viewModel.runExport(pending.first, uri, pending.second)
        } else {
            pending?.second?.fill(' ')
        }
    }

    state.pendingKind?.let { kind ->
        PassphraseDialog(
            onDismiss = viewModel::cancelExport,
            onConfirm = { passphrase ->
                armed = kind to passphrase
                viewModel.cancelExport()
                createFileLauncher.launch(viewModel.suggestedFileName(kind))
            },
        )
    }

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
                onClick = { viewModel.startExport(ExportKind.CONTACTS) },
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
                onClick = { viewModel.startExport(ExportKind.SMS) },
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

@Composable
private fun PassphraseDialog(
    onDismiss: () -> Unit,
    onConfirm: (CharArray) -> Unit,
) {
    var first by remember { mutableStateOf("") }
    var second by remember { mutableStateOf("") }

    val tooShort = first.isNotEmpty() && first.length < MIN_PASSPHRASE
    val mismatch = second.isNotEmpty() && first != second
    val valid = first.length >= MIN_PASSPHRASE && first == second

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.backup_passphrase_title)) },
        text = {
            Column(
                modifier = Modifier.imePadding(),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Text(
                    stringResource(R.string.backup_passphrase_desc),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                OutlinedTextField(
                    value = first,
                    onValueChange = { first = it },
                    label = { Text(stringResource(R.string.backup_passphrase_hint)) },
                    visualTransformation = PasswordVisualTransformation(),
                    singleLine = true,
                    isError = tooShort,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = second,
                    onValueChange = { second = it },
                    label = { Text(stringResource(R.string.backup_passphrase_repeat)) },
                    visualTransformation = PasswordVisualTransformation(),
                    singleLine = true,
                    isError = mismatch,
                    modifier = Modifier.fillMaxWidth(),
                )
                if (tooShort) {
                    Text(
                        stringResource(R.string.backup_passphrase_too_short),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                } else if (mismatch) {
                    Text(
                        stringResource(R.string.backup_passphrase_mismatch),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }
        },
        confirmButton = {
            TextButton(
                onClick = { onConfirm(first.toCharArray()) },
                enabled = valid,
            ) { Text(stringResource(R.string.backup_passphrase_continue)) }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.action_cancel)) }
        },
    )
}
