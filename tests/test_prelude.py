"""Prelude functions: config, glob, read, include, subbob, shell."""

import os
import time
from pathlib import Path

from conftest import assert_output_contains_needles


def test_config_when_unset_none(bob):
    bob.write('assert config("MODE") is None')
    bob.run("build")


def test_config_when_unset_default(bob):
    bob.write("""
        mode = config("MODE", default="off")
        Rule(f"echo {mode} > $out").build("mode.txt")
    """)
    bob.run("build")
    assert bob.output_text("mode.txt").strip() == "off"


def test_config_when_unset_required_fails(bob):
    bob.write('config("MODE", required=True)')
    r = bob.run("build", assert_succesful=False)
    assert_output_contains_needles(r, "MODE")


def test_config_when_set(bob):
    bob.write("""
        mode = config("MODE")
        Rule(f"echo {mode} > $out").build("mode.txt")
    """)
    bob.run("build", configs={"MODE": "on"})
    assert bob.output_text("mode.txt").strip() == "on"


def test_glob_enumerates_files(bob):
    (bob.tmp_path / "src").mkdir()
    (bob.tmp_path / "src" / "a.txt").write_text("a", "utf-8")
    (bob.tmp_path / "src" / "b.txt").write_text("b", "utf-8")
    (bob.tmp_path / "src" / "sub").mkdir()
    (bob.tmp_path / "src" / "sub" / "b.txt").write_text("subb", "utf-8")
    (bob.tmp_path / "src" / "sub" / "unmatched").write_text("u", "utf-8")
    bob.write("""
        cp = Rule("cp $in $out")
        for src in glob("**/*.txt", path="src"):
            cp(src, inputs=[src])
    """)
    bob.run("build")
    assert bob.output_text(Path("src") / "a.txt") == "a"
    assert bob.output_text(Path("src") / "b.txt") == "b"
    assert bob.output_text(Path("src") / "sub" / "b.txt") == "subb"
    assert not bob.output_path(Path("src") / "sub" / "unmatched").exists()


def test_glob_reconfigures_when_directory_changes(bob):
    (bob.tmp_path / "src").mkdir()
    (bob.tmp_path / "src" / "a.txt").write_text("a", "utf-8")
    bob.write("""
        cp = Rule("cp $in $out")
        for src in glob("*.txt", path="src"):
            cp(src.name, inputs=[src])
    """)
    bob.run("build")
    assert bob.output_path("a.txt").exists()

    time.sleep(0.1)
    (bob.tmp_path / "src" / "b.txt").write_text("b", "utf-8")
    bob.run("build")
    assert bob.output_text("b.txt") == "b"


def test_read_returns_bytes(bob):
    (bob.tmp_path / "data.txt").write_text("payload", "utf-8")
    bob.write("""
        body = read("data.txt").decode()
        Rule("echo $body > $out", body=body).build("out.txt")
    """)
    bob.run("build")
    assert bob.output_text("out.txt").strip() == "payload"


def test_read_reconfigures_when_file_changes(bob):
    (bob.tmp_path / "data.txt").write_text("first", "utf-8")
    bob.write("""
        body = read("data.txt").decode()
        Rule(f"echo {body} > $out").build("out.txt")
    """)
    bob.run("build")
    assert bob.output_text("out.txt").strip() == "first"

    time.sleep(0.1)
    (bob.tmp_path / "data.txt").write_text("second", "utf-8")
    bob.run("build")
    assert bob.output_text("out.txt").strip() == "second"


def test_read_nonexistent_file_fails(bob):
    bob.write('read("nope.txt")')
    r = bob.run("build", assert_succesful=False)
    assert_output_contains_needles(r, "FileNotFoundError")


def test_include_shares_caller_scope(bob):
    bob.write('targets.append("from-included")\n', name="parts/Bobfile")
    bob.write("""
        targets = []
        include("parts")
        emit = Rule("echo $name > $out")
        for t in targets:
            emit(t + ".txt", name=t)
    """)
    bob.run("build")
    assert bob.output_text("from-included.txt").strip() == "from-included"


