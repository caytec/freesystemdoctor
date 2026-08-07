package com.freeandroiddoctor.android.engine.files

import android.content.Context
import android.net.Uri
import androidx.documentfile.provider.DocumentFile
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class FolderEntry(
    val name: String,
    val uri: Uri,
    val isDirectory: Boolean,
    val sizeBytes: Long,
)

data class EmptyFolder(val name: String, val uri: Uri, val path: String)

/**
 * Browses and measures a user-granted SAF tree. Deletions here use
 * DocumentFile.delete() and do not require the MediaStore consent dialog,
 * because the user explicitly granted write access to this subtree.
 */
class SafTreeEngine(private val context: Context) {

    /** Immediate children of [tree], directories sized recursively, largest first. */
    suspend fun listChildren(tree: Uri): List<FolderEntry> = withContext(Dispatchers.IO) {
        val root = DocumentFile.fromTreeUri(context, tree) ?: return@withContext emptyList()
        root.listFiles().map { doc ->
            FolderEntry(
                name = doc.name ?: "?",
                uri = doc.uri,
                isDirectory = doc.isDirectory,
                sizeBytes = if (doc.isDirectory) sizeOf(doc) else doc.length(),
            )
        }.sortedByDescending { it.sizeBytes }
    }

    suspend fun totalSize(tree: Uri): Long = withContext(Dispatchers.IO) {
        DocumentFile.fromTreeUri(context, tree)?.let { sizeOf(it) } ?: 0L
    }

    /** Recursively finds folders that contain no files anywhere beneath them. */
    suspend fun findEmptyFolders(tree: Uri): List<EmptyFolder> = withContext(Dispatchers.IO) {
        val root = DocumentFile.fromTreeUri(context, tree) ?: return@withContext emptyList()
        val out = ArrayList<EmptyFolder>()
        collectEmpty(root, root.name ?: "", out)
        out
    }

    fun delete(uri: Uri): Boolean = runCatching {
        DocumentFile.fromSingleUri(context, uri)?.delete() ?: false
    }.getOrDefault(false)

    private fun sizeOf(doc: DocumentFile): Long {
        var total = 0L
        val stack = ArrayDeque<DocumentFile>()
        stack.addLast(doc)
        while (stack.isNotEmpty()) {
            val current = stack.removeLast()
            current.listFiles().forEach { child ->
                if (child.isDirectory) stack.addLast(child) else total += child.length()
            }
        }
        return total
    }

    /** @return true if [dir] is empty (so the caller can prune as well). */
    private fun collectEmpty(dir: DocumentFile, path: String, out: MutableList<EmptyFolder>): Boolean {
        val children = dir.listFiles()
        if (children.isEmpty()) {
            out += EmptyFolder(dir.name ?: "?", dir.uri, path)
            return true
        }
        var allEmpty = true
        children.forEach { child ->
            if (child.isDirectory) {
                val childPath = "$path/${child.name}"
                val childEmpty = collectEmpty(child, childPath, out)
                if (!childEmpty) allEmpty = false
            } else {
                allEmpty = false
            }
        }
        if (allEmpty) out += EmptyFolder(dir.name ?: "?", dir.uri, path)
        return allEmpty
    }
}
