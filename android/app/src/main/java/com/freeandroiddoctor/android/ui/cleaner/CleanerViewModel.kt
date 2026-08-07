package com.freeandroiddoctor.android.ui.cleaner

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.data.settings.ScanDepth
import com.freeandroiddoctor.android.engine.cache.JunkItem
import com.freeandroiddoctor.android.engine.cache.JunkReport
import com.freeandroiddoctor.android.engine.history.CleanSource
import com.freeandroiddoctor.android.ui.navigation.ToolRoutes
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull

enum class CleanPhaseId {
    CACHE_SCAN, CACHE_CLEAN, APK_SCAN, TEMP_SCAN,
    TRASH_SCAN, CLIPBOARD_SCAN, LARGE_FILES_SCAN,
    EMPTY_FOLDER_SCAN, LOG_FILES_SCAN,
    HIDDEN_CACHE_SCAN, CORPSE_SCAN, APP_DEEP_SCAN, DUPLICATE_SCAN,
    BLURRY_PHOTOS_SCAN, SIMILAR_PHOTOS_SCAN,
    SUMMARY,
}

enum class PhaseStatus { PENDING, RUNNING, DONE }

enum class SkipReason { NO_SAF, NOT_SUPPORTED, CANCELLED }

data class CleanPhase(
    val id: CleanPhaseId,
    val status: PhaseStatus,
    val bytes: Long = 0L,
    val count: Int = 0,
    val skipReason: SkipReason? = null,
)

data class BreakdownEntry(
    val id: CleanPhaseId,
    val bytes: Long,
    val count: Int,
    val deepLinkRoute: String? = null,
    /** True only for the cache phase where bytes were actually deleted by us. */
    val confirmedDeleted: Boolean = false,
    val skipReason: SkipReason? = null,
)

/**
 * Snapshot of a completed clean. The list-of-rows model lets the report card scale to any
 * number of phases. [cacheBytesFreed] / [cacheFilesRemoved] are kept as separate fields to
 * power the hero number — only those were actually deleted by us.
 */
data class CleaningReport(
    val depth: ScanDepth,
    val rows: List<BreakdownEntry>,
    val cacheBytesFreed: Long,
    val cacheFilesRemoved: Int,
    val cancelled: Boolean = false,
) {
    val totalReclaimableBytes: Long
        get() = rows.sumOf { it.bytes }
    val remainingReviewBytes: Long
        get() = rows.filterNot { it.confirmedDeleted }.sumOf { it.bytes }
}

data class CleanerUiState(
    val scanning: Boolean = false,
    val report: JunkReport? = null,
    val lastFreedBytes: Long = 0,
    val phases: List<CleanPhase> = emptyList(),
    val cleanReport: CleaningReport? = null,
    val depth: ScanDepth = ScanDepth.QUICK,
    val includePhotos: Boolean = false,
)

class CleanerViewModel : ViewModel() {

    private val engine = ServiceLocator.junkEngine
    private val trashEngine = ServiceLocator.trashEngine
    private val clipboardEngine = ServiceLocator.clipboardEngine
    private val largeFilesEngine = ServiceLocator.largeFilesEngine
    private val safTreeEngine = ServiceLocator.safTreeEngine
    private val logFilesEngine = ServiceLocator.logFilesEngine
    private val hiddenCacheEngine = ServiceLocator.hiddenCacheEngine
    private val corpseFinderEngine = ServiceLocator.corpseFinderEngine
    private val appDeepCleanEngine = ServiceLocator.appDeepCleanEngine
    private val duplicateEngine = ServiceLocator.duplicateEngine
    private val blurEngine = ServiceLocator.blurScreenshotEngine
    private val similarEngine = ServiceLocator.similarPhotoEngine
    private val safTreeStore = ServiceLocator.safTreeStore
    private val settings = ServiceLocator.settingsRepository
    private val shizuku = ServiceLocator.shizukuManager

    private val _state = MutableStateFlow(CleanerUiState())
    val state: StateFlow<CleanerUiState> = _state.asStateFlow()

    private var scanJob: Job? = null

