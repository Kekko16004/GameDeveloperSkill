// game-developer hooks for the skillkit installer: engine/tool detection, config.json merge, Blender addon, doctor.
import fs from "node:fs";
import path from "node:path";

const ENV = process.env;
const LOCAL = ENV.LOCALAPPDATA || "";
const PF = ENV.ProgramFiles || "C:\\Program Files";
const PF86 = ENV["ProgramFiles(x86)"] || "C:\\Program Files (x86)";

function first(ctx, list) { for (const p of list) if (p && ctx.exists(p)) return p; return ""; }

// bounded search: stops at `depth`, skips heavy folders, gives up after `budgetMs`
function findFile(roots, name, { depth = 4, budgetMs = 2500 } = {}) {
  const t0 = Date.now();
  const skip = new Set(["node_modules", ".git", "Library", "Temp", "obj", "bin", "__pycache__", ".venv", "venv", "Intermediate", "Saved", "DerivedDataCache"]);
  const hits = [];
  const walk = (d, lvl) => {
    if (lvl > depth || Date.now() - t0 > budgetMs) return;
    let entries; try { entries = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (e.isFile() && e.name.toLowerCase() === name.toLowerCase()) hits.push(path.join(d, e.name));
      else if (e.isDirectory() && !skip.has(e.name) && !e.name.startsWith(".")) walk(path.join(d, e.name), lvl + 1);
    }
  };
  for (const r of roots) if (r && fs.existsSync(r)) walk(r, 0);
  return hits.sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
}

const verOf = (s) => { const m = /(\d+)\.(\d+)(?:\.(\d+))?/.exec(s); return m ? [+m[1], +m[2], +(m[3] || 0)] : [0, 0, 0]; };
const byVer = (a, b) => { const x = verOf(a), y = verOf(b); for (let i = 0; i < 3; i++) if (x[i] !== y[i]) return y[i] - x[i]; return 0; };

export async function detect(ctx) {
  const { HOME, which, runSync, exists, ui, g, c, T, S, isWin } = ctx;
  const d = {};

  // Unity CLI + editors
  d.unityCli = which("unity") || first(ctx, [path.join(LOCAL, "Unity", "bin", "unity.exe"), path.join(PF, "Unity Hub", "resources", "cli", "unity.exe")]);
  d.unityEditors = [];
  if (d.unityCli) {
    const r = runSync(d.unityCli, ["editors", "--installed", "--format", "json", "--no-banner"], { timeout: 15000 });
    try { d.unityEditors = (JSON.parse(r.out.slice(r.out.indexOf("{"))).data || []).map((e) => e.version).filter(Boolean); } catch {}
  }

  // Unreal: launcher manifest + usual folders
  const ue = new Set();
  const dat = path.join(ENV.ProgramData || "C:\\ProgramData", "Epic", "UnrealEngineLauncher", "LauncherInstalled.dat");
  if (exists(dat)) { try { for (const i of JSON.parse(fs.readFileSync(dat, "utf8")).InstallationList || []) if (/^UE_\d/.test(i.AppName)) ue.add(i.InstallLocation); } catch {} }
  for (const root of [path.join(PF, "Epic Games"), "C:\\Games", "D:\\Games", "D:\\Epic Games"]) {
    try { for (const e of fs.readdirSync(root, { withFileTypes: true })) if (e.isDirectory() && /^UE_/.test(e.name)) ue.add(path.join(root, e.name)); } catch {}
  }
  d.unreal = [...ue].filter((p) => exists(path.join(p, "Engine", "Binaries", isWin ? "Win64" : "Mac", isWin ? "UnrealEditor.exe" : "UnrealEditor.app"))).sort(byVer);

  // Nucleon editor (PATH, then a bounded search of the usual dev roots)
  d.nucleon = which("NucleonEditor") || findFile([path.join(HOME, "Desktop", "Dev Things"), path.join(HOME, "Desktop"), path.join(HOME, "Documents"), path.join(HOME, "source", "repos"), "C:\\Dev", "D:\\Dev"], isWin ? "NucleonEditor.exe" : "NucleonEditor")[0] || "";

  // Blender: newest version folder wins
  d.blender = which("blender");
  if (!d.blender && isWin) {
    const all = findFile([path.join(PF, "Blender Foundation"), path.join(PF86, "Steam", "steamapps", "common", "Blender"), path.join(LOCAL, "Programs", "Blender Foundation")], "blender.exe", { depth: 2 });
    d.blender = all.sort((a, b) => byVer(path.basename(path.dirname(a)), path.basename(path.dirname(b))))[0] || "";
  }
  if (!d.blender && !isWin) d.blender = first(ctx, ["/Applications/Blender.app/Contents/MacOS/Blender"]);

  d.godot = which("godot") || which("godot4") || "";
  d.fabcli = which("fabcli") || first(ctx, [path.join(LOCAL, "fabcli", "fabcli.exe"), path.join(HOME, ".local", "bin", "fabcli.exe"), path.join(HOME, "Tools", "fabcli", "fabcli.exe")]);
  d.uvx = which("uvx") || first(ctx, [path.join(HOME, ".local", "bin", isWin ? "uvx.exe" : "uvx")]);
  // the real interpreter path (py.exe and Store aliases are launchers): MCP clients spawn it without a shell
  d.python = "";
  let storeAlias = "";
  for (const launcher of ["python", "python3", "py"]) {
    const exe = which(launcher) || (isWin && launcher === "python" ? "python" : "");
    if (!exe) continue;
    const r = runSync(exe, ["-c", "import sys; print(sys.executable)"]);
    const exePath = r.out.split(/\r?\n/).pop().trim();
    // a Store python reports an exe under "Program Files\WindowsApps" that cannot be spawned directly: prefer another, else its alias
    if (r.code === 0 && exePath && /[\\/]WindowsApps[\\/]/i.test(exePath)) { storeAlias = storeAlias || exe; continue; }
    if (r.code === 0 && exePath && exists(exePath)) { d.python = exePath; break; }
  }
  if (!d.python && storeAlias) d.python = storeAlias;

  // VoxelAI: saved path, then the usual checkouts
  const savedCfg = previousConfig(ctx);
  d.voxelai = first(ctx, [savedCfg?.paths?.voxelai, path.join(HOME, "Desktop", "Dev Things", "VoxelAIArtist"), path.join(HOME, "Desktop", "VoxelAIArtist"), path.join(HOME, "Documents", "VoxelAIArtist")]);

  ctx.detected = { ...ctx.detected, ...d };
  ctx.vars.paths = { voxelai: d.voxelai, blender: d.blender, unityCli: d.unityCli, unreal: d.unreal.at(-1) || "", nucleon: d.nucleon, godot: d.godot };
  ctx.vars.python = d.python || "python";

  const it = ctx.lang === "it";
  const engines = [
    d.unityCli && `Unity${d.unityEditors.length ? " " + d.unityEditors.slice(0, 3).join(", ") : ""}`,
    d.unreal.length && `Unreal ${d.unreal.map((p) => (/UE_([\d.]+)/.exec(p) || [])[1] || "?").join(", ")}`,
    d.nucleon && "Nucleon",
    d.godot && "Godot",
  ].filter(Boolean);
  ui.row(engines.length ? "ok" : "warn", "Engine", engines.join(` ${g.dot} `) || "—", engines.length ? "" : (it ? "l'engine si sceglie all'intervista GDD" : "the engine is picked in the GDD interview"));
  const unrealOld = d.unreal.length && !d.unreal.some((p) => /UE_(5\.(8|9)|[6-9])/.test(p));
  if (unrealOld) ui.row("warn", "Unreal", it ? "serve 5.8+ per l'MCP ufficiale (stile realistico)" : "5.8+ needed for the official MCP (realistic style)");
  const tools = [d.blender && "Blender", d.fabcli && "FabCLI", d.voxelai && "VoxelAI"].filter(Boolean);
  ui.row(tools.length ? "ok" : "off", it ? "Strumenti 3D" : "3D tools", tools.join(` ${g.dot} `) || "—",
    [!d.blender && "Blender", !d.fabcli && "FabCLI"].filter(Boolean).length ? c.faint(`${S.notFound}: ${[!d.blender && "Blender", !d.fabcli && "FabCLI"].filter(Boolean).join(", ")}`) : "");
}

