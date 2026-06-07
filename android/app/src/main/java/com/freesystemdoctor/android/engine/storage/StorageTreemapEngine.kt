package com.freesystemdoctor.android.engine.storage

import android.content.Context
import android.net.Uri
import androidx.documentfile.provider.DocumentFile
import com.freesystemdoctor.android.ui.storage.treemap.TreemapNode
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Walks a SAF tree and returns one [TreemapNode] level for the treemap UI. Sizes are
 * real (recursive measurement). Drilling into a child re-walks one level at a time so
 * the initial scan stays interactive on big trees.
 */
class StorageTreemapEngine(private val context: Context) {

    suspend fun scan(rootUri: Uri): TreemapNode = withContext(Dispatchers.IO) {
        val root = DocumentFile.fromTreeUri(context, rootUri)
            ?: return@withContext TreemapNode(rootUri.lastPathSegment ?: "?", 0L)
        buildLevel(root, depth = 1)
    }

    /** Re-walk [node]'s real folder one level deeper. */
    suspend fun expand(rootUri: Uri, node: TreemapNode): TreemapNode = withContext(Dispatchers.IO) {
        val root = DocumentFile.fromTreeUri(context, rootUri) ?: return@withContext node
        val target = findByName(root, node.label) ?: return@withContext node
        buildLevel(target, depth = 1)
    }

    private fun buildLevel(folder: DocumentFile, depth: Int): TreemapNode {
        val name = folder.name ?: "?"
        val children = runCatching { folder.listFiles() }.getOrNull() ?: emptyArray()
        val mapped = children.map { child ->
            val size = if (child.isDirectory) sizeOf(child) else child.length()
            TreemapNode(
                label = child.name ?: "?",
                sizeBytes = size,
                children = if (child.isDirectory && depth > 0) {
                    // Defer recursion: child has children only when user drills in.
                    listOf(TreemapNode("…", 0L))
                } else emptyList(),
            )
        }.filter { it.sizeBytes > 0 }
            .sortedByDescending { it.sizeBytes }
        return TreemapNode(
            label = name,
            sizeBytes = mapped.sumOf { it.sizeBytes },
            children = mapped,
        )
    }

    private fun findByName(root: DocumentFile, name: String): DocumentFile? =
        runCatching { root.listFiles().firstOrNull { it.name == name && it.isDirectory } }.getOrNull()

    private fun sizeOf(doc: DocumentFile): Long {
        var total = 0L
        val stack = ArrayDeque<DocumentFile>()
        stack.addLast(doc)
        while (stack.isNotEmpty()) {
            val cur = stack.removeLast()
            runCatching { cur.listFiles() }.getOrNull()?.forEach { child ->
                if (child.isDirectory) stack.addLast(child) else total += child.length()
            }
        }
        return total
    }
}