    init {
        viewModelScope.launch {
            settings.settings
                .map { it.scanDepth to it.includePhotosInDeepScan }
                .collect { (depth, includePhotos) ->
                    _state.update { it.copy(depth = depth, includePhotos = includePhotos) }
                }
        }
    }

    fun setDepth(depth: ScanDepth) {
        viewModelScope.launch { settings.setScanDepth(depth) }
    }

    fun setIncludePhotos(enabled: Boolean) {
        viewModelScope.launch { settings.setIncludePhotosInDeepScan(enabled) }
    }

    fun scan() {
        if (_state.value.scanning) return
        val depth = _state.value.depth
        val includePhotos = depth == ScanDepth.DEEP && _state.value.includePhotos
        val phaseIds = phaseListForScan(depth, includePhotos)
        startScan(phaseIds) {
            runDiscoveryPhases(depth, includePhotos, phaseIds)
        }
    }

    /** Cache delete + the full discovery flow afterwards. */
    fun cleanAppCache() {
        if (_state.value.scanning) return
        val depth = _state.value.depth
        val includePhotos = depth == ScanDepth.DEEP && _state.value.includePhotos
        val phaseIds = phaseListForCleanCache(depth, includePhotos)
        startScan(phaseIds) {
            runCleanCacheFlow(depth, includePhotos, phaseIds)
        }
    }

    fun cancelScan() {
        scanJob?.cancel()
    }

    fun mediaUris(): List<android.net.Uri> =
        _state.value.report?.mediaItems?.map(JunkItem::uri).orEmpty()

    fun buildDeleteRequest() = engine.buildDeleteRequest(mediaUris())

    fun onMediaDeleted() {
        _state.update { it.copy(cleanReport = null) }
        scan()
    }

    fun dismissReport() {
        _state.update { it.copy(cleanReport = null) }
    }

    // -------- Orchestration --------

    private fun startScan(phaseIds: List<CleanPhaseId>, block: suspend () -> Unit) {
        val initial = phaseIds.map { CleanPhase(it, PhaseStatus.PENDING) }
        _state.update { it.copy(scanning = true, phases = initial, report = null, cleanReport = null) }
        scanJob = viewModelScope.launch {
            try {
                block()
            } catch (_: CancellationException) {
                // Surface a cancelled report so the user sees partial results.
                val current = _state.value.phases
                val rows = current.filter { it.status == PhaseStatus.DONE }.map { it.toBreakdown() }
                _state.update {
                    it.copy(
                        scanning = false,
                        cleanReport = CleaningReport(
                            depth = _state.value.depth,
                            rows = rows,
                            cacheBytesFreed = it.lastFreedBytes,
                            cacheFilesRemoved = rows.firstOrNull { r -> r.id == CleanPhaseId.CACHE_CLEAN }?.count
                                ?: 0,
                            cancelled = true,
                        ),
                    )
                }
                throw CancellationException()
            }
        }
    }

