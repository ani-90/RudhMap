import xml.etree.ElementTree as ET

from rudhmap.cli import diagram_cmd
from tests.test_server import _make_repo


def test_diagram_cmd_writes_whole_repo_diagram(tmp_path, capsys):
    repo = _make_repo(tmp_path)

    code = diagram_cmd(str(repo), None, 60, None)

    assert code == 0
    out = repo / "rudhmap.drawio"
    assert out.is_file()
    ET.fromstring(out.read_text(encoding="utf-8"))
    assert f"wrote {out.resolve()}" in capsys.readouterr().out


def test_diagram_cmd_is_byte_identical_across_runs(tmp_path):
    repo = _make_repo(tmp_path)
    first, second = tmp_path / "one.drawio", tmp_path / "two.drawio"

    diagram_cmd(str(repo), None, 60, str(first))
    diagram_cmd(str(repo), None, 60, str(second))

    assert first.read_bytes() == second.read_bytes()


def test_diagram_cmd_writes_nothing_and_exits_nonzero_on_no_match(tmp_path, capsys):
    repo = _make_repo(tmp_path)

    code = diagram_cmd(str(repo), "kafka billing invoices", 60, None)

    assert code == 1
    assert not list(repo.glob("*.drawio"))
    assert "no diagram written" in capsys.readouterr().out


def test_diagram_cmd_rejects_non_drawio_output(tmp_path, capsys):
    repo = _make_repo(tmp_path)

    code = diagram_cmd(str(repo), None, 60, str(tmp_path / "out.txt"))

    assert code == 2
    assert not (tmp_path / "out.txt").exists()
    assert ".drawio" in capsys.readouterr().err
