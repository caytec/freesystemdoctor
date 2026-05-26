"""Directory of free software submission targets — APIs and manual.

Each entry describes one site with all metadata needed to either:
  - Programmatically publish (when api_class is set)
  - Open the submission form pre-filled with metadata (manual)

The submit_url field uses Python format() with these placeholders:
  {name}, {version}, {homepage}, {tags}, {summary}, {download_url}, {email}
"""

# Each target: (id, label, region, type, submit_url_or_api, notes)
SUBMISSION_TARGETS: list[dict] = [

    # ── 100% automated APIs ───────────────────────────────────────────────────
    {
        "id":         "github_releases",
        "label":      "GitHub Releases",
        "region":     "global",
        "type":       "api",
        "api_module": "github",
        "submit_url": "https://github.com/{owner}/{repo}/releases/new",
        "notes":      "Primary distribution channel. Uses gh CLI.",
        "auto":       True,
    },
    {
        "id":         "winget",
        "label":      "Winget (Microsoft)",
        "region":     "global",
        "type":       "api",
        "api_module": "winget",
        "submit_url": "https://github.com/microsoft/winget-pkgs",
        "notes":      "Generates manifest YAML and opens PR via gh fork.",
        "auto":       True,
    },
    {
        "id":         "chocolatey",
        "label":      "Chocolatey Community",
        "region":     "global",
        "type":       "api",
        "api_module": "chocolatey",
        "submit_url": "https://community.chocolatey.org/packages/upload",
        "notes":      "Requires choco installed and CHOCO_API_KEY env var.",
        "auto":       True,
    },
    {
        "id":         "scoop",
        "label":      "Scoop Bucket",
        "region":     "global",
        "type":       "api",
        "api_module": "scoop",
        "submit_url": "https://github.com/{owner}/scoop-bucket",
        "notes":      "Pushes JSON manifest to your bucket repo.",
        "auto":       True,
    },
    {
        "id":         "sourceforge",
        "label":      "SourceForge",
        "region":     "global",
        "type":       "api",
        "api_module": "sourceforge",
        "submit_url": "https://sourceforge.net/projects/{name}",
        "notes":      "FRS upload via SCP. Requires SF_USER + SF_API_KEY env.",
        "auto":       True,
    },

    # ── Browser-assist (no public API; opens form pre-filled) ────────────────
    {
        "id":         "softpedia",
        "label":      "Softpedia",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://www.softpedia.com/contact_form.php?subject=submit",
        "notes":      "Editorial review takes 1-7 days.",
        "auto":       False,
    },
    {
        "id":         "softonic",
        "label":      "Softonic",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://en.softonic.com/upload",
        "notes":      "Form-based submission.",
        "auto":       False,
    },
    {
        "id":         "filehippo",
        "label":      "FileHippo",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://filehippo.com/contact/?subject=software_submission",
        "notes":      "Email-based intake.",
        "auto":       False,
    },
    {
        "id":         "majorgeeks",
        "label":      "MajorGeeks",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://www.majorgeeks.com/page.php?id=12",
        "notes":      "Submit page for free software.",
        "auto":       False,
    },
    {
        "id":         "filehorse",
        "label":      "FileHorse",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://www.filehorse.com/contact/",
        "notes":      "Email submission.",
        "auto":       False,
    },
    {
        "id":         "filepuma",
        "label":      "FilePuma",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://www.filepuma.com/info/contact/",
        "notes":      "Contact form.",
        "auto":       False,
    },
    {
        "id":         "snapfiles",
        "label":      "Snapfiles",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://www.snapfiles.com/submit/",
        "notes":      "Web form.",
        "auto":       False,
    },
    {
        "id":         "techspot",
        "label":      "TechSpot Downloads",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://www.techspot.com/downloads/contribute.html",
        "notes":      "Contributor program.",
        "auto":       False,
    },
    {
        "id":         "ghacks",
        "label":      "gHacks Downloads",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://www.ghacks.net/contact/",
        "notes":      "Email tip line — they review and write articles.",
        "auto":       False,
    },
    {
        "id":         "alternativeto",
        "label":      "AlternativeTo",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://alternativeto.net/software/add/",
        "notes":      "Community-curated. Login required.",
        "auto":       False,
    },
    {
        "id":         "portableapps",
        "label":      "PortableApps.com",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://portableapps.com/node/add/forum/8",
        "notes":      "Forum submission for portable builds.",
        "auto":       False,
    },
    {
        "id":         "fosshub",
        "label":      "FossHub",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://www.fosshub.com/contact.html",
        "notes":      "Premium open-source mirror.",
        "auto":       False,
    },
    {
        "id":         "uptodown",
        "label":      "Uptodown",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://en.uptodown.com/windows/contact",
        "notes":      "Multi-language download portal.",
        "auto":       False,
    },
    {
        "id":         "filecluster",
        "label":      "FileCluster",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://www.filecluster.com/submit-software.html",
        "notes":      "Web form.",
        "auto":       False,
    },
    {
        "id":         "betanews",
        "label":      "BetaNews FileForum",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://fileforum.com/submit",
        "notes":      "BetaNews-affiliated.",
        "auto":       False,
    },
    {
        "id":         "windows10download",
        "label":      "Windows10Download",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://www.windows10download.com/submit/",
        "notes":      "Niche directory.",
        "auto":       False,
    },

    # ── Polish download portals ──────────────────────────────────────────────
    {
        "id":         "dobreprogramy",
        "label":      "dobreprogramy.pl",
        "region":     "poland",
        "type":       "manual",
        "submit_url": "https://www.dobreprogramy.pl/dodaj-program/",
        "notes":      "Największy polski portal z oprogramowaniem.",
        "auto":       False,
    },
    {
        "id":         "instalki",
        "label":      "instalki.pl",
        "region":     "poland",
        "type":       "manual",
        "submit_url": "https://www.instalki.pl/kontakt/",
        "notes":      "Drugi największy polski portal.",
        "auto":       False,
    },
    {
        "id":         "ks_programy",
        "label":      "Komputer Świat — Programy",
        "region":     "poland",
        "type":       "manual",
        "submit_url": "https://programy.komputerswiat.pl/kontakt",
        "notes":      "Oficjalny portal Komputer Świat.",
        "auto":       False,
    },
    {
        "id":         "chip_pl",
        "label":      "CHIP.pl",
        "region":     "poland",
        "type":       "manual",
        "submit_url": "https://www.chip.pl/kontakt",
        "notes":      "Portal CHIP Polska.",
        "auto":       False,
    },
    {
        "id":         "pliki_wp",
        "label":      "Pliki Wirtualna Polska",
        "region":     "poland",
        "type":       "manual",
        "submit_url": "https://pliki.wp.pl/kontakt",
        "notes":      "Sekcja oprogramowania WP.",
        "auto":       False,
    },
    {
        "id":         "pclab",
        "label":      "PCLab",
        "region":     "poland",
        "type":       "manual",
        "submit_url": "https://pclab.pl/kontakt",
        "notes":      "Portal PCLab.",
        "auto":       False,
    },
    {
        "id":         "pobieram",
        "label":      "pobieram.pl",
        "region":     "poland",
        "type":       "manual",
        "submit_url": "https://www.pobieram.pl/dodaj-program",
        "notes":      "Polski katalog programów.",
        "auto":       False,
    },

    # ── Reddit / Forums (announcement) ───────────────────────────────────────
    {
        "id":         "reddit_freesoft",
        "label":      "Reddit r/freesoftware",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://www.reddit.com/r/freesoftware/submit?title={name}+{version}+released&text={summary}+{homepage}",
        "notes":      "Community announcement.",
        "auto":       False,
    },
    {
        "id":         "reddit_windowsapps",
        "label":      "Reddit r/Windows",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://www.reddit.com/r/Windows/submit?title={name}+{version}+released",
        "notes":      "Windows community.",
        "auto":       False,
    },
    {
        "id":         "hn",
        "label":      "Hacker News",
        "region":     "global",
        "type":       "manual",
        "submit_url": "https://news.ycombinator.com/submitlink?u={homepage}&t={name}+v{version}",
        "notes":      "HN Show / Launch HN.",
        "auto":       False,
    },
]


def get_target(target_id: str) -> dict | None:
    for t in SUBMISSION_TARGETS:
        if t["id"] == target_id:
            return t
    return None


def list_targets(region: str = None, auto_only: bool = False) -> list[dict]:
    out = SUBMISSION_TARGETS
    if region:
        out = [t for t in out if t["region"] == region]
    if auto_only:
        out = [t for t in out if t.get("auto")]
    return out


def count_by_type() -> dict:
    counts = {"api": 0, "manual": 0, "global": 0, "poland": 0}
    for t in SUBMISSION_TARGETS:
        counts[t["type"]] = counts.get(t["type"], 0) + 1
        counts[t["region"]] = counts.get(t["region"], 0) + 1
    return counts
