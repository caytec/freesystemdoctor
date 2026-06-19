package com.freeandroiddoctor.android.ui.photos

import android.app.Activity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.IntentSenderRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.LinearProgressIndicator
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
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.util.ByteFormatter
import com.freeandroiddoctor.android.engine.media.PhotoItem
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.StatCard

@Composable
fun PhotoReviewScreen(
    modifier: Modifier = Modifier,
    viewModel: PhotoReviewViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val deleteLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartIntentSenderForResult(),
    ) { result -> if (result.resultCode == Activity.RESULT_OK) viewModel.onDeleted() }

    fun launchDelete(items: List<PhotoItem>) {
        viewModel.buildDeleteRequest(items.map { it.uri })?.let { pi ->
            deleteLauncher.launch(IntentSenderRequest.Builder(pi.intentSender).build())
        }
    }

    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoBanner(stringResource(R.string.photoreview_note))

        Button(onClick = viewModel::scan, enabled = !state.scanning) {
            Text(stringResource(R.string.action_scan))
        }
        if (state.scanning) {
            LinearProgressIndicator(
                progress = { state.progress?.fraction ?: 0f },
                modifier = Modifier.fillMaxWidth(),
            )
            Text(stringResource(R.string.action_scanning), style = MaterialTheme.typography.bodySmall)
        }

        if (state.scanned) {
            Appear {
                StatCard(
                    title = stringResource(R.string.photoreview_screenshots),
                    value = ByteFormatter.format(state.screenshots.sumOf { it.sizeBytes }),
                    subtitle = stringResource(R.string.large_files_count, state.screenshots.size),
                )
            }
            if (state.screenshots.isNotEmpty()) {
                OutlinedButton(onClick = { launchDelete(state.screenshots) }) {
                    Text(stringResource(R.string.photoreview_delete_screenshots))
                }
            }

            Appear(index = 1) {
                StatCard(
                    title = stringResource(R.string.photoreview_blurry),
                    value = ByteFormatter.format(state.blurry.sumOf { it.sizeBytes }),
                    subtitle = stringResource(R.string.large_files_count, state.blurry.size),
                )
            }
            if (state.blurry.isNotEmpty()) {
                OutlinedButton(onClick = { launchDelete(state.blurry) }) {
                    Text(stringResource(R.string.photoreview_delete_blurry))
                }
            }
        }
    }
}
