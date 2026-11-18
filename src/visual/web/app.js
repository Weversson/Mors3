const codigo = document.getElementById("codigo");
const statusEl = document.getElementById("status");
const erroEl = document.getElementById("erro");
const tokensEl = document.getElementById("tokens");
const simbolosEl = document.getElementById("simbolos");
const astEl = document.getElementById("ast");
const timelineEl = document.getElementById("timeline");
const contagemTokens = document.getElementById("contagem-tokens");
const contagemSimbolos = document.getElementById("contagem-simbolos");
const contagemTimeline = document.getElementById("contagem-timeline");
const botaoReproduzir = document.getElementById("botao-reproduzir");
const botaoReiniciar = document.getElementById("botao-reiniciar");
const botaoMorse = document.getElementById("baixar-morse");
const botaoWav = document.getElementById("baixar-wav");
const volumeEl = document.getElementById("volume");
const eventoAtualEl = document.getElementById("evento-atual");

const campos = {
  tom: document.getElementById("tom"),
  velocidade: document.getElementById("velocidade"),
  emissoes: document.getElementById("emissoes"),
  eventos: document.getElementById("eventos"),
  duracao: document.getElementById("duracao"),
  texto: document.getElementById("texto"),
};

const EXEMPLOS = {
  ola: `// Uma mensagem curta para teste.
mensagem alerta = "SOS";
tom 600.0;
velocidade 20;
emitir (alerta + " AJUDA") * 2;`,
  emissoes: `// Configurações podem aparecer em ambas as ordens, entre as mensagens.
velocidade 18;
mensagem chamada = "SOS";
tom 750.5;
mensagem resposta = "A CAMINHO";
emitir chamada * 3;
emitir resposta + " AGUARDE";`,
  precedencia: `// A repetição se aplica primeiro a "B". Os parênteses mudam o agrupamento.
emitir "A" + "B" * 2;
emitir ("A" + "B") * 2;`,
  acentos: `emitir "Ação ção ÇÃO";`,
  erro: `emitir ausente;`,
};

const NOMES_ETAPA = {
  lexico: "léxico",
  sintatico: "sintático",
  semantico: "semântico",
  execucao: "execução",
  requisicao: "requisição",
  interno: "interno",
  rede: "conexão",
  audio: "áudio",
};

const NOMES_MOTIVO = {
  simbolo: "entre símbolos",
  caractere: "entre caracteres",
  palavra: "entre palavras",
  emissao: "entre emissões",
};

const LIMITE_BLOCOS = 800;

let temporizador = null;
let sequencia = 0;

let timelineAtual = null;
let blocosEventos = [];
let cursorEl = null;
let barraProgressoEl = null;

// Reprodução: um único oscilador cobre a timeline inteira. O ganho é
// automatizado para soar apenas durante os eventos de tom, o que evita criar
// milhares de nós para programas longos.
let reproducao = null;

function definirStatus(texto, estado) {
  statusEl.textContent = texto;
  statusEl.dataset.estado = estado;
}

function agendarAnalise(atraso = 250) {
  clearTimeout(temporizador);
  temporizador = setTimeout(analisar, atraso);
}

async function analisar() {
  const atual = ++sequencia;
  definirStatus("analisando…", "ocupado");
  try {
    const resposta = await fetch("/api/analisar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fonte: codigo.value }),
    });
    if (!resposta.ok) {
      throw new Error(`HTTP ${resposta.status}`);
    }
    const dados = await resposta.json();
    if (atual !== sequencia) {
      return;
    }
    renderizar(dados);
  } catch (erro) {
    if (atual !== sequencia) {
      return;
    }
    mostrarErro({ etapa: "rede", detalhe: String(erro.message || erro) });
    definirStatus("sem conexão", "erro");
  }
}

function renderizar(dados) {
  pararReproducao();

  if (dados.ok) {
    esconderErro();
    definirStatus(`ok · ${dados.timeline.quantidade_eventos} evento(s)`, "ok");
  } else {
    mostrarErro(dados);
    definirStatus(`erro ${NOMES_ETAPA[dados.etapa] || dados.etapa}`, "erro");
  }

  renderizarTokens(dados.tokens || []);
  renderizarSimbolos(dados.simbolos || []);
  renderizarAst(dados.ast || null);
  renderizarTimeline(dados.timeline || null);
  renderizarCartoes(dados);
  atualizarControlesReproducao();
}

