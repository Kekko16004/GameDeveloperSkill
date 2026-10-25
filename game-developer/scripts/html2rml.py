#!/usr/bin/env python3
"""html2rml: a designer HTML mock -> a Nucleon game UI document (RmlUi .rml + .rcss), standard library only.

  python html2rml.py mock.html PROJECT/UI/menu.rml [--model menu] [--skin skin:skin.rcss]

RmlUi is HTML/CSS with differences (docs/engine/GAME_UI.md): units are dp, no CSS grid, no box-shadow/filter/backdrop,
no <script>, no <a href>. The converter keeps the structure, ids and classes (the Lua script binds buttons by id),
moves the CSS into <name>.rcss (px -> dp, rem/em -> dp at 16, vw/vh -> %), drops what RmlUi does not draw and reports
every change as JSON so the worker fixes the rest in the UI editor or by hand. Output on stdout: one JSON line.
"""
import argparse
import html
import json
import os
import re
import sys
from html.parser import HTMLParser

VOID = {"img", "input", "br", "hr", "meta", "link"}
DROP_TAGS = {"script", "noscript", "iframe", "svg", "canvas", "video", "audio", "template"}
RENAME = {"a": "div", "nav": "div", "header": "div", "footer": "div", "main": "div", "section": "div", "article": "div",
          "aside": "div", "figure": "div", "figcaption": "div", "ul": "div", "ol": "div", "li": "div", "label": "span",
          "strong": "b", "em": "i", "small": "span", "h4": "div", "h5": "div", "h6": "div"}
DROP_PROPS = ("box-shadow", "text-shadow", "filter", "backdrop-filter", "mix-blend-mode", "cursor", "user-select",
              "-webkit-", "-moz-", "will-change", "content-visibility", "scroll-behavior", "isolation")
KEEP_ATTRS = {"id", "class", "style", "src", "type", "value", "name", "checked", "disabled", "autofocus", "min", "max",
              "step", "placeholder", "for"}


def convert_units(css, notes):
    def rem(m):
        return "%gdp" % (float(m.group(1)) * 16)
    css = re.sub(r"(-?\d*\.?\d+)px\b", r"\1dp", css)
    css = re.sub(r"(-?\d*\.?\d+)r?em\b", rem, css)
    if re.search(r"\d(vw|vh)\b", css):
        notes.add("vw/vh -> %")
        css = re.sub(r"(-?\d*\.?\d+)v[wh]\b", r"\1%", css)
    return css


def convert_decls(block, notes):
    out = []
    for decl in block.split(";"):
        if ":" not in decl:
            continue
        prop, val = [x.strip() for x in decl.split(":", 1)]
        low = prop.lower()
        if any(low.startswith(d) for d in DROP_PROPS):
            notes.add("dropped " + low)
            continue
        if low == "display" and "grid" in val:
            notes.add("display:grid -> flex wrap (check the layout)")
            out.append("display: flex")
            out.append("flex-wrap: wrap")
            continue
        if low.startswith("grid"):
            notes.add("dropped " + low)
            continue
        if "gradient(" in val:
            notes.add("gradient kept as decorator: check it in the UI editor")
            m = re.search(r"linear-gradient\(([^)]*)\)", val)
            colors = re.findall(r"#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)", m.group(1)) if m else []
            if len(colors) >= 2:
                out.append("decorator: vertical-gradient(%s %s)" % (colors[0], colors[-1]))
            continue
        if low == "background" and re.fullmatch(r"\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)|[a-z]+)\s*", val):
            prop = "background-color"   # RmlUi has no background shorthand
        elif low == "background":
            notes.add("background shorthand -> background-color (images: use decorator: image(...))")
            colors = re.findall(r"#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)", val)
            if not colors:
                continue
            prop, val = "background-color", colors[0]
        if low == "font-family":
            val = val.split(",")[0].strip().strip("'\"")   # one face, loaded by the skin or the game
        out.append("%s: %s" % (prop, val))
    return "; ".join(out)


def convert_css(css, notes):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    variables = dict(re.findall(r"(--[\w-]+)\s*:\s*([^;}]+)", css))
    for _ in range(3):
        css = re.sub(r"var\((--[\w-]+)(?:,\s*([^)]+))?\)", lambda m: variables.get(m.group(1), m.group(2) or "").strip(), css)
    css = re.sub(r"@(media|supports|keyframes|font-face|import)[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}",
                 lambda m: notes.add("dropped @" + m.group(1)) or "", css)
    css = convert_units(css, notes)
    rules = []
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        sel = sel.strip()
        if not sel or sel.startswith(":root"):
            continue
        sel = re.sub(r"\bhtml\b", "body", sel)
        sel = re.sub(r"::?(before|after|placeholder|selection|-webkit-[\w-]+)", lambda m: notes.add("dropped ::" + m.group(1)) or "@@", sel)
        if "@@" in sel:
            continue
        for tag, new in RENAME.items():
            sel = re.sub(r"(?<![\w.#-])%s(?![\w-])" % tag, new, sel)
        decls = convert_decls(body, notes)
        if decls:
            rules.append("%s { %s; }" % (sel, decls))
    return "\n".join(rules) + "\n"


