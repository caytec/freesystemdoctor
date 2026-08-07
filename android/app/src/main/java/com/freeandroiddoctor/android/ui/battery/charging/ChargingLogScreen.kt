package com.freeandroiddoctor.android.ui.battery.charging

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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.battery.ChargingSession
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import java.text.DateFormat
import java.util.Date
import java.util.Locale

@Composable
fun ChargingLogScreen(modifier: Modifier = Modifier) {
    // null = loading, so the empty message doesn't flash before sessions() returns.
    var sessions by remember { mutableStateOf<List<ChargingSession>?>(null) }
    LaunchedEffect(Unit) { sessions = ServiceLocator.chargingSessionEngine.sessions() }
    val df = remember { DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT) }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        InfoBanner(stringResource(R.string.charging_log_note))
        val current = sessions
        val phase = when {
            current == null -> "loading"
            current.isEmpty() -> "empty"
            else -> "content"
        }
        AnimatedContent(
            targetState = phase,
            transitionSpec = {
                slideInVertically(tween(260)) { -it / 2 } + fadeIn(tween(260)) togetherWith
                    slideOutVertically(tween(180)) { it / 2 } + fadeOut(tween(180))
            },
            label = "chargingLogPhase",
        ) { targetPhase ->
            when (targetPhase) {
                "loading" -> com.freeandroiddoctor.android.ui.components.ShimmerList(rows = 5)
                "empty" -> Text(
                    stringResource(R.string.charging_log_empty),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                else -> {
                    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        itemsIndexed(current.orEmpty(), key = { _, s -> s.startTs }) { index, s ->
                            Appear(index = index) {
                                Card(
                                    modifier = Modifier.fillMaxWidth().animateItem(),
                                    colors = CardDefaults.cardColors(
                                        containerColor = MaterialTheme.colorScheme.surfaceContainer,
                                    ),
                                    shape = MaterialTheme.shapes.medium,
                                ) {
                                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                        Text(df.format(Date(s.startTs)), style = MaterialTheme.typography.titleSmall)
                                        Text(
                                            stringResource(
                                                R.string.charging_log_session,
                                                s.fromPct,
                                                s.toPct,
                                                s.estMahAdded,
                                                String.format(Locale.US, "%.1f°C", s.peakTempC),
                                            ),
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
