from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Generator, List, Optional, Tuple, Union

from bob.prelude import *

cc = Rule(
    "$ccbin -MMD -MT $out -MF $out.d $cflags -c $in -o $out",
    description="CC",
    depfile="$out.d",
    deps="gcc",
    compile_command="$ccbin -MMD -MT $out -MF $out.d $cflags -c $in -o $out",
)
cc_provider = RuleProvider(cc)
asm = Rule(
    "$asbin -MMD -MT $out -MF $out.d $asflags -c $in -o $out",
    description="AS",
    depfile="$out.d",
    deps="gcc",
    compile_command="$asbin -MMD -MT $out -MF $out.d $asflags -c $in -o $out",
)
asm_provider = RuleProvider(asm)
ld = Rule(
    "$ldbin $cflags $ldflags -o $out $in $ldlibs",
    description="LD",
)
ld_provider = RuleProvider(ld)
ar = Rule(
    "rm -f $out && $arbin crs $out $in",
    description="AR",
)
ar_provider = RuleProvider(ar)

ccbin = cc_provider["ccbin"]
asbin = asm_provider["asbin"]
ldbin = ld_provider["ldbin"]
arbin = ar_provider["arbin"]

cflags = variable("cflags", cc_provider, ld_provider)
asflags = asm_provider["asflags"]
ldflags = ld_provider["ldflags"]

cflags.provide(["-fdiagnostics-color=always"])
asflags.provide([])
ldflags.provide([])


@dataclass
class Bundle:
    """A bundle that can be used to create dependent binaries and libraries."""

    objects: BuildInput.Type = field(default_factory=list)
    ldlibs: BuildInput.Type = field(default_factory=list)
    order_only: Optional[BuildInput.Type] = None
    cflags: List[str] = field(default_factory=list)
    asflags: List[str] = field(default_factory=list)
    ldflags: List[str] = field(default_factory=list)

    def __add__(self, other: "Bundle"):
        return Bundle(
            objects=BuildInput.add(self.objects, other.objects),
            order_only=BuildInput.add(self.order_only, other.order_only),
            ldlibs=BuildInput.add(self.ldlibs, other.ldlibs),
            cflags=self.cflags + other.cflags,
            asflags=self.asflags + other.asflags,
            ldflags=self.ldflags + other.ldflags,
        )

    @contextmanager
    def _scope(
        self,
    ) -> Generator[
        Tuple[BuildInput.Type, BuildInput.Type, Optional[BuildInput.Type]], None, None
    ]:
        with (
            cflags.extend(self.cflags),
            asflags.extend(self.asflags),
            ldflags.extend(self.ldflags),
        ):
            yield self.objects, self.ldlibs, self.order_only


default_bundles = Provider[List[Bundle]]([])
"""The default bundles to use for C targets."""

objects: List[FileTarget] = []
"""All built C objects."""


def object(
    source: BuildInput.Single,
    bundles: Optional[List[Bundle]] = None,
    implicit: Optional[BuildInput.Type] = None,
    order_only: Optional[BuildInput.Type] = None,
    implicit_outputs: Optional[List[Union[str, Path]]] = None,
    name_transform: Callable[[Path], Union[str, Path]] = lambda s: s,
) -> FileTarget:
    """Build a C object created from the given C or Assembly source file."""

    source_path = BuildInput.resolve(source, path_only=True, single=True)

    name = name_transform(source_path.with_suffix(".o").value)

    with sum((bundles or []) + default_bundles.get(), Bundle())._scope() as (
        bundle_objects,
        bundle_ldlibs,
        bundle_order_only,
    ):
        if source_path.suffix == ".c":
            cc = cc_provider.get()
            result = cc(
                name,
                inputs=[source],
                implicit=implicit,
                order_only=BuildInput.add(order_only, bundle_order_only),
                implicit_outputs=implicit_outputs,
            )
        elif source_path.suffix == ".S" or source_path.suffix == ".s":
            asm = asm_provider.get()
            result = asm(
                name,
                inputs=[source],
                implicit=implicit,
                order_only=BuildInput.add(order_only, bundle_order_only),
                implicit_outputs=implicit_outputs,
            )
        else:
            raise ValueError(f"Unknown C source extension for file: {source_path}")

    objects.append(result)
    return result


@contextmanager
def _expand(
    name: str,
    sources: List[BuildInput.Single],
    inputs: Optional[BuildInput.Type] = None,
    bundles: Optional[List[Bundle]] = None,
    implicit: Optional[BuildInput.Type] = None,
    order_only: Optional[BuildInput.Type] = None,
) -> Generator[Tuple[BuildInput.Type, BuildInput.Type], None, None]:
    if inputs is None:
        inputs = []

    if not isinstance(inputs, list):
        inputs = [inputs]

    total_bundles = sum((bundles or []) + default_bundles.get(), Bundle())

    yield (
        BuildInput.add(
            *[
                object(
                    source,
                    implicit=implicit,
                    order_only=order_only,
                    bundles=bundles,
                    name_transform=lambda p: Path("obj") / name / p,
                )
                for source in sources
            ],
            inputs or [],
            total_bundles.objects,
        ),
        total_bundles.ldlibs,
    )
    return


