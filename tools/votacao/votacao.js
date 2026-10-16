/* Votação e comentários por pergunta, gravados no banco do artifact.
 * Um documento por pessoa em votos/<id>, com respostas[<id da pergunta>] = {opcao, comentario, em}.
 * A página traz <script type="application/json" id="votacao-dados"> com [{id, opcoes: [{id, nome, efeito}]}]
 * e um <div class="votacao" data-q="<id da pergunta>"> onde cada pergunta deve aparecer.
 * Capabilities do artifact: db (regras em tools/votacao/README.md) e user com scope "profile". */
(function () {
  const dadosEl = document.getElementById('votacao-dados');
  if (!dadosEl) return;
  const PERGUNTAS = JSON.parse(dadosEl.textContent);
  const porId = Object.fromEntries(PERGUNTAS.map(p => [p.id, p]));
  const V = {db: null, user: null, eu: null, pode: false, votos: {}, meu: {}, fila: Promise.resolve(), salvando: false, aviso: 'Carregando votos…'};

  const el = (tag, cls, txt) => { const n = document.createElement(tag); if (cls) n.className = cls; if (txt != null) n.textContent = txt; return n; };
  const nomeOpcao = (q, o) => (porId[q]?.opcoes || []).find(x => x.id === o)?.nome || o;
  const quando = iso => { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleDateString('pt-BR', {day: '2-digit', month: '2-digit'}) + ' ' + d.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'}); };

  function montar(caixa) {
    const q = caixa.dataset.q, p = porId[q];
    if (!p) return;
    const ul = el('ul', 'v-opcoes');
    for (const o of p.opcoes || []) {
      const b = el('button', 'v-op'); b.type = 'button'; b.dataset.q = q; b.dataset.o = o.id; b.setAttribute('aria-pressed', 'false');
      const quem = el('span', 'v-quem'); quem.append(el('span', 'v-n', '0 votos'), el('span', 'v-rostos'));
      b.append(el('b', null, o.nome), el('span', 'v-ef', o.efeito || ''), quem);
      const li = el('li'); li.append(b); ul.append(li);
    }
    const conversa = el('div', 'v-conversa');
    const ta = el('textarea', 'v-meu'); ta.id = 'vc-' + q; ta.rows = 2; ta.dataset.q = q;
    ta.placeholder = 'Explique seu voto, faça uma pergunta ou sugira outra opção';
    const rot = el('label', 'v-rotulo', 'Seu comentário'); rot.htmlFor = ta.id;
    const salvarBtn = el('button', 'v-salvar', 'Salvar comentário'); salvarBtn.type = 'button'; salvarBtn.dataset.q = q;
    const st = el('span', 'v-status'); st.setAttribute('role', 'status'); st.setAttribute('aria-live', 'polite');
    const acoes = el('div', 'v-acoes'); acoes.append(salvarBtn, st);
    conversa.append(el('h4', 'v-tit', 'Comentários'), el('ul', 'v-coms'), rot, ta, acoes);
    caixa.replaceChildren(el('h4', 'v-tit', 'Opções · clique para votar'), ul, conversa);
  }

  async function pintar() {
    const ids = Object.keys(V.votos);
    const ps = V.user && ids.length ? await V.user.profiles(ids) : {};
    const nome = id => id === V.eu ? 'Você' : (ps[id]?.name || 'Alguém');
    const rosto = id => { const i = el('img', 'v-rosto'); i.src = ps[id]?.avatarUrl || ''; i.alt = ''; i.title = nome(id); return i; };
    document.querySelectorAll('.v-op').forEach(b => {
      const {q, o} = b.dataset;
      const quem = ids.filter(id => V.votos[id]?.[q]?.opcao === o);
      b.setAttribute('aria-pressed', String(V.meu[q]?.opcao === o));
      b.classList.toggle('v-bloq', !V.pode);
      b.querySelector('.v-n').textContent = quem.length === 1 ? '1 voto' : quem.length + ' votos';
      b.querySelector('.v-rostos').replaceChildren(...quem.map(rosto));
    });
    document.querySelectorAll('.votacao').forEach(cx => {
      const q = cx.dataset.q, lista = cx.querySelector('.v-coms');
      if (!lista) return;
      const coms = ids.filter(id => (V.votos[id]?.[q]?.comentario || '').trim())
        .sort((a, b) => String(V.votos[a][q].em || '').localeCompare(String(V.votos[b][q].em || '')));
      lista.replaceChildren(...coms.map(id => {
        const r = V.votos[id][q], li = el('li'), cab = el('div', 'v-cab');
        cab.append(rosto(id), el('b', null, nome(id)), el('span', null, (r.opcao ? 'votou ' + nomeOpcao(q, r.opcao) + ' · ' : '') + quando(r.em)));
        li.append(cab, el('p', null, r.comentario));
        return li;
      }));
      if (!coms.length) lista.append(el('li', 'v-vazio', 'Nenhum comentário ainda.'));
      const ta = cx.querySelector('.v-meu');
      if (!ta.dataset.mexido && document.activeElement !== ta) ta.value = V.meu[q]?.comentario || '';
      ta.disabled = cx.querySelector('.v-salvar').disabled = !V.pode;
      const st = cx.querySelector('.v-status');
      if (!st.dataset.fixo) st.textContent = V.aviso;
    });
  }

  function salvar(q, msgOk) {
    const st = document.querySelector('.votacao[data-q="' + q + '"] .v-status');
    const r = V.meu[q];
    if (r) { r.em = new Date().toISOString(); if (!r.opcao && !(r.comentario || '').trim()) delete V.meu[q]; }
    const corpo = {respostas: JSON.parse(JSON.stringify(V.meu))};
    V.salvando = true;
    if (st) { st.dataset.fixo = '1'; st.textContent = 'Salvando…'; }
    V.fila = V.fila.then(async () => {
      try {
        await V.db.doc('votos/' + V.eu).set(corpo);
        if (st) st.textContent = msgOk;
      } catch (e) {
        if (e?.code === 'invalid_argument') { V.pode = false; V.aviso = 'Seu acesso não permite votar. Peça ao dono um convite de Editor por e-mail.'; }
        if (st) st.textContent = e?.code === 'quota_exceeded' ? 'O espaço de votos encheu. Avise o dono.'
          : e?.code === 'invalid_argument' ? V.aviso : 'Não foi possível salvar. Tente de novo.';
      } finally { V.salvando = false; pintar(); }
    });
  }

  document.addEventListener('click', e => {
    const b = e.target.closest('.v-op');
    if (b) {
      const {q, o} = b.dataset;
      if (!V.pode) {
        const st = document.querySelector('.votacao[data-q="' + q + '"] .v-status');
        if (st) { st.dataset.fixo = '1'; st.textContent = V.aviso; }
        return;
      }
      const r = V.meu[q] || (V.meu[q] = {});
      r.opcao = r.opcao === o ? '' : o;
      pintar();
      salvar(q, r.opcao ? 'Voto salvo.' : 'Voto retirado.');
      return;
    }
    const s = e.target.closest('.v-salvar');
    if (s && V.pode) {
      const q = s.dataset.q, ta = document.querySelector('.v-meu[data-q="' + q + '"]');
      const r = V.meu[q] || (V.meu[q] = {});
      r.comentario = ta.value.trim().slice(0, 4000);
      delete ta.dataset.mexido;
      salvar(q, r.comentario ? 'Comentário salvo.' : 'Comentário apagado.');
    }
  });
  document.addEventListener('input', e => { if (e.target.classList?.contains('v-meu')) e.target.dataset.mexido = '1'; });

  async function iniciar() {
    document.querySelectorAll('.votacao').forEach(montar);
    const c = window.claude;
    if (!c || typeof c.use !== 'function') { V.aviso = 'Abra esta página pelo link do claude.ai para votar e comentar.'; return pintar(); }
    [V.user, V.db] = await Promise.all([c.use('user'), c.use('db')]);
    if (!V.db) { V.aviso = 'Para votar e comentar, entre no claude.ai com o convite de Editor que o dono enviou por e-mail.'; return pintar(); }
    V.eu = V.user ? await V.user.id() : null;
    const pode = V.user ? await V.user.can('data.write') : null;
    V.pode = !!V.eu && pode !== false;
    V.aviso = V.pode ? '' : 'Você pode ver os votos, mas não votar. Para votar, peça ao dono um convite de Editor por e-mail.';
    V.db.collection('votos').onSnapshot(snap => {
      const novo = {};
      for (const d of snap.docs) { const r = d.data()?.respostas; if (r && typeof r === 'object') novo[d.id] = r; }
      V.votos = novo;
      if (V.eu && !V.salvando) V.meu = JSON.parse(JSON.stringify(novo[V.eu] || {}));
      pintar();
    }, () => { V.aviso = 'Não foi possível carregar os votos agora. Recarregue a página.'; pintar(); });
  }
  iniciar();
})();
