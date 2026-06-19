package com.freeandroiddoctor.android.ui.focus

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.PermissionGate

@Composable
fun FocusScreen(
    modifier: Modifier = Modifier,
    viewModel: FocusViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Appear { InfoBanner(stringResource(R.string.focus_note)) }

        if (!state.dndGranted) {
            PermissionGate(
                message = stringResource(R.string.focus_dnd_perm),
                actionLabel = stringResource(R.string.focus_dnd_grant),
                onAction = {
                    runCatching { context.startActivity(viewModel.dndIntent()) }
                },
            )
        }

        if (state.running) {
            Button(
                onClick = viewModel::end,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(stringResource(R.string.focus_end)) }
        } else {
            Button(
                onClick = viewModel::start,
                enabled = state.dndGranted,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(stringResource(R.string.focus_start)) }
        }

        OutlinedButton(onClick = viewModel::refresh, modifier = Modifier.fillMaxWidth()) {
            Text(stringResource(R.string.refresh))
        }

        Text(
            stringResource(R.string.battery_no_wear),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
