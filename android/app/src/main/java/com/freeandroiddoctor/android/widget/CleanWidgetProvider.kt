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
import com.freeandroiddoctor.android.core.util.ByteFormatter

class CleanWidgetProvider : AppWidgetProvider() {

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray,
    ) {
        appWidgetIds.forEach { id -> render(context, appWidgetManager, id) }
    }

    private fun render(context: Context, manager: AppWidgetManager, widgetId: Int) {
        val views = RemoteViews(context.packageName, R.layout.widget_clean)
        views.setTextViewText(R.id.widget_free, freeSpaceText(context))

        val cleanIntent = Intent(context, CleanActionReceiver::class.java)
            .setAction(CleanActionReceiver.ACTION_CLEAN)
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

    companion object {
        internal fun renderAll(context: Context) {
            val manager = AppWidgetManager.getInstance(context)
            val ids = manager.getAppWidgetIds(ComponentName(context, CleanWidgetProvider::class.java))
            val provider = CleanWidgetProvider()
            ids.forEach { provider.render(context, manager, it) }
        }
    }
}
