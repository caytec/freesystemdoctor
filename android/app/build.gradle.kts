import java.io.FileInputStream
import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
}

// Release signing is read from android/keystore.properties (git-ignored) or, in CI,
// from environment variables. If neither is present the release build is left unsigned
// (still useful for Play, which re-signs via Play App Signing).
val keystorePropsFile = rootProject.file("keystore.properties")
val keystoreProps = Properties().apply {
    if (keystorePropsFile.exists()) FileInputStream(keystorePropsFile).use { load(it) }
}
val releaseStorePath: String? =
    keystoreProps.getProperty("storeFile") ?: System.getenv("KEYSTORE_FILE")

// AdMob unit IDs — read from android/admob.properties (git-ignored). Falls back to
// admob.properties.template (committed, holds Google's official TEST IDs) so a fresh
// clone still builds and serves test ads.
val admobPropsFile = rootProject.file("admob.properties")
val admobTemplate = rootProject.file("admob.properties.template")
val admobProps = Properties().apply {
    val src = if (admobPropsFile.exists()) admobPropsFile else admobTemplate
    if (src.exists()) FileInputStream(src).use { load(it) }
}
fun admob(key: String, default: String): String =
    (admobProps.getProperty(key) ?: System.getenv(key.uppercase().replace('.', '_')) ?: default)

android {
    namespace = "com.freesystemdoctor.android"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.freesystemdoctor.android"
        minSdk = 26
        targetSdk = 35
        versionCode = 5
        versionName = "1.4.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        resourceConfigurations += listOf("en", "pl")

        // AdMob — values come from android/admob.properties (git-ignored).
        resValue(
            "string",
            "admob_app_id",
            admob("admob.app.id", "ca-app-pub-3940256099942544~3347511713"),
        )
        buildConfigField(
            "String",
            "ADMOB_BANNER_ID",
            "\"${admob("admob.banner.id", "ca-app-pub-3940256099942544/9214589741")}\"",
        )
        buildConfigField(
            "String",
            "ADMOB_INTERSTITIAL_ID",
            "\"${admob("admob.interstitial.id", "ca-app-pub-3940256099942544/1033173712")}\"",
        )
        buildConfigField(
            "String",
            "ADMOB_REWARDED_ID",
            "\"${admob("admob.rewarded.id", "ca-app-pub-3940256099942544/5224354917")}\"",
        )
        buildConfigField(
            "String",
            "ADMOB_APPOPEN_ID",
            "\"${admob("admob.appopen.id", "ca-app-pub-3940256099942544/9257395921")}\"",
        )
    }

    signingConfigs {
        create("release") {
            if (releaseStorePath != null) {
                storeFile = rootProject.file(releaseStorePath)
                storePassword = keystoreProps.getProperty("storePassword")
                    ?: System.getenv("KEYSTORE_PASSWORD")
                keyAlias = keystoreProps.getProperty("keyAlias") ?: System.getenv("KEY_ALIAS")
                keyPassword = keystoreProps.getProperty("keyPassword")
                    ?: System.getenv("KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
            signingConfig = if (releaseStorePath != null) {
                signingConfigs.getByName("release")
            } else {
                null
            }
        }
        debug {
            applicationIdSuffix = ".debug"
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    testOptions {
        unitTests {
            isIncludeAndroidResources = true
            isReturnDefaultValues = true
        }
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.core.splashscreen)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.process)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)
    implementation(libs.androidx.material.icons.extended)
    implementation(libs.androidx.navigation.compose)

    implementation(libs.androidx.datastore.preferences)
    implementation(libs.androidx.documentfile)
    implementation(libs.androidx.work.runtime.ktx)
    implementation(libs.androidx.security.crypto)
    implementation(libs.androidx.biometric)
    implementation(libs.coil.compose)

    implementation(libs.okhttp)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.kotlinx.coroutines.android)

    implementation(libs.play.services.ads)
    implementation(libs.billing.ktx)
    implementation(libs.user.messaging.platform)

    debugImplementation(libs.androidx.ui.tooling)

    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.okhttp.mockwebserver)
    testImplementation(libs.robolectric)
    testImplementation(libs.androidx.test.ext.junit)
}
