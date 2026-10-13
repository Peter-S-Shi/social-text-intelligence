"""Two-phase release gate: a private candidate, a checked draft, a verified public page.

An immutable GitHub release cannot be edited after publication, and its public
page exists only after it is published. So the gate splits the evidence:

1. `candidate` turns a private installer receipt into a sanitized manifest.
2. `render` fills the release body template. It refuses while any placeholder
   is unfilled, and needs the Owner's version and tag decisions.
3. `verify --phase draft` compares the unpublished draft (assets, body, source
   link) with the plan. Passing proves the draft is ready; it proves nothing
   public, and never produces a closure.
4. After the Owner approves and publishes, `verify --phase public` fetches the
   public API and page without credentials and repeats the checks, plus the
   immutable flag and the untouched source release. Only this phase can report
   `b1_operational_closure`.

Nothing here grants distribution permission, and no record is evidence on its
own: the receipts hold the digests of the live responses they came from.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from compliance import SH_RELEASE_URL, SH_SCHEMA_1, digest

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "distribution" / "release-source-page.md"
REPO = "Peter-S-Shi/social-text-intelligence"
SOURCE_TAG = "sources-qt-6.11.2"
TAG = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
PLACEHOLDER = re.compile(r"\{\{[A-Z0-9_]+\}\}")
SHA = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")
Fetch = Callable[[], dict[str, object]]
# Resolves a tag name through Git itself to a commit SHA, or None if it is absent.
TagCommit = Callable[[str], str | None]
MAX_TAG_DEPTH = 5
CRLF, LF = chr(13) + chr(10), chr(10)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def candidate_manifest(
    receipt: dict[str, object], installer: Path
) -> dict[str, object]:
    """A sanitized description of the private installer; no path leaves the host."""
    if (
        receipt.get("release_candidate") is not True
        or receipt.get("profile") != "candidate"
        or receipt.get("compiled") is not True
    ):
        raise ValueError("A compiled release-candidate receipt is required.")
    if (
        receipt.get("published") is not False
        or receipt.get("distribution_permitted") is not False
    ):
        raise ValueError(
            "The receipt must record an unpublished installer without permission."
        )
    if (
        receipt.get("legal_blockers") != ["B1"]
        or receipt.get("other_packet_blockers") != []
    ):
        raise ValueError("A release candidate may carry only blocker B1.")
    name = receipt.get("installer_filename")
    version = receipt.get("version")
    if not isinstance(name, str) or installer.name != name or not installer.is_file():
        raise ValueError("The installer must be the file the receipt names.")
    if installer.is_symlink():
        raise ValueError("The installer cannot be a link.")
    size = installer.stat().st_size
    sha = digest(installer)
    if size != receipt.get("installer_bytes") or sha != receipt.get("installer_sha256"):
        raise ValueError("The installer does not match its receipt.")
    revision = receipt.get("frozen_application_sha")
    if not isinstance(revision, str) or SHA.fullmatch(revision) is None:
        raise ValueError("The receipt must name the application revision.")
    if not isinstance(version, str) or name != f"STI-{version}-x64-setup.exe":
        raise ValueError("The installer name must follow the application version.")
    return {
        "schema_version": 1,
        "kind": "release-candidate",
        "status": "awaiting-owner-decisions",
        "version": version,
        "application_sha": revision,
        "installer": {"filename": name, "bytes": size, "sha256": sha},
        "input_inventory_sha256": receipt.get("input_inventory_sha256"),
        "legal_blockers": ["B1"],
        "distribution_permitted": False,
        "published": False,
        "source_release": {
            "url": SH_RELEASE_URL,
            "tag": SOURCE_TAG,
            "target_commit": SH_SCHEMA_1["release"]["target_commit"],  # type: ignore[index]
            "assets": SH_SCHEMA_1["assets"],
        },
        "owner_decisions_pending": ["application version", "application tag"],
    }


def render_body(manifest: dict[str, object], version: str, tag: str) -> str:
    """The release body, only from the Owner's decisions and a complete template."""
    if version != manifest["version"]:
        raise ValueError(
            "The version must equal the candidate's; rebuild to change it."
        )
    if TAG.fullmatch(tag) is None or tag.startswith("sources-") or tag == SOURCE_TAG:
        raise ValueError(
            "The application tag is malformed or collides with the source tag."
        )
    template = TEMPLATE.read_text(encoding="utf-8").split("## Page content\n", 1)[1]
    installer = manifest["installer"]
    assert isinstance(installer, dict)
    values = {
        "RELEASE_VERSION": version,
        "INSTALLER_FILENAME": installer["filename"],
        "INSTALLER_BYTES": f"{installer['bytes']:,}",
        "INSTALLER_SHA256": installer["sha256"],
        "RELEASE_TAG": tag,
    }
    body = "\n".join(
        line[2:] if line.startswith("> ") else "" if line == ">" else line
        for line in template.strip().splitlines()
    )
    for key, value in values.items():
        body = body.replace("{{" + key + "}}", str(value))
    if PLACEHOLDER.search(body):
        raise ValueError("The release body still has unfilled placeholders.")
    return body.rstrip() + "\n"


