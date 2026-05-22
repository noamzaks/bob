"""Bob rules."""

import copy
import inspect
import shlex
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TypeAlias, Union, overload

from bob.core.context import BobContext
from bob.core.expression import Expression
from bob.core.targets import FileTarget, PhonyTarget, RootRelativePath
from bob.core.variable import Variable

SingleRuleInput: TypeAlias = Union[str, Path, RootRelativePath, FileTarget, PhonyTarget]
RuleInput: TypeAlias = Union[SingleRuleInput, List[SingleRuleInput]]


def rule_input_add(*inputs: Optional[RuleInput]):
    result: List[SingleRuleInput] = []
    for input in inputs:
        if input is None:
            continue

        if not isinstance(input, list):
            input = [input]

        result += input

    return result


@overload
def rule_input_resolve(
    *inputs: Optional[RuleInput],
    root: Optional[Union[Path, RootRelativePath]] = None,
    path_only: False = False,
    resolve_strings_to_paths: False = False,
    single: False = False,
) -> List[Union[str, RootRelativePath]]: ...


@overload
def rule_input_resolve(
    *inputs: Optional[RuleInput],
    root: Optional[Union[Path, RootRelativePath]] = None,
    path_only: True = True,
    resolve_strings_to_paths: False = False,
    single: False = False,
) -> List[RootRelativePath]: ...


@overload
def rule_input_resolve(
    *inputs: Optional[RuleInput],
    root: Optional[Union[Path, RootRelativePath]] = None,
    path_only: False = False,
    resolve_strings_to_paths: False = False,
    single: True = True,
) -> Union[str, RootRelativePath]: ...


@overload
def rule_input_resolve(
    *inputs: Optional[RuleInput],
    root: Optional[Union[Path, RootRelativePath]] = None,
    path_only: True = True,
    resolve_strings_to_paths: False = False,
    single: True = True,
) -> RootRelativePath: ...


def rule_input_resolve(
    *inputs: Optional[RuleInput],
    root: Optional[Union[Path, RootRelativePath]] = None,
    path_only=False,
    resolve_strings_to_paths=True,
    single=False,
):
    context = BobContext.get()

    if root is None:
        root = context.current_source_dir

    rule_inputs = rule_input_add(*inputs)

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
                result.append(root / input)
            elif path_only:
                raise ValueError(f"Cannot add non-path {input}!")
            else:
                result.append(input)

            continue

        if isinstance(input, Path):
            result.append(root / input)
            continue

        result.append(input)

    if single:
        if len(result) != 1:
            raise ValueError(f"Required a single resolved output but got: {result}")
        return result[0]

    return result


def _parse_expressions(
    expressions: Optional[RuleInput] = None,
):
    if expressions is None:
        return []

    if not isinstance(expressions, list):
        expressions = [expressions]

    return [
        Expression.parse(expression) if isinstance(expression, str) else expression
        for expression in expressions
    ]


def phony(name: str, inputs: List[str]):
    context = BobContext.get()

    context.writer.build([name], "phony", inputs)

    return PhonyTarget(name)


