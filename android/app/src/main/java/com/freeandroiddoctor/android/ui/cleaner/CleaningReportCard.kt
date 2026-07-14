package com.freeandroiddoctor.android.ui.cleaner

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.scaleIn
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Android
import androidx.compose.material.icons.filled.AutoDelete
import androidx.compose.material.icons.filled.Cached
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.ContentPaste
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.FolderOff
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material.icons.filled.Photo
import androidx.compose.material.icons.filled.Storage
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.WhereToVote
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.util.ByteFormatter

private const val DEFAULT_VISIBLE_ROWS = 5

/**
 * Post-clean / post-scan launchpad. Hero shows confirmed-deleted bytes only; every other row
 * sits under a "review to confirm" subhead with a chevron that deep-links to the engine's own
 * destructive screen. Pure-numeric rows (clipboard, empty folders) stay non-interactive.
 */
@Composable
fun CleaningReportCard(
    report: CleaningReport,
    modifier: Modifier = Modifier,
    onDismiss: () -> Unit,
    onCleanMedia: (() -> Unit)? = null,
    onOpenRoute: (String) -> Unit = {},
) {
    val heroScale by animateFloatAsState(
        targetValue = 1f,
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioMediumBouncy,
            stiffness = Spring.StiffnessLow,
        ),
        label = "hero-scale",
    )

    val primary = MaterialTheme.colorScheme.primary
    val heroBrush = remember(primary) {
        Brush.verticalGradient(listOf(primary.copy(alpha = 0.18f), primary.copy(alpha = 0f)))
    }

    var expanded by remember(report) { mutableStateOf(false) }
    val visibleRows = if (expanded) report.rows else report.rows.take(DEFAULT_VISIBLE_ROWS)
    val hiddenCount = (report.rows.size - visibleRows.size).coerceAtLeast(0)

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceContainerHigh,
        ),
        shape = MaterialTheme.shapes.large,
    ) {
        Column(modifier = Modifier.fillMaxWidth()) {
            // Hero
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(heroBrush)
                    .padding(horizontal = 20.dp, vertical = 22.dp),
            ) {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Box(
                        modifier = Modifier
                            .scale(heroScale)
                            .size(56.dp)
                            .clip(CircleShape)
                            .background(MaterialTheme.colorScheme.primary),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(
                            Icons.Filled.CheckCircle,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onPrimary,
                            modifier = Modifier.size(36.dp),
                        )
                    }
                    Text(
                        stringResource(
                            if (report.cancelled) R.string.cleaner_report_title_cancelled
                            else R.string.cleaner_report_title,
                        ),
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        ByteFormatter.format(report.cacheBytesFreed),
                        style = MaterialTheme.typography.displaySmall,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        stringResource(
                            R.string.cleaner_report_subtitle,
                            report.cacheFilesRemoved,
                        ),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    if (report.remainingReviewBytes > 0) {
                        Text(
                            stringResource(
                                R.string.cleaner_report_remaining_total,
                                ByteFormatter.format(report.remainingReviewBytes),
                            ),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.secondary,
                        )
                    }
                }
            }

            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))

            // Breakdown
            Column(
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Text(
                    stringResource(R.string.cleaner_report_breakdown_title),
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )

                visibleRows.forEach { entry ->
                    BreakdownRow(
                        entry = entry,
                        onOpen = entry.deepLinkRoute?.let { route -> { onOpenRoute(route) } },
                    )
                }

                if (hiddenCount > 0) {
                    TextButton(onClick = { expanded = true }) {
                        Text(stringResource(R.string.cleaner_report_show_all, hiddenCount))
                    }
                }

                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.4f))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        stringResource(R.string.cleaner_report_total),
                        style = MaterialTheme.typography.titleSmall,
                    )
                    Text(
                        ByteFormatter.format(report.totalReclaimableBytes),
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
            }

            // Actions
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(start = 12.dp, end = 12.dp, bottom = 12.dp),
                horizontalArrangement = Arrangement.End,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                TextButton(onClick = onDismiss) {
                    Text(stringResource(R.string.cleaner_report_done))
                }
                if (onCleanMedia != null) {
                    Spacer(Modifier.width(8.dp))
                    Button(onClick = onCleanMedia) {
                        Text(stringResource(R.string.cleaner_report_clean_media))
                    }
                }
            }
        }
    }
}

