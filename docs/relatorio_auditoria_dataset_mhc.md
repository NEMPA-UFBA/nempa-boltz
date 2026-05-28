# Relatorio de auditoria do dataset MHC

## Objetivo

Este documento consolida a auditoria do dataset MHC utilizado em nempa-boltz, identifica o universo efetivamente consumido pelo treino atual e formaliza uma proposta de separacao temporal entre treino, validacao e teste.

Anexo detalhado (IDs e reconciliacao completa entre fontes):

- [docs/relatorio_auditoria_dataset_mhc_detalhado.md](docs/relatorio_auditoria_dataset_mhc_detalhado.md)

## Arquivos de referencia

- Catalogo bruto: mhc_data/TCR3d_data.csv
- Estruturas processadas: get_subsamples/mhc_samples/structures
- Manifest principal do treino: get_subsamples/mhc_samples/manifest.json
- Split de validacao em uso: get_subsamples/mhc_samples/val_ids.txt
- Lista auxiliar historica de treino: get_subsamples/train_manifest_samples.txt
- Configuracao atual de treino: scripts/train/configs/full.yaml
- Lista formal de teste: scripts/train/assets/test_ids.txt
- Lista local de teste para o gerador de YAML: get_subsamples/Arquivos yaml/test_ids.txt
- Implementacao do DataModule: src/boltz/data/module/training.py

## Comportamento efetivo do treino atual

O treino carrega o manifest.json do target_dir configurado e usa o arquivo split apenas para separar validacao. A regra implementada e:

1. Se record.id estiver em split, o registro entra em validacao.
2. Caso contrario, o registro entra em treino.

Isso implica que qualquer amostra presente no manifest.json e ausente do val_ids.txt cai automaticamente no conjunto de treino.

## Universo bruto e cobertura do processamento

O catalogo bruto em mhc_data/TCR3d_data.csv contem 1452 IDs unicos.

Distribuicao temporal no CSV:

1. 1082 entradas com data de release ate 2021-09-30.
2. 128 entradas com data de release entre 2021-10-01 e 2022-12-31.
3. 242 entradas com data de release a partir de 2023-01-01.

Cobertura atual do processamento:

1. 1141 estruturas .npz existem em get_subsamples/mhc_samples/structures.
2. 311 IDs do CSV nao possuem estrutura processada correspondente.
3. Nao foram encontradas estruturas processadas sem correspondencia no CSV.

## Formalizacao do split temporal

Para alinhar o dataset ao recorte temporal e evitar vazamento entre validacao e teste, foi adotado o seguinte criterio:

1. Treino: amostras processadas com release ate 2021-09-30.
2. Validacao: amostras processadas com release entre 2021-10-01 e 2022-12-31.
3. Teste: amostras com release a partir de 2023-01-01.

Durante a auditoria, foi identificado que 8GQV e 8GQW estavam processadas, presentes no manifest e alocadas em validacao, apesar de terem release em 2023-01-11. Para tornar o split temporal consistente:

1. 8GQV e 8GQW foram removidas de get_subsamples/mhc_samples/manifest.json.
2. 8gqv e 8gqw foram removidas de get_subsamples/mhc_samples/val_ids.txt.
3. Ambas foram adicionadas ao conjunto formal de teste em scripts/train/assets/test_ids.txt.

## Estado final apos a formalizacao

### Treino

- Regra: amostras processadas com release ate 2021-09-30.
- Quantidade formal: 1024.
- Fonte operacional: manifest.json menos val_ids.txt.

### Validacao

- Regra: amostras processadas com release entre 2021-10-01 e 2022-12-31.
- Quantidade formal: 113.
- Fonte operacional: get_subsamples/mhc_samples/val_ids.txt.

### Teste

- Regra: amostras com release a partir de 2023-01-01.
- Quantidade formal: 242.
- Fonte operacional: scripts/train/assets/test_ids.txt.

Composicao do teste formal:

1. 240 IDs ja estavam fora do manifest e, portanto, fora de treino e validacao.
2. 2 IDs, 8GQV e 8GQW, estavam processadas e haviam entrado na validacao. Por isso, foram removidas do manifest e da validacao e promovidas para teste.

## Contagens do estado atual

1. Registros no manifest.json: 1137.
2. IDs em val_ids.txt: 113.
3. IDs em train_manifest_samples.txt: 1024.
4. Uniao train_manifest_samples.txt e val_ids.txt: 1137.
5. Estruturas processadas fora de treino e validacao: 4.

As quatro estruturas processadas que permanecem fora de treino e validacao sao:

