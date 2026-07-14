package com.freeandroiddoctor.android.engine.cache

import android.content.Context
import android.net.Uri
import androidx.documentfile.provider.DocumentFile
import com.freeandroiddoctor.android.core.result.CleanResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class HiddenCachePreset(
    val packageName: String,
    val label: String,
    val subPaths: List<String>,
)

data class HiddenCacheItem(
    val preset: HiddenCachePreset,
    val folderUri: Uri,
    val sizeBytes: Long,
)

/**
 * Cleans hidden caches that popular apps store under `Android/media/<pkg>/` — the
 * "voice notes", "sent stickers" and similar shadow directories that aren't part of
 * the app's reported cache and survive the system clear-cache button.
 *
 * The user must grant SAF access to the `Android/media` tree once; from then on each
 * preset is resolved relative to that tree without further prompts.
 */
class HiddenCacheEngine(private val context: Context) {

    val presets: List<HiddenCachePreset> = listOf(
        HiddenCachePreset(
            "com.whatsapp", "WhatsApp",
            listOf("com.whatsapp/WhatsApp/Media/.Statuses"),
        ),
        HiddenCachePreset(
            "org.telegram.messenger", "Telegram",
            listOf("org.telegram.messenger/Telegram"),
        ),
        HiddenCachePreset(
            "com.discord", "Discord",
            listOf("com.discord"),
        ),
        HiddenCachePreset(
            "com.spotify.music", "Spotify",
            listOf("com.spotify.music"),
        ),
        HiddenCachePreset(
            "com.instagram.android", "Instagram",
            listOf("com.instagram.android"),
        ),
        HiddenCachePreset(
            "com.zhiliaoapp.musically", "TikTok",
            listOf("com.zhiliaoapp.musically"),
        ),
        HiddenCachePreset(
            "com.facebook.katana", "Facebook",
            listOf("com.facebook.katana"),
        ),
        HiddenCachePreset(
            "com.snapchat.android", "Snapchat",
            listOf("com.snapchat.android"),
        ),
    )

    /**
     * Walks the granted [androidMediaTree] (typically `Android/media`) and reports the size
     * of each preset folder that exists under it. Folders that aren't present are skipped.
     */
    suspend fun scan(androidMediaTree: Uri): List<HiddenCacheItem> = withContext(Dispatchers.IO) {
        val root = DocumentFile.fromTreeUri(context, androidMediaTree) ?: return@withContext emptyList()
        presets.mapNotNull { preset ->
            val folder = preset.subPaths.firstNotNullOfOrNull { resolve(root, it) }
                ?: return@mapNotNull null
            HiddenCacheItem(preset, folder.uri, sizeOf(folder))
        }.filter { it.sizeBytes > 0 }
            .sortedByDescending { it.sizeBytes }
    }

    /** Deletes everything inside [folderUri] but keeps the folder itself. */
    suspend fun clean(folderUri: Uri): CleanResult = withContext(Dispatchers.IO) {
        val doc = DocumentFile.fromTreeUri(context, folderUri)
            ?: return@withContext CleanResult(0, 0)
        var bytes = 0L
        var items = 0
        doc.listFiles().forEach { child ->
            val size = if (child.isDirectory) sizeOf(child) else child.length()
            if (deleteRecursively(child)) {
                bytes += size
                items++
            }
        }
        CleanResult(itemsRemoved = items, bytesFreed = bytes)
    }

    private fun resolve(root: DocumentFile, relativePath: String): DocumentFile? {
        var current: DocumentFile = root
        relativePath.split('/').forEach { segment ->
            if (segment.isBlank()) return@forEach
            current = current.findFile(segment) ?: return null
        }
        return current.takeIf { it.isDirectory }
    }

    private fun sizeOf(doc: DocumentFile): Long {
        var total = 0L
        val stack = ArrayDeque<DocumentFile>()
        stack.addLast(doc)
        while (stack.isNotEmpty()) {
            val cur = stack.removeLast()
            cur.listFiles().forEach { child ->
                if (child.isDirectory) stack.addLast(child) else total += child.length()
            }
        }
        return total
    }

    private fun deleteRecursively(doc: DocumentFile): Boolean {
        if (doc.isDirectory) {
            doc.listFiles().forEach { deleteRecursively(it) }
        }
        return runCatching { doc.delete() }.getOrDefault(false)
    }
}