    private suspend fun runDiscoveryPhases(
        depth: ScanDepth,
        includePhotos: Boolean,
        phaseIds: List<CleanPhaseId>,
    ) {
        val results = mutableMapOf<CleanPhaseId, PhaseOutcome>()

        // Quick / Deep both run these three.
        results[CleanPhaseId.CACHE_SCAN] = runPhase(CleanPhaseId.CACHE_SCAN, 4_000L) {
            PhaseOutcome.Done(engine.measureAppCache())
        }
        results[CleanPhaseId.APK_SCAN] = runPhase(CleanPhaseId.APK_SCAN, 4_000L) {
            val apks = engine.findApkLeftovers()
            PhaseOutcome.Done(apks.sumOf { it.sizeBytes }, apks.size, extra = apks)
        }
        results[CleanPhaseId.TEMP_SCAN] = runPhase(CleanPhaseId.TEMP_SCAN, 4_000L) {
            val temps = engine.findTempFiles()
            PhaseOutcome.Done(temps.sumOf { it.sizeBytes }, temps.size, extra = temps)
        }

        if (depth == ScanDepth.DEEP) {
            results[CleanPhaseId.TRASH_SCAN] = runPhase(CleanPhaseId.TRASH_SCAN, 3_000L) {
                val items = trashEngine.listTrashed()
                PhaseOutcome.Done(items.sumOf { it.sizeBytes }, items.size)
            }
            results[CleanPhaseId.CLIPBOARD_SCAN] = runPhase(CleanPhaseId.CLIPBOARD_SCAN, 1_500L) {
                if (clipboardEngine.hasContent()) PhaseOutcome.Done(0L, 1) else PhaseOutcome.Done(0L, 0)
            }
            results[CleanPhaseId.LARGE_FILES_SCAN] = runPhase(CleanPhaseId.LARGE_FILES_SCAN, 5_000L) {
                val files = largeFilesEngine.findLargeFiles(50L * 1024 * 1024, 200)
                PhaseOutcome.Done(files.sumOf { it.sizeBytes }, files.size)
            }
            results[CleanPhaseId.EMPTY_FOLDER_SCAN] =
                runPhase(CleanPhaseId.EMPTY_FOLDER_SCAN, 6_000L) {
                    val tree = safTreeStore.current()
                    if (tree == null) PhaseOutcome.Skipped(SkipReason.NO_SAF)
                    else {
                        val folders = safTreeEngine.findEmptyFolders(tree)
                        PhaseOutcome.Done(0L, folders.size)
                    }
                }
            results[CleanPhaseId.LOG_FILES_SCAN] = runPhase(CleanPhaseId.LOG_FILES_SCAN, 4_000L) {
                val report = logFilesEngine.scan(shizukuAvailable = shizuku.status() == com.freeandroiddoctor.android.core.shizuku.ShizukuManager.Status.Granted)
                PhaseOutcome.Done(report.totalBytes, report.files.size)
            }
            results[CleanPhaseId.HIDDEN_CACHE_SCAN] =
                runPhase(CleanPhaseId.HIDDEN_CACHE_SCAN, 8_000L) {
                    val media = safTreeStore.androidMediaTreeUri.first()
                    if (media == null) PhaseOutcome.Skipped(SkipReason.NO_SAF)
                    else {
                        val hits = hiddenCacheEngine.scan(media)
                        PhaseOutcome.Done(hits.sumOf { it.sizeBytes }, hits.size)
                    }
                }
            results[CleanPhaseId.CORPSE_SCAN] = runPhase(CleanPhaseId.CORPSE_SCAN, 12_000L) {
                val roots = listOfNotNull(safTreeStore.current())
                if (roots.isEmpty()) PhaseOutcome.Skipped(SkipReason.NO_SAF)
                else {
                    val report = corpseFinderEngine.scan(roots)
                    PhaseOutcome.Done(report.totalBytes, report.entries.size)
                }
            }
            results[CleanPhaseId.APP_DEEP_SCAN] = runPhase(CleanPhaseId.APP_DEEP_SCAN, 12_000L) {
                val roots = listOfNotNull(safTreeStore.current())
                if (roots.isEmpty()) PhaseOutcome.Skipped(SkipReason.NO_SAF)
                else {
                    val report = appDeepCleanEngine.scan(roots)
                    PhaseOutcome.Done(
                        report.totalBytes,
                        report.perApp.values.sumOf { it.hits.size },
                    )
                }
            }
            results[CleanPhaseId.DUPLICATE_SCAN] = runPhase(CleanPhaseId.DUPLICATE_SCAN, 30_000L) {
                val groups = duplicateEngine.findDuplicates(minBytes = 10L * 1024 * 1024)
                PhaseOutcome.Done(groups.sumOf { it.reclaimableBytes }, groups.size)
            }

            if (includePhotos) {
                results[CleanPhaseId.BLURRY_PHOTOS_SCAN] =
                    runPhase(CleanPhaseId.BLURRY_PHOTOS_SCAN, 60_000L) {
                        val review = blurEngine.review()
                        val items = review.blurry + review.screenshots
                        PhaseOutcome.Done(items.sumOf { it.sizeBytes }, items.size)
                    }
                results[CleanPhaseId.SIMILAR_PHOTOS_SCAN] =
                    runPhase(CleanPhaseId.SIMILAR_PHOTOS_SCAN, 60_000L) {
                        val groups = similarEngine.findSimilar()
                        PhaseOutcome.Done(groups.sumOf { it.reclaimableBytes }, groups.size)
                    }
            }
        }

        // SUMMARY
        markRunning(CleanPhaseId.SUMMARY)
        val totalBytes = results.values.filterIsInstance<PhaseOutcome.Done>().sumOf { it.bytes }
        val totalCount = results.values.filterIsInstance<PhaseOutcome.Done>().sumOf { it.count }
        phaseBreath()
        markDone(CleanPhaseId.SUMMARY, totalBytes, totalCount)

        finalizeReport(
            depth = depth,
            results = results,
            cacheBytesFreed = 0L,
            cacheFilesRemoved = 0,
            cancelled = false,
            mediaItems = collectMediaItems(results),
        )
    }

