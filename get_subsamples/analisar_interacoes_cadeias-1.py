import os
import re
import sys
from itertools import combinations

import gemmi

try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    RICH_DISPONIVEL = True
except ImportError:
    RICH_DISPONIVEL = False

try:
    import questionary

    QUESTIONARY_DISPONIVEL = True
except ImportError:
    QUESTIONARY_DISPONIVEL = False


CONSOLE = Console() if RICH_DISPONIVEL else None


def terminal_interativo_disponivel():
    return sys.stdin.isatty() and sys.stdout.isatty()


def titulo(txt):
    if RICH_DISPONIVEL:
        CONSOLE.print(Panel.fit(txt, border_style="cyan"))
    else:
        print(f"\n{txt}")


def aviso_dependencias():
    faltando = []
    if not RICH_DISPONIVEL:
        faltando.append("rich")
    if not QUESTIONARY_DISPONIVEL:
        faltando.append("questionary")

    if not faltando:
        return

    msg = "Modo visual/interativo parcial."
    cmd = f"python3 -m pip install {' '.join(faltando)}"

    if RICH_DISPONIVEL:
        CONSOLE.print(Panel(f"{msg}\nInstale para liberar tudo: {' '.join(faltando)}\n\n{cmd}", border_style="yellow"))
    else:
        print(f"\n{msg} Instale: {' '.join(faltando)}")
        print(cmd)


def encontrar_fasta_correspondente(caminho_cif):
    base = os.path.splitext(os.path.basename(caminho_cif))[0].lower()
    pasta_cif = os.path.dirname(caminho_cif)
    pasta_fasta_irma = os.path.join(os.path.dirname(pasta_cif), "toy_dataset_fasta")

    candidatos = [
        os.path.join(pasta_cif, f"{base}.fasta"),
        os.path.join(pasta_cif, f"{base.upper()}.fasta"),
        os.path.join(pasta_fasta_irma, f"{base}.fasta"),
        os.path.join(pasta_fasta_irma, f"{base.upper()}.fasta"),
    ]

    for caminho in candidatos:
        if os.path.exists(caminho):
            return caminho
    return None


def extrair_tags_cadeia_do_fasta(caminho_fasta):
    tags_por_cadeia = {}
    if not caminho_fasta:
        return tags_por_cadeia

    with open(caminho_fasta, "r", encoding="utf-8", errors="ignore") as f:
        for linha in f:
            if not linha.startswith(">"):
                continue

            cab = linha[1:].strip()
            partes = cab.split("|")
            descricao = partes[2].strip() if len(partes) > 2 else cab

            cadeias = []
            if len(partes) > 1:
                campo_chain = partes[1].strip()
                m = re.search(r"Chains?\s+(.+)", campo_chain, flags=re.IGNORECASE)
                if m:
                    lista = m.group(1)
                    cadeias = [x.strip().strip(".") for x in lista.split(",") if x.strip()]

            if not cadeias:
                m2 = re.findall(r"Chain\s+([A-Za-z0-9])", cab, flags=re.IGNORECASE)
                cadeias = [c.upper() for c in m2]

            for c in cadeias:
                c = c.upper()
                tags_por_cadeia.setdefault(c, [])
                if descricao not in tags_por_cadeia[c]:
                    tags_por_cadeia[c].append(descricao)

    return tags_por_cadeia


def resumir_tag(tag_lista, limite=58):
    if not tag_lista:
        return "-"
    txt = " | ".join(tag_lista)
    if len(txt) <= limite:
        return txt
    return txt[: limite - 3] + "..."


def classificar_cadeia_por_tamanho(len_poly):
    # Faixas iniciais para triagem. A decisão final vem da interface, não só do tamanho.
    if 7 <= len_poly <= 25:
        return "peptideo_candidato"
    if 170 <= len_poly <= 380:
        return "mhc_pesada_candidata"
    if 85 <= len_poly <= 130:
        return "beta2m_candidata"
    return "outra"


def listar_cifs(pasta):
    return sorted([f for f in os.listdir(pasta) if f.lower().endswith(".cif")])