class Mock(HTMLParser):
    def __init__(self, notes):
        super().__init__(convert_charrefs=True)
        self.notes = notes
        self.css = []
        self.title = ""
        self.out = []
        self.in_body = False
        self.skip = 0
        self.in_style = False
        self.in_title = False
        self.depth = 0
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag == "style":
            self.in_style = True
            return
        if tag == "title":
            self.in_title = True
            return
        if tag == "body":
            self.in_body = True
            return
        if not self.in_body:
            return
        if tag in DROP_TAGS:
            self.skip += 1
            self.notes.add("dropped <%s>" % tag)
            return
        if self.skip:
            return
        new = RENAME.get(tag, tag)
        if tag == "a" and (dict(attrs).get("id") or "btn" in (dict(attrs).get("class") or "")):
            new = "button"   # a link used as a button stays clickable (bind it by id in the .lua)
        self.stack.append(new)
        if new != tag:
            self.notes.add("<%s> -> <%s>" % (tag, new))
        kept = []
        for k, v in attrs:
            if k in KEEP_ATTRS or k.startswith("data-"):
                if k == "style" and v:
                    v = convert_decls(convert_units(v, self.notes), self.notes)
                kept.append(k if v is None else '%s="%s"' % (k, html.escape(v, quote=True)))
            elif k.startswith("on") or k == "href":
                self.notes.add("dropped %s= (bind it in the .lua)" % k)
        self.out.append("  " * self.depth + "<%s%s%s>" % (new, " " if kept else "", " ".join(kept)))
        if tag not in VOID:
            self.depth += 1
        else:
            self.stack.pop()
            self.out[-1] = self.out[-1][:-1] + "/>"

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False
            return
        if tag == "title":
            self.in_title = False
            return
        if tag == "body":
            self.in_body = False
            return
        if not self.in_body or tag in VOID:
            return
        if tag in DROP_TAGS:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        self.depth = max(0, self.depth - 1)
        self.out.append("  " * self.depth + "</%s>" % (self.stack.pop() if self.stack else RENAME.get(tag, tag)))

    def handle_data(self, data):
        if self.in_style:
            self.css.append(data)
        elif self.in_title:
            self.title += data
        elif self.in_body and not self.skip and data.strip():
            self.out.append("  " * self.depth + html.escape(data.strip(), quote=False))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mock")
    p.add_argument("out", help="the .rml to write (the .rcss goes next to it)")
    p.add_argument("--model", help="data-model name on <body> (UI data bindings, CreateUIModel)")
    p.add_argument("--skin", default="skin:skin.rcss", help="the skin link (empty: none)")
    a = p.parse_args()
    notes = set()
    m = Mock(notes)
    m.feed(open(a.mock, encoding="utf-8").read())
    base = os.path.splitext(a.out)[0]
    rcss = base + ".rcss"
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    css = convert_css("\n".join(m.css), notes)
    # the document is the screen: without a size on body every percentage collapses to the content
    css = "body { width: 100%; height: 100%; }\n" + css
    open(rcss, "w", encoding="utf-8").write(css)
    links = ('  <link type="text/rcss" href="%s"/>\n' % a.skin if a.skin else "") + \
        '  <link type="text/rcss" href="%s"/>\n' % os.path.basename(rcss)
    body_attr = ' data-model="%s"' % a.model if a.model else ""
    rml = "<rml>\n<head>\n  <title>%s</title>\n%s</head>\n<body%s>\n%s\n</body>\n</rml>\n" % (
        html.escape(m.title.strip() or os.path.basename(base)), links, body_attr,
        "\n".join("  " + l for l in m.out))
    open(a.out, "w", encoding="utf-8").write(rml)
    if a.model:
        preview = base + ".preview.lua"
        if not os.path.exists(preview):   # the UI editor shows bound documents with this data (GAME_UI.md "Limits")
            fields = sorted(set(re.findall(r"\{\{\s*(\w+)", rml)) | set(re.findall(r'data-(?:if|visible)="(\w+)', rml)))
            body = ", ".join("%s = %s" % (f, "true" if f.startswith(("has", "is", "show")) else '"%s"' % f) for f in fields)
            open(preview, "w", encoding="utf-8").write("return {%s = {%s}}\n" % (a.model, body))
    ids = re.findall(r'id="([^"]+)"', rml)
    buttons = re.findall(r'<button[^>]*id="([^"]+)"', rml)
    print(json.dumps({"rml": a.out, "rcss": rcss, "elements": sum(1 for l in m.out if l.lstrip().startswith("<") and
                                                                  not l.lstrip().startswith("</")),
                      "ids": len(ids), "buttons": buttons, "changes": sorted(notes)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
