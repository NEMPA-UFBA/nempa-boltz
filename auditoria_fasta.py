import os
import glob
import urllib.request

def auditar_fastas_via_api(diretorio_npz):
    # Procura os arquivos .npz para extrair os IDs
    arquivos_npz = glob.glob(os.path.join(diretorio_npz, "*.npz"))
    
    if not arquivos_npz:
        print(f"Nenhum arquivo .npz encontrado em {diretorio_npz}")
        return

    print(f"Analisando proteínas baixando o FASTA direto do PDB...\n")
    print(f"{'PDB ID':<8} | {'Total Cadeias':<14} | {'Achou MHC?':<12} | {'Achou Peptídeo?':<15}")
    print("=" * 55)

    proteinas_perfeitas = 0
    erros_download = 0

    # LIMITADOR: Está pegando apenas os primeiros 20 arquivos. 
    # Para testar todos os 1200+, mude a linha abaixo para: for caminho in arquivos_npz:
    for caminho in arquivos_npz[:20]: 
        pdb_id = os.path.basename(caminho)[:4].upper()
        
        # URL oficial da API do PDB para baixar o FASTA
        url = f"https://www.rcsb.org/fasta/entry/{pdb_id}/display"
        
        try:
            # Baixa o conteúdo do FASTA inteiro da internet
            resposta = urllib.request.urlopen(url)
            conteudo = resposta.read().decode('utf-8').splitlines()
            
            total_cadeias = 0
            achou_mhc = False
            achou_peptideo = False
            
            # Varre linha por linha
            for linha in conteudo:
                if linha.startswith(">"):  # Só analisa a linha de cabeçalho
                    total_cadeias += 1
                    linha_lower = linha.lower()
                    
                    # Procura as palavras-chave
                    if "mhc" in linha_lower or "histocompatibility" in linha_lower:
                        achou_mhc = True
                    if "peptide" in linha_lower:
                        achou_peptideo = True

            status_mhc = "✅ Sim" if achou_mhc else "❌ Não"
            status_pep = "✅ Sim" if achou_peptideo else "❌ Não"
            
            if achou_mhc and achou_peptideo:
                proteinas_perfeitas += 1

            print(f"{pdb_id:<8} | {total_cadeias:<14} | {status_mhc:<12} | {status_pep:<15}")
            
        except Exception as e:
            print(f"{pdb_id:<8} | {'ERRO DOWNLOAD':<14} | {'-':<12} | {'-':<15}")
            erros_download += 1

    print("=" * 55)
    total_analisado = min(len(arquivos_npz), 20) - erros_download
    
    if total_analisado > 0:
        taxa_sucesso = (proteinas_perfeitas / total_analisado) * 100
        print(f"Resultado Final: {taxa_sucesso:.1f}% das proteínas analisadas têm marcações perfeitas no texto.")
    else:
        print("Nenhuma proteína pôde ser analisada com sucesso.")

# ATENÇÃO: Ajuste o caminho abaixo se necessário
diretorio = "rcsb_processed_targets/structures"
auditar_fastas_via_api(diretorio)
