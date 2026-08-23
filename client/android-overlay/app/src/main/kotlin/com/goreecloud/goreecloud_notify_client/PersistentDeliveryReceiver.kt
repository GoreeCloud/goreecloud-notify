package com.goreecloud.goreecloud_notify_client

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build

class PersistentDeliveryReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED && intent.action != Intent.ACTION_MY_PACKAGE_REPLACED) return
        val store = PersistentDeliveryStore(context)
        if (!store.enabled || store.readSessionCookie().isNullOrBlank() || store.server.isNullOrBlank()) return

        val service = Intent(context, PersistentDeliveryService::class.java)
        runCatching {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(service)
            } else {
                context.startService(service)
            }
        }
    }
}