    private suspend fun runCleanCacheFlow(
        depth: ScanDepth,
        includePhotos: Boolean,
        phaseIds: List<CleanPhaseId>,
    ) {
        val results = mutableMapOf<CleanPhaseId, PhaseOutcome>()

        results[CleanPhaseId.CACHE_SCAN] = runPhase(CleanPhaseId.CACHE_SCAN, 4_000L) {
            PhaseOutcome.Done(engine.measureAppCache())
        }
        // CACHE_CLEAN — actually delete.
        results[CleanPhaseId.CACHE_CLEAN] = runPhase(CleanPhaseId.CACHE_CLEAN, 8_000L) {
            val result = engine.cleanAppCache()
            PhaseOutcome.Done(result.bytesFreed, result.itemsRemoved)
        }
        val cleanResultBytes = (results[CleanPhaseId.CACHE_CLEAN] as? PhaseOutcome.Done)?.bytes ?: 0L
        val cleanResultCount = (results[CleanPhaseId.CACHE_CLEAN] as? PhaseOutcome.Done)?.count ?: 0
        // Now also do the discovery phases.
        results[CleanPhaseId.APK_SCAN] = runPhase(CleanPhaseId.APK_SCAN, 4_000L) {
            val apks = engine.findApkLeftovers()
            PhaseOutcome.Done(apks.sumOf { it.sizeBytes }, apks.size, extra = apks)
        }
        results[CleanPhaseId.TEMP_SCAN] = runPhase(CleanPhaseId.TEMP_SCAN, 4_000L) {
            val temps = engine.findTempFiles()
            PhaseOutcome.Done(temps.sumOf { it.sizeBytes }, temps.size, extra = temps)
        }

        if (depth == ScanDepth.DEEP) {
            results[CleanPhaseId.TRASH_SCAN] = runPhase(CleanPhaseId.TRASH_SCAN, 3_000L) {
                val items = trashEngine.listTrashed()
                PhaseOutcome.Done(items.sumOf { it.sizeBytes }, items.size)
            }
            results[CleanPhaseId.CLIPBOARD_SCAN] = runPhase(CleanPhaseId.CLIPBOARD_SCAN, 1_500L) {
                if (clipboardEngine.hasContent()) PhaseOutcome.Done(0L, 1) else PhaseOutcome.Done(0L, 0)
            }
            results[CleanPhaseId.LARGE_FILES_SCAN] =
                runPhase(CleanPhaseId.LARGE_FILES_SCAN, 5_000L) {
                    val files = largeFilesEngine.findLargeFiles(50L * 1024 * 1024, 200)
                    PhaseOutcome.Done(files.sumOf { it.sizeBytes }, files.size)
                }
            results[CleanPhaseId.EMPTY_FOLDER_SCAN] =
                runPhase(CleanPhaseId.EMPTY_FOLDER_SCAN, 6_000L) {
                    val tree = safTreeStore.current()
                    if (tree == null) PhaseOutcome.Skipped(SkipReason.NO_SAF)
                    else PhaseOutcome.Done(0L, safTreeEngine.findEmptyFolders(tree).size)
                }
            results[CleanPhaseId.LOG_FILES_SCAN] = runPhase(CleanPhaseId.LOG_FILES_SCAN, 4_000L) {
                val report = logFilesEngine.scan(shizukuAvailable = shizuku.status() == com.freeandroiddoctor.android.core.shizuku.ShizukuManager.Status.Granted)
                PhaseOutcome.Done(report.totalBytes, report.files.size)
            }
            results[CleanPhaseId.HIDDEN_CACHE_SCAN] =
                runPhase(CleanPhaseId.HIDDEN_CACHE_SCAN, 8_000L) {
                    val media = safTreeStore.androidMediaTreeUri.first()
                    if (media == null) PhaseOutcome.Skipped(SkipReason.NO_SAF)
                    else {
                        val hits = hiddenCacheEngine.scan(media)
                        PhaseOutcome.Done(hits.sumOf { it.sizeBytes }, hits.size)
                    }
                }
            results[CleanPhaseId.CORPSE_SCAN] = runPhase(CleanPhaseId.CORPSE_SCAN, 12_000L) {
                val roots = listOfNotNull(safTreeStore.current())
                if (roots.isEmpty()) PhaseOutcome.Skipped(SkipReason.NO_SAF)
                else {
                    val report = corpseFinderEngine.scan(roots)
                    PhaseOutcome.Done(report.totalBytes, report.entries.size)
                }
            }
            results[CleanPhaseId.APP_DEEP_SCAN] = runPhase(CleanPhaseId.APP_DEEP_SCAN, 12_000L) {
                val roots = listOfNotNull(safTreeStore.current())
                if (roots.isEmpty()) PhaseOutcome.Skipped(SkipReason.NO_SAF)
                else {
                    val report = appDeepCleanEngine.scan(roots)
                    PhaseOutcome.Done(
                        report.totalBytes,
                        report.perApp.values.sumOf { it.hits.size },
                    )
                }
            }
            results[CleanPhaseId.DUPLICATE_SCAN] =
                runPhase(CleanPhaseId.DUPLICATE_SCAN, 30_000L) {
                    val groups = duplicateEngine.findDuplicates(minBytes = 10L * 1024 * 1024)
                    PhaseOutcome.Done(groups.sumOf { it.reclaimableBytes }, groups.size)
                }
            if (includePhotos) {
                results[CleanPhaseId.BLURRY_PHOTOS_SCAN] =
                    runPhase(CleanPhaseId.BLURRY_PHOTOS_SCAN, 60_000L) {
                        val review = blurEngine.review()
                        val items = review.blurry + review.screenshots
                        PhaseOutcome.Done(items.sumOf { it.sizeBytes }, items.size)
                    }
                results[CleanPhaseId.SIMILAR_PHOTOS_SCAN] =
                    runPhase(CleanPhaseId.SIMILAR_PHOTOS_SCAN, 60_000L) {
                        val groups = similarEngine.findSimilar()
                        PhaseOutcome.Done(groups.sumOf { it.reclaimableBytes }, groups.size)
                    }
            }
        }

        markRunning(CleanPhaseId.SUMMARY)
        val totalBytes = results.values.filterIsInstance<PhaseOutcome.Done>().sumOf { it.bytes }
        val totalCount = results.values.filterIsInstance<PhaseOutcome.Done>().sumOf { it.count }
        phaseBreath()
        markDone(CleanPhaseId.SUMMARY, totalBytes, totalCount)

        ServiceLocator.cleaningHistoryEngine.recordClean(
            CleanSource.JUNK_CACHE,
            cleanResultBytes,
            cleanResultCount,
        )
        finalizeReport(
            depth = depth,
            results = results,
            cacheBytesFreed = cleanResultBytes,
            cacheFilesRemoved = cleanResultCount,
            cancelled = false,
            mediaItems = collectMediaItems(results),
        )
    }

