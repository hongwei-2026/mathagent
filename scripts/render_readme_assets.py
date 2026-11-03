"""Render README architecture PNGs (GitHub-friendly)."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "docs" / "assets"


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def rounded(draw: ImageDraw.ImageDraw, xy, r, fill, outline=None, width=2):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def render_stack() -> None:
    w, h = 1200, 560
    img = Image.new("RGB", (w, h), "#0f1419")
    d = ImageDraw.Draw(img)
    d.text((50, 36), "MathAgent — four layers", fill="#e8eef5", font=font(36, True))
    d.text(
        (50, 86),
        "tool solve → formal/econ → research lattice → think pillars",
        fill="#8b9bb0",
        font=font(20),
    )
    layers = [
        (
            "1  Tool Agent",
            "LLM <-> SymPy / sandboxed Python · ToRA / MathChat · solve / eval",
            "#7dd3fc",
            "#243447",
        ),
        (
            "2  Formal / Econ",
            "cheap certify → repair → decompose → escalate · Lean · formal / econ",
            "#86efac",
            "#243447",
        ),
        (
            "3  MathLattice",
            "typed graph · abduction A->E · MDL · library sleep · lattice-gate",
            "#fcd34d",
            "#243447",
        ),
        (
            "4  Think pillars",
            "executable library · hypothesis arena · evidence ledger · --think",
            "#93c5fd",
            "#2a3f55",
        ),
    ]
    y = 140
    for title, sub, accent, bg in layers:
        rounded(d, (50, y, w - 50, y + 85), 14, bg, "#3d5a73", 2)
        d.text((74, y + 18), title, fill=accent, font=font(24, True))
        d.text((74, y + 50), sub, fill="#c5d0dc", font=font(18))
        y += 100
    img.save(OUT / "stack-overview.png")


def render_lattice() -> None:
    w, h = 1200, 620
    img = Image.new("RGB", (w, h), "#0f1419")
    d = ImageDraw.Draw(img)
    d.text((50, 30), "MathLattice loop", fill="#e8eef5", font=font(36, True))
    d.text(
        (50, 78),
        "conjecture → typed memory → wake certify → sleep library · honest Gaps",
        fill="#8b9bb0",
        font=font(18),
    )
    rounded(d, (400, 220, 800, 420), 16, "#1e2d3d", "#5b8def", 3)
    d.text((600, 270), "Research Graph", fill="#93c5fd", font=font(26, True), anchor="mm")
    d.text((600, 315), "Target · Conjecture · Lemma", fill="#c5d0dc", font=font(18), anchor="mm")
    d.text((600, 345), "Gap · Concept · Plan", fill="#c5d0dc", font=font(18), anchor="mm")
    d.text((600, 385), "only certified → Lemma", fill="#8b9bb0", font=font(16), anchor="mm")
    rounded(d, (440, 120, 760, 180), 10, "#243447", "#3d5a73", 2)
    d.text((600, 150), "Conjecture pool", fill="#fcd34d", font=font(22, True), anchor="mm")
    d.line([(600, 180), (600, 220)], fill="#7dd3fc", width=3)
    rounded(d, (50, 250, 320, 390), 12, "#1a2e24", "#86efac", 2)
    d.text((185, 290), "WAKE", fill="#86efac", font=font(24, True), anchor="mm")
    d.text((185, 330), "econ / Lean / SymPy", fill="#c5d0dc", font=font(16), anchor="mm")
    d.text((185, 360), "call_op · or Gap", fill="#c5d0dc", font=font(16), anchor="mm")
    d.line([(320, 320), (400, 320)], fill="#7dd3fc", width=3)
    rounded(d, (880, 250, 1150, 390), 12, "#2a2438", "#c4b5fd", 2)
    d.text((1015, 290), "SLEEP", fill="#c4b5fd", font=font(24, True), anchor="mm")
    d.text((1015, 330), "library_ops → Concept", fill="#c5d0dc", font=font(16), anchor="mm")
    d.text((1015, 360), "gated · not fake lemmas", fill="#c5d0dc", font=font(16), anchor="mm")
    d.line([(800, 320), (880, 320)], fill="#7dd3fc", width=3)
    rounded(d, (50, 460, 1150, 570), 12, "#1a2332", "#3d5a73", 2)
    d.text((70, 495), "Concept-value A->E", fill="#e8eef5", font=font(22, True))
    d.text(
        (70, 535),
        "Abduction → Concept slots → Analogy → Curator → Human gate (lattice-gate)",
        fill="#8b9bb0",
        font=font(18),
    )
    img.save(OUT / "lattice-loop.png")


def render_think() -> None:
    w, h = 1200, 580
    img = Image.new("RGB", (w, h), "#0f1419")
    d = ImageDraw.Draw(img)
    d.text((50, 30), "Think — three pillars", fill="#e8eef5", font=font(36, True))
    d.text(
        (50, 78),
        "callable · killable · accountable across runs",
        fill="#8b9bb0",
        font=font(18),
    )
    pillars = [
        (
            50,
            "#1a2e24",
            "#86efac",
            "1",
            "Executable library",
            "DreamCoder-style",
            ["templates + binding", "wake → call_op", "invoke telemetry"],
        ),
        (
            420,
            "#2a2430",
            "#fcd34d",
            "2",
            "Hypothesis arena",
            "Lakatos / IBE",
            ["cheap discriminators", "same-gap rivals", "REJECTED losers"],
        ),
        (
            790,
            "#1a2838",
            "#7dd3fc",
            "3",
            "Evidence ledger",
            "CoEvo / lifelong",
            ["evidence.jsonl", "delta graph_dl", "boost / demote"],
        ),
    ]
    for x, bg, accent, num, title, sub, bullets in pillars:
        rounded(d, (x, 120, x + 340, 400), 14, bg, accent, 3)
        d.text((x + 170, 165), num, fill=accent, font=font(32, True), anchor="mm")
        d.text((x + 170, 210), title, fill="#e8eef5", font=font(22, True), anchor="mm")
        d.text((x + 170, 250), sub, fill="#c5d0dc", font=font(16), anchor="mm")
        yy = 295
        for b in bullets:
            d.text((x + 170, yy), b, fill="#a8b8c8", font=font(16), anchor="mm")
            yy += 28
    rounded(d, (50, 440, 1150, 540), 12, "#1a2332", "#3d5a73", 2)
    d.text((600, 475), "run cycle", fill="#e8eef5", font=font(20, True), anchor="mm")
    d.text(
        (600, 510),
        "start (priors) → wake (call_op) → mid (cheap + arena) → end (delta-dl ledger)",
        fill="#8b9bb0",
        font=font(16),
        anchor="mm",
    )
    img.save(OUT / "think-pillars.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    render_stack()
    render_lattice()
    render_think()
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
