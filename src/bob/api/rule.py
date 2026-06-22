import shlex
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Literal, TypeAlias, TypeVar, overload

from ninja.ninja_syntax import escape as ninja_escape

from bob.api.scope import ScopeList
from bob.api.variable import NINJA_PROVIDED_VARIABLES, Variable
from bob.core.context import Context


@dataclass(frozen=True)
class FileTarget:
    path: Path


@dataclass(frozen=True)
class PhonyTarget:
    name: str


class RuleInput:
    Type: TypeAlias = str | Path | FileTarget | PhonyTarget
    Multiple: TypeAlias = Type | list[Type]

    def __init__(self):
        raise Exception("RuleInput is a utility namespace")

    @overload
    @staticmethod
    def resolve(
        *values: Type,
        convert_strings_to_paths=True,
        path_only: Literal[False] = False,
        convert_to_string: Literal[False] = False,
        single: Literal[True] = True,
    ) -> Path | str: ...

    @overload
    @staticmethod
    def resolve(
        *values: Type,
        convert_strings_to_paths=True,
        path_only: Literal[False] = False,
        convert_to_string: Literal[False] = False,
        single: Literal[False] = False,
    ) -> list[Path | str]: ...

    @overload
    @staticmethod
    def resolve(
        *values: Type,
        convert_strings_to_paths=True,
        path_only: Literal[True] = True,
        convert_to_string: Literal[False] = False,
        single: Literal[True] = True,
    ) -> Path: ...

    @overload
    @staticmethod
    def resolve(
        *values: Type,
        convert_strings_to_paths=True,
        path_only: Literal[True] = True,
        convert_to_string: Literal[False] = False,
        single: Literal[False] = False,
    ) -> list[Path]: ...

    @overload
    @staticmethod
    def resolve(
        *values: Type,
        convert_strings_to_paths=True,
        path_only: Literal[False] = False,
        convert_to_string: Literal[True] = True,
        single: Literal[True] = True,
    ) -> str: ...

    @overload
    @staticmethod
    def resolve(
        *values: Type,
        convert_strings_to_paths=True,
        path_only: Literal[False] = False,
        convert_to_string: Literal[True] = True,
        single: Literal[False] = False,
    ) -> list[str]: ...

    @staticmethod
    def resolve(
        *values: Type,
        convert_strings_to_paths=True,
        path_only=False,
        convert_to_string=False,
        single=True,
    ) -> Path | str | list[str] | list[Path] | list[Path | str]:
        result: list[Path | str] = []

        if single:
            assert len(values) == 1

        for value in values:
            if isinstance(value, FileTarget):
                value = value.path

            if isinstance(value, str) and convert_strings_to_paths:
                value = Path(value)

            if isinstance(value, PhonyTarget):
                value = value.name

            if path_only and not isinstance(value, Path):
                raise ValueError(f"Failed to resolve {value}")

            if convert_to_string:
                value = str(value)

            if single:
                return value

            result.append(value)

        return result


OutputType = TypeVar("OutputType", FileTarget, list[FileTarget])