    private fun finalizeReport(
        depth: ScanDepth,
        results: Map<CleanPhaseId, PhaseOutcome>,
        cacheBytesFreed: Long,
        cacheFilesRemoved: Int,
        cancelled: Boolean,
        mediaItems: List<JunkItem>,
    ) {
        val rows = results.entries.mapNotNull { (id, outcome) ->
            if (id == CleanPhaseId.SUMMARY) return@mapNotNull null
            when (outcome) {
                is PhaseOutcome.Done -> {
                    if (outcome.bytes <= 0L && outcome.count <= 0) return@mapNotNull null
                    BreakdownEntry(
                        id = id,
                        bytes = outcome.bytes,
                        count = outcome.count,
                        deepLinkRoute = deepLinkRouteFor(id),
                        confirmedDeleted = (id == CleanPhaseId.CACHE_CLEAN),
                    )
                }
                is PhaseOutcome.Skipped -> BreakdownEntry(
                    id = id,
                    bytes = 0L,
                    count = 0,
                    deepLinkRoute = deepLinkRouteFor(id),
                    skipReason = outcome.reason,
                )
            }
        }.sortedWith(compareByDescending<BreakdownEntry> { it.confirmedDeleted }.thenByDescending { it.bytes })

        _state.update {
            it.copy(
                scanning = false,
                lastFreedBytes = if (cacheBytesFreed > 0) cacheBytesFreed else it.lastFreedBytes,
                report = JunkReport(
                    appCacheBytes = (results[CleanPhaseId.CACHE_SCAN] as? PhaseOutcome.Done)?.bytes
                        ?: 0L,
                    mediaItems = mediaItems,
                ),
                cleanReport = CleaningReport(
                    depth = depth,
                    rows = rows,
                    cacheBytesFreed = cacheBytesFreed,
                    cacheFilesRemoved = cacheFilesRemoved,
                    cancelled = cancelled,
                ),
            )
        }
    }

