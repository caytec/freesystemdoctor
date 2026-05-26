package com.freesystemdoctor.android.ui.storage

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freesystemdoctor.android.R
import com.freesystemdoctor.android.core.util.ByteFormatter
import com.freesystemdoctor.android.engine.media.MediaCategory
import com.freesystemdoctor.android.ui.components.Appear
import com.freesystemdoctor.android.ui.components.StatCard

@Composable
fun StorageByTypeScreen(
    modifier: Modifier = Modifier,
    viewModel: StorageByTypeViewModel = viewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    LaunchedEffect(Unit) { viewModel.load() }

    Column(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        state.categories.forEachIndexed { index, usage ->
            Appear(index = index) {
                StatCard(
                    title = categoryLabel(context, usage.category),
                    value = ByteFormatter.format(usage.totalBytes),
                    subtitle = stringResource(R.string.storage_type_count, usage.count),
                    progress = usage.totalBytes.toFloat() / state.maxBytes,
                )
            }
        }
    }
}

private fun categoryLabel(context: android.content.Context, category: MediaCategory): String {
    val id = when (category) {
        MediaCategory.IMAGES -> R.string.type_images
        MediaCategory.VIDEO -> R.string.type_video
        MediaCategory.AUDIO -> R.string.type_audio
        MediaCategory.DOCUMENTS -> R.string.type_documents
        MediaCategory.ARCHIVES -> R.string.type_archives
        MediaCategory.OTHER -> R.string.type_other
    }
    return context.getString(id)
}
