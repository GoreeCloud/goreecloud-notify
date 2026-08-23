package com.goreecloud.goreecloud_notify_client

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

internal class PersistentDeliveryStore(context: Context) {
    private val preferences = context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)

    var enabled: Boolean
        get() = preferences.getBoolean(KEY_ENABLED, false)
        set(value) = preferences.edit().putBoolean(KEY_ENABLED, value).apply()

    var server: String?
        get() = preferences.getString(KEY_SERVER, null)
        set(value) = preferences.edit().putString(KEY_SERVER, value).apply()

    var lastDeliveryId: Long
        get() = preferences.getLong(KEY_LAST_DELIVERY_ID, 0L)
        set(value) = preferences.edit().putLong(KEY_LAST_DELIVERY_ID, value).apply()

    fun writeSessionCookie(cookie: String) {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey())
        val encrypted = cipher.doFinal(cookie.toByteArray(Charsets.UTF_8))
        preferences.edit()
            .putString(KEY_COOKIE_CIPHERTEXT, Base64.encodeToString(encrypted, Base64.NO_WRAP))
            .putString(KEY_COOKIE_IV, Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
            .apply()
    }

    fun readSessionCookie(): String? {
        val ciphertext = preferences.getString(KEY_COOKIE_CIPHERTEXT, null) ?: return null
        val iv = preferences.getString(KEY_COOKIE_IV, null) ?: return null
        return runCatching {
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(
                Cipher.DECRYPT_MODE,
                getOrCreateKey(),
                GCMParameterSpec(128, Base64.decode(iv, Base64.NO_WRAP)),
            )
            String(
                cipher.doFinal(Base64.decode(ciphertext, Base64.NO_WRAP)),
                Charsets.UTF_8,
            )
        }.getOrNull()
    }

    fun clearSession() {
        enabled = false
        preferences.edit()
            .remove(KEY_COOKIE_CIPHERTEXT)
            .remove(KEY_COOKIE_IV)
            .remove(KEY_SERVER)
            .remove(KEY_LAST_DELIVERY_ID)
            .apply()
    }

    private fun getOrCreateKey(): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }

        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE).run {
            init(
                KeyGenParameterSpec.Builder(
                    KEY_ALIAS,
                    KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
                )
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .setUserAuthenticationRequired(false)
                    .build(),
            )
            generateKey()
        }
    }

    private companion object {
        const val PREFERENCES = "goreecloud_notify_persistent_delivery"
        const val KEY_ENABLED = "enabled"
        const val KEY_SERVER = "server"
        const val KEY_LAST_DELIVERY_ID = "last_delivery_id"
        const val KEY_COOKIE_CIPHERTEXT = "session_cookie_ciphertext"
        const val KEY_COOKIE_IV = "session_cookie_iv"
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val KEY_ALIAS = "goreecloud_notify_persistent_delivery_session"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
    }
}
