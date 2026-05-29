package com.freesystemdoctor.android.ui.components

import androidx.compose.runtime.compositionLocalOf

/**
 * App-wide hook used by feature screens to ask the host to show the unlock sheet for a
 * locked tool. The host (typically [com.freesystemdoctor.android.MainActivity]) installs a
 * real controller; everything below it just calls `request(route)`.
 */
interface UnlockController {
    fun request(route: String, labelRes: Int? = null)
}

private val NoopController = object : UnlockController {
    override fun request(route: String, labelRes: Int?) = Unit
}

val LocalUnlockController = compositionLocalOf<UnlockController> { NoopController }
