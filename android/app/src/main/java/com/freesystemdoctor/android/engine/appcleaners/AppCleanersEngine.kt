package com.freesystemdoctor.android.engine.appcleaners

import android.content.Context
import android.net.Uri
import androidx.documentfile.provider.DocumentFile
import com.freesystemdoctor.android.core.result.CleanResult
import com.freesystemdoctor.android.engine.history.CleanSource
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class CleanerTarget(
    val key: String,
    val label: String,
    val relPath: String,
    val safety: com.freesystemdoctor.android.engine.appdeep.Safety,
)

data class TargetHit(
    val target: CleanerTarget,
    val folderUri: Uri,
    val sizeBytes: Long,
)

interface AppCleanerStrategy {
    val packageName: String
    val historySource: CleanSource
    val targets: List<CleanerTarget>
}

/**
 * Orchestrates the per-app cleaner sub-screens (WhatsApp/Telegram/Discord/TikTok).
 * Each strategy defines the package name plus fine-grained subfolder targets;
 * scan/clean logic is shared here so adding a 5th app is just one new strategy class.
 */
class AppCleanersEngine(private val context: Context) {

    suspend fun isInstalled(packageName: String): Boolean = withContext(Dispatchers.IO) {
        runCatching { context.packageManager.getPackageInfo(packageName, 0) }.isSuccess
    }

    suspend fun scan(strategy: AppCleanerStrategy, roots: List<Uri>): List<TargetHit> =
        withContext(Dispatchers.IO) {
            val out = ArrayList<TargetHit>()
            roots.forEach { root ->
                val doc = DocumentFile.fromTreeUri(context, root) ?: return@forEach
                strategy.targets.forEach { target ->
                    val folder = resolve(doc, target.relPath) ?: return@forEach
                    val size = sizeOf(folder)
                    if (size > 0) out += TargetHit(target, folder.uri, size)
                }
            }
            out.sortedByDescending { it.sizeBytes }
        }

    suspend fun clean(hits: List<TargetHit>): CleanResult = withContext(Dispatchers.IO) {
        var bytes = 0L
        var items = 0
        var failures = 0
        hits.forEach { hit ->
            val doc = DocumentFile.fromTreeUri(context, hit.folderUri) ?: return@forEach
            runCatching { doc.listFiles() }.getOrNull()?.forEach { child ->
                val size = if (child.isDirectory) sizeOf(child) else child.length()
                if (deleteRecursively(child)) {
                    bytes += size
                    items++
                } else failures++
            }
        }
        CleanResult(itemsRemoved = items, bytesFreed = bytes, failures = failures)
    }

    private fun resolve(root: DocumentFile, rel: String): DocumentFile? {
        var current: DocumentFile = root
        rel.split('/').forEach { seg ->
            if (seg.isBlank()) return@forEach
            current = current.findFile(seg) ?: return null
        }
        return current.takeIf { it.isDirectory }
    }

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

    private fun deleteRecursively(doc: DocumentFile): Boolean {
        if (doc.isDirectory) doc.listFiles().forEach { deleteRecursively(it) }
        return runCatching { doc.delete() }.getOrDefault(false)
    }
}
