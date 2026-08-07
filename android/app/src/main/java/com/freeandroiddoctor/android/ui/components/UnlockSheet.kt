package com.freeandroiddoctor.android.ui.components

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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AddCircleOutline
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.WorkspacePremium
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.data.quota.DailyQuotaStore

/**
 * Bottom sheet that offers ways to unlock a Pro-gated tool:
 *  0) (only if request originated from a quota exhaustion) Watch an ad → +1 use today.
 *  1) Watch an ad to unlock just THIS tool for 24h.
 *  2) Watch an ad to start a one-time 3-day "Try Pro" (disabled once consumed).
 *  3) Buy Pro forever.
 *
 * Restore-purchases lives as a tertiary text link. Header copy switches to a soft
 * "your 3-day trial ended" notice when [trialJustExpired] is true.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun UnlockSheet(
    request: UnlockRequest,
    rewardedReady: Boolean,
    trialUsed: Boolean,
    trialJustExpired: Boolean,
    onWatchAdForBonus: () -> Unit,
    onWatchAdForTool: () -> Unit,
    onWatchAdForTrial: () -> Unit,
    onBuyPro: () -> Unit,
    onRestore: () -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = MaterialTheme.colorScheme.surfaceContainerHigh,
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Header(request = request, trialJustExpired = trialJustExpired)

            if (request.quotaKey != null) {
                UnlockOption(
                    icon = Icons.Filled.AddCircleOutline,
                    title = stringResource(R.string.unlock_opt_bonus_title),
                    subtitle = stringResource(R.string.unlock_opt_bonus_sub),
                    enabled = rewardedReady,
                    disabledNote = if (!rewardedReady) stringResource(R.string.unlock_ad_not_ready) else null,
                    onClick = onWatchAdForBonus,
                )
            }

            UnlockOption(
                icon = Icons.Filled.PlayArrow,
                title = stringResource(R.string.unlock_opt_tool_title),
                subtitle = stringResource(R.string.unlock_opt_tool_sub),
                enabled = rewardedReady,
                disabledNote = if (!rewardedReady) stringResource(R.string.unlock_ad_not_ready) else null,
                onClick = onWatchAdForTool,
            )

            UnlockOption(
                icon = Icons.Filled.Star,
                title = stringResource(R.string.unlock_opt_trial_title),
                subtitle = stringResource(R.string.unlock_opt_trial_sub),
                enabled = !trialUsed && rewardedReady,
                disabledNote = when {
                    trialUsed -> stringResource(R.string.unlock_trial_used)
                    !rewardedReady -> stringResource(R.string.unlock_ad_not_ready)
                    else -> null
                },
                onClick = onWatchAdForTrial,
            )

            UnlockOption(
                icon = Icons.Filled.WorkspacePremium,
                title = stringResource(R.string.unlock_opt_buy_title),
                subtitle = stringResource(R.string.unlock_opt_buy_sub),
                enabled = true,
                disabledNote = null,
                onClick = onBuyPro,
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
            ) {
                TextButton(onClick = onRestore) {
                    Text(stringResource(R.string.unlock_restore))
                }
            }
            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
private fun Header(request: UnlockRequest, trialJustExpired: Boolean) {
    val toolName = request.labelRes?.let { stringResource(it) }
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier
                .size(44.dp)
                .clip(RoundedCornerShape(14.dp))
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.14f)),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                Icons.Filled.Lock,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
            )
        }
        Spacer(Modifier.size(14.dp))
        Column {
            Text(
                text = if (trialJustExpired) {
                    stringResource(R.string.unlock_trial_expired_title)
                } else if (toolName != null) {
                    stringResource(R.string.unlock_header_tool, toolName)
                } else {
                    stringResource(R.string.unlock_header_generic)
                },
                style = MaterialTheme.typography.titleMedium,
            )
            Text(
                text = if (trialJustExpired) {
                    stringResource(R.string.unlock_trial_expired_sub)
                } else {
                    stringResource(R.string.unlock_header_sub)
                },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun UnlockOption(
    icon: ImageVector,
    title: String,
    subtitle: String,
    enabled: Boolean,
    disabledNote: String?,
    onClick: () -> Unit,
) {
    val container = if (enabled) {
        MaterialTheme.colorScheme.surfaceContainer
    } else {
        MaterialTheme.colorScheme.surfaceContainerLow
    }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(MaterialTheme.shapes.medium)
            .background(container)
            .bounceClick(enabled = enabled, onClick = onClick)
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        val tint = if (enabled) MaterialTheme.colorScheme.primary
        else MaterialTheme.colorScheme.onSurfaceVariant
        Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(28.dp))
        Spacer(Modifier.size(14.dp))
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            Text(
                disabledNote ?: subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Icon(
            Icons.Filled.ChevronRight,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

data class UnlockRequest(
    val route: String,
    val labelRes: Int? = null,
    val quotaKey: DailyQuotaStore.Key? = null,
)
