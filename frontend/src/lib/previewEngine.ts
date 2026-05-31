import type { GeneratedFiles } from "../store/previewStore"

import * as esbuild from "esbuild-wasm"

let initialized = false

function escapeJsonForHtml(value: string): string {
  return value
    .replace(/</g, "\\u003c")
    .replace(/>/g, "\\u003e")
    .replace(/&/g, "\\u0026")
    .replace(/\u2028/g, "\\u2028")
    .replace(/\u2029/g, "\\u2029")
}

function toComponentName(fileName: string): string {
  return fileName.split("/").pop()?.replace(/\.[jt]sx?$/, "") || "Page"
}

function stripImports(code: string): string {
  return code
    .replace(/import\s+\{[^}]*\}\s+from\s+["']react["'];?\s*/g, "")
    .replace(/import\s+React\s+from\s+["']react["'];?\s*/g, "")
    .replace(/import\s+\w+\s+from\s+["']\.\/pages\/[^"']+["'];?\s*/g, "")
    .replace(/import\s+[^;]+;?\s*/g, "")
}

function transformComponentModule(fileName: string, code: string): string {
  const componentName = toComponentName(fileName)
  const normalized = stripImports(code)
    .replace(/export\s+default\s+function\s+(\w+)/g, "function $1")
    .replace(/export\s+default\s+(\w+);?/g, "")

  return `
const ${componentName} = (() => {
${normalized}
  return ${componentName};
})();
`.trim()
}

function transformAppModule(appCode: string): string {
  return stripImports(appCode)
    .replace(/export\s+default\s+function\s+App/g, "function App")
    .replace(/export\s+default\s+App;?/g, "")
}

async function ensureEsbuild() {
  if (initialized) {
    return
  }

  await esbuild.initialize({
    wasmURL: "https://unpkg.com/esbuild-wasm@0.25.12/esbuild.wasm",
    worker: true,
  })
  initialized = true
}

function buildRuntime(appCode: string, pageModules: string) {
  return `
const {
  Fragment,
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useReducer,
  useRef,
  useState
} = React;
const gsap = window.gsap;
const ScrollTrigger = window.ScrollTrigger;
const THREE = window.THREE;
if (gsap && ScrollTrigger && gsap.registerPlugin) {
  gsap.registerPlugin(ScrollTrigger);
}
const motion = new Proxy({}, {
  get: (_, tag) => tag
});
const AnimatePresence = ({ children }) => <Fragment>{children}</Fragment>;
const useScroll = () => ({ scrollY: { get: () => 0 }, scrollYProgress: { get: () => 0 } });
const useTransform = (value) => value;
const useSpring = (value) => value;
const useMotionValue = (value) => ({ get: () => value, set: () => {} });
const useInView = () => true;
const Canvas = ({ children, className, style }) => (
  <div className={className} style={style}>{children}</div>
);
const useFrame = () => {};
const OrbitControls = () => null;
const PerspectiveCamera = () => null;
const Environment = () => null;
const Float = ({ children }) => <Fragment>{children}</Fragment>;
class Lenis {
  raf() {}
  on() {}
  off() {}
  destroy() {}
}

${pageModules}

${appCode}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
`.trim()
}

function buildPreviewDocument(compiledScript: string) {
  const runtimePayload = JSON.stringify(`${compiledScript}\n//# sourceURL=preview-runtime.js`)
  const escapedRuntimePayload = escapeJsonForHtml(runtimePayload)

  return `
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/0.160.0/three.min.js"></script>
    <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <style>
      html, body, #root {
        min-height: 100%;
        margin: 0;
      }

      body {
        background: #000814;
      }

      * {
        box-sizing: border-box;
      }

      .preview-error {
        min-height: 100vh;
        background: #140707;
        color: #ffe8e8;
        padding: 24px;
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        white-space: pre-wrap;
      }
    </style>
  </head>
  <body>
    <div id="root"></div>
    <script id="preview-runtime-data" type="application/json">${escapedRuntimePayload}</script>
    <script>
      document.addEventListener("click", function(event) {
        const target = event.target;
        if (!(target instanceof Element)) return;
        const link = target.closest("a");
        if (!link) return;

        const href = link.getAttribute("href") || "";
        if (!href) return;

        if (href.startsWith("#/")) {
          event.preventDefault();
          window.location.hash = href.slice(1);
          return;
        }

        if (href === "/" || href.startsWith("/")) {
          event.preventDefault();
          window.location.hash = href;
        }
      });

      window.addEventListener("error", function(event) {
        document.getElementById("root").innerHTML =
          '<pre class="preview-error">' + "Preview runtime error:\\n" + event.message + "\\n" + event.filename + ":" + event.lineno + ":" + event.colno + "</pre>";
      });

      window.addEventListener("unhandledrejection", function(event) {
        const reason = event.reason;
        document.getElementById("root").innerHTML =
          '<pre class="preview-error">' + "Preview promise rejection:\\n" + String(reason?.stack || reason?.message || reason) + "</pre>";
      });

      try {
        const runtimePayloadNode = document.getElementById("preview-runtime-data");
        const runtimeSource = runtimePayloadNode ? JSON.parse(runtimePayloadNode.textContent || "\"\"") : "";
        const runtimeBlob = new Blob([runtimeSource], { type: "text/javascript" });
        const runtimeUrl = URL.createObjectURL(runtimeBlob);
        const runtimeScript = document.createElement("script");
        runtimeScript.src = runtimeUrl;
        runtimeScript.onload = function() {
          URL.revokeObjectURL(runtimeUrl);
        };
        runtimeScript.onerror = function() {
          document.getElementById("root").innerHTML =
            '<pre class="preview-error">' + "Preview runtime load error" + "</pre>";
          URL.revokeObjectURL(runtimeUrl);
        };
        document.body.appendChild(runtimeScript);
      } catch (error) {
        document.getElementById("root").innerHTML =
          '<pre class="preview-error">' + "Preview build error:\\n" + String(error?.stack || error?.message || error) + "</pre>";
      }
    </script>
  </body>
</html>
`.trim()
}

export async function buildPreviewHtml(files: GeneratedFiles): Promise<string> {
  await ensureEsbuild()

  const appCode =
    files["src/App.jsx"] ||
    files["App.jsx"] ||
    "export default function App(){ return <div>No App.jsx generated</div> }"

  const pageFiles = Object.keys(files).filter(
    (name) => name.startsWith("src/pages/") && /\.(jsx|tsx)$/.test(name),
  )

  const pageModules = pageFiles
    .map((name) => transformComponentModule(name, files[name]))
    .join("\n\n")

  const runtimeSource = buildRuntime(transformAppModule(appCode), pageModules)

  const transformed = await esbuild.transform(runtimeSource, {
    loader: "jsx",
    jsx: "transform",
    format: "iife",
    target: "es2020",
    sourcemap: false,
  })

  return buildPreviewDocument(transformed.code)
}
