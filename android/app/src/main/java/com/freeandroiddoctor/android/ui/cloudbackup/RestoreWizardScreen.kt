package com.freeandroiddoctor.android.ui.cloudbackup

import android.app.Application
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch


data class RestoreUiState(
    val source: Uri? = null,
    val entries: List<String>? = null,
    val error: String? = null,
)

class RestoreWizardViewModel(application: Application) : AndroidViewModel(application) {

    private val engine = ServiceLocator.cloudBackupEngine

    private val _state = MutableStateFlow(RestoreUiState())
    val state: StateFlow<RestoreUiState> = _state.asStateFlow()

    fun setSource(uri: Uri) {
        _state.value = RestoreUiState(source = uri)
    }

    fun decrypt(passphrase: String) {
        val source = _state.value.source ?: return
        viewModelScope.launch {
            runCatching { engine.listEntries(source, passphrase.toCharArray()) }
                .onSuccess { entries -> _state.value = _state.value.copy(entries = entries, error = null) }
                .onFailure { _state.value = _state.value.copy(error = "wrong") }
        }
    }
}

@Composable
fun RestoreWizardScreen(
    modifier: Modifier = Modifier,
    viewModel: RestoreWizardViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsState()
    var passphrase by remember { mutableStateOf("") }

    val picker = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri -> uri?.let(viewModel::setSource) }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear { InfoBanner(stringResource(R.string.cloud_backup_disclaimer)) }

        Button(onClick = { picker.launch(arrayOf("application/octet-stream", "*/*")) }) {
            Text(stringResource(R.string.restore_pick))
        }
        state.source?.let { Text("✓ ${it.lastPathSegment ?: it}", style = MaterialTheme.typography.bodySmall) }

        OutlinedTextField(
            value = passphrase,
            onValueChange = { passphrase = it },
            label = { Text(stringResource(R.string.cloud_backup_passphrase)) },
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            modifier = Modifier.fillMaxWidth(),
        )
        Button(
            onClick = { viewModel.decrypt(passphrase) },
            enabled = state.source != null && passphrase.isNotEmpty(),
        ) { Text(stringResource(R.string.restore_decrypt)) }

        if (state.error != null) {
            Text(
                stringResource(R.string.restore_wrong_passphrase),
                color = MaterialTheme.colorScheme.error,
            )
        }
        state.entries?.let { entries ->
            Text(stringResource(R.string.restore_manifest, entries.joinToString()))
            // v1: read-only preview. Actual selective import per section will land in Update 10.
        }
    }
}

