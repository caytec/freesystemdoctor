package com.freeandroiddoctor.android

import com.freeandroiddoctor.android.ai.AiClient
import com.freeandroiddoctor.android.ai.AiProvider
import com.freeandroiddoctor.android.ai.AiResult
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class AiClientTest {

    private lateinit var server: MockWebServer
    private val client = AiClient()

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun parsesSuccessfulResponse() = runTest {
        server.enqueue(
            MockResponse().setBody(
                """{"choices":[{"message":{"role":"assistant","content":"Clean your cache."}}]}""",
            ),
        )
        val result = client.complete(
            endpointUrl = server.url("/v1/chat/completions").toString(),
            providerName = "Test",
            apiKey = "key",
            systemPrompt = "sys",
            userPrompt = "user",
            model = "m",
        )
        assertTrue(result is AiResult.Success)
        assertEquals("Clean your cache.", (result as AiResult.Success).content)
    }

    @Test
    fun returnsErrorOnHttpFailure() = runTest {
        server.enqueue(MockResponse().setResponseCode(401).setBody("unauthorized"))
        val result = client.complete(
            endpointUrl = server.url("/v1/chat/completions").toString(),
            providerName = "Test",
            apiKey = "bad",
            systemPrompt = "sys",
            userPrompt = "user",
            model = "m",
        )
        assertTrue(result is AiResult.Error)
        assertTrue((result as AiResult.Error).message.contains("401"))
    }

    @Test
    fun sendsBearerToken() = runTest {
        server.enqueue(
            MockResponse().setBody(
                """{"choices":[{"message":{"role":"assistant","content":"ok"}}]}""",
            ),
        )
        client.complete(
            endpointUrl = server.url("/v1/chat/completions").toString(),
            providerName = "Test",
            apiKey = "secret-token",
            systemPrompt = "sys",
            userPrompt = "user",
            model = "m",
        )
        val request = server.takeRequest()
        assertEquals("Bearer secret-token", request.getHeader("Authorization"))
    }

    @Test
    fun providerUrlsAreOpenAiCompatible() {
        assertTrue(AiProvider.GROQ.chatCompletionsUrl.endsWith("/chat/completions"))
        assertTrue(AiProvider.CEREBRAS.chatCompletionsUrl.startsWith("https://"))
        assertEquals(3, AiProvider.entries.size)
    }
}
