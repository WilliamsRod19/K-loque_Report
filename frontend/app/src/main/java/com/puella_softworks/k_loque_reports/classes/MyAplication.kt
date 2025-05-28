package com.puella_softworks.k_loque_reports.classes

import android.app.Application
import android.content.Context

class MyApplication : Application() {
    companion object {
        lateinit var appContext: Context
    }

    override fun onCreate() {
        super.onCreate()
        appContext = applicationContext
    }
}