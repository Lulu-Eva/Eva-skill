#!/usr/bin/env python3
"""Temporary-directory integration checks for the managed Eva-skill installer."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "eva_global_install.py"
MANAGED_DIRECTORIES = (
    "eva",
    "eva-new-user",
    "eva-think",
    "eva-create",
    "eva-learn",
    "eva-brief",
    "eva-link",
    "eva-review",
    "eva-lens",
    "eva-shared",
)
OFFICIAL_GUIDE_HEADLINE = "关注公众号“璐璐 Eva” —— Eva-skill 的官方使用指南与案例库。"


def fail(message: str) -> None:
    raise AssertionError(message)


def run_json(
    command: str,
    source_root: Path,
    target_root: Path,
    state_file: Path,
    transactions_root: Path,
    backups_root: Path,
    *extra: str,
    expect_ok: bool = True,
) -> dict:
    base = [
        sys.executable,
        str(INSTALLER),
        command,
        "--json",
        "--source-root",
        str(source_root),
        "--target-root",
        str(target_root),
    ]
    if command in {"install", "recover"}:
        base.extend(
            [
                "--state-file",
                str(state_file),
                "--transactions-root",
                str(transactions_root),
                "--backups-root",
                str(backups_root),
            ]
        )
    if command == "verify":
        base.extend(
            [
                "--transactions-root",
                str(transactions_root),
                "--backups-root",
                str(backups_root),
            ]
        )
    process = subprocess.run(
        [*base, *extra],
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        payload = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        fail(f"{command} did not emit JSON: {process.stdout!r} / {process.stderr!r}; {exc}")
    if expect_ok and process.returncode != 0:
        fail(f"{command} failed unexpectedly: {payload}")
    if not expect_ok and process.returncode == 0:
        fail(f"{command} unexpectedly succeeded: {payload}")
    return payload


def acknowledge(state_file: Path, notice_id: str) -> dict:
    process = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            "ack",
            "--json",
            "--state-file",
            str(state_file),
            "--notice-id",
            notice_id,
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        payload = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        fail(f"ack did not emit JSON: {process.stdout!r} / {process.stderr!r}; {exc}")
    if process.returncode != 0:
        fail(f"ack failed unexpectedly: {payload}")
    return payload


def run_normal_force_install(
    source_root: Path,
    target_root: Path,
    state_file: Path,
    transactions_root: Path,
    backups_root: Path,
) -> str:
    process = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            "install",
            "--source-root",
            str(source_root),
            "--target-root",
            str(target_root),
            "--state-file",
            str(state_file),
            "--transactions-root",
            str(transactions_root),
            "--backups-root",
            str(backups_root),
            "--force",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        fail(f"normal force install failed: {process.stdout!r} / {process.stderr!r}")
    return process.stdout


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        if path.is_symlink():
            digest.update(b"symlink")
            digest.update(str(path.readlink()).encode("utf-8"))
        elif path.is_file():
            digest.update(b"file")
            digest.update(path.read_bytes())
        elif path.is_dir():
            digest.update(b"dir")
    return digest.hexdigest()


def assert_real_bundle(target_root: Path) -> None:
    actual = tuple(sorted(path.name for path in target_root.iterdir() if path.name in MANAGED_DIRECTORIES))
    if actual != tuple(sorted(MANAGED_DIRECTORIES)):
        fail(f"managed directory set drifted: {actual}")
    for name in MANAGED_DIRECTORIES:
        directory = target_root / name
        skill_file = directory / "SKILL.md"
        if not directory.is_dir() or directory.is_symlink():
            fail(f"{name} was not installed as a real directory")
        if not skill_file.is_file() or skill_file.is_symlink():
            fail(f"{name} is missing a real top-level SKILL.md")


def create_interrupted_transaction(
    target_root: Path,
    state_file: Path,
    transactions_root: Path,
    backups_root: Path,
) -> str:
    transaction_id = "test-interrupted"
    transaction_root = transactions_root / transaction_id
    backup_root = backups_root / transaction_id
    transaction_root.mkdir(parents=True)
    backup_root.mkdir(parents=True)
    original = target_root / "eva"
    backup = backup_root / "eva"
    original.rename(backup)
    shutil.copytree(backup, original)
    (original / "interrupted-copy-must-disappear.txt").write_text("new", encoding="utf-8")
    previous_state_text = state_file.read_text(encoding="utf-8")
    previous_state_path = transaction_root / "previous-state.json"
    previous_state_path.write_text(previous_state_text, encoding="utf-8")
    interrupted_state = json.loads(previous_state_text)
    interrupted_state["installed_version"] = "9.9.9"
    interrupted_state["notice_pending"] = True
    interrupted_state["pending_notice"] = {
        "id": "interrupted-notice",
        "action": "updated",
        "version": "9.9.9",
    }
    state_file.write_text(
        json.dumps(interrupted_state, ensure_ascii=False),
        encoding="utf-8",
    )
    (transaction_root / "transaction.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "product_name": "Eva-skill",
                "transaction_id": transaction_id,
                "target_root": str(target_root),
                "backup_root": str(backup_root),
                "managed_directories": list(MANAGED_DIRECTORIES),
                "original_names": ["eva"],
                "original_entry_types": {"eva": "directory"},
                "backed_up_names": ["eva"],
                "backing_up_name": None,
                "restored_names": [],
                "restoring_name": None,
                "installed_names": ["eva"],
                "activating_name": None,
                "state_file": str(state_file),
                "previous_state": {
                    "existed": True,
                    "path": str(state_file),
                    "backup": str(previous_state_path),
                },
                "status": "postcheck",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return previous_state_text


def create_staged_transaction(
    target_root: Path,
    state_file: Path,
    transactions_root: Path,
    backups_root: Path,
    transaction_id: str = "test-staged",
) -> None:
    transaction_root = transactions_root / transaction_id
    backup_root = backups_root / transaction_id
    transaction_root.mkdir(parents=True)
    backup_root.mkdir(parents=True)
    previous_state_path = transaction_root / "previous-state.json"
    previous_state_path.write_text(state_file.read_text(encoding="utf-8"), encoding="utf-8")
    (transaction_root / "transaction.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "product_name": "Eva-skill",
                "transaction_id": transaction_id,
                "target_root": str(target_root),
                "backup_root": str(backup_root),
                "managed_directories": list(MANAGED_DIRECTORIES),
                "original_names": list(MANAGED_DIRECTORIES),
                "original_entry_types": {name: "directory" for name in MANAGED_DIRECTORIES},
                "backed_up_names": [],
                "backing_up_name": None,
                "restored_names": [],
                "restoring_name": None,
                "installed_names": [],
                "activating_name": None,
                "state_file": str(state_file),
                "previous_state": {
                    "existed": True,
                    "path": str(state_file),
                    "backup": str(previous_state_path),
                },
                "status": "staged",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def assert_staged_recovery_write_failure(
    target_root: Path,
    state_file: Path,
    transactions_root: Path,
    backups_root: Path,
) -> None:
    transaction_id = "test-staged-save-failure"
    create_staged_transaction(
        target_root,
        state_file,
        transactions_root,
        backups_root,
        transaction_id,
    )
    spec = importlib.util.spec_from_file_location("eva_global_install_failure_test", INSTALLER)
    if spec is None or spec.loader is None:
        fail("could not load installer module for failure injection")
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)

    def reject_journal_write(_transaction_root: Path, _payload: dict) -> None:
        raise OSError("injected journal write failure")

    installer.save_journal = reject_journal_write
    try:
        installer.recover_pending_transactions(
            target_root,
            transactions_root,
            backups_root,
            expected_state_file=state_file,
            requested=True,
        )
    except installer.InstallError as exc:
        if "无法写入回滚事务状态" not in str(exc):
            fail(f"staged recovery surfaced the wrong write failure: {exc}")
    else:
        fail("staged recovery reported success after its journal write failed")

    journal = json.loads(
        (transactions_root / transaction_id / "transaction.json").read_text(encoding="utf-8")
    )
    if journal.get("status") != "staged":
        fail("failure injection did not preserve the on-disk staged journal fixture")


def create_postcheck_transaction(
    transaction_id: str,
    target_root: Path,
    state_file: Path,
    transactions_root: Path,
    backups_root: Path,
    *,
    restoring_name: str | None = None,
) -> None:
    transaction_root = transactions_root / transaction_id
    backup_root = backups_root / transaction_id
    transaction_root.mkdir(parents=True)
    backup_root.mkdir(parents=True)
    previous_state_path = transaction_root / "previous-state.json"
    previous_state_path.write_text(state_file.read_text(encoding="utf-8"), encoding="utf-8")
    (transaction_root / "transaction.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "product_name": "Eva-skill",
                "transaction_id": transaction_id,
                "target_root": str(target_root),
                "backup_root": str(backup_root),
                "managed_directories": list(MANAGED_DIRECTORIES),
                "original_names": ["eva"],
                "original_entry_types": {"eva": "directory"},
                "backed_up_names": ["eva"],
                "backing_up_name": None,
                "restored_names": [],
                "restoring_name": restoring_name,
                "installed_names": ["eva"],
                "activating_name": None,
                "state_file": str(state_file),
                "previous_state": {
                    "existed": True,
                    "path": str(state_file),
                    "backup": str(previous_state_path),
                },
                "status": "postcheck",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="eva-global-install-test-") as temporary:
        root = Path(temporary).resolve()
        target = root / "home" / ".agents" / "skills"
        state_file = root / "home" / ".agents" / "eva-skill-state" / "global-install.json"
        transactions = root / "home" / ".agents" / "eva-skill-transactions"
        backups = root / "home" / ".agents" / "eva-skill-backups"
        target.mkdir(parents=True)
        (target / "other-skill").mkdir()
        (target / "other-skill" / "SKILL.md").write_text("---\nname: other-skill\ndescription: keep\n---\n", encoding="utf-8")
        (target / "eva-custom").mkdir()
        (target / "eva-custom" / "SKILL.md").write_text("---\nname: eva-custom\ndescription: keep\n---\n", encoding="utf-8")

        missing_target = root / "missing" / "skills"
        missing_verify = run_json(
            "verify",
            ROOT,
            missing_target,
            root / "missing-state.json",
            root / "missing-transactions",
            root / "missing-backups",
            expect_ok=False,
        )
        if "尚未检测到 Eva-skill 安装目录" not in str(missing_verify.get("summary", "")):
            fail(f"verify must explain a missing installation clearly: {missing_verify}")
        if missing_target.exists():
            fail("verify created a missing target directory despite being a verification command")

        nested_state_target = root / "nested-state" / "skills"
        nested_state = nested_state_target / "eva" / "SKILL.md"
        rejected_nested_state = run_json(
            "install",
            ROOT,
            nested_state_target,
            nested_state,
            root / "nested-state-transactions",
            root / "nested-state-backups",
            expect_ok=False,
        )
        if rejected_nested_state.get("ok") is not False or nested_state_target.exists():
            fail(f"state inside the Skill root must be rejected before mutation: {rejected_nested_state}")

        world_transactions = root / "world-writable-transactions"
        world_transactions.mkdir()
        world_transactions.chmod(0o777)
        rejected_shared_control = run_json(
            "install",
            ROOT,
            root / "world-target" / "skills",
            root / "world-state" / "state.json",
            world_transactions,
            root / "world-backups",
            expect_ok=False,
        )
        if rejected_shared_control.get("ok") is not False:
            fail("shared-writable transaction roots must be rejected")

        installed = run_json("install", ROOT, target, state_file, transactions, backups)
        if installed.get("action") != "installed":
            fail(f"fresh install action must be installed: {installed}")
        notice = installed.get("notice") or {}
        if not notice.get("id"):
            fail(f"fresh install must create a one-time notice: {installed}")
        if OFFICIAL_GUIDE_HEADLINE not in str(installed.get("rendered_notice", "")):
            fail("installer notice must use the official guide headline exactly")
        assert_real_bundle(target)
        if not (target / "other-skill" / "SKILL.md").exists() or not (target / "eva-custom" / "SKILL.md").exists():
            fail("installer changed an unmanaged sibling Skill")

        before_topology_rejections = tree_digest(target)
        original_eva_skill = (target / "eva" / "SKILL.md").read_text(encoding="utf-8")
        rejected_skill_state = run_json(
            "install",
            ROOT,
            target,
            target / "eva" / "SKILL.md",
            root / "overlap-state-transactions",
            root / "overlap-state-backups",
            "--force",
            expect_ok=False,
        )
        if rejected_skill_state.get("ok") is not False:
            fail("installer accepted a state file inside an active Skill")
        if (target / "eva" / "SKILL.md").read_text(encoding="utf-8") != original_eva_skill:
            fail("rejected nested state path changed eva/SKILL.md")
        rejected_nested_transactions = run_json(
            "install",
            ROOT,
            target,
            state_file,
            target / "eva" / "transactions",
            root / "overlap-transaction-backups",
            "--force",
            expect_ok=False,
        )
        if rejected_nested_transactions.get("ok") is not False:
            fail("installer accepted a transaction root inside an active Skill")
        if tree_digest(target) != before_topology_rejections:
            fail("rejected control-path overlap changed the active installation")

        acknowledged = acknowledge(state_file, str(notice["id"]))
        if acknowledged.get("notice_pending") is not False:
            fail(f"ack must clear pending notice: {acknowledged}")
        normal_output = run_normal_force_install(ROOT, target, state_file, transactions, backups)
        if OFFICIAL_GUIDE_HEADLINE not in normal_output:
            fail("normal installer output must show the official guide headline")
        normal_state = json.loads(state_file.read_text(encoding="utf-8"))
        if normal_state.get("notice_pending") is not False:
            fail("normal installer must acknowledge the card it just showed")

        pending = run_json("install", ROOT, target, state_file, transactions, backups, "--force")
        pending_notice = pending.get("notice") or {}
        create_staged_transaction(target, state_file, transactions, backups)
        acknowledge(state_file, str(pending_notice["id"]))
        staged_recovery = run_json("recover", ROOT, target, state_file, transactions, backups)
        if staged_recovery.get("action") != "recovered":
            fail(f"staged recovery must succeed: {staged_recovery}")
        staged_state = json.loads(state_file.read_text(encoding="utf-8"))
        if staged_state.get("notice_pending") is not False:
            fail("recovering an unactivated staged transaction reverted a later acknowledgement")
        assert_staged_recovery_write_failure(
            target,
            state_file,
            transactions,
            backups,
        )

        bootstrap_orphan = transactions / "test-bootstrap-orphan"
        bootstrap_backup = backups / "test-bootstrap-orphan"
        bootstrap_orphan.mkdir()
        bootstrap_backup.mkdir()
        (bootstrap_orphan / "previous-state.json").write_text(
            state_file.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        bootstrap_recovery = run_json("recover", ROOT, target, state_file, transactions, backups)
        if bootstrap_recovery.get("action") != "recovered":
            fail(f"recover must clean a proven pre-activation orphan: {bootstrap_recovery}")
        if bootstrap_orphan.exists() or bootstrap_backup.exists():
            fail("pre-activation orphan cleanup left transaction or backup directories behind")
        state_before_verify = state_file.read_text(encoding="utf-8")
        verified = run_json("verify", ROOT, target, state_file, transactions, backups)
        if verified.get("action") != "verified":
            fail(f"verify must report verified: {verified}")
        if state_file.read_text(encoding="utf-8") != state_before_verify:
            fail("verify must not write installation state")

        unchanged = run_json("install", ROOT, target, state_file, transactions, backups)
        if unchanged.get("action") != "unchanged" or unchanged.get("notice") is not None:
            fail(f"same managed version must not show a second notice: {unchanged}")

        execution_marker = root / "untrusted-target-script-ran"
        target_doctor = target / "eva-shared" / "scripts" / "eva_doctor.py"
        target_doctor.write_text(
            "from pathlib import Path\n"
            f"Path({str(execution_marker)!r}).write_text('ran', encoding='utf-8')\n"
            "raise SystemExit(99)\n",
            encoding="utf-8",
        )
        rejected_verify = run_json(
            "verify",
            ROOT,
            target,
            state_file,
            transactions,
            backups,
            expect_ok=False,
        )
        if rejected_verify.get("ok") is not False:
            fail(f"verify must reject target/source integrity drift: {rejected_verify}")
        if execution_marker.exists():
            fail("verify executed an untrusted target-side validation script")
        repaired = run_json("install", ROOT, target, state_file, transactions, backups)
        if repaired.get("action") != "repaired":
            fail(f"tampered same-version bundle must be repaired: {repaired}")
        if execution_marker.exists():
            fail("repair install executed an untrusted pre-existing target script")
        repaired_notice = repaired.get("notice") or {}
        acknowledge(state_file, str(repaired_notice["id"]))

        state_before_recover = create_interrupted_transaction(
            target,
            state_file,
            transactions,
            backups,
        )
        recovered = run_json("recover", ROOT, target, state_file, transactions, backups)
        if recovered.get("action") != "recovered":
            fail(f"recover must report recovered: {recovered}")
        state_after_recover = state_file.read_text(encoding="utf-8")
        if state_after_recover != state_before_recover:
            fail(
                "recover must restore the pre-transaction installation state: "
                f"{state_after_recover!r} != {state_before_recover!r}"
            )
        if (target / "eva" / "interrupted-copy-must-disappear.txt").exists():
            fail("recover did not replace the interrupted active directory with its backup")
        assert_real_bundle(target)
        run_json("verify", ROOT, target, state_file, transactions, backups)

        create_postcheck_transaction(
            "test-restore-interrupted",
            target,
            state_file,
            transactions,
            backups,
            restoring_name="eva",
        )
        restore_interrupted = run_json("recover", ROOT, target, state_file, transactions, backups)
        if restore_interrupted.get("action") != "recovered":
            fail(f"recover must converge after backup-to-target already moved: {restore_interrupted}")
        run_json("verify", ROOT, target, state_file, transactions, backups)

        before_missing_backup = tree_digest(target)
        create_postcheck_transaction(
            "test-missing-backup",
            target,
            state_file,
            transactions,
            backups,
        )
        rejected_missing_backup = run_json(
            "recover",
            ROOT,
            target,
            state_file,
            transactions,
            backups,
            expect_ok=False,
        )
        if "已记录的旧模块备份缺失" not in str(rejected_missing_backup.get("summary", "")):
            fail(f"recover must fail closed when a required backup is missing: {rejected_missing_backup}")
        if tree_digest(target) != before_missing_backup:
            fail("missing-backup recovery changed the active bundle before reporting failure")
        shutil.rmtree(transactions / "test-missing-backup")
        shutil.rmtree(backups / "test-missing-backup")

        corrupt_transaction = transactions / "test-corrupt"
        corrupt_backup = backups / "test-corrupt"
        corrupt_transaction.mkdir()
        corrupt_backup.mkdir()
        (corrupt_transaction / "transaction.json").write_text("{", encoding="utf-8")
        rejected_corrupt_recover = run_json(
            "recover",
            ROOT,
            target,
            state_file,
            transactions,
            backups,
            expect_ok=False,
        )
        if "拒绝假装恢复成功" not in str(rejected_corrupt_recover.get("summary", "")):
            fail(f"recover must surface a corrupt journal: {rejected_corrupt_recover}")
        shutil.rmtree(corrupt_transaction)
        shutil.rmtree(corrupt_backup)

        before_invalid_source = tree_digest(target)
        broken_source = root / "broken-source"
        shutil.copytree(
            ROOT,
            broken_source,
            ignore=shutil.ignore_patterns(".git", "SkillHub", "__pycache__"),
        )
        (broken_source / "skills" / "eva-shared" / "SKILL.md").unlink()
        rejected = run_json(
            "install",
            broken_source,
            target,
            state_file,
            transactions,
            backups,
            expect_ok=False,
        )
        if rejected.get("ok") is not False:
            fail(f"broken source must be rejected: {rejected}")
        if tree_digest(target) != before_invalid_source:
            fail("rejected source changed the existing temporary installation")
        run_json("verify", ROOT, target, state_file, transactions, backups)

        lint_broken_source = root / "lint-broken-source"
        shutil.copytree(
            ROOT,
            lint_broken_source,
            ignore=shutil.ignore_patterns(".git", "SkillHub", "__pycache__"),
        )
        lint_target_text = lint_broken_source / "skills" / "eva-think" / "SKILL.md"
        lint_target_text.write_text(
            lint_target_text.read_text(encoding="utf-8") + "\n" + OFFICIAL_GUIDE_HEADLINE + "\n",
            encoding="utf-8",
        )
        before_lint_rejection = tree_digest(target)
        rejected_lint_source = run_json(
            "install",
            lint_broken_source,
            target,
            state_file,
            transactions,
            backups,
            "--force",
            expect_ok=False,
        )
        if rejected_lint_source.get("ok") is not False:
            fail("installer accepted a staged source that fails prompt lint")
        if tree_digest(target) != before_lint_rejection:
            fail("prompt-lint rejection changed the existing installation")

        legacy_target = root / "legacy" / ".agents" / "skills"
        legacy_state = root / "legacy" / ".agents" / "eva-skill-state" / "global-install.json"
        legacy_transactions = root / "legacy" / ".agents" / "eva-skill-transactions"
        legacy_backups = root / "legacy" / ".agents" / "eva-skill-backups"
        legacy_target.mkdir(parents=True)
        for name in MANAGED_DIRECTORIES:
            shutil.copytree(ROOT / "skills" / name, legacy_target / name)
        legacy_common = legacy_target / "eva-shared" / "scripts" / "eva_common.py"
        legacy_common.write_text(
            legacy_common.read_text(encoding="utf-8").replace(
                'VERSION = "eva-shared-2.1.3"',
                'VERSION = "eva-shared-2.1.2"',
            ),
            encoding="utf-8",
        )
        migrated = run_json(
            "install",
            ROOT,
            legacy_target,
            legacy_state,
            legacy_transactions,
            legacy_backups,
        )
        if migrated.get("action") != "migrated":
            fail(f"an unmanaged 2.1.2-style bundle must migrate conservatively: {migrated}")
        legacy_backup_root = Path(str(migrated.get("backup_root")))
        backed_up_common = legacy_backup_root / "eva-shared" / "scripts" / "eva_common.py"
        if "eva-shared-2.1.2" not in backed_up_common.read_text(encoding="utf-8"):
            fail("2.1.2 migration did not preserve the old bundle in backup")
        assert_real_bundle(legacy_target)
        run_json(
            "verify",
            ROOT,
            legacy_target,
            legacy_state,
            legacy_transactions,
            legacy_backups,
        )

        migrated_notice = migrated.get("notice") or {}
        acknowledge(legacy_state, str(migrated_notice["id"]))
        future_common = legacy_target / "eva-shared" / "scripts" / "eva_common.py"
        future_common.write_text(
            future_common.read_text(encoding="utf-8").replace(
                'VERSION = "eva-shared-2.1.3"',
                'VERSION = "eva-shared-9.9.9"',
            ),
            encoding="utf-8",
        )
        future_state = json.loads(legacy_state.read_text(encoding="utf-8"))
        future_state["installed_version"] = "9.9.9"
        legacy_state.write_text(json.dumps(future_state, ensure_ascii=False), encoding="utf-8")
        (legacy_target / "eva" / "SKILL.md").unlink()
        before_downgrade_rejection = tree_digest(legacy_target)
        rejected_downgrade = run_json(
            "install",
            ROOT,
            legacy_target,
            legacy_state,
            legacy_transactions,
            legacy_backups,
            expect_ok=False,
        )
        if "拒绝从 9.9.9 降级到 2.1.3" not in str(rejected_downgrade.get("summary", "")):
            fail(f"damaged future bundles must still require --allow-downgrade: {rejected_downgrade}")
        if tree_digest(legacy_target) != before_downgrade_rejection:
            fail("rejected downgrade changed the damaged future bundle")
        allowed_downgrade = run_json(
            "install",
            ROOT,
            legacy_target,
            legacy_state,
            legacy_transactions,
            legacy_backups,
            "--allow-downgrade",
        )
        if allowed_downgrade.get("action") != "repaired":
            fail(f"explicitly allowed downgrade should repair the damaged bundle: {allowed_downgrade}")
        assert_real_bundle(legacy_target)

    print("Eva global installer temporary integration checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
