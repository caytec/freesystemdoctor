package com.freesystemdoctor.android.ui.battery

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.RoundRect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.clipPath
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.freesystemdoctor.android.ui.theme.BadRed
import com.freesystemdoctor.android.ui.theme.GoodGreen
import com.freesystemdoctor.android.ui.theme.WarnAmber
import kotlin.math.PI
import kotlin.math.sin

/** Vertical battery silhouette with an animated wave filling to [levelPercent]. */
@Composable
fun BatteryWaveViz(
    levelPercent: Int,
    modifier: Modifier = Modifier,
) {
    val target = levelPercent.coerceIn(0, 100) / 100f
    val fillFraction by animateFloatAsState(target, tween(900), label = "fill")
    val color = when {
        levelPercent >= 60 -> GoodGreen
        levelPercent >= 25 -> WarnAmber
        else -> BadRed
    }
    val transition = rememberInfiniteTransition(label = "wave")
    val phase by transition.animateFloat(
        initialValue = 0f,
        targetValue = (2 * PI).toFloat(),
        animationSpec = infiniteRepeatable(tween(2200, easing = LinearEasing), RepeatMode.Restart),
        label = "phase",
    )
    val track = MaterialTheme.colorScheme.surfaceContainerHigh

    Box(modifier.size(width = 140.dp, height = 220.dp), contentAlignment = Alignment.Center) {
        Canvas(modifier = Modifier.size(140.dp, 220.dp)) {
            val w = size.width
            val h = size.height
            val capH = h * 0.05f
            val capW = w * 0.35f
            val bodyTop = capH
            val bodyHeight = h - bodyTop
            val cornerR = w * 0.16f
            val strokePx = 3.dp.toPx()

            // Cap
            drawRoundRect(
                color = track,
                topLeft = Offset((w - capW) / 2f, 0f),
                size = Size(capW, capH * 1.6f),
                cornerRadius = CornerRadius(capW * 0.20f),
            )

            // Body fill via clip + wave path
            val bodyRect = RoundRect(
                rect = Rect(0f, bodyTop, w, h),
                cornerRadius = CornerRadius(cornerR),
            )
            val clipPath = Path().apply { addRoundRect(bodyRect) }
            clipPath(clipPath) {
                val waterY = bodyTop + bodyHeight * (1f - fillFraction)
                val amplitude = w * 0.04f
                val wavePath = Path().apply {
                    moveTo(0f, h)
                    var x = 0f
                    val step = 4f
                    while (x <= w) {
                        val y = waterY + sin(x * 0.06f + phase) * amplitude
                        lineTo(x, y)
                        x += step
                    }
                    lineTo(w, h)
                    close()
                }
                drawPath(wavePath, color = color.copy(alpha = 0.90f))
            }

            // Body outline
            drawRoundRect(
                color = track,
                topLeft = Offset(0f, bodyTop),
                size = Size(w, bodyHeight),
                cornerRadius = CornerRadius(cornerR),
                style = Stroke(width = strokePx),
            )
        }
        Text(
            text = "$levelPercent%",
            style = MaterialTheme.typography.displaySmall,
            color = Color.White,
            fontWeight = FontWeight.Bold,
        )
    }
}
