package com.freesystemdoctor.android.ui.cleaner

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.cache.JunkItem
import com.freesystemdoctor.android.engine.cache.JunkReport
import com.freesystemdoctor.android.engine.history.CleanSource
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

enum class CleanPhaseId { CACHE_SCAN, CACHE_CLEAN, APK_SCAN, TEMP_SCAN, SUMMARY }
enum class PhaseStatus { PENDING, RUNNING, DONE }

data class CleanPhase(
    val id: CleanPhaseId,
    val status: PhaseStatus,
    val bytes: Long = 0L,
    val count: Int = 0,
)

data class CleanerUiState(
    val scanning: Boolean = false,
    val report: JunkReport? = null,
    val lastFreedBytes: Long = 0,
    val phases: List<CleanPhase> = emptyList(),
)

class CleanerViewModel : ViewModel() {

    private val engine = ServiceLocator.junkEngine
    private val _state = MutableStateFlow(CleanerUiState())
    val state: StateFlow<CleanerUiState> = _state.asStateFlow()

    fun scan() {
        if (_state.value.scanning) return
        val initial = listOf(
            CleanPhase(CleanPhaseId.CACHE_SCAN, PhaseStatus.PENDING),
            CleanPhase(CleanPhaseId.APK_SCAN, PhaseStatus.PENDING),
            CleanPhase(CleanPhaseId.TEMP_SCAN, PhaseStatus.PENDING),
            CleanPhase(CleanPhaseId.SUMMARY, PhaseStatus.PENDING),
        )
        _state.update { it.copy(scanning = true, phases = initial, report = null) }
        viewModelScope.launch {
            mark(CleanPhaseId.CACHE_SCAN, PhaseStatus.RUNNING)
            val cacheBytes = engine.measureAppCache()
            phaseBreath()
            mark(CleanPhaseId.CACHE_SCAN, PhaseStatus.DONE, bytes = cacheBytes)

            mark(CleanPhaseId.APK_SCAN, PhaseStatus.RUNNING)
            val apks = engine.findApkLeftovers()
            phaseBreath()
            mark(CleanPhaseId.APK_SCAN, PhaseStatus.DONE, bytes = apks.sumOf { it.sizeBytes }, count = apks.size)

            mark(CleanPhaseId.TEMP_SCAN, PhaseStatus.RUNNING)
            val temps = engine.findTempFiles()
            phaseBreath()
            mark(CleanPhaseId.TEMP_SCAN, PhaseStatus.DONE, bytes = temps.sumOf { it.sizeBytes }, count = temps.size)

            mark(CleanPhaseId.SUMMARY, PhaseStatus.RUNNING)
            val total = cacheBytes + apks.sumOf { it.sizeBytes } + temps.sumOf { it.sizeBytes }
            phaseBreath()
            mark(CleanPhaseId.SUMMARY, PhaseStatus.DONE, bytes = total, count = apks.size + temps.size)

            _state.update {
                it.copy(
                    scanning = false,
                    report = JunkReport(
                        appCacheBytes = cacheBytes,
                        mediaItems = (apks + temps).sortedByDescending { item -> item.sizeBytes },
                    ),
                )
            }
        }
    }

    /** Deletes this app's own cache via the same phased UI, then rescans for media junk. */
    fun cleanAppCache() {
        if (_state.value.scanning) return
        val initial = listOf(
            CleanPhase(CleanPhaseId.CACHE_SCAN, PhaseStatus.PENDING),
            CleanPhase(CleanPhaseId.CACHE_CLEAN, PhaseStatus.PENDING),
            CleanPhase(CleanPhaseId.APK_SCAN, PhaseStatus.PENDING),
            CleanPhase(CleanPhaseId.TEMP_SCAN, PhaseStatus.PENDING),
            CleanPhase(CleanPhaseId.SUMMARY, PhaseStatus.PENDING),
        )
        _state.update { it.copy(scanning = true, phases = initial, report = null) }
        viewModelScope.launch {
            mark(CleanPhaseId.CACHE_SCAN, PhaseStatus.RUNNING)
            val cacheBytesBefore = engine.measureAppCache()
            phaseBreath()
            mark(CleanPhaseId.CACHE_SCAN, PhaseStatus.DONE, bytes = cacheBytesBefore)

            mark(CleanPhaseId.CACHE_CLEAN, PhaseStatus.RUNNING)
            val result = engine.cleanAppCache()
            phaseBreath()
            mark(
                CleanPhaseId.CACHE_CLEAN, PhaseStatus.DONE,
                bytes = result.bytesFreed, count = result.itemsRemoved,
            )

            mark(CleanPhaseId.APK_SCAN, PhaseStatus.RUNNING)
            val apks = engine.findApkLeftovers()
            phaseBreath()
            mark(CleanPhaseId.APK_SCAN, PhaseStatus.DONE, bytes = apks.sumOf { it.sizeBytes }, count = apks.size)

            mark(CleanPhaseId.TEMP_SCAN, PhaseStatus.RUNNING)
            val temps = engine.findTempFiles()
            phaseBreath()
            mark(CleanPhaseId.TEMP_SCAN, PhaseStatus.DONE, bytes = temps.sumOf { it.sizeBytes }, count = temps.size)

            mark(CleanPhaseId.SUMMARY, PhaseStatus.RUNNING)
            val remainingBytes = apks.sumOf { it.sizeBytes } + temps.sumOf { it.sizeBytes }
            phaseBreath()
            mark(
                CleanPhaseId.SUMMARY, PhaseStatus.DONE,
                bytes = result.bytesFreed + remainingBytes,
                count = result.itemsRemoved + apks.size + temps.size,
            )

            _state.update {
                it.copy(
                    scanning = false,
                    lastFreedBytes = result.bytesFreed,
                    report = JunkReport(
                        appCacheBytes = 0L,
                        mediaItems = (apks + temps).sortedByDescending { item -> item.sizeBytes },
                    ),
                )
            }
            ServiceLocator.cleaningHistoryEngine.recordClean(
                CleanSource.JUNK_CACHE,
                result.bytesFreed,
                result.itemsRemoved,
            )
        }
    }

    fun mediaUris(): List<android.net.Uri> =
        _state.value.report?.mediaItems?.map(JunkItem::uri).orEmpty()

    fun buildDeleteRequest() = engine.buildDeleteRequest(mediaUris())

    fun onMediaDeleted() = scan()

    private fun mark(id: CleanPhaseId, status: PhaseStatus, bytes: Long = 0L, count: Int = 0) {
        _state.update { s ->
            s.copy(
                phases = s.phases.map { p ->
                    if (p.id == id) p.copy(status = status, bytes = bytes, count = count) else p
                },
            )
        }
    }

    /** Ensures each step is visible long enough for the animation to land. */
    private suspend fun phaseBreath() = delay(PHASE_DELAY_MS)

    private companion object {
        const val PHASE_DELAY_MS = 280L
    }
}
