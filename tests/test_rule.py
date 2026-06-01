"""Single-Rule semantics: $var substitution, scoping, per-build override,
multi-output, anonymous naming, phony, generate_rule, override, extend.
"""

import time

from conftest import assert_output_contains_needles


def test_default_variable_substitutes(bob):
    bob.write('Rule("echo $msg > $out", msg="hello world").build("out.txt")')
    bob.run("build")
    assert bob.output_text("out.txt").strip() == "hello world"


def test_per_build_variable_overrides_default(bob):
    bob.write("""
        emit = Rule("echo $word > $out", word="default")
        emit("a.txt")
        emit("b.txt", word="override")
    """)
    bob.run("build")
    assert bob.output_text("a.txt").strip() == "default"
    assert bob.output_text("b.txt").strip() == "override"


def test_list_variable_escaped(bob):
    bob.write('Rule("echo $words > $out", words=["one", "two three"]).build("out.txt")')
    bob.run("build")
    # second element contains a space → shlex-quoted on the build edge.
    assert bob.output_text("out.txt").strip() == "one two three"


def test_variable_provide_scoped(bob):
    bob.write("""
        emit = Rule("echo $tag > $out", tag="ignored")
        with emit["tag"].provide("scoped"):
            emit("inside.txt")
        emit("outside.txt")
    """)
    bob.run("build")
    assert bob.output_text("inside.txt").strip() == "scoped"
    assert bob.output_text("outside.txt").strip() == "ignored"


def test_variable_extend_scoped(bob):
    bob.write("""
        emit = Rule("echo $flags > $out", flags=["base"])
        with emit["flags"].extend(["extra"]):
            emit("ext.txt")
        emit("base.txt")
    """)
    bob.run("build")
    assert bob.output_text("ext.txt").strip() == "base extra"
    assert bob.output_text("base.txt").strip() == "base"


def test_variable(bob):
    bob.write("""
        a = Rule("echo $shared a > $out", shared="x")
        b = Rule("echo $shared b > $out", shared="x")
        shared = variable("shared", a, b)
        with shared.provide("Y"):
            a("a.txt")
            b("b.txt")
    """)
    bob.run("build")
    assert bob.output_text("a.txt").strip() == "Y a"
    assert bob.output_text("b.txt").strip() == "Y b"


def test_rule_rebuilds_when_input_changes(bob):
    (bob.tmp_path / "src.txt").write_text("first", "utf-8")
    bob.write('Rule("cp $in $out").build("out.txt", inputs=["src.txt"])')
    bob.run("build")
    assert bob.output_text("out.txt") == "first"

    time.sleep(0.1)
    (bob.tmp_path / "src.txt").write_text("second", "utf-8")
    bob.run("build")
    assert bob.output_text("out.txt") == "second"


def test_rule_skips_when_input_unchanged(bob):
    (bob.tmp_path / "src.txt").write_text("body", "utf-8")
    bob.write('Rule("cp $in $out").build("out.txt", inputs=["src.txt"])')
    bob.run("build")
    mtime = bob.output_path("out.txt").stat().st_mtime

    time.sleep(0.1)
    bob.run("build")
    assert bob.output_path("out.txt").stat().st_mtime == mtime


def test_multi_output_edge_writes_all_outputs(bob):
    """Both outputs of a multi-output edge must exist after one build."""
    bob.write('Rule("echo hi | tee $out > /dev/null").build("a.txt", "b.txt")')
    bob.run("build")
    assert bob.output_text("a.txt").strip() == "hi"
    assert bob.output_text("b.txt").strip() == "hi"


def test_multi_output_edge_runs_once_per_build(bob):
    """A single multi-output edge produces both outputs in one invocation —
    not one edge per output. Both files share a single mtime."""
    bob.write('Rule("echo hi | tee $out > /dev/null").build("a.txt", "b.txt")')
    bob.run("build")
    # mtime resolution can collapse to whole seconds on some filesystems, so
    # we assert |delta| < 1s rather than equality.
    delta = abs(
        bob.output_path("a.txt").stat().st_mtime
        - bob.output_path("b.txt").stat().st_mtime
    )
    assert delta < 1, f"outputs have differing mtimes (delta={delta}s)"


def test_generate_rule_skips_downstream_when_output_unchanged(bob):
    """`generate_rule` swaps via `cmp -s`: output mtime only bumps when the
    new content differs. A downstream rule sees the same mtime and stays
    cached on the next build."""
    (bob.tmp_path / "src.txt").write_text("constant", "utf-8")
    bob.write("""
        gen = generate_rule("cat src.txt").build("gen.txt")
        Rule("cp $in $out").build("downstream.txt", inputs=[gen])
    """)
    bob.run("build")
    downstream_mtime = bob.output_path("downstream.txt").stat().st_mtime

    time.sleep(0.1)
    bob.run("build", "-F")
    # generator content unchanged → gen.txt mtime stable → downstream not rebuilt.
    assert bob.output_path("downstream.txt").stat().st_mtime == downstream_mtime


def test_generate_rule_always_runs(bob):
    """`generate_rule` re-executes its command on every build — `restat=1`
    keeps the output mtime stable when content matches, but the command
    itself still runs. Verify via a side-effect counter file."""
    counter = bob.tmp_path / "counter"
    counter.write_text("", "utf-8")
    bob.write(f"""
        generate_rule("printf x >> {counter} && echo stable").build("gen.txt")
    """)
    bob.run("build")
    after_first = len(counter.read_text("utf-8"))

    bob.run("build")
    after_second = len(counter.read_text("utf-8"))

    assert after_first >= 1, "command did not run on first build"
    assert after_second > after_first, (
        f"command did not re-run on second build: {after_first} → {after_second}"
    )