def escolher_arquivo(cifs):
    # if QUESTIONARY_DISPONIVEL and terminal_interativo_disponivel():
    #     escolha = questionary.select(
    #         "Escolha o arquivo CIF para analisar:",
    #         choices=cifs,
    #         use_shortcuts=True,
    #     ).ask()
    #     if escolha:
    #         return escolha

    print("\nArquivos CIF disponiveis:\n")
    for i, nome in enumerate(cifs, start=1):
        print(f"{i:>2}. {nome}")
    
    while True:
        escolha = input("\nDigite o nome do arquivo para analisar: ").strip()
        # if not escolha.isdigit():
        #     print("Entrada invalida. Digite apenas o nome da cif.")
        #     continue

        # idx = int(escolha)
        # if 1 <= idx <= len(cifs):
        #     return cifs[idx - 1]
        if f"{escolha}.cif" in cifs:
            return f"{escolha}.cif"
        print("Opcao fora da faixa. Tente novamente.")


def contar_contatos_direcionais(model, neighbor_search, cadeia_origem, cadeia_destino, cutoff):
    # Contagem direcional: percorre átomos da cadeia_origem e busca vizinhos na cadeia_destino.
    # Mantemos assim para facilitar inspeção e depuração por sentido (C1->C2 vs C2->C1).
    contatos_atomicos = 0
    pares_residuos = set()
    residuos_origem_em_contato = set()
    residuos_destino_em_contato = set()

    for res_origem in model[cadeia_origem]:
        if res_origem.is_water():
            continue

        for atom_origem in res_origem:
            if atom_origem.element.name == "H":
                continue

            vizinhos = neighbor_search.find_atoms(pos=atom_origem.pos, alt="\0", radius=cutoff)
            for vizinho in vizinhos:
                cra = vizinho.to_cra(model)

                if cra.chain.name != cadeia_destino:
                    continue
                if cra.residue.is_water():
                    continue
                if cra.atom.element.name == "H":
                    continue

                contatos_atomicos += 1
                # Guardamos também par de resíduos para não depender só do número bruto de átomos.
                id_origem = (res_origem.name, res_origem.seqid.num)
                id_destino = (cra.residue.name, cra.residue.seqid.num)
                pares_residuos.add((id_origem, id_destino))
                residuos_origem_em_contato.add(id_origem)
                residuos_destino_em_contato.add(id_destino)

    return {
        "contatos_atomicos": contatos_atomicos,
        "res_pairs_set": pares_residuos,
        "res_origem_set": residuos_origem_em_contato,
        "res_destino_set": residuos_destino_em_contato,
    }


def ids_residuos_polymer(cadeia):
    # Aqui entram só resíduos do trecho polimérico.
    # Isso evita Cob% > 100 por conta de hetero-resíduos na mesma cadeia.
    ids = set()
    for res in cadeia.get_polymer():
        ids.add((res.name, res.seqid.num))
    return ids


def rotulo_forca(contatos_total):
    if contatos_total >= 300:
        return "forte"
    if contatos_total >= 100:
        return "moderada"
    return "fraca"


def classificar_confianca(score, cobertura, contatos_total):
    # Regras práticas de confiança. São heurísticas e podem ser recalibradas depois.
    if score >= 380 and cobertura >= 0.65 and contatos_total >= 140:
        return "alta"
    if score >= 220 and cobertura >= 0.45 and contatos_total >= 90:
        return "media"
    return "baixa"


def imprimir_tabela_cadeias(model, info_cadeias):
    if RICH_DISPONIVEL:
        tabela = Table(title="Resumo por cadeia", box=box.SIMPLE_HEAVY)
        tabela.add_column("Cadeia", style="bold cyan")
        tabela.add_column("len(chain)", justify="right")
        tabela.add_column("len(polymer)", justify="right")
        tabela.add_column("Classe", style="magenta")
        tabela.add_column("Tag FASTA", style="green")

        for cadeia in model:
            i = info_cadeias[cadeia.name]
            tabela.add_row(cadeia.name, str(i["len_chain"]), str(i["len_poly"]), i["classe"], i["tag_fasta"])
        CONSOLE.print(tabela)
        return

    print("\nResumo por cadeia:")
    print(f"{'Cadeia':<8} {'len(chain)':>10} {'len(polymer)':>14} {'Classe':>24} {'Tag FASTA':<60}")
    print("-" * 125)
    for cadeia in model:
        i = info_cadeias[cadeia.name]
        print(f"{cadeia.name:<8} {i['len_chain']:>10} {i['len_poly']:>14} {i['classe']:>24} {i['tag_fasta']:<60}")


