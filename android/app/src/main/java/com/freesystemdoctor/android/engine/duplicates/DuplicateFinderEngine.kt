package com.freesystemdoctor.android.engine.duplicates

import android.content.Context
import android.net.Uri
import android.provider.MediaStore
import com.freesystemdoctor.android.core.result.ScanProgress
import com.freesystemdoctor.android.core.util.Hashing
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class DuplicateFile(
    val uri: Uri,
    val displayName: String,
    val sizeBytes: Long,
)

data class DuplicateGroup(
    val hash: String,
    val files: List<DuplicateFile>,
) {
    /** Bytes that could be reclaimed by keeping a single copy. */
    val reclaimableBytes: Long
        get() = files.drop(1).sumOf { it.sizeBytes }
}

/**
 * Finds exact duplicate files: first buckets candidates by size, then confirms with a
 * streaming SHA-256 only for sizes that collide (avoids hashing unique files).
 */
class DuplicateFinderEngine(private val context: Context) {

    suspend fun findDuplicates(
        minBytes: Long = 1L * 1024 * 1024,
        progress: (ScanProgress) -> Unit = {},
    ): List<DuplicateGroup> = withContext(Dispatchers.IO) {
        val candidates = queryFiles(minBytes)
        val bySize = candidates.groupBy { it.sizeBytes }.filter { it.value.size > 1 }

        val byHash = HashMap<String, MutableList<DuplicateFile>>()
        val collisionFiles = bySize.values.flatten()
        collisionFiles.forEachIndexed { index, file ->
            progress(ScanProgress(index + 1, collisionFiles.size, file.displayName))
            val hash = runCatching {
                context.contentResolver.openInputStream(file.uri)?.use { Hashing.sha256(it) }
            }.getOrNull() ?: return@forEachIndexed
            byHash.getOrPut(hash) { mutableListOf() }.add(file)
        }

        byHash.filterValues { it.size > 1 }
            .map { (hash, files) -> DuplicateGroup(hash, files.sortedByDescending { it.sizeBytes }) }
            .sortedByDescending { it.reclaimableBytes }
    }

    private fun queryFiles(minBytes: Long): List<DuplicateFile> {
        val collection = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL)
        val projection = arrayOf(
            MediaStore.Files.FileColumns._ID,
            MediaStore.Files.FileColumns.DISPLAY_NAME,
            MediaStore.Files.FileColumns.SIZE,
        )
        val selection = "${MediaStore.Files.FileColumns.SIZE} >= ?"
        val args = arrayOf(minBytes.toString())

        val files = mutableListOf<DuplicateFile>()
        context.contentResolver.query(collection, projection, selection, args, null)?.use { c ->
            val idCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns._ID)
            val nameCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.DISPLAY_NAME)
            val sizeCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns.SIZE)
            while (c.moveToNext()) {
                val id = c.getLong(idCol)
                files += DuplicateFile(
                    uri = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL, id),
                    displayName = c.getString(nameCol) ?: "",
                    sizeBytes = c.getLong(sizeCol),
                )
            }
        }
        return files
    }
}
