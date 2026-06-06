package com.freesystemdoctor.android.ui.history

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.util.ByteFormatter
import com.freesystemdoctor.android.ui.components.Appear
import com.freesystemdoctor.android.ui.components.GlassCard
import com.freesystemdoctor.android.ui.components.InfoBanner
import com.freesystemdoctor.android.ui.components.LocalUnlockController
import com.freesystemdoctor.android.ui.components.SectionHeader
import com.freesystemdoctor.android.ui.navigation.ToolRoutes
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun CleaningHistoryScreen(viewModel: CleaningHistoryViewModel = viewModel()) {
    val ui by viewModel.ui.collectAsStateWithLifecycle()
    val isPro by viewModel.isPro.collectAsStateWithLifecycle()
    val unlockController = LocalUnlockController.current

    val createDocument = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("text/csv"),
    ) { uri ->
        if (uri != null) viewModel.exportCsv(uri)
    }

    LaunchedEffect(ui.exportSuccess, ui.exportError) {
        if (ui.exportSuccess != null || ui.exportError != null) {
            kotlinx.coroutines.delay(4_000)
            viewModel.clearExportMessages()
        }
    }

    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Icon(
                        Icons.Filled.History,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                    )
                    Text(
                        stringResource(R.string.cleaning_history_title),
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(top = 8.dp),
                    )
                    ui.summary?.let { s ->
                        Text(
                            stringResource(
                                R.string.cleaning_history_lifetime,
                                ByteFormatter.format(s.lifetimeBytesFreed),
                            ),
                            style = MaterialTheme.typography.bodyLarge,
                            color = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.padding(top = 8.dp),
                        )
                        Text(
                            stringResource(
                                R.string.cleaning_history_30d,
                                ByteFormatter.format(s.last30dBytesFreed),
                                s.last30dItemsRemoved,
                            ),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(top = 4.dp),
                        )
                    } ?: Text(
                        stringResource(R.string.cleaning_history_empty),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 8.dp),
                    )
                }
            }
        }

        InfoBanner(text = stringResource(R.string.cleaning_history_honesty_note))

        ui.exportSuccess?.let { count ->
            InfoBanner(text = stringResource(R.string.cleaning_history_export_ok, count))
        }
        ui.exportError?.let { err ->
            InfoBanner(text = stringResource(R.string.cleaning_history_export_failed, err))
        }

        // CSV export: PRO-gated.
        OutlinedButton(
            onClick = {
                if (isPro) {
                    createDocument.launch("freesystemdoctor-history.csv")
                } else {
                    unlockController.request(
                        ToolRoutes.CLEANING_HISTORY,
                        R.string.tool_cleaning_history,
                    )
                }
            },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Icon(
                if (isPro) Icons.Filled.Download else Icons.Filled.Lock,
                contentDescription = null,
            )
            Text(
                stringResource(R.string.cleaning_history_export_csv),
                modifier = Modifier.padding(start = 8.dp),
            )
        }

        SectionHeader(stringResource(R.string.cleaning_history_records))

        val records = ui.summary?.records.orEmpty()
        val dateFmt = remember { SimpleDateFormat("MMM d, HH:mm", Locale.getDefault()) }
        val visible = if (isPro) records else records.take(5)
        visible.forEach { rec ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceContainer,
                ),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(
                            dateFmt.format(Date(rec.timestamp)),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        Text(
                            rec.source.replace('_', ' ').lowercase(Locale.getDefault())
                                .replaceFirstChar { it.uppercase() },
                            style = MaterialTheme.typography.bodyMedium,
                        )
                    }
                    Text(
                        ByteFormatter.format(rec.bytesFreed),
                        style = MaterialTheme.typography.titleSmall,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
            }
        }
        if (!isPro && records.size > visible.size) {
            InfoBanner(text = stringResource(R.string.cleaning_history_more_pro, records.size - visible.size))
        }
    }
}

