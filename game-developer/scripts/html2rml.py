#!/usr/bin/env python3
"""html2rml: a designer HTML mock -> a Nucleon game UI document (RmlUi 6.0 .rml + .rcss), standard library only.

  python html2rml.py mock.html PROJECT/UI/menu/menu.rml [--state N] [--model menu] [--skin skin:skin.rcss]
                     [--map /p/=PROJECT] [--strip-class cap] [--keep-class cap] [--no-plate]

Writes <name>.rml, <name>.rcss, <name>.fonts.lua (the @font-face files as UI.loadFont calls) and <name>.conv.json (the report:
fonts, assets, notes), and prints the same report as one JSON line on stdout.

What it does (RmlUi 6.0 as vendored in Nucleon, engine render interface without shaders or layers; docs/engine/GAME_UI.md):
- var(): resolved everywhere (rules, @keyframes, style="" attributes) from the :root / html / body custom properties, with fallbacks.
- units: px -> dp, rem -> dp (16), em / vw / vh / % kept (RmlUi has them), vmin / vmax -> vh / vw (landscape), pt/cm/mm/in -> dp, ms -> s.
- colors: rgb()/rgba()/hsl() -> #RRGGBBAA (RmlUi reads the rgba alpha as 0-255), CSS named colors -> hex.
- border shorthands: the style keyword (solid, dashed...) is removed (RmlUi's border is "width color"; with a style it drops the border).
- backgrounds: color -> background-color; url() -> decorator: image(path fit align) from background-size/-repeat/-position (also from
  the element's class rules for an inline background-image); linear-gradient -> horizontal-gradient / vertical-gradient with the direction
  kept (to top / to left reverse the colors; angles snap to the nearest axis); the engine has no shader support, so linear-gradient()
  decorators would draw nothing.
- transitions / animations: CSS easing -> RmlUi tweens (ease-out -> cubic-out, ease-in-out -> cubic-in-out, ease -> quadratic-in-out,
  linear -> linear-in-out, cubic-bezier -> cubic-in-out), unknown property names dropped, "all" alone.
- text-shadow -> font-effect shadow()/glow(); -webkit-text-stroke -> font-effect outline().
- @font-face: dropped from the RCSS, listed in "fonts" and written to <name>.fonts.lua (UI.loadFont); the family name is read from the
  font file (RmlUi matches the file's own family) and every font-family in the output is renamed to it when the mock used another name.
- Variant Studio parts stripped: elements with class concept / cap / caption / vs-only / vs-caption (caption strips), data-vs-* only
  attributes, rules on html[data-vs-*] and on the stripped classes. --state N keeps the Nth of the stacked state frames (class frame or
  state) of a multi-state mock.
- whitespace: RmlUi drops whitespace-only text nodes, so a space between two inline elements becomes a no-break space; text runs are
  never re-indented.
- paths: /p/... (the Variant Studio server) maps to the project folder (found from the mock), every asset path is written relative to the
  .rml with the case it has on disk; missing files are reported.
- a small user-agent sheet (div/p/h1.. block, b bold, i italic...) starts the RCSS: RmlUi has no default style sheet.
Unsupported (reported in "notes"): box-shadow, filter, backdrop-filter, mask, radial/conic gradients, multi-stop gradients (approximated by
the first and last color), CSS grid (flex wrap), calc() mixing units, pseudo-elements, :is/:where/:has, @media.
"""
import argparse
import colorsys
import html
import json
import os
import re
import struct
import sys
from html.parser import HTMLParser

# --- RmlUi 6.0 knowledge (third_party/rmlui/Source/Core/StyleSheetSpecification.cpp) ---------------------------------------
RML_PROPS = set("""align-content align-items align-self animation backdrop-filter background background-color border border-bottom
border-bottom-color border-bottom-left-radius border-bottom-right-radius border-bottom-width border-color border-left border-left-color
border-left-width border-radius border-right border-right-color border-right-width border-top border-top-color border-top-left-radius
border-top-right-radius border-top-width border-width bottom box-shadow box-sizing caret-color clear clip color column-gap cursor decorator
display drag fill-image filter flex flex-basis flex-direction flex-flow flex-grow flex-shrink flex-wrap float focus font font-effect
font-family font-size font-style font-weight gap height image-color justify-content left letter-spacing line-height margin margin-bottom
margin-left margin-right margin-top mask-image max-height max-width min-height min-width nav nav-down nav-left nav-right nav-up opacity
overflow overflow-x overflow-y overscroll-behavior padding padding-bottom padding-left padding-right padding-top perspective
perspective-origin perspective-origin-x perspective-origin-y pointer-events position right row-gap scrollbar-margin tab-index text-align
text-decoration text-transform top transform transform-origin transform-origin-x transform-origin-y transform-origin-z transition
vertical-align visibility white-space width word-break z-index""".split())
# Parsed by RmlUi but not drawn by the engine's render interface (no CompileShader / layers / clip mask): dropped on purpose.
NOT_DRAWN = {"box-shadow": "box-shadow (needs render layers the engine does not have)",
             "filter": "filter (no render layers in the engine)",
             "backdrop-filter": "backdrop-filter (no render layers; Graphics.setMenuBackdrop blurs the 3D frame instead)",
             "mask-image": "mask-image (no clip mask in the engine)"}
DYNAMIC_PSEUDO = {"hover", "active", "focus", "focus-visible", "checked", "disabled", "selected"}
STRUCT_PSEUDO = {"nth-child", "nth-last-child", "nth-of-type", "nth-last-of-type", "first-child", "last-child", "first-of-type",
                 "last-of-type", "only-child", "only-of-type", "empty", "not"}
TWEENS = {"ease": "quadratic-in-out", "ease-in": "cubic-in", "ease-out": "cubic-out", "ease-in-out": "cubic-in-out",
          "linear": "linear-in-out", "step-start": "linear-in-out", "step-end": "linear-in-out"}
RML_TWEEN_RE = re.compile(r"^(back|bounce|circular|cubic|elastic|exponential|linear|quadratic|quartic|quintic|sine)-(in|out|in-out)$")
BORDER_STYLES = {"solid", "dashed", "dotted", "double", "groove", "ridge", "inset", "outset", "none", "hidden"}

VOID = {"img", "input", "br", "hr", "meta", "link", "source", "wbr", "col", "area", "base", "embed", "param", "track"}
DROP_TAGS = {"script", "noscript", "iframe", "svg", "canvas", "audio", "template", "object", "picture", "map"}
RENAME = {"a": "div", "nav": "div", "header": "div", "footer": "div", "main": "div", "section": "div", "article": "div",
          "aside": "div", "figure": "div", "figcaption": "div", "ul": "div", "ol": "div", "li": "div", "label": "span",
          "strong": "b", "em": "i", "small": "span", "h4": "div", "h5": "div", "h6": "div", "dl": "div", "dt": "div", "dd": "div",
          "code": "span", "kbd": "span", "mark": "span", "time": "span", "abbr": "span", "cite": "span", "u": "span", "s": "span",
          "sub": "span", "sup": "span", "blockquote": "div", "address": "div", "details": "div", "summary": "div", "dialog": "div"}
KEEP_ATTRS = {"id", "class", "style", "src", "type", "value", "name", "checked", "disabled", "autofocus", "min", "max",
              "step", "placeholder", "for", "selected", "maxlength", "size", "rows", "cols", "multiple", "loop", "muted", "autoplay"}
BLOCK_TAGS = {"div", "p", "h1", "h2", "h3", "pre", "hr", "form", "table", "body", "tr", "td", "th", "thead", "tbody", "tfoot", "video"}
INLINE_TAGS = {"span", "b", "i", "img", "button", "input", "select", "textarea", "progress", "br"}
# Variant Studio presentation parts: never part of the game screen.
ANON_TAG = "anon"   # wraps text that sits straight in a flex container (no mock selector matches this tag)
STRIP_CLASSES = {"concept", "cap", "caption", "vs-only", "vs-cap", "vs-caption", "vs-label", "vs-note"}
STATE_CLASSES = ("frame", "state")
UA_SHEET = """/* user-agent defaults (RmlUi has no default style sheet) */
body { display: block; font-size: 16dp; color: #000000; }
div, p, h1, h2, h3, pre, hr, form { display: block; }
p { margin: 1em 0dp; }
h1 { font-size: 2em; margin: 0.67em 0dp; font-weight: bold; }
h2 { font-size: 1.5em; margin: 0.83em 0dp; font-weight: bold; }
h3 { font-size: 1.17em; margin: 1em 0dp; font-weight: bold; }
b { font-weight: bold; }
i { font-style: italic; }
pre { white-space: pre; }
table { display: table; }
tr { display: table-row; }
thead, tbody, tfoot { display: table-row-group; }
td, th { display: table-cell; }
th { font-weight: bold; }
input, select, textarea, button, progress { display: inline-block; }
"""

