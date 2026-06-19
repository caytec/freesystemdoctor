package com.freeandroiddoctor.android.engine.vault

import android.content.Context
import android.net.Uri
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.io.File
import java.security.KeyStore
import java.util.UUID
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

@Serializable
data class VaultEntry(
    val id: String,
    val originalName: String,
    val sizeBytes: Long,
    val addedAt: Long,
    val mimeType: String,
)

@Serializable
private data class VaultIndex(val entries: List<VaultEntry> = emptyList())

/**
 * Encrypted on-device sandbox for sensitive files. Files are encrypted with an
 * AndroidKeystore-backed AES/GCM key and stored under `filesDir/vault/<id>.enc`;
 * the keystore alias never leaves the device. The UI gates access behind a
 * BiometricPrompt before listing or exporting any entries.
 */
class AppVaultEngine(private val context: Context) {

    private val vaultDir: File = File(context.filesDir, "vault").apply { mkdirs() }
    private val indexFile: File = File(vaultDir, "index.json")
    private val json = Json { ignoreUnknownKeys = true; prettyPrint = false }

    suspend fun list(): List<VaultEntry> = withContext(Dispatchers.IO) { readIndex().entries }

    /** Reads bytes from [source] (a SAF document the user picked) and writes an encrypted blob. */
    suspend fun add(source: Uri, displayName: String, mimeType: String): VaultEntry? =
        withContext(Dispatchers.IO) {
            val input = context.contentResolver.openInputStream(source) ?: return@withContext null
            val bytes = input.use { it.readBytes() }
            val id = UUID.randomUUID().toString()
            val cipher = Cipher.getInstance(TRANSFORMATION).apply { init(Cipher.ENCRYPT_MODE, key()) }
            val ciphertext = cipher.doFinal(bytes)
            val out = File(vaultDir, "$id.enc")
            out.outputStream().use {
                it.write(cipher.iv.size)
                it.write(cipher.iv)
                it.write(ciphertext)
            }
            val entry = VaultEntry(
                id = id,
                originalName = displayName,
                sizeBytes = bytes.size.toLong(),
                addedAt = System.currentTimeMillis(),
                mimeType = mimeType,
            )
            saveIndex(readIndex().copy(entries = readIndex().entries + entry))
            entry
        }

    /** Decrypts [id] and writes the plaintext to [destination] (a SAF document). */
    suspend fun export(id: String, destination: Uri): Boolean = withContext(Dispatchers.IO) {
        val file = File(vaultDir, "$id.enc").takeIf { it.exists() } ?: return@withContext false
        runCatching {
            val data = file.readBytes()
            val ivLen = data[0].toInt()
            val iv = data.copyOfRange(1, 1 + ivLen)
            val ciphertext = data.copyOfRange(1 + ivLen, data.size)
            val cipher = Cipher.getInstance(TRANSFORMATION).apply {
                init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(GCM_TAG_BITS, iv))
            }
            val plain = cipher.doFinal(ciphertext)
            context.contentResolver.openOutputStream(destination)?.use { it.write(plain) }
                ?: return@runCatching false
            true
        }.getOrDefault(false)
    }

    suspend fun delete(id: String) = withContext(Dispatchers.IO) {
        File(vaultDir, "$id.enc").delete()
        val idx = readIndex()
        saveIndex(idx.copy(entries = idx.entries.filterNot { it.id == id }))
    }

    private fun readIndex(): VaultIndex =
        if (indexFile.exists()) {
            runCatching { json.decodeFromString(VaultIndex.serializer(), indexFile.readText()) }
                .getOrDefault(VaultIndex())
        } else VaultIndex()

    private fun saveIndex(index: VaultIndex) {
        indexFile.writeText(json.encodeToString(VaultIndex.serializer(), index))
    }

    private fun key(): SecretKey {
        val ks = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        (ks.getKey(ALIAS, null) as? SecretKey)?.let { return it }
        val gen = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE)
        gen.init(
            KeyGenParameterSpec.Builder(
                ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build(),
        )
        return gen.generateKey()
    }

    private companion object {
        const val KEYSTORE = "AndroidKeyStore"
        const val ALIAS = "fsd_vault_v1"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val GCM_TAG_BITS = 128
    }
}
