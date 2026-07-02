import hashlib

from wc2026.hashing import git_commit, git_dirty, hash_file, hash_json


def test_hash_json_is_key_order_independent():
    a = {"x": 1, "y": {"a": 2, "b": 3}}
    b = {"y": {"b": 3, "a": 2}, "x": 1}
    assert hash_json(a) == hash_json(b)


def test_hash_json_changes_with_value():
    assert hash_json({"x": 1}) != hash_json({"x": 2})


def test_hash_file_matches_sha256(tmp_path):
    p = tmp_path / "blob.bin"
    data = b"world-cup-2026" * 1000
    p.write_bytes(data)
    assert hash_file(p) == hashlib.sha256(data).hexdigest()


def test_git_helpers_never_raise():
    # Outside or inside a repo, these must degrade gracefully, never throw.
    assert git_commit() is None or isinstance(git_commit(), str)
    assert git_dirty() in (True, False, None)
