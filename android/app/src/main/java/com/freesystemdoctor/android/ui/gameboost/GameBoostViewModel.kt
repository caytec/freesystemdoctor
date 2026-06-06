package com.freesystemdoctor.android.ui.gameboost

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.freesystemdoctor.android.core.di.ServiceLocator
import com.freesystemdoctor.android.engine.gameboost.BoostResult
import com.freesystemdoctor.android.engine.gameboost.InstalledGame
import com.freesystemdoctor.android.service.GameBoostService
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class GameBoostUi(
    val loading: Boolean = false,
    val games: List<InstalledGame> = emptyList(),
    val allApps: List<InstalledGame> = emptyList(),
    val showAllApps: Boolean = false,
    val sustainedPerformanceSupported: Boolean = false,
    val hasDndAccess: Boolean = true,
    val lastResult: BoostResult? = null,
    val sessionRunning: Boolean = false,
)

class GameBoostViewModel(app: Application) : AndroidViewModel(app) {

    private val engine = ServiceLocator.gameBoostEngine
    private val profileStore = ServiceLocator.gameProfileStore
    private val focus = ServiceLocator.focusEngine

    private val _ui = MutableStateFlow(GameBoostUi())
    val ui: StateFlow<GameBoostUi> = _ui.asStateFlow()

    val boostedPackages: StateFlow<Set<String>> = profileStore.boostedPackages
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptySet())
    val enterDnd: StateFlow<Boolean> = profileStore.enterDnd
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), true)

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _ui.value = _ui.value.copy(loading = true)
            val games = engine.listInstalledGames()
            _ui.value = _ui.value.copy(
                loading = false,
                games = games,
                sustainedPerformanceSupported = engine.sustainedPerformanceSupported(),
                hasDndAccess = focus.hasDndAccess(),
            )
        }
    }

    fun loadAllApps() {
        viewModelScope.launch {
            val apps = engine.listAllInstalledApps()
            _ui.value = _ui.value.copy(allApps = apps, showAllApps = true)
        }
    }

    fun hideAllApps() {
        _ui.value = _ui.value.copy(showAllApps = false)
    }

    fun togglePackage(pkg: String) {
        viewModelScope.launch { profileStore.togglePackage(pkg) }
    }

    fun setEnterDnd(value: Boolean) {
        viewModelScope.launch { profileStore.setEnterDnd(value) }
    }

    fun boostOnly() {
        viewModelScope.launch {
            val result = engine.runBoost()
            _ui.value = _ui.value.copy(lastResult = result)
            // Start the session service so the user can end it cleanly.
            GameBoostService.start(getApplication(), enterDnd = enterDnd.value, launchPackage = null)
            _ui.value = _ui.value.copy(sessionRunning = true)
        }
    }

    fun boostAndLaunch(pkg: String) {
        viewModelScope.launch {
            val result = engine.runBoost()
            _ui.value = _ui.value.copy(lastResult = result, sessionRunning = true)
            GameBoostService.start(getApplication(), enterDnd = enterDnd.value, launchPackage = pkg)
        }
    }

    fun endSession() {
        GameBoostService.stop(getApplication())
        _ui.value = _ui.value.copy(sessionRunning = false)
    }
}
