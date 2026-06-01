"""Provider / RuleProvider behavior via Bobfiles. They require an active
BobContext (registration in `context.providers`), so they can't be tested
purely; we drive them through `bob configure` / `bob build`."""

from conftest import assert_output_contains_needles


def test_provider_swaps_value_inside_scope(bob):
    bob.write("""
        p = Provider("base")
        echo = Rule("echo $v > $out", v="x")
        with p.provide("override"):
            echo("inside.txt", v=p.get())
        echo("outside.txt", v=p.get())
    """)
    bob.run("build")
    assert bob.output_text("inside.txt").strip() == "override"
    assert bob.output_text("outside.txt").strip() == "base"


def test_provider_optional_returns_default(bob):
    bob.write("""
        p = Provider()
        Rule("echo $v > $out", v=p.get(optional=True, default="fb")).build("out.txt")
    """)
    bob.run("build")
    assert bob.output_text("out.txt").strip() == "fb"


def test_rule_provider_swaps_implementation(bob):
    bob.write("""
        real = Rule("echo real > $out")
        stub = Rule("echo stub > $out")
        real_provider = RuleProvider(real)
        with real_provider.provide(stub):
            real_provider("first.txt")
        real_provider("second.txt")
    """)
    bob.run("build")
    assert bob.output_text("first.txt").strip() == "stub"
    assert bob.output_text("second.txt").strip() == "real"


def test_rule_provider_rejects_incompatible_single_input(bob):
    bob.write("""
        single = Rule("cat $in > $out", single_input=True)
        multi = Rule("cat $in > $out")
        p = RuleProvider(single)
        p.provide(multi)
    """)
    r = bob.run("build", assert_succesful=False)
    # Pin the exception class + the kwarg + the violated direction. Rich
    # may wrap "single_input=False" across lines, so use the kwarg + class
    # together instead of the full literal.
    assert_output_contains_needles(r, "ValueError", "single_input")


def test_rule_provider_rejects_incompatible_single_output(bob):
    bob.write("""
        single = Rule("echo > $out", single_output=True)
        multi = Rule("echo > $out")
        p = RuleProvider(single)
        p.provide(multi)
    """)
    r = bob.run("build", assert_succesful=False)
    assert_output_contains_needles(r, "ValueError", "single_output")


def test_provider_extend_appends_to_current(bob):
    """`Provider.extend` adds to the current value within its scope and
    restores the prior value on exit."""
    bob.write("""
        p = Provider(["a"])
        echo = Rule("echo $v > $out", v="x")
        with p.extend(["b"]):
            echo("inside.txt", v=p.get())
        echo("outside.txt", v=p.get())
    """)
    bob.run("build")
    assert bob.output_text("inside.txt").strip() == "a b"
    assert bob.output_text("outside.txt").strip() == "a"


def test_rule_provider_init_respects_explicit_single_input_kwarg(bob):
    """Passing `single_input=True` with a rule that has `single_input=False`
    should error (or honor the kwarg), not silently swap to False."""
    bob.write("""
        r = Rule("cat $in > $out", single_input=False)
        p = RuleProvider(r, single_input=True)
    """)
    r = bob.run("configure", assert_succesful=False)
    assert_output_contains_needles(r, "ValueError", "single_input")
