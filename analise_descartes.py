import os
import json

def investigar_descartes_detalhado():
    arquivo_originais = "mhc_data/mhc_split.txt" 
    dir_novo = "mhc_data/dataset_limpo/structures"
    manifesto_path = "rcsb_processed_targets/manifest.json"
    arquivo_saida = "mhc_data/relatorio_descartes_detalhado.txt"
    
    try:
        with open(arquivo_originais, 'r') as f:
            originais = set([linha.strip().upper() for linha in f.readlines() if linha.strip()])
    except FileNotFoundError:
        print(f"Erro: O arquivo {arquivo_originais} não encontrado.")
        return

    novos = set([f.replace('.npz', '').upper() for f in os.listdir(dir_novo) if f.endswith('.npz')])
    descartados = sorted(list(originais - novos))
    
    if os.path.exists(manifesto_path):
        with open(manifesto_path, 'r') as f:
            manifesto_lista = json.load(f)
        manifesto_dict = {item.get('id', '').upper(): item for item in manifesto_lista}
            
        with open(arquivo_saida, 'w') as out:
            header = f"{'PDB ID':<8} | {'Cadeias':<8} | {'Maior':<8} | {'Menor':<8} | {'Diagnóstico'}"
            out.write("="*75 + "\n")
            out.write(f"🕵️ RELATÓRIO DETALHADO DE DESCARTE ({len(descartados)} proteínas)\n")
            out.write("="*75 + "\n")
            out.write(header + "\n")
            out.write("-" * 75 + "\n")
            
            for pdb_id in descartados:
                proteina_info = manifesto_dict.get(pdb_id)
                if proteina_info:
                    cadeias = proteina_info.get('chains', [])
                    num_cadeias = len(cadeias)
                    tamanhos = [c.get('num_residues', 0) for c in cadeias]
                    maior = max(tamanhos) if tamanhos else 0
                    menor = min(tamanhos) if tamanhos else 0
                    
                    motivos = []
                    if maior <= 200: motivos.append("MHC Incompleto")
                    if menor >= 25: motivos.append("Pep. Ausente")
                    diag = " + ".join(motivos) if motivos else "Outro"
                    
                    out.write(f"{pdb_id:<8} | {num_cadeias:<8} | {maior:<8} | {menor:<8} | ❌ {diag}\n")
                else:
                    out.write(f"{pdb_id:<8} | {'?':<8} | {'-':<8} | {'-':<8} | ⚠️ Não consta no manifesto\n")
            
            out.write("="*75 + "\n")
            
        print(f"✅ Relatório detalhado gerado em: {arquivo_saida}")
    else:
        print("Manifesto não encontrado.")

investigar_descartes_detalhado()