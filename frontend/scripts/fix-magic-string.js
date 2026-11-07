const fs = require("fs");
const path = require("path");

// npm тянет ESM-версию magic-string 1.x внутрь @tailwindcss/node,
// которую turbopack не может require(). Подменяем на CJS-совместимую 0.30.5.
const dst = path.join(__dirname, "..", "node_modules", "@tailwindcss", "node", "node_modules", "magic-string");
const src = path.join(__dirname, "..", "_vendor", "magic-string");

try {
  const pkgPath = path.join(dst, "package.json");
  if (fs.existsSync(pkgPath)) {
    const v = JSON.parse(fs.readFileSync(pkgPath, "utf8")).version;
    if (v === "0.30.5") {
      console.log("magic-string already 0.30.5, skip");
      process.exit(0);
    }
  }
  fs.rmSync(dst, { recursive: true, force: true });
  fs.cpSync(src, dst, { recursive: true });
  const v2 = JSON.parse(fs.readFileSync(path.join(dst, "package.json"), "utf8")).version;
  console.log("magic-string patched to", v2);
} catch (e) {
  console.log("magic-string patch skipped:", e.message);
}
