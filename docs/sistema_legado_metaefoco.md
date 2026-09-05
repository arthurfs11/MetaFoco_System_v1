# Sistema legado "Meta e Foco" — engenharia reversa

Documento gerado a partir da análise do arquivo `Meta e Foco.rar` (sistema de produção
antigo da JAFs, em descontinuidade). Objetivo: servir de referência/validação para o
MetaFoco v1 (FastAPI + PostgreSQL).

> **Aviso:** credenciais/fips de acesso dos bancos legados NÃO são reproduzidas aqui.
> Elas vivem nos arquivos `.ini` do pacote (`metaefoco_sistema.ini`, `jafs_officecommerce.ini`)
> e no `criarbanco.bat`, que permanecem apenas na máquina de origem.

---

## 1. Visão geral do pacote

O `.rar` (≈118 MB) contém a instalação/produção de **dois sistemas distintos** que
compartilham a stack Delphi da JAFs, além de utilitários e builds de release:

| Item | Papel |
|---|---|
| `Meta_e_Foco.exe` (+ dezenas de versões datadas) | **Sistema de controle de endividamento** (o que interessa p/ o projeto) |
| `OfficeCommerce.exe` | **ERP comercial/fiscal** (vendas, NF, estoque) |
| `P_CadContratos.exe` | Utilitário de cadastro de contratos |
| `P_AtualizaContratos.exe` | Utilitário de atualização/manutenção de contratos |
| `old/P_RelResumoEndividamento.exe` | Gerador do Resumo de Endividamento |
| `relatorios/` (`*.rpt`) | Relatórios Crystal Reports |
| `Relatorios/*.rav` (referenciado) | Relatórios ReportBuilder |
| `base_inicio.backup` | Dump PostgreSQL do banco `office` (ERP) |
| `criarbanco.bat` / `instalapdf.bat` | Criação do banco + registro das DLLs de PDF |
| DLLs | `crpe32.dll` (Crystal), `pdfkit.dll`/`PDFSplitMerge.dll` (PDF), `libmysql.dll` (MySQL), `libxml2/libxslt/libxmlsec` (XML Signature) |

## 2. Stack tecnológica

- **Apps:** Delphi (Borland/CodeGear) — desktop Windows, clientes leves que falam direto
  com o banco via **Zeos** (`TZConnection ZC_Metaefoco`).
- **Bancos:**
  - `metaefoco` — banco do sistema de endividamento. Originalmente **MySQL** (`PORTA=3306`,
    libmysql.dll no pacote); os utilitários de contrato foram compilados contra o driver
    **PostgreSQL** (`ZPlainPostgreSqlDriver`) → em pelo menos uma fase o `metaefoco`
    rodou em PostgreSQL.
  - `office` — ERP OfficeCommerce, **PostgreSQL 9.2** (dump `base_inicio.backup`,
    restaurável via `criarbanco.bat`).
- **Relatórios:** Crystal Reports (`.rpt`) + ReportBuilder (`.rav`); geração de PDF
  (pdfkit) para envio automático.

## 3. Banco `metaefoco` — schema reconstruído

Schema reconstruído a partir dos símbolos/queries embutidos nos binários (nomes reais
das colunas, inclusive prefixos de tabela).

### Tabela `contrato` (prefixo `ctt_`) — parâmetros do financiamento

- **Identificação:** `ctt_id`, `ctt_numero`, `ctt_prestamista`, `ctt_observacao`, `ctt_ativo`, `ctt_manual`
- **Valores/prazo:** `ctt_valorfinanciado`, `ctt_entradarecurso`, `ctt_vencimentofinal`,
  `ctt_qtdeparcelas`, `ctt_periodicidadeparcela`, `ctt_diavencimento`, `ctt_tipovencimento`, `ctt_vencvariavel`
- **Juros/taxas:** `ctt_taxa`, `ctt_taxaano`, `ctt_tipojurosdiario`, `ctt_fixo`, `ctt_flat`,
  `ctt_cdiperc`, `ctt_indexpercaa`, `ctt_indexpercam`, `ctt_tipocdi`
- **Indexadores (flags de correção):** `ctt_calculacdi`, `ctt_calculaipca`, `ctt_calculaselic`,
  `ctt_calculatjlp`, `ctt_calculatr`
