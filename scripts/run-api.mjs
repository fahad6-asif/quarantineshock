// Cross-platform launcher for the FastAPI backend (or pytest) using the project venv.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const backend = join(root, "backend");
const win = process.platform === "win32";
const py = join(backend, ".venv", win ? "Scripts" : "bin", win ? "python.exe" : "python");
if (!existsSync(py)) {
  console.error("Python venv not found. Run: python scripts/setup.py");
  process.exit(1);
}
// No auto-reload by default: on Windows uvicorn's reloader sends Ctrl+C to the whole console group,
// which also kills the Next.js dev server. Opt in with `npm run dev:api -- --reload`.
const reload = process.argv.includes("--reload") ? ["--reload", "--reload-dir", "app"] : [];
const args = process.argv.includes("--pytest")
  ? ["-m", "pytest", "-q"]
  : ["-m", "uvicorn", "app.main:app", "--port", "8000", ...reload];
const child = spawn(py, args, { cwd: backend, stdio: "inherit" });
child.on("exit", (code) => process.exit(code ?? 0));
for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => child.kill(sig));
