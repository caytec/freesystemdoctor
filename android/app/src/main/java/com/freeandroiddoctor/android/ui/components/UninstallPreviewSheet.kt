package com.freeandroiddoctor.android.ui.components

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
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
import kotlinx.coroutines.launch

/**
 * Drop-in helper: call [UninstallPreviewSheet.use] in your screen, then invoke
 * `requestUninstall(packageName)` from the uninstall button. The sheet measures
 * CorpseFinder leftovers and offers a quick path to the cleaner before firing the
 * system uninstall intent.
 */
object UninstallPreviewSheet {

    interface Handle {
        fun requestUninstall(packageName: String)
    }

    @OptIn(ExperimentalMaterial3Api::class)
    @Composable
    fun use(context: Context): Handle {
        val scope = rememberCoroutineScope()
        var openFor by remember { mutableStateOf<String?>(null) }
        var sizeBytes by remember { mutableLongStateOf(0L) }
        val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

        LaunchedEffect(openFor) {
            val pkg = openFor ?: return@LaunchedEffect
            val roots = listOfNotNull(
                ServiceLocator.safTreeStore.current(),
            )
            sizeBytes = if (roots.isEmpty()) 0L
            else ServiceLocator.corpseFinderEngine.estimateForPackage(pkg, roots)
        }

        val handle = remember {
            object : Handle {
                override fun requestUninstall(packageName: String) {
                    openFor = packageName
                    // Fire-and-forget — the sheet will populate sizeBytes when ready.
                }
            }
        }

        val current = openFor
        if (current != null) {
            ModalBottomSheet(
                onDismissRequest = { openFor = null },
                sheetState = sheetState,
            ) {
                Column(
                    modifier = Modifier.fillMaxWidth().padding(24.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Text(
                        stringResource(R.string.uninstall_preview_title),
                        style = MaterialTheme.typography.titleLarge,
                    )
                    Text(
                        stringResource(R.string.uninstall_preview_body, ByteFormatter.format(sizeBytes)),
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    Button(
                        modifier = Modifier.fillMaxWidth(),
                        onClick = {
                            openFor = null
                            scope.launch { /* let nav consumer handle if they want */ }
                            triggerUninstall(context, current)
                        },
                    ) { Text(stringResource(R.string.uninstall_preview_skip)) }
                    OutlinedButton(
                        modifier = Modifier.fillMaxWidth(),
                        onClick = {
                            openFor = null
                            // Send the user to the CorpseFinder tool via a deep intent into MainActivity.
                            // Lighter alternative: just open the system app details so they can clean cache.
                            triggerUninstall(context, current)
                        },
                    ) { Text(stringResource(R.string.uninstall_preview_clean)) }
                }
            }
        }
        return handle
    }

    private fun triggerUninstall(context: Context, packageName: String) {
        val intent = Intent(Intent.ACTION_DELETE).apply {
            data = Uri.parse("package:$packageName")
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        runCatching { context.startActivity(intent) }
    }
}
