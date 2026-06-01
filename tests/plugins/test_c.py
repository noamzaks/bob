"""C plugin: compile real binaries with clang and run them.

Assumes `clang` and `llvm-ar` are on $PATH.
"""

import subprocess

from conftest import assert_output_contains_needles


def _run_binary(path) -> str:
    p = subprocess.run([str(path)], capture_output=True, text=True, timeout=10)
    assert p.returncode == 0, f"{path} exited {p.returncode}: stderr={p.stderr!r}"
    return p.stdout.strip()


_TOOLCHAIN = 'import bob.plugins.c as c\nc.toolchain(ccbin="clang", arbin="llvm-ar")\n'
# `ar` (rather than `llvm-ar`) is always present, so configure/identity tests
# that don't depend on the archiver implementation use this toolchain.
_TOOLCHAIN_AR = 'import bob.plugins.c as c\nc.toolchain(ccbin="clang", arbin="ar")\n'


def test_binary_compiles_and_runs(bob):
    (bob.tmp_path / "main.c").write_text(
        '#include <stdio.h>\nint main(void){puts("ok"); return 0;}\n', "utf-8"
    )
    bob.write(_TOOLCHAIN + 'c.binary("hello", sources=["main.c"])')
    bob.run("build")
    assert _run_binary(bob.build / "hello") == "ok"


def test_cflags_extend_drives_compile_define(bob):
    (bob.tmp_path / "main.c").write_text(
        "#include <stdio.h>\n"
        "int main(void){\n"
        '#ifdef LOUD\n    puts("LOUD");\n'
        '#else\n    puts("quiet");\n'
        "#endif\n    return 0;}\n",
        "utf-8",
    )
    bob.write(
        _TOOLCHAIN
        + 'if config("LOUD") == "y":\n'
        + '    c.cflags.extend(["-DLOUD"])\n'
        + 'c.binary("app", sources=["main.c"])\n',
    )
    bob.run("build")
    assert _run_binary(bob.build / "app") == "quiet"
    bob.run("build", "-F", configs={"LOUD": "y"})
    assert _run_binary(bob.build / "app") == "LOUD"


def test_bundle_threads_public_cflags_into_consumer(bob):
    (bob.tmp_path / "include").mkdir()
    (bob.tmp_path / "include" / "lib.h").write_text("void greet(void);\n", "utf-8")
    (bob.tmp_path / "lib.c").write_text(
        '#include "lib.h"\n#include <stdio.h>\nvoid greet(void){puts("from lib");}\n',
        "utf-8",
    )
    (bob.tmp_path / "main.c").write_text(
        '#include "lib.h"\nint main(void){greet(); return 0;}\n', "utf-8"
    )
    bob.write(
        _TOOLCHAIN
        + 'bundle = c.static_library_bundle("greet", sources=["lib.c"], public_cflags=["-Iinclude"])\n'
        + 'c.binary("app", sources=["main.c"], bundles=[bundle])\n'
    )
    bob.run("build")
    assert _run_binary(bob.build / "app") == "from lib"


def test_toolchain_returns_scope_usable_with_block(bob):
    bob.write("""
        import bob.plugins.c as c
        with c.toolchain(ccbin="clang", arbin="ar"):
            assert c.ccbin.get() == "clang", c.ccbin.get()
            assert c.arbin.get() == "ar", c.arbin.get()
        Rule("echo ok > $out").build("ok.txt")
    """)
    bob.run("configure")


def test_toolchain_passes_binary_name_through_unchanged(bob):
    """The toolchain binaries are stored verbatim, not resolved to paths — a
    name like `clang++` must survive untouched."""
    bob.write("""
        import bob.plugins.c as c
        with c.toolchain(ccbin="clang++", arbin="my-ar"):
            assert c.ccbin.get() == "clang++", c.ccbin.get()
            assert c.arbin.get() == "my-ar", c.arbin.get()
        Rule("echo ok > $out").build("ok.txt")
    """)
    bob.run("configure")


def test_ccbin_and_ccbinvar_are_same_object(bob):
    # `ccbinvar` is the internal alias `toolchain()` writes through; it must be
    # the very same Variable exposed publicly as `ccbin`.
    bob.write("""
        import bob.plugins._c as _c
        assert _c.ccbin is _c.ccbinvar
        Rule("echo ok > $out").build("ok.txt")
    """)
    bob.run("configure")


