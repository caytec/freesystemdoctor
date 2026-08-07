package com.freeandroiddoctor.android.ui.metadata

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.LocationOff
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.StatCard

@Composable
fun MetadataScreen(
    modifier: Modifier = Modifier,
    viewModel: MetadataViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    // System photo picker — no storage permission needed, privacy-friendly.
    val picker = rememberLauncherForActivityResult(
        ActivityResultContracts.PickMultipleVisualMedia(maxItems = 50),
    ) { uris -> if (uris.isNotEmpty()) viewModel.strip(uris) }

    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear { InfoBanner(stringResource(R.string.metadata_note)) }

        Button(
            onClick = {
                viewModel.reset()
                picker.launch(
                    PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly),
                )
            },
            enabled = !state.working,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(stringResource(R.string.metadata_pick)) }

        if (state.working) {
            val frac by animateFloatAsState(
                targetValue = if (state.total == 0) 0f else state.processed.toFloat() / state.total,
                animationSpec = tween(300, easing = FastOutSlowInEasing),
                label = "stripProgress",
            )
            LinearProgressIndicator(progress = { frac }, modifier = Modifier.fillMaxWidth())
            Text(
                stringResource(R.string.metadata_progress, state.processed, state.total),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                state.currentName,
                style = MaterialTheme.typography.bodySmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        if (state.done) {
            Appear {
                StatCard(
                    title = stringResource(R.string.metadata_result_title),
                    value = stringResource(R.string.metadata_result_cleaned, state.cleaned),
                    subtitle = stringResource(
                        R.string.metadata_result_subtitle,
                        state.withLocation,
                    ),
                    icon = Icons.Filled.LocationOff,
                    accent = MaterialTheme.colorScheme.secondary,
                )
            }
            if (state.failed > 0) {
                Text(
                    stringResource(R.string.metadata_result_failed, state.failed),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }
            state.outcomes.filter { it.success }.take(50).forEachIndexed { index, o ->
                Appear(index = index) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceContainer,
                        ),
                        shape = MaterialTheme.shapes.small,
                    ) {
                        Column(Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
                            Text(
                                o.originalName,
                                style = MaterialTheme.typography.bodyMedium,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                            Text(
                                if (o.hadLocation) {
                                    stringResource(R.string.metadata_removed_location)
                                } else {
                                    stringResource(R.string.metadata_removed_meta)
                                },
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.secondary,
                            )
                        }
                    }
                }
            }
            OutlinedButton(
                onClick = {
                    viewModel.reset()
                    picker.launch(
                        PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly),
                    )
                },
                modifier = Modifier.fillMaxWidth(),
            ) { Text(stringResource(R.string.metadata_pick_more)) }
        }
    }
}
