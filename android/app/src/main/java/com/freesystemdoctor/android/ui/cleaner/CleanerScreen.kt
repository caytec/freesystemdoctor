package com.freesystemdoctor.android.ui.cleaner

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
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.util.ByteFormatter
import com.freesystemdoctor.android.ui.components.InfoBanner
import com.freesystemdoctor.android.ui.components.StatCard

@Composable
fun CleanerScreen(
    modifier: Modifier = Modifier,
    viewModel: CleanerViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val deleteLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartIntentSenderForResult(),
    ) { result ->
        if (result.resultCode == android.app.Activity.RESULT_OK) {
            viewModel.onMediaDeleted()
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        val report = state.report
        StatCard(
            title = stringResource(R.string.cleaner_title),
            value = report?.let {
                stringResource(R.string.cleaner_reclaimable, ByteFormatter.format(it.reclaimableBytes))
            } ?: "—",
            subtitle = if (state.lastFreedBytes > 0) {
                stringResource(R.string.cleaner_freed, ByteFormatter.format(state.lastFreedBytes))
            } else {
                null
            },
        )

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = viewModel::scan, enabled = !state.scanning) {
                Text(stringResource(R.string.cleaner_scan))
            }
            OutlinedButton(onClick = viewModel::cleanAppCache, enabled = !state.scanning) {
                Text(stringResource(R.string.cleaner_app_cache))
            }
            if (report != null && report.mediaItems.isNotEmpty()) {
                Button(onClick = {
                    viewModel.buildDeleteRequest()?.let { pi ->
                        deleteLauncher.launch(IntentSenderRequest.Builder(pi.intentSender).build())
                    }
                }) {
                    Text(stringResource(R.string.cleaner_clean))
                }
            }
        }

        if (state.scanning) {
            Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                CircularProgressIndicator(modifier = Modifier.padding(end = 8.dp))
                Text(stringResource(R.string.cleaner_scanning))
            }
        }

        InfoBanner(stringResource(R.string.cleaner_note))

        report?.let {
            LazyColumn(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                items(it.mediaItems) { item ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text(item.displayName, modifier = Modifier.weight(1f))
                        Text(ByteFormatter.format(item.sizeBytes))
                    }
                }
            }
        }
    }
}