def binary(
    name: str,
    sources: List[BuildInput.Single],
    inputs: Optional[BuildInput.Type] = None,
    bundles: Optional[List[Bundle]] = None,
    implicit: Optional[BuildInput.Type] = None,
    order_only: Optional[BuildInput.Type] = None,
    implicit_outputs: Optional[List[Union[str, Path]]] = None,
    ldlibs: Optional[List[str]] = None,
) -> FileTarget:
    """Build a binary from the given C sources and additional inputs."""

    if ldlibs is None:
        ldlibs = []

    ld = ld_provider.get()

    with (
        _expand(
            name=name,
            sources=sources,
            inputs=inputs,
            bundles=bundles,
            implicit=implicit,
            order_only=order_only,
        ) as (inputs, bundle_ldlibs),
        ld["ldlibs"].provide(BuildInput.add(*ldlibs, bundle_ldlibs)),
    ):
        return ld(
            name,
            inputs=inputs,
            implicit=bundle_ldlibs,
            implicit_outputs=implicit_outputs,
        )


def static_library(
    name: str,
    sources: List[BuildInput.Single],
    inputs: Optional[BuildInput.Type] = None,
    bundles: Optional[List[Bundle]] = None,
    implicit: Optional[BuildInput.Type] = None,
    order_only: Optional[BuildInput.Type] = None,
    implicit_outputs: Optional[List[Union[str, Path]]] = None,
) -> FileTarget:
    """Build a static archive from the given C sources and additional inputs."""

    ar = ar_provider.get()

    with _expand(
        name=name,
        sources=sources,
        inputs=inputs,
        bundles=bundles,
        implicit=implicit,
        order_only=order_only,
    ) as (inputs, bundle_ldlibs):
        return ar(name + ".a", inputs=inputs, implicit_outputs=implicit_outputs)


def static_library_bundle(
    name: str,
    sources: List[BuildInput.Single],
    inputs: Optional[BuildInput.Type] = None,
    bundles: Optional[List[Bundle]] = None,
    public_cflags: Optional[List[str]] = None,
    public_asflags: Optional[List[str]] = None,
    public_ldflags: Optional[List[str]] = None,
    implicit: Optional[BuildInput.Type] = None,
    order_only: Optional[BuildInput.Type] = None,
    implicit_outputs: Optional[List[Union[str, Path]]] = None,
) -> Bundle:
    """Build a static archive from the given C sources and additional inputs and return a bundle which lets other binaries and libraries use this library."""

    if public_cflags is None:
        public_cflags = []
    if public_asflags is None:
        public_asflags = []
    if public_ldflags is None:
        public_ldflags = []

    with (
        cflags.extend(public_cflags),
        asflags.extend(public_asflags),
        ldflags.extend(public_ldflags),
    ):
        library = static_library(
            name=name,
            sources=sources,
            inputs=inputs,
            bundles=bundles,
            implicit=implicit,
            order_only=order_only,
            implicit_outputs=implicit_outputs,
        )

    ldlibs: BuildInput.Type = BuildInput.add(
        library.path,
        *[bundle.ldlibs for bundle in (bundles or []) + default_bundles.get()],
    )

    return Bundle(
        ldlibs=ldlibs,
        cflags=public_cflags,
        asflags=public_asflags,
        ldflags=public_ldflags,
    )


ccbinvar = ccbin
asbinvar = asbin
ldbinvar = ldbin
arbinvar = arbin


def toolchain(
    ccbin: BuildInput.Type,
    arbin: BuildInput.Type,
    asbin: Optional[BuildInput.Type] = None,
    ldbin: Optional[BuildInput.Type] = None,
) -> Scope:
    """
    Return a scope using the given C toolchain.
    The `ccbin` is used for `asbin` and `ldbin` if they aren't provided.
    """

    if asbin is None:
        asbin = ccbin

    if ldbin is None:
        ldbin = ccbin

    return (
        ccbinvar.provide(ccbin)
        | asbinvar.provide(asbin)
        | ldbinvar.provide(ldbin)
        | arbinvar.provide(arbin)
    )


def add_include_path(
    path: BuildInput.Type, extend_cflags=True, extend_asflags=True
) -> Scope:
    flags = [f"-I{p}" for p in BuildInput.resolve(path, path_only=True)]

    scopes: List[Scope] = []
    if extend_cflags:
        scopes.append(cflags.extend(flags))
    if extend_asflags:
        scopes.append(asflags.extend(flags))

    return ScopeList(scopes)


__all__ = [
    "cc",
    "asm",
    "ld",
    "ar",
    "ccbin",
    "asbin",
    "ldbin",
    "arbin",
    "cc_provider",
    "asm_provider",
    "ld_provider",
    "ar_provider",
    "cflags",
    "asflags",
    "ldflags",
    "Bundle",
    "object",
    "binary",
    "static_library",
    "static_library_bundle",
    "toolchain",
    "add_include_path",
    "objects",
    "default_bundles",
]
