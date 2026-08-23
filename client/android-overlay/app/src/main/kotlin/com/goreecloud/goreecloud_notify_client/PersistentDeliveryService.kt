package com.goreecloud.goreecloud_notify_client

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import java.net.HttpURLConnection
import java.net.URI
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.math.min

class PersistentDeliveryService : Service() {
    private val executor = Executors.newSingleThreadExecutor()
    private val deliveryLoopRunning = AtomicBoolean(false)
    @Volatile private var stopped = false

    override fun onCreate() {
        super.onCreate()
        createChannels()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val store = PersistentDeliveryStore(this)
        if (!store.enabled || store.readSessionCookie().isNullOrBlank() || store.server.isNullOrBlank()) {
            stopSelf()
            return START_NOT_STICKY
        }

        val notification = foregroundNotification()
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(
                FOREGROUND_NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE,
            )
        } else {
            startForeground(FOREGROUND_NOTIFICATION_ID, notification)
        }

        if (deliveryLoopRunning.compareAndSet(false, true)) {
            executor.execute {
                try {
                    deliveryLoop(store)
                } finally {
                    deliveryLoopRunning.set(false)
                }
            }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        stopped = true
        executor.shutdownNow()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun deliveryLoop(store: PersistentDeliveryStore) {
        var retrySeconds = 3L
        while (!stopped && store.enabled) {
            val server = store.server ?: break
            val cookie = store.readSessionCookie() ?: break
            val after = store.lastDeliveryId
            var connection: HttpURLConnection? = null
            try {
                val streamUrl = URI.create("$server/api/v1/inbox/stream?after_id=$after").toURL()
                connection = (streamUrl.openConnection() as HttpURLConnection).apply {
                    requestMethod = "GET"
                    setRequestProperty("Accept", "text/event-stream")
                    setRequestProperty("Cookie", cookie)
                    connectTimeout = 15_000
                    readTimeout = 75_000
                    instanceFollowRedirects = false
                }
                val status = connection.responseCode
                if (status == 401) {
                    store.clearSession()
                    stopSelf()
                    return
                }
                if (status != 200) throw IllegalStateException("unexpected stream status")

                retrySeconds = 3L
                var event = ""
                var eventId = ""
                connection.inputStream.bufferedReader(Charsets.UTF_8).useLines { lines ->
                    lines.forEach { line ->
                        if (stopped || !store.enabled) return@forEach
                        if (line.isEmpty()) {
                            val deliveryId = eventId.toLongOrNull()
                            if (event == "inbox" && deliveryId != null && deliveryId > store.lastDeliveryId) {
                                store.lastDeliveryId = deliveryId
                                if (!ProcessVisibility.appVisible) showPrivateAlert(deliveryId)
                            }
                            event = ""
                            eventId = ""
                        } else if (!line.startsWith(":")) {
                            when {
                                line.startsWith("event:") -> event = line.substringAfter(':').trim()
                                line.startsWith("id:") -> eventId = line.substringAfter(':').trim()
                            }
                        }
                    }
                }
            } catch (_: Exception) {
                if (!stopped && store.enabled) {
                    try {
                        TimeUnit.SECONDS.sleep(retrySeconds)
                    } catch (_: InterruptedException) {
                        Thread.currentThread().interrupt()
                        return
                    }
                    retrySeconds = min(retrySeconds * 2, 30L)
                }
            } finally {
                connection?.disconnect()
            }
        }
    }

    private fun createChannels() {
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(
                SERVICE_CHANNEL_ID,
                "GoreeCloud Notify background delivery",
                NotificationManager.IMPORTANCE_LOW,
            ).apply {
                description = "Persistent private delivery connection"
                setShowBadge(false)
                lockscreenVisibility = Notification.VISIBILITY_SECRET
            },
        )
        manager.createNotificationChannel(
            NotificationChannel(
                ALERT_CHANNEL_ID,
                "GoreeCloud Notify messages",
                NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                description = "Private GoreeCloud notification alerts"
                lockscreenVisibility = Notification.VISIBILITY_PRIVATE
            },
        )
    }

    private fun foregroundNotification(): Notification =
        Notification.Builder(this, SERVICE_CHANNEL_ID)
            .setSmallIcon(applicationInfo.icon)
            .setContentTitle("GoreeCloud Notify")
            .setContentText("Background alerts enabled")
            .setContentIntent(openAppIntent())
            .setOngoing(true)
            .setCategory(Notification.CATEGORY_SERVICE)
            .setVisibility(Notification.VISIBILITY_SECRET)
            .build()

    private fun showPrivateAlert(deliveryId: Long) {
        val notification = Notification.Builder(this, ALERT_CHANNEL_ID)
            .setSmallIcon(applicationInfo.icon)
            .setContentTitle("GoreeCloud Notify")
            .setContentText("New notification received. Open Notify to view details.")
            .setContentIntent(openAppIntent())
            .setAutoCancel(true)
            .setCategory(Notification.CATEGORY_MESSAGE)
            .setVisibility(Notification.VISIBILITY_PRIVATE)
            .build()
        getSystemService(NotificationManager::class.java)
            .notify((deliveryId and 0x7fffffff).toInt(), notification)
    }

    private fun openAppIntent(): PendingIntent {
        val intent = packageManager.getLaunchIntentForPackage(packageName)
            ?: Intent(this, MainActivity::class.java)
        return PendingIntent.getActivity(
            this,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    private companion object {
        const val SERVICE_CHANNEL_ID = "goreecloud_notify_background_delivery"
        const val ALERT_CHANNEL_ID = "goreecloud_notify_messages"
        const val FOREGROUND_NOTIFICATION_ID = 41001
    }
}
