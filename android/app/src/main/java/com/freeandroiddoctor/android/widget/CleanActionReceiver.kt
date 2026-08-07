package com.freeandroiddoctor.android.widget

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.freeandroiddoctor.android.core.di.ServiceLocator
import kotlin.concurrent.thread

/**
 * Handles the widget's clean button. Separate, non-exported receiver so no
 * other app can trigger cache cleaning by spoofing the widget action —
 * the widget provider itself must stay exported for APPWIDGET_UPDATE.
 */
class CleanActionReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != ACTION_CLEAN) return
        val pending = goAsync()
        thread {
            runCatching { ServiceLocator.junkEngine.cleanAppCache() }
            CleanWidgetProvider.renderAll(context)
            pending.finish()
        }
    }

    companion object {
        const val ACTION_CLEAN = "com.freeandroiddoctor.android.widget.CLEAN"
    }
}
