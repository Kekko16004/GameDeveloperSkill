#!/usr/bin/env python3
"""Unit tests of html2rml.py (standard library only):  python scripts/tests/test_html2rml.py  [-v]"""
import json
import os
import re
import shutil
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import html2rml as h  # noqa: E402


def decl(prop, val, ctx=None, bg=None):
    ctx = ctx or h.Ctx()
    return dict(h.convert_decl(prop, val, ctx, bg)), ctx


def tiny_ttf(path, family):
    """A font file with only a name table (family = name ID 1), enough for font_family_of."""
    s = family.encode("utf-16-be")
    name = struct.pack(">HHH", 0, 1, 6 + 12) + struct.pack(">HHHHHH", 3, 1, 0x409, 1, len(s), 0) + s
    head = struct.pack(">IHHHH", 0x00010000, 1, 16, 0, 0)
    rec = struct.pack(">4sIII", b"name", 0, 12 + 16, len(name))
    with open(path, "wb") as f:
        f.write(head + rec + name)


class Project:
    """A scratch project: project.ncproject, UI/fonts, UI/img, a mock under .variant-studio."""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="html2rml-test-")
        h.write_text(os.path.join(self.root, "project.ncproject"), "return {}\n")
        os.makedirs(os.path.join(self.root, "UI", "fonts"))
        os.makedirs(os.path.join(self.root, "UI", "Img"))
        os.makedirs(os.path.join(self.root, ".variant-studio", "rounds", "001"))
        tiny_ttf(os.path.join(self.root, "UI", "fonts", "Narrow-Bold.ttf"), "PT Sans Narrow")
        h.write_text(os.path.join(self.root, "UI", "Img", "plate.png"), "PNG")

    def convert(self, html_text, name="t", **kw):
        mock = os.path.join(self.root, ".variant-studio", "rounds", "001", "a.html")
        h.write_text(mock, html_text)
        out = os.path.join(self.root, "UI", "_conv_test", name, name + ".rml")
        rep = h.convert(mock, out, **kw)
        rml = h.read_text(out)
        rcss = h.read_text(out[:-4] + ".rcss")
        return rep, rml, rcss

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


def page(css, body):
    return "<!doctype html><html><head><title>T</title><style>%s</style></head><body>%s</body></html>" % (css, body)


class Gradients(unittest.TestCase):
    def test_gradient_to_bottom_is_vertical(self):
        d, _ = decl("background-image", "linear-gradient(to bottom, #000000, #FFFFFF)")
        self.assertEqual(d["decorator"], "vertical-gradient(#000000 #FFFFFF)")

    def test_gradient_to_top_reverses_colors(self):
        d, _ = decl("background-image", "linear-gradient(to top, #111111, #222222)")
        self.assertEqual(d["decorator"], "vertical-gradient(#222222 #111111)")

    def test_gradient_to_right_is_horizontal(self):
        d, _ = decl("background-image", "linear-gradient(to right, #111111, #222222)")
        self.assertEqual(d["decorator"], "horizontal-gradient(#111111 #222222)")

    def test_gradient_to_left_reverses_horizontal(self):
        d, _ = decl("background", "linear-gradient(to left, #111111, #222222)")
        self.assertEqual(d["decorator"], "horizontal-gradient(#222222 #111111)")
        self.assertEqual(d["background-color"], "transparent")

    def test_gradient_angles(self):
        self.assertEqual(decl("background-image", "linear-gradient(90deg, #111111, #222222)")[0]["decorator"],
                         "horizontal-gradient(#111111 #222222)")
        self.assertEqual(decl("background-image", "linear-gradient(0deg, #111111, #222222)")[0]["decorator"],
                         "vertical-gradient(#222222 #111111)")
        d, ctx = decl("background-image", "linear-gradient(100deg, #111111, #222222)")
        self.assertEqual(d["decorator"], "horizontal-gradient(#111111 #222222)")
        self.assertTrue(any("snapped" in n for n in ctx.notes))

    def test_gradient_default_direction_and_rgba(self):
        d, _ = decl("background-image", "linear-gradient(rgba(0,0,0,0.5), transparent)")
        self.assertEqual(d["decorator"], "vertical-gradient(#00000080 transparent)")

    def test_gradient_multistop_is_reported(self):
        d, ctx = decl("background-image", "linear-gradient(to bottom, #000 0%, #111 40%, #222 100%)")
        self.assertEqual(d["decorator"], "vertical-gradient(#000 #222)")
        self.assertTrue(any("multi-stop" in n for n in ctx.notes))

    def test_radial_gradient_dropped(self):
        d, ctx = decl("background-image", "radial-gradient(circle, #000, #fff)")
        self.assertEqual(d["decorator"], "none")
        self.assertTrue(any("radial-gradient" in n for n in ctx.notes))

    def test_gradient_and_image_layers_keep_css_order(self):
        ctx = h.Ctx()
        ctx.maps = [("/p/", ctx.mock_dir)]
        d, _ = decl("background-image", "linear-gradient(to right, #000, #fff), url('/p/x.png')", ctx,
                    {"background-size": "cover"})
        self.assertTrue(d["decorator"].startswith("horizontal-gradient(#000 #fff), image("))
        self.assertTrue(d["decorator"].endswith(" cover)"))


