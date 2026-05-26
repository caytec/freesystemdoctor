package com.freesystemdoctor.android

import android.app.Application
import com.freesystemdoctor.android.core.di.ServiceLocator

class FsdApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        ServiceLocator.init(this)
        ServiceLocator.appOpenAdManager.register()
    }
}
