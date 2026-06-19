package com.freeandroiddoctor.android.ui.cleaner

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.IntentSenderRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.spring
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.CleaningServices
import androidx.compose.material.icons.filled.Radar
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Switch
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
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.core.util.ByteFormatter
import com.freeandroiddoctor.android.data.settings.ScanDepth
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.StatCard

@Composable
fun CleanerScreen(
    modifier: Modifier = Modifier,
    onNavigate: (String) -> Unit = {},
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

    LaunchedEffect(state.cleanReport) {
        val report = state.cleanReport
        if (report != null && !state.scanning && !report.cancelled) {
            activity?.let { act ->
                com.freeandroiddoctor.android.ui.review.maybeRequestReview(
                    act,
                    ServiceLocator.settingsRepository,
                )
            }
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

        // Quick / Deep selector
        ScanDepthSelector(
            depth = state.depth,
            enabled = !state.scanning,
            onChange = viewModel::setDepth,
        )

        // Photo-toggle row, visible only on Deep
        AnimatedVisibility(visible = state.depth == ScanDepth.DEEP) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        stringResource(R.string.cleaner_include_photos_title),
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    Text(
                        stringResource(R.string.cleaner_include_photos_hint),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Switch(
                    checked = state.includePhotos,
                    onCheckedChange = viewModel::setIncludePhotos,
                    enabled = !state.scanning,
                )
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                onClick = {
                    ServiceLocator.appOpenAdManager.suppressForMillis(60_000L)
                    viewModel.scan()
                },
                enabled = !state.scanning,
            ) {
                Text(stringResource(R.string.cleaner_scan))
            }
            OutlinedButton(onClick = viewModel::cleanAppCache, enabled = !state.scanning) {
                Text(stringResource(R.string.cleaner_app_cache))
            }
            if (state.scanning) {
                OutlinedButton(onClick = viewModel::cancelScan) {
                    Text(stringResource(R.string.cleaner_cancel))
                }
            } else if (report != null && report.mediaItems.isNotEmpty()) {
                Button(onClick = {
                    ServiceLocator.appOpenAdManager.suppressForMillis(30_000L)
                    viewModel.buildDeleteRequest()?.let { pi ->
                        deleteLauncher.launch(IntentSenderRequest.Builder(pi.intentSender).build())
                    }
                }) {
                    Text(stringResource(R.string.cleaner_clean))
                }
            }
        }

        val launchMediaCleanup: () -> Unit = {
            ServiceLocator.appOpenAdManager.suppressForMillis(30_000L)
            viewModel.buildDeleteRequest()?.let { pi ->
                deleteLauncher.launch(IntentSenderRequest.Builder(pi.intentSender).build())
            }
        }

        if (state.cleanReport != null && !state.scanning) {
            AnimatedReport(
                report = state.cleanReport,
                onDismiss = viewModel::dismissReport,
                onCleanMedia = if (report != null && report.mediaItems.isNotEmpty()) launchMediaCleanup else null,
                onOpenRoute = onNavigate,
            )
        } else if (state.phases.isNotEmpty()) {
            CleaningSteps(phases = state.phases)
        }

        InfoBanner(stringResource(R.string.cleaner_note))

        Box(Modifier.fillMaxWidth().animateContentSize(spring(dampingRatio = 0.8f))) {
            report?.let {
                Appear {
                    LazyColumn(
                        modifier = Modifier.fillMaxWidth(),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        itemsIndexed(it.mediaItems, key = { _, item -> item.uri.toString() }) { _, item ->
                            Card(
                                modifier = Modifier.fillMaxWidth().animateItem(),
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
                                    verticalAlignment = Alignment.CenterVertically,
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
}

@Composable
private fun ScanDepthSelector(
    depth: ScanDepth,
    enabled: Boolean,
    onChange: (ScanDepth) -> Unit,
) {
    SingleChoiceSegmentedButtonRow(modifier = Modifier.fillMaxWidth()) {
        SegmentedButton(
            selected = depth == ScanDepth.QUICK,
            onClick = { if (enabled) onChange(ScanDepth.QUICK) },
            shape = SegmentedButtonDefaults.itemShape(index = 0, count = 2),
            icon = { Icon(Icons.Filled.Bolt, contentDescription = null) },
        ) { Text(stringResource(R.string.cleaner_scan_quick)) }
        SegmentedButton(
            selected = depth == ScanDepth.DEEP,
            onClick = { if (enabled) onChange(ScanDepth.DEEP) },
            shape = SegmentedButtonDefaults.itemShape(index = 1, count = 2),
            icon = { Icon(Icons.Filled.Radar, contentDescription = null) },
        ) { Text(stringResource(R.string.cleaner_scan_deep)) }
    }
}