function renderizarCartoes(dados) {
  const timeline = dados.timeline;
  campos.tom.textContent = dados.tom ?? "—";
  campos.velocidade.textContent = dados.velocidade ?? "—";
  campos.emissoes.textContent = timeline ? timeline.quantidade_emissoes : "—";
  campos.eventos.textContent = timeline ? timeline.quantidade_eventos : "—";
  campos.duracao.textContent = timeline
    ? formatarMs(timeline.duracao_total_ms)
    : "—";
  campos.texto.textContent = timeline
    ? (timeline.texto || "(vazio)")
    : "—";
}

function renderizarTokens(tokens) {
  tokensEl.replaceChildren();
  contagemTokens.textContent = tokens.length ? `(${tokens.length})` : "";
  if (tokens.length === 0) {
    vazio(tokensEl, "Nenhum token.");
    return;
  }
  const fragmento = document.createDocumentFragment();
  for (const token of tokens) {
    const item = document.createElement("span");
    item.className = `token t-${token.tipo.toLowerCase()}`;
    item.textContent = token.texto;
    item.title = `${token.tipo} · linha ${token.linha}, coluna ${token.coluna}`;
    fragmento.append(item);
  }
  tokensEl.append(fragmento);
}

function renderizarSimbolos(simbolos) {
  simbolosEl.replaceChildren();
  contagemSimbolos.textContent = simbolos.length ? `(${simbolos.length})` : "";
  if (simbolos.length === 0) {
    vazio(simbolosEl, "Nenhuma mensagem declarada.");
    return;
  }
  const lista = document.createElement("ul");
  for (const simbolo of simbolos) {
    const item = document.createElement("li");
    const nome = document.createElement("code");
    nome.textContent = simbolo.nome;
    const posicao = document.createElement("span");
    posicao.className = "pos";
    posicao.textContent = `linha ${simbolo.linha}, coluna ${simbolo.coluna}`;
    item.append(nome, posicao);
    lista.append(item);
  }
  simbolosEl.append(lista);
}

function renderizarAst(ast) {
  astEl.replaceChildren();
  if (!ast) {
    vazio(astEl, "Sem AST: a análise parou antes da sintaxe.");
    return;
  }
  astEl.append(renderizarNo(ast));
}

function renderizarNo(no) {
  if (Array.isArray(no)) {
    const lista = document.createElement("ol");
    lista.className = "lista-ast";
    for (const item of no) {
      const elemento = document.createElement("li");
      elemento.append(renderizarNo(item));
      lista.append(elemento);
    }
    return lista;
  }

  if (no === null || typeof no !== "object") {
    const valor = document.createElement("span");
    valor.className = "valor";
    valor.textContent = JSON.stringify(no);
    return valor;
  }

  const detalhes = document.createElement("details");
  detalhes.className = "no-ast";
  detalhes.open = true;

  const resumo = document.createElement("summary");
  const tipo = document.createElement("span");
  tipo.className = "tipo-no";
  tipo.textContent = no.tipo || "Objeto";
  resumo.append(tipo);
  if (no.linha != null) {
    const posicao = document.createElement("span");
    posicao.className = "pos";
    posicao.textContent = `L${no.linha}:C${no.coluna}`;
    resumo.append(posicao);
  }
  detalhes.append(resumo);

  const corpo = document.createElement("div");
  corpo.className = "corpo-ast";
  for (const [chave, valor] of Object.entries(no)) {
    if (chave === "tipo" || chave === "linha" || chave === "coluna") {
      continue;
    }
    const linha = document.createElement("div");
    linha.className = "campo-ast";
    const rotulo = document.createElement("span");
    rotulo.className = "chave";
    rotulo.textContent = chave;
    linha.append(rotulo, renderizarNo(valor));
    corpo.append(linha);
  }
  detalhes.append(corpo);
  return detalhes;
}

