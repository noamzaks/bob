def test_make_supports_explicit_makefile(bob):
    (bob.tmp_path / "sub").mkdir()
    (bob.tmp_path / "sub" / "MyMake").write_text(
        "$(BUILD)/out:\n\tmkdir -p $(shell dirname $@)\n\techo from-explicit > $@\n",
        "utf-8",
    )
    bob.write("""
        from pathlib import Path
        import bob.plugins.make as m
        m.make("sub/out", dir=Path("sub"), file=Path("MyMake"), flags=["BUILD=" + str(Path(*['..' for _ in curdir().value.parts], '..') / builddir().value / 'sub')])
    """)
    # TODO: A Ninja-compatible jobserver requires GNU Make 4.4+ which we don't have yet in CI.
    bob.run("build", "--no-jobserver")

    for f in bob.build.parent.rglob("*"):
        print(f)
    assert (bob.build / "sub" / "out").read_text("utf-8").strip() == "from-explicit"