- **Amortização:** `ctt_parcelafixa` (PRICE), campo de amortização calculado por parcela em
  `contrato_parcela.ctp_amortizacao` (SAC/BULLET via tabela própria / percentual)
- **Carência:** `ctt_carencia`, `ctt_carenciaembutida`, `ctt_carenciaperiodicidade`,
  `ctt_dataprimeiracarencia`, `ctt_diluircarencia`, `ctt_valorcarencia`, `ctt_jurosdurantecarencia`, `ctt_prazocarencia`
- **IOF/tarifas:** `ctt_iofadicional`, `ctt_iofdirario`, `ctt_ioffinanciado`, `ctt_iofvalor`,
  `ctt_tarifavalor`, `ctt_outrastarifas`
- **Garantias:** `ctt_garantias`, `ctt_percgarantia`, `ctt_percgarantia2`, `ctt_valorgarantia1`,
  `ctt_valorgarantia2`, `ctt_descgarantia1`, `ctt_descgarantia2`
- **CET:** `ctt_cettotal`; **relatório:** `ctt_exiberelbanco`
- Chaves: `ctt_bco_id` (banco), `ctt_emp_id` (empresa), `ctt_mod_id` (modalidade)

### Tabela `contrato_parcela` (prefixo `ctp_`) — cronograma de pagamento

`ctp_id`, `ctt_id`, `ctp_parcela`, `ctp_vencimento`, `ctp_valor` (prestação),
`ctp_juros`, `ctp_amortizacao`, `ctp_saldodevedor`, `ctp_iof`, `ctp_qtdedias`,
`ctp_cdi`, `ctp_ipca`, `ctp_selic`, `ctp_tjlp`, `ctp_tr` (correção por período),
`ctp_demonstrativo` (0=real/1=?) , `ctp_datalancamento`, `ctp_datapagto`, `ctp_valorpago`

### Tabela `contrato_juros` (prefixo `ctj_`) — série de juros por vencimento

`ctj_id`, `ctj_vencimento`, `ctj_juros`, `ctj_amort`, `ctj_saldodevedor`

### Tabelas de apoio

- `banco` (`bco_id`, `bco_nome`, `bco_apelido`, `bco_codigo`, `bco_ativo`, endereço/fone)
- `empresa` (`emp_id`, `emp_nome`, `emp_fantasia`, `emp_cnpj`, `emp_inscest`, `emp_ativo`, contato) + `empresa_documentos`
- `modalidade`/`mod` (`mod_id`, `mod_descricao`, `mod_sigla`, `mod_ativo`)
- `grupo_empresa` (`gre_id`, `gre_titulo`, `gre_descricao`, `gre_ativo`)
- `grupo_relatorio` (`grl_id`, `grl_nivel` — hierárquico com `.`, `grl_descricao`, `grl_silga`, `grl_ativo`)
- `relatorio` (`rel_id`, `rel_descricao`, `rel_nomearquivo`, `rel_nomeoriginal`, `rel_ativo`, ligado a `grl_id`)
- Referências da empresa: `referencia_bancaria`, `fornecedor`, `concorrente`, `princ_cliente`, `socio`
- `faturamento` (`fat_id`, `fat_data`, `fat_valor`, `emp_id`) — série histórica de faturamento (usada p/ evolução)

### Indexadores (séries)

- `cdi` (`cdi_id`, `cdi_data`, `cdi_inicial`, `cdi_atual`/`cdi_fatorindice`, `cdi_taxa`, `cdi_taxaano`)
  — consulta padrão: `cdi_data in (select max(cdi_data) from cdi where cdi_data <= :data)` → fator do período.
- `ipca` (`ipc_id`, `ipc_data`, `ipc_taxamensal`, `ipc_acumuladoano`, `ipc_ultimo12meses`)
- `selic` (`sel_data`, ...), `tjlp` (`tjl_id`, `tjl_data`, `tjl_taxaaoano`), `tr` (`tr_id`, `tr_data`, `tr_taxa`)
- Telas de importação por Excel: `Form_CadCDIImpExcel`, `Form_CadIPCAImpExcel`, `Form_CadSELICImpExcel`

### Contrato × regras de negócio