1. 7bh8.
2. 7ndt.
3. 8gqv.
4. 8gqw.

Interpretacao:

1. 8gqv e 8gqw pertencem ao teste formal.
2. 7bh8 e 7ndt existem como estruturas processadas, mas nao aparecem no manifest atual. Devem ser tratados como casos fora do universo de treino e validacao ate decisao especifica de curadoria.

## Conclusoes operacionais

1. O treino atual pode continuar apontando para scripts/train/configs/full.yaml, pois o manifest.json e o val_ids.txt agora estao coerentes com o recorte temporal formalizado.
2. O conjunto de teste formal nao deve ser inferido a partir das 311 entradas sem estrutura processada, porque esse grupo mistura periodos temporais diferentes.
3. O teste formal deve ser definido pela data de release, e nao pela ausencia no manifest.
4. As 311 entradas sem estrutura processada podem ser usadas separadamente em estudos exploratorios de predict, desde que isso fique explicitamente documentado como um conjunto auxiliar e nao como o teste temporal formal.

## Uso com o gerador de YAML

O script get_subsamples/Arquivos yaml/gerador_yaml.py foi ajustado para:

1. Procurar primeiro um test_ids.txt local na mesma pasta do script.
2. Usar scripts/train/assets/test_ids.txt como fallback.
3. Criar automaticamente as pastas de saida para FASTA e YAML.

Exemplo para gerar os arquivos do conjunto de validacao:

```bash
conda run -n boltz_env python "/home/gpu/nempa-boltz/get_subsamples/Arquivos yaml/gerador_yaml.py" \
  --ids "/home/gpu/nempa-boltz/get_subsamples/mhc_samples/val_ids.txt" \
  --output "/home/gpu/nempa-boltz/get_subsamples/dados_validacao"
```

Exemplo para gerar os arquivos do teste formal:

```bash
conda run -n boltz_env python "/home/gpu/nempa-boltz/get_subsamples/Arquivos yaml/gerador_yaml.py" \
  --ids "/home/gpu/nempa-boltz/scripts/train/assets/test_ids.txt" \
  --output "/home/gpu/nempa-boltz/get_subsamples/dados_teste_temporal"
```

## Limitacoes conhecidas do gerador

1. O gerador constroi os YAMLs a partir do FASTA do RCSB.
2. O gerador trata as entradas polimericas como sequencias de proteina.
3. O gerador nao incorpora, por padrao, ligantes, constraints, modificacoes especiais ou MSA customizada.

Para o caso MHC-peptideo, o gerador pode ser usado como etapa operacional de preparacao de entradas para predict, mas os arquivos gerados devem ser entendidos como entradas simplificadas.

## Atualizacao operacional (2026-05-28)

### Status do predict do teste temporal

- Total de entradas no teste temporal: 241.
- Predicoes concluidas (CIF): 176.
- Predicoes restantes no momento desta atualizacao: 65.

Observacao:

- As contagens acima representam um snapshot operacional em 2026-05-28 e devem ser revalidadas antes de consolidar o fechamento do lote.

### Incidente observado durante a retomada

Durante a retomada de predições faltantes, houve falha de parse em parte dos YAMLs, com erro do tipo:

- KeyError em parse_boltz_schema, com IDs de cadeia no formato `A[auth ...]`.

### Causa-raiz

- O gerador de YAML preservava IDs de cadeia com sufixo de autoria do FASTA do RCSB (`[auth ...]`), formato que não é aceito pela etapa de parse do Boltz nesse fluxo.

### Correção aplicada

1. O script [get_subsamples/Arquivos yaml/gerador_yaml.py](get_subsamples/Arquivos%20yaml/gerador_yaml.py) foi ajustado para sanitizar IDs de cadeia, removendo sufixos `[auth ...]` e garantindo unicidade por arquivo.
2. Foi executada correção em lote nos YAMLs já gerados em [get_subsamples/dados_teste_temporal/yaml](get_subsamples/dados_teste_temporal/yaml), removendo IDs inválidos.
3. A retomada passou a ser feita por amostra, com log por ID, reduzindo perda de progresso em caso de interrupção.

### Procedimento operacional recomendado para fechamento do lote

1. Processar apenas IDs faltantes (em vez de relançar todo o conjunto).
2. Manter logs por amostra em `logs/predict_missing_retry`.
3. Revalidar progresso por contagem de CIFs (`DONE/TOTAL`) até atingir `241/241`.
4. Somente após conclusão total do predict, liberar a etapa automatizada de treino para evitar concorrência de GPU.
