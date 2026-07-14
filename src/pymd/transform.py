import inspect

from pymd import precompute, render


def inspect_params(func):
    return list(inspect.signature(func).parameters)


def _collect_nodes(ast):
    inputs = {}
    input_nodes = {}
    calc_namespace = {}
    plot_nodes = []

    for child in ast["children"]:
        node_type = child["type"]
        if node_type == "pymd-input-slider":
            name = child["arg"]
            options = child["options"]
            inputs[name] = (options["min"], options["max"], options["step"])
            input_nodes[name] = child
        elif node_type == "pymd-calc-python":
            exec(child["body"], calc_namespace)
        elif node_type == "pymd-plot":
            plot_nodes.append(child)

    return inputs, input_nodes, calc_namespace, plot_nodes


def transform_document(ast):
    inputs, input_nodes, calc_namespace, plot_nodes = _collect_nodes(ast)

    new_children = []
    for child in ast["children"]:
        if child["type"] != "pymd-plot":
            new_children.append(child)
            continue

        function_name = child["options"]["data"]
        if function_name not in calc_namespace:
            raise NameError(
                f"plot block references '{function_name}', which is not "
                f"defined by any calc-python block on this page."
            )
        func = calc_namespace[function_name]
        grid_result = precompute.compute_grid(func, inputs)

        input_specs = [
            {
                "name": name,
                "value": input_nodes[name]["options"]["value"],
                "min": input_nodes[name]["options"]["min"],
                "max": input_nodes[name]["options"]["max"],
                "step": input_nodes[name]["options"]["step"],
            }
            for name in inspect_params(func)
            if name in input_nodes
        ]
        html = render.render_plot(child, grid_result, input_specs)
        new_children.append({"type": "html", "value": html})

    return {**ast, "children": new_children}
