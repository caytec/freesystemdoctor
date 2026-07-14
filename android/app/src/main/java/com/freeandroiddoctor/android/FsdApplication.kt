package com.freeandroiddoctor.android

import android.app.Application
import com.freeandroiddoctor.android.core.di.ServiceLocator

class FsdApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        ServiceLocator.init(this)
        ServiceLocator.appOpenAdManager.register()
    }
}
