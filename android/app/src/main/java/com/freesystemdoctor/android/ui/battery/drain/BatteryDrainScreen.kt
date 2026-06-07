package com.freesystemdoctor.android.ui.battery.drain

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.battery.DrainEstimate
import com.freesystemdoctor.android.ui.components.InfoBanner
import java.util.Locale

@Composable
fun BatteryDrainScreen(modifier: Modifier = Modifier) {
    var rows by remember { mutableStateOf<List<DrainEstimate>>(emptyList()) }
    LaunchedEffect(Unit) { rows = ServiceLocator.batteryDrainEngine.compute() }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoBanner(stringResource(R.string.battery_drain_note))
        if (rows.isEmpty()) {
            Text(
                stringResource(R.string.battery_drain_empty),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(rows, key = { it.packageName }) { r ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceContainer,
                        ),
                        shape = MaterialTheme.shapes.medium,
                    ) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text(r.label, style = MaterialTheme.typography.titleSmall)
                            Text(
                                stringResource(
                                    R.string.battery_drain_row,
                                    r.foregroundMinutes,
                                    String.format(Locale.US, "%.1f", r.weight),
                                ),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }
        }
    }
}
