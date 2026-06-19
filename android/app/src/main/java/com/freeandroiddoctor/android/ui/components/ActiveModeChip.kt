package com.freeandroiddoctor.android.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.di.ServiceLocator

/**
 * Compact "Active mode: Focus" pill that lives in the app top bar.
 * Hidden entirely when no mode is active so the bar stays tidy.
 */
@Composable
fun ActiveModeChip(modifier: Modifier = Modifier, onClick: () -> Unit = {}) {
    val store = ServiceLocator.modeStore
    val snapshot by store.activeSnapshot.collectAsState(initial = null)
    val active = snapshot ?: return

    val label = when (active.activeModeId) {
        "game" -> stringResource(R.string.mode_game)
        "travel" -> stringResource(R.string.mode_travel)
        "focus" -> stringResource(R.string.mode_focus)
        "privacy" -> stringResource(R.string.mode_privacy)
        "storage_saver" -> stringResource(R.string.mode_storage_saver)
        else -> active.activeModeId
    }

    Row(
        modifier = modifier
            .clip(RoundedCornerShape(20.dp))
            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.18f))
            .padding(horizontal = 10.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            Icons.Filled.Bolt,
            contentDescription = null,
            modifier = Modifier.size(14.dp),
            tint = MaterialTheme.colorScheme.primary,
        )
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.padding(start = 6.dp),
        )
    }
}