class Rule[OutputType]:
    @overload
    def __new__(
        cls,
        command: str,
        depfile: None | str = None,
        deps: None | str = None,
        description: None | str = None,
        restat=False,
        generator=False,
        pool: None | str = None,
        always=False,
        compile_command: None | str = None,
        single_input=False,
        single_output: Literal[True] = True,
        variables: None | dict[str, RuleInput.Type] = None,
    ) -> "Rule[FileTarget]": ...

    @overload
    def __new__(
        cls,
        command: str,
        depfile: None | str = None,
        deps: None | str = None,
        description: None | str = None,
        restat=False,
        generator=False,
        pool: None | str = None,
        always=False,
        compile_command: None | str = None,
        single_input=False,
        single_output: Literal[False] = False,
        variables: None | dict[str, RuleInput.Type] = None,
    ) -> "Rule[list[FileTarget]]": ...

    def __new__(
        cls,
        *args,
        **kwargs,
    ) -> "Rule[FileTarget] | Rule[list[FileTarget]]":
        return super().__new__(
            cls,
        )

    def __init__(
        self,
        command: str,
        depfile: None | str = None,
        deps: None | str = None,
        description: None | str = None,
        restat=False,
        generator=False,
        pool: None | str = None,
        always=False,
        compile_command: None | str = None,
        single_input=False,
        single_output=True,
        variables: None | dict[str, RuleInput.Type] = None,
    ):
        context = Context.current()

        rule_index = context.variables.get("rule_index", 1)
        context.variables["rule_index"] = rule_index + 1

        name = f"bob-{rule_index}"
        if description is not None:
            name = "".join(c for c in description.lower() if c.isalnum()) + "-" + name
            description += " $out"

        if variables is None:
            variables = {}

        command_template = Template(command)
        depfile_template = Template(depfile) if depfile is not None else None
        description_template = (
            Template(description) if description is not None else None
        )
        compile_command_template = (
            Template(compile_command) if compile_command is not None else None
        )

        variable_names: set[str] = set()
        for template_name, template in (
            ("command", command_template),
            ("depfile", depfile_template),
            ("description", description_template),
            ("compile command", compile_command_template),
        ):
            if template is None:
                continue

            if not template.is_valid():
                raise ValueError(f"Invalid {template_name}: {depfile}")

            variable_names.update(template.get_identifiers())

        self.name = name
        self.command = command_template
        self.depfile = Template(depfile) if depfile is not None else None
        self.variable_names = variable_names
        self.variables: dict[str, RuleInput.Multiple] = {}
        self.has_compile_command = compile_command is not None
        self.single_input = single_input
        self.single_output = single_output
        self.always = always

        for key, value in variables.items():
            self[key].set(
                RuleInput.resolve(
                    value, convert_strings_to_paths=False, convert_to_string=True
                )
            )

        assert context.writer is not None
        assert context.compdb_writer is not None
        context.writer.rule(
            name=name,
            command=command,
            description=description,
            depfile=depfile,
            generator=generator,
            pool=pool,
            restat=restat,
            deps=deps,
        )
        context.writer.newline()
        if compile_command is not None:
            context.compdb_writer.rule(name=name, command=compile_command)

    def __getitem__(self, name: str) -> Variable:
        return Variable(name, self)

    def build(
        self,
        *outputs: str | Path,
        inputs: None | list[RuleInput.Type] = None,
        implicit: None | list[RuleInput.Type] = None,
        order_only: None | list[RuleInput.Type] = None,
        implicit_outputs: None | list[str | Path] = None,
        pool: None | str = None,
        dyndep: None | str = None,
        variables: None | dict[str, RuleInput.Multiple] = None,
    ) -> OutputType:
        if variables is None:
            variables = {}

        if self.single_output and len(outputs) != 1:
            raise ValueError("Expected a single output!")

        if self.single_input and (inputs is None or len(inputs) != 1):
            raise ValueError("Expected a single input!")

        with ScopeList([self[key].set(value) for key, value in variables.items()]):
            for variable in self.variable_names:
                if (
                    variable not in NINJA_PROVIDED_VARIABLES
                    and variable not in self.variables
                ):
                    raise ValueError(f'Variable "{variable}" is uninitialized')

            context = Context.current()

            resolved_outputs = [context.builddir / output for output in outputs]

            resolved_variables = {
                key: shlex.join(
                    ninja_escape(
                        RuleInput.resolve(
                            v, convert_strings_to_paths=False, convert_to_string=True
                        )
                    )
                    for v in value
                )
                if not isinstance(value, str)
                and not isinstance(value, Path)
                and not isinstance(value, FileTarget)
                and not isinstance(value, PhonyTarget)
                else ninja_escape(
                    RuleInput.resolve(
                        value, convert_strings_to_paths=False, convert_to_string=True
                    )
                )
                for key, value in self.variables.items()
            }

            if self.always:
                implicit = implicit or []
                assert context.always is not None
                implicit.append(context.always)

            resolved_inputs = (
                RuleInput.resolve(
                    *inputs,
                    convert_strings_to_paths=False,
                    convert_to_string=True,
                    single=False,
                )
                if inputs is not None
                else None
            )
            resolved_implicit = (
                RuleInput.resolve(
                    *implicit,
                    convert_strings_to_paths=False,
                    convert_to_string=True,
                    single=False,
                )
                if implicit is not None
                else None
            )

            assert context.writer is not None
            assert context.compdb_writer is not None
            context.writer.build(
                outputs=[str(output) for output in resolved_outputs],
                rule=self.name,
                inputs=resolved_inputs,
                implicit=resolved_implicit,
                order_only=RuleInput.resolve(
                    *order_only,
                    convert_strings_to_paths=False,
                    convert_to_string=True,
                    single=False,
                )
                if order_only is not None
                else None,
                variables=resolved_variables,
                implicit_outputs=list(map(str, implicit_outputs))
                if implicit_outputs is not None
                else None,
                pool=pool,
                dyndep=dyndep,
            )

            if self.has_compile_command:
                context.compdb_writer.build(
                    outputs=[str(output) for output in resolved_outputs],
                    rule=self.name,
                    inputs=resolved_inputs,
                )

            if self.single_output:
                return FileTarget(resolved_outputs[0])  # ty:ignore[invalid-return-type]
            else:
                return [FileTarget(output) for output in resolved_outputs]  # ty:ignore[invalid-return-type]


def phony(name: str, inputs: None | list[RuleInput.Type] = None) -> PhonyTarget:
    context = Context.current()

    assert context.writer is not None
    context.writer.build(
        [name],
        rule="phony",
        inputs=RuleInput.resolve(
            *inputs,
            convert_strings_to_paths=False,
            convert_to_string=True,
            single=False,
        )
        if inputs is not None
        else None,
    )

    return PhonyTarget(name)


def shell_output_rule(
    command: str, pool: None | str = None, single_input=False
) -> Rule[FileTarget]:
    return Rule(
        command=f"(({command}) > $out.new && cmp -s $out $out.new || mv $out.new $out); rm -f $out.new",
        description="SHELL OUTPUT",
        restat=True,
        pool=pool,
        always=True,
        single_input=single_input,
    )