- `acessorios_parcela` (`acp_id`, `acp_parcela`, `acp_vencimento`, `acp_ativo`) — acessórios por parcela
- `percentual_pagamento` (`ptp_id`, `ptp_parcela`, `ptp_vencimento`) — % de pagamento por parcela
- `prorrogacao` (`prg_id`, `prg_tipo`, `prg_aumentarqtdeparcelas`, `prg_mantervalorparcela`,
  `prg_valorfixo`) + `prorrogacao_parcela` (`prp_vencimento`) — **renovação**: “Adicionar Qtde
  Parcelas”, “Apenas Parcelas”, manter valor da parcela ou valor fixo
- `contrato_calculotaxa`, `outras_taxas`, `aux_rel_endividamento` (tabela auxiliar de relatório),
  `garantias`

## 4. Stored functions (MySQL) — mesma lógica do nosso motor

Acessórias chamadas nas queries de relatório, sempre com base em data:

| Função | Uso observado | Equivalente no MetaFoco v1 |
|---|---|---|
| `busca_saldodevedor(ctt_id, data)` | Saldo na data base (soma/última parcela *vencida* ≤ data) | `linha` snapshot / saldo do motor |
| `busca_curtoprazo(ctt_id, data, dataLongo)` | Curto prazo = saldo a vencer até `dataLongo` | `_calcular_particao` (CP) |
| `busca_amortizacao(ctt_id, data)` | Amortização na data base | `am` das linhas PARC |
| `busca_juros(ctt_id, data)` | Juros na data base | `juros` |
| `busca_jurosapropriar(ctt_id, data)` | Juros a apropriar | encargos a incorrer (detalhe) |
| `busca_valorparcela(ctt_id, data)` | Prestação na data base | `prestacao` |
| `busca_cdi_data(data)` | Correção CDI até a data | `calc_cdi_periodo` |
| `busca_inicio_contrato(ctt_id)` | 1º vencimento/início | `entrada` |

### CP/LP (confirmado nos datasets)

```
Curto_Prazo = ctp_saldodevedor  − busca_saldodevedor(ctt_id, :dataBaseLongo)
Longo_Prazo = busca_saldodevedor(ctt_id, :dataBase) − busca_curtoprazo(ctt_id, :dataBase, :dataBaseLongo)
CURTO       = busca_curtoprazo(ctt_id, :dataBase, :dataBaseLongo)   -- saldo a vencer em até 12m
```

Idêntico à regra do Excel que implementamos: **CP = saldo a vencer ≤ 12m; LP = saldo − CP**.

### Snapshot do saldo (confirmado)

```
max(ctp_vencimento)  para parcelas com  ctp_vencimento BETWEEN (dataBase − 28/30 dias) AND dataBase
```

→ última parcela “viewport” na data base (demonstrativo 0), equivalente ao nosso `linha`.

## 5. Módulos (forms Delphi)

Cadastros: `TForm_CadBancos`, `TForm_CadCDI(+ImpExcel)`, `TForm_CadIPCA(+ImpExcel)`,
`TForm_CadSELICImpExcel`, `TForm_CadTJLP`, `TForm_CadTR`, `TForm_CadOutrasTaxas`,
`TForm_CadModalidade`, `TForm_CadEmpresa(+AddEdit)`, `TForm_CadGrupoEmpresarial`,
`TForm_CadGrupoRelatorio`, `TForm_CadUsuario`/`TForm_CadUsuarioExterno` (com “Gera Senha”),
`TForm_CadFaturamento`.

Contratos: `TForm_CadContratos(+AddEdit)`, `TForm_CadContratosManual`, `TForm_CadContratosParcelas`,
`TForm_CadContratosAcessorios`, `TForm_CadContratosPercentPagt`, `TForm_CadContratosCalculaTaxa`,
`TForm_CadContratosProrrogacao`, `TForm_CadContratosSaldoDevedor`,
`TForm_CadContratoMemoriaCalculo` (memória de cálculo), `TForm_CadContratosAddEdit8`.

Visão/Dashboard: `TForm_Endividamento`, `TForm_EndividamentoAlterar`, `TForm_Menu`, `TForm_Login`.

Relatórios: `TForm_RelEvolucao`, `TForm_RelPMT`, `TForm_RelResumoEndividamento(+Rel)`,
`TForm_RelResumoEndContabil`, `TForm_RelatorioAcesso`, `TForm_EnvioRelatorio(+AcessoGrupo+AddEdit)`,
`TForm_UserRelatorios`, `TForm_UsuarioAcesso`.

## 6. Relatórios