class Borders(unittest.TestCase):
    def test_border_shorthand_drops_solid(self):
        d, _ = decl("border", "2px solid #FFFFFF")
        self.assertEqual(d["border"], "2dp #FFFFFF")

    def test_border_side_with_style_first(self):
        d, _ = decl("border-left", "solid 4px transparent")
        self.assertEqual(d["border-left"], "4dp transparent")

    def test_border_none(self):
        self.assertEqual(decl("border", "none")[0]["border"], "0dp")
        self.assertEqual(decl("border-style", "none")[0]["border-width"], "0dp")

    def test_border_style_property_dropped(self):
        self.assertEqual(decl("border-style", "solid")[0], {})


class Motion(unittest.TestCase):
    def test_ease_out_becomes_cubic_out(self):
        d, _ = decl("transition", "background-color 0.08s ease-out, color 80ms ease-in-out")
        self.assertEqual(d["transition"], "background-color 0.08s cubic-out, color 0.08s cubic-in-out")

    def test_linear_and_bezier(self):
        self.assertEqual(decl("transition", "opacity 1s linear")[0]["transition"], "opacity 1s linear-in-out")
        self.assertEqual(decl("transition", "opacity 1s cubic-bezier(.2,.8,.2,1)")[0]["transition"], "opacity 1s cubic-in-out")

    def test_unknown_transition_property_dropped(self):
        d, ctx = decl("transition", "outline-color 0.1s ease, opacity 0.2s ease")
        self.assertEqual(d["transition"], "opacity 0.2s quadratic-in-out")

    def test_transition_all_alone(self):
        self.assertEqual(decl("transition", "all 0.2s ease-out")[0]["transition"], "all 0.2s cubic-out")

    def test_animation_easing(self):
        d, _ = decl("animation", "pulse 600ms ease-in-out infinite alternate forwards")
        self.assertEqual(d["animation"], "pulse 0.6s cubic-in-out infinite alternate")

    def test_transform_rotate_kept(self):
        self.assertEqual(decl("transform", "rotate(26deg)")[0]["transform"], "rotate(26deg)")
        self.assertEqual(decl("transform", "translate(10px, -50%) rotate(0.25turn)")[0]["transform"],
                         "translate(10dp, -50%) rotate(90deg)")


class Vars(unittest.TestCase):
    def test_nested_var_and_fallback(self):
        ctx = h.Ctx()
        ctx.vars = {"--a": "var(--b)", "--b": "12px"}
        self.assertEqual(decl("padding", "var(--a) var(--missing, 4px)", ctx)[0]["padding"], "12dp 4dp")

    def test_undefined_var_drops_declaration(self):
        d, ctx = decl("color", "var(--nope)")
        self.assertEqual(d, {})
        self.assertTrue(any("--nope" in n for n in ctx.notes))

    def test_var_in_style_attribute(self):
        p = Project()
        try:
            _, rml, _ = p.convert(page(":root { --gap: 24px; --accent: #E0962B; }",
                                       '<div style="margin-left: var(--gap); color: var(--accent)">x</div>'))
            self.assertIn('style="margin-left: 24dp; color: #E0962B;"', rml)
        finally:
            p.close()

    def test_scoped_custom_property_reported(self):
        ctx = h.Ctx()
        h.convert_css(".x { --c: red; color: var(--c, blue); }", ctx)
        self.assertTrue(any("ignored" in n for n in ctx.notes))


