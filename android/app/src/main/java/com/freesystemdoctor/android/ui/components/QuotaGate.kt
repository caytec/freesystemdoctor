package com.freesystemdoctor.android.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.WorkspacePremium
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonColors
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.data.quota.DailyQuotaStore
import kotlinx.coroutines.launch

/**
 * Wraps an action button with a daily-quota counter. Free-tier users see a
 * "n/limit today" badge; once exhausted, the button routes to the PRO upsell
 * via [LocalUnlockController]. PRO users see no badge and the original button.
 */
@Composable
fun QuotaGatedButton(
    text: String,
    quotaKey: DailyQuotaStore.Key,
    unlockRoute: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    colors: ButtonColors = ButtonDefaults.buttonColors(),
    onConsume: suspend () -> Unit,
) {
    val billing = ServiceLocator.billingManager
    val store = ServiceLocator.dailyQuotaStore
    val isPro by billing.isPro.collectAsState()
    val used by store.used(quotaKey).collectAsState(initial = 0)
    val controller = LocalUnlockController.current
    val scope = rememberCoroutineScope()

    val exhausted = !isPro && used >= quotaKey.limit

    Row(
        modifier = modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Button(
            modifier = Modifier.weight(1f),
            enabled = enabled && !exhausted,
            colors = colors,
            shape = RoundedCornerShape(14.dp),
            onClick = {
                if (exhausted) {
                    controller.request(unlockRoute)
                } else {
                    scope.launch {
                        store.consume(quotaKey)
                        onConsume()
                    }
                }
            },
        ) {
            if (exhausted) {
                Icon(Icons.Filled.Lock, contentDescription = null, modifier = Modifier.size(16.dp))
            }
            Text(text, modifier = Modifier.padding(start = if (exhausted) 8.dp else 0.dp))
        }
        if (!isPro) {
            AssistChip(
                onClick = { controller.request(unlockRoute) },
                label = {
                    Text(
                        text = "$used/${quotaKey.limit}",
                        style = MaterialTheme.typography.labelSmall,
                    )
                },
                leadingIcon = {
                    Icon(
                        Icons.Filled.WorkspacePremium,
                        contentDescription = null,
                        modifier = Modifier.size(14.dp),
                        tint = MaterialTheme.colorScheme.primary,
                    )
                },
                colors = AssistChipDefaults.assistChipColors(
                    containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.08f),
                ),
            )
        }
    }
}
