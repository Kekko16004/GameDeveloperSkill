import fs from "node:fs";
import path from "node:path";

function cssToUss(cssContent) {
  let uss = cssContent;
  uss = uss.replace(/px/g, "px");
  uss = uss.replace(/rem/g, "0px");
  uss = uss.replace(/box-sizing:[^;]+;/g, "");
  uss = uss.replace(/display:\s*flex;/g, "display: flex; flex-direction: column;");
  return uss;
}

function convertTag(nodeName, attrs, textContent) {
  const className = attrs.class ? ` class="${attrs.class}"` : "";
  const name = attrs.id ? ` name="${attrs.id}"` : "";
  const text = textContent ? ` text="${textContent.trim().replace(/"/g, "&quot;")}"` : "";

  switch (nodeName.toLowerCase()) {
    case "button":
      return `<ui:Button${name}${className}${text} />`;
    case "h1":
    case "h2":
    case "h3":
    case "p":
    case "span":
    case "label":
      return `<ui:Label${name}${className}${text} />`;
    case "input":
      return `<ui:TextField${name}${className} />`;
    case "img":
      return `<ui:Image${name}${className} />`;
    case "div":
    case "section":
    case "main":
    case "header":
    default:
      return `<ui:VisualElement${name}${className}>`;
  }
}

function parseHtmlSimple(htmlContent) {
  const bodyMatch = htmlContent.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  const content = bodyMatch ? bodyMatch[1] : htmlContent;
  
  let uxmlBody = "";
  const tagRegex = /<([a-zA-Z0-9]+)([^>]*)>([^<]*)<\/\1>|<([a-zA-Z0-9]+)([^>]*)\/>|<([a-zA-Z0-9]+)([^>]*)>/g;
  let match;
  
  while ((match = tagRegex.exec(content)) !== null) {
    const isPair = !!match[1];
    const tagName = match[1] || match[4] || match[6];
    const rawAttrs = match[2] || match[5] || match[7] || "";
    const text = isPair ? match[3] : "";

    const attrs = {};
    const attrRegex = /([a-zA-Z0-9_-]+)="([^"]*)"/g;
    let attrMatch;
    while ((attrMatch = attrRegex.exec(rawAttrs)) !== null) {
      attrs[attrMatch[1]] = attrMatch[2];
    }

    if (isPair) {
      uxmlBody += `    ${convertTag(tagName, attrs, text)}\n`;
    } else if (match[4]) {
      uxmlBody += `    ${convertTag(tagName, attrs, "")}\n`;
    } else if (match[6]) {
      uxmlBody += `    ${convertTag(tagName, attrs, "")}\n`;
    }
  }

  return uxmlBody;
}

function generateCSharpController(className, buttons) {
  const fields = buttons.map(b => `    private Button _${b}Button;`).join("\n");
  const queries = buttons.map(b => `        _${b}Button = root.Q<Button>("${b}");\n        if (_${b}Button != null) _${b}Button.clicked += On${b}Clicked;`).join("\n");
  const handlers = buttons.map(b => `    private void On${b}Clicked()\n    {\n        Debug.Log("${b} clicked");\n    }`).join("\n\n");

  return `using UnityEngine;
using UnityEngine.UIElements;

public class ${className} : MonoBehaviour
{
    [SerializeField] private UIDocument uiDocument;

${fields}

    private void OnEnable()
    {
        if (uiDocument == null) uiDocument = GetComponent<UIDocument>();
        if (uiDocument == null) return;

        var root = uiDocument.rootVisualElement;
${queries}
    }

${handlers}
}
`;
}

function main() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error("Usage: node ui-transpiler.mjs <input.html> <input.css> [outputDir] [screenName]");
    process.exit(1);
  }

  const htmlPath = path.resolve(args[0]);
  const cssPath = path.resolve(args[1]);
  const outDir = path.resolve(args[2] || "./Assets/_Game/UI");
  const screenName = args[3] || "HUD";

  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  const html = fs.readFileSync(htmlPath, "utf-8");
  const css = fs.existsSync(cssPath) ? fs.readFileSync(cssPath, "utf-8") : "";

  const uss = cssToUss(css);
  const ussPath = path.join(outDir, `${screenName}.uss`);
  fs.writeFileSync(ussPath, uss, "utf-8");

  const uxmlInner = parseHtmlSimple(html);
  const uxml = `<?xml version="1.0" encoding="utf-8"?>
<ui:UXML
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:ui="UnityEngine.UIElements"
    xmlns:uie="UnityEditor.UIElements"
    xsi:noNamespaceSchemaLocation="../../../UIElementsSchema/UIElements.xsd"
>
    <Style src="${screenName}.uss" />
${uxmlInner}
</ui:UXML>
`;
  const uxmlPath = path.join(outDir, `${screenName}.uxml`);
  fs.writeFileSync(uxmlPath, uxml, "utf-8");

  const buttonMatches = [...html.matchAll(/id="([^"]+)"/g)].map(m => m[1]);
  const csCode = generateCSharpController(`${screenName}Controller`, buttonMatches);
  const csPath = path.join(outDir, `${screenName}Controller.cs`);
  fs.writeFileSync(csPath, csCode, "utf-8");

  console.log(`Transpiled successfully to ${outDir}`);
}

main();