class Units(unittest.TestCase):
    def test_vw_vh_kept_px_rem_converted(self):
        d, _ = decl("margin", "1.5vw 2vh 3px 1rem")
        self.assertEqual(d["margin"], "1.5vw 2vh 3dp 16dp")

    def test_em_kept(self):
        self.assertEqual(decl("letter-spacing", "0.1em")[0]["letter-spacing"], "0.1em")

    def test_vmin_vmax(self):
        self.assertEqual(decl("width", "10vmin")[0]["width"], "10vh")

    def test_calc_same_unit_and_mixed(self):
        self.assertEqual(decl("width", "calc(10px + 6px)")[0]["width"], "16dp")
        d, ctx = decl("width", "calc(100% - 20px)")
        self.assertEqual(d, {})
        self.assertTrue(any("calc()" in n for n in ctx.notes))

    def test_url_not_rewritten(self):
        ctx = h.Ctx()
        masked, restore = h.mask_urls("url('/icons/16px.png') 12px")
        self.assertEqual(restore(masked), "url('/icons/16px.png') 12px")
        self.assertEqual(h.convert_units("url('/icons/16px.png') 12px", ctx), "url('/icons/16px.png') 12dp")

    def test_rgba_alpha_and_named_colors(self):
        self.assertEqual(decl("color", "rgba(224, 150, 43, 0.5)")[0]["color"], "#E0962B80")
        self.assertEqual(decl("color", "rgb(255 0 0 / 25%)")[0]["color"], "#FF000040")
        self.assertEqual(decl("color", "tomato")[0]["color"], "#FF6347")
        self.assertEqual(decl("color", "white")[0]["color"], "white")

    def test_font_size_snapped_to_whole_pixels(self):
        d, _ = decl("font-size", "0.8333vw")    # 15.9994 px at 1920: RmlUi would draw 15 px
        v = float(d["font-size"][:-2])
        self.assertEqual(int(v * 19.2), 16)
        self.assertEqual(decl("font-size", "1.1vw")[0]["font-size"], "1.1vw")   # 21.12 px: not a whole pixel, untouched

    def test_letter_spacing_rounded_to_whole_pixels(self):
        d, _ = decl("letter-spacing", "0.05208vw")   # 0.9999 px at 1920: RmlUi would add no spacing at all
        self.assertEqual(int(float(d["letter-spacing"][:-2]) * 19.2), 1)
        self.assertEqual(decl("letter-spacing", "0.0781vw")[0]["letter-spacing"], "0.0781vw")   # 1.4995 px: a half, goes down
        self.assertEqual(decl("letter-spacing", "1.5px")[0]["letter-spacing"], "1.5dp")
        self.assertEqual(decl("letter-spacing", "1.7px")[0]["letter-spacing"], "2dp")
        self.assertEqual(decl("letter-spacing", "1px")[0]["letter-spacing"], "1dp")
        self.assertEqual(decl("letter-spacing", "0.0156vw")[0]["letter-spacing"], "0.0156vw")   # 0.3 px: truncates to 0, nearest
        self.assertEqual(decl("letter-spacing", "-1px")[0]["letter-spacing"], "-1dp")

    def test_overflow_hidden_clips_always(self):
        d, _ = decl("overflow", "hidden")
        self.assertEqual(d["clip"], "always")

    def test_unsupported_properties_dropped(self):
        for prop, val in (("box-shadow", "0 0 4px #000"), ("filter", "blur(2px)"), ("outline", "1px solid red"),
                          ("object-fit", "cover"), ("cursor", "pointer")):
            d, ctx = decl(prop, val)
            if prop == "cursor":
                self.assertEqual(d, {"cursor": "pointer"})
            else:
                self.assertEqual(d, {}, prop)
                self.assertTrue(ctx.notes)

    def test_text_shadow_to_font_effect(self):
        self.assertEqual(decl("text-shadow", "1px 2px #000")[0]["font-effect"], "shadow(1dp 2dp #000)")
        self.assertEqual(decl("text-shadow", "0 0 4px #E0962B")[0]["font-effect"], "glow(0dp 4dp 0 0 #E0962B)")

    def test_important_removed(self):
        self.assertEqual(decl("color", "#fff !important")[0]["color"], "#fff")


