package com.freeandroiddoctor.android.widget

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.StatFs
import android.widget.RemoteViews
import com.freeandroiddoctor.android.MainActivity
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.core.util.ByteFormatter
import kotlin.concurrent.thread

class CleanWidgetProvider : AppWidgetProvider() {

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray,
    ) {
        appWidgetIds.forEach { id -> render(context, appWidgetManager, id) }
    }

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)
        if (intent.action == ACTION_CLEAN) {
            val pending = goAsync()
            thread {
                runCatching { ServiceLocator.junkEngine.cleanAppCache() }
                renderAll(context)
                pending.finish()
            }
        }
    }

    private fun renderAll(context: Context) {
        val manager = AppWidgetManager.getInstance(context)
        val ids = manager.getAppWidgetIds(ComponentName(context, CleanWidgetProvider::class.java))
        ids.forEach { render(context, manager, it) }
    }

    private fun render(context: Context, manager: AppWidgetManager, widgetId: Int) {
        val views = RemoteViews(context.packageName, R.layout.widget_clean)
        views.setTextViewText(R.id.widget_free, freeSpaceText(context))

        val cleanIntent = Intent(context, CleanWidgetProvider::class.java).setAction(ACTION_CLEAN)
        val cleanPending = PendingIntent.getBroadcast(
            context, 0, cleanIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        views.setOnClickPendingIntent(R.id.widget_clean_button, cleanPending)

        val openPending = PendingIntent.getActivity(
            context, 1, Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        views.setOnClickPendingIntent(R.id.widget_title, openPending)

        manager.updateAppWidget(widgetId, views)
    }

    private fun freeSpaceText(context: Context): String {
        val stat = StatFs(context.filesDir.absolutePath)
        val free = stat.availableBytes
        val total = stat.totalBytes
        return context.getString(
            R.string.widget_free_of,
            ByteFormatter.format(free),
            ByteFormatter.format(total),
        )
    }

    private companion object {
        const val ACTION_CLEAN = "com.freeandroiddoctor.android.widget.CLEAN"
    }
}
