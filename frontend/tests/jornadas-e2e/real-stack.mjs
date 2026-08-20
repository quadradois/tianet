import assert from "node:assert/strict";
import { execFileSync, spawn } from "node:child_process";
import { once } from "node:events";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import net from "node:net";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = fileURLToPath(new URL("../../../", import.meta.url));
const frontendRoot = resolve(repositoryRoot, "frontend");
const statePath = resolve(frontendRoot, "test-results/jornadas/state.json");
const seedPath = resolve(frontendRoot, "test-results/jornadas/seed.json");
const containerName = `emprestimo-imp301-${process.pid}`;
const sessionKey = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
const jwtSecret = "imp301-integrated-stack-only";

function run(command, args, options = {}) {
  return execFileSync(command, args, {
    cwd: repositoryRoot,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    ...options,
  }).trim();
}

function runNpm(args, options = {}) {
  return execFileSync(process.platform === "win32" ? "cmd" : "npm", process.platform === "win32" ? ["/d", "/s", "/c", ["npm", ...args].join(" ")] : args, {
    cwd: frontendRoot,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    ...options,
  }).trim();
}

function spawnNpm(args, options = {}) {
  return process.platform === "win32" ? spawn("cmd", ["/d", "/s", "/c", ["npm", ...args].join(" ")], {
    cwd: frontendRoot,
    stdio: ["ignore", "pipe", "pipe"],
    ...options,
  }) : spawn("npm", args, {
    cwd: frontendRoot,
    stdio: ["ignore", "pipe", "pipe"],
    ...options,
  });
}

function freePort() {
  return new Promise((resolvePort, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (typeof address === "string" || address === null) {
        server.close();
        reject(new Error("Could not allocate a local port"));
        return;
      }
      server.close((error) => (error ? reject(error) : resolvePort(address.port)));
    });
  });
}

async function waitUntil(probe, description, timeoutMs = 120_000) {
  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    try {
      return await probe();
    } catch (error) {
      lastError = error;
      await new Promise((resolveWait) => setTimeout(resolveWait, 300));
    }
  }
  throw new Error(`${description} did not become ready`, { cause: lastError });
}

async function stopProcessTree(child, label) {
  if (!child || child.exitCode !== null) return;
  if (process.platform === "win32") {
    run("taskkill", ["/pid", String(child.pid), "/t", "/f"]);
  } else {
    child.kill("SIGTERM");
  }
  await Promise.race([
    once(child, "exit"),
    new Promise((_, reject) => setTimeout(() => reject(new Error(`${label} did not stop`)), 10_000)),
  ]).catch(async () => {
    child.kill("SIGKILL");
    await once(child, "exit");
  });
}

async function globalSetup() {
  mkdirSync(dirname(statePath), { recursive: true });
  const postgresPort = await freePort();
  const apiPort = await freePort();
  const frontendPort = await freePort();
  const databaseUrl = `postgresql+psycopg://emprestimo:emprestimo@127.0.0.1:${postgresPort}/emprestimo`;
  const apiUrl = `http://127.0.0.1:${apiPort}`;
  const frontendUrl = `http://127.0.0.1:${frontendPort}`;
  let apiProcess;
  let nextProcess;
  let apiOutput = "";
  let nextOutput = "";
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
    }, "PostgreSQL 16");

    run("uv", [
      "run",
      "python",
      "frontend/tests/jornadas-e2e/seed_integrated.py",
      "--database-url",
      databaseUrl,
      "--output",
      seedPath,
    ], {
      env: { ...process.env, APP_ENV: "test", DATABASE_URL: databaseUrl, JWT_SECRET_KEY: jwtSecret },
    });
    const seed = JSON.parse(readFileSync(seedPath, "utf-8"));

    apiProcess = spawn("uv", [
      "run",
      "uvicorn",
      "emprestimo.presentation.api.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      String(apiPort),
    ], {
      cwd: repositoryRoot,
      env: { ...process.env, APP_ENV: "test", DATABASE_URL: databaseUrl, JWT_SECRET_KEY: jwtSecret },
      stdio: ["ignore", "pipe", "pipe"],
    });
    apiProcess.stdout.on("data", (chunk) => { apiOutput += chunk.toString(); });
    apiProcess.stderr.on("data", (chunk) => { apiOutput += chunk.toString(); });

    await waitUntil(async () => {
      if (apiProcess.exitCode !== null) throw new Error(`FastAPI exited early: ${apiOutput}`);
      const response = await fetch(`${apiUrl}/health`);
      assert.equal(response.status, 200);
      const health = await response.json();
      assert.equal(health.status, "healthy");
      assert.equal(health.service, "api");
      assert.equal(health.checks.database, "healthy");
      return true;
    }, "FastAPI /health");

    const frontendEnv = {
      ...process.env,
      FRONTEND_BACKEND_URL: apiUrl,
      FRONTEND_ORIGIN: frontendUrl,
      FRONTEND_LOGIN_TENANT_IDENTIFICADOR: seed.credentials.institution,
      FRONTEND_SESSION_KEY: sessionKey,
      FRONTEND_SESSION_KEY_ID: "jornadas-current",
    };
    runNpm(["run", "build"], { env: frontendEnv, timeout: 180_000 });
    nextProcess = spawnNpm(["run", "start", "--", "--hostname", "127.0.0.1", "--port", String(frontendPort)], { env: frontendEnv });
    nextProcess.stdout.on("data", (chunk) => { nextOutput += chunk.toString(); });
    nextProcess.stderr.on("data", (chunk) => { nextOutput += chunk.toString(); });

    await waitUntil(async () => {
      if (nextProcess.exitCode !== null) throw new Error(`Next exited early: ${nextOutput}`);
      const response = await fetch(`${frontendUrl}/login`);
      assert.equal(response.status, 200);
      return true;
    }, "Next.js /login");

    writeFileSync(statePath, JSON.stringify({
      apiUrl,
      apiPid: apiProcess.pid,
      containerName,
      frontendUrl,
      seedPath,
      markers: [
        "login, refresh e logout",
        "acesso negado por RBAC",
        "404 neutro cross-scope",
        "Devedor -> Proposta",
        "Proposta -> Contrato -> Emprestimo",
        "wizard -> emprestimo livre -> extrato -> pagamento",
        "pagamento repetido com a mesma chave",
        "consulta do Motor sem calculo local",
        "cobranca -> promessa -> agenda -> comunicacao",
        "automacao operacional",
        "5xx correlacionado",
      ],
    }, null, 2));

    return async () => {
      await stopProcessTree(nextProcess, "Next.js");
      await stopProcessTree(apiProcess, "FastAPI");
      if (containerStarted) {
        run("docker", ["rm", "--force", containerName]);
        assert.throws(() => run("docker", ["inspect", containerName]), undefined, "PostgreSQL container must be absent after cleanup");
      }
    };
  } catch (error) {
    await stopProcessTree(nextProcess, "Next.js");
    await stopProcessTree(apiProcess, "FastAPI");
    if (containerStarted) run("docker", ["rm", "--force", containerName]);
    throw error;
  }
}

export default globalSetup;
