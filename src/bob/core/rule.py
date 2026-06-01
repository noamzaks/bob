"""Bob rules."""

import copy
import inspect
import shlex
from pathlib import Path
from types import FrameType
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    TypeAlias,
    TypeVar,
    Union,
    overload,
)

from bob.core.context import BobContext
from bob.core.expression import Expression
from bob.core.targets import FileTarget, PhonyTarget, RootRelativePath
from bob.core.variable import Variable
from bob.utilities import get_caller_frame

if TYPE_CHECKING:
    from bob.core.provider import RuleProvider

SingleBuildInputType: TypeAlias = Union[
    str, Path, RootRelativePath, FileTarget, PhonyTarget
]
BuildInputType: TypeAlias = Union[
    SingleBuildInputType,
    List[SingleBuildInputType],
    List[str],
    List[Path],
    List[RootRelativePath],
    List[FileTarget],
    List[PhonyTarget],
]


class BuildInput:
    Single: TypeAlias = SingleBuildInputType
    Type: TypeAlias = BuildInputType

    def __init__(self, *args: Any, **kwargs: Any):
        raise Exception(
            "BuildInput.Type is a utility namespace and mustn't be instantiated!"
        )

    @staticmethod
    def add(*inputs: Optional["BuildInput.Type"]) -> List["BuildInput.Single"]:
        """Return a list of single build inputs representing all of the given build inputs."""

        result: List[BuildInput.Single] = []

        for input in inputs:
            if input is None:
                continue

            result += (
                [input]
                if isinstance(
                    input, (str, Path, RootRelativePath, FileTarget, PhonyTarget)
                )
                else input
            )

        return result

    @overload
    @staticmethod
    def resolve(
        *inputs: Optional["BuildInput.Type"],
        single: Literal[False] = False,
        resolve_strings_to_paths: Literal[False] = False,
        path_only: Literal[False] = False,
        _srcdir: Optional[Union[Path, RootRelativePath]] = None,
    ) -> List[Union[str, RootRelativePath]]: ...

    @overload
    @staticmethod
    def resolve(
        *inputs: Optional["BuildInput.Type"],
        single: Literal[False] = False,
        resolve_strings_to_paths: Literal[False] = False,
        path_only: Literal[True] = True,
        _srcdir: Optional[Union[Path, RootRelativePath]] = None,
    ) -> List[RootRelativePath]: ...

    @overload
    @staticmethod
    def resolve(
        *inputs: Optional["BuildInput.Type"],
        single: Literal[True] = True,
        resolve_strings_to_paths: Literal[False] = False,
        path_only: Literal[False] = False,
        _srcdir: Optional[Union[Path, RootRelativePath]] = None,
    ) -> Union[str, RootRelativePath]: ...

    @overload
    @staticmethod
    def resolve(
        *inputs: Optional["BuildInput.Type"],
        single: Literal[True] = True,
        resolve_strings_to_paths: Literal[False] = False,
        path_only: Literal[True] = True,
        _srcdir: Optional[Union[Path, RootRelativePath]] = None,
    ) -> RootRelativePath: ...

    @staticmethod
    def resolve(
        *inputs: Optional["BuildInput.Type"],
        single=False,
        resolve_strings_to_paths=True,
        path_only=False,
        _srcdir: Optional[Union[Path, RootRelativePath]] = None,
    ) -> Union[
        str,
        RootRelativePath,
        List[RootRelativePath],
        List[Union[str, RootRelativePath]],
    ]:
        """
        Resolve the given build inputs.
        :param single: Whether the given inputs should only resolve to a single build input.
        :param resolve_strings_to_paths: Whether string inputs should be interpreted as srcdir-relative paths.
        :param path_only: Whether the inputs must resolve to valid root-relative paths.
        """
        rule_inputs = BuildInput.add(*inputs)

        resolved_srcdir = RootRelativePath(_srcdir) if _srcdir is not None else None

        result: List[Union[str, RootRelativePath]] = []
        for input in rule_inputs:
            if isinstance(input, FileTarget):
                input = input.path

            if isinstance(input, PhonyTarget):
                if path_only:
                    raise ValueError(
                        f"Cannot resolve phony target {input.name} into a path!"
                    )
                else:
                    result.append(input.name)

                continue

            if isinstance(input, str):
                if resolve_strings_to_paths:
                    result.append(RootRelativePath(input, _srcdir=resolved_srcdir))
                elif path_only:
                    raise ValueError(f"Cannot add non-path {input}!")
                else:
                    result.append(input)

                continue

            if isinstance(input, Path):
                result.append(RootRelativePath(input, _srcdir=resolved_srcdir))
                continue

            result.append(input)

        if single:
            if len(result) != 1:
                raise ValueError(f"Required a single resolved output but got: {result}")
            return result[0]

        return result


