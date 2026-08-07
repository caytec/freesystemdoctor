package com.freeandroiddoctor.android.ui.system

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner

@Composable
fun ClipboardScreen(modifier: Modifier = Modifier) {
    val engine = remember { ServiceLocator.clipboardEngine }
    var cleared by remember { mutableStateOf(false) }

    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear { InfoBanner(stringResource(R.string.clipboard_note)) }
        Appear(index = 1) {
            Button(
                onClick = { cleared = engine.clear() },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(stringResource(R.string.clipboard_clear))
            }
        }
        AnimatedContent(
            targetState = cleared,
            transitionSpec = {
                slideInVertically(tween(260)) { -it / 2 } + fadeIn(tween(260)) togetherWith
                    slideOutVertically(tween(180)) { it / 2 } + fadeOut(tween(180))
            },
            label = "clipboardCleared",
        ) { done ->
            if (done) {
                Text(
                    stringResource(R.string.clipboard_done),
                    color = MaterialTheme.colorScheme.secondary,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
    }
}
