"""Populate git mirrors and isolated dependency environments at image build time."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess


CONFIG = Path("/opt/crucible/config/repos.json")
REPOS = Path("/opt/repos")
VENVS = Path("/opt/venvs")
CHECKOUTS = Path("/opt/setup-checkouts")


def run(args: list[str], **kwargs: object) -> None:
    subprocess.run(args, check=True, **kwargs)


def slug(name: str) -> str:
    return name.replace("/", "--")


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    for repo in config["repos"]:
        if repo["status"] not in {"accepted", "probe"}:
            continue
        name = slug(repo["repo"])
        mirror = REPOS / f"{name}.git"
        run(["git", "clone", "--mirror", repo["clone_url"], str(mirror)])
        for revision, commit in (("head", repo["head_commit"]), ("old", repo["old_commit"])):
            checkout = CHECKOUTS / f"{name}--{revision}"
            venv = VENVS / f"{name}--{revision}"
            run(["git", "clone", str(mirror), str(checkout)])
            run(["git", "-C", str(checkout), "checkout", "--detach", commit])
            run(["python", "-m", "venv", str(venv)])
            python = str(venv / "bin/python")
            lock = Path("/opt/crucible/config/locks") / f"{name}--{revision}.txt"
            run([python, "-m", "pip", "install", "--requirement", str(lock)])
            run([python, "-m", "pip", "install", "--no-deps", "--no-build-isolation", "-e", str(checkout)])
            freeze = subprocess.run(
                [python, "-m", "pip", "freeze", "--all"],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout
            (venv / "requirements.freeze.txt").write_text(freeze, encoding="utf-8")
            shutil.rmtree(checkout)


if __name__ == "__main__":
    main()