def test_include_traceback_points_at_included_file(bob):
    """`include()` compiles with the file path so tracebacks reference it."""
    bob.write("x = 1 / 0\n", name="parts/Bobfile")
    bob.write('include("parts")')
    r = bob.run("build", assert_succesful=False)
    assert_output_contains_needles(r, os.path.join("parts", "Bobfile"))


def test_include_change_source_dir_resolves_relative_to_subdir(bob):
    """`change_source_dir=True` makes Bobfile-relative paths inside the
    include resolve against the subdir."""
    (bob.tmp_path / "sub" / "src").mkdir(parents=True)
    (bob.tmp_path / "sub" / "src" / "data.txt").write_text("hello", "utf-8")
    bob.write(
        'Rule("cp $in $out").build("out.txt", inputs=["src/data.txt"])\n',
        name="sub/Bobfile",
    )
    bob.write('include("sub")')
    bob.run("build")
    assert bob.output_text("out.txt") == "hello"


def test_include_change_build_dir_outputs_under_subdir(bob):
    """`change_build_dir=True` (also via change_source_dir=True default
    cascade) places outputs at build/<sub>/<name>."""
    bob.write('Rule("echo hi > $out").build("inner.txt")\n', name="parts/Bobfile")
    bob.write('include("parts", change_build_dir=True)')
    bob.run("build")
    assert bob.output_text(Path("parts") / "inner.txt").strip() == "hi"


def test_include_does_not_change_build_dir_by_default(bob):
    """Default `change_build_dir=False`: included outputs land flat."""
    bob.write('Rule("echo hi > $out").build("flat.txt")\n', name="parts/Bobfile")
    bob.write('include("parts")')
    bob.run("build")
    assert bob.output_text("flat.txt").strip() == "hi"
    assert not bob.output_path(Path("parts") / "flat.txt").exists()


def test_include_restores_parent_source_and_build_dirs(bob):
    """After an `include`, parent's source/build dirs are unchanged."""
    bob.write('Rule("echo from-sub > $out").build("sub.txt")\n', name="parts/Bobfile")
    bob.write("""
        include("parts", change_build_dir=True)
        Rule("echo parent > $out").build("parent.txt")
    """)
    bob.run("build")
    assert bob.output_text(Path("parts") / "sub.txt").strip() == "from-sub"
    assert bob.output_text("parent.txt").strip() == "parent"


def test_glob_in_included_subdir_anchors_at_subdir(bob):
    """`glob()` inside an include with change_source_dir resolves against
    the sub directory's tree."""
    (bob.tmp_path / "lib").mkdir()
    (bob.tmp_path / "lib" / "a.txt").write_text("a", "utf-8")
    (bob.tmp_path / "lib" / "b.txt").write_text("b", "utf-8")
    bob.write(
        """
        cp = Rule("cp $in $out")
        for f in glob("*.txt"):
            cp(f.name, inputs=[f])
    """,
        name="lib/Bobfile",
    )
    bob.write('include("lib", change_build_dir=True, change_source_dir=True)')
    bob.run("build")
    assert bob.output_text(Path("lib") / "a.txt") == "a"
    assert bob.output_text(Path("lib") / "b.txt") == "b"


def test_subbob_passes_parameter_in(bob):
    """Outer `subbob(key=value)` arrives via inner `use(key)`."""
    bob.write(
        """
        prefix = use("prefix", type=str)
        Rule("echo $p > $out", p=prefix).build("greet.txt")
    """,
        name="lib/Bobfile",
    )
    bob.write('subbob("lib", provides={"prefix": "hi"})')
    bob.run("build")
    assert bob.output_text(Path("lib") / "greet.txt").strip() == "hi"


def test_subbob_export_returned_to_outer(bob):
    """Inner `export(key=value)` reaches outer `subbob(...).use(key)`."""
    bob.write('export(produced="hello")\n', name="lib/Bobfile")
    bob.write("""
        got = subbob("lib").use("produced", type=str)
        Rule("echo $v > $out", v=got).build("relay.txt")
    """)
    bob.run("build")
    assert bob.output_text("relay.txt").strip() == "hello"


