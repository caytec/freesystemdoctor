package com.freeandroiddoctor.android.ui.automation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.data.automation.AutoRule
import com.freeandroiddoctor.android.data.automation.AutoRuleTrigger
import com.freeandroiddoctor.android.ui.components.SectionHeader

@Composable
fun AutoRulesScreen(viewModel: AutoRulesViewModel = viewModel()) {
    val rules by viewModel.rules.collectAsStateWithLifecycle()
    LazyColumn(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        contentPadding = PaddingValues(vertical = 12.dp),
    ) {
        item { SectionHeader(stringResource(R.string.auto_rules_active)) }
        if (rules.isEmpty()) {
            item {
                Text(
                    text = stringResource(R.string.auto_rules_empty),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        items(rules, key = { it.id }) { rule ->
            RuleRow(rule, viewModel, modifier = Modifier.animateItem())
        }

        item { SectionHeader(stringResource(R.string.auto_rules_add)) }
        items(AutoRuleTrigger.values().toList(), key = { "preset_$it" }) { trigger ->
            Card(
                modifier = Modifier.fillMaxWidth().animateItem(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
                shape = MaterialTheme.shapes.medium,
            ) {
                Row(
                    modifier = Modifier.padding(14.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(text = trigger.localize(), style = MaterialTheme.typography.titleSmall)
                        Text(
                            text = trigger.localizeDescription(),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    AssistChip(
                        onClick = { viewModel.addPreset(trigger) },
                        label = { Text(stringResource(R.string.action_add)) },
                    )
                }
            }
        }
    }
}

@Composable
private fun RuleRow(
    rule: AutoRule,
    viewModel: AutoRulesViewModel,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(rule.trigger.localize(), style = MaterialTheme.typography.titleSmall)
                Text(
                    text = rule.trigger.localizeDescription(),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Switch(
                checked = rule.enabled,
                onCheckedChange = { viewModel.toggle(rule.id, it) },
            )
            IconButton(onClick = { viewModel.delete(rule.id) }) {
                Icon(Icons.Filled.Delete, contentDescription = stringResource(R.string.action_delete))
            }
        }
    }
}

@Composable
private fun AutoRuleTrigger.localize(): String = when (this) {
    AutoRuleTrigger.LOW_STORAGE -> stringResource(R.string.auto_rule_low_storage)
    AutoRuleTrigger.CHARGING_FULL -> stringResource(R.string.auto_rule_charging)
    AutoRuleTrigger.BOOT -> stringResource(R.string.auto_rule_boot)
    AutoRuleTrigger.WEEKLY_DEEP_SCAN -> stringResource(R.string.auto_rule_weekly)
    AutoRuleTrigger.OPEN_WIFI_DETECTED -> stringResource(R.string.auto_rule_open_wifi)
    AutoRuleTrigger.APP_INSTALLED -> stringResource(R.string.auto_rule_install)
}

@Composable
private fun AutoRuleTrigger.localizeDescription(): String = when (this) {
    AutoRuleTrigger.LOW_STORAGE -> stringResource(R.string.auto_rule_low_storage_desc)
    AutoRuleTrigger.CHARGING_FULL -> stringResource(R.string.auto_rule_charging_desc)
    AutoRuleTrigger.BOOT -> stringResource(R.string.auto_rule_boot_desc)
    AutoRuleTrigger.WEEKLY_DEEP_SCAN -> stringResource(R.string.auto_rule_weekly_desc)
    AutoRuleTrigger.OPEN_WIFI_DETECTED -> stringResource(R.string.auto_rule_open_wifi_desc)
    AutoRuleTrigger.APP_INSTALLED -> stringResource(R.string.auto_rule_install_desc)
}