NAMED_COLORS = {
    "aliceblue": "#F0F8FF", "antiquewhite": "#FAEBD7", "aquamarine": "#7FFFD4", "azure": "#F0FFFF", "beige": "#F5F5DC",
    "bisque": "#FFE4C4", "blanchedalmond": "#FFEBCD", "blueviolet": "#8A2BE2", "brown": "#A52A2A", "burlywood": "#DEB887",
    "cadetblue": "#5F9EA0", "chartreuse": "#7FFF00", "chocolate": "#D2691E", "coral": "#FF7F50", "cornflowerblue": "#6495ED",
    "cornsilk": "#FFF8DC", "crimson": "#DC143C", "cyan": "#00FFFF", "darkblue": "#00008B", "darkcyan": "#008B8B",
    "darkgoldenrod": "#B8860B", "darkgray": "#A9A9A9", "darkgrey": "#A9A9A9", "darkgreen": "#006400", "darkkhaki": "#BDB76B",
    "darkmagenta": "#8B008B", "darkolivegreen": "#556B2F", "darkorange": "#FF8C00", "darkorchid": "#9932CC", "darkred": "#8B0000",
    "darksalmon": "#E9967A", "darkseagreen": "#8FBC8F", "darkslateblue": "#483D8B", "darkslategray": "#2F4F4F",
    "darkslategrey": "#2F4F4F", "darkturquoise": "#00CED1", "darkviolet": "#9400D3", "deeppink": "#FF1493",
    "deepskyblue": "#00BFFF", "dimgray": "#696969", "dimgrey": "#696969", "dodgerblue": "#1E90FF", "firebrick": "#B22222",
    "floralwhite": "#FFFAF0", "forestgreen": "#228B22", "gainsboro": "#DCDCDC", "ghostwhite": "#F8F8FF", "gold": "#FFD700",
    "goldenrod": "#DAA520", "greenyellow": "#ADFF2F", "honeydew": "#F0FFF0", "hotpink": "#FF69B4", "indianred": "#CD5C5C",
    "indigo": "#4B0082", "ivory": "#FFFFF0", "khaki": "#F0E68C", "lavender": "#E6E6FA", "lavenderblush": "#FFF0F5",
    "lawngreen": "#7CFC00", "lemonchiffon": "#FFFACD", "lightblue": "#ADD8E6", "lightcoral": "#F08080", "lightcyan": "#E0FFFF",
    "lightgoldenrodyellow": "#FAFAD2", "lightgray": "#D3D3D3", "lightgrey": "#D3D3D3", "lightgreen": "#90EE90",
    "lightpink": "#FFB6C1", "lightsalmon": "#FFA07A", "lightseagreen": "#20B2AA", "lightskyblue": "#87CEFA",
    "lightslategray": "#778899", "lightslategrey": "#778899", "lightsteelblue": "#B0C4DE", "lightyellow": "#FFFFE0",
    "limegreen": "#32CD32", "linen": "#FAF0E6", "magenta": "#FF00FF", "mediumaquamarine": "#66CDAA", "mediumblue": "#0000CD",
    "mediumorchid": "#BA55D3", "mediumpurple": "#9370DB", "mediumseagreen": "#3CB371", "mediumslateblue": "#7B68EE",
    "mediumspringgreen": "#00FA9A", "mediumturquoise": "#48D1CC", "mediumvioletred": "#C71585", "midnightblue": "#191970",
    "mintcream": "#F5FFFA", "mistyrose": "#FFE4E1", "moccasin": "#FFE4B5", "navajowhite": "#FFDEAD", "oldlace": "#FDF5E6",
    "olivedrab": "#6B8E23", "orangered": "#FF4500", "orchid": "#DA70D6", "palegoldenrod": "#EEE8AA", "palegreen": "#98FB98",
    "paleturquoise": "#AFEEEE", "palevioletred": "#DB7093", "papayawhip": "#FFEFD5", "peachpuff": "#FFDAB9", "peru": "#CD853F",
    "pink": "#FFC0CB", "plum": "#DDA0DD", "powderblue": "#B0E0E6", "rebeccapurple": "#663399", "rosybrown": "#BC8F8F",
    "royalblue": "#4169E1", "saddlebrown": "#8B4513", "salmon": "#FA8072", "sandybrown": "#F4A460", "seagreen": "#2E8B57",
    "seashell": "#FFF5EE", "sienna": "#A0522D", "skyblue": "#87CEEB", "slateblue": "#6A5ACD", "slategray": "#708090",
    "slategrey": "#708090", "snow": "#FFFAFA", "springgreen": "#00FF7F", "steelblue": "#4682B4", "tan": "#D2B48C",
    "thistle": "#D8BFD8", "tomato": "#FF6347", "turquoise": "#40E0D0", "violet": "#EE82EE", "wheat": "#F5DEB3",
    "whitesmoke": "#F5F5F5", "yellowgreen": "#9ACD32"}
NUM = r"-?(?:\d+\.?\d*|\.\d+)"


def read_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


class Ctx:
    """Conversion state: the notes, the custom properties, the path mapping, the collected assets and fonts."""

    def __init__(self, mock_dir=".", out_dir=".", project=None, maps=None):
        self.notes = set()
        self.vars = {}
        self.mock_dir = os.path.abspath(mock_dir)
        self.out_dir = os.path.abspath(out_dir)
        self.project = os.path.abspath(project) if project else None
        self.maps = list(maps or [])           # [(url prefix, folder)]
        self.assets = set()                    # absolute paths of the files the document uses
        self.missing = set()
        self.fonts = []                        # {"family", "file_family", "weight", "style", "path", "abs"}
        self.family_map = {}                   # mock family (lower) -> family name inside the font file
        self.class_bg = {}                     # class -> {"background-size": .., "background-repeat": .., "background-position": ..}
        self.strip_classes = set(STRIP_CLASSES)
        self.ref_w, self.ref_h = 1920, 1080   # the screen the mock was measured on (vw/vh font size snapping)

    def note(self, text):
        self.notes.add(text)


# --- small CSS helpers --------------------------------------------------------------------------------------------------------
def split_top(text, sep=","):
    """Split on sep outside parentheses and quotes."""
    out, depth, cur, quote = [], 0, [], None
    for ch in text:
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == sep and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return out


def split_ws(text):
    """Split on white space outside parentheses."""
    return [p for p in split_top(re.sub(r"\s+", " ", text.strip()), " ") if p]


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def parse_blocks(css):
    """Top level CSS -> [(prelude, body)] with nested braces kept in body (at-rules)."""
    out, i, n = [], 0, len(css)
    while i < n:
        j = css.find("{", i)
        semi = css.find(";", i)
        if j < 0:
            break
        if 0 <= semi < j and css[i:semi].strip().startswith("@"):   # @import x; @charset x;
            out.append((css[i:semi].strip(), None))
            i = semi + 1
            continue
        depth, k = 1, j + 1
        while k < n and depth:
            if css[k] == "{":
                depth += 1
            elif css[k] == "}":
                depth -= 1
            k += 1
        out.append((css[i:j].strip(), css[j + 1:k - 1]))
        i = k
    return out


def parse_decls(body):
    out = []
    for decl in split_top(body, ";"):
        if ":" not in decl:
            continue
        prop, val = decl.split(":", 1)
        prop, val = prop.strip(), val.strip()
        if prop and val:
            out.append((prop, val))
    return out


# --- var() ----------------------------------------------------------------------------------------------------------------------
VAR_RE = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*((?:[^()]|\([^()]*\))*))?\)")


def resolve_vars(val, variables, ctx=None, depth=0):
    """Resolve var(--x, fallback) recursively. Returns None when a variable has no value and no fallback."""
    missing = []

    def sub(m):
        name, fb = m.group(1), m.group(2)
        if name in variables:
            return variables[name]
        if fb is not None:
            return fb.strip()
        missing.append(name)
        return ""
    for _ in range(12):
        if "var(" not in val:
            break
        val = VAR_RE.sub(sub, val)
    if missing:
        if ctx:
            ctx.note("undefined custom property %s (declaration dropped)" % ", ".join(sorted(set(missing))))
        return None
    if "var(" in val:
        if ctx:
            ctx.note("var() left unresolved (cycle?)")
        return None
    return val.strip()


