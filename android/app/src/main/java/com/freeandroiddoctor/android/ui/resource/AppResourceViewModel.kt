package com.freeandroiddoctor.android.ui.resource

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.resource.AppResourceReport
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class ResourceUiState(
    val report: AppResourceReport? = null,
    val loading: Boolean = true,
    val message: String? = null,
)

class AppResourceViewModel(application: Application) : AndroidViewModel(application) {

    private val engine = ServiceLocator.appResourceEngine
    private val appManager = ServiceLocator.appManagerEngine
    private val permissions = ServiceLocator.permissionManager

    private val _state = MutableStateFlow(ResourceUiState())
    val state: StateFlow<ResourceUiState> = _state.asStateFlow()

    init { refresh() }

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true)
            val report = engine.report(includeSystem = false, topN = 50)
            _state.value = ResourceUiState(report = report, loading = false)
        }
    }

    fun openAppSettings(packageName: String) =
        appManager.appDetailsIntent(packageName)

    fun uninstallIntent(packageName: String) =
        appManager.uninstallIntent(packageName)

    fun tryStop(packageName: String) {
        val am = getApplication<Application>().getSystemService(
            android.content.Context.ACTIVITY_SERVICE,
        ) as android.app.ActivityManager
        runCatching { am.killBackgroundProcesses(packageName) }
    }

    fun usageAccessIntent() = permissions.usageAccessSettingsIntent()

    fun exportCsv(destination: Uri) {
        viewModelScope.launch {
            val rows = _state.value.report?.rows ?: return@launch
            val ctx = getApplication<Application>()
            val csv = buildString {
                append("packageName,label,score,storageBytes,cacheBytes,data30dBytes,screenTime7dMillis,lastUsed\n")
                rows.forEach {
                    append('"').append(it.packageName).append('"').append(',')
                    append('"').append(it.label.replace("\"", "''")).append('"').append(',')
                    append(it.score).append(',')
                    append(it.storageBytes).append(',')
                    append(it.cacheBytes).append(',')
                    append(it.data30dBytes).append(',')
                    append(it.screenTime7dMillis).append(',')
                    append(it.lastUsed).append('\n')
                }
            }
            runCatching {
                ctx.contentResolver.openOutputStream(destination)?.use { it.write(csv.toByteArray()) }
            }
            _state.value = _state.value.copy(message = "ok")
        }
    }
}
