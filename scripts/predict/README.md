# Predicao: ferramentas NEMPA

## Procedencia

Os scripts desta pasta foram adicionados pela equipe NEMPA neste fork; eles nao
fazem parte da distribuicao upstream de `jwohlwend/boltz`. Foram agrupados aqui
para organizar o fluxo local de pre-processamento, sem alterar os modulos do
modelo Boltz.

## Scripts

- `prepare_boltz_fastas.py`: seleciona cadeias a partir de CIFs e gera FASTAs
  compativeis com Boltz, alem de `selection_report.tsv`.
- `download_rcsb_fastas_legacy.py`: downloader historico de FASTAs brutos do
  RCSB. Esses arquivos nao sao entradas compativeis com Boltz; use o preparador
  acima para gerar os FASTAs de predicao.

Os caminhos de execucao e os parametros usados no benchmark estao registrados
no guia operacional em `docs/Bem-vind@/Guia de Operacao (Atualizado 2026-09-29).md`.