def test_generate_rule_rebuilds_downstream_when_output_changes(bob):
    (bob.tmp_path / "src.txt").write_text("first", "utf-8")
    bob.write("""
        gen = generate_rule("cat src.txt").build("gen.txt")
        Rule("cp $in $out").build("downstream.txt", inputs=[gen])
    """)
    bob.run("build")
    downstream_mtime = bob.output_path("downstream.txt").stat().st_mtime

    time.sleep(0.1)
    (bob.tmp_path / "src.txt").write_text("second", "utf-8")
    bob.run("build", "-F")
    assert bob.output_text("downstream.txt").strip() == "second"
    assert bob.output_path("downstream.txt").stat().st_mtime > downstream_mtime


def test_rule_single_input_enforced(bob):
    bob.write("""
        r = Rule("cat $in > $out", single_input=True)
        r("out.txt", inputs=["a", "b"])
    """)
    r = bob.run("build", assert_succesful=False)
    assert_output_contains_needles(r, "single_input")


def test_rule_single_output_enforced(bob):
    bob.write("""
        r = Rule("echo hi > $out", single_output=True)
        r("a.txt", "b.txt")
    """)
    r = bob.run("build", assert_succesful=False)
    assert_output_contains_needles(r, "single_output")


def test_rule_variable_accepts_path_value(bob):
    """A per-build `var=Path(...)` is resolved relative to the source dir."""
    (bob.tmp_path / "src.txt").write_text("payload", "utf-8")
    bob.write("""
        from pathlib import Path
        Rule("cat $extra > $out", extra="").build(
            "out.txt", inputs=[], extra=Path("src.txt")
        )
    """)
    bob.run("build")
    assert bob.output_text("out.txt") == "payload"


def test_rule_implicit_accepts_filetarget(bob):
    """`implicit=[file_target]` adds the underlying path as an implicit dep."""
    bob.write("""
        gen = Rule("echo gen > $out").build("gen.txt")
        echo = Rule("echo hi > $out")
        echo("out.txt", implicit=[gen])
    """)
    bob.run("configure")
    deps = bob.query("out.txt")
    assert any("gen.txt" in d for d in deps["implicit"]), deps


def test_rule_implicit_accepts_root_relative_path(bob):
    bob.write("""
        Rule("echo seed > $out").build("seed.txt")
        echo = Rule("echo hi > $out")
        echo("out.txt", implicit=[RootRelativePath("seed.txt")])
    """)
    bob.run("configure")
    deps = bob.query("out.txt")
    assert any("seed.txt" in d for d in deps["implicit"]), deps


def test_rule_uninitialized_variable(bob):
    bob.write('Rule("$missing > $out").build("a.txt")')
    r = bob.run("build", assert_succesful=False)
    assert_output_contains_needles(r, "uninitialized")


def test_rule_unused_variable_at_construction(bob):
    bob.write('Rule("echo $known > $out", surprise="x")')
    r = bob.run("build", assert_succesful=False)
    assert_output_contains_needles(r, "not a variable of the rule")


def test_rule_unused_variable_at_build(bob):
    bob.write("""
        emit = Rule("echo $known > $out", known="x")
        emit("a.txt", typo="y")
    """)
    r = bob.run("build", assert_succesful=False)
    assert_output_contains_needles(r, "unused variable")


def test_rule_build_single_output_returns_filetarget(bob):
    bob.write("""
        r = Rule("echo hi > $out", single_output=True).build("a.txt")
        assert isinstance(r, FileTarget), type(r)
    """)
    bob.run("configure")


def test_rule_build_multi_output_returns_list_of_filetargets(bob):
    bob.write("""
        r = Rule("echo hi | tee $out > /dev/null").build("a.txt", "b.txt")
        assert isinstance(r, list), type(r)
        assert all(isinstance(x, FileTarget) for x in r), r
    """)
    bob.run("configure")


def test_rule_path_with_spaces_in_input(bob):
    (bob.tmp_path / "my src.txt").write_text("spaced", "utf-8")
    bob.write('Rule("cp $in $out").build("out.txt", inputs=["my src.txt"])')
    bob.run("build")
    assert bob.output_text("out.txt") == "spaced"


def test_rule_path_with_colon_in_input(bob):
    (bob.tmp_path / "a:b.txt").write_text("colon", "utf-8")
    bob.write('Rule("cp $in $out").build("out.txt", inputs=["a:b.txt"])')
    bob.run("build")
    assert bob.output_text("out.txt") == "colon"


def test_rule_path_with_dollar_in_input(bob):
    """A `$` in an input path must be escaped (`$$`) on the Ninja build edge
    rather than treated as a variable reference."""
    (bob.tmp_path / "a$b.txt").write_text("dollar", "utf-8")
    bob.write('Rule("cp $in $out").build("out.txt", inputs=["a$b.txt"])')
    bob.run("build")
    assert bob.output_text("out.txt") == "dollar"


def test_rule_unicode_in_command_and_output_name(bob):
    bob.write('Rule("echo café > $out").build("café.txt")')
    bob.run("build")
    assert bob.output_text("café.txt").strip() == "café"
