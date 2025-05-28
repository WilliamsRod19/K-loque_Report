package com.puella_softworks.k_loque_reports.classes

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

object SessionManager {
    private const val PREFS_NAME = "k_loque_reports_secure_prefs"
    private const val KEY_TOKEN = "jwt_token"

    private fun getEncryptedSharedPreferences(context: Context): SharedPreferences {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        return EncryptedSharedPreferences.create(
            context,
            PREFS_NAME,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    fun saveToken(context: Context, token: String) {
        val prefs = getEncryptedSharedPreferences(context)
        prefs.edit().putString(KEY_TOKEN, token).apply()
    }

    fun getToken(context: Context): String? {
        val prefs = getEncryptedSharedPreferences(context)
        return prefs.getString(KEY_TOKEN, null)
    }

    fun clearSession(context: Context) {
        val prefs = getEncryptedSharedPreferences(context)
        prefs.edit().clear().apply()
    }
}