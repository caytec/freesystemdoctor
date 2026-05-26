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
