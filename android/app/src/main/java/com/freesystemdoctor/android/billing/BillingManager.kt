package com.freesystemdoctor.android.billing

import android.app.Activity
import android.content.Context
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.PendingPurchasesParams
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.PurchasesUpdatedListener
import com.android.billingclient.api.QueryProductDetailsParams
import com.android.billingclient.api.QueryPurchasesParams
import com.android.billingclient.api.acknowledgePurchase
import com.android.billingclient.api.queryProductDetails
import com.android.billingclient.api.queryPurchasesAsync
import com.freesystemdoctor.android.data.billing.ProStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

/** A purchasable Pro plan surfaced to the UI. */
data class ProProduct(
    val productId: String,
    val title: String,
    val price: String,
    val isSubscription: Boolean,
    val details: ProductDetails,
    val offerToken: String?,
)

/**
 * Wraps Google Play Billing v7. Offers two subscriptions and a one-time lifetime
 * purchase that all grant "Pro" (ad-free + advanced tools). Entitlement is verified
 * against Google Play on every connection and cached in [ProStore].
 */
class BillingManager(
    context: Context,
    private val proStore: ProStore,
) : PurchasesUpdatedListener {

    private val appContext = context.applicationContext
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    private val _products = MutableStateFlow<List<ProProduct>>(emptyList())
    val products: StateFlow<List<ProProduct>> = _products.asStateFlow()

    private val _isPro = MutableStateFlow(false)
    val isPro: StateFlow<Boolean> = _isPro.asStateFlow()

    private val client: BillingClient = BillingClient.newBuilder(appContext)
        .setListener(this)
        .enablePendingPurchases(
            PendingPurchasesParams.newBuilder().enableOneTimeProducts().build(),
        )
        .build()

    init {
        scope.launch { _isPro.value = proStore.isPro.first() }
    }

    fun connect() {
        if (client.isReady) {
            refresh()
            return
        }
        client.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(result: BillingResult) {
                if (result.responseCode == BillingClient.BillingResponseCode.OK) refresh()
            }

            override fun onBillingServiceDisconnected() {}
        })
    }

    private fun refresh() {
        scope.launch {
            queryProducts()
            queryEntitlements()
        }
    }

    private suspend fun queryProducts() {
        val subProducts = listOf(SUB_MONTHLY, SUB_YEARLY).map {
            QueryProductDetailsParams.Product.newBuilder()
                .setProductId(it)
                .setProductType(BillingClient.ProductType.SUBS)
                .build()
        }
        val inAppProducts = listOf(LIFETIME).map {
            QueryProductDetailsParams.Product.newBuilder()
                .setProductId(it)
                .setProductType(BillingClient.ProductType.INAPP)
                .build()
        }

        val result = ArrayList<ProProduct>()
        runCatching {
            val subs = client.queryProductDetails(
                QueryProductDetailsParams.newBuilder().setProductList(subProducts).build(),
            )
            subs.productDetailsList?.forEach { details ->
                val offer = details.subscriptionOfferDetails?.firstOrNull()
                val price = offer?.pricingPhases?.pricingPhaseList?.firstOrNull()?.formattedPrice
                result += ProProduct(
                    productId = details.productId,
                    title = details.title,
                    price = price.orEmpty(),
                    isSubscription = true,
                    details = details,
                    offerToken = offer?.offerToken,
                )
            }
            val inApp = client.queryProductDetails(
                QueryProductDetailsParams.newBuilder().setProductList(inAppProducts).build(),
            )
            inApp.productDetailsList?.forEach { details ->
                result += ProProduct(
                    productId = details.productId,
                    title = details.title,
                    price = details.oneTimePurchaseOfferDetails?.formattedPrice.orEmpty(),
                    isSubscription = false,
                    details = details,
                    offerToken = null,
                )
            }
        }
        _products.value = result
    }

    private suspend fun queryEntitlements() {
        var entitled = false
        runCatching {
            val subs = client.queryPurchasesAsync(
                QueryPurchasesParams.newBuilder()
                    .setProductType(BillingClient.ProductType.SUBS).build(),
            )
            val inApp = client.queryPurchasesAsync(
                QueryPurchasesParams.newBuilder()
                    .setProductType(BillingClient.ProductType.INAPP).build(),
            )
            (subs.purchasesList + inApp.purchasesList).forEach { purchase ->
                if (purchase.purchaseState == Purchase.PurchaseState.PURCHASED) {
                    entitled = true
                    acknowledgeIfNeeded(purchase)
                }
            }
        }
        _isPro.value = entitled
        proStore.setPro(entitled)
    }

    fun purchase(activity: Activity, product: ProProduct) {
        com.freesystemdoctor.android.core.di.ServiceLocator.appOpenAdManager.suppressNextShow()
        val paramsBuilder = BillingFlowParams.ProductDetailsParams.newBuilder()
            .setProductDetails(product.details)
        product.offerToken?.let { paramsBuilder.setOfferToken(it) }
        val flowParams = BillingFlowParams.newBuilder()
            .setProductDetailsParamsList(listOf(paramsBuilder.build()))
            .build()
        client.launchBillingFlow(activity, flowParams)
    }

    fun restore() = refresh()

    override fun onPurchasesUpdated(result: BillingResult, purchases: MutableList<Purchase>?) {
        if (result.responseCode == BillingClient.BillingResponseCode.OK && purchases != null) {
            scope.launch {
                var entitled = false
                purchases.forEach { purchase ->
                    if (purchase.purchaseState == Purchase.PurchaseState.PURCHASED) {
                        entitled = true
                        acknowledgeIfNeeded(purchase)
                    }
                }
                if (entitled) {
                    _isPro.value = true
                    proStore.setPro(true)
                }
            }
        }
    }

    private suspend fun acknowledgeIfNeeded(purchase: Purchase) {
        if (!purchase.isAcknowledged) {
            runCatching {
                client.acknowledgePurchase(
                    AcknowledgePurchaseParams.newBuilder()
                        .setPurchaseToken(purchase.purchaseToken).build(),
                )
            }
        }
    }

    companion object {
        const val SUB_MONTHLY = "fsd_pro_monthly"
        const val SUB_YEARLY = "fsd_pro_yearly"
        const val LIFETIME = "fsd_pro_lifetime"
    }
}
