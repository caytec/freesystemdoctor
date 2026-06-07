package com.freesystemdoctor.android.service

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import com.freesystemdoctor.android.core.di.ServiceLocator

data class ActiveNotification(
    val key: String,
    val packageName: String,
    val title: String,
    val text: String,
)

/**
 * Lets the user review and dismiss active notifications. Enabled by the user via
 * the system Notification Access screen (a sensitive permission), not at runtime.
 *
 * Also feeds [com.freesystemdoctor.android.engine.notifications.NotificationStatsEngine]
 * with one event per posted notification so the Notification Stats free-tier tool can
 * show 7-day spammer counts.
 */
class FsdNotificationListener : NotificationListenerService() {

    override fun onListenerConnected() {
        instance = this
    }

    override fun onListenerDisconnected() {
        if (instance === this) instance = null
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        sbn?.packageName?.let { ServiceLocator.notificationStatsEngine.record(it) }
    }

    fun snapshot(): List<ActiveNotification> = runCatching {
        activeNotifications?.mapNotNull { it.toModel() }.orEmpty()
    }.getOrDefault(emptyList())

    fun dismiss(key: String) = runCatching { cancelNotification(key) }

    fun dismissAll() = runCatching { cancelAllNotifications() }

    private fun StatusBarNotification.toModel(): ActiveNotification? {
        val extras = notification?.extras ?: return null
        val title = extras.getCharSequence("android.title")?.toString().orEmpty()
        val text = extras.getCharSequence("android.text")?.toString().orEmpty()
        if (title.isBlank() && text.isBlank()) return null
        return ActiveNotification(
            key = key,
            packageName = packageName,
            title = title.ifBlank { packageName },
            text = text,
        )
    }

    companion object {
        @Volatile
        var instance: FsdNotificationListener? = null
            private set
    }
}