- **Crystal (`*.rpt`):** `PMTs.rpt`, `PMTs_Banco.rpt`, `PMTs_Grupo.rpt`,
  `Evolucao_Empresa.rpt`, `Evolucao_Grupo.rpt` (com versões de backup).
- **ReportBuilder (`*.rav`)** no diretório de produção:
  `ResumoEndividamento_Geral.rav`, `ResumoEndividamento_Contratos.rav`, `Bancario.rav`,
  `Contabil.rav`, `Contabil_Obs.rav`, `Diretoria.rav`, e `Endividamento.rav`.
- O Resumo é **gerado e distribuído automaticamente por acesso de usuário**
  (`EnvioRelatorio` + `grupo_relatorio`) — mesma lógica de grupos de relatório.

## 7. Utilitários de contrato (P_*)

- `P_CadContratos.exe` — cadastro pontual de contratos.
- `P_AtualizaContratos.exe` — manutenção programada: recalcula parcelas e juros
  (`update contrato_parcela`, `update contrato_juros`, `update contrato set ctt_manual=1`)
  usando `busca_*`; regra: “**se efetuar o cálculo, todos os lançamentos são classificados
  como Manual**” (flag `ctt_manual`).
- `old/P_RelResumoEndividamento.exe` — versão antiga do relatório.

## 8. ERP OfficeCommerce (banco `office`)

Delphi + PostgreSQL 9.2. Tabelas principais: `produto`, `venda`/`venda_parcela`/`venda_produto`,
`nota_fiscal`/`nota_fiscal_itens`/`nota_fiscal_fatura`/`nota_fiscal_volume`, `cte`/`cte_cargas`
`cte_docs`/`cte_seguro`, `cupom`/`cupom_itens`, `movimento_estoque`/`entrada_produto`
`historico_mensal_estoque`, `ordem_producao`/`produto_producao`/`tipo_producao`,
`contas_pagar`/`contas_receber`/`grupo_financeiro(_sub)`, `compra`/`compra_item`, `fornecedor`,
`vendedor`/`vendedor_comissao`/`produto_comissao`, `conta_corrente`/`empresa_conta_bancaria`,
`distribuicao`/`distribuicao_produto`, `regiao(_cidade)`, `perfil`/`perfil_tela`/`telas`,
`config`/`config_nfse`, `tributos_aproximados`, `situacao_tributaria`, `natureza_operacao`,
`catalogo_email`, `municipio`, `usuario`, `banco`, `cliente`, `obs_adicionais`.
Não faz parte do escopo de endividamento.

## 9. Mapa para o MetaFoco v1 (validação potencial)

A lógica do sistema atual (motor de amortização, CP/LP, indexadores) é **equivalente** ao que
o legado fazia em stored functions. Consequências úteis:

1. **Validação cruzada:** se houver acesso ao banco `metaefoco`, comparar
   `busca_saldodevedor`/`busca_amortizacao`/`busca_valorparcela` por contrato × data com o
   resultado do endpoint `/api/amortizacao/{aba}?data_base=`.
2. **Importação:** a tabela `contrato` cobre exatamente os parâmetros da planilha
   (taxas aa/am, indexadores, IOF, carência, garantias, dia do vencimento, nº de parcelas)
   → possível povoar `contrato_params`/`parcelas` a partir do legado.
3. **Relatórios:** os datasets do legado (Resumo, PMTs, Evolução) são a especificação dos
   relatórios que hoje replicamos no dashboard/detalhe.
4. **Regra de negócio nova:** flag `ctt_manual` e os tipos de `prorrogacao` (renovação com
   novo calendário de parcelas) não existem no MetaFoco v1 — candidatos a feature futura.

## 10. Descrição de lógica apreendida (referência rápida)

- **Snapshot de saldo:** última parcela ≤ data base (janela de 28–30 dias antes).
- **CP/LP:** curto = saldo a vencer em ≤12 meses; longo = saldo total − curto.
- **Correção por índice:** sempre pela última série disponível ≤ data (`max(cdi_data) <= :data`);
  juros/CDI/IOF separados por parcela na tabela (`ctp_juros`, `ctp_cdi`, `ctp_iof`, ...).
- **Sistema de amortização:** SAC/PRICE (`ctt_parcelafixa`)/BULLET, com carência
  explícita ou embutida (`ctt_carenciaembutida`), período de carência podendo pagar juros
  (`ctt_jurosdurantecarencia`), com documento “Memória de cálculo”.