package com.freesystemdoctor.android.ui.storage.treemap

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.core.util.ByteFormatter
import com.freesystemdoctor.android.ui.components.InfoBanner
import com.freesystemdoctor.android.ui.components.ShimmerList
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
        InfoBanner(stringResource(R.string.storage_treemap_note))

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
        when {
            loading -> ShimmerList()
            rootUri == null || current == null -> Text(
                stringResource(R.string.storage_treemap_grant),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            current.children.isEmpty() -> Text(
                "${current.label} · ${ByteFormatter.format(current.sizeBytes)}",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            else -> {
                Text(
                    "${current.label} · ${ByteFormatter.format(current.sizeBytes)}",
                    style = MaterialTheme.typography.titleSmall,
                )
                Box(modifier = Modifier.fillMaxWidth().height(420.dp)) {
                    SquarifiedTreemap(
                        root = current,
                        onTap = { node ->
                            // Drill in if the tapped node has children.
                            if (node.children.isNotEmpty()) {
                                val parentUri = stack.last().second
                                scope.launch {
                                    val deeper = ServiceLocator.storageTreemapEngine.expand(parentUri, node)
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
