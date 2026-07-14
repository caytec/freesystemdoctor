package com.freeandroiddoctor.android.engine.corpse

import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import androidx.documentfile.provider.DocumentFile
import com.freeandroiddoctor.android.core.result.CleanResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.io.File

enum class CorpseRisk { HIGH, MEDIUM, LOW }

data class CorpseEntry(
    val displayName: String,
    val packageName: String,
    val folderUri: Uri,
    val sizeBytes: Long,
    val risk: CorpseRisk,
    /** True for paths the user-granted SAF tree could read; false means inferred only. */
    val deletable: Boolean,
)

data class CorpseReport(
    val entries: List<CorpseEntry>,
    /** True when one or more Android/data subfolders were blocked by SAF on Android 13+. */
    val androidDataBlocked: Boolean,
) {
    val totalBytes: Long get() = entries.sumOf { it.sizeBytes }
}

@Serializable
private data class UninstallLog(val packages: List<String> = emptyList())

/**
 * Finds folders left behind by uninstalled apps. Walks SAF-granted roots for:
 * 1. `Android/data/<pkg>` and `Android/media/<pkg>` — package-named folders.
 * 2. Top-of-root friendly-name folders mapped to a known package via [PackageFolderMap].
 *
 * Risk:
 *  - HIGH: pkg-named subfolder AND the package was just uninstalled (uninstall log).
 *  - MEDIUM: pkg-named subfolder, no uninstall log entry.
 *  - LOW: friendly-name match only.
 *
 * Persists a small JSON log of recently uninstalled packages under
 * `filesDir/corpse/uninstall_log.json`, written by [UninstallWatcherReceiver].
 */
class CorpseFinderEngine(private val context: Context) {

    private val dir = File(context.filesDir, "corpse").apply { mkdirs() }
    private val logFile = File(dir, "uninstall_log.json")
    private val json = Json { ignoreUnknownKeys = true }
    private val mutex = Mutex()

    suspend fun appendUninstalled(pkg: String) = withContext(Dispatchers.IO) {
        if (pkg.isBlank()) return@withContext
        mutex.withLock {
            val current = readLog().packages.toMutableSet()
            current += pkg
            // Keep the last 200 uninstalls to bound size.
            val trimmed = current.toList().takeLast(MAX_LOG)
            writeLog(UninstallLog(trimmed))
        }
    }

    suspend fun recentlyUninstalled(): Set<String> = withContext(Dispatchers.IO) {
        mutex.withLock { readLog().packages.toSet() }
    }

    suspend fun scan(roots: List<Uri>): CorpseReport = withContext(Dispatchers.IO) {
        val pm = context.packageManager
        val installed = installedPackages(pm)
        val recent = recentlyUninstalled()
        val out = ArrayList<CorpseEntry>()
        var blocked = false

        roots.forEach { root ->
            val rootDoc = DocumentFile.fromTreeUri(context, root) ?: return@forEach
            // Two passes: friendly-name children at root, and pkg-named children under Android/{data,media}.
            rootDoc.listFiles().forEach { child ->
                if (!child.isDirectory) return@forEach
                val name = child.name ?: return@forEach
                // 1. Friendly-name lookup (e.g. "WhatsApp" → com.whatsapp).
                PackageFolderMap.lookup(name)?.let { mapped ->
                    if (mapped.packageName !in installed) {
                        out += CorpseEntry(
                            displayName = name,
                            packageName = mapped.packageName,
                            folderUri = child.uri,
                            sizeBytes = sizeOf(child),
                            risk = if (mapped.packageName in recent) CorpseRisk.HIGH else CorpseRisk.LOW,
                            deletable = child.canWrite(),
                        )
                    }
                }
            }

            // 2. Drill into Android/data and Android/media for pkg-named children.
            listOf("Android/data", "Android/media").forEach { rel ->
                val sub = resolvePath(rootDoc, rel)
                if (sub == null) {
                    // Android/data is often unreadable on 13+; flag it.
                    if (rel == "Android/data") blocked = true
                    return@forEach
                }
                val children = runCatching { sub.listFiles() }.getOrNull()
                if (children == null) {
                    if (rel == "Android/data") blocked = true
                    return@forEach
                }
                children.forEach { child ->
                    if (!child.isDirectory) return@forEach
                    val pkg = child.name ?: return@forEach
                    if (!looksLikePackageName(pkg)) return@forEach
                    if (pkg in installed) return@forEach
                    out += CorpseEntry(
                        displayName = pkg,
                        packageName = pkg,
                        folderUri = child.uri,
                        sizeBytes = sizeOf(child),
                        risk = if (pkg in recent) CorpseRisk.HIGH else CorpseRisk.MEDIUM,
                        deletable = child.canWrite(),
                    )
                }
            }
        }

        CorpseReport(
            entries = out.sortedByDescending { it.sizeBytes },
            androidDataBlocked = blocked,
        )
    }

    /** Estimate of leftover bytes for [pkg] across granted SAF roots — used by Pre-Uninstall preview. */
    suspend fun estimateForPackage(pkg: String, roots: List<Uri>): Long = withContext(Dispatchers.IO) {
        var total = 0L
        roots.forEach { root ->
            val rootDoc = DocumentFile.fromTreeUri(context, root) ?: return@forEach
            listOf("Android/data", "Android/media").forEach { rel ->
                resolvePath(rootDoc, rel)?.listFiles()?.forEach { child ->
                    if (child.isDirectory && child.name == pkg) total += sizeOf(child)
                }
            }
            // Friendly-name reverse lookup.
            PackageFolderMap.entries
                .filter { it.packageName == pkg }
                .forEach { entry ->
                    rootDoc.findFile(entry.folderName)?.takeIf { it.isDirectory }?.let {
                        total += sizeOf(it)
                    }
                }
        }
        total
    }

    suspend fun delete(entries: List<CorpseEntry>): CleanResult = withContext(Dispatchers.IO) {
        var bytes = 0L
        var items = 0
        var failures = 0
        entries.forEach { entry ->
            val doc = DocumentFile.fromTreeUri(context, entry.folderUri)
                ?: DocumentFile.fromSingleUri(context, entry.folderUri)
            if (doc == null || !deleteRecursively(doc)) {
                failures++
            } else {
                bytes += entry.sizeBytes
                items++
            }
        }
        CleanResult(itemsRemoved = items, bytesFreed = bytes, failures = failures)
    }

    private fun installedPackages(pm: PackageManager): Set<String> =
        runCatching {
            pm.getInstalledPackages(0).map { it.packageName }.toSet()
        }.getOrDefault(emptySet())

    private fun looksLikePackageName(name: String): Boolean {
        if (name.length < 3 || !name.contains('.')) return false
        return name.all { it.isLetterOrDigit() || it == '.' || it == '_' }
    }

    private fun resolvePath(root: DocumentFile, rel: String): DocumentFile? {
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

    private fun readLog(): UninstallLog =
        if (!logFile.exists()) UninstallLog()
        else runCatching { json.decodeFromString<UninstallLog>(logFile.readText()) }
            .getOrElse { UninstallLog() }

    private fun writeLog(log: UninstallLog) {
        runCatching { logFile.writeText(json.encodeToString(UninstallLog.serializer(), log)) }
    }

    private companion object { const val MAX_LOG = 200 }
}
