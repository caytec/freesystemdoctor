package com.freeandroiddoctor.android.billing

import android.util.Base64
import com.freeandroiddoctor.android.BuildConfig
import java.security.KeyFactory
import java.security.Signature
import java.security.spec.X509EncodedKeySpec

/**
 * Verifies that a Purchase's `originalJson` was really signed by Google Play,
 * using the app's RSA public key from Play Console (Monetization → Licensing).
 *
 * This raises the bar against forged entitlements: a value written straight into
 * [com.freeandroiddoctor.android.data.billing.ProStore] (e.g. on a rooted device
 * or via a restored backup) has no valid Play signature and is rejected. It is
 * NOT a substitute for server-side verification against the Play Developer API —
 * a determined attacker who patches the APK can still bypass a client-side check —
 * but it stops the trivial, common forgeries.
 *
 * The key is injected at build time via the `PLAY_PUBLIC_KEY` gradle property
 * (see app/build.gradle.kts). When it is blank — e.g. debug builds without the
 * property — verification is skipped so local testing still works; release builds
 * must ship the real key.
 */
object PurchaseVerifier {

    private const val ALGORITHM = "SHA1withRSA"
    private const val KEY_FACTORY = "RSA"

    fun isSignatureValid(originalJson: String, signatureBase64: String): Boolean {
        val publicKeyBase64 = BuildConfig.PLAY_PUBLIC_KEY
        if (publicKeyBase64.isBlank()) {
            // No key configured: allow in debug (local testing), reject in release
            // so a production build can never silently skip verification.
            return BuildConfig.DEBUG
        }
        return runCatching {
            val keyBytes = Base64.decode(publicKeyBase64, Base64.DEFAULT)
            val publicKey = KeyFactory.getInstance(KEY_FACTORY)
                .generatePublic(X509EncodedKeySpec(keyBytes))
            val signatureBytes = Base64.decode(signatureBase64, Base64.DEFAULT)
            Signature.getInstance(ALGORITHM).run {
                initVerify(publicKey)
                update(originalJson.toByteArray(Charsets.UTF_8))
                verify(signatureBytes)
            }
        }.getOrDefault(false)
    }
}
