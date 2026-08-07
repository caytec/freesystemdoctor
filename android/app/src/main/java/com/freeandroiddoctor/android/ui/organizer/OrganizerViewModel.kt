package com.freeandroiddoctor.android.ui.organizer

import android.app.Application
import android.content.Intent
import androidx.core.content.pm.ShortcutInfoCompat
import androidx.core.content.pm.ShortcutManagerCompat
import androidx.core.graphics.drawable.IconCompat
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.freeandroiddoctor.android.MainActivity
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.engine.organizer.AppCategory
import com.freeandroiddoctor.android.engine.organizer.OrganizerReport
import com.freeandroiddoctor.android.ui.navigation.ORGANIZER_CATEGORY_EXTRA
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class OrganizerUiState(
    val report: OrganizerReport? = null,
    val loading: Boolean = true,
    val expanded: Set<AppCategory> = emptySet(),
    val pinSupported: Boolean = false,
)

class OrganizerViewModel(application: Application) : AndroidViewModel(application) {

    private val engine = ServiceLocator.appOrganizerEngine

    private val _state = MutableStateFlow(OrganizerUiState())
    val state: StateFlow<OrganizerUiState> = _state.asStateFlow()

    init {
        _state.value = _state.value.copy(
            pinSupported = ShortcutManagerCompat.isRequestPinShortcutSupported(application),
        )
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true)
            val report = runCatching { engine.organize() }.getOrNull()
            _state.value = _state.value.copy(report = report, loading = false)
        }
    }

    fun toggleExpanded(category: AppCategory) {
        val current = _state.value.expanded
        _state.value = _state.value.copy(
            expanded = if (category in current) current - category else current + category,
        )
    }

    /** Used when arriving from a pinned shortcut — jumps straight to that category. */
    fun expandOnly(category: AppCategory) {
        _state.value = _state.value.copy(expanded = setOf(category))
    }

    fun launchIntent(packageName: String) = engine.launchIntent(packageName)

    fun setCategory(packageName: String, category: AppCategory?) {
        viewModelScope.launch {
            engine.setManualCategory(packageName, category)
            refresh()
        }
    }

    /**
     * Asks the system to pin a shortcut for [category] to the real home screen. Always shows
     * a system confirmation dialog — we cannot silently place anything there, and the user
     * can remove it afterwards exactly like any other icon.
     */
    fun pinShortcut(category: AppCategory, label: String) {
        val context = getApplication<Application>()
        if (!ShortcutManagerCompat.isRequestPinShortcutSupported(context)) return
        val intent = Intent(context, MainActivity::class.java).apply {
            action = Intent.ACTION_VIEW
            putExtra(ORGANIZER_CATEGORY_EXTRA, category.name)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val shortcut = ShortcutInfoCompat.Builder(context, "organizer_${category.name}")
            .setShortLabel(label)
            .setIcon(IconCompat.createWithResource(context, R.mipmap.ic_launcher))
            .setIntent(intent)
            .build()
        runCatching { ShortcutManagerCompat.requestPinShortcut(context, shortcut, null) }
    }
}