def collect_vars(blocks, ctx):
    """Custom properties of :root / html / body (later ones win); scoped ones elsewhere are reported."""
    for prelude, body in blocks:
        if body is None or prelude.startswith("@"):
            continue
        sels = [s.strip() for s in prelude.split(",")]
        decls = [(p, v) for p, v in parse_decls(body) if p.startswith("--")]
        if not decls:
            continue
        if all(s in (":root", "html", "body", "*") for s in sels):
            for p, v in decls:
                ctx.vars[p] = v
        else:
            ctx.note("custom properties set on %s ignored (only :root / html / body ones are resolved)" % prelude[:40])


# --- values ---------------------------------------------------------------------------------------------------------------------
def _hex2(x):
    return "%02X" % max(0, min(255, int(round(x))))


def _alpha(a):
    a = a.strip()
    if a.endswith("%"):
        return float(a[:-1]) / 100.0
    return float(a)


def color_fn_to_hex(fn, args):
    parts = [p for p in re.split(r"[\s,/]+", args.strip()) if p]
    try:
        if fn.startswith("rgb"):
            rgb = [float(p[:-1]) * 2.55 if p.endswith("%") else float(p) for p in parts[:3]]
            a = _alpha(parts[3]) if len(parts) > 3 else 1.0
        else:
            h = float(re.sub(r"deg$", "", parts[0])) % 360 / 360.0
            s = float(parts[1].rstrip("%")) / 100.0
            l = float(parts[2].rstrip("%")) / 100.0
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            rgb = [r * 255, g * 255, b * 255]
            a = _alpha(parts[3]) if len(parts) > 3 else 1.0
    except (ValueError, IndexError):
        return None
    out = "#" + "".join(_hex2(c) for c in rgb)
    if a < 0.999:
        out += _hex2(a * 255)
    return out


def norm_colors(val):
    """rgb()/rgba()/hsl()/hsla() -> hex (RmlUi reads an rgba alpha as 0-255), named CSS colors RmlUi lacks -> hex."""
    def fn(m):
        h = color_fn_to_hex(m.group(1).lower(), m.group(2))
        return h or m.group(0)
    val = re.sub(r"\b(rgba?|hsla?)\(([^()]*)\)", fn, val, flags=re.I)

    def named(m):
        w = m.group(0)
        return NAMED_COLORS.get(w.lower(), w)
    return re.sub(r"(?<![\w#.-])[a-zA-Z]+(?![\w(-])", named, val)


def mask_urls(val):
    """Hide url(...) and quoted strings from the unit rewriting; returns (masked, restore)."""
    saved = []

    def keep(m):
        saved.append(m.group(0))
        return "\x00%d\x00" % (len(saved) - 1)
    masked = re.sub(r"url\((?:[^()\"']|\"[^\"]*\"|'[^']*')*\)|\"[^\"]*\"|'[^']*'", keep, val)

    def restore(s):
        return re.sub(r"\x00(\d+)\x00", lambda m: saved[int(m.group(1))], s)
    return masked, restore


def _fmt(x):
    s = ("%.4f" % x).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def eval_calc(expr, ctx):
    """calc() with one unit (or plain numbers): computed; mixed units: None."""
    terms = re.findall(r"(%s)(px|dp|vw|vh|%%|em|rem|deg|s|ms)?" % NUM, expr)
    units = {u for _, u in terms if u}
    if len(units) > 1:
        return None
    unit = units.pop() if units else ""
    py = re.sub(r"(%s)(px|dp|vw|vh|%%|em|rem|deg|s|ms)?" % NUM, lambda m: m.group(1), expr)
    if not re.fullmatch(r"[\d.\s+\-*/()]+", py):
        return None
    try:
        return _fmt(eval(py, {"__builtins__": {}}, {})) + unit   # only digits and operators reach here
    except Exception:
        return None


def convert_units(val, ctx):
    masked, restore = mask_urls(val)
    for _ in range(4):
        m = re.search(r"calc\(((?:[^()]|\([^()]*\))*)\)", masked)
        if not m:
            break
        res = eval_calc(m.group(1), ctx)
        if res is None:
            ctx.note("calc() mixing units is not supported (declaration dropped)")
            return None
        masked = masked[:m.start()] + res + masked[m.end():]
    if re.search(r"\b(min|max|clamp)\(", masked):
        ctx.note("min()/max()/clamp() not supported (declaration dropped)")
        return None
    masked = re.sub(r"(%s)px\b" % NUM, r"\1dp", masked)
    masked = re.sub(r"(%s)rem\b" % NUM, lambda m: _fmt(float(m.group(1)) * 16) + "dp", masked)
    masked = re.sub(r"(%s)pt\b" % NUM, lambda m: _fmt(float(m.group(1)) * 4 / 3) + "dp", masked)
    masked = re.sub(r"(%s)(cm|mm|in)\b" % NUM,
                    lambda m: _fmt(float(m.group(1)) * {"cm": 96 / 2.54, "mm": 96 / 25.4, "in": 96}[m.group(2)]) + "dp", masked)
    if re.search(r"%s(vmin|vmax)\b" % NUM, masked):
        ctx.note("vmin/vmax -> vh/vw (landscape screen assumed)")
        masked = re.sub(r"(%s)vmin\b" % NUM, r"\1vh", masked)
        masked = re.sub(r"(%s)vmax\b" % NUM, r"\1vw", masked)
    masked = re.sub(r"(%s)turn\b" % NUM, lambda m: _fmt(float(m.group(1)) * 360) + "deg", masked)
    return restore(masked)


def seconds(tok):
    m = re.fullmatch(r"(%s)(m?s)" % NUM, tok)
    if not m:
        return None
    v = float(m.group(1)) / (1000.0 if m.group(2) == "ms" else 1.0)
    return _fmt(v) + "s"


def convert_tween(tok, ctx):
    t = tok.lower()
    if t in TWEENS:
        return TWEENS[t]
    if RML_TWEEN_RE.match(t):
        return t
    if t.startswith("cubic-bezier("):
        ctx.note("cubic-bezier() easing -> cubic-in-out")
        return "cubic-in-out"
    if t.startswith("steps("):
        ctx.note("steps() easing -> linear-in-out")
        return "linear-in-out"
    return None


def convert_transition(val, ctx):
    if val.strip() == "none":
        return "none"
    items, has_all = [], False
    for item in split_top(val):
        out, timed = [], False
        for tok in split_ws(item):
            tw = convert_tween(tok, ctx)
            s = seconds(tok)
            if tw:
                out.append(tw)
            elif s:
                out.append(s)
                timed = True
            elif tok == "all":
                has_all = True
                out.append("all")
            elif tok in RML_PROPS:
                out.append(tok)
            elif tok == "background-image":
                out.append("decorator")
            else:
                ctx.note("transition on %s dropped (RmlUi does not know it)" % tok)
                out = []
                break
        if out and timed:
            items.append(" ".join(out))
    if not items:
        return None
    if has_all:
        return [i for i in items if "all" in i.split()][0]
    return ", ".join(items)


def convert_animation(val, ctx):
    if val.strip() == "none":
        return "none"
    items = []
    for item in split_top(val):
        out = []
        for tok in split_ws(item):
            tw = convert_tween(tok, ctx)
            s = seconds(tok)
            if tw:
                out.append(tw)
            elif s:
                out.append(s)
            elif tok in ("infinite", "alternate", "paused"):
                out.append(tok)
            elif re.fullmatch(NUM, tok):
                out.append(tok)
            elif tok in ("forwards", "backwards", "both", "normal", "running", "reverse", "alternate-reverse"):
                ctx.note("animation keyword %s dropped" % tok)
            else:
                out.append(tok)   # the keyframes name
        items.append(" ".join(out))
    return ", ".join(items)


# --- paths ----------------------------------------------------------------------------------------------------------------------
def true_case(path):
    """The path with the case each component has on disk (Windows is case-insensitive, paks are not)."""
    path = os.path.abspath(path)
    drive, rest = os.path.splitdrive(path)
    parts = [p for p in re.split(r"[\\/]", rest) if p]
    cur = drive + os.sep if drive else os.sep
    for p in parts:
        try:
            names = os.listdir(cur)
        except OSError:
            return path
        hit = [n for n in names if n == p] or [n for n in names if n.lower() == p.lower()]
        if not hit:
            return path
        cur = os.path.join(cur, hit[0])
    return cur


def resolve_path(url, ctx):
    """A mock url -> an absolute file path (None for data:, http: and the like)."""
    url = html.unescape(url.strip().strip("\"'"))
    url = url.split("?")[0].split("#")[0]
    if re.match(r"^(data|https?|blob):", url, re.I):
        return None
    for prefix, folder in ctx.maps:
        if url.startswith(prefix):
            return os.path.normpath(os.path.join(folder, url[len(prefix):]))
    if url.startswith("/") and ctx.project:
        return os.path.normpath(os.path.join(ctx.project, url.lstrip("/")))
    return os.path.normpath(os.path.join(ctx.mock_dir, url))


