from __future__ import annotations

import asyncio
import sqlite3
import sys
import time
from contextlib import closing
from pathlib import Path

import pytest

from mcp_behavior.contract import CommandSpec
from mcp_behavior.effects import _capture_file, _capture_sqlite, _capture_tree, resolve_within
from mcp_behavior.execution import ExecutionError, run_command


def test_file_tree_and_sqlite_observers_are_deterministic(tmp_path: Path) -> None:
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    database = tmp_path / "state.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("create table items (id integer, name text)")
        connection.executemany("insert into items values (?, ?)", [(2, "b"), (1, "a")])
        connection.commit()

    file_value = _capture_file(tmp_path, "a.txt", 10_000)
    tree_value = _capture_tree(tmp_path, 100_000)
    sqlite_value = _capture_sqlite(tmp_path, "state.db", "select * from items order by id", 10_000)

    assert file_value["text"] == "a"  # type: ignore[index]
    assert [entry["path"] for entry in tree_value["entries"]][:2] == [  # type: ignore[index]
        "a.txt",
        "b.txt",
    ]
    assert sqlite_value["rows"] == [[1, "a"], [2, "b"]]  # type: ignore[index]


def test_observer_path_cannot_escape_root(tmp_path: Path) -> None:
    with pytest.raises(ExecutionError, match="escapes declared root"):
        resolve_within(tmp_path / "root", "../secret.txt")


def test_command_timeout_kills_the_launched_process(tmp_path: Path) -> None:
    spec = CommandSpec((sys.executable, "-c", "import time; time.sleep(10)"), None)
    with pytest.raises(ExecutionError, match="timed out"):
        asyncio.run(
            run_command(
                spec,
                source=tmp_path / "contract.yaml",
                label="slow fixture",
                workspace=tmp_path,
                default_timeout=0.05,
                log_limit=1000,
            )
        )


def test_command_output_limit_is_shared_across_streams(tmp_path: Path) -> None:
    code = "import sys; print('a'*100); print('b'*100, file=sys.stderr)"
    spec = CommandSpec((sys.executable, "-c", code), None)
    with pytest.raises(ExecutionError, match="output exceeded"):
        asyncio.run(
            run_command(
                spec,
                source=tmp_path / "contract.yaml",
                label="noisy fixture",
                workspace=tmp_path,
                default_timeout=2,
                log_limit=50,
            )
        )


def test_command_timeout_kills_descendant_processes(tmp_path: Path) -> None:
    marker = tmp_path / "descendant-survived.txt"
    child = (
        "import time; from pathlib import Path; time.sleep(0.6); "
        f"Path({str(marker)!r}).write_text('survived')"
    )
    parent = (
        "import subprocess,sys,time; "
        f"subprocess.Popen([sys.executable, '-c', {child!r}]); time.sleep(10)"
    )
    spec = CommandSpec((sys.executable, "-c", parent), None)

    with pytest.raises(ExecutionError, match="timed out"):
        asyncio.run(
            run_command(
                spec,
                source=tmp_path / "contract.yaml",
                label="process-tree fixture",
                workspace=tmp_path,
                default_timeout=0.2,
                log_limit=1000,
            )
        )
    time.sleep(0.8)
    assert not marker.exists()
