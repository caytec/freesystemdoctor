package com.freeandroiddoctor.android.ui.privacy

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Launch
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.data.privacy.PrivacyProfile
import com.freeandroiddoctor.android.data.quota.DailyQuotaStore
import com.freeandroiddoctor.android.ui.components.QuotaGatedButton
import com.freeandroiddoctor.android.ui.components.SectionHeader
import com.freeandroiddoctor.android.ui.navigation.ToolRoutes

@Composable
fun PrivacyProfilesScreen(viewModel: PrivacyProfilesViewModel = viewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current

    LazyColumn(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        contentPadding = PaddingValues(vertical = 12.dp),
    ) {
        item { SectionHeader(text = stringResource(R.string.privacy_profiles_builtin)) }
        items(state.builtIn, key = { it.id }) { p ->
            ProfileRow(
                profile = p,
                active = state.activeId == p.id,
                onPick = viewModel::buildPlan,
                modifier = Modifier.animateItem(),
            )
        }
        if (state.custom.isNotEmpty()) {
            item { SectionHeader(text = stringResource(R.string.privacy_profiles_custom)) }
            items(state.custom, key = { it.id }) { p ->
                ProfileRow(
                    profile = p,
                    active = state.activeId == p.id,
                    onPick = viewModel::buildPlan,
                    modifier = Modifier.animateItem(),
                )
            }
        }
    }

    val plan = state.plan
    if (plan != null) {
        AlertDialog(
            onDismissRequest = viewModel::clearPlan,
            title = { Text(stringResource(R.string.privacy_plan_title, plan.profile.localizedName())) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(stringResource(R.string.privacy_plan_apps, plan.steps.size))
                    if (plan.clipboardWillBeCleared) Text(stringResource(R.string.privacy_plan_clipboard))
                    if (plan.suggestPrivateDns) Text(stringResource(R.string.privacy_plan_dns))
                    plan.steps.take(5).forEach { step ->
                        Text(
                            text = "• ${step.appLabel} — ${step.violations.joinToString()}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    if (plan.steps.size > 5) {
                        Text(stringResource(R.string.privacy_plan_more, plan.steps.size - 5))
                    }
                }
            },
            confirmButton = {
                Column {
                    QuotaGatedButton(
                        text = stringResource(R.string.privacy_plan_apply),
                        quotaKey = DailyQuotaStore.Key.PRIVACY_PROFILE_APPLY,
                        unlockRoute = ToolRoutes.PRIVACY_PROFILES,
                        onConsume = {
                            plan.steps.firstOrNull()?.let { context.startActivity(it.intent) }
                            viewModel.finalizePlan()
                        },
                    )
                }
            },
            dismissButton = {
                TextButton(onClick = viewModel::clearPlan) { Text(stringResource(R.string.action_cancel)) }
            },
        )
    }
}

@Composable
private fun ProfileRow(
    profile: PrivacyProfile,
    active: Boolean,
    onPick: (PrivacyProfile) -> Unit,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(profile.localizedName(), style = MaterialTheme.typography.titleSmall)
                Text(
                    text = profile.summary(),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (active) Icon(Icons.Filled.Check, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            OutlinedButton(onClick = { onPick(profile) }) {
                Icon(Icons.Filled.Launch, contentDescription = null)
                Text(stringResource(R.string.privacy_profile_review), modifier = Modifier.padding(start = 8.dp))
            }
        }
    }
}

@Composable
private fun PrivacyProfile.localizedName(): String = when (id) {
    "balanced" -> stringResource(R.string.privacy_profile_balanced)
    "strict" -> stringResource(R.string.privacy_profile_strict)
    "game" -> stringResource(R.string.privacy_profile_game)
    else -> labelKey
}

@Composable
private fun PrivacyProfile.summary(): String {
    val parts = buildList {
        if (forbidLocation) add(stringResource(R.string.privacy_perm_location))
        if (forbidContacts) add(stringResource(R.string.privacy_perm_contacts))
        if (forbidMicrophone) add(stringResource(R.string.privacy_perm_mic))
        if (forbidCamera) add(stringResource(R.string.privacy_perm_camera))
        if (forbidSms) add(stringResource(R.string.privacy_perm_sms))
        if (clearClipboard) add(stringResource(R.string.privacy_perm_clipboard))
        if (suggestPrivateDns) add(stringResource(R.string.privacy_perm_dns))
    }
    return parts.joinToString(", ").ifEmpty { stringResource(R.string.privacy_profile_minimal) }
}
