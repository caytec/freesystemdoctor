package com.freeandroiddoctor.android.service

import com.freeandroiddoctor.android.engine.gameboost.BoostResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * One-way channel from [GameBoostService] to the Game Boost UI.
 *
 * The boost runs exactly once, inside the service, because only the service knows whether
 * DND was actually applied and whether the game was actually launched. The ViewModel used
 * to run its own second boost just to get numbers to display — that double execution is
 * gone; it now observes the real result from here.
 */
object GameBoostResults {

    private val _last = MutableStateFlow<BoostResult?>(null)
    val last: StateFlow<BoostResult?> = _last.asStateFlow()

    fun publish(result: BoostResult) {
        _last.value = result
    }

    fun clear() {
        _last.value = null
    }
}
