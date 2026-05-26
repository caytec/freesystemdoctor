package com.freesystemdoctor.android.ui.photos

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
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.util.ByteFormatter
import com.freesystemdoctor.android.ui.components.Appear
import com.freesystemdoctor.android.ui.components.InfoBanner
import com.freesystemdoctor.android.ui.components.StatCard

@Composable
fun SimilarPhotosScreen(
    modifier: Modifier = Modifier,
    viewModel: SimilarPhotosViewModel = viewModel(),
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
                title = stringResource(R.string.similar_title),
                value = ByteFormatter.format(state.reclaimableBytes),
                subtitle = stringResource(R.string.similar_groups, state.groups.size),
            )
        }
        InfoBanner(stringResource(R.string.similar_note))

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = viewModel::scan, enabled = !state.scanning) {
                Text(stringResource(R.string.action_scan))
            }
            if (state.groups.isNotEmpty()) {
                Button(onClick = {
                    viewModel.buildDeleteRequest()?.let { pi ->
                        deleteLauncher.launch(IntentSenderRequest.Builder(pi.intentSender).build())
                    }
                }) { Text(stringResource(R.string.duplicates_clean)) }
            }
        }

        if (state.scanning) {
            LinearProgressIndicator(
                progress = { state.progress?.fraction ?: 0f },
                modifier = Modifier.fillMaxWidth(),
            )
            Text(stringResource(R.string.action_scanning), style = MaterialTheme.typography.bodySmall)
            com.freesystemdoctor.android.ui.components.ShimmerList(rows = 4)
        }
        if (state.scanned && state.groups.isEmpty() && !state.scanning) {
            Text(stringResource(R.string.similar_none))
        }

        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            itemsIndexed(state.groups) { index, group ->
                Appear(index = index) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceContainer,
                        ),
                        shape = MaterialTheme.shapes.small,
                    ) {
                        Column(Modifier.padding(12.dp)) {
                            Text(
                                stringResource(R.string.similar_group_size, group.items.size),
                                style = MaterialTheme.typography.titleSmall,
                                color = MaterialTheme.colorScheme.primary,
                            )
                            group.items.forEach { p ->
                                Text(
                                    "${p.displayName}  ·  ${ByteFormatter.format(p.sizeBytes)}",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