class Rule:
    def __init__(
        self,
        command: str,
        depfile: Optional[str] = None,
        deps: Optional[str] = None,
        compile_command: Optional[str] = None,
        description: Optional[str] = None,
        restat=False,
        generator: Optional[bool] = None,
        pool: Optional[str] = None,
        always=False,
        implicit: Optional[RuleInput] = None,
        order_only: Optional[RuleInput] = None,
        implicit_outputs: Optional[RuleInput] = None,
        single_input=False,
        single_output=False,
        **variables: RuleInput,
    ):
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

        self.description = description + " $out" if description is not None else None

        self.variables = (
            self.command_expression.variables
            | self.depfile_expression.variables
            | self.compile_command_expression.variables
        )
        for expression in (
            self.extra_implicit + self.extra_order_only + self.extra_implicit_outputs
        ):
            self.variables.update(expression.variables)

        self.always = always

        self.values: Dict[str, RuleInput] = variables

        self._backups: List[Tuple[Rule, Dict[str, Union[str, List[str]]]]] = []
        self.override_rule: Optional[Rule] = None

        for key in variables:
            if key not in self.variables:
                raise KeyError(
                    f"{key} is not a variable of the rule and can't be initialized!"
                )

        try:
            frame = inspect.currentframe().f_back.f_back
            context.writer.comment(
                f"Defined in {inspect.getfile(frame)}:{frame.f_lineno}"
            )
        except Exception:
            pass

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

    def _resolve(
        self,
        rule_inputs: Optional[List[RuleInput]],
        extras: Optional[List[RuleInput]],
        variables: Dict[str, str],
        root: Path,
    ) -> List[str]:
        if extras is not None:
            rule_inputs = (rule_inputs or []) + [
                extra.expand(**variables) if isinstance(extra, Expression) else extra
                for extra in extras
            ]

        if rule_inputs is None:
            return []

        if root is None:
            root = Path(".")

        resolved = rule_input_resolve(*rule_inputs, root=root)

        return resolved

    def build(
        self,
        *outputs: Union[str, Path],
        inputs: Optional[List[RuleInput]] = None,
        implicit: Optional[List[RuleInput]] = None,
        order_only: Optional[List[RuleInput]] = None,
        implicit_outputs: Optional[List[Union[str, Path]]] = None,
        always: Optional[bool] = None,
        dyndep: Optional[str] = None,
        allow_unused=False,
        **variables: RuleInput,
    ):
        """
        Build the given outputs using this rule.
        @param outputs: The built outputs, will be built in the current build directory by default.
        @param inputs: The inputs this build depends on.
        @param implicit: The inputs this build depends on but aren't used in the command line.
        @param order_only: The inputs this build should verify are built before running, but doesn't require rebuilding if they change.
        @param implicit_outputs: Additional outputs generated by the rule which aren't used in the command line.
        @param always: Whether these outputs should always be built.
        @param dyndep: A dynamic dependencies file generated by this specific build.
        @param allow_unused: Whether unused variables are allowed to be specified.
        @param variables: Variables to use for the command line of the rule for this target.
        """

        context = BobContext.get()

        if always is None:
            always = self.always

        if always:
            assert context.always is not None
            implicit = (implicit or []) + [context.always]

        variables = {**self.values, **variables}
        variables = {
            key: rule_input_resolve(value, resolve_strings_to_paths=False)
            for key, value in variables.items()
            if value is not None
        }

        values = {
            key: value for key, value in variables.items() if isinstance(value, str)
        }
        if self.single_input:
            values["in"] = inputs[0]
        if self.single_output:
            values["out"] = outputs[0]

        inputs = self._resolve(inputs, [], values, root=context.current_source_dir)
        implicit = self._resolve(
            implicit, self.extra_implicit, values, root=context.current_source_dir
        )
        order_only = self._resolve(
            order_only, self.extra_order_only, values, root=context.current_source_dir
        )
        outputs = self._resolve(
            list(outputs),
            [],
            values,
            root=context.current_build_dir.value,
        )
        implicit_outputs = self._resolve(
            implicit_outputs,
            self.extra_implicit_outputs,
            values,
            root=context.current_build_dir.value,
        )

        self.command_expression.validate(variables, allow_unused=allow_unused)

        for expression in (
            self.depfile_expression,
            self.compile_command_expression,
        ):
            expression.validate(variables, allow_unused=True)

        variables = {
            key: shlex.join(map(str, value))
            if isinstance(value, list)
            else shlex.quote(str(value))
            for key, value in variables.items()
        }

        outputs = list(map(str, outputs))
        inputs = list(map(str, inputs))

        if self.has_compile_command:
            context.compdb_writer.build(
                outputs=outputs, rule=self.name, inputs=inputs, variables=variables
            )

        if not context.allow_build_outside_builddir:
            for output in outputs:
                if (
                    context.builddir.value.resolve()
                    not in Path(output).resolve().parents
                ):
                    raise ValueError(
                        f"Refusing to build {output} which is outside the build directory!"
                    )

        if self.single_input and len(inputs) != 1:
            raise ValueError(
                f"Cannot build multiple inputs {inputs} in single-input rule!"
            )
        if self.single_output and len(outputs) != 1:
            raise ValueError(
                f"Cannot build multiple outputs {outputs} in single-output rule!"
            )

        context.writer.build(
            outputs=outputs,
            rule=self.name,
            inputs=inputs,
            implicit=list(map(str, implicit)),
            order_only=list(map(str, order_only)),
            implicit_outputs=list(map(str, implicit_outputs)),
            variables=variables,
            dyndep=dyndep,
        )

        if len(outputs) == 1:
            return FileTarget(path=RootRelativePath(outputs[0]))

        return [FileTarget(path=RootRelativePath(output)) for output in outputs]

    def __getitem__(self, variable: str):
        return Variable(self, name=variable)

    __call__ = build

    def _backup(self):
        self._backups.append(copy.deepcopy(self.values))

    def _restore(self):
        self.values = self._backups.pop()
