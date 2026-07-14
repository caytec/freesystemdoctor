package com.freeandroiddoctor.android.engine.cloudbackup

import java.io.InputStream
import java.io.OutputStream
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.CipherInputStream
import javax.crypto.CipherOutputStream
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.PBEKeySpec
import javax.crypto.spec.SecretKeySpec

/**
 * Streaming AES-256/GCM with a PBKDF2-derived key, used to wrap the cloud-backup ZIP.
 *
 * Layout written to the destination:
 *   `[ 16-byte salt ][ 12-byte nonce ][ ciphertext... ][ GCM tag (16B, appended by JCE) ]`
 *
 * Why not reuse [com.freeandroiddoctor.android.engine.vault.AppVaultEngine]?
 * The vault key lives in AndroidKeystore and is device-bound; a backup must be portable
 * to a new device, so we derive the AES key from a user passphrase instead.
 *
 * KDF: PBKDF2WithHmacSHA256, **600_000** iterations (OWASP 2024 minimum). PBKDF2-SHA1 — the
 * Java default for the PBKDF2WithHmacSHA name without a hash suffix — is explicitly NOT used.
 */
class BackupCryptoEngine {

    private val random = SecureRandom()

    /**
     * Returns a [CipherOutputStream] that streams ciphertext to [target]. The 28-byte header
     * (salt + nonce) is already written before this returns. Caller closes the returned stream;
     * the GCM tag is appended on close.
     */
    fun wrap(target: OutputStream, passphrase: CharArray): OutputStream {
        val salt = ByteArray(SALT_BYTES).also { random.nextBytes(it) }
        val nonce = ByteArray(NONCE_BYTES).also { random.nextBytes(it) }
        target.write(salt)
        target.write(nonce)
        val key = deriveKey(passphrase, salt)
        val cipher = Cipher.getInstance(TRANSFORMATION).apply {
            init(Cipher.ENCRYPT_MODE, key, GCMParameterSpec(GCM_TAG_BITS, nonce))
        }
        return CipherOutputStream(target, cipher)
    }

    /** Reads the header off [source] and returns a [CipherInputStream] of plaintext. */
    fun unwrap(source: InputStream, passphrase: CharArray): InputStream {
        val salt = source.readNBytesCompat(SALT_BYTES)
        val nonce = source.readNBytesCompat(NONCE_BYTES)
        val key = deriveKey(passphrase, salt)
        val cipher = Cipher.getInstance(TRANSFORMATION).apply {
            init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(GCM_TAG_BITS, nonce))
        }
        return CipherInputStream(source, cipher)
    }

    private fun deriveKey(passphrase: CharArray, salt: ByteArray): SecretKeySpec {
        val spec = PBEKeySpec(passphrase, salt, PBKDF2_ITERATIONS, AES_KEY_BITS)
        val raw = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
            .generateSecret(spec).encoded
        return SecretKeySpec(raw, "AES")
    }

    private fun InputStream.readNBytesCompat(n: Int): ByteArray {
        val out = ByteArray(n)
        var off = 0
        while (off < n) {
            val read = read(out, off, n - off)
            if (read < 0) error("Backup truncated — header incomplete")
            off += read
        }
        return out
    }

    private companion object {
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val SALT_BYTES = 16
        const val NONCE_BYTES = 12
        const val GCM_TAG_BITS = 128
        const val AES_KEY_BITS = 256
        const val PBKDF2_ITERATIONS = 600_000
    }
}
