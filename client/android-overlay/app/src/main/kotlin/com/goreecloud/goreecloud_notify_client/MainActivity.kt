package com.goreecloud.goreecloud_notify_client

import android.content.Intent
import android.os.Build
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun onResume() {
        super.onResume()
        ProcessVisibility.appVisible = true
    }

    override fun onPause() {
        ProcessVisibility.appVisible = false
        super.onPause()
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            CHANNEL,
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "enable" -> {
                    val server = call.argument<String>("server")?.trimEnd('/')
                    val cookie = call.argument<String>("cookie")
                    val afterId = call.argument<Number>("afterId")?.toLong() ?: 0L
                    if (server.isNullOrBlank() || cookie.isNullOrBlank()) {
                        result.error("invalid_arguments", "Server and authenticated session are required.", null)
                        return@setMethodCallHandler
                    }
                    val store = PersistentDeliveryStore(this)
                    store.server = server
                    store.lastDeliveryId = afterId
                    store.writeSessionCookie(cookie)
                    store.enabled = true
                    val service = Intent(this, PersistentDeliveryService::class.java)
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        startForegroundService(service)
                    } else {
                        startService(service)
                    }
                    result.success(true)
                }

                "disable" -> {
                    PersistentDeliveryStore(this).clearSession()
                    stopService(Intent(this, PersistentDeliveryService::class.java))
                    result.success(true)
                }

                "isEnabled" -> result.success(PersistentDeliveryStore(this).enabled)
                else -> result.notImplemented()
            }
        }
    }

    private companion object {
        const val CHANNEL = "com.goreecloud.notify/persistent_alerts"
    }
}