def map_url(url, ctx, relative_to=None):
    """A mock url -> the path the document uses (relative to the .rml/.rcss), recording the asset."""
    p = resolve_path(url, ctx)
    if p is None:
        ctx.note("external or data: url kept as is (RmlUi cannot load it): %s" % url[:60])
        return url
    p = true_case(p)
    if os.path.exists(p):
        ctx.assets.add(p)
    else:
        ctx.missing.add(p)
    base = relative_to or ctx.out_dir
    try:
        return os.path.relpath(p, base).replace("\\", "/")
    except ValueError:   # another drive
        return p.replace("\\", "/")


def project_relative(p, ctx):
    if ctx.project:
        try:
            rel = os.path.relpath(p, ctx.project).replace("\\", "/")
            if not rel.startswith(".."):
                return rel
        except ValueError:
            pass
    return p.replace("\\", "/")


# --- fonts ----------------------------------------------------------------------------------------------------------------------
def font_family_of(path):
    """The family the engine sees: name ID 16 (typographic family), else 1, Microsoft English then Mac Roman (gameui_fonts.cpp)."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return None
    try:
        num = struct.unpack(">H", data[4:6])[0]
        name_off = None
        for i in range(num):
            tag, _, off, _ = struct.unpack(">4sIII", data[12 + 16 * i:28 + 16 * i])
            if tag == b"name":
                name_off = off
        if name_off is None:
            return None
        _, count, str_off = struct.unpack(">HHH", data[name_off:name_off + 6])
        recs = {}
        for i in range(count):
            pid, eid, lid, nid, length, off = struct.unpack(">HHHHHH", data[name_off + 6 + 12 * i:name_off + 18 + 12 * i])
            raw = data[name_off + str_off + off:name_off + str_off + off + length]
            if pid == 3 and eid == 1 and lid == 0x409:
                recs.setdefault((nid, 0), raw.decode("utf-16-be", "replace"))
            elif pid == 1 and eid == 0 and lid == 0:
                recs.setdefault((nid, 1), raw.decode("mac_roman", "replace"))
        for nid in (16, 1):
            for plat in (0, 1):
                if recs.get((nid, plat)):
                    return recs[(nid, plat)]
    except (struct.error, IndexError):
        return None
    return None


def first_family(val):
    fams = [f.strip().strip("\"'") for f in split_top(val)]
    return fams[0] if fams else ""


def add_font_face(body, ctx):
    d = dict((p.lower(), v) for p, v in parse_decls(body))
    fam = first_family(resolve_vars(d.get("font-family", ""), ctx.vars, ctx) or "")
    src = d.get("src", "")
    m = re.search(r"url\(\s*([\"']?)(.*?)\1\s*\)", src)
    if not fam or not m:
        ctx.note("@font-face without family or url skipped")
        return
    p = resolve_path(m.group(2), ctx)
    if p is None:
        ctx.note("@font-face %s: url not local, load the font yourself" % fam)
        return
    p = true_case(p)
    file_family = None
    if os.path.exists(p):
        ctx.assets.add(p)
        file_family = font_family_of(p)
    else:
        ctx.missing.add(p)
    if file_family and file_family.lower() != fam.lower():
        ctx.family_map[fam.lower()] = file_family
        ctx.note("font-family %r renamed to %r (the family inside %s)" % (fam, file_family, os.path.basename(p)))
    if not any(f["abs"] == p for f in ctx.fonts):
        ctx.fonts.append({"family": fam, "file_family": file_family or fam, "weight": d.get("font-weight", "normal"),
                          "style": d.get("font-style", "normal"), "path": project_relative(p, ctx), "abs": p})


# --- declarations ---------------------------------------------------------------------------------------------------------------
def border_value(val, ctx):
    """'2px solid #fff' -> '2dp #fff'; 'none' -> '0dp'."""
    toks = split_ws(val)
    if any(t.lower() in ("none", "hidden") for t in toks) and len(toks) == 1:
        return "0dp"
    if any(t.lower() in BORDER_STYLES - {"solid", "none", "hidden"} for t in toks):
        ctx.note("border styles other than solid are drawn solid")
    out = [t for t in toks if t.lower() not in BORDER_STYLES]
    widths = {"thin": "1dp", "medium": "3dp", "thick": "5dp"}
    out = [widths.get(t.lower(), t) for t in out]
    if not out:
        return "0dp"
    if len(out) == 1 and re.match(NUM, out[0]):
        ctx.note("border without a color: the color is black (CSS uses the text color)")
    return " ".join(out)


def gradient_decorator(fn, args, ctx):
    """linear-gradient(...) -> 'vertical-gradient(a b)' / 'horizontal-gradient(a b)' (the engine draws only these)."""
    if fn.startswith("repeating"):
        ctx.note("repeating gradient drawn once")
    if "radial" in fn or "conic" in fn:
        ctx.note("%s() not supported by the engine (no shaders): dropped" % fn)
        return None
    parts = [p.strip() for p in split_top(args)]
    axis, reverse = "vertical", False
    first = parts[0].lower()
    angle = None
    if first.startswith("to "):
        sides = first[3:].split()
        side = sides[0]
        if len(sides) > 1:   # 'to bottom right': the vertical side wins
            ctx.note("diagonal gradient (%s) drawn along one axis" % first)
            side = next((s for s in sides if s in ("top", "bottom")), sides[0])
        angle = {"top": 0, "right": 90, "bottom": 180, "left": 270}.get(side, 180)
        parts = parts[1:]
    else:
        m = re.fullmatch(r"(%s)(deg|turn|rad|grad)" % NUM, first)
        if m:
            v = float(m.group(1))
            angle = {"deg": v, "turn": v * 360, "rad": v * 57.29578, "grad": v * 0.9}[m.group(2)] % 360
            snapped = min((0, 90, 180, 270, 360), key=lambda a: abs(a - angle)) % 360
            if abs(((angle - snapped + 180) % 360) - 180) > 1:
                ctx.note("gradient angle %sdeg snapped to %ddeg" % (_fmt(angle), snapped))
            angle = snapped
            parts = parts[1:]
    if angle is None:
        angle = 180
    axis = "vertical" if angle in (0, 180) else "horizontal"
    reverse = angle in (0, 270)
    stops = []
    for p in parts:
        toks = split_ws(p)
        col = [t for t in toks if not re.fullmatch(r"%s(%%|dp|px|vw|vh|em)?" % NUM, t)]
        pos = [t for t in toks if re.fullmatch(r"%s(%%|dp|px|vw|vh|em)?" % NUM, t)]
        if col:
            stops.append((col[0], pos))
    if len(stops) < 2:
        ctx.note("gradient with fewer than two colors dropped")
        return None
    edge = stops[0][1] in ([], ["0%"], ["0"], ["0dp"]) and stops[-1][1] in ([], ["100%"])
    if len(stops) > 2 or not edge:
        ctx.note("multi-stop gradient approximated by its first and last color (%s)" % args[:50])
    a, b = stops[0][0], stops[-1][0]
    if reverse:
        a, b = b, a
    return "%s-gradient(%s %s)" % (axis, a, b)


def image_fit(size, repeat, position):
    size = (size or "auto").strip().lower()
    repeat = (repeat or "repeat").strip().lower()
    if size in ("100% 100%",):
        fit = "fill"
    elif size == "cover":
        fit = "cover"
    elif size == "contain":
        fit = "contain"
    elif size.startswith("auto"):
        if repeat in ("no-repeat",):
            fit = "scale-none"
        elif repeat == "repeat-x":
            fit = "repeat-x"
        elif repeat == "repeat-y":
            fit = "repeat-y"
        else:
            fit = "repeat"
    else:
        fit = "fill"
    align = ""
    if position and fit not in ("fill",):
        toks = split_ws(position.lower())
        xs = {"left": "left", "center": "center", "right": "right"}
        ys = {"top": "top", "center": "center", "bottom": "bottom"}
        x = next((xs[t] for t in toks if t in xs and t != "center"), None)
        y = next((ys[t] for t in toks if t in ys and t != "center"), None)
        nums = [t for t in toks if re.fullmatch(r"%s(%%|dp)" % NUM, t)]
        if nums:
            x = x or nums[0]
            y = y or (nums[1] if len(nums) > 1 else None)
        x, y = x or "center", y or "center"
        if len(toks) == 1 and toks[0] in ys and toks[0] != "center":
            x, y = "center", toks[0]
        align = " %s %s" % (x, y)
    elif fit in ("scale-none", "repeat", "repeat-x", "repeat-y"):
        align = " left top"   # CSS default background-position
    return fit + align


def background_layers(val, ctx, bg):
    """A background(-image) value -> (decorators, color)."""
    decorators, color = [], None
    for layer in split_top(val):
        layer = layer.strip()
        if not layer or layer == "none":
            continue
        m = re.search(r"((?:repeating-)?(?:linear|radial|conic)-gradient)\(((?:[^()]|\([^()]*\))*)\)", layer)
        if m:
            d = gradient_decorator(m.group(1), m.group(2), ctx)
            if d:
                decorators.append(d)
            continue
        m = re.search(r"url\(\s*([\"']?)(.*?)\1\s*\)", layer)
        if m:
            rest = layer.replace(m.group(0), " ")
            size = bg.get("background-size")
            if "/" in rest:   # shorthand: position / size
                pos_part, size_part = rest.split("/", 1)
                st = [t for t in split_ws(size_part) if re.match(r"%s|auto|cover|contain" % NUM, t)][:2]
                size = " ".join(st) or size
                rest = pos_part
            repeat = next((t for t in split_ws(rest) if t.startswith(("repeat", "no-repeat", "space", "round"))),
                          bg.get("background-repeat"))
            pos = " ".join(t for t in split_ws(rest) if t in ("left", "right", "top", "bottom", "center")
                           or re.fullmatch(r"%s(%%|dp)" % NUM, t)) or bg.get("background-position")
            decorators.append("image(%s %s)" % (map_url(m.group(2), ctx), image_fit(size, repeat, pos)))
            continue
        toks = split_ws(layer)
        cols = [t for t in toks if t.startswith("#") or t.lower() in ("transparent",) or t.lower() in NAMED_COLORS
                or t.lower() in ("black", "white", "red", "green", "blue", "gray", "grey", "silver", "maroon", "orange",
                                 "purple", "fuchsia", "lime", "olive", "yellow", "navy", "teal", "aqua")]
        if cols:
            color = cols[-1]
    return decorators, color


def snap_font_size(val, ctx):
    """RmlUi asks the font engine for (int)font-size: 0.8333vw is 15.999 px at 1920 and draws at 15. A vw/vh size that is meant
    to be a whole pixel count at the reference screen is nudged just above it, so the text keeps the mock's size."""
    m = re.fullmatch(r"(%s)(vw|vh)" % NUM, val.strip())
    if not m:
        return val
    ref = ctx.ref_w if m.group(2) == "vw" else ctx.ref_h
    px = float(m.group(1)) * ref / 100.0
    target = round(px)
    if target <= 0 or abs(px - target) > 0.05:
        return val   # a size between two pixels on purpose: left as it is
    v = (target + 0.01) * 100.0 / ref
    if abs(v - float(m.group(1))) > 1e-9:
        ctx.note("vw/vh font sizes nudged to whole pixels at %dx%d (RmlUi truncates the font size)" % (ctx.ref_w, ctx.ref_h))
    return "%s%s" % (("%.5f" % v).rstrip("0").rstrip("."), m.group(2))


