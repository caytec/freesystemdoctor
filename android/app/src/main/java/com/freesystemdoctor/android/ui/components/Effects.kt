package com.freesystemdoctor.android.ui.components

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.ripple
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import com.freesystemdoctor.android.ui.theme.Coral
import com.freesystemdoctor.android.ui.theme.Violet
import com.freesystemdoctor.android.ui.theme.brandGradient
import com.freesystemdoctor.android.ui.theme.glassBrush

/** Clickable with a tactile press-scale animation + haptic tap. */
@Composable
fun Modifier.bounceClick(
    enabled: Boolean = true,
    haptic: Boolean = true,
    onClick: () -> Unit,
): Modifier {
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (pressed) 0.96f else 1f,
        animationSpec = spring(),
        label = "bounce",
    )
    val hapticFeedback = LocalHapticFeedback.current
    return this
        .graphicsLayer { scaleX = scale; scaleY = scale }
        .clickable(
            interactionSource = interaction,
            indication = ripple(),
            enabled = enabled,
        ) {
            if (haptic) hapticFeedback.performHapticFeedback(HapticFeedbackType.LongPress)
            onClick()
        }
}

/** Sweeping shimmer placeholder for loading states. */
@Composable
fun ShimmerBox(
    modifier: Modifier = Modifier,
    shape: Shape = RoundedCornerShape(14.dp),
) {
    val base = MaterialTheme.colorScheme.surfaceContainer
    val highlight = MaterialTheme.colorScheme.surfaceContainerHigh
    val transition = rememberInfiniteTransition(label = "shimmer")
    val progress by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(1300, easing = LinearEasing), RepeatMode.Restart),
        label = "shimmerX",
    )
    Box(
        modifier
            .clip(shape)
            .drawWithCache {
                val w = size.width
                val start = -w + progress * (2 * w)
                val brush = Brush.linearGradient(
                    colors = listOf(base, highlight, base),
                    start = Offset(start, 0f),
                    end = Offset(start + w, 0f),
                )
                onDrawBehind { drawRect(brush) }
            },
    )
}

/** Translucent, lightly-bordered "glass" surface for hero and premium sections. */
@Composable
fun GlassCard(
    modifier: Modifier = Modifier,
    shape: Shape = RoundedCornerShape(24.dp),
    content: @Composable () -> Unit,
) {
    val dark = MaterialTheme.colorScheme.background.luminance() < 0.5f
    val borderColor = if (dark) Color(0x33FFFFFF) else Color(0x33000000)
    Box(
        modifier
            .clip(shape)
            .background(MaterialTheme.colorScheme.surfaceContainer.copy(alpha = 0.55f), shape)
            .background(glassBrush(dark), shape)
            .border(1.dp, borderColor, shape),
    ) { content() }
}

/** Primary CTA with the brand gradient, bounce + haptic. */
@Composable
fun GradientButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    val shape = RoundedCornerShape(16.dp)
    Box(
        modifier
            .fillMaxWidth()
            .heightIn(min = 52.dp)
            .clip(shape)
            .background(if (enabled) brandGradient() else Brush.linearGradient(listOf(Color(0x33808080), Color(0x33808080))))
            .bounceClick(enabled = enabled, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text,
                color = Color(0xFF0F1B2D),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 12.dp),
            )
        }
    }
}

/** Runs [onResume] every time the screen returns to the foreground (e.g. back from Settings). */
@Composable
fun OnResume(onResume: () -> Unit) {
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) { onResume() }
}

/** A column of shimmer placeholder rows for list scanning/loading states. */
@Composable
fun ShimmerList(rows: Int = 5, modifier: Modifier = Modifier) {
    Column(modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        repeat(rows) {
            ShimmerBox(Modifier.fillMaxWidth().height(64.dp))
        }
    }
}

/** Two soft, slowly drifting accent glows behind the whole app for an alive, immersive feel. */
@Composable
fun AnimatedBackdrop(modifier: Modifier = Modifier) {
    val transition = rememberInfiniteTransition(label = "backdrop")
    val drift by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(9000, easing = LinearEasing), RepeatMode.Reverse),
        label = "drift",
    )
    Box(
        modifier.fillMaxSize().drawBehind {
            val w = size.width
            val h = size.height
            val c1 = Offset(w * 0.18f, h * (0.12f + 0.10f * drift))
            val r1 = h * 0.42f
            drawCircle(
                brush = Brush.radialGradient(
                    listOf(Coral.copy(alpha = 0.10f), Color.Transparent),
                    center = c1, radius = r1,
                ),
                radius = r1, center = c1,
            )
            val c2 = Offset(w * 0.85f, h * (0.9f - 0.10f * drift))
            val r2 = h * 0.4f
            drawCircle(
                brush = Brush.radialGradient(
                    listOf(Violet.copy(alpha = 0.10f), Color.Transparent),
                    center = c2, radius = r2,
                ),
                radius = r2, center = c2,
            )
        },
    )
}