def plan(manifest: dict[str, object], version: str, tag: str) -> dict[str, object]:
    body = render_body(manifest, version, tag)
    installer = manifest["installer"]
    assert isinstance(installer, dict)
    return {
        "tag": tag,
        "target_commit": manifest["application_sha"],
        "body_sha256": sha256_text(body),
        "assets": {
            installer["filename"]: {
                "bytes": installer["bytes"],
                "sha256": installer["sha256"],
            }
        },
        "source_url": SH_RELEASE_URL,
    }


def normalize(api: dict[str, object]) -> dict[str, object]:
    """The few fields the checks use, from a GitHub release API response."""
    assets = api.get("assets")
    return {
        "draft": api.get("draft"),
        "prerelease": api.get("prerelease"),
        "immutable": api.get("immutable"),
        "tag": api.get("tag_name"),
        "target": api.get("target_commitish"),
        "body": api.get("body") or "",
        "assets": {
            str(a.get("name")): {"bytes": a.get("size"), "digest": a.get("digest")}
            for a in (assets if isinstance(assets, list) else [])
            if isinstance(a, dict)
        },
    }


def release_checks(
    state: dict[str, object], expected: dict[str, object], phase: str
) -> dict[str, bool]:
    """Each named check is true or false; nothing is inferred from a missing field."""
    body = state["body"]
    assets = state["assets"]
    assert isinstance(assets, dict)
    wanted = expected["assets"]
    assert isinstance(wanted, dict)
    checks = {
        "state_matches_phase": state["draft"] is (phase == "draft"),
        "tag": state["tag"] == expected["tag"],
        "target_is_candidate_revision": state["target"] == expected["target_commit"],
        "not_prerelease": state["prerelease"] is False,
        "body_is_planned_body": isinstance(body, str)
        and sha256_text(body.replace(CRLF, LF)) == expected["body_sha256"],
        "body_links_source_release": isinstance(body, str)
        and str(expected["source_url"]) in body,
        "only_planned_assets": set(assets) == set(wanted),
        "asset_digests": all(
            name in assets
            and assets[name]["digest"] == "sha256:" + str(item["sha256"])  # type: ignore[index]
            and assets[name]["bytes"] == item["bytes"]  # type: ignore[index]
            for name, item in wanted.items()
        ),
    }
    if phase == "public":
        checks["immutable"] = state["immutable"] is True
    return checks


def source_release_checks(state: dict[str, object]) -> dict[str, bool]:
    """The published source release must still be the one SOURCE_HOSTING.json pins."""
    release = SH_SCHEMA_1["release"]
    assert isinstance(release, dict)
    assets = state["assets"]
    assert isinstance(assets, dict)
    pinned = SH_SCHEMA_1["assets"]
    assert isinstance(pinned, dict)
    return {
        "source_release_public": state["draft"] is False,
        "source_release_immutable": state["immutable"] is True,
        "source_release_tag": state["tag"] == release["tag"],
        "source_release_target": state["target"] == release["target_commit"],
        "source_release_assets": {name: item["digest"] for name, item in assets.items()}
        == {name: "sha256:" + str(value) for name, value in pinned.items()},
    }


def resolve_tag(get: Callable[[str], dict[str, object] | None], tag: str) -> str | None:
    """The commit a tag really points to, from the Git refs API.

    A release's `target_commitish` says nothing once the tag exists, because
    GitHub ignores it then. An annotated tag is followed to its commit; any
    other target type, a loop or a too-deep chain is refused.
    """
    ref = get(f"git/ref/tags/{tag}")
    if ref is None:
        return None
    for _ in range(MAX_TAG_DEPTH):
        target = ref.get("object")
        if not isinstance(target, dict):
            raise ValueError("The tag reference is malformed.")
        kind, sha = target.get("type"), target.get("sha")
        if not isinstance(sha, str) or SHA.fullmatch(sha) is None:
            raise ValueError("The tag reference is malformed.")
        if kind == "commit":
            return sha
        if kind != "tag":
            raise ValueError("The tag does not point to a commit.")
        followed = get(f"git/tags/{sha}")
        if followed is None:
            raise ValueError("An annotated tag object is missing.")
        ref = followed
    raise ValueError("The tag chain is too deep.")


