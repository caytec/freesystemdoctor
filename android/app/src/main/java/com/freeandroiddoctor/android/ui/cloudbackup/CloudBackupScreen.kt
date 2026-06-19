package com.freeandroiddoctor.android.ui.cloudbackup

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.util.ByteFormatter
import com.freeandroiddoctor.android.engine.cloudbackup.BackupOptions
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner

@Composable
fun CloudBackupScreen(
    onOpenRestore: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: CloudBackupViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val folder by viewModel.backupFolder.collectAsStateWithLifecycle()

    var passphrase by remember { mutableStateOf("") }
    var savePassphraseForAuto by remember { mutableStateOf(false) }
    var includeSettings by remember { mutableStateOf(true) }
    var includeApps by remember { mutableStateOf(true) }
    var includeWifi by remember { mutableStateOf(false) }
    var includeContacts by remember { mutableStateOf(false) }
    var includeSms by remember { mutableStateOf(false) }

    val pickFolder = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocumentTree(),
    ) { uri -> uri?.let(viewModel::setFolder) }

    val options = BackupOptions(
        includeSettings = includeSettings,
        includeApps = includeApps,
        includeWifi = includeWifi,
        includeContacts = includeContacts,
        includeSms = includeSms,
    )

    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear { InfoBanner(stringResource(R.string.cloud_backup_note)) }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { pickFolder.launch(null) }) {
                Text(stringResource(R.string.cloud_backup_pick_folder))
            }
            OutlinedButton(onClick = onOpenRestore) {
                Text(stringResource(R.string.cloud_backup_open_restore))
            }
        }
        if (folder != null) {
            Text(
                stringResource(R.string.cloud_backup_folder_set),
                color = MaterialTheme.colorScheme.secondary,
            )
        }

        Text(stringResource(R.string.cloud_backup_include), style = MaterialTheme.typography.titleSmall)
        IncludeRow(stringResource(R.string.cloud_backup_include_settings), includeSettings) { includeSettings = it }
        IncludeRow(stringResource(R.string.cloud_backup_include_apps), includeApps) { includeApps = it }
        IncludeRow(stringResource(R.string.cloud_backup_include_wifi), includeWifi) { includeWifi = it }
        IncludeRow(stringResource(R.string.cloud_backup_include_contacts), includeContacts) { includeContacts = it }
        IncludeRow(stringResource(R.string.cloud_backup_include_sms), includeSms) { includeSms = it }

        OutlinedTextField(
            value = passphrase,
            onValueChange = { passphrase = it },
            label = { Text(stringResource(R.string.cloud_backup_passphrase)) },
            placeholder = { Text(stringResource(R.string.cloud_backup_passphrase_hint)) },
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            modifier = Modifier.fillMaxWidth(),
        )
        Text(
            stringResource(R.string.cloud_backup_passphrase_warn),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.error,
        )

        Row(verticalAlignment = Alignment.CenterVertically) {
            Switch(checked = savePassphraseForAuto, onCheckedChange = { savePassphraseForAuto = it })
            Text(
                stringResource(R.string.cloud_backup_schedule),
                modifier = Modifier.padding(start = 12.dp),
            )
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = { viewModel.estimate(options) }) {
                Text(stringResource(R.string.cloud_backup_dryrun))
            }
            Button(
                onClick = {
                    viewModel.runNow(passphrase, options)
                    if (savePassphraseForAuto && passphrase.length >= 12) {
                        viewModel.saveScheduledPassphrase(passphrase)
                    } else if (!savePassphraseForAuto) {
                        viewModel.cancelSchedule()
                    }
                },
                enabled = folder != null && passphrase.length >= 12 && !state.running,
            ) {
                Text(
                    if (state.running) stringResource(R.string.cloud_backup_in_progress)
                    else stringResource(R.string.cloud_backup_run),
                )
            }
        }

        state.estimate?.let {
            Text(
                stringResource(R.string.cloud_backup_estimate, ByteFormatter.format(it.sizeBytes)),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.primary,
            )
            Text(
                stringResource(R.string.restore_manifest, it.entries.joinToString()),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        state.lastResult?.let {
            Text(
                stringResource(R.string.cloud_backup_done, it),
                color = MaterialTheme.colorScheme.secondary,
            )
        }
        state.error?.let {
            Text(
                stringResource(R.string.cloud_backup_failed, it),
                color = MaterialTheme.colorScheme.error,
            )
        }

        Text(
            stringResource(R.string.cloud_backup_disclaimer),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun IncludeRow(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Checkbox(checked = checked, onCheckedChange = onChange)
        Text(label, modifier = Modifier.padding(start = 6.dp))
    }
}
