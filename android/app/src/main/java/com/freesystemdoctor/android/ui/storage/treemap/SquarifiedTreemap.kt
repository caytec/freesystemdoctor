package com.freesystemdoctor.android.ui.storage.treemap

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.input.pointer.pointerInput
import com.freesystemdoctor.android.core.util.ByteFormatter
import kotlin.math.max
import kotlin.math.min

data class TreemapNode(
    val label: String,
    val sizeBytes: Long,
    val children: List<TreemapNode> = emptyList(),
)

private data class PlacedRect(val node: TreemapNode, val rect: Rect)

/**
 * Squarified treemap. Standard algorithm — keeps rectangles as close to square as
 * possible by greedily picking the orientation that minimises max aspect ratio.
 * Renders into one Compose [Canvas]; tap inside a child rectangle invokes [onTap].
 */
@Composable
fun SquarifiedTreemap(
    root: TreemapNode,
    onTap: (TreemapNode) -> Unit,
    modifier: Modifier = Modifier,
) {
    val accent = MaterialTheme.colorScheme.primary
    val accentSoft = MaterialTheme.colorScheme.tertiary
    val outline = MaterialTheme.colorScheme.outline
    val onSurface = MaterialTheme.colorScheme.onSurface
    val placed = remember(root) { layout(root) }

    Canvas(
        modifier = modifier.fillMaxSize().pointerInput(root) {
            detectTapGestures { offset ->
                placed.firstOrNull { it.rect.contains(offset) }?.let { onTap(it.node) }
            }
        },
    ) {
        val sized = layoutFor(root, Size(size.width, size.height))
        val textPaint = android.graphics.Paint().apply {
            color = onSurface.toArgb()
            textSize = 28f
            isAntiAlias = true
        }
        sized.forEachIndexed { idx, p ->
            val fill = if (idx % 2 == 0) accent.copy(alpha = 0.35f) else accentSoft.copy(alpha = 0.35f)
            drawRect(color = fill, topLeft = p.rect.topLeft, size = p.rect.size)
            drawRect(color = outline, topLeft = p.rect.topLeft, size = p.rect.size, style = Stroke(width = 1.5f))
            if (p.rect.width > 90 && p.rect.height > 28) {
                drawContext.canvas.nativeCanvas.drawText(
                    "${p.node.label}  ${ByteFormatter.format(p.node.sizeBytes)}",
                    p.rect.left + 8,
                    p.rect.top + 22,
                    textPaint,
                )
            }
        }
    }
}

private fun layout(root: TreemapNode): List<PlacedRect> =
    layoutFor(root, Size(1f, 1f))

private fun layoutFor(root: TreemapNode, size: Size): List<PlacedRect> {
    val total = root.children.sumOf { it.sizeBytes }
    if (total <= 0 || root.children.isEmpty()) return emptyList()
    val area = size.width * size.height
    val scaled = root.children
        .filter { it.sizeBytes > 0 }
        .map { it to (it.sizeBytes.toDouble() / total * area) }
    return squarify(scaled, Rect(0f, 0f, size.width, size.height))
}

private fun squarify(
    items: List<Pair<TreemapNode, Double>>,
    rect: Rect,
): List<PlacedRect> {
    if (items.isEmpty()) return emptyList()
    val out = ArrayList<PlacedRect>()
    var remaining = items
    var current = rect
    while (remaining.isNotEmpty()) {
        val (row, rest) = takeRow(remaining, min(current.width, current.height).toDouble())
        out += placeRow(row, current)
        // Advance the rectangle for the leftover space.
        val rowSum = row.sumOf { it.second }
        val short = min(current.width, current.height)
        val long = if (short == 0f) 0f else (rowSum / short).toFloat()
        current = if (current.width >= current.height) {
            Rect(current.left + long, current.top, current.right, current.bottom)
        } else {
            Rect(current.left, current.top + long, current.right, current.bottom)
        }
        remaining = rest
        if (current.width <= 0f || current.height <= 0f) break
    }
    return out
}

private fun takeRow(
    items: List<Pair<TreemapNode, Double>>,
    short: Double,
): Pair<List<Pair<TreemapNode, Double>>, List<Pair<TreemapNode, Double>>> {
    if (items.isEmpty()) return emptyList<Pair<TreemapNode, Double>>() to emptyList()
    val row = ArrayList<Pair<TreemapNode, Double>>()
    var bestRatio = Double.MAX_VALUE
    for (i in items.indices) {
        val candidate = row + items[i]
        val ratio = worstRatio(candidate, short)
        if (ratio > bestRatio) return row to items.drop(i)
        row.clear()
        row.addAll(candidate)
        bestRatio = ratio
    }
    return row to emptyList()
}

private fun worstRatio(row: List<Pair<TreemapNode, Double>>, short: Double): Double {
    if (row.isEmpty() || short <= 0.0) return Double.MAX_VALUE
    val sum = row.sumOf { it.second }
    val rMax = row.maxOf { it.second }
    val rMin = row.minOf { it.second }
    return max((short * short * rMax) / (sum * sum), (sum * sum) / (short * short * rMin))
}

private fun placeRow(
    row: List<Pair<TreemapNode, Double>>,
    rect: Rect,
): List<PlacedRect> {
    if (row.isEmpty()) return emptyList()
    val out = ArrayList<PlacedRect>()
    val rowSum = row.sumOf { it.second }
    val short = min(rect.width, rect.height)
    if (short <= 0f) return emptyList()
    val long = (rowSum / short).toFloat()
    if (rect.width >= rect.height) {
        var y = rect.top
        row.forEach { (node, area) ->
            val h = if (rowSum == 0.0) 0f else (area / rowSum).toFloat() * short
            out += PlacedRect(node, Rect(rect.left, y, rect.left + long, y + h))
            y += h
        }
    } else {
        var x = rect.left
        row.forEach { (node, area) ->
            val w = if (rowSum == 0.0) 0f else (area / rowSum).toFloat() * short
            out += PlacedRect(node, Rect(x, rect.top, x + w, rect.top + long))
            x += w
        }
    }
    return out
}

private fun Color.toArgb(): Int {
    val a = (alpha * 255).toInt() and 0xFF
    val r = (red * 255).toInt() and 0xFF
    val g = (green * 255).toInt() and 0xFF
    val b = (blue * 255).toInt() and 0xFF
    return (a shl 24) or (r shl 16) or (g shl 8) or b
}
