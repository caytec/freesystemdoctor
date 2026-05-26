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
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CleaningServices
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
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
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.core.util.ByteFormatter
import com.freesystemdoctor.android.ui.components.Appear
import com.freesystemdoctor.android.ui.components.InfoBanner
import com.freesystemdoctor.android.ui.components.StatCard

@Composable
fun CleanerScreen(
    modifier: Modifier = Modifier,
    viewModel: CleanerViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val activity = androidx.compose.ui.platform.LocalContext.current as? android.app.Activity
    val deleteLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartIntentSenderForResult(),
    ) { result ->
        if (result.resultCode == android.app.Activity.RESULT_OK) {
            viewModel.onMediaDeleted()
            activity?.let { ServiceLocator.adsController.maybeShowInterstitial(it) }
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        val report = state.report
        Appear {
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
                icon = Icons.Filled.CleaningServices,
            )
        }

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
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                itemsIndexed(it.mediaItems) { index, item ->
                    Appear(index = index) {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.surfaceContainer,
                            ),
                            shape = MaterialTheme.shapes.small,
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(horizontal = 14.dp, vertical = 12.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
                            ) {
                                Text(
                                    item.displayName,
                                    modifier = Modifier.weight(1f),
                                    maxLines = 1,
                                    overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis,
                                )
                                Text(
                                    ByteFormatter.format(item.sizeBytes),
                                    color = MaterialTheme.colorScheme.primary,
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
