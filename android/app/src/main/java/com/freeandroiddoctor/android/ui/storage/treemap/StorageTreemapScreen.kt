package com.freeandroiddoctor.android.ui.storage.treemap

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.core.util.ByteFormatter
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.InfoBanner
import com.freeandroiddoctor.android.ui.components.ShimmerList
import kotlinx.coroutines.launch

@Composable
fun StorageTreemapScreen(modifier: Modifier = Modifier) {
    val scope = rememberCoroutineScope()
    var rootUri by remember { mutableStateOf<Uri?>(null) }
    var stack by remember { mutableStateOf<List<Pair<TreemapNode, Uri>>>(emptyList()) }
    var loading by remember { mutableStateOf(false) }

    val pick = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocumentTree(),
    ) { uri ->
        if (uri != null) {
            rootUri = uri
            loading = true
            scope.launch {
                ServiceLocator.safTreeStore.persist(uri)
                val node = ServiceLocator.storageTreemapEngine.scan(uri)
                stack = listOf(node to uri)
                loading = false
            }
        }
    }

    LaunchedEffect(Unit) {
        ServiceLocator.safTreeStore.current()?.let { uri ->
            rootUri = uri
            loading = true
            val node = ServiceLocator.storageTreemapEngine.scan(uri)
            stack = listOf(node to uri)
            loading = false
        }
    }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Appear { InfoBanner(stringResource(R.string.storage_treemap_note)) }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { pick.launch(null) }) {
                Text(stringResource(R.string.corpse_finder_pick))
            }
            if (stack.size > 1) {
                OutlinedButton(onClick = { stack = stack.dropLast(1) }) {
                    Text(stringResource(R.string.storage_treemap_up))
                }
            }
        }

        val current = stack.lastOrNull()?.first
        val treemapState = when {
            loading -> "loading"
            rootUri == null || current == null -> "grant"
            current.children.isEmpty() -> "empty"
            else -> "content"
        }
        AnimatedContent(
            targetState = treemapState,
            transitionSpec = {
                slideInVertically(tween(260)) { -it / 2 } + fadeIn(tween(260)) togetherWith
                    slideOutVertically(tween(180)) { it / 2 } + fadeOut(tween(180))
            },
            label = "storageTreemapState",
        ) { s ->
            when (s) {
                "loading" -> ShimmerList()
                "grant" -> Text(
                    stringResource(R.string.storage_treemap_grant),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                "empty" -> Text(
                    "${current?.label} · ${ByteFormatter.format(current?.sizeBytes ?: 0L)}",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                else -> {
                    val node = current!!
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(
                            "${node.label} · ${ByteFormatter.format(node.sizeBytes)}",
                            style = MaterialTheme.typography.titleSmall,
                        )
                        Box(modifier = Modifier.fillMaxWidth().weight(1f, fill = true)) {
                            SquarifiedTreemap(
                                root = node,
                                onTap = { tapped ->
                                    // Drill in if the tapped node has children.
                                    if (tapped.children.isNotEmpty()) {
                                        val parentUri = stack.last().second
                                        scope.launch {
                                            val deeper = ServiceLocator.storageTreemapEngine.expand(parentUri, tapped)
                                            stack = stack + (deeper to parentUri)
                                        }
                                    }
                                },
                            )
                        }
                    }
                }
            }
        }
    }
}
