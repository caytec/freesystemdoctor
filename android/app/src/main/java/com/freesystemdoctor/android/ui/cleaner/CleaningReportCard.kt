package com.freesystemdoctor.android.ui.cleaner

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
import androidx.compose.material.icons.filled.Android
import androidx.compose.material.icons.filled.Cached
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Description
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
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.util.ByteFormatter

/**
 * Full post-clean report: hero "X freed" headline + per-category breakdown +
 * follow-up actions for media items the user still has to confirm.
 */
@Composable
fun CleaningReportCard(
    report: CleaningReport,
    modifier: Modifier = Modifier,
    onDismiss: () -> Unit,
    onCleanMedia: (() -> Unit)? = null,
) {
    val heroScale by animateFloatAsState(
        targetValue = 1f,
        animationSpec = spring(dampingRatio = Spring.DampingRatioMediumBouncy, stiffness = Spring.StiffnessLow),
        label = "hero-scale",
    )

    val primary = MaterialTheme.colorScheme.primary
    val heroBrush = remember(primary) {
        Brush.verticalGradient(listOf(primary.copy(alpha = 0.18f), primary.copy(alpha = 0f)))
    }

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
                        stringResource(R.string.cleaner_report_title),
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
                }
            }

            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))

            // Breakdown
            Column(
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 16.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Text(
                    stringResource(R.string.cleaner_report_breakdown_title),
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )

                BreakdownRow(
                    icon = Icons.Filled.Cached,
                    label = stringResource(R.string.cleaner_report_row_cache),
                    detail = stringResource(
                        R.string.cleaner_report_row_cache_detail,
                        report.cacheFilesRemoved,
                    ),
                    bytes = report.cacheBytesFreed,
                    accent = MaterialTheme.colorScheme.primary,
                )

                AnimatedVisibility(visible = report.apkFilesFound > 0) {
                    BreakdownRow(
                        icon = Icons.Filled.Android,
                        label = stringResource(R.string.cleaner_report_row_apk),
                        detail = stringResource(
                            R.string.cleaner_report_row_apk_detail,
                            report.apkFilesFound,
                        ),
                        bytes = report.apkBytesFound,
                        accent = MaterialTheme.colorScheme.tertiary,
                    )
                }

                AnimatedVisibility(visible = report.tempFilesFound > 0) {
                    BreakdownRow(
                        icon = Icons.Filled.Description,
                        label = stringResource(R.string.cleaner_report_row_temp),
                        detail = stringResource(
                            R.string.cleaner_report_row_temp_detail,
                            report.tempFilesFound,
                        ),
                        bytes = report.tempBytesFound,
                        accent = MaterialTheme.colorScheme.secondary,
                    )
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

                AnimatedVisibility(
                    visible = report.remainingMediaItems > 0,
                    enter = fadeIn() + expandVertically(),
                ) {
                    Text(
                        stringResource(
                            R.string.cleaner_report_remaining_hint,
                            report.remainingMediaItems,
                            ByteFormatter.format(report.remainingMediaBytes),
                        ),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
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
                if (onCleanMedia != null && report.remainingMediaItems > 0) {
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
    icon: ImageVector,
    label: String,
    detail: String,
    bytes: Long,
    accent: androidx.compose.ui.graphics.Color,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier
                .size(36.dp)
                .clip(CircleShape)
                .background(accent.copy(alpha = 0.14f)),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                icon,
                contentDescription = null,
                tint = accent,
                modifier = Modifier.size(20.dp),
            )
        }
        Spacer(Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(label, style = MaterialTheme.typography.bodyMedium)
            Text(
                detail,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Text(
            ByteFormatter.format(bytes),
            style = MaterialTheme.typography.titleSmall,
            color = accent,
            fontWeight = FontWeight.SemiBold,
        )
    }
}

/** Helper: drop-in animated wrapper to celebrate the report appearing. */
@Composable
fun AnimatedReport(
    report: CleaningReport?,
    onDismiss: () -> Unit,
    onCleanMedia: (() -> Unit)? = null,
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
                modifier = modifier,
            )
        }
    }
}