    @Suppress("UNCHECKED_CAST")
    private fun collectMediaItems(results: Map<CleanPhaseId, PhaseOutcome>): List<JunkItem> {
        val apks = (results[CleanPhaseId.APK_SCAN] as? PhaseOutcome.Done)
            ?.extra as? List<JunkItem> ?: emptyList()
        val temps = (results[CleanPhaseId.TEMP_SCAN] as? PhaseOutcome.Done)
            ?.extra as? List<JunkItem> ?: emptyList()
        return (apks + temps).sortedByDescending { it.sizeBytes }
    }

    private suspend fun runPhase(
        id: CleanPhaseId,
        budgetMs: Long,
        block: suspend () -> PhaseOutcome,
    ): PhaseOutcome {
        markRunning(id)
        val outcome = withTimeoutOrNull(budgetMs) {
            runCatching { block() }.getOrElse { PhaseOutcome.Skipped(SkipReason.NOT_SUPPORTED) }
        } ?: PhaseOutcome.Skipped(SkipReason.NOT_SUPPORTED)
        phaseBreath()
        when (outcome) {
            is PhaseOutcome.Done -> markDone(id, outcome.bytes, outcome.count)
            is PhaseOutcome.Skipped -> markSkipped(id, outcome.reason)
        }
        return outcome
    }

    // -------- Phase ID lists --------

    private fun phaseListForScan(depth: ScanDepth, includePhotos: Boolean): List<CleanPhaseId> {
        val base = mutableListOf(
            CleanPhaseId.CACHE_SCAN,
            CleanPhaseId.APK_SCAN,
            CleanPhaseId.TEMP_SCAN,
        )
        if (depth == ScanDepth.DEEP) {
            base += listOf(
                CleanPhaseId.TRASH_SCAN,
                CleanPhaseId.CLIPBOARD_SCAN,
                CleanPhaseId.LARGE_FILES_SCAN,
                CleanPhaseId.EMPTY_FOLDER_SCAN,
                CleanPhaseId.LOG_FILES_SCAN,
                CleanPhaseId.HIDDEN_CACHE_SCAN,
                CleanPhaseId.CORPSE_SCAN,
                CleanPhaseId.APP_DEEP_SCAN,
                CleanPhaseId.DUPLICATE_SCAN,
            )
            if (includePhotos) {
                base += listOf(
                    CleanPhaseId.BLURRY_PHOTOS_SCAN,
                    CleanPhaseId.SIMILAR_PHOTOS_SCAN,
                )
            }
        }
        base += CleanPhaseId.SUMMARY
        return base
    }