def test_add_include_path_extends_cflags_only_when_asflags_disabled(bob):
    bob.write("""
        import bob.plugins.c as c
        before_as = list(c.asflags.get())
        with c.add_include_path("inc", extend_asflags=False):
            assert "-Iinc" in c.cflags.get(), c.cflags.get()
            assert c.asflags.get() == before_as
        Rule("echo ok > $out").build("ok.txt")
    """)
    bob.run("configure")


def test_add_include_path_extends_asflags_only_when_cflags_disabled(bob):
    bob.write("""
        import bob.plugins.c as c
        before_c = list(c.cflags.get())
        with c.add_include_path("inc", extend_cflags=False):
            assert "-Iinc" in c.asflags.get(), c.asflags.get()
            assert c.cflags.get() == before_c
        Rule("echo ok > $out").build("ok.txt")
    """)
    bob.run("configure")


def test_static_library_bundle_places_archive_before_dep_ldlibs(bob):
    """A bundle's own archive must precede its dependencies' archives on the
    link line so the linker resolves symbols in the right order."""
    bob.write(
        _TOOLCHAIN_AR
        + 'dep = c.static_library_bundle("dep", sources=["dep.c"])\n'
        + 'top = c.static_library_bundle("top", sources=["top.c"], bundles=[dep])\n'
        + "libs = [str(x) for x in top.ldlibs]\n"
        + 'assert libs[0].endswith("top.a"), libs\n'
        + 'assert any(x.endswith("dep.a") for x in libs[1:]), libs\n'
    )
    bob.run("configure")


def test_default_bundles_provider_resets_between_runs(bob):
    """`default_bundles` is a scoped Provider: a bundle provided inside a
    `with` block is gone once the block exits."""
    bob.write("""
        import bob.plugins._c as _c
        extra = _c.Bundle(cflags=["-DEXTRA"])
        with _c.default_bundles.provide([extra]):
            assert _c.default_bundles.get() == [extra]
        assert _c.default_bundles.get() == []
        Rule("echo ok > $out").build("ok.txt")
    """)
    bob.run("configure")


def test_cc_rule_rejects_multi_output_invocation(bob):
    bob.write(_TOOLCHAIN_AR + 'c.cc("a.o", "b.o", inputs=["a.c"])')
    r = bob.run("configure", assert_succesful=False)
    assert_output_contains_needles(r, "single resolved output")


def test_cc_dep_file_picked_up_on_header_change(bob):
    """`cc` emits a depfile (`deps="gcc"`), so editing an included header
    forces a recompile even though the `.c` file is untouched."""
    (bob.tmp_path / "v.h").write_text("#define VALUE 1\n", "utf-8")
    (bob.tmp_path / "main.c").write_text(
        '#include "v.h"\n#include <stdio.h>\n'
        'int main(void){printf("%d\\n", VALUE); return 0;}\n',
        "utf-8",
    )
    bob.write(_TOOLCHAIN_AR + 'c.binary("app", sources=["main.c"])')
    bob.run("build")
    assert _run_binary(bob.build / "app") == "1"

    import time

    time.sleep(0.1)
    (bob.tmp_path / "v.h").write_text("#define VALUE 2\n", "utf-8")
    bob.run("build")
    assert _run_binary(bob.build / "app") == "2"


def test_binary_with_repeated_bundle_does_not_double_link(bob):
    """Passing the same bundle twice must still produce a working binary."""
    (bob.tmp_path / "include").mkdir()
    (bob.tmp_path / "include" / "lib.h").write_text("void greet(void);\n", "utf-8")
    (bob.tmp_path / "lib.c").write_text(
        '#include "lib.h"\n#include <stdio.h>\nvoid greet(void){puts("from lib");}\n',
        "utf-8",
    )
    (bob.tmp_path / "main.c").write_text(
        '#include "lib.h"\nint main(void){greet(); return 0;}\n', "utf-8"
    )
    bob.write(
        _TOOLCHAIN_AR
        + 'bundle = c.static_library_bundle("greet", sources=["lib.c"], public_cflags=["-Iinclude"])\n'
        + 'c.binary("app", sources=["main.c"], bundles=[bundle, bundle])\n'
    )
    bob.run("build")
    assert _run_binary(bob.build / "app") == "from lib"