def imprimir_tabela_pares(resultados, cutoff):
    if RICH_DISPONIVEL:
        tabela = Table(title=f"Interacoes entre pares (cutoff {cutoff:.1f} A)", box=box.SIMPLE_HEAVY)
        tabela.add_column("Par", style="bold cyan")
        tabela.add_column("C1->C2", justify="right")
        tabela.add_column("C2->C1", justify="right")
        tabela.add_column("Total", justify="right", style="bold")
        tabela.add_column("Res12", justify="right")
        tabela.add_column("Res21", justify="right")
        # ResTotal é direcional (Res12 + Res21); útil para leitura rápida.
        tabela.add_column("ResTotal", justify="right")
        tabela.add_column("Obs", style="yellow")

        for r in resultados:
            tabela.add_row(
                r["par"],
                str(r["contatos_12"]),
                str(r["contatos_21"]),
                str(r["contatos_total"]),
                str(r["res_pairs_12"]),
                str(r["res_pairs_21"]),
                str(r["res_pairs_total"]),
                rotulo_forca(r["contatos_total"]),
            )
        CONSOLE.print(tabela)
        return

    print("\nTabela de interacoes entre pares de cadeias")
    print(f"Cutoff: {cutoff:.1f} A | sem agua | sem H")
    print("-" * 105)
    print(
        f"{'Par':<8} {'C1->C2':>10} {'C2->C1':>10} {'Total':>10} "
        f"{'Res12':>10} {'Res21':>10} {'ResTotal':>10} {'Observacao':>16}"
    )
    print("-" * 105)
    for r in resultados:
        print(
            f"{r['par']:<8} {r['contatos_12']:>10} {r['contatos_21']:>10} {r['contatos_total']:>10} "
            f"{r['res_pairs_12']:>10} {r['res_pairs_21']:>10} {r['res_pairs_total']:>10} {rotulo_forca(r['contatos_total']):>16}"
        )


def imprimir_tabela_candidatos(candidatos):
    if RICH_DISPONIVEL:
        tabela = Table(title="Candidatos MHC-peptideo (score composto)", box=box.SIMPLE_HEAVY)
        tabela.add_column("MHC", style="bold cyan")
        tabela.add_column("Pept", style="bold cyan")
        tabela.add_column("Contatos", justify="right")
        tabela.add_column("ResUnicos", justify="right")
        tabela.add_column("PepLen", justify="right")
        # PepCont = resíduos do peptídeo (poliméricos) que tocaram o MHC.
        tabela.add_column("PepCont", justify="right")
        # Cob% = PepCont / PepLen * 100.
        tabela.add_column("Cob%", justify="right")
        tabela.add_column("Score", justify="right", style="bold")
        tabela.add_column("Confianca", style="yellow")

        for c in candidatos:
            tabela.add_row(
                c["mhc"],
                c["pep"],
                str(c["contatos_total"]),
                str(c["res_pairs_unicos"]),
                str(c["pep_len"]),
                str(c["pep_res_em_contato"]),
                f"{100*c['cobertura_peptideo']:.1f}%",
                f"{c['score']:.1f}",
                c["confianca"],
            )
        CONSOLE.print(tabela)
        return

    print("\nCandidatos MHC-peptideo (score composto)")
    print("-" * 116)
    print(
        f"{'MHC':<6} {'Pept':<6} {'Contatos':>10} {'ResUnicos':>10} {'PepLen':>8} "
        f"{'PepCont':>8} {'Cob%':>8} {'Score':>10} {'Confianca':>12}"
    )
    print("-" * 116)
    for c in candidatos:
        print(
            f"{c['mhc']:<6} {c['pep']:<6} {c['contatos_total']:>10} {c['res_pairs_unicos']:>10} "
            f"{c['pep_len']:>8} {c['pep_res_em_contato']:>8} {100*c['cobertura_peptideo']:>7.1f}% "
            f"{c['score']:>10.1f} {c['confianca']:>12}"
        )


def explorar_pares_interativamente(resultados):
    if not QUESTIONARY_DISPONIVEL or not resultados or not terminal_interativo_disponivel():
        return

    while True:
        escolha = questionary.select(
            "Inspecionar detalhes de um par?",
            choices=["Nao"] + [r["par"] for r in resultados[:20]],
            use_shortcuts=True,
        ).ask()

        if not escolha or escolha == "Nao":
            break

        r = next(x for x in resultados if x["par"] == escolha)
        msg = (
            f"Par: {r['par']}\n"
            f"Contatos direcionais: {r['contatos_12']} e {r['contatos_21']}\n"
            f"Contatos totais: {r['contatos_total']}\n"
            f"Pares de residuos (12, 21, total): {r['res_pairs_12']}, {r['res_pairs_21']}, {r['res_pairs_total']}\n"
            f"Forca: {rotulo_forca(r['contatos_total'])}"
        )
        if RICH_DISPONIVEL:
            CONSOLE.print(Panel(msg, border_style="green"))
        else:
            print(f"\n{msg}")


