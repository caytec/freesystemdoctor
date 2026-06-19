package com.freeandroiddoctor.android.ui.appcleaners

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.core.util.ByteFormatter
import com.freeandroiddoctor.android.engine.appcleaners.AppCleanerStrategy
import com.freeandroiddoctor.android.engine.appcleaners.TargetHit
import com.freeandroiddoctor.android.engine.appcleaners.strategies.DiscordCleaner
import com.freeandroiddoctor.android.engine.appcleaners.strategies.TelegramCleaner
import com.freeandroiddoctor.android.engine.appcleaners.strategies.TikTokCleaner
import com.freeandroiddoctor.android.engine.appcleaners.strategies.WhatsAppCleaner
import com.freeandroiddoctor.android.engine.appdeep.Safety
import com.freeandroiddoctor.android.ui.components.InfoBanner
import kotlinx.coroutines.launch

@Composable fun WhatsAppCleanerScreen(modifier: Modifier = Modifier) = StrategyScreen(WhatsAppCleaner, modifier)
@Composable fun TelegramCleanerScreen(modifier: Modifier = Modifier) = StrategyScreen(TelegramCleaner, modifier)
@Composable fun DiscordCleanerScreen(modifier: Modifier = Modifier) = StrategyScreen(DiscordCleaner, modifier)
@Composable fun TikTokCleanerScreen(modifier: Modifier = Modifier) = StrategyScreen(TikTokCleaner, modifier)

@Composable
private fun StrategyScreen(strategy: AppCleanerStrategy, modifier: Modifier = Modifier) {
    val scope = rememberCoroutineScope()
    var rootUri by remember { mutableStateOf<Uri?>(null) }
    var hits by remember { mutableStateOf<List<TargetHit>>(emptyList()) }
    var selected by remember { mutableStateOf<Set<String>>(emptySet()) }
    var freedBytes by remember { mutableStateOf(0L) }
    var scanning by remember { mutableStateOf(false) }

    val pick = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocumentTree(),
    ) { uri ->
        if (uri != null) {
            scope.launch {
                ServiceLocator.safTreeStore.persist(uri)
                rootUri = uri
                runScan(strategy, uri) { newHits ->
                    hits = newHits
                    selected = newHits.filter { it.target.safety != Safety.OPT_IN }
                        .map { it.folderUri.toString() }.toSet()
                }
            }
        }
    }

    LaunchedEffect(Unit) {
        ServiceLocator.safTreeStore.current()?.let { uri ->
            rootUri = uri
            scanning = true
            runScan(strategy, uri) { newHits ->
                hits = newHits
                selected = newHits.filter { it.target.safety != Safety.OPT_IN }
                    .map { it.folderUri.toString() }.toSet()
                scanning = false
            }
        }
    }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoBanner(stringResource(R.string.app_deep_clean_note))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { pick.launch(null) }) {
                Text(stringResource(R.string.corpse_finder_pick))
            }
        }
        if (freedBytes > 0) {
            Text(
                stringResource(R.string.cleaner_freed, ByteFormatter.format(freedBytes)),
                color = MaterialTheme.colorScheme.secondary,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        if (rootUri == null) {
            Text(stringResource(R.string.storage_treemap_grant), color = MaterialTheme.colorScheme.onSurfaceVariant)
            return@Column
        }
        if (hits.isEmpty()) {
            Text(stringResource(R.string.app_deep_clean_empty), color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            Button(
                enabled = selected.isNotEmpty(),
                onClick = {
                    scope.launch {
                        val chosen = hits.filter { it.folderUri.toString() in selected }
                        val result = ServiceLocator.appCleanersEngine.clean(chosen)
                        freedBytes += result.bytesFreed
                        ServiceLocator.cleaningHistoryEngine.recordClean(
                            strategy.historySource, result.bytesFreed, result.itemsRemoved,
                        )
                        rootUri?.let { uri ->
                            runScan(strategy, uri) { newHits ->
                                hits = newHits
                                selected = newHits.filter { it.target.safety != Safety.OPT_IN }
                                    .map { it.folderUri.toString() }.toSet()
                            }
                        }
                    }
                },
            ) { Text(stringResource(R.string.app_deep_clean_run)) }

            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(hits, key = { it.folderUri.toString() }) { hit ->
                    HitCard(
                        hit = hit,
                        checked = hit.folderUri.toString() in selected,
                        onToggle = {
                            val k = hit.folderUri.toString()
                            selected = if (k in selected) selected - k else selected + k
                        },
                    )
                }
            }
        }
    }
}

private suspend fun runScan(
    strategy: AppCleanerStrategy,
    rootUri: Uri,
    onResult: (List<TargetHit>) -> Unit,
) {
    val media = ServiceLocator.safTreeStore.androidMediaTreeUri.let { _ ->
        // Use both treeUri + androidMedia for richer SAF coverage.
        listOfNotNull(rootUri)
    }
    val result = ServiceLocator.appCleanersEngine.scan(strategy, media)
    onResult(result)
}

@Composable
private fun HitCard(hit: TargetHit, checked: Boolean, onToggle: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Checkbox(checked = checked, onCheckedChange = { onToggle() })
                Column {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        SafetyChip(hit.target.safety)
                        Text(hit.target.label, style = MaterialTheme.typography.bodyMedium)
                    }
                    Text(
                        hit.target.relPath,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            Text(
                ByteFormatter.format(hit.sizeBytes),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.primary,
            )
        }
    }
}

@Composable
private fun SafetyChip(s: Safety) {
    val (label, color) = when (s) {
        Safety.SAFE -> stringResource(R.string.app_deep_clean_safety_safe) to MaterialTheme.colorScheme.secondary
        Safety.CAUTIOUS -> stringResource(R.string.app_deep_clean_safety_cautious) to MaterialTheme.colorScheme.tertiary
        Safety.OPT_IN -> stringResource(R.string.app_deep_clean_safety_optin) to MaterialTheme.colorScheme.outline
    }
    Box(
        modifier = Modifier
            .clip(MaterialTheme.shapes.extraSmall)
            .background(color.copy(alpha = 0.18f))
            .padding(horizontal = 6.dp, vertical = 2.dp),
    ) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = color)
    }
}
