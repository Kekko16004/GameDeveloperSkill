// CwXmlToBin: converte file CodeWalker XML (esportati da Sollumz) nei binari usati dal gioco/FiveM.
// Uso:
//   CwXmlToBin <input.xxx.xml> [output]          singolo file (output default = input senza ".xml")
//   CwXmlToBin --dir <cartella_in> [cartella_out] tutti i *.xml (ricorsivo)
//   CwXmlToBin --info <file binario>              rilegge il binario e stampa il contenuto (verifica)
//   CwXmlToBin --gen9 <in> <out>                  converte un binario Gen8 (Legacy) in Gen9 (Enhanced)
//                                                  (.ydr/.ydd/.yft/.ytd/.ypt; gli altri tipi sono identici)
//   CwXmlToBin --gen9-dir <cartella_in> <cartella_out>
// Le texture embedded devono stare nella cartella omonima accanto all'XML (come le crea Sollumz).
using System;
using System.IO;
using System.Xml;
using CodeWalker.GameFiles;
using CodeWalker.Core.Utils;

static class Program
{
    static int Convert(string input, string output)
    {
        var fname = Path.GetFileName(input).ToLowerInvariant();
        var fmt = XmlMeta.GetXMLFormat(fname, out int trim);
        if (fmt == MetaFormat.XML)
        {
            Console.Error.WriteLine($"[skip] formato non riconosciuto: {fname}");
            return 1;
        }
        var doc = new XmlDocument();
        doc.Load(input);
        var folder = Path.GetDirectoryName(Path.GetFullPath(input)) ?? ".";
        // le texture embedded di x.ydr.xml stanno in <cartella>/x/
        var baseName = fname.Substring(0, fname.Length - trim);
        var texFolder = Path.Combine(folder, Path.GetFileNameWithoutExtension(baseName));
        byte[] data = XmlMeta.GetData(doc, fmt, Directory.Exists(texFolder) ? texFolder : folder);
        if (data == null || data.Length == 0)
        {
            Console.Error.WriteLine($"[ERRORE] conversione fallita: {fname} ({fmt})");
            return 2;
        }
        output ??= Path.Combine(folder, baseName);
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output)) ?? ".");
        File.WriteAllBytes(output, data);
        Console.WriteLine($"[ok] {fname} -> {output} ({data.Length} bytes, {fmt})");
        return 0;
    }

    static void DrawableInfo(DrawableBase d, string indent = "  ")
    {
        if (d == null) { Console.WriteLine(indent + "drawable: null"); return; }
        var m = d.DrawableModels;
        Console.WriteLine($"{indent}models H/M/L/VL: {m?.High?.Length ?? 0}/{m?.Med?.Length ?? 0}/{m?.Low?.Length ?? 0}/{m?.VLow?.Length ?? 0}  lodDist H/M/L/VL: {d.LodDistHigh}/{d.LodDistMed}/{d.LodDistLow}/{d.LodDistVlow}");
        var sg = d.ShaderGroup;
        Console.WriteLine($"{indent}shaders: {sg?.Shaders?.data_items?.Length ?? 0}");
        var tex = sg?.TextureDictionary?.Textures?.data_items;
        Console.WriteLine($"{indent}embedded textures: {(tex == null ? "0" : string.Join(", ", Array.ConvertAll(tex, t => $"{t.Name} {t.Width}x{t.Height} {t.Format} mips={t.Levels}")))}");
        var bones = d.Skeleton?.Bones?.Items;
        Console.WriteLine($"{indent}bones: {(bones == null ? "0 (nessuno scheletro)" : string.Join(", ", Array.ConvertAll(bones, b => $"{b.Name}#{b.Tag}")))}");
        if (d is Drawable dr)
        {
            Console.WriteLine($"{indent}lights: {dr.LightAttributes?.data_items?.Length ?? 0}  embedded bound: {(dr.Bound != null ? dr.Bound.Type.ToString() : "no")}");
        }
    }

    static int Info(string path)
    {
        var data = File.ReadAllBytes(path);
        var ext = Path.GetExtension(path).ToLowerInvariant();
        uint ver = data.Length >= 8 ? BitConverter.ToUInt32(data, 4) : 0;
        bool gen9 = (ext == ".ytd" && ver == 5) || ((ext == ".ydr" || ext == ".ydd") && ver == 159) ||
                    (ext == ".yft" && ver == 171) || (ext == ".ypt" && ver == 71);
        Console.WriteLine($"== {Path.GetFileName(path)} ({data.Length} bytes, RSC v{ver} => {(gen9 ? "Gen9/Enhanced" : "Gen8/Legacy")})");
        var prevGen9 = RpfManager.IsGen9;
        RpfManager.IsGen9 = gen9;
        try { InfoBody(ext, data); } finally { RpfManager.IsGen9 = prevGen9; }
        return 0;
    }

    static void InfoBody(string ext, byte[] data)
    {
        switch (ext)
        {
            case ".ydr":
                DrawableInfo(RpfFile.GetResourceFile<YdrFile>(data)?.Drawable);
                break;
            case ".yft":
                var yft = RpfFile.GetResourceFile<YftFile>(data);
                DrawableInfo(yft?.Fragment?.Drawable);
                var grp = yft?.Fragment?.PhysicsLODGroup?.PhysicsLOD1?.Groups?.data_items;
                Console.WriteLine($"  physics groups: {(grp == null ? "0" : string.Join(", ", Array.ConvertAll(grp, g => g.Name.ToString())))}");
                break;
            case ".ytd":
                var ytd = RpfFile.GetResourceFile<YtdFile>(data);
                var t = ytd?.TextureDict?.Textures?.data_items;
                Console.WriteLine($"  textures: {(t == null ? "0" : string.Join(", ", Array.ConvertAll(t, x => $"{x.Name} {x.Width}x{x.Height} {x.Format} mips={x.Levels}")))}");
                break;
            case ".ycd":
                var ycd = RpfFile.GetResourceFile<YcdFile>(data);
                foreach (var c in ycd?.ClipMapEntries ?? Array.Empty<ClipMapEntry>())
                    Console.WriteLine($"  clip: {c.Clip?.ShortName} (hash {c.Hash}) type={c.Clip?.Type}");
                Console.WriteLine($"  animations: {ycd?.AnimMapEntries?.Length ?? 0}");
                break;
            default:
                Console.WriteLine("  (info non disponibile per questo tipo)");
                break;
        }
    }

    static int ToGen9(string input, string output)
    {
        var data = File.ReadAllBytes(input);
        var ext = Path.GetExtension(input).ToLowerInvariant();
        var prev = RpfManager.IsGen9;
        RpfManager.IsGen9 = true;
        try
        {
            var outData = Gen9Converter.TryConvert(data, ext, msg => { }, Path.GetFileName(input), true, out bool converted);
            if (outData == null) { Console.Error.WriteLine($"[ERRORE] gen9: {input}"); return 2; }
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output)) ?? ".");
            File.WriteAllBytes(output, outData);
            Console.WriteLine($"[ok] gen9 {(converted ? "convertito" : "copiato (non serve conversione)")}: {Path.GetFileName(input)} -> {output}");
            return 0;
        }
        finally { RpfManager.IsGen9 = prev; }
    }

    static int Main(string[] args)
    {
        if (args.Length == 0)
        {
            Console.WriteLine("Uso: CwXmlToBin <file.xml> [output] | --dir <in> [out]");
            return 1;
        }
        try
        {
            if (args[0] == "--info")
            {
                for (int i = 1; i < args.Length; i++) Info(args[i]);
                return 0;
            }
            if (args[0] == "--gen9") return ToGen9(args[1], args[2]);
            if (args[0] == "--gen9-dir")
            {
                int errs = 0;
                foreach (var f in Directory.GetFiles(args[1]))
                    errs += ToGen9(f, Path.Combine(args[2], Path.GetFileName(f))) == 0 ? 0 : 1;
                return errs == 0 ? 0 : 2;
            }
            if (args[0] == "--dir")
            {
                var inDir = args[1];
                var outDir = args.Length > 2 ? args[2] : null;
                int errors = 0;
                foreach (var f in Directory.GetFiles(inDir, "*.xml", SearchOption.AllDirectories))
                {
                    string o = null;
                    if (outDir != null)
                    {
                        var rel = Path.GetRelativePath(inDir, f);
                        o = Path.Combine(outDir, rel.Substring(0, rel.Length - 4));
                    }
                    errors += Convert(f, o) == 0 ? 0 : 1;
                }
                return errors == 0 ? 0 : 2;
            }
            return Convert(args[0], args.Length > 1 ? args[1] : null);
        }
        catch (Exception e)
        {
            Console.Error.WriteLine("[ERRORE] " + e);
            return 3;
        }
    }
}
