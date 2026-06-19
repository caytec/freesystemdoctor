package com.freeandroiddoctor.android.ui.privacy

import android.app.Application
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.freeandroiddoctor.android.R
import com.freeandroiddoctor.android.core.di.ServiceLocator
import com.freeandroiddoctor.android.core.util.ByteFormatter
import com.freeandroiddoctor.android.engine.privacy.BrowserDataEntry
import com.freeandroiddoctor.android.ui.components.SectionHeader
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class BrowserDataViewModel(app: Application) : AndroidViewModel(app) {
    private val engine = ServiceLocator.browserDataEngine
    private val _entries = MutableStateFlow<List<BrowserDataEntry>>(emptyList())
    val entries: StateFlow<List<BrowserDataEntry>> = _entries.asStateFlow()

    fun refresh() {
        viewModelScope.launch { _entries.value = engine.scan() }
    }
}

@Composable
fun BrowserDataScreen(viewModel: BrowserDataViewModel = viewModel()) {
    LaunchedEffect(Unit) { viewModel.refresh() }
    val entries by viewModel.entries.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val engine = ServiceLocator.browserDataEngine

    LazyColumn(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        contentPadding = PaddingValues(vertical = 12.dp),
    ) {
        item { SectionHeader(text = stringResource(R.string.browser_data_header)) }
        if (entries.isEmpty()) {
            item {
                Text(
                    text = stringResource(R.string.browser_data_empty),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        items(entries, key = { it.packageName }) { entry ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
                shape = MaterialTheme.shapes.medium,
            ) {
                Row(
                    modifier = Modifier.padding(14.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(entry.label, style = MaterialTheme.typography.bodyLarge)
                        Text(
                            text = stringResource(
                                R.string.browser_data_size,
                                ByteFormatter.format(entry.cacheBytes),
                                ByteFormatter.format(entry.dataBytes),
                            ),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    Button(onClick = { context.startActivity(engine.appInfoIntent(entry.packageName)) }) {
                        Text(stringResource(R.string.browser_data_clear))
                    }
                }
            }
        }
    }
}