def calcular_resultados_estrutura(caminho_cif, cutoff=4.0):
    st = gemmi.read_structure(caminho_cif)
    st.setup_entities()
    model = st[0]
    nomes_cadeias = [c.name for c in model]

    caminho_fasta = encontrar_fasta_correspondente(caminho_cif)
    tags_fasta = extrair_tags_cadeia_do_fasta(caminho_fasta)

    info_cadeias = {}
    for cadeia in model:
        len_poly = len(cadeia.get_polymer())
        info_cadeias[cadeia.name] = {
            "len_chain": len(cadeia),
            "len_poly": len_poly,
            "classe": classificar_cadeia_por_tamanho(len_poly),
            "tag_fasta": resumir_tag(tags_fasta.get(cadeia.name.upper(), [])),
        }

    ns = gemmi.NeighborSearch(model, st.cell, cutoff)
    ns.populate(include_h=False)

    resultados = []
    for c1, c2 in combinations(nomes_cadeias, 2):
        # Todas as combinações 2 a 2 entre cadeias do modelo.
        met_12 = contar_contatos_direcionais(model, ns, c1, c2, cutoff)
        met_21 = contar_contatos_direcionais(model, ns, c2, c1, cutoff)
        res_pairs_12 = len(met_12["res_pairs_set"])
        res_pairs_21 = len(met_21["res_pairs_set"])
        res_pairs_unicos = len(met_12["res_pairs_set"] | {(b, a) for (a, b) in met_21["res_pairs_set"]})

        resultados.append(
            {
                "par": f"{c1}-{c2}",
                "c1": c1,
                "c2": c2,
                "contatos_12": met_12["contatos_atomicos"],
                "contatos_21": met_21["contatos_atomicos"],
                "contatos_total": met_12["contatos_atomicos"] + met_21["contatos_atomicos"],
                "res_pairs_12": res_pairs_12,
                "res_pairs_21": res_pairs_21,
                # "res_pairs_total" mantém a visão direcional da tabela principal.
                "res_pairs_total": res_pairs_12 + res_pairs_21,
                "res_pairs_unicos": res_pairs_unicos,
                "met_12": met_12,
                "met_21": met_21,
            }
        )

    resultados.sort(key=lambda x: x["contatos_total"], reverse=True)

    candidatos = []
    for r in resultados:
        c1 = r["c1"]
        c2 = r["c2"]
        classe_1 = info_cadeias[c1]["classe"]
        classe_2 = info_cadeias[c2]["classe"]

        orientacoes = []
        if classe_1 == "mhc_pesada_candidata" and classe_2 == "peptideo_candidato":
            orientacoes.append((c1, c2, r["met_12"], r["met_21"]))
        if classe_2 == "mhc_pesada_candidata" and classe_1 == "peptideo_candidato":
            orientacoes.append((c2, c1, r["met_21"], r["met_12"]))

        for cadeia_mhc, cadeia_pep, met_mhc_pep, met_pep_mhc in orientacoes:
            len_pep = info_cadeias[cadeia_pep]["len_poly"]
            ids_poly_pep = ids_residuos_polymer(model[cadeia_pep])
            residues_pep_em_contato = met_mhc_pep["res_destino_set"] | met_pep_mhc["res_origem_set"]
            residues_pep_poly_em_contato = residues_pep_em_contato & ids_poly_pep
            pep_cont = len(residues_pep_poly_em_contato)
            # Cobertura mede quanto do peptídeo está de fato engajado na interface.
            cobertura_peptideo = pep_cont / max(1, len_pep)
            contatos_total = r["contatos_total"]
            res_pairs = r["res_pairs_unicos"]

            # Score composto:
            # - contatos_total: intensidade de interface
            # - res_pairs: diversidade de contato entre resíduos
            # - cobertura: evita favorecer pares com contato muito localizado
            score = contatos_total + (2.5 * res_pairs) + (120.0 * cobertura_peptideo)

            candidatos.append(
                {
                    "mhc": cadeia_mhc,
                    "pep": cadeia_pep,
                    "contatos_total": contatos_total,
                    "res_pairs_unicos": res_pairs,
                    "pep_len": len_pep,
                    "pep_res_em_contato": pep_cont,
                    "cobertura_peptideo": cobertura_peptideo,
                    "score": score,
                    "confianca": classificar_confianca(score, cobertura_peptideo, contatos_total),
                }
            )

    candidatos.sort(key=lambda x: x["score"], reverse=True)

    return {
        "arquivo": os.path.basename(caminho_cif),
        "caminho_fasta": caminho_fasta,
        "model": model,
        "nomes_cadeias": nomes_cadeias,
        "info_cadeias": info_cadeias,
        "resultados": resultados,
        "candidatos": candidatos,
    }


