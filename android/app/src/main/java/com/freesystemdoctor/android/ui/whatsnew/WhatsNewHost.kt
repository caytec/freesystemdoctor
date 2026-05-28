package com.freesystemdoctor.android.ui.whatsnew

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.res.stringArrayResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.freesystemdoctor.android.BuildConfig
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.data.settings.AppSettings
import kotlinx.coroutines.launch

/**
 * Shows a one-time "What's new" dialog the first time the user opens a new version.
 * Fresh installs are silently marked as up-to-date so the dialog only appears on updates.
 */
@Composable
fun WhatsNewHost() {
    val settings = remember { ServiceLocator.settingsRepository }
    val current = BuildConfig.VERSION_CODE
    val state by settings.settings.collectAsState(initial = AppSettings())
    val scope = rememberCoroutineScope()
    var dismissed by remember { mutableStateOf(false) }

    // Fresh install: record current version so we don't pop on first launch.
    LaunchedEffect(state.lastSeenVersionCode) {
        if (state.lastSeenVersionCode == 0) settings.setLastSeenVersionCode(current)
    }

    val show = !dismissed && state.lastSeenVersionCode in 1 until current
    if (!show) return

    val items = stringArrayResource(R.array.whats_new_items)
    AlertDialog(
        onDismissRequest = {},
        title = { Text(stringResource(R.string.whats_new_title)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                items.forEach { Text("• $it") }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                dismissed = true
                scope.launch { settings.setLastSeenVersionCode(current) }
            }) { Text(stringResource(R.string.whats_new_dismiss)) }
        },
    )
}
