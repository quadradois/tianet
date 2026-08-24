// Exige um build de producao atual antes de subir o servidor das suites
// Playwright.
//
// Por que existe (PLAN-032 §9.5): ate 2026-08-23 cada config do Playwright
// rodava `npm run build && npm run start`. Treze configs, treze builds — e
// todos escrevendo no MESMO `.next/`. Alem do desperdicio, isso e uma corrida:
// o servidor de uma suite ainda encerrando enquanto a seguinte sobrescreve o
// build produz ERR_CONNECTION_REFUSED intermitente.
//
// Agora o build acontece UMA vez, antes das suites, e cada config so faz
// `start`. Este guard existe para que a economia nao vire um risco pior:
// rodar teste contra build velho passaria despercebido e daria falso verde.

import { existsSync, readdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const RAIZ = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const BUILD_ID = join(RAIZ, ".next", "BUILD_ID");

const abortar = (motivo) => {
  console.error(`\nrequire-build: ${motivo}`);
  console.error("require-build: rode `npm run build` no diretorio frontend/ e tente de novo.");
  console.error("require-build: o hook pre-push e o npm run gate:full ja fazem isso por voce.\n");
  process.exit(1);
};

if (!existsSync(BUILD_ID)) {
  abortar("nao existe build de producao em .next/.");
}

const buildEm = statSync(BUILD_ID).mtimeMs;

// Procura qualquer fonte mais nova que o build. Testar codigo que nao esta no
// bundle e pior que perder tempo reconstruindo: da verde em cima do que nao foi
// exercitado.
const maisNovoQueOBuild = (diretorio) => {
  for (const entrada of readdirSync(diretorio, { withFileTypes: true })) {
    if (entrada.name === "node_modules" || entrada.name.startsWith(".")) continue;
    const caminho = join(diretorio, entrada.name);
    if (entrada.isDirectory()) {
      const achado = maisNovoQueOBuild(caminho);
      if (achado) return achado;
      continue;
    }
    if (statSync(caminho).mtimeMs > buildEm) return caminho;
  }
  return null;
};

const desatualizado = maisNovoQueOBuild(join(RAIZ, "src"));
if (desatualizado) {
  abortar(`o build esta velho — ${desatualizado.slice(RAIZ.length + 1)} mudou depois dele.`);
}
