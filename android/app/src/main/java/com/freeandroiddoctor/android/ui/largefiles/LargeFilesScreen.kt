package com.freeandroiddoctor.android.ui.largefiles

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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
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
import com.freeandroiddoctor.android.ui.components.StatCard

@Composable
fun LargeFilesScreen(
    modifier: Modifier = Modifier,
    viewModel: LargeFilesViewModel = viewModel(),
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
                title = stringResource(R.string.tool_large_files),
                value = ByteFormatter.format(state.totalBytes),
                subtitle = stringResource(R.string.large_files_count, state.files.size),
            )
        }

        FilterChip(
            selected = state.videosOnly,
            onClick = { viewModel.setVideosOnly(!state.videosOnly) },
            label = { Text(stringResource(R.string.large_files_videos_only)) },
        )

        Button(onClick = viewModel::scan, enabled = !state.scanning) {
            Text(stringResource(R.string.action_scan))
        }

        if (state.scanning) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(modifier = Modifier.size(22.dp).padding(end = 8.dp))
                Text(stringResource(R.string.action_scanning))
            }
            com.freeandroiddoctor.android.ui.components.ShimmerList(rows = 5)
        }

        if (state.scanned && state.files.isEmpty() && !state.scanning) {
            Text(stringResource(R.string.large_files_none))
        }

        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            itemsIndexed(state.files, key = { _, f -> f.uri.toString() }) { _, file ->
                Card(
                    modifier = Modifier.fillMaxWidth().animateItem(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surfaceContainer,
                    ),
                    shape = MaterialTheme.shapes.small,
                ) {
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 10.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(
                                    file.displayName,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                    style = MaterialTheme.typography.bodyMedium,
                                )
                                Text(
                                    ByteFormatter.format(file.sizeBytes),
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.primary,
                                )
                            }
                            TextButton(onClick = {
                                ServiceLocator.appOpenAdManager.suppressForMillis(30_000L)
                                viewModel.buildDeleteRequest(listOf(file.uri))?.let { pi ->
                                    deleteLauncher.launch(
                                        IntentSenderRequest.Builder(pi.intentSender).build(),
                                    )
                                }
                            }) { Text(stringResource(R.string.action_delete)) }
                        }
                    }
            }
        }
    }
}
