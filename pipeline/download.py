"""Download the six monthly Uber pickup files from FiveThirtyEight's public repository."""

import logging
import shutil
import urllib.request
from pathlib import Path

from pipeline.config import RAW_DIR, SOURCE_FILES, SOURCE_URL

log = logging.getLogger(__name__)

EXPECTED_HEADER = '"Date/Time","Lat","Lon","Base"'


def download(raw_dir: Path = RAW_DIR, timeout: float = 120) -> list[Path]:
    """Fetch any source file not already in raw_dir. Returns the paths of all six files.

    Each file is written to a .part file first and only renamed once complete and its header
    checks out, so an interrupted download never leaves a truncated CSV behind.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in SOURCE_FILES:
        target = raw_dir / name
        paths.append(target)
        if target.exists():
            log.info("%s already present", name)
            continue

        partial = target.with_suffix(".part")
        log.info("downloading %s", name)
        with urllib.request.urlopen(SOURCE_URL.format(name=name), timeout=timeout) as resp:
            with partial.open("wb") as fh:
                shutil.copyfileobj(resp, fh)

        with partial.open(encoding="utf-8") as fh:
            header = fh.readline().strip()
        if header != EXPECTED_HEADER:
            partial.unlink()
            raise ValueError(f"{name}: unexpected header {header!r}")
        partial.rename(target)
    return paths


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    download()