def verify(
    manifest: dict[str, object],
    version: str,
    tag: str,
    phase: str,
    release: Fetch,
    tag_commit: TagCommit,
    source: Fetch | None = None,
    page: Callable[[], str] | None = None,
) -> dict[str, object]:
    """Run one phase. Only the public phase can report operational closure.

    `tag_commit` resolves a tag through Git refs, not through the release
    response. A draft may have no tag yet, so its planned target is checked;
    a tag that already exists must point to the expected commit, and the
    public phase requires the tag to exist and to point there.
    """
    if phase not in ("draft", "public"):
        raise ValueError("The phase must be draft or public.")
    expected = plan(manifest, version, tag)
    api = release()
    checks = release_checks(normalize(api), expected, phase)
    digests = {"release_api_sha256": sha256_text(json.dumps(api, sort_keys=True))}
    resolved = tag_commit(tag)
    expected_commit = expected["target_commit"]
    checks["tag_points_to_candidate_revision"] = (
        resolved == expected_commit
        if phase == "public"
        else resolved in (None, expected_commit)
    )
    resolved_tags: dict[str, str | None] = {"application": resolved}
    if phase == "public":
        if source is None or page is None:
            raise ValueError("The public phase needs the source release and the page.")
        source_api = source()
        checks.update(source_release_checks(normalize(source_api)))
        release_pin = SH_SCHEMA_1["release"]
        assert isinstance(release_pin, dict)
        source_resolved = tag_commit(SOURCE_TAG)
        checks["source_tag_points_to_pinned_commit"] = (
            source_resolved == release_pin["target_commit"]
        )
        resolved_tags["source"] = source_resolved
        html = page()
        checks["page_links_source_release"] = SH_RELEASE_URL in html
        digests["source_release_api_sha256"] = sha256_text(
            json.dumps(source_api, sort_keys=True)
        )
        digests["page_sha256"] = sha256_text(html)
    passed = all(checks.values())
    return {
        "schema_version": 1,
        "kind": "release-gate-receipt",
        "phase": phase,
        "version": version,
        "tag": tag,
        "installer_sha256": manifest["installer"]["sha256"],  # type: ignore[index]
        "plan_sha256": sha256_text(json.dumps(expected, sort_keys=True)),
        "checks": checks,
        "all_checks_passed": passed,
        "response_digests": digests,
        "resolved_tag_commits": resolved_tags,
        # A draft proves readiness only. B1's operational prerequisite is met by
        # the public phase alone, and only for this release; the packet inside
        # the installer was fixed before publication and is not changed by it.
        "ready_for_owner_approval": phase == "draft" and passed,
        "b1_operational_closure": phase == "public" and passed,
        "distribution_permitted": False,
    }


def gh_draft(tag: str) -> Fetch:
    def fetch() -> dict[str, object]:
        out = subprocess.check_output(
            ["gh", "api", f"repos/{REPO}/releases", "--paginate"], text=True
        )
        found = [
            item
            for item in json.loads(out)
            if item.get("draft") is True and item.get("tag_name") == tag
        ]
        if len(found) != 1:
            raise ValueError("Exactly one draft with that tag is required.")
        return dict(found[0])

    return fetch


def public_get(url: str) -> bytes:
    """An unauthenticated GET; the public phase must not rely on credentials."""
    request = urllib.request.Request(url, headers={"User-Agent": "sti-release-gate"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data: bytes = response.read()
        return data


def git_get(path: str) -> dict[str, object] | None:
    """A Git API object from the public API, or None when GitHub says 404."""
    try:
        data = public_get(f"https://api.github.com/repos/{REPO}/{path}")
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    return dict(json.loads(data))


def git_tag_commit(tag: str) -> str | None:
    return resolve_tag(git_get, tag)


def public_release(tag: str) -> Fetch:
    return lambda: dict(
        json.loads(
            public_get(f"https://api.github.com/repos/{REPO}/releases/tags/{tag}")
        )
    )


def public_page(tag: str) -> Callable[[], str]:
    return lambda: public_get(f"https://github.com/{REPO}/releases/tag/{tag}").decode(
        "utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    cand = sub.add_parser("candidate")
    cand.add_argument("--receipt", type=Path, required=True)
    cand.add_argument("--installer", type=Path, required=True)
    cand.add_argument("--out", type=Path, required=True)
    for name in ("render", "verify"):
        item = sub.add_parser(name)
        item.add_argument("--manifest", type=Path, required=True)
        item.add_argument("--version", required=True)
        item.add_argument("--tag", required=True)
        item.add_argument("--out", type=Path, required=True)
    sub.choices["verify"].add_argument(
        "--phase", choices=["draft", "public"], required=True
    )
    args = parser.parse_args()
    try:
        if args.command == "candidate":
            receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
            manifest = candidate_manifest(receipt, args.installer)
            args.out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            print(
                json.dumps(
                    {"status": manifest["status"], "installer": manifest["installer"]}
                )
            )
            return 0
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        if args.command == "render":
            body = render_body(manifest, args.version, args.tag)
            args.out.write_text(body, encoding="utf-8", newline="\n")
            print(json.dumps({"body_sha256": sha256_text(body)}))
            return 0
        if args.phase == "draft":
            result = verify(
                manifest,
                args.version,
                args.tag,
                "draft",
                gh_draft(args.tag),
                git_tag_commit,
            )
        else:
            result = verify(
                manifest,
                args.version,
                args.tag,
                "public",
                public_release(args.tag),
                git_tag_commit,
                public_release(SOURCE_TAG),
                public_page(args.tag),
            )
        args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    key: result[key]
                    for key in ("phase", "all_checks_passed", "b1_operational_closure")
                }
            )
        )
        return 0 if result["all_checks_passed"] else 2
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        print(f"Release gate refused: {error}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