// config.json values set by the user on this PC: canonical copy first, then older host copies, then the repo one
function previousConfig(ctx) {
  const cands = [
    path.join(ctx.CANON, "game-developer", "config.json"),
    path.join(ctx.HOME, ".claude", "skills", "game-developer", "config.json"),
    path.join(ctx.HOME, ".config", "kilo", "skills", "game-developer", "config.json"),
    path.join(ctx.HOME, ".codex", "skills", "game-developer", "config.json"),
    path.join(ctx.ROOT, "game-developer", "config.json"),
  ];
  // a backup made by this installer counts too (the old copy was moved there)
  for (const p of cands) { const j = ctx.readJson(p); if (j) return j; }
  return null;
}

function merge(base, over) {
  for (const [k, v] of Object.entries(over || {})) {
    if (v && typeof v === "object" && !Array.isArray(v) && base[k] && typeof base[k] === "object" && !Array.isArray(base[k])) merge(base[k], v);
    else if (v !== null && v !== undefined && v !== "") base[k] = v;
  }
  return base;
}

export async function config(ctx, skill, dest) {
  const defaults = ctx.readJson(path.join(ctx.ROOT, skill.path, "config", "defaults.json"), {});
  const user = ctx.prevConfig ?? (ctx.prevConfig = previousConfig(ctx));
  const d = ctx.detected;
  const detected = {
    hosts: ctx.hosts,
    paths: { blender: d.blender, unityCli: d.unityCli, voxelai: ctx.vars.voxelai?.dir || d.voxelai, terminalmcp: ctx.vars.terminalmcp?.dir || "", unreal: d.unreal?.at(-1) || "", nucleon: d.nucleon, godot: d.godot, designerSkill: path.join(ctx.CANON, "designer") },
    fab: { cli: d.fabcli },
  };
  const cfg = merge(merge(structuredClone(defaults), detected), dropMissingPaths(ctx, structuredClone(user || {})));
  // paths managed by the installer always follow the current install
  if (ctx.vars.terminalmcp?.dir) cfg.paths.terminalmcp = ctx.vars.terminalmcp.dir;
  cfg.hosts = ctx.hosts;
  cfg.modules = cfg.modules || {};
  const on = (id) => ctx.components.includes(id);
  Object.assign(cfg.modules, { designSkill: on("designer"), unityOfficialSkills: on("unitySkills"), terminalMcp: on("terminalmcp"), blenderMcp: on("blenderMcp"), voxelMcp: on("voxelai") });
  delete cfg.paths.designerSkillLegacy;
  if (!ctx.DRY) fs.writeFileSync(path.join(dest, "config.json"), JSON.stringify(cfg, null, 2) + "\n");
}
function dropMissingPaths(ctx, user) {
  // saved paths that do not exist on this PC (copied from another machine) are dropped, detection wins
  for (const [k, v] of Object.entries(user.paths || {})) if (typeof v === "string" && v && !ctx.exists(v)) user.paths[k] = "";
  // the installer manages these now
  if (user.paths) { delete user.paths.terminalmcp; delete user.paths.designerSkill; }
  delete user.hosts;
  delete user.modules?.designSkill; delete user.modules?.unityOfficialSkills; delete user.modules?.terminalMcp; delete user.modules?.blenderMcp; delete user.modules?.voxelMcp;
  return user;
}

