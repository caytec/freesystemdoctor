# ---- kotlinx.serialization (official R8 keep rules) ----
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**

# Keep the Companion of @Serializable classes.
-if @kotlinx.serialization.Serializable class **
-keepclassmembers class <1> {
    static <1>$Companion Companion;
}

# Keep serializer() on those companions.
-if @kotlinx.serialization.Serializable class ** {
    static **$Companion Companion;
}
-keepclassmembers class <1>$Companion {
    kotlinx.serialization.KSerializer serializer(...);
}

# Keep INSTANCE.serializer() for serializable objects.
-if @kotlinx.serialization.Serializable class ** {
    public static ** INSTANCE;
}
-keepclassmembers class <1> {
    public static <1> INSTANCE;
    kotlinx.serialization.KSerializer serializer(...);
}

-keepclassmembers class **$$serializer { *; }

# Our serializable AI DTOs.
-keep,includedescriptorclasses class com.freesystemdoctor.android.ai.**$$serializer { *; }
-keepclassmembers class com.freesystemdoctor.android.ai.** {
    *** Companion;
}

# OkHttp / Okio ship their own consumer rules; AdMob and Play Billing bundle theirs.
-dontwarn okhttp3.**
-dontwarn okio.**

# Play Core review-ktx references an annotation from a newer play-services-tasks
# that isn't on its classpath; safe to ignore (annotation only, no runtime effect).
-dontwarn com.google.android.gms.common.annotation.**
