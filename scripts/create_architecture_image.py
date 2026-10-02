"""Render the actual CommerceGraph architecture as PNG and editable SVG."""

from html import escape
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from commercegraph.audit import audit_graph
from commercegraph.dataset import load_dataset
from commercegraph.graph import build_graph

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "docs" / "diagrams"
WIDTH, HEIGHT = 2560, 1440
INK, MUTED = "#172B35", "#536C77"
TEAL, LINE = "#087F72", "#91A8AE"
image = Image.new("RGB", (WIDTH, HEIGHT), "#F6F8F9")
canvas = ImageDraw.Draw(image)
svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
    f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
    '<title id="title">CommerceGraph architecture</title>',
    '<desc id="desc">Validated JSON builds a local NetworkX graph. A question passes through '
    "Gemini query planning, Python validation and graph retrieval, an evidence bundle, "
    "Gemini answer planning, and Python reference validation and factual rendering. "
    "The interface presents the answer and supporting evidence.</desc>",
    '<rect width="2560" height="1440" fill="#F6F8F9"/>',
]


def font(size, bold=False):
    return ImageFont.truetype(
        str(Path("C:/Windows/Fonts") / ("seguisb.ttf" if bold else "segoeui.ttf")), size
    )


def text(x, y, value, size=28, color=INK, bold=False):
    canvas.text((x, y), value, font=font(size, bold), fill=color, anchor="lt")
    weight = 600 if bold else 400
    svg.append(
        f'<text x="{x}" y="{y + size}" font-family="Segoe UI,Arial,sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{color}">{escape(value)}</text>'
    )


def box(x, y, w, h, fill="#FFFFFF", outline="#DCE6E8", radius=20):
    canvas.rounded_rectangle((x, y, x + w, y + h), radius, fill, outline, width=2)
    svg.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
        f'fill="{fill}" stroke="{outline}" stroke-width="2"/>'
    )


def arrow(points, color=LINE, width=3):
    canvas.line(points, fill=color, width=width, joint="curve")
    x, y = points[-1]
    previous_x, previous_y = points[-2]
    if x > previous_x:
        triangle = [(x, y), (x - 13, y - 7), (x - 13, y + 7)]
    elif x < previous_x:
        triangle = [(x, y), (x + 13, y - 7), (x + 13, y + 7)]
    elif y > previous_y:
        triangle = [(x, y), (x - 7, y - 13), (x + 7, y - 13)]
    else:
        triangle = [(x, y), (x - 7, y + 13), (x + 7, y + 13)]
    canvas.polygon(triangle, fill=color)
    path = " ".join(f"{a},{b}" for a, b in points)
    vertices = " ".join(f"{a},{b}" for a, b in triangle)
    svg.append(f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="{width}"/>')
    svg.append(f'<polygon points="{vertices}" fill="{color}"/>')


def step(x, y, number, title, lines, cloud=False):
    accent = "#7960AA" if cloud else TEAL
    fill = "#F2EDF9" if cloud else "#FFFFFF"
    outline = "#D8CBEA" if cloud else "#DCE6E8"
    box(x, y, 500, 190, fill, outline)
    box(x + 24, y + 27, 48, 48, accent, accent, 14)
    text(x + 37, y + 33, str(number), 28, "#FFFFFF", True)
    text(x + 88, y + 35, title, 31, INK, True)
    for index, line in enumerate(lines):
        text(x + 28, y + 103 + index * 36, line, 26, MUTED)


dataset, _ = load_dataset()
graph = build_graph(dataset)
audit = audit_graph(graph)

text(140, 66, "COMMERCEGRAPH", 25, TEAL, True)
text(140, 112, "From a question to a grounded answer", 60, INK, True)
text(140, 198, "DATA FOUNDATION  /  BUILT LOCALLY AT STARTUP", 24, MUTED, True)

box(140, 250, 550, 140)
text(168, 275, "Synthetic JSON dataset", 34, INK, True)
text(168, 330, "Entities, purchases and typed links", 26, MUTED)
box(865, 250, 550, 140)
text(893, 275, "Pydantic validation", 34, INK, True)
text(893, 330, "Schema, unique IDs and references", 26, MUTED)
box(1590, 250, 830, 140, "#E9F4EF", "#BDDCD1")
text(1618, 275, "NetworkX directed graph + integrity audit", 34, INK, True)
text(
    1618,
    330,
    f"{len(graph)} nodes  ·  {len(graph.edges)} edges  ·  {audit['occurrences']} marker values",
    26,
    MUTED,
)
arrow([(690, 320), (865, 320)])
arrow([(1415, 320), (1590, 320)])
arrow([(1825, 390), (1825, 445), (985, 445), (985, 590)], TEAL)
text(1120, 406, "Canonical IDs + names", 24, TEAL)
arrow([(2175, 390), (2175, 590)], TEAL)
text(2200, 465, "Graph data", 24, TEAL)

text(140, 520, "QUESTION PIPELINE  /  RUNS ONLY ON SUBMIT", 24, MUTED, True)
step(140, 590, 1, "User question", ["Streamlit UI or CLI", "Standalone question"])
step(
    735,
    590,
    2,
    "Gemini · QueryPlan",
    ["Structured operation + filters", "Uses the entity catalog"],
    cloud=True,
)
step(1330, 590, 3, "Validate + resolve", ["Python checks the plan", "Resolves exact names and IDs"])
step(1925, 590, 4, "Graph retrieval", ["Seven approved traversals", "Python reads graph facts"])
for start in (640, 1235, 1830):
    arrow([(start, 685), (start + 95, 685)])
arrow([(2175, 780), (2175, 900)])

step(
    1925, 900, 5, "Evidence bundle", ["Records + supporting paths", "Integer-paise totals + counts"]
)
step(
    1330,
    900,
    6,
    "Gemini · AnswerPlan",
    ["Template + record references", "References to aggregates"],
    cloud=True,
)
step(
    735,
    900,
    7,
    "Validate + render",
    ["Check complete references", "Python fills facts from evidence"],
)
step(
    140, 900, 8, "Answer + evidence", ["UI / CLI · inspect query + graph", "Download CSV and JSON"]
)
for start in (1925, 1330, 735):
    arrow([(start, 995), (start - 95, 995)])
arrow([(2175, 1090), (2175, 1160), (985, 1160), (985, 1090)], TEAL)
text(1330, 1180, "Retrieved facts also feed the Python renderer", 25, TEAL)

box(140, 1270, 2285, 82, "#EDF2F4", "#EDF2F4", 14)
text(
    166,
    1291,
    "Planning failure → explicit error   ·   Presentation failure → labeled evidence fallback",
    29,
    MUTED,
)
text(140, 1380, "LOCAL: Python · NetworkX · Pydantic · Streamlit · Plotly", 24, MUTED)
text(1560, 1380, "PURPLE = GEMINI API    /    TEAL = GRAPH FACTS", 24, "#7960AA", True)

DESTINATION.mkdir(exist_ok=True)
image.save(DESTINATION / "commercegraph-architecture.png")
svg.append("</svg>")
(DESTINATION / "commercegraph-architecture.svg").write_text("\n".join(svg), encoding="utf-8")
print("Architecture PNG and SVG created from the validated packaged dataset.")