def snap_letter_spacing(val, ctx):
    """RmlUi adds (int)letter_spacing pixels per glyph (FontFaceHandleDefault.cpp): 0.05208vw (0.9999 px) would draw no spacing
    at all. The spacing is rounded to the nearest whole pixel at the reference screen and written
    so that the truncation lands on it. A half (within 0.05 px) goes down: the text is then never wider than in the mock, so it
    cannot overflow a box sized for it."""
    m = re.fullmatch(r"(%s)(vw|vh|dp)" % NUM, val.strip())
    if not m:
        return val
    num, unit = float(m.group(1)), m.group(2)
    ref = {"vw": ctx.ref_w, "vh": ctx.ref_h, "dp": 100.0}[unit]
    px = num * ref / 100.0
    if px <= 0:
        return val   # negative spacing: left as it is
    target = int(px + 0.45 - 1e-9)   # nearest pixel, halves down
    if target == int(px):
        return val   # the truncation already gives the nearest pixel
    ctx.note("letter-spacing rounded to whole pixels at %dx%d (RmlUi truncates it)" % (ctx.ref_w, ctx.ref_h))
    if unit == "dp":
        return "%ddp" % target
    v = (target + 0.01) * 100.0 / ref
    return "%s%s" % (("%.5f" % v).rstrip("0").rstrip("."), unit)


