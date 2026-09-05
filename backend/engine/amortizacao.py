"""Motor de amortização que reproduz a lógica das abas de contrato do Excel.

Cobre os sistemas SAC, PRICE e BULLET com indexadores NULO (pré-fixado), CDI, TLP, IPCA,
para contratos com parcelas mensais e layout padrão. Contratos com parcelas anuais
(PARC. ANUAIS) ou com layout de conversão exigem tratamento específico e são sinalizados.

Uso:
    engine = AmortizacaoEngine(session)
    tabela = engine.calcular(nome_aba, data_base)
"""
from datetime import date, timedelta
from calendar import monthrange
from models.models import (
    ContratoParam, Parcela, Feriado, CdiDiario, Ipca, Tlp,
)


def _months_between(d1, d2):
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def _add_months(dt, months):
    m = dt.month - 1 + months
    y = dt.year + m // 12
    m = m % 12 + 1
    dia = min(dt.day, monthrange(y, m)[1])
    return date(y, m, dia)


def _eom(dt):
    return date(dt.year, dt.month, monthrange(dt.year, dt.month)[1])


class AmortizacaoEngine:
    def __init__(self, session):
        self.session = session
        self._feriados = None
        self._cdi = None
        self._ipca = None
        self._tlp = None

    def carregar_referencias(self):
        if self._feriados is None:
            self._feriados = {f.data for f in self.session.query(Feriado).all()}
        if self._cdi is None:
            self._cdi = {c.data: c.fator_decimal or 0.0
                         for c in self.session.query(CdiDiario).all()}
        if self._ipca is None:
            self._ipca = {}
            for i in self.session.query(Ipca).all():
                self._ipca[(i.mes, i.ano)] = (i.indice or 0.0, i.indice1 if i.indice1 is not None else (i.indice or 0.0))
        if self._tlp is None:
            self._tlp = {t.data: t.taxa_aa for t in self.session.query(Tlp).all()}

    def nearest_util_parc(self, d):
        """Data útil da parcela: primeiro dia útil >= d (avança para frente).
        Matches Excel's WORKDAY.INTL(A, IF(fer/FDS,1,0), 1, FERIADOS)."""
        while d.weekday() >= 5 or d in self._feriados:
            d += timedelta(days=1)
        return d

    def nearest_util_eom(self, d):
        """Data EOM: usa a própria data de fim de mês (sem ajuste de FDS/feriado),
        matching Excel's uso de WORKDAY.INTL(d,0) que mantém datas finais de mês."""
        return d

    def parcela_mensal(self, p):
        """Prestação Price constante: H3 / ((1-(1+H6)^-n)/H6)."""
        financiado = p.valor_financiado or 0.0
        n = int(p.qt_parc or 0)
        if n <= 0 or financiado <= 0:
            return 0.0
        if p.taxa_am is None:
            taxa_am = ((1 + (p.taxa_aa or 0.0)) ** (1 / 12)) - 1
        else:
            taxa_am = p.taxa_am
        if taxa_am == 0:
            return financiado / n
        return financiado / ((1 - (1 + taxa_am) ** -n) / taxa_am)

    def juros_sistema(self, sist, principal, dias, taxa_aa, taxa_am):
        if sist in ("SAC", "BULLET"):
            return principal * ((1 + taxa_aa) ** (dias / 365) - 1)
        elif sist == "PRICE":
            return (taxa_am / 30) * dias * principal
        return principal * ((1 + taxa_aa) ** (dias / 365) - 1)

    def calc_indexador(self, indexador, usa, prev_util, dutil, d, principal):
        if indexador == "CDI" and usa == "SIM":
            return self.calc_cdi_periodo(prev_util, dutil) * principal
        elif indexador == "IPCA" and usa == "SIM":
            return self.calc_ipca_periodo(d.month, d.year) / 100 * principal
        elif indexador == "TLP" and usa == "SIM":
            return self.calc_tlp_mes(d, principal)
        return 0.0

    def calc_cdi_periodo(self, d1, d2):
        """Soma dos fatores diários de CDI entre d1 e d2 (inclusive)."""
        total = 0.0
        for k, v in self._cdi.items():
            if d1 <= k <= d2:
                total += v
        return total

    def calc_ipca_periodo(self, mes, ano):
        indice1 = self._ipca.get((mes, ano))
        return indice1[1] if indice1 else 0.0

    def calc_tlp_mes(self, data, principal):
        """Correção monetária TLP do mês da data, sobre o principal.
        TLP é anual na tabela (mes,ano -> taxa_aa); converte para o fator mensal composto."""
        if not self._tlp:
            return 0.0
        chave = (data.month, data.year)
        taxa_aa = None
        for d, t in self._tlp.items():
            if d.month == chave[0] and d.year == chave[1]:
                taxa_aa = t
                break
        if taxa_aa is None:
            return 0.0
        return principal * ((1 + taxa_aa) ** (1 / 12) - 1)

    def calcular(self, nome_aba, data_base):
        p = self.session.query(ContratoParam).filter(ContratoParam.nome_aba == nome_aba).first()
        if p is None:
            raise ValueError(f"Contrato {nome_aba} não encontrado")
        if p.parc_anuais == "PARC. ANUAIS":
            return self._calcular_anual(p, data_base)
        return self._calcular_mensal(p, data_base)

    def _calcular_mensal(self, p, data_base):
        self.carregar_referencias()
        financiado = p.valor_financiado or 0.0
        sist = (p.sist_amort or "").upper()
        indexador = (p.indexador_nome or "").upper()
        usa = (p.usa_indice or "NÃO").upper()
        taxa_aa = p.taxa_aa or 0.0
        taxa_am = p.taxa_am if p.taxa_am is not None else (((1 + taxa_aa) ** (1 / 12)) - 1)
        n_parc = int(p.qt_parc or 0)
        carencia = int(p.carencia or 0)
        amort_const = financiado / n_parc if (sist == "SAC" and n_parc > 0) else 0.0
        price_parc = self.parcela_mensal(p)

        entrada = p.entrada_recurso or p.data_1o_pagam
        venc = p.vencimento_final or (p.entrada_recurso or date.today())
        parc_dia = (p.data_pgto_1o_parc or p.data_1o_pagam or entrada).day

        linhas = []
        d0 = self.nearest_util_parc(entrada)
        linhas.append({"data_contrato": entrada, "data_util": d0, "dias": 0,
                       "juros": 0.0, "indice_periodo": 0.0, "prestacao": 0.0,
                       "amortizacao": 0.0, "saldo": financiado, "cp": 0.0, "lp": 0.0,
                       "parcela_n": 0, "tipo": "LIB"})

        principal = financiado  # balanço de amortização (âncora do cálculo de juros)
        ancora_util = d0        # última data útil de parcela/entrada (base do 'dias')

        # datas REAIS de vencimento de cada parcela, fixadas pelo negócio no Excel.
        # detecção de carência implícita: linhas iniciais de juros puro (mutuario J/I)
        ps = (self.session.query(Parcela)
              .filter(Parcela.nome_aba == p.nome_aba)
              .order_by(Parcela.data_vencimento)
              .all())
        ps = [pr for pr in ps if pr.data_vencimento is not None]
        # carência implícita = linhas iniciais de juros puro, marcadas na importação
        # (M=0, G=J/I, prestação>0). Linhas de amortização real (M>0), mesmo marcadas
        # J/I no Excel, NÃO contam — senão um BULLET com amortização marcada J vira carência.
        carencia_impl = 0
        for pr in ps:
            if pr.is_carencia:
                carencia_impl += 1
            else:
                break
        # carência = apenas as linhas de juros puro presentes na tabela (is_carencia).
        # NÃO forçar via parâmetro H14: muitos contratos têm H14>0 mas a tabela já
        # amortiza desde a 1ª parcela (as parcelas reais são todas de amortização);
        # forçar H14 seguraria indevidamente a amortização dessas parcelas.
        carencia = carencia_impl

        # ordena por data de vencimento (robusto contra inversões do arquivo)
        parcelas_reais = sorted([pr.data_vencimento for pr in ps])
        conj_parc = {d for d in parcelas_reais}
        # a última parcela real (data útil de pagamento) pode cair 1-2 dias após o
        # vencimento_final contratual (ex.: vence domingos/feriados) — amplia o loop
        venc_efetivo = max(venc, max(parcelas_reais, default=venc))

        # sequência: [EOM da entrada], depois por parcela [parc_real, EOM(parc_real)].
        # mantém no máx. 1 parcela por mês (robusto contra corrupções com 2 datas no mesmo mês)
        seq_datas = [_eom(entrada)]
        ultimo_parc_mes = None
        for pp in parcelas_reais:
            mes_pp = (pp.year, pp.month)
            if pp < seq_datas[0]:
                continue
            if mes_pp == ultimo_parc_mes:
                continue
            eom = _eom(pp)
            seq_datas.append(pp)
            ultimo_parc_mes = mes_pp
            if eom != pp:
                seq_datas.append(eom)
            if pp >= venc_efetivo:
                break

        parc_n = 0
        for d in seq_datas:
            if d > venc_efetivo:
                break
            e_parcela = d in conj_parc
            # parcela usa a data útil real (já fixada); EOM usa a data crua de fim de mês
            dutil = d if e_parcela else self.nearest_util_eom(d)
            if dutil == ancora_util:
                continue

            # dias e juros sempre medidos desde a última data de parcela (ou entrada)
            dias = (dutil - ancora_util).days
            ind = self.calc_indexador(indexador, usa, ancora_util, dutil, d, principal)
            juros = self.juros_sistema(sist, principal, dias, taxa_aa, taxa_am)

            if e_parcela:
                parc_n += 1
            em_carencia = carencia > 0 and parc_n <= carencia

            if sist == "SAC":
                if e_parcela and not em_carencia:
                    am = amort_const
                    prest = juros + ind + am
                elif e_parcela:
                    am, prest = 0.0, juros + ind
                else:
                    am, prest = 0.0, 0.0
            elif sist == "BULLET":
                if e_parcela and not em_carencia and parc_n == n_parc:
                    am = principal
                    prest = juros + ind + am
                elif e_parcela:
                    am, prest = 0.0, juros + ind
                else:
                    am, prest = 0.0, 0.0
            else:  # PRICE
                if e_parcela and not em_carencia:
                    prest = price_parc
                    am = max(0.0, price_parc - juros - ind)
                elif e_parcela:
                    am, prest = 0.0, juros + ind
                else:
                    am, prest = 0.0, 0.0

            if am > 0:
                principal = max(0.0, principal - am)
                ancora_util = dutil  # parcela vira nova âncora
            elif e_parcela:
                ancora_util = dutil  # parcela (mesmo sem amort) vira âncora

            saldo = principal + juros + ind if not e_parcela else principal
            linhas.append({
                "data_contrato": d, "data_util": dutil, "dias": dias,
                "juros": juros, "indice_periodo": ind, "prestacao": prest,
                "amortizacao": am, "saldo": saldo, "cp": 0.0, "lp": 0.0,
                "parcela_n": parc_n, "tipo": "PARC" if e_parcela else "EOM",
            })

        self._calcular_particao(linhas)

        resultado = None
        for linha in linhas:
            if linha["data_util"] <= data_base:
                resultado = linha
            else:
                break

        return {
            "contrato": p.nome_aba,
            "sist_amort": sist,
            "indexador": indexador,
            "valor_financiado": financiado,
            "taxa_aa": taxa_aa,
            "data_base": data_base,
            "linha": resultado,
            "tabela": linhas,
        }

    def _calcular_particao(self, linhas):
        """Preenche CP/LP: CP = saldo a vencer <= 12 meses, LP = resto."""
        for i in range(len(linhas)):
            linha = linhas[i]
            alvo = _add_months(linha["data_util"], 12)
            saldo_fut = saldo = linha["saldo"]
            for j in range(i + 1, len(linhas)):
                if linhas[j]["data_util"] >= alvo:
                    saldo_fut = linhas[j]["saldo"]
                    break
                saldo_fut = linhas[j]["saldo"]
            cp = max(0.0, saldo - saldo_fut)
            lp = saldo - cp
            linha["cp"] = cp if linha["data_util"] < alvo else 0.0
            linha["lp"] = lp if linha["data_util"] < alvo else saldo

    def _calcular_anual(self, p, data_base):
        # Parcelas anuais: tabela mensal, mas amortização/prestação só nas datas de parcela (H12 + k anos)
        self.carregar_referencias()
        financiado = p.valor_financiado or 0.0
        sist = (p.sist_amort or "").upper()
        indexador = (p.indexador_nome or "").upper()
        usa = (p.usa_indice or "NÃO").upper()
        taxa_aa = p.taxa_aa or 0.0
        n_parc = int(p.qt_parc or 0)
        amort_const = financiado / n_parc if n_parc > 0 else 0.0

        entrada = p.entrada_recurso or p.data_1o_pagam
        venc = p.vencimento_final or entrada
        data_parc1 = p.data_pgto_1o_parc or p.data_1o_pagam or entrada

        # datas de parcela: data_parc1 + 1,2,... n_parc-1 anos
        datas_parc = []
        for k in range(n_parc):
            dt = date(data_parc1.year + k, data_parc1.month, data_parc1.day)
            if dt > venc:
                dt = venc
            datas_parc.append(dt)

        linhas = []
        d0 = self.nearest_util_parc(entrada)
        linhas.append({"data_contrato": entrada, "data_util": d0, "juros": 0.0,
                       "indice_periodo": 0.0, "prestacao": 0.0, "amortizacao": 0.0,
                       "saldo": financiado, "cp": 0.0, "lp": 0.0, "parcela_n": 0,
                       "tipo": "LIB"})

        prev = linhas[-1]
        parc_idx = 0
        d = _eom(entrada)
        guarda = 0
        while d <= venc and guarda < 400:
            guarda += 1
            dutil = self.nearest_util_eom(d)
            dias = (dutil - prev["data_util"]).days
            juros = prev["saldo"] * ((1 + taxa_aa) ** (dias / 365) - 1)

            if indexador == "CDI" and usa == "SIM":
                ind = self.calc_cdi_periodo(prev["data_util"], dutil) * prev["saldo"]
            elif indexador == "IPCA" and usa == "SIM":
                ind = self.calc_ipca_periodo(d.month, d.year) / 100 * prev["saldo"]
            elif indexador == "TLP" and usa == "SIM":
                ind = self.calc_tlp_mes(d, prev["saldo"])
            else:
                ind = 0.0

            e_parcela = (parc_idx < len(datas_parc)) and d >= datas_parc[parc_idx] - timedelta(days=40)
            if e_parcela:
                am = amort_const * (n_parc - parc_idx) if sist == "BULLET" else amort_const
                # prestação = indexador + juros + amortização da parcela (juros acumulados do ano)
                prest = (ind + prev["saldo"] * ((1 + taxa_aa) ** (365 / 365) - 1)) if False else (ind + juros + am)
                parc_idx += 1
            else:
                am = 0.0
                prest = ind + juros

            saldo = prev["saldo"] + ind + juros - prest
            linhas.append({"data_contrato": d, "data_util": dutil, "dias": dias,
                           "juros": juros, "indice_periodo": ind, "prestacao": prest,
                           "amortizacao": am, "saldo": saldo, "cp": 0.0, "lp": 0.0,
                           "parcela_n": parc_idx,
                           "tipo": "PARC" if e_parcela else "EOM"})
            prev = linhas[-1]
            if d >= venc:
                break
            d = _add_months(_eom(d), 1)

        self._calcular_particao(linhas)

        resultado = None
        for linha in linhas:
            if linha["data_util"] <= data_base:
                resultado = linha
            else:
                break

        return {"contrato": p.nome_aba, "sist_amort": sist, "indexador": indexador,
                "valor_financiado": financiado, "taxa_aa": taxa_aa,
                "data_base": data_base, "linha": resultado, "tabela": linhas}
