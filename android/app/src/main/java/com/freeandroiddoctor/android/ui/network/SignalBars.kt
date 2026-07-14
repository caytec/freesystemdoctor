package com.freeandroiddoctor.android.ui.network

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp

/** Four-bar Wi-Fi signal indicator; top bar pulses when [animated] and [level] == 4. */
@Composable
fun SignalBars(
    level: Int,
    modifier: Modifier = Modifier,
    animated: Boolean = false,
) {
    val clamped = level.coerceIn(0, 4)
    val active = MaterialTheme.colorScheme.primary
    val track = MaterialTheme.colorScheme.surfaceContainerHigh
    val pulseT = rememberInfiniteTransition(label = "sigPulse")
    val pulse by pulseT.animateFloat(
        initialValue = 0.85f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(tween(900), RepeatMode.Reverse),
        label = "pulseA",
    )
    Row(
        modifier = modifier.size(width = 36.dp, height = 28.dp),
        verticalAlignment = Alignment.Bottom,
        horizontalArrangement = Arrangement.spacedBy(3.dp),
    ) {
        val heights = listOf(8.dp, 14.dp, 20.dp, 28.dp)
        heights.forEachIndexed { i, h ->
            val isOn = i < clamped
            val color = if (isOn) active else track
            val alpha = if (animated && isOn && i == 3) pulse else 1f
            Box(
                modifier = Modifier
                    .width(6.dp)
                    .height(h)
                    .clip(RoundedCornerShape(2.dp))
                    .background(color)
                    .graphicsLayer { this.alpha = alpha },
            )
        }
    }
}
