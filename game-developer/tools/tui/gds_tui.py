#!/usr/bin/env python3
"""Console for GameDeveloperSkill.

Three jobs, nothing else:
- point FabCLI at the right binary and download folder
- copy DesignerSkill into the installed hosts, or leave them alone
- read the attached Unity/Godot project

No model viewer. No web server. Stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config.json"
DEFAULTS_PATH = ROOT / "config" / "defaults.json"
DOCTOR = ROOT / "scripts" / "doctor.ps1"
RELEASES = "https://github.com/zirklerite/FabCLI/releases"

SKIP_DIRS = {".git", "__pycache__", ".variant-studio", "node_modules", ".playwright-mcp"}

HOST_DIRS = {
    "kilo": ("Kilo", [Path.home() / ".config" / "kilo" / "skills" / "real-world-design"]),
    "claude": ("Claude", [Path.home() / ".claude" / "skills" / "real-world-design"]),
    "codex": (
        "Codex",
        [
            Path.home() / ".codex" / "skills" / "real-world-design",
            Path.home() / ".agents" / "skills" / "real-world-design",
        ],
    ),
    "antigravity": (
        "Antigravity",
        [
            Path.home() / ".gemini" / "antigravity" / "skills" / "real-world-design",
            Path.home() / ".antigravity" / "skills" / "real-world-design",
        ],
    ),
}

SCREENS = ("progetto", "fab", "design")
RESET = "\x1b[0m"
ACCENT = "\x1b[38;5;179m"
DIM = "\x1b[38;5;245m"
SEL = "\x1b[48;5;236m\x1b[38;5;223m"

HOST_CMDS = {
    "kilo": [
        Path.home() / ".config" / "kilo" / "command",
        Path.home() / ".config" / "kilo" / "commands",
    ],
    "claude": [Path.home() / ".claude" / "commands"],
}


def enable_vt() -> None:
    if os.name != "nt":
        return
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        import ctypes

        kernel = ctypes.windll.kernel32
        handle = kernel.GetStdHandle(-11)
        mode = ctypes.c_uint()
        if kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def load_config() -> dict:
    path = CONFIG_PATH if CONFIG_PATH.exists() else DEFAULTS_PATH
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, dict) else {}


def save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"
    CONFIG_PATH.write_text(text, encoding="utf-8")


def ensure_shape(cfg: dict) -> None:
    fab = cfg.get("fab")
    if not isinstance(fab, dict):
        fab = {}
        cfg["fab"] = fab
    fab.setdefault("enabled", False)
    fab.setdefault("cli", "")
    fab.setdefault("library_path", "")

    project = cfg.get("project")
    if isinstance(project, str):
        project = {"path": project}
        cfg["project"] = project
    elif not isinstance(project, dict):
        project = {}
        cfg["project"] = project
    project.setdefault("path", "")

    policy = cfg.get("designerSkillPolicy")
    if not isinstance(policy, dict):
        policy = {}
        cfg["designerSkillPolicy"] = policy
    policy.setdefault("allowUpdate", False)
    policy.setdefault("lastSync", None)
    policy.setdefault("source", "")

    paths = cfg.get("paths")
    if not isinstance(paths, dict):
        cfg["paths"] = {}


def fit(text: str, width: int) -> str:
    text = text.replace("\n", " ")
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width == 1:
        return "…"
    return "…" + text[-(width - 1) :]


def sig(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    return digest


def resolve_skill_dir(raw: str) -> Path | None:
    if not raw:
        return None
    path = Path(raw)
    if (path / "SKILL.md").is_file():
        return path
    nested = path / "real-world-design"
    if (nested / "SKILL.md").is_file():
        return nested
    return None


def skill_source(cfg: dict) -> str:
    policy = cfg.get("designerSkillPolicy") or {}
    paths = cfg.get("paths") or {}
    return str(policy.get("source") or paths.get("designerSkill") or "")


def under_home(path: Path) -> bool:
    try:
        path.resolve().relative_to(Path.home().resolve())
    except ValueError:
        return False
    return True


def selected_hosts(cfg: dict) -> list[str]:
    hosts = cfg.get("hosts") or []
    if not isinstance(hosts, list):
        return []
    return [h for h in hosts if h in HOST_DIRS]


def design_targets(cfg: dict) -> list[dict]:
    source = resolve_skill_dir(skill_source(cfg))
    source_sig = sig(source / "SKILL.md") if source else None
    rows = []
    for host in selected_hosts(cfg):
        label, dirs = HOST_DIRS[host]
        for dest in dirs:
            dest_sig = sig(dest / "SKILL.md")
            if dest_sig is None:
                state = "assente"
            elif source_sig is None:
                state = "presente, sorgente illeggibile"
            elif dest_sig == source_sig:
                state = "uguale alla sorgente"
            else:
                state = "diversa dalla sorgente"
            rows.append(
                {
                    "host": host,
                    "label": label,
                    "dest": dest,
                    "state": state,
                    "safe": under_home(dest),
                }
            )
    return rows


def sync_skill(src: Path, dest: Path) -> tuple[int, int]:
    if not under_home(dest):
        raise RuntimeError(f"destinazione fuori dal profilo utente: {dest}")
    if not (src / "SKILL.md").is_file():
        raise RuntimeError(f"SKILL.md mancante in {src}")
    copied = 0
    kept = 0
    dest.mkdir(parents=True, exist_ok=True)
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        rel = Path(dirpath).relative_to(src)
        target_dir = dest / rel
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in filenames:
            target = target_dir / name
            if rel == Path(".") and name == "config.json" and target.exists():
                kept += 1
                continue
            shutil.copy2(Path(dirpath) / name, target)
            copied += 1
    return copied, kept


def scan_project(path_str: str) -> dict:
    info = {
        "path": path_str,
        "exists": False,
        "kind": "nessun percorso",
        "editor": "—",
        "gdd": "—",
        "title": "—",
        "context": "—",
        "shots": "—",
        "glbs": "—",
        "gds": "—",
        "assets": "—",
    }
    if not path_str:
        return info
    path = Path(path_str)
    if not path.exists():
        info["kind"] = "percorso inesistente"
        return info
    if not path.is_dir():
        info["kind"] = "non è una cartella"
        return info
    info["exists"] = True
    version = path / "ProjectSettings" / "ProjectVersion.txt"
    if version.is_file():
        info["kind"] = "Unity"
        text = version.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"m_EditorVersion:\s*(\S+)", text)
        info["editor"] = match.group(1) if match else "versione non letta"
    elif (path / "project.godot").is_file():
        info["kind"] = "Godot"
        info["editor"] = "project.godot"
    else:
        info["kind"] = "cartella, non è un progetto Unity o Godot"

    gdd = path / "GDD.md"
    if not gdd.is_file():
        info["gdd"] = "manca GDD.md"
    else:
        raw = gdd.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"status:\s*([A-Za-z0-9_-]+)", raw)
        info["gdd"] = f"status {match.group(1)}" if match else "presente, status non scritto"

    ctx = path / "GAME_CONTEXT.md"
    if not ctx.is_file():
        info["context"] = "manca GAME_CONTEXT.md"
    else:
        raw = ctx.read_text(encoding="utf-8", errors="replace")
        title = re.search(r"Titolo Gioco:\*\*\s*`([^`]*)`", raw)
        if title and title.group(1) and not title.group(1).startswith("["):
            info["title"] = title.group(1).strip()
        elif title:
            info["title"] = "template, titolo ancora vuoto"
        else:
            info["title"] = "contesto presente, titolo non trovato"
        info["context"] = "presente"

    shots = path / "screenshots"
    if shots.is_dir():
        pngs = [p for p in shots.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
        info["shots"] = f"{len(pngs)} immagini"
    else:
        info["shots"] = "cartella assente"

    exports = path / "art" / "exports"
    if exports.is_dir():
        glbs = list(exports.glob("*.glb"))
        info["glbs"] = f"{len(glbs)} glb in art/exports"
    else:
        info["glbs"] = "art/exports assente"

    info["assets"] = "Assets/ presente" if (path / "Assets").is_dir() else "Assets/ assente"
    gds = path / "Assets" / "_Game" / "Editor" / "GDS" / "GDS.Editor.asmdef"
    info["gds"] = "installato nel progetto" if gds.is_file() else "non installato"
    return info


def find_fabcli(configured: str) -> str:
    if configured:
        path = Path(configured)
        if path.is_file():
            return str(path)
    found = shutil.which("fabcli")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        Path.home() / ".local" / "bin" / "fabcli.exe",
        Path.home() / "bin" / "fabcli.exe",
        Path(local) / "fabcli" / "fabcli.exe" if local else None,
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return str(candidate)
    return ""


def token_path() -> Path:
    override = os.environ.get("FABCLI_TOKEN_PATH", "").strip()
    if override:
        return Path(override)
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        return Path(appdata) / "fabcli" / "token.json"
    return Path.home() / "AppData" / "Roaming" / "fabcli" / "token.json"


def run_capture(argv: list[str], timeout: int) -> tuple[int, str]:
    try:
        done = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or "") + (exc.stderr or "")
        return 124, (out or "") + "\ntempo scaduto"
    except OSError as exc:
        return 1, str(exc)
    text = ""
    if done.stdout:
        text += done.stdout
    if done.stderr:
        if text and not text.endswith("\n"):
            text += "\n"
        text += done.stderr
    return done.returncode, text.strip()


def probe_fab(cfg: dict) -> dict:
    fab = cfg.get("fab") or {}
    configured = str(fab.get("cli") or "")
    exe = find_fabcli(configured)
    token = token_path()
    library = str(fab.get("library_path") or "")
    info = {
        "exe": exe,
        "configured": configured,
        "version": "non eseguito",
        "token": "presente" if token.is_file() else "assente",
        "token_path": str(token),
        "library": library,
        "library_state": "non impostata",
        "enabled": bool(fab.get("enabled")),
    }
    if library:
        info["library_state"] = "esiste" if Path(library).is_dir() else "cartella assente"
    if not exe:
        info["version"] = "eseguibile non trovato"
        return info
    code, text = run_capture([exe, "--version"], 8)
    first = text.splitlines()[0].strip() if text else ""
    info["version"] = first or f"exit {code}, nessuna versione"
    return info


def clipboard_text() -> str:
    if os.name != "nt":
        return ""
    code, text = run_capture(
        ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
        4,
    )
    if code != 0:
        return ""
    return text.strip().strip('"')


class App:
    def __init__(self, cfg: dict):
        ensure_shape(cfg)
        self.cfg = cfg
        self.screen = "progetto"
        self.focus = 0
        self.notice = "Legge il progetto. Non lo modifica."
        self.mode = "main"
        self.edit = ""
        self.edit_id = ""
        self.log: list[str] = []
        self.log_top = 0
        self.pending = ""
        self.dirty = False
        self.project = scan_project(str(cfg["project"].get("path") or ""))
        self.fab = probe_fab(cfg)

    def items(self) -> list[dict]:
        if self.screen == "progetto":
            p = self.project
            return [
                {"id": "h", "kind": "header", "label": "Progetto collegato"},
                {"id": "path", "kind": "field", "label": "Percorso", "value": p["path"] or "vuoto"},
                {"id": "i1", "kind": "info", "label": "Tipo", "value": p["kind"]},
                {"id": "i2", "kind": "info", "label": "Editor", "value": p["editor"]},
                {"id": "i3", "kind": "info", "label": "GDD", "value": p["gdd"]},
                {"id": "i4", "kind": "info", "label": "Titolo", "value": p["title"]},
                {"id": "i5", "kind": "info", "label": "Contesto", "value": p["context"]},
                {"id": "i6", "kind": "info", "label": "Screenshot", "value": p["shots"]},
                {"id": "i7", "kind": "info", "label": "Export", "value": p["glbs"]},
                {"id": "i8", "kind": "info", "label": "Assets", "value": p["assets"]},
                {"id": "i9", "kind": "info", "label": "GDS editor", "value": p["gds"]},
                {"id": "gap", "kind": "gap", "label": ""},
                {"id": "h2", "kind": "header", "label": "Azioni"},
                {"id": "rescan", "kind": "action", "label": "Rileggi il disco", "value": "invio"},
                {
                    "id": "doctor",
                    "kind": "action",
                    "label": "Esegui doctor",
                    "value": "crea screenshots/ se manca",
                },
            ]
        if self.screen == "fab":
            fab = self.fab
            uso = "acceso" if fab["enabled"] else "spento"
            exe = fab["exe"] or "non trovato"
            return [
                {"id": "h", "kind": "header", "label": "FabCLI — tool non ufficiale"},
                {
                    "id": "cli",
                    "kind": "field",
                    "label": "Eseguibile",
                    "value": fab["configured"] or "vuoto, non salvato",
                },
                {"id": "found", "kind": "info", "label": "Trovato", "value": exe},
                {"id": "ver", "kind": "info", "label": "Versione", "value": fab["version"]},
                {"id": "tok", "kind": "info", "label": "Token", "value": f"{fab['token']}  {fab['token_path']}"},
                {"id": "lib", "kind": "field", "label": "Download", "value": fab["library"] or "vuoto"},
                {"id": "lib2", "kind": "info", "label": "Cartella", "value": fab["library_state"]},
                {"id": "on", "kind": "toggle", "label": "Uso nel workflow", "value": uso},
                {"id": "gap", "kind": "gap", "label": ""},
                {"id": "h2", "kind": "header", "label": "Azioni"},
                {"id": "pin", "kind": "action", "label": "Fissa trovato", "value": exe},
                {"id": "version", "kind": "action", "label": "Leggi la versione", "value": "fabcli --version"},
                {"id": "status", "kind": "action", "label": "Stato login", "value": "fabcli auth status"},
                {"id": "login", "kind": "action", "label": "Accedi", "value": "apre la finestra Epic"},
                {"id": "releases", "kind": "action", "label": "Apri le release", "value": "se l'eseguibile manca"},
            ]
        source = skill_source(self.cfg)
        resolved = resolve_skill_dir(source)
        policy = self.cfg["designerSkillPolicy"]
        choice = "consentito" if policy.get("allowUpdate") else "no, le copie restano"
        last = policy.get("lastSync") or "mai"
        rows = [
            {"id": "h", "kind": "header", "label": "DesignerSkill"},
            {"id": "src", "kind": "field", "label": "Sorgente", "value": source or "vuoto"},
            {
                "id": "res",
                "kind": "info",
                "label": "SKILL.md",
                "value": str(resolved) if resolved else "non trovato sotto la sorgente",
            },
            {"id": "pol", "kind": "toggle", "label": "Aggiornamento", "value": choice},
            {"id": "last", "kind": "info", "label": "Ultima copia", "value": str(last)},
            {"id": "gap", "kind": "gap", "label": ""},
            {"id": "h2", "kind": "header", "label": "Copie installate"},
        ]
        targets = design_targets(self.cfg)
        if not targets:
            rows.append(
                {
                    "id": "none",
                    "kind": "info",
                    "label": "Host",
                    "value": "nessun host noto in config.hosts",
                }
            )
        for index, target in enumerate(targets):
            rows.append(
                {
                    "id": f"t{index}",
                    "kind": "info",
                    "label": target["label"],
                    "value": target["state"],
                }
            )
            rows.append(
                {
                    "id": f"p{index}",
                    "kind": "info",
                    "label": "cartella",
                    "value": str(target["dest"]),
                }
            )
        rows.extend(
            [
                {"id": "gap2", "kind": "gap", "label": ""},
                {"id": "h3", "kind": "header", "label": "Azioni"},
                {
                    "id": "sync",
                    "kind": "action",
                    "label": "Aggiorna le copie",
                    "value": "non tocca config.json né MCP",
                },
                {
                    "id": "leave",
                    "kind": "action",
                    "label": "Non aggiornare",
                    "value": "salva la scelta e non copia",
                },
            ]
        )
        return rows

    def focusables(self) -> list[int]:
        return [i for i, item in enumerate(self.items()) if item["kind"] in {"field", "toggle", "action"}]

    def clamp_focus(self) -> None:
        ids = self.focusables()
        if not ids:
            self.focus = 0
            return
        self.focus = max(0, min(self.focus, len(ids) - 1))

    def current(self) -> dict | None:
        ids = self.focusables()
        self.clamp_focus()
        if not ids:
            return None
        return self.items()[ids[self.focus]]

    def render(self, width: int, height: int) -> list[str]:
        width = max(40, width)
        height = max(12, height)
        inner = width - 1
        title = " GDS   FabCLI, DesignerSkill, progetto aperto"
        if self.dirty:
            title += "   modifiche non salvate"
        lines = [ACCENT + fit(title, inner) + RESET]
        tabs = []
        for name in SCREENS:
            label = name.upper() if name == self.screen else name
            tabs.append((ACCENT + label + RESET) if name == self.screen else (DIM + label + RESET))
        lines.append("  " + "    ".join(tabs))
        blurbs = {
            "progetto": "Stato del gioco sul disco. Doctor è l'unica azione che può creare screenshots/.",
            "fab": "FabCLI si scarica dalle release. Qui si imposta il binario, la cartella e il login. Nessun viewer.",
            "design": "La sorgente è la cartella Desktop. Aggiornare ricopia i file. config.json delle copie resta.",
        }
        lines.append(fit(" " + blurbs[self.screen], inner))

        body = self._body_lines(inner)
        window = max(1, height - 5)
        focus_line = 0
        ids = self.focusables()
        if ids:
            wanted = ids[min(self.focus, len(ids) - 1)]
            for index, (item_index, _text) in enumerate(body):
                if item_index == wanted:
                    focus_line = index
                    break
        top = 0
        if self.mode == "log":
            body = [(None, fit(line, inner)) for line in self.log] or [(None, "(vuoto)")]
            window = max(1, height - 5)
            top = min(self.log_top, max(0, len(body) - window))
            self.log_top = top
        else:
            if focus_line >= top + window:
                top = focus_line - window + 1
            if focus_line < top:
                top = focus_line

        slice_ = body[top : top + window]
        while len(slice_) < window:
            slice_.append((None, ""))
        for _item_index, text in slice_:
            lines.append(text)

        notice = self.notice
        if self.mode == "edit":
            notice = "modifica: " + self.edit
        elif self.mode == "confirm":
            notice = self.notice
        lines.append(fit(" " + notice, inner))
        if self.mode == "edit":
            help_line = " invio conferma   esc annulla   ctrl+v incolla"
        elif self.mode == "log":
            help_line = " j/k scorri   esc chiude il log"
        elif self.mode == "confirm":
            help_line = " y conferma   n annulla"
        else:
            help_line = " 1 2 3 schermate   e modifica   invio esegue   spazio toggle   s salva   q esci"
        lines.append(fit(help_line, inner))
        return lines[:height]

    def _body_lines(self, width: int) -> list[tuple[int | None, str]]:
        rows = []
        focus_ids = self.focusables()
        selected = focus_ids[self.focus] if focus_ids else -1
        for index, item in enumerate(self.items()):
            if item["kind"] == "gap":
                rows.append((None, ""))
                continue
            if item["kind"] == "header":
                rows.append((None, DIM + fit(" " + item["label"], width) + RESET))
                continue
            marker = ">" if index == selected and self.mode != "log" else " "
            label = item["label"][:18].ljust(18)
            prefix = f"{marker} {label} "
            value = fit(item.get("value") or "", max(8, width - len(prefix)))
            text = prefix + value
            if index == selected and self.mode != "log":
                text = SEL + text + RESET
            rows.append((index, text))
        return rows

    def set_screen(self, name: str) -> None:
        self.screen = name
        self.focus = 0
        self.mode = "main"
        if name == "progetto":
            self.notice = "Legge il progetto. Non lo modifica."
        elif name == "fab":
            self.notice = "Il token non viene letto. Si controlla solo se il file c'è."
        else:
            self.notice = "Aggiornare è una copia di file. Non è un git pull."

    def mark(self) -> None:
        self.dirty = True

    def save(self) -> None:
        save_config(self.cfg)
        self.dirty = False
        self.notice = f"salvato {CONFIG_PATH}"

    def rescan(self) -> None:
        path = str(self.cfg["project"].get("path") or "")
        self.project = scan_project(path)
        self.notice = "progetto riletto"

    def refresh_fab(self) -> None:
        self.fab = probe_fab(self.cfg)

    def begin_edit(self) -> None:
        item = self.current()
        if not item or item["kind"] != "field":
            self.notice = "questa riga non si modifica"
            return
        self.mode = "edit"
        self.edit_id = item["id"]
        current = {
            "path": str(self.cfg["project"].get("path") or ""),
            "cli": str(self.cfg["fab"].get("cli") or ""),
            "lib": str(self.cfg["fab"].get("library_path") or ""),
            "src": skill_source(self.cfg),
        }
        self.edit = current.get(self.edit_id, "")

    def commit_edit(self) -> None:
        value = self.edit.strip().strip('"')
        if self.edit_id == "path":
            self.cfg["project"]["path"] = value
            self.project = scan_project(value)
        elif self.edit_id == "cli":
            self.cfg["fab"]["cli"] = value
            self.refresh_fab()
        elif self.edit_id == "lib":
            self.cfg["fab"]["library_path"] = value
            self.refresh_fab()
        elif self.edit_id == "src":
            self.cfg["paths"]["designerSkill"] = value
            self.cfg["designerSkillPolicy"]["source"] = value
        self.mark()
        self.mode = "main"
        self.notice = "valore in memoria, s per scriverlo su disco"

    def toggle(self) -> None:
        item = self.current()
        if not item or item["kind"] != "toggle":
            return
        if item["id"] == "on":
            self.cfg["fab"]["enabled"] = not bool(self.cfg["fab"].get("enabled"))
            self.refresh_fab()
            state = "acceso" if self.cfg["fab"]["enabled"] else "spento"
            self.notice = f"FabCLI nel workflow: {state}"
        elif item["id"] == "pol":
            policy = self.cfg["designerSkillPolicy"]
            policy["allowUpdate"] = not bool(policy.get("allowUpdate"))
            state = "consentito" if policy["allowUpdate"] else "bloccato"
            self.notice = f"aggiornamento DesignerSkill {state}"
        self.mark()

    def ask(self, key: str, text: str) -> None:
        self.pending = key
        self.mode = "confirm"
        self.notice = text

    def open_log(self, title: str, text: str) -> None:
        self.log = [title, ""] + (text.splitlines() or ["(nessun output)"])
        self.log_top = 0
        self.mode = "log"
        self.notice = title

    def do_version(self) -> None:
        exe = self.fab.get("exe") or ""
        if not exe:
            self.notice = "FabCLI non trovato. Apri le release, estrai fabcli.exe, poi e sul percorso."
            return
        code, text = run_capture([exe, "--version"], 12)
        self.refresh_fab()
        self.open_log(f"fabcli --version  exit {code}", text)

    def do_status(self) -> None:
        exe = self.fab.get("exe") or ""
        if not exe:
            self.notice = "FabCLI non trovato."
            return
        code, text = run_capture([exe, "auth", "status", "--pretty"], 25)
        self.open_log(f"fabcli auth status  exit {code}", text)

    def do_login(self) -> None:
        exe = self.fab.get("exe") or ""
        if not exe:
            self.notice = "Prima imposta l'eseguibile."
            return
        leave_screen()
        try:
            print("Login FabCLI. Si apre la finestra Epic. Quando finisce torni qui.")
            subprocess.run([exe, "auth", "login"])
        finally:
            enter_screen()
        code, text = run_capture([exe, "auth", "status", "--pretty"], 25)
        self.refresh_fab()
        self.open_log(f"dopo il login  auth status exit {code}", text)

    def do_doctor(self) -> None:
        if not DOCTOR.is_file():
            self.notice = f"manca {DOCTOR}"
            return
        argv = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(DOCTOR),
            "-ConfigPath",
            str(CONFIG_PATH if CONFIG_PATH.exists() else DEFAULTS_PATH),
        ]
        project = str(self.cfg["project"].get("path") or "")
        if project:
            argv.extend(["-ProjectPath", project])
        code, text = run_capture(argv, 120)
        self.open_log(f"doctor  exit {code}", text)
        self.rescan()

    def do_sync(self) -> None:
        source = resolve_skill_dir(skill_source(self.cfg))
        if source is None:
            self.notice = "Sorgente senza SKILL.md. Correggi il percorso."
            return
        targets = [row for row in design_targets(self.cfg) if row["safe"]]
        if not targets:
            self.notice = "Nessuna destinazione. Controlla config.hosts."
            return
        copied = 0
        kept = 0
        notes = []
        for row in targets:
            try:
                c, k = sync_skill(source, row["dest"])
            except Exception as exc:
                notes.append(f"ERRORE {row['dest']}: {exc}")
                continue
            copied += c
            kept += k
            notes.append(f"{row['label']}  {c} file  config tenuti {k}  {row['dest']}")
        if copied == 0:
            self.open_log("copia non riuscita", "\n".join(notes) or "nessun file")
            return

        self.cfg["designerSkillPolicy"]["allowUpdate"] = True
        self.cfg["designerSkillPolicy"]["lastSync"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        self.cfg["designerSkillPolicy"]["source"] = skill_source(self.cfg)
        cmd = source.parent / "command" / "design.md"
        if cmd.is_file():
            for host in selected_hosts(self.cfg):
                for folder in HOST_CMDS.get(host, []):
                    if not under_home(folder):
                        continue
                    folder.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(cmd, folder / "design.md")
                    notes.append(f"comando /design  {folder / 'design.md'}")
        self.mark()
        self.save()
        self.open_log(f"copia fatta  {copied} file, {kept} config.json lasciati", "\n".join(notes))

    def do_leave(self) -> None:
        self.cfg["designerSkillPolicy"]["allowUpdate"] = False
        self.mark()
        self.save()
        self.notice = "aggiornamento disattivato e salvato. Nessun file copiato."

    def activate(self) -> None:
        item = self.current()
        if not item:
            return
        if item["kind"] == "field":
            self.begin_edit()
            return
        if item["kind"] == "toggle":
            self.toggle()
            return
        action = item["id"]
        if action == "rescan":
            self.rescan()
        elif action == "doctor":
            self.ask("doctor", "Doctor può creare screenshots/ nel progetto. Eseguirlo? y/n")
        elif action == "pin":
            exe = self.fab.get("exe") or ""
            if not exe:
                self.notice = "Nessun fabcli.exe trovato da fissare."
                return
            self.cfg["fab"]["cli"] = exe
            self.mark()
            self.refresh_fab()
            self.notice = "eseguibile fissato in memoria, s per salvarlo"
        elif action == "version":
            self.do_version()
        elif action == "status":
            self.do_status()
        elif action == "login":
            self.ask("login", "Apre la finestra di login Epic. Continuare? y/n")
        elif action == "releases":
            webbrowser.open(RELEASES)
            self.notice = "pagina release aperta nel browser"
        elif action == "sync":
            self.ask("sync", "Ricopiare DesignerSkill sugli host in config? config.json esistente resta. y/n")
        elif action == "leave":
            self.do_leave()

    def confirm(self, yes: bool) -> None:
        pending = self.pending
        self.pending = ""
        self.mode = "main"
        if not yes:
            self.notice = "annullato"
            return
        if pending == "doctor":
            self.do_doctor()
        elif pending == "login":
            self.do_login()
        elif pending == "sync":
            self.do_sync()
        elif pending == "quit":
            raise SystemExit(0)

    def handle(self, key: str) -> None:
        if self.mode == "edit":
            self._edit_key(key)
            return
        if self.mode == "log":
            if key in {"esc", "q"}:
                self.mode = "main"
                self.notice = "log chiuso"
            elif key in {"j", "down"}:
                self.log_top += 1
            elif key in {"k", "up"}:
                self.log_top = max(0, self.log_top - 1)
            return
        if self.mode == "confirm":
            if key == "s" and self.pending == "quit":
                self.save()
                raise SystemExit(0)
            if key in {"y", "Y"}:
                self.confirm(True)
            elif key in {"n", "N", "esc"}:
                self.confirm(False)
            return

        if key in {"q"}:
            if self.dirty:
                self.ask("quit", "Modifiche non salvate. y esce senza salvare, n torna, s salva ed esce.")
                return
            raise SystemExit(0)
        if key == "s":
            self.save()
            return
        if key == "1":
            self.set_screen("progetto")
            return
        if key == "2":
            self.set_screen("fab")
            return
        if key == "3":
            self.set_screen("design")
            return
        if key in {"right", "l"}:
            index = SCREENS.index(self.screen)
            self.set_screen(SCREENS[(index + 1) % len(SCREENS)])
            return
        if key in {"left", "h"}:
            index = SCREENS.index(self.screen)
            self.set_screen(SCREENS[(index - 1) % len(SCREENS)])
            return
        if key in {"j", "down"}:
            self.focus += 1
            self.clamp_focus()
            return
        if key in {"k", "up"}:
            self.focus -= 1
            self.clamp_focus()
            return
        if key == "e":
            self.begin_edit()
            return
        if key == "space":
            self.toggle()
            return
        if key == "enter":
            self.activate()
            return
        if key == "r" and self.screen == "progetto":
            self.rescan()

    def _edit_key(self, key: str) -> None:
        if key == "enter":
            self.commit_edit()
        elif key == "esc":
            self.mode = "main"
            self.notice = "modifica annullata"
        elif key == "backspace":
            self.edit = self.edit[:-1]
        elif key == "paste":
            clip = clipboard_text()
            if clip:
                self.edit += clip
        elif key and len(key) == 1 and key.isprintable():
            self.edit += key


def read_key() -> str:
    import msvcrt

    ch = msvcrt.getwch()
    if ch in {"\x00", "\xe0"}:
        nxt = msvcrt.getwch()
        return {"H": "up", "P": "down", "K": "left", "M": "right"}.get(nxt, "")
    if ch == "\r":
        return "enter"
    if ch == "\x1b":
        return "esc"
    if ch == "\x08" or ch == "\x7f":
        return "backspace"
    if ch == "\x16":
        return "paste"
    if ch == "\x03":
        raise KeyboardInterrupt
    if ch == " ":
        return "space"
    return ch


def enter_screen() -> None:
    sys.stdout.write("\x1b[?1049h\x1b[?25l\x1b[2J\x1b[H")
    sys.stdout.flush()


def leave_screen() -> None:
    sys.stdout.write("\x1b[?25h\x1b[?1049l")
    sys.stdout.flush()


def paint(lines: list[str]) -> None:
    out = ["\x1b[H"]
    last = len(lines) - 1
    for index, line in enumerate(lines):
        out.append("\x1b[2K")
        out.append(line)
        if index != last:
            out.append("\r\n")
    sys.stdout.write("".join(out))
    sys.stdout.flush()


def run_ui(app: App) -> None:
    enter_screen()
    try:
        while True:
            size = shutil.get_terminal_size(fallback=(100, 32))
            paint(app.render(size.columns, size.lines))
            app.handle(read_key())
    finally:
        leave_screen()


def plain(app: App, width: int = 100) -> str:
    blocks = []
    for name in SCREENS:
        app.set_screen(name)
        app.mode = "main"
        blocks.append("\n".join(app.render(width, 36)))
        blocks.append("")
    return "\n".join(blocks)


def check_text(cfg: dict) -> str:
    ensure_shape(cfg)
    project = scan_project(str(cfg["project"].get("path") or ""))
    fab = probe_fab(cfg)
    lines = [
        f"config: {CONFIG_PATH}",
        f"progetto: {project['path'] or '(vuoto)'} | {project['kind']} | gdd {project['gdd']}",
        f"fab: enabled={fab['enabled']} exe={fab['exe'] or '(manca)'} version={fab['version']}",
        f"fab download: {fab['library'] or '(vuoto)'} {fab['library_state']}",
        f"fab token: {fab['token']} {fab['token_path']}",
        f"designer source: {skill_source(cfg) or '(vuoto)'}",
        f"designer resolved: {resolve_skill_dir(skill_source(cfg)) or '(no SKILL.md)'}",
        f"designer allowUpdate: {cfg['designerSkillPolicy'].get('allowUpdate')}",
    ]
    for row in design_targets(cfg):
        lines.append(f"  {row['label']}: {row['state']} | {row['dest']}")
    return "\n".join(lines)


def selftest() -> int:
    import tempfile

    empty = scan_project("")
    assert empty["kind"] == "nessun percorso"
    missing = scan_project(r"C:\questa\cartella\non\esiste\gds")
    assert missing["kind"] == "percorso inesistente"

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        proj = root / "Game"
        (proj / "ProjectSettings").mkdir(parents=True)
        (proj / "ProjectSettings" / "ProjectVersion.txt").write_text(
            "m_EditorVersion: 6000.3.2f1\n", encoding="utf-8"
        )
        (proj / "Assets").mkdir()
        (proj / "GDD.md").write_text("---\nstatus: locked\n---\n", encoding="utf-8")
        (proj / "GAME_CONTEXT.md").write_text(
            "- **Titolo Gioco:** `Osteria`\n", encoding="utf-8"
        )
        (proj / "screenshots").mkdir()
        (proj / "screenshots" / "a.png").write_bytes(b"x")
        (proj / "art" / "exports").mkdir(parents=True)
        (proj / "art" / "exports" / "house.glb").write_bytes(b"glb")
        scanned = scan_project(str(proj))
        assert scanned["kind"] == "Unity", scanned
        assert scanned["editor"] == "6000.3.2f1"
        assert scanned["gdd"] == "status locked"
        assert scanned["title"] == "Osteria"
        assert scanned["shots"] == "1 immagini"
        assert "1 glb" in scanned["glbs"]

        src = root / "skill"
        (src / "references").mkdir(parents=True)
        (src / "SKILL.md").write_text("skill-v2\n", encoding="utf-8")
        (src / "references" / "a.md").write_text("a\n", encoding="utf-8")
        (src / "config.json").write_text('{"from":"source"}\n', encoding="utf-8")
        dest = root / "homeish"
        # under_home would reject this dest; test the copy rules directly
        dest.mkdir()
        (dest / "config.json").write_text('{"from":"user"}\n', encoding="utf-8")
        copied = 0
        kept = 0
        for dirpath, dirnames, filenames in os.walk(src):
            dirnames[:] = [n for n in dirnames if n not in SKIP_DIRS]
            rel = Path(dirpath).relative_to(src)
            target_dir = dest / rel
            target_dir.mkdir(parents=True, exist_ok=True)
            for name in filenames:
                target = target_dir / name
                if rel == Path(".") and name == "config.json" and target.exists():
                    kept += 1
                    continue
                shutil.copy2(Path(dirpath) / name, target)
                copied += 1
        assert (dest / "SKILL.md").read_text(encoding="utf-8") == "skill-v2\n"
        assert json.loads((dest / "config.json").read_text(encoding="utf-8"))["from"] == "user"
        assert kept == 1 and copied >= 2

        cfg = {"extra": {"keep": True}, "hosts": ["kilo"], "paths": {}}
        ensure_shape(cfg)
        assert cfg["extra"]["keep"] is True
        assert cfg["fab"]["enabled"] is False
        assert cfg["project"]["path"] == ""
        cfg["project"]["path"] = str(proj)
        found = find_fabcli(str(src / "SKILL.md"))
        assert found == str(src / "SKILL.md")
        assert find_fabcli("") in {"", shutil.which("fabcli") or ""}
        cfg["fab"]["cli"] = ""

        app = App(cfg)
        text = plain(app, 96)
        assert "Osteria" in text
        assert "6000.3.2f1" in text
        assert "FabCLI" in text
        assert "config.json" in text
        assert "Fissa trovato" in text
        assert "Fissa eseguibile t" not in text

        app.handle("e")
        assert app.mode == "edit"
        app.edit = str(proj)
        app.handle("enter")
        assert app.cfg["project"]["path"] == str(proj)
        assert app.project["title"] == "Osteria"
        assert app.dirty is True
        app.handle("2")
        assert app.screen == "fab"
        for _ in range(12):
            current = app.current()
            if current and current["id"] == "on":
                break
            app.handle("down")
        assert app.current()["id"] == "on"
        app.handle("space")
        assert app.cfg["fab"]["enabled"] is True
        try:
            app.handle("q")
        except SystemExit:
            raise AssertionError("quit with dirty state must ask first")
        assert app.mode == "confirm"
        app.handle("n")
        assert app.mode == "main"

    installed = Path.home() / ".agents" / "skills" / "real-world-design"
    if installed.is_dir():
        found = resolve_skill_dir(str(installed))
        assert found is not None and (found / "SKILL.md").is_file()
    print("selftest ok")
    return 0


def main(argv: list[str]) -> int:
    enable_vt()
    cfg = load_config()
    if "--selftest" in argv:
        return selftest()
    if "--check" in argv:
        print(check_text(cfg))
        return 0
    app = App(cfg)
    if "--preview" in argv:
        print(plain(app))
        return 0
    if os.name != "nt":
        print("Questa console è scritta per Windows.")
        print(check_text(cfg))
        return 1
    if not sys.stdout.isatty():
        print("Serve un terminale interattivo.")
        print("Avvia start-dashboard.bat")
        print(check_text(cfg))
        return 1
    try:
        run_ui(app)
    except SystemExit:
        return 0
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
