package com.freesystemdoctor.android.ui.assistant

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
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
import com.freesystemdoctor.android.ui.components.InfoBanner

@Composable
fun AssistantScreen(
    modifier: Modifier = Modifier,
    viewModel: AssistantViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { viewModel.refreshKey() }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(stringResource(R.string.assistant_title), style = MaterialTheme.typography.titleLarge)
        InfoBanner(stringResource(R.string.assistant_intro))

        if (!state.hasKey) {
            InfoBanner(stringResource(R.string.assistant_no_key))
        }

        Button(onClick = viewModel::analyze, enabled = state.hasKey && !state.analyzing) {
            Text(stringResource(R.string.assistant_analyze))
        }

        if (state.analyzing) {
            CircularProgressIndicator()
            Text(stringResource(R.string.assistant_analyzing))
        }

        state.recommendations?.let { text ->
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                Text(text, modifier = Modifier.padding(16.dp))
            }
        }

        state.error?.takeIf { it != "missing_key" }?.let { err ->
            Text(err, color = MaterialTheme.colorScheme.error)
        }
    }
}
