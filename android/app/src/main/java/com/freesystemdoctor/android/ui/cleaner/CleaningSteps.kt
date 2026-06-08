package com.freesystemdoctor.android.ui.cleaner

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.util.ByteFormatter

@Composable
fun CleaningSteps(
    phases: List<CleanPhase>,
    modifier: Modifier = Modifier,
) {
    if (phases.isEmpty()) return
    val done = phases.count { it.status == PhaseStatus.DONE }
    val total = phases.size
    val targetFraction = if (total == 0) 0f else done.toFloat() / total
    val animatedFraction by animateFloatAsState(
        targetValue = targetFraction,
        animationSpec = tween(durationMillis = 450),
        label = "clean-progress",
    )

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceContainerHigh,
        ),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            LinearProgressIndicator(
                progress = { animatedFraction },
                modifier = Modifier.fillMaxWidth().height(6.dp).clip(CircleShape),
            )
            phases.forEach { phase ->
                AnimatedVisibility(
                    visible = phase.status != PhaseStatus.PENDING,
                    enter = fadeIn(tween(220)) +
                        expandVertically(spring(dampingRatio = 0.8f)) +
                        slideInVertically(initialOffsetY = { it / 3 }),
                    exit = fadeOut() + shrinkVertically(),
                ) {
                    StepRow(phase)
                }
            }
        }
    }
}

@Composable
private fun StepRow(phase: CleanPhase) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        StepIcon(phase.status)
        Spacer(Modifier.width(12.dp))
        Column(modifier = Modifier.fillMaxWidth()) {
            Text(
                stringResource(phaseLabelRes(phase.id)),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface,
            )
            AnimatedVisibility(
                visible = phase.status == PhaseStatus.DONE,
                enter = fadeIn(tween(180)) + expandVertically(spring(dampingRatio = 0.85f)),
            ) {
                Text(
                    phaseResultText(phase),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
        }
    }
}

@Composable
private fun StepIcon(status: PhaseStatus) {
    Box(
        modifier = Modifier.size(26.dp),
        contentAlignment = Alignment.Center,
    ) {
        when (status) {
            PhaseStatus.RUNNING -> {
                val transition = rememberInfiniteTransition(label = "spin")
                val angle by transition.animateFloat(
                    initialValue = 0f,
                    targetValue = 360f,
                    animationSpec = infiniteRepeatable(
                        animation = tween(durationMillis = 900, easing = LinearEasing),
                        repeatMode = RepeatMode.Restart,
                    ),
                    label = "spin-angle",
                )
                CircularProgressIndicator(
                    modifier = Modifier.size(20.dp).rotate(angle),
                    strokeWidth = 2.dp,
                )
            }
            PhaseStatus.DONE -> {
                Box(
                    modifier = Modifier
                        .size(24.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.primary),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        Icons.Filled.Check,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onPrimary,
                        modifier = Modifier.size(16.dp),
                    )
                }
            }
            PhaseStatus.PENDING -> {
                Box(
                    modifier = Modifier
                        .size(20.dp)
                        .clip(CircleShape)
                        .background(Color.Transparent),
                )
            }
        }
    }
}