export async function after(ctx) {
  const { ui, run, which, runSync, isWin, lang, ROOT, CANON, detected: d } = ctx;
  const it = lang === "it";
  if (ctx.components.includes("blenderMcp") && d.uvx) {
    await ui.task(it ? "addon Blender" : "Blender addon", async (t) => {
      if (ctx.DRY) return {};
      const r = await run(d.uvx, ["mcp-for-blender", "install-addon"], { onLine: t.update, env: { PYTHONIOENCODING: "utf-8" }, timeout: 300000 });
      return r.code === 0 ? { note: it ? "Blender → Preferenze → Add-on → MCP for Blender" : "Blender → Preferences → Add-ons → MCP for Blender" } : { state: "warn", note: r.out.trim().split("\n").pop() };
    });
  }
  if (d.unityCli) {
    await ui.task("Unity CLI", async () => {
      const r = runSync(d.unityCli, ["auth", "status", "--format", "json", "--no-banner"], { timeout: 15000 });
      let logged = null; try { logged = JSON.parse(r.out.slice(r.out.indexOf("{"))).data?.loggedIn; } catch {}
      if (logged === false) { ctx.footer.push(`${ctx.c.warn(ctx.g.warn)} unity auth login`); return { state: "warn", note: it ? "sessione scaduta: unity auth login" : "session expired: unity auth login" }; }
      return { note: d.unityEditors.length ? d.unityEditors.join(", ") : "ok" };
    });
  } else {
    ctx.footer.push(`${ctx.c.dim("Unity CLI")}  ${isWin ? "$env:UNITY_CLI_CHANNEL='beta'; irm https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.ps1 | iex" : "curl -fsSL https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.sh | bash"}`);
  }
  if (isWin) {
    await ui.task("doctor.ps1", async () => {
      if (ctx.DRY) return {};
      const r = await run("powershell", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", path.join(CANON, "game-developer", "scripts", "doctor.ps1"), "-ConfigPath", path.join(CANON, "game-developer", "config.json")], { timeout: 120000 });
      const lines = r.out.split(/\r?\n/).filter((l) => /^(PASS|WARN|FAIL) \|/.test(l));
      const n = (s) => lines.filter((l) => l.startsWith(s)).length;
      for (const l of lines.filter((x) => x.startsWith("FAIL"))) ui.detail(l.replace(/^FAIL \| /, ""), "err");
      return { state: n("FAIL") ? "warn" : "ok", note: `${n("PASS")} pass ${ctx.g.dot} ${n("WARN")} warn ${ctx.g.dot} ${n("FAIL")} fail` };
    });
  }
}

export async function summary(ctx, rows) {
  const it = ctx.lang === "it";
  rows.push([it ? "Usa" : "Use", "/game <idea>   /gdd   /playtest   /resumegame"]);
  if (ctx.hosts.includes("claude")) ctx.footer.push(`${ctx.c.dim(it ? "Realistico (Claude Code)" : "Realistic (Claude Code)")}  /plugin install unreal-engine-skills-for-claude-code@claude-plugins-official`);
  if (ctx.components.includes("blenderMcp")) ctx.footer.push(`${ctx.c.dim("Blender")}  ${it ? "pannello N → MCP → Start MCP Server (solo per edifici / hero prop)" : "N panel → MCP → Start MCP Server (buildings / hero props only)"}`);
}

export async function doctor(ctx) {
  const cfg = ctx.readJson(path.join(ctx.CANON, "game-developer", "config.json"));
  if (!cfg) { ctx.ui.row("fail", "config.json", ctx.S.missing); return 1; }
  ctx.ui.row("ok", "config.json", ctx.tilde(path.join(ctx.CANON, "game-developer", "config.json")));
  return 0;
}
