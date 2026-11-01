from backup_tool.lock import BackupLock
from backup_tool.restore import restore_snapshot
from backup_tool.retention import RetentionPolicy


def test_backup_lock_acquire_and_release(tmp_path):
    lock_path = tmp_path / "backup.lock"
    lock = BackupLock(lock_path)

    assert lock.acquire()
    assert lock_path.read_text(encoding="utf-8").isdigit()
    assert not BackupLock(lock_path).acquire()

    lock.release()
    assert not lock_path.exists()


def test_restore_snapshot_copies_contents_but_skips_manifest(tmp_path):
    snapshot = tmp_path / "snapshot"
    (snapshot / "nested").mkdir(parents=True)
    (snapshot / "file.txt").write_text("saved", encoding="utf-8")
    (snapshot / "nested" / "item.txt").write_text("nested", encoding="utf-8")
    (snapshot / "manifest.json").write_text("{}", encoding="utf-8")
    target = tmp_path / "restored"

    restore_snapshot(snapshot, target)

    assert (target / "file.txt").read_text(encoding="utf-8") == "saved"
    assert (target / "nested" / "item.txt").read_text(encoding="utf-8") == "nested"
    assert not (target / "manifest.json").exists()


def test_retention_keeps_newest_daily_snapshots_and_only_touches_job(tmp_path):
    snapshot_root = tmp_path / "snapshots" / "documents"
    other_job_root = tmp_path / "snapshots" / "other"
    for day in range(1, 5):
        snapshot = snapshot_root / f"2025010{day}"
        snapshot.mkdir(parents=True)
        (snapshot / "backup.txt").write_text(str(day), encoding="utf-8")
    other_snapshot = other_job_root / "20250101"
    other_snapshot.mkdir(parents=True)

    RetentionPolicy({"daily": 2, "weekly": 0, "monthly": 0}).apply(
        tmp_path, "documents"
    )

    assert sorted(path.name for path in snapshot_root.iterdir()) == [
        "20250103",
        "20250104",
    ]
    assert other_snapshot.exists()
