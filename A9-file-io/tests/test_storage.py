"""LocalStorage 단위 테스트."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fileio.storage import LocalStorage


async def _gen(*chunks: bytes) -> AsyncIterator[bytes]:
    for c in chunks:
        yield c


async def test_put_and_stat(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    obj = await storage.put("hello.txt", _gen(b"hello", b" world"))
    assert obj.size == 11
    assert len(obj.sha256) == 64

    stat = await storage.stat("hello.txt")
    assert stat is not None
    assert stat.size == 11
    assert stat.sha256 == obj.sha256


async def test_get_streams_full_content(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    await storage.put("a.bin", _gen(b"abcdefghij"))
    iterator = await storage.get("a.bin")
    data = b"".join([c async for c in iterator])
    assert data == b"abcdefghij"


async def test_get_range(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path, chunk_bytes=4)
    await storage.put("nums.bin", _gen(b"0123456789"))
    iterator = await storage.get_range("nums.bin", 2, 6)  # "23456"
    data = b"".join([c async for c in iterator])
    assert data == b"23456"


async def test_atomic_rename_on_failure(tmp_path: Path) -> None:
    """예외 발생 시 _부분 파일_ 이 최종 키로 노출되지 않는지."""
    storage = LocalStorage(tmp_path)

    async def failing():
        yield b"partial"
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await storage.put("oops.bin", failing())

    assert await storage.stat("oops.bin") is None
    # .part 임시 파일도 정리됐는지
    assert not (tmp_path / "oops.bin.part").exists()


async def test_delete(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    await storage.put("k", _gen(b"x"))
    await storage.delete("k")
    assert await storage.stat("k") is None
    # 없는 키 삭제는 _조용히_ no-op
    await storage.delete("k")


async def test_invalid_key_rejected(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    with pytest.raises(ValueError):
        await storage.put("../escape", _gen(b"x"))
    with pytest.raises(ValueError):
        await storage.put("/abs/path", _gen(b"x"))
