package com.freesystemdoctor.android.ui.pro

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.WorkspacePremium
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.ui.components.Appear
import com.freesystemdoctor.android.ui.components.bounceClick
import com.freesystemdoctor.android.ui.theme.brandGradient

@Composable
fun ProScreen(
    modifier: Modifier = Modifier,
    viewModel: ProViewModel = viewModel(),
) {
    val products by viewModel.products.collectAsStateWithLifecycle()
    val isPro by viewModel.isPro.collectAsStateWithLifecycle()
    val trialUsed by viewModel.trialUsed.collectAsStateWithLifecycle()
    val trialUntil by viewModel.trialUntil.collectAsStateWithLifecycle()
    val context = androidx.compose.ui.platform.LocalContext.current
    val activity = context.findActivity()
    var rewardGranted by remember { mutableStateOf(false) }
    var trialGranted by remember { mutableStateOf(false) }
    val trialActive = trialUntil > System.currentTimeMillis()

    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear {
            com.freesystemdoctor.android.ui.components.GlassCard(modifier = Modifier.fillMaxWidth()) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(6.dp)
                            .background(brandGradient()),
                    )
                    Column(
                        modifier = Modifier.padding(20.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) {
                        Icon(
                            Icons.Filled.WorkspacePremium,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(48.dp),
                        )
                        Text(
                            stringResource(if (isPro) R.string.pro_active else R.string.pro_title),
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(top = 8.dp),
                        )
                        Text(
                            stringResource(R.string.pro_subtitle),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(top = 4.dp),
                        )
                    }
                }
            }
        }

        val benefits = listOf(
            R.string.pro_benefit_game_boost,
            R.string.pro_benefit_ads,
            R.string.pro_benefit_advanced,
            R.string.pro_benefit_history_export,
            R.string.pro_benefit_ai_unlimited,
            R.string.pro_benefit_schedule,
            R.string.pro_benefit_monitor,
            R.string.pro_benefit_support,
        )
        benefits.forEachIndexed { i, benefit ->
            Appear(index = i) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        Icons.Filled.Check,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.secondary,
                        modifier = Modifier.size(20.dp).padding(end = 8.dp),
                    )
                    Text(stringResource(benefit), style = MaterialTheme.typography.bodyMedium)
                }
            }
        }

        if (isPro) {
            Text(
                stringResource(R.string.pro_thanks),
                color = MaterialTheme.colorScheme.secondary,
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(top = 8.dp),
            )
        } else {
            products.forEach { product ->
                Appear {
                    androidx.compose.material3.Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .bounceClick(enabled = activity != null) {
                                activity?.let { viewModel.purchase(it, product) }
                            },
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceContainer,
                        ),
                        shape = MaterialTheme.shapes.medium,
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(16.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(product.title, style = MaterialTheme.typography.titleMedium)
                                Text(
                                    product.price,
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.primary,
                                )
                            }
                            Text(
                                stringResource(R.string.pro_buy),
                                style = MaterialTheme.typography.labelLarge,
                                color = MaterialTheme.colorScheme.primary,
                            )
                        }
                    }
                }
            }

            if (products.isEmpty()) {
                Text(
                    stringResource(R.string.pro_unavailable),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            OutlinedButton(onClick = viewModel::restore, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.pro_restore))
            }

            // 3-day Pro trial via rewarded ad (one-time).
            if (viewModel.rewardedReady() && activity != null && !trialUsed) {
                com.freesystemdoctor.android.ui.components.GradientButton(
                    text = stringResource(R.string.pro_try_trial),
                    onClick = { viewModel.watchAdForTrial(activity) { trialGranted = true } },
                )
                Text(
                    stringResource(R.string.pro_try_trial_sub),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (trialGranted || trialActive) {
                Text(
                    stringResource(R.string.pro_trial_active),
                    color = MaterialTheme.colorScheme.secondary,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }

            // Legacy 24h global unlock — grandfathered, hidden when trial available.
            if (viewModel.rewardedReady() && activity != null && trialUsed) {
                com.freesystemdoctor.android.ui.components.GradientButton(
                    text = stringResource(R.string.pro_unlock_ad),
                    onClick = { viewModel.watchAdToUnlock(activity) { rewardGranted = true } },
                )
            }
            if (rewardGranted) {
                Text(
                    stringResource(R.string.pro_unlock_ad_done),
                    color = MaterialTheme.colorScheme.secondary,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
    }
}

private fun Context.findActivity(): Activity? {
    var ctx = this
    while (ctx is ContextWrapper) {
        if (ctx is Activity) return ctx
        ctx = ctx.baseContext
    }
    return null
}