function renderizarTimeline(timeline) {
  timelineAtual = timeline;
  blocosEventos = [];
  cursorEl = null;
  barraProgressoEl = null;
  timelineEl.replaceChildren();
  contagemTimeline.textContent = timeline
    ? `(${timeline.quantidade_eventos})`
    : "";
  if (!timeline) {
    vazio(timelineEl, "Sem timeline: a análise parou antes da execução.");
    atualizarEventoAtual(-1);
    return;
  }

  const resumo = document.createElement("p");
  resumo.className = "resumo-timeline";
  resumo.textContent = [
    `${timeline.quantidade_eventos} eventos`,
    `duração ${formatarMs(timeline.duracao_total_ms)}`,
    `ponto de ${formatarMs(timeline.unidade_ms)}`,
  ].join(" · ");

  const texto = document.createElement("p");
  texto.className = "texto-expandido";
  texto.textContent = timeline.texto || "(texto vazio)";

  const progresso = document.createElement("div");
  progresso.className = "progresso";
  barraProgressoEl = document.createElement("div");
  barraProgressoEl.className = "barra-progresso";
  progresso.append(barraProgressoEl);

  const faixa = document.createElement("div");
  faixa.className = "faixa";
  const total = Number(timeline.duracao_total_ms);
  const visiveis = Math.min(timeline.eventos.length, LIMITE_BLOCOS);
  for (let indice = 0; indice < visiveis; indice += 1) {
    const evento = timeline.eventos[indice];
    const bloco = document.createElement("span");
    bloco.className =
      `evento ${evento.tipo}${evento.motivo ? ` m-${evento.motivo}` : ""}`;
    bloco.dataset.indice = String(indice);
    const fracao = total > 0 ? (Number(evento.duracao_ms) / total) * 100 : 0;
    bloco.style.flex = `0 0 ${fracao}%`;
    bloco.title = [
      evento.tipo,
      evento.simbolo || evento.motivo || "",
      `${evento.inicio_ms}–${evento.fim_ms} ms`,
    ].join(" · ");
    faixa.append(bloco);
    blocosEventos.push(bloco);
  }

  cursorEl = document.createElement("span");
  cursorEl.className = "cursor";
  cursorEl.setAttribute("aria-hidden", "true");
  faixa.append(cursorEl);

  timelineEl.append(resumo, texto, progresso, faixa);
  if (timeline.eventos.length > visiveis) {
    const nota = document.createElement("p");
    nota.className = "nota";
    nota.textContent =
      `Exibindo os primeiros ${visiveis} de ${timeline.eventos.length} eventos; ` +
      "o áudio reproduz a timeline completa.";
    timelineEl.append(nota);
  }

  atualizarCursor(0);
  atualizarEventoAtual(-1);
}

function formatarMs(valor) {
  const numero = Number(valor);
  if (!Number.isFinite(numero)) {
    return `${valor} ms`;
  }
  if (numero >= 1000) {
    return `${(numero / 1000).toFixed(2).replace(".", ",")} s`;
  }
  return `${numero.toFixed(numero < 10 ? 2 : 0).replace(".", ",")} ms`;
}

function mostrarErro(dados) {
  const etapa = NOMES_ETAPA[dados.etapa] || dados.etapa || "desconhecido";
  const partes = [`Erro ${etapa}`];
  if (dados.linha != null) {
    partes.push(`linha ${dados.linha}, coluna ${dados.coluna}`);
  }
  const cabecalho = document.createElement("strong");
  cabecalho.textContent = partes.join(" · ");
  const detalhe = document.createElement("p");
  detalhe.textContent = dados.detalhe || "sem detalhe";
  erroEl.replaceChildren(cabecalho, detalhe);
  erroEl.classList.remove("oculto");
}

function esconderErro() {
  erroEl.classList.add("oculto");
  erroEl.replaceChildren();
}

function vazio(elemento, texto) {
  const paragrafo = document.createElement("p");
  paragrafo.className = "vazio";
  paragrafo.textContent = texto;
  elemento.append(paragrafo);
}

function podeReproduzir() {
  return Boolean(timelineAtual && timelineAtual.eventos.length > 0);
}

function atualizarControlesReproducao() {
  const ativo = podeReproduzir();
  botaoReproduzir.disabled = !ativo;
  botaoReiniciar.disabled = !ativo;
  botaoMorse.disabled = !ativo;
  botaoWav.disabled = !ativo;
  if (!ativo) {
    botaoReproduzir.textContent = "Reproduzir";
  }
  botaoReproduzir.title = ativo
    ? "Reproduzir ou pausar a timeline"
    : "Nenhuma timeline para reproduzir";
}

function definirBotaoReproduzir(texto) {
  botaoReproduzir.textContent = texto;
}

function atualizarCursor(milissegundos) {
  const duracao = timelineAtual
    ? Number(timelineAtual.duracao_total_ms)
    : 0;
  const fracao = duracao > 0
    ? Math.min(1, Math.max(0, milissegundos / duracao))
    : 0;
  const porcentagem = `${(fracao * 100).toFixed(4)}%`;
  if (cursorEl) {
    cursorEl.style.left = porcentagem;
  }
  if (barraProgressoEl) {
    barraProgressoEl.style.width = porcentagem;
  }
}

function destacarBloco(indice) {
  for (const bloco of blocosEventos) {
    bloco.classList.toggle("ativo", Number(bloco.dataset.indice) === indice);
  }
}

