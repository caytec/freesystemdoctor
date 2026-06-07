package com.freesystemdoctor.android.engine.appdeep

import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import androidx.documentfile.provider.DocumentFile
import com.freesystemdoctor.android.core.result.CleanResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class DeepHit(
    val rule: ExpendableRule,
    val folderUri: Uri,
    val sizeBytes: Long,
)

data class AppDeepReport(
    /** packageName → label → hits (kept ordered, largest first). */
    val perApp: Map<String, AppGroup>,
) {
    val totalBytes: Long get() = perApp.values.sumOf { it.totalBytes }
}

data class AppGroup(
    val packageName: String,
    val appLabel: String,
    val hits: List<DeepHit>,
) {
    val totalBytes: Long get() = hits.sumOf { it.sizeBytes }
}

/**
 * Walks granted SAF roots and reports expendable subfolders, grouped per installed app.
 * Uses the same SAF traversal pattern as [com.freesystemdoctor.android.engine.cache.HiddenCacheEngine]
 * but resolves paths from the curated [AppExpendablePathsDb] instead of 8 hardcoded presets.
 */
class AppDeepCleanEngine(private val context: Context) {

    suspend fun scan(roots: List<Uri>): AppDeepReport = withContext(Dispatchers.IO) {
        val pm = context.packageManager
        val installed = installedLabels(pm)
        val perApp = HashMap<String, AppGroup>()

        roots.forEach { root ->
            val rootDoc = DocumentFile.fromTreeUri(context, root) ?: return@forEach
            AppExpendablePathsDb.rules.forEach { rule ->
                // Skip rules for apps not installed (except generic "media.thumbs").
                if (rule.packageName != "media.thumbs" && rule.packageName !in installed) return@forEach
                val doc = resolve(rootDoc, rule.relPath) ?: return@forEach
                val size = sizeOf(doc)
                if (size <= 0) return@forEach
                val hit = DeepHit(rule, doc.uri, size)
                val existing = perApp[rule.packageName]
                val label = installed[rule.packageName] ?: rule.packageName
                perApp[rule.packageName] = if (existing == null) {
                    AppGroup(rule.packageName, label, listOf(hit))
                } else {
                    existing.copy(hits = existing.hits + hit)
                }
            }
        }

        AppDeepReport(
            perApp = perApp
                .mapValues { (_, g) -> g.copy(hits = g.hits.sortedByDescending { it.sizeBytes }) }
                .toList()
                .sortedByDescending { it.second.totalBytes }
                .toMap(),
        )
    }

    suspend fun clean(hits: List<DeepHit>): CleanResult = withContext(Dispatchers.IO) {
        var bytes = 0L
        var items = 0
        var failures = 0
        hits.forEach { hit ->
            val doc = DocumentFile.fromTreeUri(context, hit.folderUri) ?: return@forEach
            // Clear contents, keep the folder shell (apps may recreate it lazily).
            val children = runCatching { doc.listFiles() }.getOrNull() ?: emptyArray()
            children.forEach { child ->
                val size = if (child.isDirectory) sizeOf(child) else child.length()
                if (deleteRecursively(child)) {
                    bytes += size
                    items++
                } else failures++
            }
        }
        CleanResult(itemsRemoved = items, bytesFreed = bytes, failures = failures)
    }

    private fun installedLabels(pm: PackageManager): Map<String, String> =
        runCatching {
            pm.getInstalledApplications(0).associate { app ->
                app.packageName to (runCatching { pm.getApplicationLabel(app).toString() }
                    .getOrDefault(app.packageName))
            }
        }.getOrDefault(emptyMap())

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