def analisar_estrutura(caminho_cif, cutoff=4.0):
    dados = calcular_resultados_estrutura(caminho_cif, cutoff=cutoff)
    model = dados["model"]
    nomes_cadeias = dados["nomes_cadeias"]
    resultados = dados["resultados"]
    candidatos = dados["candidatos"]

    titulo(f"Estrutura: {dados['arquivo']}")
    print(f"Numero de cadeias no modelo: {len(nomes_cadeias)}")
    print(f"Numero de pares 2 a 2: {len(nomes_cadeias) * (len(nomes_cadeias) - 1) // 2}")

    if dados["caminho_fasta"]:
        print(f"FASTA usado para tags: {os.path.basename(dados['caminho_fasta'])}")
    else:
        print("FASTA usado para tags: nao encontrado")

    imprimir_tabela_cadeias(model, dados["info_cadeias"])
    imprimir_tabela_pares(resultados, cutoff)

    if candidatos:
        imprimir_tabela_candidatos(candidatos)
        top = candidatos[0]
        print("\nMelhor candidato MHC-peptideo (regra atual):")
        print(
            f"MHC={top['mhc']} | Peptideo={top['pep']} | Score={top['score']:.1f} "
            f"| Cobertura={100*top['cobertura_peptideo']:.1f}% | Confianca={top['confianca']}"
        )
    else:
        print("\nNenhum par bateu o filtro de tamanho (mhc pesado + peptideo curto).")

    if resultados:
        top_par = resultados[0]
        print("\nPar com maior interacao (metrica bruta):")
        print(f"{top_par['par']} | total={top_par['contatos_total']} (dir: {top_par['contatos_12']} + {top_par['contatos_21']})")

    explorar_pares_interativamente(resultados)


def _resumo_top(candidatos):
    # Ignora candidatos sem contato real para não poluir top 1/top 2.
    validos = [c for c in candidatos if c["contatos_total"] > 0]
    top1 = validos[0] if len(validos) >= 1 else None
    top2 = validos[1] if len(validos) >= 2 else None
    return top1, top2