function atualizarEventoAtual(indice) {
  if (!timelineAtual || indice < 0 || indice >= timelineAtual.eventos.length) {
    eventoAtualEl.textContent = podeReproduzir()
      ? "Pronto para reproduzir."
      : "Nenhuma timeline disponível.";
    return;
  }
  const evento = timelineAtual.eventos[indice];
  const partes = [];
  if (evento.tipo === "tom") {
    partes.push(`tom ${evento.simbolo}`);
  } else {
    partes.push(`silêncio (${NOMES_MOTIVO[evento.motivo] || evento.motivo})`);
  }
  if (evento.caractere) {
    partes.push(`caractere ${evento.caractere}`);
  }
  if (evento.emissao != null) {
    partes.push(`emissão ${evento.emissao + 1}`);
  }
  partes.push(formatarMs(evento.duracao_ms));
  eventoAtualEl.textContent = partes.join(" · ");
}

function encontrarEvento(milissegundos) {
  if (!timelineAtual) {
    return -1;
  }
  const eventos = timelineAtual.eventos;
  let baixo = 0;
  let alto = eventos.length - 1;
  while (baixo <= alto) {
    const meio = (baixo + alto) >> 1;
    const evento = eventos[meio];
    if (milissegundos < Number(evento.inicio_ms)) {
      alto = meio - 1;
    } else if (milissegundos >= Number(evento.fim_ms)) {
      baixo = meio + 1;
    } else {
      return meio;
    }
  }
  return -1;
}

function criarContextoAudio() {
  const Construtor = window.AudioContext || window.webkitAudioContext;
  if (!Construtor) {
    throw new Error("este navegador não oferece Web Audio");
  }
  return new Construtor();
}

function encerrarAudio() {
  if (!reproducao) {
    return;
  }
  cancelAnimationFrame(reproducao.quadro);
  try {
    reproducao.oscilador.stop();
  } catch {
    // O oscilador pode já ter parado no fim da timeline.
  }
  try {
    reproducao.oscilador.disconnect();
  } catch {
    // Nó já desconectado.
  }
  reproducao.contexto.close().catch(() => {});
  reproducao = null;
}

function pararReproducao({ manterCursor = false } = {}) {
  encerrarAudio();
  if (!manterCursor) {
    destacarBloco(-1);
    atualizarCursor(0);
    atualizarEventoAtual(-1);
  }
  definirBotaoReproduzir("Reproduzir");
  atualizarControlesReproducao();
}

function agendarTimeline(contexto, inicio, volume) {
  const oscilador = contexto.createOscillator();
  const ganho = contexto.createGain();
  const mestre = contexto.createGain();
  const tom = Number(timelineAtual.tom) || 600;
  const duracao = Number(timelineAtual.duracao_total_ms);

  mestre.gain.value = volume;
  oscilador.type = "sine";
  oscilador.frequency.setValueAtTime(tom, inicio);
  ganho.gain.setValueAtTime(0, inicio);

  for (const evento of timelineAtual.eventos) {
    if (evento.tipo !== "tom") {
      continue;
    }
    const inicioEvento = inicio + Number(evento.inicio_ms) / 1000;
    const fimEvento = inicio + Number(evento.fim_ms) / 1000;
    const duracaoEvento = fimEvento - inicioEvento;
    if (duracaoEvento <= 0) {
      continue;
    }
    const rampa = Math.min(0.004, duracaoEvento / 4);
    ganho.gain.setValueAtTime(0, inicioEvento);
    ganho.gain.linearRampToValueAtTime(volume, inicioEvento + rampa);
    ganho.gain.setValueAtTime(
      volume, Math.max(inicioEvento + rampa, fimEvento - rampa));
    ganho.gain.linearRampToValueAtTime(0, fimEvento);
  }

  oscilador.connect(ganho).connect(mestre).connect(contexto.destination);
  oscilador.start(inicio);
  oscilador.stop(inicio + duracao / 1000 + 0.05);
  return { oscilador, mestre };
}

