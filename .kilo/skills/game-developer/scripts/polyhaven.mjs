#!/usr/bin/env node
/**
 * Poly Haven CC0 helper. Usage:
 *   node polyhaven.mjs search <query> [--type textures|models]
 *   node polyhaven.mjs get <id> --out <dir> [--res 1k|2k]
 * HDRIs are refused (game-asset lighting rule).
 */
const UA = "GameDeveloperSkill/1.0";
const args = process.argv.slice(2);
const cmd = args[0];

function flag(name, fallback) {
  const i = args.indexOf(name);
  if (i === -1) return fallback;
  return args[i + 1] ?? fallback;
}

async function api(path) {
  const res = await fetch("https://api.polyhaven.com" + path, {
    headers: { "User-Agent": UA },
  });
  if (!res.ok) throw new Error(`Poly Haven ${res.status} ${path} (check User-Agent)`);
  return res.json();
}

if (cmd === "search") {
  const q = (args[1] || "").toLowerCase();
  const typeName = flag("--type", "textures");
  const typeMap = { hdris: 0, textures: 1, models: 2 };
  if (typeName === "hdris") {
    console.error("HDRIs are forbidden for game-asset lighting.");
    process.exit(2);
  }
  const data = await api("/assets?t=" + typeName);
  const hits = Object.entries(data)
    .filter(([id, a]) => {
      const blob = (id + " " + (a.name || "") + " " + (a.tags || []).join(" ")).toLowerCase();
      return !q || blob.includes(q);
    })
    .slice(0, 12);
  for (const [id, a] of hits) {
    console.log(`${id}\t${a.name || ""}\t${(a.tags || []).slice(0, 6).join(",")}`);
  }
} else if (cmd === "get") {
  const id = args[1];
  const out = flag("--out", ".");
  const res = flag("--res", "1k");
  if (!id) {
    console.error("id required");
    process.exit(2);
  }
  const metaList = await api("/assets");
  const meta = metaList[id];
  if (meta && meta.type === 0) {
    console.error("Refusing HDRI " + id);
    process.exit(2);
  }
  const files = await api("/files/" + id);
  const { mkdir, writeFile } = await import("node:fs/promises");
  const { join, basename } = await import("node:path");
  await mkdir(out, { recursive: true });
  const urls = [];
  function walk(obj) {
    if (!obj || typeof obj !== "object") return;
    if (typeof obj.url === "string") urls.push(obj.url);
    for (const v of Object.values(obj)) walk(v);
  }
  const bucket = files[res] || files.gltf || files.blend || files;
  walk(bucket);
  const picked = urls.filter((u) => u.includes(res) || u.endsWith(".gltf") || u.endsWith(".glb") || u.endsWith(".png") || u.endsWith(".jpg") || u.endsWith(".exr")).slice(0, 12);
  const list = picked.length ? picked : urls.slice(0, 8);
  for (const url of list) {
    const r = await fetch(url, { headers: { "User-Agent": UA } });
    if (!r.ok) continue;
    const name = basename(new URL(url).pathname);
    const buf = Buffer.from(await r.arrayBuffer());
    await writeFile(join(out, name), buf);
    console.log("saved " + join(out, name));
  }
  console.log("ledger: " + id + " | polyhaven | CC0 | " + out + " | attrib Poly Haven");
} else {
  console.error("Usage: node polyhaven.mjs search <q> [--type textures|models]");
  console.error("       node polyhaven.mjs get <id> --out <dir> [--res 1k|2k]");
  process.exit(1);
}
