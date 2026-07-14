package com.freeandroiddoctor.android.ui.gameboost

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.SportsEsports
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.util.ByteFormatter
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.GlassCard
import com.freeandroiddoctor.android.ui.components.GradientButton
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.SectionHeader
import com.freeandroiddoctor.android.ui.components.bounceClick
import com.freeandroiddoctor.android.ui.theme.brandGradient

@Composable
fun GameBoostScreen(viewModel: GameBoostViewModel = viewModel()) {
    val ui by viewModel.ui.collectAsStateWithLifecycle()
    val boosted by viewModel.boostedPackages.collectAsStateWithLifecycle()
    val enterDnd by viewModel.enterDnd.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
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
                            Icons.Filled.SportsEsports,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(48.dp),
                        )
                        Text(
                            stringResource(R.string.game_boost_title),
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(top = 8.dp),
                        )
                        Text(
                            stringResource(R.string.game_boost_subtitle),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(top = 4.dp),
                        )
                        Spacer(Modifier.height(12.dp))
                        if (ui.sessionRunning) {
                            GradientButton(
                                text = stringResource(R.string.game_boost_end),
                                onClick = viewModel::endSession,
                                modifier = Modifier.fillMaxWidth(),
                            )
                        } else {
                            GradientButton(
                                text = stringResource(R.string.game_boost_start),
                                onClick = viewModel::boostOnly,
                                modifier = Modifier.fillMaxWidth(),
                            )
                        }
                    }
                }
            }
        }

        if (!ui.hasDndAccess) {
            InfoBanner(text = stringResource(R.string.game_boost_dnd_missing))
        }
        InfoBanner(text = stringResource(R.string.game_boost_honesty_note))

        ui.lastResult?.let { result ->
            Appear {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surfaceContainer,
                    ),
                ) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(
                            stringResource(R.string.game_boost_result_title),
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.SemiBold,
                        )
                        Text(
                            stringResource(
                                R.string.game_boost_result_ram,
                                ByteFormatter.format(result.ramFreedBytes),
                            ),
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        Text(
                            stringResource(
                                R.string.game_boost_result_cache,
                                ByteFormatter.format(result.cacheFreedBytes),
                            ),
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        if (result.sustainedPerformanceSupported) {
                            Text(
                                stringResource(R.string.game_boost_result_sustained),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }
        }

        Appear {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceContainer,
                ),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(
                            stringResource(R.string.game_boost_dnd_label),
                            style = MaterialTheme.typography.titleSmall,
                        )
                        Text(
                            stringResource(R.string.game_boost_dnd_sub),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    Switch(checked = enterDnd, onCheckedChange = viewModel::setEnterDnd)
                }
            }
        }

        SectionHeader(stringResource(R.string.game_boost_games_header))

        if (ui.games.isEmpty() && !ui.showAllApps) {
            Text(
                stringResource(R.string.game_boost_no_games),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            TextButton(onClick = viewModel::loadAllApps) {
                Text(stringResource(R.string.game_boost_show_all))
            }
        }

        val visibleGames = if (ui.showAllApps) ui.allApps else ui.games
        visibleGames.forEach { game ->
            val isBoosted = game.packageName in boosted
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .bounceClick { viewModel.boostAndLaunch(game.packageName) },
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceContainer,
                ),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(
                        Icons.Filled.Bolt,
                        contentDescription = null,
                        tint = if (isBoosted) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Spacer(Modifier.width(8.dp))
                    Text(
                        game.label,
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.weight(1f),
                    )
                    IconButton(onClick = { viewModel.togglePackage(game.packageName) }) {
                        Icon(
                            if (isBoosted) Icons.Filled.Stop else Icons.Filled.PlayArrow,
                            contentDescription = stringResource(
                                if (isBoosted) R.string.game_boost_remove_profile
                                else R.string.game_boost_add_profile,
                            ),
                            tint = if (isBoosted) MaterialTheme.colorScheme.error
                            else MaterialTheme.colorScheme.primary,
                        )
                    }
                }
            }
        }
    }
}
