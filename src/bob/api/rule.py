from string import Template

from bob.api.scope import ScopeList
from bob.api.variable import NINJA_PROVIDED_VARIABLES, Variable
from bob.core.context import Context


class Rule:
    def __init__(
        self,
        command: str,
        depfile: None | str = None,
        deps: None | str = None,
        description: None | str = None,
        restat=False,
        generator=False,
        pool: None | str = None,
        compile_command: None | str = None,
        variables: None | dict[str, str] = None,
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
        self.variables: dict[str, str] = {}
        self.has_compile_command = compile_command is not None

        for key, value in variables.items():
            self[key].provide(value)

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
        *outputs: str,
        inputs: None | list[str] = None,
        implicit: None | list[str] = None,
        order_only: None | list[str] = None,
        implicit_outputs: None | list[str] = None,
        pool: None | str = None,
        dyndep: None | str = None,
        variables: None | dict[str, str] = None,
    ):
        if variables is None:
            variables = {}

        with ScopeList([self[key].provide(value) for key, value in variables.items()]):
            for variable in self.variable_names:
                if (
                    variable not in NINJA_PROVIDED_VARIABLES
                    and variable not in self.variables
                ):
                    raise ValueError(f'Variable "{variable}" is uninitialized')

            context = Context.current()

            resolved_outputs = [str(context.builddir / output) for output in outputs]

            assert context.writer is not None
            assert context.compdb_writer is not None
            context.writer.build(
                outputs=resolved_outputs,
                rule=self.name,
                inputs=inputs,
                implicit=implicit,
                order_only=order_only,
                variables=self.variables,
                implicit_outputs=implicit_outputs,
                pool=pool,
                dyndep=dyndep,
            )

            if self.has_compile_command:
                context.compdb_writer.build(
                    outputs=resolved_outputs, rule=self.name, inputs=inputs
                )
