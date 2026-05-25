# kotlinx.serialization
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**
-keepclassmembers class **$$serializer { *; }
-keepclasseswithmembers class com.freesystemdoctor.android.** {
    kotlinx.serialization.KSerializer serializer(...);
}
