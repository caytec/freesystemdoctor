package com.freeandroiddoctor.android.ui.modes

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.data.modes.AppMode
import com.freeandroiddoctor.android.data.modes.BuiltInModes
import com.freeandroiddoctor.android.data.modes.ModeSnapshot
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class ModesState(
    val builtIn: List<AppMode> = BuiltInModes.all,
    val custom: List<AppMode> = emptyList(),
    val active: ModeSnapshot? = null,
    val busy: Boolean = false,
)

class ModesViewModel(app: Application) : AndroidViewModel(app) {

    private val store = ServiceLocator.modeStore
    private val engine = ServiceLocator.appModesEngine

    private val _busy = MutableStateFlow(false)

    val state: StateFlow<ModesState> = combine(
        store.customModes, store.activeSnapshot, _busy,
    ) { custom, active, busy ->
        ModesState(custom = custom, active = active, busy = busy)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), ModesState())

    fun activate(mode: AppMode) {
        if (_busy.value) return
        _busy.value = true
        viewModelScope.launch {
            ServiceLocator.dailyQuotaStore.consume(
                com.freeandroiddoctor.android.data.quota.DailyQuotaStore.Key.MODE_SWITCH,
            )
            engine.activate(mode)
            _busy.value = false
        }
    }

    fun deactivate() {
        if (_busy.value) return
        _busy.value = true
        viewModelScope.launch {
            engine.deactivate()
            _busy.value = false
        }
    }
}
