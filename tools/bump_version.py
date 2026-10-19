"""Increase the patch version for unversioned first-parent commits on main."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = Path("az_it/__init__.py")
PATTERN = re.compile(r'^__version__ = "(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"$', re.MULTILINE)


def git(*args, root=ROOT):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def bump(root=ROOT):
    path = root / VERSION_FILE
    source = path.read_text(encoding="utf-8")
    match = PATTERN.search(source)
    if not match:
        raise ValueError("Expected a single semantic __version__ assignment")
    # The last change to the version file is the baseline, including manual releases.
    baseline = git("log", "--first-parent", "-1", "--format=%H", "--", VERSION_FILE.as_posix(), root=root)
    if not baseline:
        raise ValueError("Version file must have a committed baseline")
    count = int(git("rev-list", "--first-parent", "--count", f"{baseline}..HEAD", root=root))
    major, minor, patch = map(int, match.groups())
    version = f"{major}.{minor}.{patch + count}"
    if count:
        path.write_text(PATTERN.sub(f'__version__ = "{version}"', source), encoding="utf-8")
    print(f"{version} ({count} new commits)")
    return count


if __name__ == "__main__":
    bump()
