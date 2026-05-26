"""FreeSystemDoctor release publisher — automated multi-channel distribution.

Channels:
  Fully automated (API):
    - GitHub Releases       (gh CLI)
    - winget-pkgs PR        (manifest + gh PR)
    - Chocolatey            (choco pack/push if installed)
    - Scoop bucket          (JSON manifest in your bucket repo)
    - SourceForge           (FRS via SCP/REST)

  Browser-assisted (form pre-fill):
    - Softpedia, Softonic, FileHippo, MajorGeeks, FilePlanet, FileHorse
    - Polish: dobreprogramy.pl, instalki.pl, programy.komputerswiat.pl
    - AlternativeTo, Portable Apps
"""

from .config import RELEASE_CONFIG, get_version, get_repo
from .directory import SUBMISSION_TARGETS, get_target, list_targets
from .release_builder import build_release_artifacts
from .orchestrator import publish_all, publish_to