internal fun phaseLabelRes(id: CleanPhaseId): Int = when (id) {
    CleanPhaseId.CACHE_SCAN -> R.string.cleaner_phase_cache_scan
    CleanPhaseId.CACHE_CLEAN -> R.string.cleaner_phase_cache_clean
    CleanPhaseId.APK_SCAN -> R.string.cleaner_phase_apk
    CleanPhaseId.TEMP_SCAN -> R.string.cleaner_phase_temp
    CleanPhaseId.TRASH_SCAN -> R.string.cleaner_phase_trash
    CleanPhaseId.CLIPBOARD_SCAN -> R.string.cleaner_phase_clipboard
    CleanPhaseId.LARGE_FILES_SCAN -> R.string.cleaner_phase_large_files
    CleanPhaseId.EMPTY_FOLDER_SCAN -> R.string.cleaner_phase_empty_folders
    CleanPhaseId.LOG_FILES_SCAN -> R.string.cleaner_phase_log_files
    CleanPhaseId.HIDDEN_CACHE_SCAN -> R.string.cleaner_phase_hidden_cache
    CleanPhaseId.CORPSE_SCAN -> R.string.cleaner_phase_corpse
    CleanPhaseId.APP_DEEP_SCAN -> R.string.cleaner_phase_app_deep
    CleanPhaseId.DUPLICATE_SCAN -> R.string.cleaner_phase_duplicates
    CleanPhaseId.BLURRY_PHOTOS_SCAN -> R.string.cleaner_phase_blurry_photos
    CleanPhaseId.SIMILAR_PHOTOS_SCAN -> R.string.cleaner_phase_similar_photos
    CleanPhaseId.SUMMARY -> R.string.cleaner_phase_summary
}

@Composable
internal fun phaseResultText(phase: CleanPhase): String {
    phase.skipReason?.let { reason ->
        return when (reason) {
            SkipReason.NO_SAF -> stringResource(R.string.cleaner_phase_skip_no_saf)
            SkipReason.NOT_SUPPORTED -> stringResource(R.string.cleaner_phase_skip_not_supported)
            SkipReason.CANCELLED -> stringResource(R.string.cleaner_phase_skip_cancelled)
        }
    }
    val size = ByteFormatter.format(phase.bytes)
    return when (phase.id) {
        CleanPhaseId.CACHE_SCAN -> stringResource(R.string.cleaner_phase_cache_scan_result, size)
        CleanPhaseId.CACHE_CLEAN -> stringResource(
            R.string.cleaner_phase_cache_clean_result, phase.count, size,
        )
        CleanPhaseId.APK_SCAN -> stringResource(
            R.string.cleaner_phase_apk_result, phase.count, size,
        )
        CleanPhaseId.TEMP_SCAN -> stringResource(
            R.string.cleaner_phase_temp_result, phase.count, size,
        )
        CleanPhaseId.TRASH_SCAN -> stringResource(
            R.string.cleaner_phase_trash_result, phase.count, size,
        )
        CleanPhaseId.CLIPBOARD_SCAN -> stringResource(
            if (phase.count > 0) R.string.cleaner_phase_clipboard_has
            else R.string.cleaner_phase_clipboard_empty,
        )
        CleanPhaseId.LARGE_FILES_SCAN -> stringResource(
            R.string.cleaner_phase_large_files_result, phase.count, size,
        )
        CleanPhaseId.EMPTY_FOLDER_SCAN -> stringResource(
            R.string.cleaner_phase_empty_folders_result, phase.count,
        )
        CleanPhaseId.LOG_FILES_SCAN -> stringResource(
            R.string.cleaner_phase_log_files_result, phase.count, size,
        )
        CleanPhaseId.HIDDEN_CACHE_SCAN -> stringResource(
            R.string.cleaner_phase_hidden_cache_result, phase.count, size,
        )
        CleanPhaseId.CORPSE_SCAN -> stringResource(
            R.string.cleaner_phase_corpse_result, phase.count, size,
        )
        CleanPhaseId.APP_DEEP_SCAN -> stringResource(
            R.string.cleaner_phase_app_deep_result, phase.count, size,
        )
        CleanPhaseId.DUPLICATE_SCAN -> stringResource(
            R.string.cleaner_phase_duplicates_result, phase.count, size,
        )
        CleanPhaseId.BLURRY_PHOTOS_SCAN -> stringResource(
            R.string.cleaner_phase_blurry_photos_result, phase.count, size,
        )
        CleanPhaseId.SIMILAR_PHOTOS_SCAN -> stringResource(
            R.string.cleaner_phase_similar_photos_result, phase.count, size,
        )
        CleanPhaseId.SUMMARY -> stringResource(R.string.cleaner_phase_summary_result, size)
    }
}
