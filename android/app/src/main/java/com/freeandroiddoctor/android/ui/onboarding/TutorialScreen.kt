package com.freeandroiddoctor.android.ui.onboarding

import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Apps
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.CleaningServices
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.GridView
import androidx.compose.material.icons.filled.PieChart
import androidx.compose.material.icons.filled.RocketLaunch
import androidx.compose.material.icons.filled.ShieldMoon
import androidx.compose.material.icons.filled.WavingHand
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.ui.components.Appear
import com.freeandroiddoctor.android.ui.components.GradientButton
import com.freeandroiddoctor.android.ui.theme.accentGlow
import com.freeandroiddoctor.android.ui.theme.appBackgroundBrush
import kotlinx.coroutines.launch

private data class TutorialTab(val icon: ImageVector, val labelRes: Int)

private val tutorialTabs = listOf(
    TutorialTab(Icons.Filled.Dashboard, R.string.nav_dashboard),
    TutorialTab(Icons.Filled.CleaningServices, R.string.nav_cleaner),
    TutorialTab(Icons.Filled.Apps, R.string.nav_apps),
    TutorialTab(Icons.Filled.GridView, R.string.nav_tools),
    TutorialTab(Icons.Filled.PieChart, R.string.nav_storage),
)

/**
 * First-run, permission-free walkthrough of how the app is laid out. Shown once, before
 * [OnboardingScreen] (which is a permissions request, not a tutorial) — gated by its own
 * `tutorialDone` flag so it never re-appears once dismissed, independent of the
 * permissions-onboarding flag.
 */
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun TutorialScreen(onDone: () -> Unit) {
    val pageCount = 5
    val pagerState = rememberPagerState(pageCount = { pageCount })
    val scope = rememberCoroutineScope()
    val dark = MaterialTheme.colorScheme.background.luminance() < 0.5f
    val isLastPage = pagerState.currentPage == pageCount - 1

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(appBackgroundBrush(dark))
            .padding(16.dp),
    ) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
            TextButton(onClick = onDone) { Text(stringResource(R.string.perm_skip)) }
        }

        HorizontalPager(
            state = pagerState,
            modifier = Modifier.weight(1f).fillMaxWidth(),
        ) { page ->
            Appear {
                when (page) {
                    0 -> TutorialPage(
                        icon = Icons.Filled.WavingHand,
                        title = stringResource(R.string.tutorial_welcome_title),
                        body = stringResource(R.string.tutorial_welcome_body),
                    )
                    1 -> TutorialTabsPage()
                    2 -> TutorialPage(
                        icon = Icons.Filled.Bolt,
                        title = stringResource(R.string.tutorial_quick_clean_title),
                        body = stringResource(R.string.tutorial_quick_clean_body),
                    )
                    3 -> TutorialPage(
                        icon = Icons.Filled.ShieldMoon,
                        title = stringResource(R.string.tutorial_privacy_title),
                        body = stringResource(R.string.tutorial_privacy_body),
                    )
                    else -> TutorialPage(
                        icon = Icons.Filled.RocketLaunch,
                        title = stringResource(R.string.tutorial_turbo_title),
                        body = stringResource(R.string.tutorial_turbo_body),
                    )
                }
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth().padding(vertical = 20.dp),
            horizontalArrangement = Arrangement.Center,
        ) {
            repeat(pageCount) { i ->
                val selected = pagerState.currentPage == i
                val width by animateDpAsState(
                    targetValue = if (selected) 24.dp else 8.dp,
                    animationSpec = tween(260),
                    label = "dotWidth",
                )
                Box(
                    modifier = Modifier
                        .padding(horizontal = 4.dp)
                        .height(8.dp)
                        .width(width)
                        .clip(CircleShape)
                        .background(
                            if (selected) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.3f)
                            },
                        ),
                )
            }
        }

        GradientButton(
            text = stringResource(if (isLastPage) R.string.tutorial_start else R.string.perm_continue),
            onClick = {
                if (isLastPage) {
                    onDone()
                } else {
                    scope.launch { pagerState.animateScrollToPage(pagerState.currentPage + 1) }
                }
            },
        )
    }
}

@Composable
private fun TutorialPage(icon: ImageVector, title: String, body: String) {
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        TutorialIconBadge(icon)
        Text(
            title,
            style = MaterialTheme.typography.headlineSmall,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 24.dp),
        )
        Text(
            body,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 8.dp, start = 12.dp, end = 12.dp),
        )
    }
}

@Composable
private fun TutorialTabsPage() {
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            stringResource(R.string.tutorial_tabs_title),
            style = MaterialTheme.typography.headlineSmall,
            textAlign = TextAlign.Center,
        )
        Text(
            stringResource(R.string.tutorial_tabs_body),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 8.dp, start = 12.dp, end = 12.dp, bottom = 24.dp),
        )
        tutorialTabs.forEachIndexed { index, tab ->
            Appear(index = index) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp, horizontal = 24.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    TutorialIconBadge(tab.icon, size = 40.dp)
                    Text(
                        stringResource(tab.labelRes),
                        style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.padding(start = 16.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun TutorialIconBadge(icon: ImageVector, size: androidx.compose.ui.unit.Dp = 88.dp) {
    Box(
        modifier = Modifier
            .size(size)
            .clip(CircleShape)
            .background(accentGlow(MaterialTheme.colorScheme.primary)),
        contentAlignment = Alignment.Center,
    ) {
        androidx.compose.material3.Icon(
            icon,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(size * 0.45f),
        )
    }
}