def test_subbob_use_optional_returns_default(bob):
    bob.write("# empty\n", name="lib/Bobfile")
    bob.write("""
        result = subbob("lib").use("missing", type=str, optional=True, default="fb")
        Rule("echo $r > $out", r=result).build("out.txt")
    """)
    bob.run("build")
    assert bob.output_text("out.txt").strip() == "fb"


def test_subbob_restores_parent_rule_values(bob):
    """A child's `provide` on a parent rule's variable must not leak."""
    bob.write(
        """
        emit = use("emit")
        with emit["msg"].provide("from-child"):
            emit("child.txt")
    """,
        name="lib/Bobfile",
    )
    bob.write("""
        emit = Rule("echo $msg > $out", msg="parent")
        subbob("lib", provides={"emit": emit})
        emit("after.txt")
    """)
    bob.run("build")
    assert bob.output_text(Path("lib") / "child.txt").strip() == "from-child"
    assert bob.output_text("after.txt").strip() == "parent"


def test_subbob_use_type_mismatch_fails(bob):
    bob.write("export(thing=123)\n", name="lib/Bobfile")
    bob.write('subbob("lib").use("thing", type=str)')
    r = bob.run("build", assert_succesful=False)
    assert_output_contains_needles(r, "TypeError")


def test_subbob_use_missing_key_fails(bob):
    bob.write("# empty\n", name="lib/Bobfile")
    bob.write('subbob("lib").use("absent", type=str)')
    r = bob.run("build", assert_succesful=False)
    assert_output_contains_needles(r, "absent")


def test_subbob_rebuild_when_child_bobfile_changes(bob):
    """Editing a child Bobfile must trigger reconfigure on next parent build —
    child path lives in `configure_implicit_dependencies`."""
    bob.write('Rule("echo first > $out").build("sub.txt")', name="lib/Bobfile")
    bob.write('subbob("lib")')
    bob.run("build")
    assert bob.output_text(Path("lib") / "sub.txt").strip() == "first"

    time.sleep(0.1)
    bob.write('Rule("echo second > $out").build("sub.txt")', name="lib/Bobfile")
    bob.run("build")
    assert bob.output_text(Path("lib") / "sub.txt").strip() == "second"


def test_subbob_restores_parent_build_dir(bob):
    """Parent rule built AFTER a subbob lands at builddir root, not subdir."""
    bob.write('Rule("echo child > $out").build("c.txt")\n', name="lib/Bobfile")
    bob.write("""
        subbob("lib")
        Rule("echo parent > $out").build("p.txt")
    """)
    bob.run("build")
    assert bob.output_text(Path("lib") / "c.txt").strip() == "child"
    assert bob.output_text("p.txt").strip() == "parent"
    assert not bob.output_path(Path("lib") / "p.txt").exists()


def test_subbob_restores_provides_after_return(bob):
    """A child's `use` mustn't leak: parent `use(...)` after subbob is
    unaffected."""
    bob.write('use("k", type=str)\n', name="lib/Bobfile")
    bob.write("""
        subbob("lib", provides={"k": "child-value"})
        assert use("k", type=str, optional=True, default="absent") == "absent"
        Rule("echo ok > $out").build("ok.txt")
    """)
    bob.run("build")
    assert bob.output_text("ok.txt").strip() == "ok"


def test_subbob_no_output_collision_between_siblings(bob):
    """Two sibling subbobs may declare the same output name; each lands
    under its own curdir."""
    bob.write('Rule("echo a > $out").build("out.txt")', name="a/Bobfile")
    bob.write('Rule("echo b > $out").build("out.txt")', name="b/Bobfile")
    bob.write("""
        subbob("a")
        subbob("b")
    """)
    bob.run("build")
    assert bob.output_text(Path("a") / "out.txt").strip() == "a"
    assert bob.output_text(Path("b") / "out.txt").strip() == "b"


