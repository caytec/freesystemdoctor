package com.freesystemdoctor.android.ui.memory

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
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
import com.freesystemdoctor.android.core.util.ByteFormatter
import com.freesystemdoctor.android.ui.components.Appear
import com.freesystemdoctor.android.ui.components.InfoBanner
import com.freesystemdoctor.android.ui.components.StatCard

@Composable
fun MemoryScreen(
    modifier: Modifier = Modifier,
    viewModel: MemoryViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { viewModel.load() }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        state.info?.let { m ->
            Appear {
                StatCard(
                    title = stringResource(R.string.dashboard_memory),
                    value = ByteFormatter.format(m.usedBytes),
                    subtitle = stringResource(
                        R.string.ram_used_of,
                        ByteFormatter.format(m.usedBytes),
                        ByteFormatter.format(m.totalBytes),
                    ),
                    progress = m.usedFraction,
                )
            }
        }

        InfoBanner(stringResource(R.string.memory_note))

        Button(
            onClick = viewModel::freeBackground,
            enabled = !state.working,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(stringResource(R.string.memory_free)) }

        state.lastFreedBytes?.let {
            Text(
                stringResource(R.string.memory_freed, ByteFormatter.format(it)),
                color = MaterialTheme.colorScheme.secondary,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}
