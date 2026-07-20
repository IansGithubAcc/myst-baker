# Two-source potential field (contour)

Two sliders (`separation`, `strength_ratio`) drive one `calc` function
that builds a `go.Contour` trace over a full 2D grid, layered with a
`go.Scatter` trace marking the two source points, a labeled colorbar,
inline contour-line labels, and a dynamic title — a combination no
single trace type can produce on its own.

```{input-slider} separation
:value: 2
:min: 1
:max: 4
:step: 1
```

```{input-slider} strength_ratio
:value: 1
:min: 0.5
:max: 2
:step: 0.1
```

```python{calc}
import math
import plotly.graph_objects as go

def two_source_field(separation, strength_ratio):
    n = 25
    coords = [-5 + 10 * i / (n - 1) for i in range(n)]
    x1, y1 = -separation / 2, 0
    x2, y2 = separation / 2, 0

    z = []
    for yi in coords:
        row = []
        for xi in coords:
            d1 = math.hypot(xi - x1, yi - y1) + 0.3
            d2 = math.hypot(xi - x2, yi - y2) + 0.3
            row.append(1 / d1 - strength_ratio / d2)
        z.append(row)

    fig = go.Figure(data=go.Contour(
        x=coords, y=coords, z=z,
        colorscale="RdBu", reversescale=True,
        contours=dict(showlabels=True, labelfont=dict(size=9, color="white")),
        colorbar=dict(title="potential"),
    ))
    fig.add_trace(go.Scatter(
        x=[x1, x2], y=[y1, y2], mode="markers+text",
        text=["+", "−"], textposition="middle center",
        textfont=dict(color="white", size=16),
        marker=dict(size=18, color=["#8B0000", "#00008B"]),
        showlegend=False,
    ))
    fig.update_layout(
        title=f"Two-source field — separation {separation}, strength ratio {strength_ratio:.1f}",
        xaxis_title="x",
        yaxis_title="y",
        annotations=[
            dict(
                x=0, y=4.6, showarrow=False,
                text=f"sources {separation} apart, strength ratio {strength_ratio:.1f}",
            )
        ],
    )
    return fig
```

```{plot} figure
:data: two_source_field
```
