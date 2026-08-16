import assert from "node:assert/strict";
import { execFileSync, spawn } from "node:child_process";
import { once } from "node:events";
import { fileURLToPath } from "node:url";
import net from "node:net";

const repositoryRoot = fileURLToPath(new URL("../../../", import.meta.url));
const containerName = `emprestimo-imp285-${process.pid}`;

function run(command, args, options = {}) {
  return execFileSync(command, args, {
    cwd: repositoryRoot,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    ...options,
  }).trim();
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (typeof address === "string" || address === null) {
        server.close();
        reject(new Error("Could not allocate a local port"));
        return;
      }
      server.close((error) => (error ? reject(error) : resolve(address.port)));
    });
  });
}

async function waitUntil(probe, description, timeoutMs = 60_000) {
  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    try {
      return await probe();
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
  }
  throw new Error(`${description} did not become ready`, { cause: lastError });
}

async function stopProcessTree(child) {
  if (child.exitCode !== null) return;
  if (process.platform === "win32") {
    run("taskkill", ["/pid", String(child.pid), "/t", "/f"]);
  } else {
    child.kill("SIGTERM");
  }
  await Promise.race([
    once(child, "exit"),
    new Promise((_, reject) => setTimeout(() => reject(new Error("FastAPI did not stop")), 10_000)),
  ]).catch(async () => {
    child.kill("SIGKILL");
    await once(child, "exit");
  });
}

const postgresPort = await freePort();
const apiPort = await freePort();
let api;
let apiOutput = "";
let containerStarted = false;

try {
  run("docker", ["version", "--format", "{{.Server.Version}}"]);
  run("docker", [
    "run",
    "--rm",
    "--detach",
    "--name",
    containerName,
    "--env",
    "POSTGRES_USER=emprestimo",
    "--env",
    "POSTGRES_PASSWORD=emprestimo",
    "--env",
    "POSTGRES_DB=emprestimo",
    "--publish",
    `127.0.0.1:${postgresPort}:5432`,
    "postgres:16",
  ]);
  containerStarted = true;

  await waitUntil(() => {
    run("docker", ["exec", containerName, "pg_isready", "-U", "emprestimo", "-d", "emprestimo"]);
    return true;
  }, "PostgreSQL");

  api = spawn(
    "uv",
    [
      "run",
      "uvicorn",
      "emprestimo.presentation.api.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      String(apiPort),
    ],
    {
      cwd: repositoryRoot,
      env: {
        ...process.env,
        DATABASE_URL: `postgresql+psycopg://emprestimo:emprestimo@127.0.0.1:${postgresPort}/emprestimo`,
        JWT_SECRET_KEY: "imp285-local-smoke-only",
      },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  api.stdout.on("data", (chunk) => { apiOutput += chunk.toString(); });
  api.stderr.on("data", (chunk) => { apiOutput += chunk.toString(); });

  const health = await waitUntil(async () => {
    if (api.exitCode !== null) throw new Error(`FastAPI exited early: ${apiOutput}`);
    const response = await fetch(`http://127.0.0.1:${apiPort}/health`);
    assert.equal(response.status, 200);
    return response.json();
  }, "FastAPI /health");

  assert.equal(health.status, "healthy");
  assert.equal(health.service, "api");
  assert.equal(health.checks.database, "healthy");
  console.log("IMP-285 infrastructure: PostgreSQL 16 + FastAPI /health, ready and isolated.");
} finally {
  if (api) await stopProcessTree(api);
  if (containerStarted) {
    run("docker", ["rm", "--force", containerName]);
    assert.throws(
      () => run("docker", ["inspect", containerName]),
      undefined,
      "PostgreSQL container must be absent after cleanup",
    );
  }
}
