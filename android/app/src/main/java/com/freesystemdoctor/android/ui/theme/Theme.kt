package com.freesystemdoctor.android.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

private val DarkColors = darkColorScheme(
    primary = Coral,
    onPrimary = Navy,
    primaryContainer = CoralDark,
    onPrimaryContainer = TextPrimary,
    secondary = SkyBlue,
    onSecondary = Navy,
    tertiary = Violet,
    onTertiary = Navy,
    background = Navy,
    onBackground = TextPrimary,
    surface = NavySurface,
    onSurface = TextPrimary,
    surfaceVariant = NavyVariant,
    onSurfaceVariant = TextSecondary,
    surfaceContainer = NavyVariant,
    surfaceContainerHigh = NavyElevated,
    outline = NavyElevated,
    error = BadRed,
)

private val LightColors = lightColorScheme(
    primary = CoralDark,
    onPrimary = Color.White,
    primaryContainer = CoralLight,
    onPrimaryContainer = LightText,
    secondary = SkyBlue,
    tertiary = Violet,
    background = LightBg,
    onBackground = LightText,
    surface = LightSurface,
    onSurface = LightText,
    surfaceVariant = LightSurfaceVariant,
    onSurfaceVariant = LightTextSecondary,
    surfaceContainer = LightSurfaceVariant,
    surfaceContainerHigh = Color.White,
    error = BadRed,
)

private val FsdShapes = Shapes(
    extraSmall = RoundedCornerShape(8.dp),
    small = RoundedCornerShape(12.dp),
    medium = RoundedCornerShape(18.dp),
    large = RoundedCornerShape(24.dp),
    extraLarge = RoundedCornerShape(32.dp),
)

/** Vertical background gradient used behind the whole app. */
@Composable
fun appBackgroundBrush(darkTheme: Boolean): Brush =
    if (darkTheme) {
        Brush.verticalGradient(listOf(NavyDeep, Navy, NavySurface))
    } else {
        Brush.verticalGradient(listOf(LightBg, Color(0xFFEDF2FA)))
    }

/** Brand accent gradient for primary CTAs and accent strips. */
fun brandGradient(): Brush = Brush.linearGradient(listOf(Coral, Color(0xFFB86BFF)))

/** Coral→sky gradient for the health hero. */
fun heroGradient(): Brush =
    Brush.linearGradient(listOf(Coral.copy(alpha = 0.30f), Violet.copy(alpha = 0.22f), SkyBlue.copy(alpha = 0.16f)))

/** Translucent surface for glass / blurred cards. */
fun glassBrush(darkTheme: Boolean): Brush = if (darkTheme) {
    Brush.verticalGradient(listOf(Color(0x33FFFFFF), Color(0x14FFFFFF)))
} else {
    Brush.verticalGradient(listOf(Color(0xAAFFFFFF), Color(0x66FFFFFF)))
}

/** Soft radial glow used behind hero elements. */
fun accentGlow(color: Color): Brush =
    Brush.radialGradient(listOf(color.copy(alpha = 0.45f), Color.Transparent))

@Composable
fun FsdTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = Typography,
        shapes = FsdShapes,
        content = content,
    )
}
