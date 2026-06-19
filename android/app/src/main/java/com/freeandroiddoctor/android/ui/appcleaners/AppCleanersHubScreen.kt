package com.freeandroiddoctor.android.ui.appcleaners

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.appcleaners.AppCleanerStrategy
import com.freeandroiddoctor.android.engine.appcleaners.strategies.DiscordCleaner
import com.freeandroiddoctor.android.engine.appcleaners.strategies.TelegramCleaner
import com.freeandroiddoctor.android.engine.appcleaners.strategies.TikTokCleaner
import com.freeandroiddoctor.android.engine.appcleaners.strategies.WhatsAppCleaner
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.bounceClick
import com.freeandroiddoctor.android.ui.navigation.ToolRoutes
import kotlinx.coroutines.launch

private data class HubEntry(
    val titleRes: Int,
    val route: String,
    val strategy: AppCleanerStrategy,
)

@Composable
fun AppCleanersHubScreen(onOpen: (String) -> Unit, modifier: Modifier = Modifier) {
    val scope = rememberCoroutineScope()
    val entries = remember {
        listOf(
            HubEntry(R.string.app_cleaner_whatsapp_title, ToolRoutes.APP_CLEANER_WHATSAPP, WhatsAppCleaner),
            HubEntry(R.string.app_cleaner_telegram_title, ToolRoutes.APP_CLEANER_TELEGRAM, TelegramCleaner),
            HubEntry(R.string.app_cleaner_discord_title, ToolRoutes.APP_CLEANER_DISCORD, DiscordCleaner),
            HubEntry(R.string.app_cleaner_tiktok_title, ToolRoutes.APP_CLEANER_TIKTOK, TikTokCleaner),
        )
    }
    var installed by remember { mutableStateOf<Set<String>>(emptySet()) }
    LaunchedEffect(Unit) {
        scope.launch {
            installed = entries.filter { ServiceLocator.appCleanersEngine.isInstalled(it.strategy.packageName) }
                .map { it.strategy.packageName }.toSet()
        }
    }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoBanner(stringResource(R.string.app_cleaners_hub_note))
        entries.forEach { entry ->
            val isInstalled = entry.strategy.packageName in installed
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .bounceClick(enabled = isInstalled) { onOpen(entry.route) },
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
                shape = MaterialTheme.shapes.medium,
            ) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(stringResource(entry.titleRes), style = MaterialTheme.typography.titleMedium)
                    Text(
                        if (isInstalled) entry.strategy.packageName
                        else stringResource(R.string.app_cleaner_install_required, entry.strategy.packageName),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}