def _parse_expressions(
    expressions: Optional[BuildInput.Type] = None,
) -> List[Union[Expression, BuildInput.Single]]:
    if expressions is None:
        return []

    if isinstance(expressions, (str, Path, RootRelativePath, FileTarget, PhonyTarget)):
        expressions = [expressions]

    return [
        Expression.parse(expression) if isinstance(expression, str) else expression
        for expression in expressions
    ]


def phony(name: str, inputs: List[str]) -> PhonyTarget:
    context = BobContext.get()

    assert context.writer is not None
    context.writer.build([name], "phony", inputs)

    return PhonyTarget(name)


OutputType = TypeVar("OutputType", FileTarget, List[FileTarget])


class Rule(Generic[OutputType]):
    @overload
    def __new__(
        cls,
        command: str,
        depfile: Optional[str] = None,
        deps: Optional[str] = None,
        compile_command: Optional[str] = None,
        description: Optional[str] = None,
        restat=False,
        generator=False,
        pool: Optional[str] = None,
        always=False,
        implicit: Optional[BuildInput.Type] = None,
        order_only: Optional[BuildInput.Type] = None,
        implicit_outputs: Optional[BuildInput.Type] = None,
        single_input=False,
        single_output: Literal[True] = True,
        _caller_frame: Optional[FrameType] = None,
        **variables: BuildInput.Type,
    ) -> "Rule[FileTarget]": ...

    @overload
    def __new__(
        cls,
        command: str,
        depfile: Optional[str] = None,
        deps: Optional[str] = None,
        compile_command: Optional[str] = None,
        description: Optional[str] = None,
        restat=False,
        generator=False,
        pool: Optional[str] = None,
        always=False,
        implicit: Optional[BuildInput.Type] = None,
        order_only: Optional[BuildInput.Type] = None,
        implicit_outputs: Optional[BuildInput.Type] = None,
        single_input=False,
        single_output: Literal[False] = False,
        _caller_frame: Optional[FrameType] = None,
        **variables: BuildInput.Type,
    ) -> "Rule[List[FileTarget]]": ...

    def __new__(
        cls,
        command: str,
        depfile: Optional[str] = None,
        deps: Optional[str] = None,
        compile_command: Optional[str] = None,
        description: Optional[str] = None,
        restat=False,
        generator=False,
        pool: Optional[str] = None,
        always=False,
        implicit: Optional[BuildInput.Type] = None,
        order_only: Optional[BuildInput.Type] = None,
        implicit_outputs: Optional[BuildInput.Type] = None,
        single_input=False,
        single_output=True,
        _caller_frame: Optional[FrameType] = None,
        **variables: BuildInput.Type,
    ) -> "Union[Rule[FileTarget], Rule[List[FileTarget]]]":
        return super().__new__(
            cls,
        )

    def __init__(
        self,
        command: str,
        depfile: Optional[str] = None,
        deps: Optional[str] = None,
        compile_command: Optional[str] = None,
        description: Optional[str] = None,
        restat=False,
        generator=False,
        pool: Optional[str] = None,
        always=False,
        implicit: Optional[BuildInput.Type] = None,
        order_only: Optional[BuildInput.Type] = None,
        implicit_outputs: Optional[BuildInput.Type] = None,
        single_input=False,
        single_output=True,
        _caller_frame: Optional[FrameType] = None,
        **variables: BuildInput.Type,
    ) -> None:
        """
        A rule for building targets.
        :param command: The command to run for building, can use $variables.
        :param depfile: A generated dependency file.
        :param deps: The format of the generated dependency file.
        :param compile_command: The command to use in the compilation database, if any.
        :param description: The short description of the rule to show in non-verbose mode.
        :param restat: Whether to restat the outputs after building.
        :param generator: Whether this rule's targets shouldn't be cleaned.
        :param pool: A Ninja pool to use for this rule.
        :param always: Whether to always build any targets built by the rule.
        :param implicit: Implicit dependencies which should be added to every target invocation built by the rule.
        :param order_only: Order-only dependencies which should be added to every target invocation built by the rule.
        :param implicit_outputs: Implicit outputs which should be added to every target invocation built by the rule.
        :param single_input: Whether the rule only accepts a single input per build.
        :param single_output: Whether the rule only creates a single output per build.
        :param variables: Initial values for variables.
        """
        context = BobContext.get()

        name = f"bob-rule-{context.rule_index}"
        context.rule_index += 1

        if description is not None:
            name = "".join(c for c in description.lower() if c.isalnum()) + "-" + name

        self.name = name
        self.has_compile_command = compile_command is not None
        self.single_input = single_input
        self.single_output = single_output

        self.command_expression = Expression.parse(command)
        self.depfile_expression = Expression.parse(depfile)
        self.compile_command_expression = Expression.parse(compile_command)

        self.extra_implicit = _parse_expressions(implicit)
        self.extra_order_only = _parse_expressions(order_only)
        self.extra_implicit_outputs = _parse_expressions(implicit_outputs)
        self.provider: Optional[RuleProvider] = None

        self.description = description + " $out" if description is not None else None

        self.variables = (
            self.command_expression.variables
            | self.depfile_expression.variables
            | self.compile_command_expression.variables
        )
        for expression in (
            self.extra_implicit + self.extra_order_only + self.extra_implicit_outputs
        ):
            if not isinstance(expression, Expression):
                continue
            self.variables.update(expression.variables)

        self.always = always

        self.values: Dict[str, BuildInput.Type] = variables

        self._backups: List[Dict[str, BuildInput.Type]] = []

        for key in variables:
            if key not in self.variables:
                raise KeyError(
                    f"{key} is not a variable of the rule and can't be initialized!"
                )

        assert context.writer is not None
        assert context.compdb_writer is not None

        resolved_caller_frame = (
            _caller_frame if _caller_frame is not None else get_caller_frame()
        )
        if resolved_caller_frame is not None:
            context.writer.comment(
                f"Defined in {inspect.getfile(resolved_caller_frame)}:{resolved_caller_frame.f_lineno}"
            )

        if self.has_compile_command:
            context.compdb_writer.rule(
                name=name, command=self.compile_command_expression.expand()
            )

        context.writer.rule(
            name=name,
            command=self.command_expression.expand(),
            description=self.description,
            depfile=self.depfile_expression.expand(),
            deps=deps,
            restat=restat,
            generator=generator,
            pool=pool,
        )

        context.rules.append(self)

    def _resolve(
        self,
        rule_inputs: Optional[BuildInput.Type],
        extras: Optional[List[Union[BuildInput.Single, Expression]]],
        variables: Dict[str, str],
        srcdir: RootRelativePath,
    ) -> List[str]:
        if extras is not None:
            rule_inputs = BuildInput.add(
                rule_inputs or [],
                [
                    extra.expand(**variables)
                    if isinstance(extra, Expression)
                    else extra
                    for extra in extras
                ],
            )

        if rule_inputs is None:
            return []

        return [
            str(x).replace("$", "$$")
            for x in BuildInput.resolve(rule_inputs, _srcdir=srcdir)
        ]

    def build(
        self,
        *outputs: Union[str, Path],
        inputs: Optional[BuildInput.Type] = None,
        implicit: Optional[BuildInput.Type] = None,
        order_only: Optional[BuildInput.Type] = None,
        implicit_outputs: Optional[List[Union[str, Path]]] = None,
        always: Optional[bool] = None,
        dyndep: Optional[str] = None,
        **variables: BuildInput.Type,
    ) -> OutputType:
        """
        Build the given outputs using this rule.
        :param outputs: The built outputs, will be built in the current build directory by default.
        :param inputs: The inputs this build depends on.
        :param implicit: The inputs this build depends on but aren't used in the command line.
        :param order_only: The inputs this build should verify are built before running, but doesn't require rebuilding if they change.
        :param implicit_outputs: Additional outputs generated by the rule which aren't used in the command line.
        :param always: Whether these outputs should always be built.
        :param dyndep: A dynamic dependencies file generated by this specific build.
        :param variables: Variables to use for the command line of the rule for this target.
        """

        context = BobContext.get()

        assert context.writer is not None
        assert context.compdb_writer is not None

        if always is None:
            always = self.always

        if always:
            assert context.always is not None
            implicit = BuildInput.add(implicit or [], context.always)

        variables = {
            **(self.provider.values if self.provider is not None else {}),
            **self.values,
            **variables,
        }
        resolved_variables = {
            key: BuildInput.resolve(value, resolve_strings_to_paths=False)
            for key, value in variables.items()
            if value is not None
        }

        values = {
            key: value[0]
            for key, value in resolved_variables.items()
            if len(value) > 0 and isinstance(value[0], str)
        }
        if self.single_input:
            values["in"] = str(
                BuildInput.resolve(inputs, resolve_strings_to_paths=False, single=True)
            )
        if self.single_output:
            values["out"] = str(
                BuildInput.resolve(
                    *outputs, resolve_strings_to_paths=False, single=True
                )
            )

        resolved_inputs = self._resolve(
            inputs, [], values, srcdir=context.current_source_dir
        )
        resolved_implicit = self._resolve(
            implicit, self.extra_implicit, values, srcdir=context.current_source_dir
        )
        resolved_order_only = self._resolve(
            order_only, self.extra_order_only, values, srcdir=context.current_source_dir
        )
        resolved_outputs = self._resolve(
            list(outputs),
            [],
            values,
            srcdir=context.current_build_dir,
        )
        resolved_implicit_outputs: list[str] = self._resolve(
            implicit_outputs,  # ty:ignore[invalid-argument-type] wtf???
            self.extra_implicit_outputs,
            values,
            srcdir=context.current_build_dir,
        )

        self.command_expression.validate(
            variables,
            allow_unused=self.provider.variables if self.provider is not None else None,
        )

        for expression in (
            self.depfile_expression,
            self.compile_command_expression,
        ):
            expression.validate(variables, allow_unused=True)

        expanded_variables = {
            key: shlex.join(map(str, value))
            if isinstance(value, list)
            else shlex.quote(str(value))
            for key, value in resolved_variables.items()
        }

        if self.has_compile_command:
            context.compdb_writer.build(
                outputs=resolved_outputs,
                rule=self.name,
                inputs=resolved_inputs,
                variables=expanded_variables,
            )

        if not context.allow_build_outside_builddir:
            for output in resolved_outputs:
                if (
                    context.builddir.value.resolve()
                    not in Path(output).resolve().parents
                ):
                    raise ValueError(
                        f"Refusing to build {output} which is outside the build directory!"
                    )

        context.writer.build(
            outputs=resolved_outputs,
            rule=self.name,
            inputs=resolved_inputs,
            implicit=resolved_implicit,
            order_only=resolved_order_only,
            implicit_outputs=resolved_implicit_outputs,
            variables=expanded_variables,
            dyndep=dyndep,
        )

        if self.single_output:
            return FileTarget(
                path=RootRelativePath(
                    resolved_outputs[0], _use_current_source_dir=False
                )
            )  # ty:ignore[invalid-return-type]

        return [
            FileTarget(path=RootRelativePath(output, _use_current_source_dir=False))
            for output in resolved_outputs
        ]  # ty:ignore[invalid-return-type]

    def __getitem__(self, variable: str) -> Variable:
        return Variable(self, name=variable)

    __call__ = build

    def _backup(self):
        self._backups.append(copy.deepcopy(self.values))

    def _restore(self):
        self.values = self._backups.pop()
