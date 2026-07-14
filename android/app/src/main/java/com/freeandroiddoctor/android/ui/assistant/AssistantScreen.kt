package com.freeandroiddoctor.android.ui.assistant

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner

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
        Appear { Text(stringResource(R.string.assistant_title), style = MaterialTheme.typography.headlineSmall) }
        Appear(index = 1) { InfoBanner(stringResource(R.string.assistant_intro)) }

        if (!state.hasKey) {
            Appear(index = 2) { InfoBanner(stringResource(R.string.assistant_no_key)) }
        }

        Appear(index = 3) {
            Button(
                onClick = viewModel::analyze,
                enabled = state.hasKey && !state.analyzing,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Filled.AutoAwesome, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.size(8.dp))
                Text(stringResource(R.string.assistant_analyze))
            }
        }

        if (state.analyzing) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(modifier = Modifier.size(22.dp))
                Spacer(Modifier.size(10.dp))
                Text(stringResource(R.string.assistant_analyzing))
            }
        }

        state.recommendations?.let { text ->
            Appear {
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
                    shape = MaterialTheme.shapes.medium,
                ) {
                    Text(text, modifier = Modifier.padding(16.dp))
                }
            }
        }

        state.error?.takeIf { it != "missing_key" }?.let { err ->
            Text(err, color = MaterialTheme.colorScheme.error)
        }

        if (state.limitReached) {
            Appear {
                InfoBanner(stringResource(R.string.assistant_limit_reached, AssistantViewModel.FREE_DAILY_LIMIT))
            }
        } else if (state.usageToday in 1 until AssistantViewModel.FREE_DAILY_LIMIT) {
            Text(
                stringResource(R.string.assistant_usage_today, state.usageToday, AssistantViewModel.FREE_DAILY_LIMIT),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