    private fun phaseListForCleanCache(
        depth: ScanDepth,
        includePhotos: Boolean,
    ): List<CleanPhaseId> {
        val base = mutableListOf(
            CleanPhaseId.CACHE_SCAN,
            CleanPhaseId.CACHE_CLEAN,
            CleanPhaseId.APK_SCAN,
            CleanPhaseId.TEMP_SCAN,
        )
        if (depth == ScanDepth.DEEP) {
            base += listOf(
                CleanPhaseId.TRASH_SCAN,
                CleanPhaseId.CLIPBOARD_SCAN,
                CleanPhaseId.LARGE_FILES_SCAN,
                CleanPhaseId.EMPTY_FOLDER_SCAN,
                CleanPhaseId.LOG_FILES_SCAN,
                CleanPhaseId.HIDDEN_CACHE_SCAN,
                CleanPhaseId.CORPSE_SCAN,
                CleanPhaseId.APP_DEEP_SCAN,
                CleanPhaseId.DUPLICATE_SCAN,
            )
            if (includePhotos) {
                base += listOf(
                    CleanPhaseId.BLURRY_PHOTOS_SCAN,
                    CleanPhaseId.SIMILAR_PHOTOS_SCAN,
                )
            }
        }
        base += CleanPhaseId.SUMMARY
        return base
    }

    // -------- Phase state mutation helpers --------

    private fun markRunning(id: CleanPhaseId) = updatePhase(id) {
        it.copy(status = PhaseStatus.RUNNING)
    }

    private fun markDone(id: CleanPhaseId, bytes: Long, count: Int) = updatePhase(id) {
        it.copy(status = PhaseStatus.DONE, bytes = bytes, count = count)
    }

    private fun markSkipped(id: CleanPhaseId, reason: SkipReason) = updatePhase(id) {
        it.copy(status = PhaseStatus.DONE, skipReason = reason)
    }

    private fun updatePhase(id: CleanPhaseId, transform: (CleanPhase) -> CleanPhase) {
        _state.update { s ->
            s.copy(phases = s.phases.map { if (it.id == id) transform(it) else it })
        }
    }

    private suspend fun phaseBreath() = delay(PHASE_DELAY_MS)

    private fun deepLinkRouteFor(id: CleanPhaseId): String? = when (id) {
        CleanPhaseId.TRASH_SCAN -> ToolRoutes.RECYCLE_BIN
        CleanPhaseId.LARGE_FILES_SCAN -> ToolRoutes.LARGE_FILES
        CleanPhaseId.HIDDEN_CACHE_SCAN -> ToolRoutes.HIDDEN_CACHE
        CleanPhaseId.CORPSE_SCAN -> ToolRoutes.CORPSE_FINDER
        CleanPhaseId.APP_DEEP_SCAN -> ToolRoutes.APP_DEEP_CLEAN
        CleanPhaseId.DUPLICATE_SCAN -> ToolRoutes.DUPLICATES
        CleanPhaseId.BLURRY_PHOTOS_SCAN, CleanPhaseId.SIMILAR_PHOTOS_SCAN -> ToolRoutes.PHOTO_REVIEW
        else -> null
    }

    private fun CleanPhase.toBreakdown(): BreakdownEntry = BreakdownEntry(
        id = id,
        bytes = bytes,
        count = count,
        deepLinkRoute = deepLinkRouteFor(id),
        confirmedDeleted = (id == CleanPhaseId.CACHE_CLEAN),
        skipReason = skipReason,
    )

    private sealed class PhaseOutcome {
        data class Done(val bytes: Long, val count: Int = 0, val extra: Any? = null) : PhaseOutcome()
        data class Skipped(val reason: SkipReason) : PhaseOutcome()
    }

    private companion object {
        const val PHASE_DELAY_MS = 220L
    }
}