def convert_decl(prop, val, ctx, bg=None, out=None):
    """One CSS declaration -> a list of (property, value) for RCSS (possibly empty)."""
    out = [] if out is None else out
    prop = prop.strip().lower()
    if prop.startswith("--"):
        return out
    if "!important" in val:
        ctx.note("!important removed (RmlUi has no !important)")
        val = val.replace("!important", "").strip()
    val = resolve_vars(val, ctx.vars, ctx)
    if val is None:
        return out
    val = convert_units(val, ctx)
    if val is None:
        return out
    if prop not in ("font-family", "font", "animation", "transition"):
        masked, restore = mask_urls(val)
        val = restore(norm_colors(masked))
    bg = bg or {}

    if prop in NOT_DRAWN:
        ctx.note("dropped " + NOT_DRAWN[prop])
        return out
    if prop in ("transition",):
        v = convert_transition(val, ctx)
        if v:
            out.append(("transition", v))
        return out
    if prop in ("animation",):
        out.append(("animation", convert_animation(val, ctx)))
        return out
    if prop.startswith(("transition-", "animation-")):
        ctx.note("dropped %s (RmlUi only has the transition / animation shorthands)" % prop)
        return out
    if prop in ("border", "border-top", "border-right", "border-bottom", "border-left"):
        out.append((prop, border_value(val, ctx)))
        return out
    if prop in ("border-style", "border-top-style", "border-right-style", "border-bottom-style", "border-left-style"):
        if val.strip() in ("none", "hidden"):
            out.append((prop.replace("style", "width"), "0dp"))
        return out
    if prop in ("border-width", "border-top-width", "border-right-width", "border-bottom-width", "border-left-width"):
        widths = {"thin": "1dp", "medium": "3dp", "thick": "5dp"}
        out.append((prop, " ".join(widths.get(t, t) for t in split_ws(val))))
        return out
    if prop == "background-image":
        decs, _ = background_layers(val, ctx, bg)
        out.append(("decorator", ", ".join(decs) if decs else "none"))
        return out
    if prop == "background":
        decs, color = background_layers(val, ctx, bg)
        out.append(("background-color", color or "transparent"))
        out.append(("decorator", ", ".join(decs) if decs else "none"))
        return out
    if prop in ("background-size", "background-repeat", "background-position"):
        return out   # read together with the image (bg)
    if prop.startswith("background-") and prop != "background-color":
        ctx.note("dropped " + prop)
        return out
    if prop == "display":
        v = val.strip()
        if "grid" in v:
            ctx.note("display:grid -> flex wrap (check the layout)")
            out += [("display", "flex"), ("flex-wrap", "wrap")]
        elif v in ("list-item", "contents", "run-in"):
            ctx.note("display:%s -> block" % v)
            out.append(("display", "block"))
        else:
            out.append(("display", v))
        return out
    if prop.startswith("grid") or prop in ("place-items", "place-self", "justify-items", "justify-self"):
        ctx.note("dropped " + prop)
        return out
    if prop == "place-content":
        t = split_ws(val)
        out += [("align-content", t[0]), ("justify-content", t[-1])]
        return out
    if prop in ("align-items", "align-self", "align-content", "justify-content"):
        out.append((prop, {"start": "flex-start", "end": "flex-end", "self-start": "flex-start",
                           "self-end": "flex-end", "normal": "stretch" if prop != "justify-content" else "flex-start"}.get(val, val)))
        return out
    if prop == "inset":
        t = split_ws(val)
        t = (t * 4)[:4] if len(t) == 1 else (t + t)[:4] if len(t) == 2 else (t + [t[1]])[:4] if len(t) == 3 else t
        out += [("top", t[0]), ("right", t[1]), ("bottom", t[2]), ("left", t[3])]
        return out
    if prop == "position" and val == "sticky":
        ctx.note("position:sticky -> relative")
        out.append(("position", "relative"))
        return out
    if prop in ("overflow", "overflow-x", "overflow-y"):
        v = " ".join({"clip": "hidden", "overlay": "auto"}.get(t, t) for t in split_ws(val))
        out.append((prop, v))
        if any(t in ("hidden", "auto", "scroll") for t in split_ws(v)) and ("clip", "always") not in out:
            # RmlUi clips only when the in-flow content overflows; absolutely positioned children (a map in a frame)
            # are drawn outside without this
            out.append(("clip", "always"))
        return out
    if prop == "text-align":
        out.append((prop, {"start": "left", "end": "right"}.get(val, val)))
        return out
    if prop == "text-decoration" or prop == "text-decoration-line":
        kw = [t for t in split_ws(val) if t in ("none", "underline", "overline", "line-through")]
        if kw:
            out.append(("text-decoration", kw[0]))
        return out
    if prop == "font-family":
        fam = first_family(val)
        if fam.lower() in ("serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "inherit", "initial"):
            ctx.note("generic font family %r: RmlUi needs a loaded font name" % fam)
        fam = ctx.family_map.get(fam.lower(), fam)
        out.append(("font-family", fam))   # unquoted: RmlUi keeps the spaces of a string property, single quotes would stay
        return out
    if prop == "font":
        toks = split_ws(val)
        fam_start = next((i for i, t in enumerate(toks) if re.fullmatch(r"%s(dp|em|%%|vw|vh)(/.*)?" % NUM, t)), None)
        if fam_start is None:
            ctx.note("font shorthand without a size dropped")
            return out
        for t in toks[:fam_start]:
            if t in ("italic", "oblique"):
                out.append(("font-style", "italic"))
            elif t in ("bold", "bolder", "lighter", "normal") or re.fullmatch(r"\d00", t):
                out.append(("font-weight", t if t != "bolder" else "bold"))
        size = toks[fam_start]
        if "/" in size:
            size, lh = size.split("/", 1)
            out.append(("line-height", lh))
        out.append(("font-size", size))
        convert_decl("font-family", " ".join(toks[fam_start + 1:]), ctx, bg, out)
        return out
    if prop == "font-weight":
        out.append((prop, {"bolder": "bold", "lighter": "normal"}.get(val, val)))
        return out
    if prop == "font-size":
        out.append((prop, snap_font_size(val, ctx)))
        return out
    if prop == "letter-spacing":
        out.append((prop, snap_letter_spacing(val, ctx)))
        return out
    if prop == "opacity" and val.endswith("%"):
        out.append((prop, _fmt(float(val[:-1]) / 100)))
        return out
    if prop in ("width", "height", "min-width", "max-width", "min-height", "max-height", "flex-basis") and \
            val in ("fit-content", "max-content", "min-content"):
        ctx.note("%s:%s -> auto" % (prop, val))
        out.append((prop, "auto" if not prop.startswith("max") else "none"))
        return out
    if prop in ("text-shadow", "-webkit-text-stroke"):
        eff = None
        if prop == "text-shadow" and val != "none":
            layers = split_top(val)
            if len(layers) > 1:
                ctx.note("only the first text-shadow is kept")
            toks = split_ws(layers[0])
            lens = [t for t in toks if re.fullmatch(r"%s(dp|em|vw|vh)?" % NUM, t)]
            col = [t for t in toks if t not in lens]
            c = col[0] if col else "#000000"
            x, y = (lens + ["0dp", "0dp"])[:2]
            blur = lens[2] if len(lens) > 2 else "0dp"
            if re.fullmatch(r"0(\.0*)?(dp|em|vw|vh)?", blur):
                eff = "shadow(%s %s %s)" % (x, y, c)
            else:
                eff = "glow(0dp %s %s %s %s)" % (blur, x, y, c)
        elif prop == "-webkit-text-stroke":
            toks = split_ws(val)
            eff = "outline(%s %s)" % (toks[0], toks[1] if len(toks) > 1 else "#000000")
        if eff:
            prev = [i for i, (p, _) in enumerate(out) if p == "font-effect"]
            if prev:
                out[prev[0]] = ("font-effect", out[prev[0]][1] + ", " + eff)
            else:
                out.append(("font-effect", eff))
        return out
    if prop in ("word-wrap", "overflow-wrap") and val == "break-word":
        out.append(("word-break", "break-word"))
        return out
    if prop not in RML_PROPS:
        ctx.note("dropped %s (not an RmlUi property)" % prop)
        return out
    out.append((prop, val))
    return out


def convert_block(body, ctx, bg=None):
    """A declaration block -> RCSS text, the background-size/-repeat/-position of the block feeding its images."""
    decls = parse_decls(body)
    local_bg = dict(bg or {})
    for p, v in decls:
        if p.lower() in ("background-size", "background-repeat", "background-position"):
            r = resolve_vars(v, ctx.vars)
            if r is not None:
                local_bg[p.lower()] = convert_units(r, ctx) or r
    out = []
    for p, v in decls:
        convert_decl(p, v, ctx, local_bg, out)
    return out


# --- selectors ------------------------------------------------------------------------------------------------------------------
def convert_selector(sel, ctx):
    """One selector of a list -> RCSS selector, or None when it targets something RmlUi or the game does not have."""
    s = sel.strip()
    if not s:
        return None
    s = re.sub(r"^:root\b", "body", s)   # the document root of RML is body
    if re.search(r"\[data-vs[\w-]*", s):
        return None   # Variant Studio states
    for cls in ctx.strip_classes:
        if re.search(r"\.%s(?![\w-])" % re.escape(cls), s):
            return None
    if "::" in s or re.search(r":(before|after|placeholder|selection|marker|first-line|first-letter)\b", s):
        ctx.note("dropped rules on pseudo-elements (::before/::after...)")
        return None
    m = re.search(r":(is|where|has|focus-within|visited|link|target|any-link|root|placeholder-shown|"
                  r"read-only|read-write|invalid|valid|required|optional|indeterminate|default|defined)\b", s)
    if m:
        ctx.note("dropped rules with :%s" % m.group(1))
        return None
    s = re.sub(r"(?<![\w.#-])html(?![\w-])", "body", s)
    for tag, new in RENAME.items():
        s = re.sub(r"(?<![\w.#\[=\"'-])%s(?![\w-])" % tag, new, s)
    return s


def selector_specificity(sel):
    ids = len(re.findall(r"#[\w-]+", sel))
    cls = len(re.findall(r"\.[\w-]+|\[[^\]]*\]|:(?!not)[\w-]+", sel))
    tags = len(re.findall(r"(?:^|[\s>+~])[a-zA-Z][\w-]*", sel))
    return (ids, cls, tags)


# --- the CSS of the mock --------------------------------------------------------------------------------------------------------
def convert_css(css, ctx):
    """Mock CSS -> (RCSS text, rules for the element matching [(selector, [(prop, val)], order)])."""
    css = strip_comments(css)
    blocks = parse_blocks(css)
    collect_vars(blocks, ctx)
    # @font-face first: the family renames apply to every rule
    for prelude, body in blocks:
        if prelude.lower().startswith("@font-face") and body is not None:
            add_font_face(body, ctx)
    # class-level background-size/-repeat/-position, used by inline background images
    for prelude, body in blocks:
        if body is None or prelude.startswith("@"):
            continue
        for sel in prelude.split(","):
            m = re.fullmatch(r"\s*\.([\w-]+)\s*", sel)
            if m:
                for p, v in parse_decls(body):
                    if p.lower() in ("background-size", "background-repeat", "background-position"):
                        ctx.class_bg.setdefault(m.group(1), {})[p.lower()] = v
    lines, rules, order = [], [], 0
    for prelude, body in blocks:
        low = prelude.lower()
        if low.startswith("@"):
            kind = re.match(r"@([\w-]+)", low).group(1)
            if kind == "font-face":
                continue
            if kind == "keyframes" and body is not None:
                name = prelude.split(None, 1)[1].strip() if len(prelude.split(None, 1)) > 1 else "anim"
                frames = []
                for fsel, fbody in parse_blocks(body):
                    decls = convert_block(fbody or "", ctx)
                    if decls:
                        frames.append("  %s { %s; }" % (fsel, "; ".join("%s: %s" % d for d in decls)))
                lines.append("@keyframes %s {\n%s\n}" % (name, "\n".join(frames)))
                continue
            if kind == "import":
                ctx.note("@import dropped (inline the file in the mock <style>)")
                continue
            ctx.note("dropped @" + kind)
            continue
        if body is None:
            continue
        items = [convert_selector(s, ctx) for s in split_top(prelude)]
        items = [s for s in items if s]
        if not items:
            continue
        decls = convert_block(body, ctx)
        if not decls:
            continue
        sel = ", ".join(items)
        lines.append("%s { %s; }" % (sel, "; ".join("%s: %s" % d for d in decls)))
        for s in items:
            rules.append((s, decls, order))
            order += 1
    return "\n".join(lines) + "\n", rules


# --- HTML tree ------------------------------------------------------------------------------------------------------------------
class Node:
    def __init__(self, tag, attrs=None, parent=None, text=None):
        self.tag, self.attrs, self.parent, self.text = tag, list(attrs or []), parent, text
        self.children = []

    def get(self, k, default=None):
        for a, v in self.attrs:
            if a == k:
                return v
        return default

    def classes(self):
        return (self.get("class") or "").split()


class Mock(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.css = []
        self.links = []
        self.title = ""
        self.body = None
        self.cur = None
        self.in_style = self.in_title = False
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag == "style":
            self.in_style = True
            return
        if tag == "title":
            self.in_title = True
            return
        if tag == "link":
            d = dict(attrs)
            if "stylesheet" in (d.get("rel") or "") and d.get("href"):
                self.links.append(d["href"])
            return
        if tag == "body":
            self.body = Node("body", attrs)
            self.cur = self.body
            return
        if self.cur is None:
            return
        if self.skip or tag in DROP_TAGS:
            if tag not in VOID:
                self.skip += 1
            return
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        if self.skip or tag in DROP_TAGS or self.cur is None and tag != "link":
            return
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.cur is not None and self.cur.tag == tag:
            self.cur = self.cur.parent

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False
            return
        if tag == "title":
            self.in_title = False
            return
        if self.cur is None or tag in VOID:
            return
        if self.skip:
            self.skip -= 1
            return
        if tag == "body":
            self.cur = None
            return
        n = self.cur
        while n is not None and n.tag != tag:   # tolerate unclosed tags
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        if self.in_style:
            self.css.append(data)
        elif self.in_title:
            self.title += data
        elif self.cur is not None and not self.skip:
            kids = self.cur.children
            if kids and kids[-1].tag is None:
                kids[-1].text += data   # one text node per run, like the DOM
            else:
                kids.append(Node(None, parent=self.cur, text=data))


def strip_vs(node, ctx):
    """Remove the Variant Studio presentation parts (concept pictures, caption strips, data-vs-only elements)."""
    keep = []
    for c in node.children:
        if c.tag is not None:
            cls = set(c.classes())
            hit = cls & ctx.strip_classes
            if hit or c.get("data-vs-only") is not None or c.get("data-vs-caption") is not None:
                ctx.note("stripped Variant Studio part <%s class=%s>" % (c.tag, ",".join(sorted(hit)) or "data-vs"))
                continue
            strip_vs(c, ctx)
        keep.append(c)
    node.children = keep


def find_state_groups(node, out):
    kids = [c for c in node.children if c.tag and set(c.classes()) & set(STATE_CLASSES)]
    if len(kids) >= 2:
        out.append((node, kids))
    for c in node.children:
        if c.tag:
            find_state_groups(c, out)
    return out


def select_state(body, n, ctx):
    groups = find_state_groups(body, [])
    if not groups:
        if n:
            ctx.note("--state %d: the mock has no stacked state frames" % n)
        return 1
    parent, kids = groups[0]
    if not n:
        ctx.note("%d states stacked (class frame/state): all kept, pass --state N for one screen" % len(kids))
        return len(kids)
    if n > len(kids):
        raise SystemExit("--state %d: the mock has %d states" % (n, len(kids)))
    drop = set(id(k) for i, k in enumerate(kids) if i != n - 1)
    parent.children = [c for c in parent.children if id(c) not in drop]
    return len(kids)


def match_compound(comp, node):
    """Does the last compound selector match the element (ancestors and dynamic pseudo-classes ignored)?"""
    if re.search(r":(%s)\b" % "|".join(DYNAMIC_PSEUDO), comp):
        return False
    comp = re.sub(r":[\w-]+(\([^)]*\))?", "", comp)
    m = re.match(r"^([a-zA-Z][\w-]*|\*)?", comp)
    tag = m.group(1) if m else None
    if tag and tag != "*" and tag != node.out_tag:
        return False
    for i in re.findall(r"#([\w-]+)", comp):
        if node.get("id") != i:
            return False
    cls = set(node.classes())
    for c in re.findall(r"\.([\w-]+)", comp):
        if c not in cls:
            return False
    for a in re.findall(r"\[([\w-]+)", comp):
        if node.get(a) is None:
            return False
    return True


def computed_prop(node, rules, prop):
    """The value of one property on the element (rule order and specificity; ancestors of the selectors ignored)."""
    best, best_key = None, None
    for sel, decls, order in rules:
        vals = [v for p, v in decls if p == prop]
        if not vals:
            continue
        last = re.split(r"\s*[>+~]\s*|\s+", sel.strip())[-1]
        if match_compound(last, node):
            key = (selector_specificity(sel), order)
            if best_key is None or key >= best_key:
                best, best_key = vals[-1], key
    m = re.findall(r"(?:^|;)\s*%s\s*:\s*([\w-]+)" % re.escape(prop), node.get("style") or "")
    return m[-1] if m else best


def computed_display(node, rules, ctx):
    """display, with 'out-of-flow' for absolute / fixed elements (white space next to them is never drawn)."""
    if computed_prop(node, rules, "position") in ("absolute", "fixed"):
        return "out-of-flow"
    best = computed_prop(node, rules, "display")
    if best is None:
        best = "block" if node.out_tag in BLOCK_TAGS else "inline"
    return best


WS = " \t\n\r\f"


def is_ws(s):
    return all(c in WS for c in s)


def collapse(s):
    return re.sub(r"[ \t\n\r\f]+", " ", s)


def out_tag_of(node):
    tag = RENAME.get(node.tag, node.tag)
    if node.tag == "a" and (node.get("id") or "btn" in (node.get("class") or "")):
        tag = "button"   # a link used as a button stays clickable (bind it by id in the .lua)
    return tag


def annotate(node, ctx):
    for c in node.children:
        if c.tag:
            c.out_tag = out_tag_of(c)
            if c.out_tag != c.tag:
                ctx.note("<%s> -> <%s>" % (c.tag, c.out_tag))
            annotate(c, ctx)


def convert_attrs(node, ctx):
    kept = []
    width = height = None
    for k, v in node.attrs:
        if k == "style" and v:
            bg = {}
            for c in node.classes():
                bg.update(ctx.class_bg.get(c, {}))
            bg = {p: (convert_units(resolve_vars(val, ctx.vars) or val, ctx) or val) for p, val in bg.items()}
            decls = convert_block(v, ctx, bg)
            if decls:
                kept.append('style="%s"' % html.escape("; ".join("%s: %s" % d for d in decls) + ";", quote=True))
        elif k == "src" and v:
            kept.append('src="%s"' % html.escape(map_url(v, ctx), quote=True))
        elif node.tag == "img" and k in ("width", "height") and v:
            if k == "width":
                width = v
            else:
                height = v
        elif k in KEEP_ATTRS or k.startswith("data-"):
            if k.startswith("data-vs"):
                continue
            kept.append(k if v is None else '%s="%s"' % (k, html.escape(v, quote=True)))
        elif k.startswith("on") or k == "href":
            ctx.note("dropped %s= (bind it in the .lua)" % k)
    if width or height:
        extra = "; ".join("%s: %sdp" % (p, re.sub(r"px$", "", v)) for p, v in (("width", width), ("height", height)) if v)
        styles = [i for i, a in enumerate(kept) if a.startswith('style="')]
        if styles:
            kept[styles[0]] = kept[styles[0]][:-1] + " " + html.escape(extra) + ';"'
        else:
            kept.append('style="%s;"' % extra)
    return kept


def serialize(node, rules, ctx, depth):
    """The children of an element -> RML. Element-only content is indented (RmlUi drops white-space-only text nodes, so the
    indentation is free); content with text is written in one piece, with exactly the white space the mock had."""
    disp = computed_display(node, rules, ctx) if node.out_tag != "body" else "block"
    flex = computed_prop(node, rules, "display") in ("flex", "inline-flex")
    if disp == "out-of-flow":
        disp = "block"   # an absolutely positioned element is a block container for its own children
    kids = node.children
    pieces, inline = [], False
    for i, c in enumerate(kids):
        if c.tag is not None:
            pieces.append(("el", element_rml(c, rules, ctx, depth + 1)))
            continue
        if not is_ws(c.text):
            txt = collapse(c.text)
            if flex:
                # text straight in a flex container is an anonymous flex item in CSS; RmlUi does not draw it: wrap it in an
                # element no selector of the mock can match
                ctx.note("text in a flex container wrapped in <%s> (anonymous flex item)" % ANON_TAG)
                pieces.append(("el", "<%s>%s</%s>" % (ANON_TAG, html.escape(txt.strip(" "), quote=False), ANON_TAG)))
                continue
            if not disp.startswith("inline"):   # white space at the start / end of a block line is not drawn
                if i == 0:
                    txt = txt.lstrip(" ")
                if i == len(kids) - 1:
                    txt = txt.rstrip(" ")
            pieces.append(("text", html.escape(txt, quote=False)))
            inline = True
            continue
        # white space only: significant between two inline-level siblings outside a flex container (as in a browser)
        prev = kids[i - 1] if i > 0 else None
        nxt = kids[i + 1] if i + 1 < len(kids) else None
        if not flex and prev is not None and nxt is not None and prev.tag and nxt.tag and \
                computed_display(prev, rules, ctx).startswith("inline") and computed_display(nxt, rules, ctx).startswith("inline"):
            pieces.append(("text", " "))   # a no-break space survives; a plain one would be dropped
            inline = True
    if not pieces:
        return ""
    if inline:
        return "".join(p for _, p in pieces)
    pad = "  " * (depth + 1)
    return "".join("\n" + pad + p for _, p in pieces) + "\n" + "  " * depth


def element_rml(node, rules, ctx, depth):
    attrs = convert_attrs(node, ctx)
    open_ = "<%s%s%s" % (node.out_tag, " " if attrs else "", " ".join(attrs))
    if node.tag in VOID:
        return open_ + "/>"
    return "%s>%s</%s>" % (open_, serialize(node, rules, ctx, depth), node.out_tag)


# --- main -----------------------------------------------------------------------------------------------------------------------
def find_project(start):
    d = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(d, "project.ncproject")):
            return d
        up = os.path.dirname(d)
        if up == d:
            return None
        d = up


def convert(mock_path, out_path, state=0, model=None, skin="", maps=None, project=None, strip=(), keep=(), no_plate=False,
            ref=(1920, 1080)):
    """Convert one mock. Returns the report dict (also written as <name>.conv.json)."""
    mock_path = os.path.abspath(mock_path)
    out_path = os.path.abspath(out_path)
    base = os.path.splitext(out_path)[0]
    name = os.path.basename(base)
    out_dir = os.path.dirname(out_path)
    os.makedirs(out_dir, exist_ok=True)
    project = project or find_project(os.path.dirname(mock_path))
    maps = list(maps or [])
    if project and not any(p == "/p/" for p, _ in maps):
        maps.append(("/p/", project))
    ctx = Ctx(os.path.dirname(mock_path), out_dir, project, maps)
    ctx.ref_w, ctx.ref_h = ref
    ctx.strip_classes |= set(strip)
    ctx.strip_classes -= set(keep)
    if no_plate:
        ctx.strip_classes.add("plate")

    m = Mock()
    m.feed(read_text(mock_path))
    if m.body is None:
        raise SystemExit("no <body> in " + mock_path)
    css_parts = []
    for href in m.links:
        p = resolve_path(href, ctx)
        if p and os.path.exists(true_case(p)):
            css_parts.append(read_text(true_case(p)))
            ctx.note("linked style sheet %s inlined" % os.path.basename(p))
        else:
            ctx.note("linked style sheet %s not found" % href)
    css_parts += m.css
    rcss_body, rules = convert_css("\n".join(css_parts), ctx)

    strip_vs(m.body, ctx)
    states = select_state(m.body, state, ctx)
    m.body.out_tag = "body"
    annotate(m.body, ctx)

    body_attrs = convert_attrs(m.body, ctx)
    if model:
        body_attrs.append('data-model="%s"' % model)
    inner = serialize(m.body, rules, ctx, 0)

    rcss_path = base + ".rcss"
    rcss = ("/* %s.rcss: converted by html2rml.py from %s */\n" % (name, os.path.basename(mock_path)) + UA_SHEET +
            "/* the document is the screen: without a size on body every percentage collapses to the content */\n"
            "body { width: 100%; height: 100%; }\n/* the mock */\n" + rcss_body)
    write_text(rcss_path, rcss)
    links = ('  <link type="text/rcss" href="%s"/>\n' % skin if skin else "") + \
        '  <link type="text/rcss" href="%s"/>\n' % os.path.basename(rcss_path)
    title = html.escape(collapse(m.title).strip() or name, quote=False)
    rml = "<rml>\n<head>\n  <title>%s</title>\n%s</head>\n<body%s%s>%s</body>\n</rml>\n" % (
        title, links, " " if body_attrs else "", " ".join(body_attrs), inner if inner.startswith("\n") else inner)
    write_text(out_path, rml)

    used_families = set(f.strip('"').lower() for f in re.findall(r"font-family:\s*([^;]+)", rcss + rml))
    fonts = [f for f in ctx.fonts if f["file_family"].lower() in used_families]
    for fam in sorted(used_families - set(f["file_family"].lower() for f in ctx.fonts)):
        ctx.note("font family %r is used but no @font-face names its file: load it yourself" % fam)
    fonts_lua = base + ".fonts.lua"
    lua = ["-- Fonts of %s.rml (the @font-face rules of %s; RCSS has no @font-face)." % (name, os.path.basename(mock_path)),
           "-- Load them once, before the document is shown: dofile or require this file, or copy the calls.",
           "local fonts = {"]
    lua += ['  "%s",   -- %s %s %s' % (f["path"], f["file_family"], f["weight"], f["style"]) for f in fonts]
    lua += ["}", "for _, f in ipairs(fonts) do", "  if not UI.loadFont(f) then print(\"[ui] font not loaded: \" .. f) end", "end",
            "return fonts", ""]
    write_text(fonts_lua, "\n".join(lua))

    if model:
        preview = base + ".preview.lua"
        if not os.path.exists(preview):   # the UI editor shows bound documents with this data (GAME_UI.md "Limits")
            fields = sorted(set(re.findall(r"\{\{\s*(\w+)", rml)) | set(re.findall(r'data-(?:if|visible)="(\w+)', rml)))
            body = ", ".join("%s = %s" % (f, "true" if f.startswith(("has", "is", "show")) else '"%s"' % f) for f in fields)
            write_text(preview, "return {%s = {%s}}\n" % (model, body))

    ids = re.findall(r'\sid="([^"]+)"', rml)
    buttons = re.findall(r'<button[^>]*\sid="([^"]+)"', rml)
    report = {
        "rml": out_path.replace("\\", "/"), "rcss": rcss_path.replace("\\", "/"), "fontsLua": fonts_lua.replace("\\", "/"),
        "elements": len(re.findall(r"<(?!/)(?!rml|head|title|link|body)[a-z]", rml)), "ids": len(ids), "buttons": buttons,
        "states": states, "state": state or None, "project": project.replace("\\", "/") if project else None,
        "fonts": [{"path": f["path"], "family": f["file_family"], "weight": f["weight"], "style": f["style"]} for f in fonts],
        "lua": "".join('UI.loadFont("%s")\n' % f["path"] for f in fonts) + 'local doc = UI.loadDocument("%s")\ndoc:show()\n' %
               project_relative(out_path, ctx),
        "assets": sorted(project_relative(p, ctx) for p in ctx.assets),
        "missing": sorted(p.replace("\\", "/") for p in ctx.missing),
        "notes": sorted(ctx.notes)}
    with open(base + ".conv.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mock")
    p.add_argument("out", help="the .rml to write (the .rcss, .fonts.lua and .conv.json go next to it)")
    p.add_argument("--state", type=int, default=0, help="keep only the Nth (1-based) of the stacked state frames")
    p.add_argument("--model", help="data-model name on <body> (UI data bindings, CreateUIModel)")
    p.add_argument("--skin", default="", help="a skin link to add before the document's own sheet, e.g. skin:skin.rcss")
    p.add_argument("--map", action="append", default=[], metavar="PREFIX=DIR",
                   help="url prefix -> folder (default /p/=the project folder found above the mock)")
    p.add_argument("--project", help="the project folder (default: found above the mock)")
    p.add_argument("--strip-class", action="append", default=[], help="also remove elements with this class")
    p.add_argument("--keep-class", action="append", default=[], help="do not remove elements with this class")
    p.add_argument("--no-plate", action="store_true", help="also remove the background plate pictures (class plate)")
    p.add_argument("--ref", default="1920x1080", help="the screen size the mock was measured on (font size snapping)")
    a = p.parse_args()
    maps = []
    for m in a.map:
        k, _, v = m.partition("=")
        maps.append((k, os.path.abspath(v)))
    ref = tuple(int(x) for x in a.ref.lower().split("x"))
    rep = convert(a.mock, a.out, a.state, a.model, a.skin, maps, a.project, a.strip_class, a.keep_class, a.no_plate, ref)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(rep, ensure_ascii=False))
    return 1 if rep["missing"] else 0


if __name__ == "__main__":
    sys.exit(main())
