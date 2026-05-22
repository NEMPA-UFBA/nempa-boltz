import pandas as pd

# Caminho de leitura e Caminho EXATO de saída pedido pelo Ernest
csv_path = "mhc_data/TCR3d_data.csv"
output_path = "scripts/train/assets/validation_ids.txt"

def generate_validation_split():
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Erro: Arquivo {csv_path} não encontrado.")
        return

    df['Release date'] = pd.to_datetime(df['Release date'])

    # Janela das 128 amostras
    start_date = '2021-10-01'
    end_date = '2022-12-31'

    mask = (df['Release date'] >= start_date) & (df['Release date'] <= end_date)
    filtered_df = df.loc[mask]

    # Extrair PDB IDs e converter para minúsculas
    val_ids = filtered_df['PDB ID'].dropna().str.lower().unique().tolist()

    # Salvar no local correto
    with open(output_path, "w") as f:
        for pdb_id in val_ids:
            f.write(f"{pdb_id}\n")

    print(f"✅ Sucesso! Arquivo gerado em: {output_path}")
    print(f"📊 Total de proteínas na validação: {len(val_ids)}")

if __name__ == "__main__":
    generate_validation_split()
