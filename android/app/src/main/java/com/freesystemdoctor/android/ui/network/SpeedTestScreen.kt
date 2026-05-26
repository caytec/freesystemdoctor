package com.freesystemdoctor.android.ui.network

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.util.ByteFormatter
import com.freesystemdoctor.android.ui.components.Appear
import com.freesystemdoctor.android.ui.components.InfoBanner
import com.freesystemdoctor.android.ui.components.StatCard
import java.util.Locale

@Composable
fun SpeedTestScreen(
    modifier: Modifier = Modifier,
    viewModel: SpeedTestViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear { InfoBanner(stringResource(R.string.speed_note)) }

        Button(
            onClick = viewModel::run,
            enabled = !state.testing,
            modifier = Modifier.fillMaxWidth(),
        ) { Text(stringResource(R.string.speed_run)) }

        if (state.testing) CircularProgressIndicator()

        state.result?.let { r ->
            if (r.success) {
                Appear {
                    StatCard(
                        title = stringResource(R.string.speed_download),
                        value = String.format(Locale.US, "%.1f Mbps", r.mbps),
                        subtitle = stringResource(
                            R.string.speed_detail,
                            ByteFormatter.format(r.bytes),
                            r.millis,
                        ),
                    )
                }
            } else {
                Text(stringResource(R.string.speed_error), color = MaterialTheme.colorScheme.error)
            }
        }
    }
}
