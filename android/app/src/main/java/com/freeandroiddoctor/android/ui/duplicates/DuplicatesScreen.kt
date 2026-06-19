package com.freeandroiddoctor.android.ui.duplicates

import android.app.Activity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.IntentSenderRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.core.util.ByteFormatter
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.StatCard

@Composable
fun DuplicatesScreen(
    modifier: Modifier = Modifier,
    viewModel: DuplicatesViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val deleteLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartIntentSenderForResult(),
    ) { result -> if (result.resultCode == Activity.RESULT_OK) viewModel.onDeleted() }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear {
            StatCard(
                title = stringResource(R.string.tool_duplicates),
                value = ByteFormatter.format(state.reclaimableBytes),
                subtitle = stringResource(R.string.duplicates_groups, state.groups.size),
            )
        }

        FilterChip(
            selected = state.audioOnly,
            onClick = { viewModel.setAudioOnly(!state.audioOnly) },
            label = { Text(stringResource(R.string.duplicates_audio_only)) },
        )

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = viewModel::scan, enabled = !state.scanning) {
                Text(stringResource(R.string.action_scan))
            }
            if (state.groups.isNotEmpty()) {
                Button(onClick = {
                    viewModel.buildDeleteRequest()?.let { pi ->
                        ServiceLocator.appOpenAdManager.suppressForMillis(30_000L)
                        deleteLauncher.launch(IntentSenderRequest.Builder(pi.intentSender).build())
                    }
                }) { Text(stringResource(R.string.duplicates_clean)) }
            }
        }

        if (state.scanning) {
            val frac = state.progress?.fraction ?: 0f
            LinearProgressIndicator(progress = { frac }, modifier = Modifier.fillMaxWidth())
            Text(
                state.progress?.label ?: stringResource(R.string.action_scanning),
                style = MaterialTheme.typography.bodySmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            com.freeandroiddoctor.android.ui.components.ShimmerList(rows = 4)
        }

        InfoBanner(stringResource(R.string.duplicates_note))

        if (state.scanned && state.groups.isEmpty() && !state.scanning) {
            Text(stringResource(R.string.duplicates_none))
        }

        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            itemsIndexed(state.groups, key = { _, group -> group.hash }) { _, group ->
                Card(
                    modifier = Modifier.fillMaxWidth().animateItem(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surfaceContainer,
                    ),
                    shape = MaterialTheme.shapes.small,
                ) {
                    Column(Modifier.padding(12.dp)) {
                        Text(
                            stringResource(R.string.duplicates_group_size, group.files.size),
                            style = MaterialTheme.typography.titleSmall,
                            color = MaterialTheme.colorScheme.primary,
                        )
                        group.files.forEach { f ->
                            Text(
                                "${f.displayName}  ·  ${ByteFormatter.format(f.sizeBytes)}",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                                modifier = Modifier.padding(top = 2.dp),
                            )
                        }
                    }
                }
            }
        }
    }
}
