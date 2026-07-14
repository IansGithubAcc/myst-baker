import json


def render_plot(plot_node, grid_result):
    return f'<script type="application/json">{json.dumps(grid_result)}</script>'
