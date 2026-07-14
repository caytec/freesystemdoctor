package com.freeandroiddoctor.android.core.media

import android.app.PendingIntent
import android.content.Context
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import com.freeandroiddoctor.android.core.result.CleanResult

/**
 * Single place for deleting MediaStore-indexed files the app did not create.
 * On Android 11+ this requires a user-confirmed system dialog ([buildDeleteRequest]);
 * on older versions callers fall back to [deleteLegacy].
 */
class MediaDeleteHelper(private val context: Context) {

    fun buildDeleteRequest(uris: List<Uri>): PendingIntent? {
        if (uris.isEmpty()) return null
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            MediaStore.createDeleteRequest(context.contentResolver, uris)
        } else {
            null
        }
    }

    fun deleteLegacy(uris: List<Uri>): CleanResult {
        var count = 0
        uris.forEach { uri ->
            runCatching { if (context.contentResolver.delete(uri, null, null) > 0) count++ }
        }
        return CleanResult(itemsRemoved = count, bytesFreed = 0)
    }
}
