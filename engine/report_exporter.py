"""Report Exporter — generate HTML/PDF optimization reports."""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_PDF_AVAILABLE = False
try:
    import pypdf
    _PDF_AVAILABLE = True
except ImportError:
    pass


def generate_report(sections: list[dict], output_path: str = "") -> str:
    """Generate an HTML report from scan results.
    sections: list of {title, items: [{label, value, status}]}
    Returns path to saved file."""

    if not output_path:
        desktop = Path(os.environ.get("USERPROFILE", "~")) / "Desktop"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(desktop / f"FreeSystemDoctor_Report_{ts}.html")

    system_info = _get_system_info()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>FreeSystemDoctor Report</title>
<style>
  body {{ font-family: Segoe UI, Arial, sans-serif; background: #f4f6fb; color: #222; margin: 0; padding: 20px; }}
  .header {{ background: #1e2d4a; color: white; padding: 24px 32px; border-radius: 8px; margin-bottom: 20px; }}
  .header h1 {{ margin: 0; font-size: 24px; }}
  .header p {{ margin: 4px 0 0; color: #8a93b0; font-size: 13px; }}
  .sysinfo {{ display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap; }}
  .sysinfo-item {{ background: white; border-radius: 6px; padding: 12px 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
  .sysinfo-item .val {{ font-size: 20px; font-weight: bold; color: #4f7ef8; }}
  .sysinfo-item .lbl {{ font-size: 11px; color: #888; margin-top: 2px; }}
  .section {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
  .section h2 {{ margin: 0 0 12px; font-size: 16px; color: #1e2d4a; border-bottom: 2px solid #e8eaf0; padding-bottom: 8px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #f4f6fb; text-align: left; padding: 8px 12px; font-size: 12px; color: #666; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #f0f0f0; font-size: 13px; }}
  .ok {{ color: #2db37a; font-weight: bold; }}
  .warn {{ color: #e8900a; font-weight: bold; }}
  .danger {{ color: #d94040; font-weight: bold; }}
  .footer {{ text-align: center; color: #aaa; font-size: 12px; margin-top: 20px; }}
</style>
</head>
<body>
<div class="header">
  <h1>FreeSystemDoctor — System Report</h1>
  <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
</div>

<div class="sysinfo">
  <div class="sysinfo-item"><div class="val">{system_info.get('cpu_pct', '--')}%</div><div class="lbl">CPU Usage</div></div>
  <div class="sysinfo-item"><div class="val">{system_info.get('ram_pct', '--')}%</div><div class="lbl">RAM Usage</div></div>
  <div class="sysinfo-item"><div class="val">{system_info.get('disk_pct', '--')}%</div><div class="lbl">Disk C: Used</div></div>
  <div class="sysinfo-item"><div class="val">{system_info.get('uptime', '--')}</div><div class="lbl">Uptime</div></div>
</div>
"""

    for section in sections:
        html += f'<div class="section"><h2>{section["title"]}</h2>\n'
        items = section.get("items", [])
        if items:
            html += '<table><tr><th>Item</th><th>Value</th><th>Status</th></tr>\n'
            for item in items:
                status = item.get("status", "")
                cls = "ok" if status == "ok" else "warn" if status == "warn" else "danger" if status == "danger" else ""
                html += f'<tr><td>{item.get("label","")}</td><td>{item.get("value","")}</td><td class="{cls}">{status.upper() if status else ""}</td></tr>\n'
            html += '</table>\n'
        else:
            html += '<p style="color:#aaa">No data</p>\n'
        html += '</div>\n'

    html += f'<div class="footer">FreeSystemDoctor &mdash; Generated {datetime.now().strftime("%Y-%m-%d %H:%M")}</div></body></html>'

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def generate_quick_report(output_path: str = "") -> str:
    """Generate a report from current system state."""
    sections = []

    # Health section
    try:
        from engine import health_check
        scores = health_check.get_health_scores()
        sections.append({
            "title": "Health Scores",
            "items": [
                {"label": "Privacy", "value": f"{scores.get('privacy_score',0)}/100", "status": "ok" if scores.get("privacy_score",0) >= 80 else "warn"},
                {"label": "Speed", "value": f"{scores.get('speed_score',0)}/100", "status": "ok" if scores.get("speed_score",0) >= 80 else "warn"},
                {"label": "Security", "value": f"{scores.get('security_score',0)}/100", "status": "ok" if scores.get("security_score",0) >= 80 else "warn"},
                {"label": "Space", "value": f"{scores.get('space_score',0)}/100", "status": "ok" if scores.get("space_score",0) >= 80 else "warn"},
            ]
        })
    except Exception:
        pass

    # Disk section
    try:
        from engine import disk_cleaner
        items = disk_cleaner.scan_junk()
        total = sum(i.size for i in items)
        sections.append({
            "title": "Disk Cleaner",
            "items": [{"label": "Junk files found", "value": f"{len(items)} files ({_fmt_bytes(total)})",
                       "status": "warn" if total > 100*1024*1024 else "ok"}]
        })
    except Exception:
        pass

    # Startup section
    try:
        from engine import startup_manager
        entries = startup_manager.get_startup_entries_with_impact()
        high = [e for e in entries if e.impact == "High" and e.enabled]
        sections.append({
            "title": "Startup Programs",
            "items": [
                {"label": "Total startup programs", "value": str(len(entries)), "status": "warn" if len(entries) > 10 else "ok"},
                {"label": "High impact programs", "value": str(len(high)), "status": "warn" if high else "ok"},
            ] + [{"label": e.name, "value": "High Impact", "status": "warn"} for e in high[:5]]
        })
    except Exception:
        pass

    return generate_report(sections, output_path)


def _get_system_info() -> dict:
    info = {}
    if _PSUTIL:
        try:
            info["cpu_pct"] = f"{psutil.cpu_percent(interval=0.3):.0f}"
            mem = psutil.virtual_memory()
            info["ram_pct"] = f"{mem.percent:.0f}"
            disk = psutil.disk_usage("C:\\")
            info["disk_pct"] = f"{disk.percent:.0f}"
            boot = psutil.boot_time()
            from datetime import datetime
            uptime = datetime.now() - datetime.fromtimestamp(boot)
            days = uptime.days
            hours = uptime.seconds // 3600
            info["uptime"] = f"{days}d {hours}h"
        except Exception:
            pass
    return info


def _fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} GB"


def export_to_pdf(html_path: str, pdf_path: str = "") -> str:
    """Convert HTML report to PDF using external tool."""
    if not pdf_path:
        desktop = Path(os.environ.get("USERPROFILE", "~")) / "Desktop"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = str(desktop / f"FreeSystemDoctor_Report_{ts}.pdf")

    try:
        # Try using wkhtmltopdf if available
        result = subprocess.run(
            ["wkhtmltopdf", html_path, pdf_path],
            capture_output=True,
            timeout=30
        )
        if result.returncode == 0:
            return pdf_path
    except Exception:
        pass

    # Fallback: just copy HTML as-is (browser can print to PDF)
    if Path(html_path).exists():
        import shutil
        pdf_path_alt = pdf_path.replace(".pdf", ".html")
        shutil.copy(html_path, pdf_path_alt)
        return pdf_path_alt

    return ""


def generate_report_with_charts(sections: list[dict], output_format: str = "html", output_path: str = "") -> str:
    """Generate report with embedded charts in HTML/PDF.
    output_format: 'html' or 'pdf'"""

    if not output_path:
        desktop = Path(os.environ.get("USERPROFILE", "~")) / "Desktop"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = ".pdf" if output_format == "pdf" else ".html"
        output_path = str(desktop / f"FreeSystemDoctor_Report_{ts}{ext}")

    system_info = _get_system_info()

    # Generate HTML with embedded SVG charts
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>FreeSystemDoctor Report</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
<style>
  body {{ font-family: Segoe UI, Arial, sans-serif; background: #f4f6fb; color: #222; margin: 0; padding: 20px; }}
  .header {{ background: linear-gradient(135deg, #1e2d4a 0%, #2a3f5f 100%); color: white; padding: 24px 32px; border-radius: 8px; margin-bottom: 20px; }}
  .header h1 {{ margin: 0; font-size: 28px; }}
  .header p {{ margin: 4px 0 0; color: #a0afc0; font-size: 13px; }}
  .sysinfo {{ display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap; }}
  .sysinfo-item {{ background: white; border-radius: 6px; padding: 16px 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); min-width: 150px; text-align: center; }}
  .sysinfo-item .val {{ font-size: 28px; font-weight: bold; color: #0078d4; }}
  .sysinfo-item .lbl {{ font-size: 12px; color: #666; margin-top: 6px; }}
  .section {{ background: white; border-radius: 8px; padding: 24px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
  .section h2 {{ margin: 0 0 16px; font-size: 18px; color: #1e2d4a; border-bottom: 3px solid #0078d4; padding-bottom: 12px; }}
  .chart-container {{ position: relative; height: 300px; margin: 20px 0; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #f8f9fa; text-align: left; padding: 12px; font-size: 12px; color: #555; font-weight: 600; }}
  td {{ padding: 12px; border-bottom: 1px solid #e8e8e8; font-size: 13px; }}
  tr:hover {{ background: #f9f9f9; }}
  .ok {{ color: #28a745; font-weight: 600; }}
  .warn {{ color: #ffc107; font-weight: 600; }}
  .danger {{ color: #dc3545; font-weight: 600; }}
  .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 32px; padding-top: 16px; border-top: 1px solid #e8e8e8; }}
  @media print {{ body {{ background: white; }} .sysinfo-item {{ box-shadow: none; border: 1px solid #ddd; }} .section {{ box-shadow: none; border: 1px solid #ddd; }} }}
</style>
</head>
<body>
<div class="header">
  <h1>FreeSystemDoctor — Comprehensive System Report</h1>
  <p>Generated: {datetime.now().strftime("%A, %B %d, %Y at %H:%M:%S")}</p>
</div>

<div class="sysinfo">
  <div class="sysinfo-item"><div class="val">{system_info.get('cpu_pct', '--')}%</div><div class="lbl">CPU Usage</div></div>
  <div class="sysinfo-item"><div class="val">{system_info.get('ram_pct', '--')}%</div><div class="lbl">RAM Usage</div></div>
  <div class="sysinfo-item"><div class="val">{system_info.get('disk_pct', '--')}%</div><div class="lbl">Disk Used</div></div>
  <div class="sysinfo-item"><div class="val">{system_info.get('uptime', '--')}</div><div class="lbl">System Uptime</div></div>
</div>
"""

    for i, section in enumerate(sections):
        html += f'<div class="section"><h2>{section["title"]}</h2>\n'
        items = section.get("items", [])

        if items:
            # Add simple chart for numeric data
            numeric_values = []
            labels = []
            for item in items:
                try:
                    val = float(str(item.get("value", "0")).split()[0])
                    numeric_values.append(val)
                    labels.append(item.get("label", "")[:20])
                except ValueError:
                    pass

            if numeric_values and len(numeric_values) > 1:
                chart_id = f"chart_{i}"
                html += f'''<div class="chart-container">
                  <canvas id="{chart_id}"></canvas>
                </div>
                <script>
                  new Chart(document.getElementById("{chart_id}"), {{
                    type: "bar",
                    data: {{
                      labels: {json.dumps(labels)},
                      datasets: [{{
                        label: "{section.get('title', 'Data')}",
                        data: {json.dumps(numeric_values)},
                        backgroundColor: "rgba(0, 120, 212, 0.6)",
                        borderColor: "rgba(0, 120, 212, 1)",
                        borderWidth: 1
                      }}]
                    }},
                    options: {{ responsive: true, maintainAspectRatio: false }}
                  }});
                </script>
                '''

            html += '<table><tr><th>Item</th><th>Value</th><th>Status</th></tr>\n'
            for item in items:
                status = item.get("status", "")
                cls = "ok" if status == "ok" else "warn" if status == "warn" else "danger" if status == "danger" else ""
                html += f'<tr><td><strong>{item.get("label","")}</strong></td><td>{item.get("value","")}</td><td class="{cls}">{status.upper() if status else "—"}</td></tr>\n'
            html += '</table>\n'
        else:
            html += '<p style="color:#999; font-style:italic;">No data available</p>\n'

        html += '</div>\n'

    html += f'''<div class="footer">
    <p>FreeSystemDoctor — System Optimization & Maintenance Suite</p>
    <p>Report generated on {datetime.now().strftime("%Y-%m-%d at %H:%M:%S")}</p>
    </div>
</body></html>'''

    # Save as HTML
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Convert to PDF if requested
    if output_format == "pdf":
        pdf_path = output_path.replace(".html", ".pdf")
        pdf_result = export_to_pdf(output_path, pdf_path)
        if pdf_result:
            return pdf_result

    return output_path
