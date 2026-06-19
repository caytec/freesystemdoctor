package com.freeandroiddoctor.android.ui.settings

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.BuildConfig
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.ai.AiProvider
import com.freeandroiddoctor.android.ui.components.GlassCard
import com.freeandroiddoctor.android.ui.components.SectionHeader
import com.freeandroiddoctor.android.ui.navigation.ToolRoutes

private const val PRIVACY_POLICY_URL = "https://caytec.github.io/FreeAndroidDoctor/privacy-android.html"

@Composable
fun SettingsScreen(
    onNavigate: (String) -> Unit = {},
    modifier: Modifier = Modifier,
    viewModel: SettingsViewModel = viewModel(),
) {
    val settings by viewModel.settings.collectAsStateWithLifecycle()
    val hasKey by viewModel.hasKey.collectAsStateWithLifecycle()
    var keyInput by remember { mutableStateOf("") }
    val context = LocalContext.current

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        // ── Appearance ────────────────────────────────────────────
        SectionHeader(stringResource(R.string.settings_appearance))
        GlassCard {
            Column(
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                PreferenceRow(
                    title = stringResource(R.string.settings_theme),
                ) {
                    Switch(
                        checked = settings.darkTheme,
                        onCheckedChange = viewModel::setDarkTheme,
                        enabled = !settings.followSystem,
                    )
                }
                PreferenceRow(
                    title = stringResource(R.string.settings_follow_system),
                    subtitle = stringResource(R.string.settings_follow_system_desc),
                ) {
                    Switch(
                        checked = settings.followSystem,
                        onCheckedChange = viewModel::setFollowSystem,
                    )
                }
            }
        }

        // ── Cleaning ──────────────────────────────────────────────
        SectionHeader(stringResource(R.string.settings_cleaning))
        GlassCard {
            Column(
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                PreferenceRow(
                    title = stringResource(R.string.tool_schedule),
                    subtitle = stringResource(R.string.schedule_note),
                ) {
                    Switch(
                        checked = settings.scheduledCleaning,
                        onCheckedChange = viewModel::setScheduledCleaning,
                    )
                }
                if (settings.scheduledCleaning) {
                    TextButton(
                        onClick = { onNavigate(ToolRoutes.SCHEDULE) },
                        modifier = Modifier.align(Alignment.End),
                    ) {
                        Text(stringResource(R.string.settings_schedule_configure))
                        Icon(Icons.Filled.ChevronRight, contentDescription = null)
                    }
                }
                PreferenceRow(title = stringResource(R.string.settings_advanced)) {
                    Switch(
                        checked = settings.advancedMode,
                        onCheckedChange = viewModel::setAdvancedMode,
                    )
                }
            }
        }

        // ── AI Assistant ──────────────────────────────────────────
        SectionHeader(stringResource(R.string.settings_ai_provider))
        GlassCard {
            Column(
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    AiProvider.entries.forEach { provider ->
                        FilterChip(
                            selected = settings.aiProvider == provider,
                            onClick = { viewModel.setProvider(provider) },
                            label = { Text(provider.displayName) },
                            leadingIcon = if (settings.aiProvider == provider) {
                                { Icon(Icons.Filled.AutoAwesome, contentDescription = null) }
                            } else null,
                        )
                    }
                }
                OutlinedTextField(
                    value = keyInput,
                    onValueChange = { keyInput = it },
                    label = { Text(stringResource(R.string.settings_ai_key_hint)) },
                    visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        onClick = {
                            viewModel.saveKey(keyInput)
                            keyInput = ""
                        },
                        enabled = keyInput.isNotBlank(),
                    ) { Text(stringResource(R.string.settings_ai_save)) }
                    OutlinedButton(onClick = viewModel::clearKey, enabled = hasKey) {
                        Text(stringResource(R.string.settings_ai_clear))
                    }
                }
                if (hasKey) {
                    Text(
                        stringResource(R.string.perm_granted),
                        color = MaterialTheme.colorScheme.secondary,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            }
        }

        // ── Monitoring ────────────────────────────────────────────
        SectionHeader(stringResource(R.string.settings_monitoring))
        GlassCard {
            Column(
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
            ) {
                PreferenceRow(
                    title = stringResource(R.string.monitor_toggle),
                    subtitle = stringResource(R.string.monitor_desc),
                ) {
                    Switch(
                        checked = settings.monitorEnabled,
                        onCheckedChange = viewModel::setMonitorEnabled,
                    )
                }
            }
        }

        // ── Power-user mode (Shizuku) ─────────────────────────────
        SectionHeader(stringResource(R.string.settings_shizuku_section))
        GlassCard {
            Column(
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                PreferenceRow(
                    title = stringResource(R.string.settings_shizuku_toggle),
                    subtitle = stringResource(R.string.settings_shizuku_desc),
                ) {
                    Switch(
                        checked = settings.shizukuEnabled,
                        onCheckedChange = viewModel::setShizukuEnabled,
                    )
                }
                val status = viewModel.shizukuStatusLabel()
                Text(
                    status,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }

        // ── About & Legal ─────────────────────────────────────────
        SectionHeader(stringResource(R.string.settings_about))
        GlassCard {
            Column(
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text(
                    stringResource(R.string.settings_about_body),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        stringResource(R.string.settings_version),
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    Text(
                        BuildConfig.VERSION_NAME,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                TextButton(
                    onClick = {
                        context.startActivity(
                            Intent(Intent.ACTION_VIEW, Uri.parse(PRIVACY_POLICY_URL))
                        )
                    },
                ) {
                    Text(stringResource(R.string.settings_privacy_policy))
                }
            }
        }

        Spacer(Modifier.height(16.dp))
    }
}

@Composable
private fun PreferenceRow(
    title: String,
    subtitle: String? = null,
    trailing: @Composable () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = if (subtitle != null) Alignment.Top else Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f).padding(end = 16.dp)) {
            Text(title, style = MaterialTheme.typography.bodyLarge)
            if (subtitle != null) {
                Text(
                    subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        trailing()
    }
}
