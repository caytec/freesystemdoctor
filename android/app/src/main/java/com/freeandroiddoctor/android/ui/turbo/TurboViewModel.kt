package com.freeandroiddoctor.android.ui.turbo

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.core.shizuku.ShizukuCommand
import com.freeandroiddoctor.android.core.shizuku.ShizukuManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/** Which privileged action the user can run, and whether it is currently applied. */
enum class TurboAction { TRIM_CACHES, FAST_ANIMATIONS, NORMAL_ANIMATIONS }

data class TurboUiState(
    val status: ShizukuManager.Status = ShizukuManager.Status.Unavailable,
    val running: TurboAction? = null,
    val lastAction: TurboAction? = null,
    val lastSucceeded: Boolean? = null,
    val lastMessage: String? = null,
)

class TurboViewModel : ViewModel() {

    private val shizuku = ServiceLocator.shizukuManager

    private val _state = MutableStateFlow(TurboUiState())
    val state: StateFlow<TurboUiState> = _state.asStateFlow()

    fun refreshStatus() {
        _state.value = _state.value.copy(status = shizuku.status())
    }

    fun requestPermission() {
        shizuku.requestPermission()
        refreshStatus()
    }

    fun run(action: TurboAction) {
        if (_state.value.running != null) return
        _state.value = _state.value.copy(running = action, lastSucceeded = null, lastMessage = null)
        viewModelScope.launch {
            val command = when (action) {
                TurboAction.TRIM_CACHES -> ShizukuCommand.TrimCaches()
                TurboAction.FAST_ANIMATIONS -> ShizukuCommand.SetAnimationScale(0.5f)
                TurboAction.NORMAL_ANIMATIONS -> ShizukuCommand.SetAnimationScale(1.0f)
            }
            val result = shizuku.run(command)
            _state.value = _state.value.copy(
                running = null,
                lastAction = action,
                lastSucceeded = result.ok,
                // Only surface stderr on failure, and never the command itself.
                lastMessage = if (result.ok) null else result.stderr.take(200).ifBlank { null },
                status = shizuku.status(),
            )
        }
    }
}
