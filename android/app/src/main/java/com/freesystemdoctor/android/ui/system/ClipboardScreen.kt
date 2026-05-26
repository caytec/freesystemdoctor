package com.freesystemdoctor.android.ui.system

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.ui.components.Appear
import com.freesystemdoctor.android.ui.components.InfoBanner

@Composable
fun ClipboardScreen(modifier: Modifier = Modifier) {
    val engine = remember { ServiceLocator.clipboardEngine }
    var cleared by remember { mutableStateOf(false) }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear { InfoBanner(stringResource(R.string.clipboard_note)) }
        Appear(index = 1) {
            Button(
                onClick = { cleared = engine.clear() },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(stringResource(R.string.clipboard_clear))
            }
        }
        if (cleared) {
            Text(
                stringResource(R.string.clipboard_done),
                color = MaterialTheme.colorScheme.secondary,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}
