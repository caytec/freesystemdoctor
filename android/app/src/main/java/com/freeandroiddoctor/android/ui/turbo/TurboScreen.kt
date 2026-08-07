package com.freeandroiddoctor.android.ui.turbo

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.shizuku.ShizukuManager
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.OnResume
import com.freeandroiddoctor.android.ui.theme.BadRed
import com.freeandroiddoctor.android.ui.theme.GoodGreen

@Composable
fun TurboScreen(
    modifier: Modifier = Modifier,
    viewModel: TurboViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    // Shizuku can be started/stopped outside the app, so re-check on every resume.
    OnResume { viewModel.refreshStatus() }

    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoBanner(stringResource(R.string.turbo_note))

        AnimatedContent(
            targetState = state.status,
            transitionSpec = {
                slideInVertically(tween(260)) { -it / 2 } + fadeIn(tween(260)) togetherWith
                    slideOutVertically(tween(180)) { it / 2 } + fadeOut(tween(180))
            },
            label = "turboStatus",
        ) { status ->
            when (status) {
                ShizukuManager.Status.Unavailable -> SetupCard(
                    title = stringResource(R.string.turbo_unavailable_title),
                    body = stringResource(R.string.turbo_unavailable_body),
                )

                ShizukuManager.Status.Denied -> Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    SetupCard(
                        title = stringResource(R.string.turbo_denied_title),
                        body = stringResource(R.string.turbo_denied_body),
                    )
                    Button(
                        onClick = viewModel::requestPermission,
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text(stringResource(R.string.turbo_grant)) }
                }

                ShizukuManager.Status.Granted -> Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Appear(index = 0) {
                        ActionCard(
                            title = stringResource(R.string.turbo_trim_title),
                            body = stringResource(R.string.turbo_trim_body),
                            button = stringResource(R.string.turbo_trim_action),
                            enabled = state.running == null,
                            onClick = { viewModel.run(TurboAction.TRIM_CACHES) },
                        )
                    }
                    Appear(index = 1) {
                        ActionCard(
                            title = stringResource(R.string.turbo_anim_title),
                            body = stringResource(R.string.turbo_anim_body),
                            button = stringResource(R.string.turbo_anim_action),
                            enabled = state.running == null,
                            onClick = { viewModel.run(TurboAction.FAST_ANIMATIONS) },
                            // Every privileged change must be reversible, and visibly so.
                            revertLabel = stringResource(R.string.turbo_anim_revert),
                            onRevert = { viewModel.run(TurboAction.NORMAL_ANIMATIONS) },
                        )
                    }

                    state.lastSucceeded?.let { ok ->
                        Appear {
                            Text(
                                if (ok) {
                                    stringResource(R.string.turbo_done)
                                } else {
                                    state.lastMessage?.let {
                                        stringResource(R.string.turbo_failed_detail, it)
                                    } ?: stringResource(R.string.turbo_failed)
                                },
                                style = MaterialTheme.typography.bodyMedium,
                                color = if (ok) GoodGreen else BadRed,
                            )
                        }
                    }
                }
            }
        }

        Text(
            stringResource(R.string.turbo_footer),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun SetupCard(title: String, body: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(Modifier.padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            Text(
                body,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 6.dp),
            )
        }
    }
}

@Composable
private fun ActionCard(
    title: String,
    body: String,
    button: String,
    enabled: Boolean,
    onClick: () -> Unit,
    revertLabel: String? = null,
    onRevert: (() -> Unit)? = null,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
        shape = MaterialTheme.shapes.medium,
    ) {
        Column(Modifier.padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            Text(
                body,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 6.dp, bottom = 10.dp),
            )
            Button(
                onClick = onClick,
                enabled = enabled,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(button) }
            if (revertLabel != null && onRevert != null) {
                OutlinedButton(
                    onClick = onRevert,
                    enabled = enabled,
                    modifier = Modifier.fillMaxWidth().padding(top = 6.dp),
                ) { Text(revertLabel) }
            }
        }
    }
}