def test_shell_runs_command_at_configure(bob):
    bob.write("""
        magic = shell("echo abracadabra").strip()
        Rule("echo $word > $out", word=magic).build("out.txt")
    """)
    bob.run("build")
    assert bob.output_text("out.txt").strip() == "abracadabra"


def test_shell_failure_aborts_configure(bob):
    """A non-zero exit from `shell(...)` must abort configure with a
    non-zero bob exit and surface the original stderr."""
    bob.write('shell("echo boom 1>&2; false")')
    r = bob.run("build", assert_succesful=False)
    assert_output_contains_needles(r, "boom")


def test_shell_inside_subbob_writes_to_per_subbob_build_dir(bob):
    bob.write(
        'magic = shell("echo deep").strip()\nRule(f"echo {magic} > $out").build("out.txt")\n',
        name="lib/Bobfile",
    )
    bob.write('subbob("lib")')
    bob.run("build")
    assert bob.output_text(Path("lib") / "out.txt").strip() == "deep"


def test_nested_subbob_resolves_correctly(bob):
    bob.write(
        'Rule("echo deep > $out").build("inner.txt")\n',
        name="a/b/Bobfile",
    )
    bob.write('subbob("b")\n', name="a/Bobfile")
    bob.write('subbob("a")')
    bob.run("build")
    assert bob.output_text(Path("a") / "b" / "inner.txt").strip() == "deep"


def test_shell_reconfigures_when_output_changes(bob):
    (bob.tmp_path / "magic").write_text("first\n", "utf-8")
    bob.write("""
        magic = shell("cat magic").strip()
        Rule(f"echo {magic} > $out").build("out.txt")
    """)
    bob.run("build")
    assert bob.output_text("out.txt").strip() == "first"

    time.sleep(0.1)
    (bob.tmp_path / "magic").write_text("second\n", "utf-8")
    bob.run("build")
    assert bob.output_text("out.txt").strip() == "second"


def test_read_text_true_returns_str(bob):
    (bob.tmp_path / "data.txt").write_text("payload", "utf-8")
    bob.write("""
        body = read("data.txt", text=True)
        assert isinstance(body, str), type(body)
        Rule("echo $b > $out", b=body).build("out.txt")
    """)
    bob.run("build")
    assert bob.output_text("out.txt").strip() == "payload"


def test_shell_text_false_returns_bytes(bob):
    bob.write("""
        out = shell("printf raw", text=False)
        assert isinstance(out, bytes), type(out)
        Rule("echo $w > $out", w=out.decode()).build("out.txt")
    """)
    bob.run("build")
    assert bob.output_text("out.txt").strip() == "raw"


def test_glob_unicode_filenames(bob):
    (bob.tmp_path / "src").mkdir()
    (bob.tmp_path / "src" / "café.txt").write_text("u", "utf-8")
    bob.write("""
        cp = Rule("cp $in $out")
        for src in glob("*.txt", path="src"):
            cp(src.name, inputs=[src])
    """)
    bob.run("build")
    assert bob.output_text("café.txt") == "u"


def test_bob_required_version_two_segment_string(bob):
    # A "major.minor" string (no patch) must parse and satisfy the running
    # bob version.
    bob.write("""
        bob_required_version("1.0")
        Rule("echo ok > $out").build("ok.txt")
    """)
    bob.run("build")
    assert bob.output_text("ok.txt").strip() == "ok"


def test_include_function_defined_in_child_callable_from_parent(bob):
    bob.write(
        """
        def make(name):
            Rule("echo $n > $out", n=name).build(name + ".txt")
        """,
        name="parts/Bobfile",
    )
    bob.write("""
        include("parts")
        make("from-helper")
    """)
    bob.run("build")
    assert bob.output_text("from-helper.txt").strip() == "from-helper"


def test_include_nested_resolves_against_current_source_dir(bob):
    """An `include` inside an included file should resolve its child path
    against the deepest current source dir."""
    (bob.tmp_path / "a" / "b").mkdir(parents=True)
    (bob.tmp_path / "a" / "b" / "data.txt").write_text("deep", "utf-8")
    bob.write(
        'Rule("cp $in $out").build("out.txt", inputs=["data.txt"])\n',
        name="a/b/Bobfile",
    )
    bob.write('include("b")\n', name="a/Bobfile")
    bob.write('include("a")')
    bob.run("build")
    assert bob.output_text("out.txt") == "deep"


