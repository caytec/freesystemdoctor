package com.freesystemdoctor.android.ui.trash

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
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
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
import com.freesystemdoctor.android.ui.components.ShimmerList

@Composable
fun TrashScreen(
    modifier: Modifier = Modifier,
    viewModel: TrashViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartIntentSenderForResult(),
    ) { result ->
        if (result.resultCode == android.app.Activity.RESULT_OK) viewModel.refresh()
    }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear { InfoBanner(stringResource(R.string.recycle_bin_note)) }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                enabled = state.selected.isNotEmpty(),
                onClick = {
                    viewModel.restoreRequest()?.let {
                        launcher.launch(IntentSenderRequest.Builder(it).build())
                    }
                },
            ) { Text(stringResource(R.string.recycle_bin_restore)) }
            OutlinedButton(
                enabled = state.selected.isNotEmpty(),
                onClick = {
                    viewModel.deleteRequest()?.let {
                        launcher.launch(IntentSenderRequest.Builder(it).build())
                    }
                },
            ) { Text(stringResource(R.string.recycle_bin_delete)) }
            OutlinedButton(
                enabled = state.items.isNotEmpty(),
                onClick = viewModel::selectAll,
            ) { Text(stringResource(R.string.select_all)) }
        }

        when {
            state.isLoading -> ShimmerList()
            state.items.isEmpty() -> Text(
                stringResource(R.string.recycle_bin_empty),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            else -> LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(state.items, key = { it.uri }) { item ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceContainer,
                        ),
                        shape = MaterialTheme.shapes.medium,
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Checkbox(
                                checked = item.uri in state.selected,
                                onCheckedChange = { viewModel.toggle(item.uri) },
                            )
                            Column(Modifier.weight(1f).padding(start = 8.dp)) {
                                Text(
                                    item.displayName,
                                    style = MaterialTheme.typography.titleSmall,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                                Text(
                                    ByteFormatter.format(item.sizeBytes),
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