def relatorio_sintetizado_todos(cifs, pasta, cutoff=4.0):
    linhas = []

    for nome_cif in cifs:
        caminho = os.path.join(pasta, nome_cif)
        try:
            dados = calcular_resultados_estrutura(caminho, cutoff=cutoff)
            top1, top2 = _resumo_top(dados["candidatos"])
            # Também mostramos o "par bruto" para comparar regra biológica vs maior contato total.
            bruto = dados["resultados"][0] if dados["resultados"] else None
            linhas.append({"arquivo": nome_cif, "top1": top1, "top2": top2, "bruto": bruto, "erro": None})
        except Exception as exc:
            linhas.append({"arquivo": nome_cif, "top1": None, "top2": None, "bruto": None, "erro": str(exc)})

    titulo("Relatorio sintetizado de todas as estruturas")
    print(f"Total de arquivos: {len(cifs)} | Cutoff: {cutoff:.1f} A")

    if RICH_DISPONIVEL:
        tabela = Table(title="Top candidatos MHC-peptideo por CIF", box=box.SIMPLE_HEAVY)
        tabela.add_column("CIF", style="bold cyan")
        tabela.add_column("Top1", style="green")
        tabela.add_column("Score1", justify="right")
        tabela.add_column("Conf1", justify="center")
        tabela.add_column("Top2", style="green")
        tabela.add_column("Score2", justify="right")
        tabela.add_column("Conf2", justify="center")
        tabela.add_column("Par Bruto", style="yellow")
        tabela.add_column("Status")

        for l in linhas:
            if l["erro"]:
                tabela.add_row(l["arquivo"], "-", "-", "-", "-", "-", "-", "-", f"erro: {l['erro']}")
                continue

            t1 = l["top1"]
            t2 = l["top2"]
            bruto = l["bruto"]
            tabela.add_row(
                l["arquivo"],
                f"{t1['mhc']}-{t1['pep']}" if t1 else "-",
                f"{t1['score']:.1f}" if t1 else "-",
                t1["confianca"] if t1 else "-",
                f"{t2['mhc']}-{t2['pep']}" if t2 else "-",
                f"{t2['score']:.1f}" if t2 else "-",
                t2["confianca"] if t2 else "-",
                f"{bruto['par']} ({bruto['contatos_total']})" if bruto else "-",
                "ok",
            )

        CONSOLE.print(tabela)
        return

    print("\nTop candidatos MHC-peptideo por CIF")
    print("-" * 130)
    print(
        f"{'CIF':<14} {'Top1':<10} {'Score1':>8} {'Conf1':>8} "
        f"{'Top2':<10} {'Score2':>8} {'Conf2':>8} {'ParBruto':<16} {'Status':<20}"
    )
    print("-" * 130)
    for l in linhas:
        if l["erro"]:
            print(f"{l['arquivo']:<14} {'-':<10} {'-':>8} {'-':>8} {'-':<10} {'-':>8} {'-':>8} {'-':<16} erro")
            continue

        t1 = l["top1"]
        t2 = l["top2"]
        bruto = l["bruto"]

        top1 = f"{t1['mhc']}-{t1['pep']}" if t1 else "-"
        score1 = f"{t1['score']:.1f}" if t1 else "-"
        conf1 = t1["confianca"] if t1 else "-"
        top2 = f"{t2['mhc']}-{t2['pep']}" if t2 else "-"
        score2 = f"{t2['score']:.1f}" if t2 else "-"
        conf2 = t2["confianca"] if t2 else "-"
        par_bruto = f"{bruto['par']}({bruto['contatos_total']})" if bruto else "-"

        print(f"{l['arquivo']:<14} {top1:<10} {score1:>8} {conf1:>8} {top2:<10} {score2:>8} {conf2:>8} {par_bruto:<16} ok")


def main():
    pasta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../cif_files/")
    print(f"Procurando arquivos .cif em: {pasta}")
    aviso_dependencias()

    while True:
        cifs = listar_cifs(pasta)
        if not cifs:
            print("Nenhum arquivo .cif encontrado na pasta do script.")
            return

        if QUESTIONARY_DISPONIVEL and terminal_interativo_disponivel():
            acao = questionary.select(
                "O que voce quer fazer?",
                choices=[
                    "Analisar um arquivo",
                    "Relatorio sintetizado (todos os CIFs)",
                    "Sair",
                ],
            ).ask()

            if acao == "Sair" or not acao:
                print("Encerrando.")
                break

            if acao == "Relatorio sintetizado (todos os CIFs)":
                relatorio_sintetizado_todos(cifs, pasta, cutoff=4.0)
                continue

            arquivo_escolhido = escolher_arquivo(cifs)
            caminho = os.path.join(pasta, arquivo_escolhido)
            print(f"\nAnalisando {caminho}...")
            try:
                analisar_estrutura(caminho_cif=caminho, cutoff=4.0)
            except Exception as exc:
                print(f"\nErro ao analisar {arquivo_escolhido}: {exc}")

            repetir = questionary.select("Deseja analisar outro arquivo?", choices=["Sim", "Nao"]).ask()
            if repetir != "Sim":
                print("Encerrando.")
                break

        else:
            print("\nEscolha uma opcao:")
            print("1) Analisar um arquivo")
            print("2) Relatorio sintetizado (todos os CIFs)")
            print("3) Sair")
            escolha = input("Opcao: ").strip()

            if escolha == "3":
                print("Encerrando.")
                break

            if escolha == "2":
                relatorio_sintetizado_todos(cifs, pasta, cutoff=4.0)
                continuar = input("\nVoltar ao menu principal? [s/n]: ").strip().lower()
                if continuar != "s":
                    print("Encerrando.")
                    break
                continue

            arquivo_escolhido = escolher_arquivo(cifs)
            caminho = os.path.join(pasta, arquivo_escolhido)
            try:
                analisar_estrutura(caminho_cif=caminho, cutoff=4.0)
            except Exception as exc:
                print(f"\nErro ao analisar {arquivo_escolhido}: {exc}")

            repetir = input("\nDeseja analisar outro arquivo? [s/n]: ").strip().lower()
            if repetir != "s":
                print("Encerrando.")
                break


if __name__ == "__main__":
    main()
