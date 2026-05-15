import os
import glob

def auditar_cabecalhos_fasta(diretorio_fastas):
    arquivos_fasta = glob.glob(os.path.join(diretorio_fastas, "*.fasta"))
    
    if not arquivos_fasta:
        print(f"Nenhum arquivo .fasta encontrado em {diretorio_fastas}")
        return

    print(f"Analisando {len(arquivos_fasta)} arquivos FASTA...\n")
    print(f"{'PDB ID':<8} | {'Total Cadeias':<14} | {'Achou MHC?':<12} | {'Achou Peptídeo?':<15}")
    print("=" * 55)

    proteinas_perfeitas = 0

    for caminho in arquivos_fasta:
        pdb_id = os.path.basename(caminho).replace('.fasta', '').upper()
        
        total_cadeias = 0
        achou_mhc = False
        achou_peptideo = False
        
        with open(caminho, 'r') as f:
            linhas = f.readlines()
            
            for linha in linhas:
                if linha.startswith(">"):  # É uma linha de cabeçalho da cadeia
                    total_cadeias += 1
                    linha_lower = linha.lower()
                    
                    if "mhc" in linha_lower or "histocompatibility" in linha_lower:
                        achou_mhc = True
                    if "peptide" in linha_lower:
                        achou_peptideo = True

        status_mhc = "✅ Sim" if achou_mhc else "❌ Não"
        status_pep = "✅ Sim" if achou_peptideo else "❌ Não"
        
        if achou_mhc and achou_peptideo:
            proteinas_perfeitas += 1

        print(f"{pdb_id:<8} | {total_cadeias:<14} | {status_mhc:<12} | {status_pep:<15}")

    print("=" * 55)
    taxa_sucesso = (proteinas_perfeitas / len(arquivos_fasta)) * 100
    print(f"Resultado Final: {taxa_sucesso:.1f}% das proteínas têm as marcações perfeitas no texto.")

# Substitua pelo caminho onde os arquivos .fasta foram salvos no servidor
diretorio_dos_fastas = "rcsb_processed_targets/fasta" 
auditar_cabecalhos_fasta(diretorio_dos_fastas)