function iniciarReproducao() {
  if (!podeReproduzir()) {
    return;
  }

  if (reproducao && reproducao.estado === "pausado") {
    reproducao.estado = "tocando";
    reproducao.contexto.resume();
    definirBotaoReproduzir("Pausar");
    reproducao.quadro = requestAnimationFrame(animarReproducao);
    return;
  }

  if (reproducao) {
    encerrarAudio();
  }

  let contexto = null;
  try {
    contexto = criarContextoAudio();
    const inicio = contexto.currentTime + 0.08;
    const volume = (Number(volumeEl.value) / 100) * 0.5;
    const { oscilador, mestre } = agendarTimeline(contexto, inicio, volume);
    reproducao = {
      contexto,
      oscilador,
      mestre,
      inicio,
      duracaoMs: Number(timelineAtual.duracao_total_ms),
      estado: "tocando",
      indice: -1,
      quadro: null,
    };
    contexto.resume();
    esconderErro();
    definirBotaoReproduzir("Pausar");
    reproducao.quadro = requestAnimationFrame(animarReproducao);
  } catch (erro) {
    if (contexto) {
      contexto.close().catch(() => {});
    }
    encerrarAudio();
    mostrarErro({ etapa: "audio", detalhe: String(erro.message || erro) });
  }
}

function animarReproducao() {
  if (!reproducao || reproducao.estado !== "tocando") {
    return;
  }
  const decorrido = Math.max(
    0, (reproducao.contexto.currentTime - reproducao.inicio) * 1000);
  const indice = encontrarEvento(decorrido);

  atualizarCursor(decorrido);
  if (indice !== reproducao.indice) {
    reproducao.indice = indice;
    destacarBloco(indice);
    atualizarEventoAtual(indice);
  }

  if (decorrido >= reproducao.duracaoMs) {
    const duracao = reproducao.duracaoMs;
    encerrarAudio();
    destacarBloco(-1);
    atualizarCursor(duracao);
    atualizarEventoAtual(-1);
    definirBotaoReproduzir("Reproduzir");
    return;
  }

  reproducao.quadro = requestAnimationFrame(animarReproducao);
}

function alternarReproducao() {
  if (!reproducao) {
    iniciarReproducao();
    return;
  }
  if (reproducao.estado === "tocando") {
    reproducao.estado = "pausado";
    reproducao.contexto.suspend();
    cancelAnimationFrame(reproducao.quadro);
    definirBotaoReproduzir("Continuar");
    return;
  }
  if (reproducao.estado === "pausado") {
    iniciarReproducao();
  }
}

function reiniciarReproducao() {
  if (!podeReproduzir()) {
    return;
  }
  pararReproducao({ manterCursor: true });
  iniciarReproducao();
}

async function baixar(formato) {
  if (!podeReproduzir()) {
    return;
  }
  botaoMorse.disabled = true;
  botaoWav.disabled = true;
  definirStatus(`gerando ${formato}…`, "ocupado");
  try {
    const resposta = await fetch("/api/exportar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fonte: codigo.value, formato }),
    });
    const tipo = resposta.headers.get("Content-Type") || "";
    if (tipo.includes("application/json")) {
      const dados = await resposta.json();
      mostrarErro(dados);
      definirStatus(
        `erro ${NOMES_ETAPA[dados.etapa] || dados.etapa}`, "erro");
      return;
    }
    if (!resposta.ok) {
      throw new Error(`HTTP ${resposta.status}`);
    }
    const blob = await resposta.blob();
    const url = URL.createObjectURL(blob);
    const ancora = document.createElement("a");
    ancora.href = url;
    ancora.download = `morselang.${formato}`;
    document.body.append(ancora);
    ancora.click();
    ancora.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    definirStatus(`${formato} pronto para download`, "ok");
  } catch (erro) {
    mostrarErro({ etapa: "rede", detalhe: String(erro.message || erro) });
    definirStatus("sem conexão", "erro");
  } finally {
    atualizarControlesReproducao();
  }
}

codigo.addEventListener("input", () => agendarAnalise());
codigo.addEventListener("keydown", (evento) => {
  if ((evento.ctrlKey || evento.metaKey) && evento.key === "Enter") {
    evento.preventDefault();
    clearTimeout(temporizador);
    analisar();
  }
});

for (const botao of document.querySelectorAll("[data-exemplo]")) {
  botao.addEventListener("click", () => {
    const exemplo = EXEMPLOS[botao.dataset.exemplo];
    if (exemplo === undefined) {
      return;
    }
    codigo.value = exemplo;
    clearTimeout(temporizador);
    analisar();
  });
}

botaoReproduzir.addEventListener("click", alternarReproducao);
botaoReiniciar.addEventListener("click", reiniciarReproducao);
botaoMorse.addEventListener("click", () => baixar("morse"));
botaoWav.addEventListener("click", () => baixar("wav"));

volumeEl.addEventListener("input", () => {
  if (reproducao) {
    reproducao.mestre.gain.value = (Number(volumeEl.value) / 100) * 0.5;
  }
});

definirStatus("pronto", "ok");
atualizarControlesReproducao();
analisar();