def test_include_failure_restores_parent_source_and_build_dirs(bob):
    """If an included Bobfile raises, the parent's source/build dirs are
    restored (the `finally` in `include`)."""
    bob.write('raise RuntimeError("boom")\n', name="parts/Bobfile")
    bob.write("""
        before_source = curdir().value
        before_build = builddir().value
        try:
            include("parts", change_build_dir=True)
        except RuntimeError:
            pass
        assert curdir().value == before_source
        assert builddir().value == before_build
        Rule("echo ok > $out").build("ok.txt")
    """)
    bob.run("build")
    assert bob.output_text("ok.txt").strip() == "ok"


def test_subbob_returns_exports_instance(bob):
    bob.write("# empty\n", name="lib/Bobfile")
    bob.write("""
        from bob.core.context import Exports
        result = subbob("lib")
        assert isinstance(result, Exports), type(result)
        Rule("echo ok > $out").build("ok.txt")
    """)
    bob.run("build")
    assert bob.output_text("ok.txt").strip() == "ok"


def test_subbob_failure_restores_parent_state(bob):
    """A raising child must not leave the parent's source dir recursed: the
    `finally` in `subbob` restores the backed-up context."""
    bob.write('raise RuntimeError("boom")\n', name="lib/Bobfile")
    bob.write("""
        before = curdir().value
        try:
            subbob("lib")
        except RuntimeError:
            pass
        assert curdir().value == before
        Rule("echo ok > $out").build("ok.txt")
    """)
    bob.run("build")
    assert bob.output_text("ok.txt").strip() == "ok"


def test_source_recurse_scopes_current_source_dir_within_with_block(bob):
    bob.write("""
        from pathlib import Path
        with source_recurse("sub"):
            assert curdir().value == Path("sub"), curdir().value
        Rule("echo ok > $out").build("ok.txt")
    """)
    bob.run("build")
    assert bob.output_text("ok.txt").strip() == "ok"


def test_source_recurse_restores_after_exit(bob):
    bob.write("""
        before = curdir().value
        with source_recurse("sub"):
            pass
        assert curdir().value == before
        Rule("echo ok > $out").build("ok.txt")
    """)
    bob.run("build")
    assert bob.output_text("ok.txt").strip() == "ok"


def test_build_recurse_scopes_current_build_dir(bob):
    bob.write("""
        before = builddir().value
        with build_recurse("sub"):
            assert builddir().value == before / "sub", builddir().value
        assert builddir().value == before
        Rule("echo ok > $out").build("ok.txt")
    """)
    bob.run("build")
    assert bob.output_text("ok.txt").strip() == "ok"


def test_source_recurse_nested_compose_paths(bob):
    bob.write("""
        from pathlib import Path
        with source_recurse("a"):
            with source_recurse("b"):
                assert curdir().value == Path("a/b"), curdir().value
        Rule("echo ok > $out").build("ok.txt")
    """)
    bob.run("build")
    assert bob.output_text("ok.txt").strip() == "ok"


def test_root_relative_path_default_anchors_to_current_source_dir(bob):
    bob.write("""
        from pathlib import Path
        with source_recurse("sub"):
            assert RootRelativePath("x").value == Path("sub/x")
        Rule("echo ok > $out").build("ok.txt")
    """)
    bob.run("build")
    assert bob.output_text("ok.txt").strip() == "ok"


def test_root_relative_path_resolve_returns_absolute_under_context_root(bob):
    bob.write("""
        r = RootRelativePath("foo.txt").resolve()
        assert r.is_absolute(), r
        assert str(r).endswith("foo.txt"), r
        Rule("echo ok > $out").build("ok.txt")
    """)
    bob.run("build")
    assert bob.output_text("ok.txt").strip() == "ok"
