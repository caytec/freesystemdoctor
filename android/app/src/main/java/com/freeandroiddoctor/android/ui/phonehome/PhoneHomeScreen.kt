package com.freeandroiddoctor.android.ui.phonehome

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.util.ByteFormatter
import com.freeandroiddoctor.android.engine.network.PhoneHomeItem
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.PermissionGate
import com.freeandroiddoctor.android.ui.components.ShimmerList
import com.freeandroiddoctor.android.ui.components.ThinProgress
import kotlin.math.roundToInt

@Composable
fun PhoneHomeScreen(
    modifier: Modifier = Modifier,
    viewModel: PhoneHomeViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    com.freeandroiddoctor.android.ui.components.OnResume { viewModel.load() }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoBanner(stringResource(R.string.phonehome_note))

        if (!state.hasUsageAccess) {
            PermissionGate(
                message = stringResource(R.string.app_usage_need_access),
                actionLabel = stringResource(R.string.perm_grant),
                onAction = { runCatching { context.startActivity(viewModel.usageAccessIntent()) } },
            )
            return@Column
        }

        when {
            state.loading -> ShimmerList(rows = 6)
            state.items.isEmpty() -> Text(
                stringResource(R.string.phonehome_empty),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            else -> LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(state.items, key = { it.packageName }) { item ->
                    PhoneHomeCard(
                        item = item,
                        onManage = {
                            runCatching {
                                context.startActivity(viewModel.appDetailsIntent(item.packageName))
                            }
                        },
                        modifier = Modifier.animateItem(),
                    )
                }
            }
        }
    }
}

@Composable
private fun PhoneHomeCard(
    item: PhoneHomeItem,
    onManage: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    item.label,
                    style = MaterialTheme.typography.titleSmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f).padding(end = 8.dp),
                )
                Text(
                    stringResource(R.string.phonehome_bg_pct, (item.backgroundFraction * 100).roundToInt()),
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
            ThinProgress(
                progress = item.backgroundFraction,
                modifier = Modifier.padding(vertical = 8.dp),
            )
            Text(
                stringResource(
                    R.string.phonehome_breakdown,
                    ByteFormatter.format(item.backgroundBytes),
                    ByteFormatter.format(item.foregroundBytes),
                ),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            TextButton(onClick = onManage, modifier = Modifier.padding(top = 4.dp)) {
                Text(stringResource(R.string.phonehome_restrict))
            }
        }
    }
}
