package com.freeandroiddoctor.android.engine.system

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.os.Build

class ClipboardCleanerEngine(private val context: Context) {

    fun hasContent(): Boolean {
        val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        return cm.hasPrimaryClip() && (cm.primaryClip?.itemCount ?: 0) > 0
    }

    /** Clears the system clipboard. Works when the app is in the foreground. */
    fun clear(): Boolean = runCatching {
        val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            cm.clearPrimaryClip()
        } else {
            cm.setPrimaryClip(ClipData.newPlainText("", ""))
        }
        true
    }.getOrDefault(false)
}
