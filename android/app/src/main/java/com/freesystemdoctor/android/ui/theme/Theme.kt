package com.freesystemdoctor.android.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val DarkColors = darkColorScheme(
    primary = Coral,
    onPrimary = Navy,
    secondary = SkyBlue,
    onSecondary = Navy,
    background = Navy,
    onBackground = TextPrimary,
    surface = NavySurface,
    onSurface = TextPrimary,
    surfaceVariant = NavyVariant,
    onSurfaceVariant = TextSecondary,
    error = BadRed,
)

private val LightColors = lightColorScheme(
    primary = CoralDark,
    secondary = SkyBlue,
    error = BadRed,
)

@Composable
fun FsdTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = Typography,
        content = content,
    )
}