@Composable
private fun BreakdownRow(
    entry: BreakdownEntry,
    onOpen: (() -> Unit)?,
) {
    val accent = accentFor(entry.id)
    val icon = iconFor(entry.id)
    val rowModifier = Modifier
        .fillMaxWidth()
        .let { if (onOpen != null) it.clickable(onClick = onOpen) else it }
        .padding(vertical = 6.dp)

    Row(
        modifier = rowModifier,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier
                .size(36.dp)
                .clip(CircleShape)
                .background(accent.copy(alpha = 0.14f)),
            contentAlignment = Alignment.Center,
        ) {
            Icon(icon, contentDescription = null, tint = accent, modifier = Modifier.size(20.dp))
        }
        Spacer(Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                stringResource(phaseLabelRes(entry.id)),
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(
                rowDetailText(entry),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        if (entry.skipReason == null && (entry.bytes > 0 || entry.count > 0)) {
            Text(
                if (entry.bytes > 0) ByteFormatter.format(entry.bytes)
                else stringResource(R.string.cleaner_report_count_only, entry.count),
                style = MaterialTheme.typography.titleSmall,
                color = accent,
                fontWeight = FontWeight.SemiBold,
            )
        }
        if (onOpen != null && entry.skipReason == null) {
            Spacer(Modifier.width(6.dp))
            Icon(
                Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(18.dp),
            )
        }
    }
}

@Composable
private fun rowDetailText(entry: BreakdownEntry): String {
    entry.skipReason?.let { reason ->
        return when (reason) {
            SkipReason.NO_SAF -> stringResource(R.string.cleaner_report_skip_no_saf)
            SkipReason.NOT_SUPPORTED -> stringResource(R.string.cleaner_report_skip_not_supported)
            SkipReason.CANCELLED -> stringResource(R.string.cleaner_report_skip_cancelled)
        }
    }
    return if (entry.confirmedDeleted) {
        stringResource(R.string.cleaner_report_row_detail_deleted, entry.count)
    } else {
        stringResource(R.string.cleaner_report_row_detail_review, entry.count)
    }
}

@Composable
private fun accentFor(id: CleanPhaseId): Color = when (id) {
    CleanPhaseId.CACHE_CLEAN, CleanPhaseId.CACHE_SCAN -> MaterialTheme.colorScheme.primary
    CleanPhaseId.APK_SCAN, CleanPhaseId.APP_DEEP_SCAN -> MaterialTheme.colorScheme.tertiary
    CleanPhaseId.TEMP_SCAN, CleanPhaseId.LOG_FILES_SCAN -> MaterialTheme.colorScheme.secondary
    CleanPhaseId.TRASH_SCAN, CleanPhaseId.HIDDEN_CACHE_SCAN -> MaterialTheme.colorScheme.tertiary
    CleanPhaseId.CORPSE_SCAN -> MaterialTheme.colorScheme.error
    CleanPhaseId.DUPLICATE_SCAN -> MaterialTheme.colorScheme.primary
    CleanPhaseId.LARGE_FILES_SCAN -> MaterialTheme.colorScheme.secondary
    CleanPhaseId.EMPTY_FOLDER_SCAN -> MaterialTheme.colorScheme.outline
    CleanPhaseId.CLIPBOARD_SCAN -> MaterialTheme.colorScheme.outline
    CleanPhaseId.BLURRY_PHOTOS_SCAN, CleanPhaseId.SIMILAR_PHOTOS_SCAN ->
        MaterialTheme.colorScheme.secondary
    CleanPhaseId.SUMMARY -> MaterialTheme.colorScheme.primary
}

private fun iconFor(id: CleanPhaseId): ImageVector = when (id) {
    CleanPhaseId.CACHE_SCAN, CleanPhaseId.CACHE_CLEAN -> Icons.Filled.Cached
    CleanPhaseId.APK_SCAN -> Icons.Filled.Android
    CleanPhaseId.TEMP_SCAN -> Icons.Filled.Description
    CleanPhaseId.TRASH_SCAN -> Icons.Filled.AutoDelete
    CleanPhaseId.CLIPBOARD_SCAN -> Icons.Filled.ContentPaste
    CleanPhaseId.LARGE_FILES_SCAN -> Icons.Filled.Storage
    CleanPhaseId.EMPTY_FOLDER_SCAN -> Icons.Filled.FolderOff
    CleanPhaseId.LOG_FILES_SCAN -> Icons.Filled.Description
    CleanPhaseId.HIDDEN_CACHE_SCAN -> Icons.Filled.Visibility
    CleanPhaseId.CORPSE_SCAN -> Icons.Filled.Delete
    CleanPhaseId.APP_DEEP_SCAN -> Icons.Filled.Folder
    CleanPhaseId.DUPLICATE_SCAN -> Icons.Filled.ContentCopy
    CleanPhaseId.BLURRY_PHOTOS_SCAN -> Icons.Filled.Photo
    CleanPhaseId.SIMILAR_PHOTOS_SCAN -> Icons.Filled.PhotoLibrary
    CleanPhaseId.SUMMARY -> Icons.Filled.WhereToVote
}

/** Helper: drop-in animated wrapper to celebrate the report appearing. */
@Composable
fun AnimatedReport(
    report: CleaningReport?,
    onDismiss: () -> Unit,
    onCleanMedia: (() -> Unit)? = null,
    onOpenRoute: (String) -> Unit = {},
    modifier: Modifier = Modifier,
) {
    AnimatedVisibility(
        visible = report != null,
        enter = fadeIn(tween(280)) +
            scaleIn(initialScale = 0.92f, animationSpec = spring(dampingRatio = 0.7f)) +
            slideInVertically(initialOffsetY = { it / 6 }),
    ) {
        report?.let {
            CleaningReportCard(
                report = it,
                onDismiss = onDismiss,
                onCleanMedia = onCleanMedia,
                onOpenRoute = onOpenRoute,
                modifier = modifier,
            )
        }
    }
}
