/* Glossário financeiro do MetaFoco — termos do sistema e do legado.
 * Abre um modal com busca por termo/definição. Botão no topbar (auth.js). */
(function () {
  'use strict';

  const GLOSSARIO = [
    // ----- Conceitos gerais -----
    {
      categoria: 'Conceitos gerais',
      termo: 'MetaFoco',
      definicao: 'Sistema web (sucessor do legado "Meta e Foco") de controle do endividamento do grupo: cadastro de contratos, motor de amortização, dashboard e relatórios.',
    },
    {
      categoria: 'Conceitos gerais',
      termo: 'Data base',
      definicao: 'Data de referência usada para calcular a posição (saldo, curto/longo prazo, juros). Todas as tabelas do motor são amostradas sobre a data base escolhida.',
    },
    {
      categoria: 'Conceitos gerais',
      termo: 'Instituição (banco)',
      definicao: 'Instituição financeira credora, emissora do financiamento. No Excel, cada contrato pertence a uma instituição/banco.',
    },
    {
      categoria: 'Conceitos gerais',
      termo: 'Empresa do grupo',
      definicao: 'Empresa do grupo empresarial que contratou o financiamento. A exposição pode ser consolidada por empresa ou por grupo.',
    },
    {
      categoria: 'Conceitos gerais',
      termo: 'Modalidade',
      definicao: 'Natureza/tipo do contrato (ex.: capital de giro, investimento, conta garantida), determinada pela instituição.',
    },
    {
      categoria: 'Conceitos gerais',
      termo: 'Valor financiado / contratado',
      definicao: 'Montante originalmente liberado (principal) no contrato. É a base para a amortização e o saldo inicial.',
    },
    {
      categoria: 'Conceitos gerais',
      termo: 'Saldo devedor',
      definicao: 'Montante em aberto numa data: principal menos amortizações, acrescido de juros e correção do período. Em parcela = principal; em fim de mês = principal + juros + índice.',
    },
    {
      categoria: 'Conceitos gerais',
      termo: 'Total a pagar',
      definicao: 'Previsão de desembolso restante (soma do que ainda vence: principal, juros e correção).',
    },
    {
      categoria: 'Conceitos gerais',
      termo: 'Prestamista',
      definicao: 'Responsável/avaliante pelo pagamento do contrato (avalista ou coobrigado).',
    },

    // ----- Juros e prazos -----
    {
      categoria: 'Juros e prazos',
      termo: 'Curto prazo (CP)',
      definicao: 'Parcela do saldo devedor com vencimento em até 12 meses à frente. Calculado como saldo hoje menos o saldo projetado para daqui a 12 meses.',
    },
    {
      categoria: 'Juros e prazos',
      termo: 'Longo prazo (LP)',
      definicao: 'Parcela do saldo devedor com vencimento além de 12 meses. CP + LP = saldo devedor total.',
    },
    {
      categoria: 'Juros e prazos',
      termo: 'Vencimento final',
      definicao: 'Data-limite de quitação do contrato (última parcela).',
    },
    {
      categoria: 'Juros e prazos',
      termo: 'Entrada do recurso',
      definicao: 'Data da liberação do capital ao mutuário; marco inicial da contagem de juros do motor.',
    },
    {
      categoria: 'Juros e prazos',
      termo: 'Carência',
      definicao: 'Período inicial em que se paga apenas juros/correção, sem amortizar o principal. Pode estar explícita no contrato ou embutida na tabela.',
    },
    {
      categoria: 'Juros e prazos',
      termo: 'Parcela / prestação',
      definicao: 'Pagamento periódico do contrato. Normalmente = juros + correção (índice) + amortização.',
    },
    {
      categoria: 'Juros e prazos',
      termo: 'Prorrogação (renovação)',
      definicao: 'Recalendário das parcelas de um contrato (ex.: adicionar quantidade de parcelas, manter valor da parcela ou definir valor fixo).',
    },
    {
      categoria: 'Juros e prazos',
      termo: 'Juros',
      definicao: 'Remuneração do capital. No motor: principal × ((1 + taxa a.a.)^(dias/365) − 1), medido entre datas de parcela/fim de mês.',
    },
    {
      categoria: 'Juros e prazos',
      termo: 'Taxa a.a. / a.m.',
      definicao: 'Taxa de juros anual (a.a.) ou mensal (a.m.) do contrato. Taxa mensal equivale a (1 + a.a.)^(1/12) − 1.',
    },
    {
      categoria: 'Juros e prazos',
      termo: 'dias/365 (contagem)',
      definicao: 'Convenção de juros compostos por período proporcional aos dias corridos (exponencial no ano), usada pelo motor.',
    },

    // ----- Amortização -----
    {
      categoria: 'Amortização',
      termo: 'Amortização',
      definicao: 'Devolução do principal, reduzindo o saldo devedor. Soma das amortizações ≈ valor financiado (critério de fidelidade do motor).',
    },
    {
      categoria: 'Amortização',
      termo: 'SAC',
      definicao: 'Sistema de Amortização Constante: amortização igual em todas as parcelas (valor financiado ÷ nº de parcelas); prestação decrescente.',
    },
    {
      categoria: 'Amortização',
      termo: 'PRICE',
      definicao: 'Prestação fixa e constante; amortização crescente ao longo do tempo (prestação = financiado ÷((1−(1+i)^-n)/i)).',
    },
    {
      categoria: 'Amortização',
      termo: 'BULLET',
      definicao: 'Amortização integral do principal na última parcela; durante o contrato paga-se apenas juros/correção.',
    },
    {
      categoria: 'Amortização',
      termo: 'Memória de cálculo',
      definicao: 'Demonstrativo completo dos parâmetros e do cálculo de cada contrato (no legado, tela específica de cálculo por parcela).',
    },

    // ----- Indexadores -----
    {
      categoria: 'Indexadores',
      termo: 'Índice / indexador',
      definicao: 'Fator de correção aplicado sobre o saldo devedor no período (por parcela/fim de mês). PRÉ/NULO = sem indexador.',
    },
    {
      categoria: 'Indexadores',
      termo: 'PRÉ / NULO',
      definicao: 'Contrato pré-fixado: não há correção por índice; apenas a taxa de juros contratual.',
    },
    {
      categoria: 'Indexadores',
      termo: 'CDI',
      definicao: 'Taxa interbancária brasileira. No sistema, série diária de fatores; correção = soma dos fatores do período × principal.',
    },
    {
      categoria: 'Indexadores',
      termo: 'IPCA',
      definicao: 'Inflação oficial (IBGE). No sistema, tabela mensal; correção = variação do mês / 100 × principal.',
    },
    {
      categoria: 'Indexadores',
      termo: 'TLP',
      definicao: 'Taxa de Longo Prazo (BNDES), mensalizada a partir da taxa anual da tabela de referência.',
    },
    {
      categoria: 'Indexadores',
      termo: 'SELIC',
      definicao: 'Taxa básica de juros da economia, usada como referência/benchmark no dashboard.',
    },
    {
      categoria: 'Indexadores',
      termo: 'TR / TJLP',
      definicao: 'Taxa Referencial (TR) e Taxa de Juros de Longo Prazo (TJLP) — indexadores históricos também presentes no sistema legado.',
    },

    // ----- Encargos e tributos -----
    {
      categoria: 'Encargos',
      termo: 'IOF',
      definicao: 'Imposto sobre Operações Financeiras. No legado, eram modeladas várias componentes (adicional, diário, financiado) por contrato.',
    },
    {
      categoria: 'Encargos',
      termo: 'CET',
      definicao: 'Custo Efetivo Total: taxa que embute juros, tarifas e IOF do contrato. No Excel, calculada por XIRR sobre o fluxo de caixa.',
    },
    {
      categoria: 'Encargos',
      termo: 'Tarifas / outras taxas',
      definicao: 'Encargos adicionais além dos juros (taxas de abertura de crédito, etc.), que elevam o custo efetivo.',
    },

    // ----- Garantias -----
    {
      categoria: 'Garantias',
      termo: 'Garantia',
      definicao: 'Valor/bem que assegura o contrato. No sistema, descrição das garantias, valor e percentual de cobertura sobre o financiado.',
    },
    {
      categoria: 'Garantias',
      termo: 'Percentual de garantia',
      definicao: 'Cobertura da garantia em relação ao valor financiado (ex.: 100% de cobertura por aval/penhor).',
    },

    // ----- Motor e fidelidade -----
    {
      categoria: 'Motor',
      termo: 'Motor de amortização',
      definicao: 'Componente do backend que reproduz a lógica da planilha de cada contrato (SAC/PRICE/BULLET × indexadores), recalculando juros, prestação, amortização, saldo e CP/LP para qualquer data base.',
    },
    {
      categoria: 'Motor',
      termo: 'Fidelidade (status)',
      definicao: 'Classificação de quanto o motor reproduz o contrato da planilha: OK, PARCIAL, FORA_PADRAO ou DADO_FALTANTE.',
    },
    {
      categoria: 'Motor',
      termo: 'OK',
      definicao: 'O motor reproduz o contrato fielmente (soma das amortizações fecha com o valor financiado).',
    },
    {
      categoria: 'Motor',
      termo: 'PARCIAL',
      definicao: 'Reprodução próxima do contrato, com pequenas diferenças (geralmente parcela final ausente na planilha).',
    },
    {
      categoria: 'Motor',
      termo: 'FORA_PADRAO',
      definicao: 'Estrutura que o motor ainda não cobre (cadência quinzenal, PRICE divergente, CDI custom), exigindo ajuste por contrato.',
    },
    {
      categoria: 'Motor',
      termo: 'DADO_FALTANTE',
      definicao: 'Contrato sem parcelas capturáveis ou sem valor financiado — não é possível calcular.',
    },

    // ----- Legado -----
    {
      categoria: 'Legado (sistema antigo)',
      termo: 'Sistema "Meta e Foco"',
      definicao: 'Aplicativo desktop Delphi/Windows da JAFs que controlava o endividamento sobre o banco próprio ("metaefoco"). Continha os mesmos conceitos: contratos, parcelas, indexadores CDI/IPCA/SELIC/TJLP/TR, IOF, carência e garantias, com stored functions equivalentes ao motor atual (busca_saldodevedor, busca_amortizacao, busca_valorparcela, busca_curtoprazo).',
    },
    {
      categoria: 'Legado (sistema antigo)',
      termo: 'Relatórios do legado',
      definicao: 'Relatórios gerados no sistema antigo e que inspiram o dashboard atual: Evolução (por empresa/grupo), PMTs (prestações por banco/grupo) e Resumo de Endividamento (geral, bancário, contábil, diretoria) — via Crystal Reports (.rpt) e ReportBuilder (.rav).',
    },
    {
      categoria: 'Legado (sistema antigo)',
      termo: 'Utilitários P_*',
      definicao: 'Programas separados do legado: P_CadContratos (cadastro), P_AtualizaContratos (manutenção que recalcula parcelas/juros e marca contratos como "manual") e P_RelResumoEndividamento.',
    },
  ];

  function abrirGlossario() {
    const existente = document.getElementById('glossario-modal');
    if (existente) { existente.remove(); return; }

    const overlay = document.createElement('div');
    overlay.id = 'glossario-modal';
    overlay.className = 'modal-overlay show';

    const grupos = {};
    GLOSSARIO.forEach(g => { (grupos[g.categoria] = grupos[g.categoria] || []).push(g); });
    const total = GLOSSARIO.length;

    overlay.innerHTML = `
      <div class="modal glossario-modal">
        <div class="modal-header">
          <div class="modal-title">Glossário financeiro</div>
          <button class="modal-close" data-glo-fechar>&times;</button>
        </div>
        <div class="modal-body">
          <div class="glossario-toolbar">
            <input class="glossario-search" type="text" placeholder="Buscar termo ou definição… (ex.: CP, CDI, SAC, carência)" data-glo-busca />
            <span class="muted glossario-count">${total} termos</span>
          </div>
          <div class="glossario-list" data-glo-lista></div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-ghost" data-glo-fechar>Fechar</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    const lista = overlay.querySelector('[data-glo-lista]');
    const busca = overlay.querySelector('[data-glo-busca]');

    function render(filtro) {
      const q = (filtro || '').trim().toLowerCase();
      let html = '';
      Object.keys(grupos).forEach(cat => {
        let itens = grupos[cat];
        let match = 0;
        if (q) itens = itens.filter(g => g.termo.toLowerCase().includes(q) || g.definicao.toLowerCase().includes(q));
        if (!itens.length) return;
        html += `<div class="glossario-cat">${cat} <span class="muted">(${itens.length})</span></div>`;
        itens.forEach(g => {
          html += `<div class="glossario-item">
            <div class="glossario-termo">${g.termo}</div>
            <div class="glossario-def">${g.definicao}</div>
          </div>`;
        });
      });
      lista.innerHTML = html || '<div class="empty-state">Nenhum termo encontrado.</div>';
    }

    busca.addEventListener('input', () => render(busca.value));
    overlay.querySelectorAll('[data-glo-fechar]').forEach(b => b.addEventListener('click', () => overlay.remove()));
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
    render('');
    busca.focus();
  }

  // Botão no topbar (renderTopbar em auth.js) via delegação
  document.addEventListener('click', (e) => {
    const alvo = e.target.closest('[data-glo-abrir]');
    if (alvo) {
      e.preventDefault();
      abrirGlossario();
    }
  });

  // Estilos do glossário (injetados uma única vez)
  const style = document.createElement('style');
  style.textContent = `
    .glossario-modal { max-width: 720px; width: 92vw; }
    .glossario-toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
    .glossario-search {
      flex: 1; background: var(--bg, #0b0e14); color: var(--text, #e6e9ed);
      border: 1px solid var(--border, #2a313c); border-radius: 7px;
      padding: 9px 12px; font-size: 13px; font-family: inherit;
    }
    .glossario-search:focus { outline: none; border-color: var(--blue, #5794f2); }
    .glossario-count { font-size: 11.5px; white-space: nowrap; }
    .glossario-list { display: flex; flex-direction: column; gap: 2px; max-height: 62vh; overflow: auto; padding-right: 4px; }
    .glossario-cat {
      margin: 12px 0 4px; padding-top: 10px; border-top: 1px solid var(--border-soft, #1f2730);
      font-size: 11px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
      color: var(--text-muted, #9aa4b2);
    }
    .glossario-cat:first-child { border-top: 0; margin-top: 0; padding-top: 0; }
    .glossario-item { padding: 8px 10px; border-radius: 6px; background: var(--panel-hi, #161a21); }
    .glossario-termo { font-weight: 700; font-size: 13px; color: var(--text, #e6e9ed); }
    .glossario-def { font-size: 12.5px; color: var(--text-dim, #a4abb5); margin-top: 2px; line-height: 1.5; }
  `;
  document.head.appendChild(style);
})();