class Documents(unittest.TestCase):
    def setUp(self):
        self.p = Project()

    def tearDown(self):
        self.p.close()

    def test_font_face_listed_and_lua_written(self):
        css = ('@font-face { font-family: "Narrow Display"; font-weight: 700; src: url("/p/ui/fonts/Narrow-Bold.ttf"); }'
               ' .t { font-family: "Narrow Display", Arial, sans-serif; }')
        rep, rml, rcss = self.p.convert(page(css, '<span class="t">A</span>'))
        self.assertEqual([f["path"] for f in rep["fonts"]], ["UI/fonts/Narrow-Bold.ttf"])   # the disk case: UI, not ui
        self.assertIn("font-family: PT Sans Narrow", rcss)   # renamed to the family inside the file
        self.assertNotIn("@font-face", rcss)
        lua = h.read_text(rep["fontsLua"])
        self.assertIn('"UI/fonts/Narrow-Bold.ttf"', lua)
        self.assertIn("UI.loadFont", lua)
        self.assertIn('UI.loadFont("UI/fonts/Narrow-Bold.ttf")', rep["lua"])

    def test_variant_studio_parts_stripped(self):
        css = ('.concept { display: none; } html[data-vs-state="Concept"] .ui { display: none; }'
               ' .cap { height: 40px; } .ui { width: 100%; }')
        body = ('<div class="cap"><span>01</span>Caption</div><div class="ui">X</div>'
                '<img class="concept" src="/p/ui/Img/plate.png" alt="c"><div data-vs-only>vs</div>')
        rep, rml, rcss = self.p.convert(page(css, body))
        self.assertNotIn("concept", rml + rcss)
        self.assertNotIn("Caption", rml)
        self.assertNotIn(".cap", rcss)
        self.assertNotIn("data-vs", rml + rcss)
        self.assertIn('<div class="ui">X</div>', rml)

    def test_state_selection(self):
        body = '<div class="ui"><div class="frame">ONE</div><div class="frame">TWO</div></div>'
        rep, rml, _ = self.p.convert(page(".frame { height: 10px; }", body), state=2)
        self.assertEqual(rep["states"], 2)
        self.assertIn("TWO", rml)
        self.assertNotIn("ONE", rml)

    def test_text_in_flex_container_wrapped(self):
        css = ".row { display: flex; } .row span { margin-left: 8px; }"
        _, rml, _ = self.p.convert(page(css, '<div class="row"><img src="/p/ui/Img/plate.png">Seleziona</div>'))
        self.assertIn("<anon>Seleziona</anon>", rml)

    def test_space_between_inline_elements_kept(self):
        _, rml, _ = self.p.convert(page("", '<div><b>18,4</b> <span>KG</span></div>'))
        self.assertIn("<b>18,4</b> <span>KG</span>", rml)

    def test_text_runs_not_reindented(self):
        _, rml, _ = self.p.convert(page("", '<div>Usa una benda <span class="k">[3]</span>.</div>'))
        self.assertIn('<div>Usa una benda <span class="k">[3]</span>.</div>', rml)

    def test_paths_relative_with_disk_case_and_inline_background_fit(self):
        css = ".screen { background-size: 100% 100%; background-repeat: no-repeat; }"
        rep, rml, _ = self.p.convert(page(css, '<div class="screen" style="background-image: url(\'/p/ui/img/plate.png\')">'
                                              '<img src="/p/ui/img/plate.png"></div>'))
        self.assertIn('src="../../Img/plate.png"', rml)
        self.assertIn("decorator: image(../../Img/plate.png fill)", rml)
        self.assertIn("UI/Img/plate.png", rep["assets"])
        self.assertEqual(rep["missing"], [])

    def test_missing_asset_reported(self):
        rep, _, _ = self.p.convert(page("", '<img src="/p/ui/none.png">'))
        self.assertTrue(rep["missing"])

    def test_ua_sheet_and_renames(self):
        _, rml, rcss = self.p.convert(page("section > ul li { color: #fff; }", "<section><ul><li>a</li></ul></section>"))
        self.assertIn("div, p, h1, h2, h3, pre, hr, form { display: block; }", rcss)
        self.assertIn("div > div div { color: #fff; }", rcss)

    def test_report_written(self):
        rep, _, _ = self.p.convert(page("", "<div>x</div>"), name="rep")
        on_disk = json.loads(h.read_text(rep["rml"][:-4] + ".conv.json"))
        self.assertEqual(on_disk["rml"], rep["rml"])


if __name__ == "__main__":
    unittest.main()
