import assert from "node:assert/strict";
import { execSync } from "node:child_process";

const npmVersion = execSync("npm --version", { encoding: "utf8" }).trim();

assert.equal(process.version, "v24.19.0", "Node.js deve corresponder ao pin governado");
assert.equal(npmVersion, "11.17.0", "npm deve corresponder ao pin governado");

console.log(`Toolchain governada: Node.js ${process.version}, npm ${npmVersion}.`);
