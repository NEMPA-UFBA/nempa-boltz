# Relatorio de auditoria MHC - Anexo detalhado

## 1. Inventario de fontes e contagens

- CSV bruto (`mhc_data/TCR3d_data.csv`): **1452** IDs
- Estruturas processadas (`get_subsamples/mhc_samples/structures`): **1141** arquivos `.npz`
- Manifest atual (`get_subsamples/mhc_samples/manifest.json`): **1137** registros
- Validacao atual (`get_subsamples/mhc_samples/val_ids.txt`): **113** IDs
- Lista de treino auxiliar (`get_subsamples/train_manifest_samples.txt`): **1024** IDs
- Teste formal (`scripts/train/assets/test_ids.txt`): **242** IDs

## 2. Distribuicao temporal (CSV bruto)

- Ate 2021-09-30: **1082**
- 2021-10-01 a 2022-12-31: **128**
- A partir de 2023-01-01: **242**

## 3. Cobertura do manifest por faixa temporal

- Manifest (ate 2021-09-30): **1024**
- Manifest (2021-10 a 2022-12): **113**
- Manifest (>=2023-01-01): **0**

IDs fora do manifest (por faixa):

- Fora do manifest (ate 2021-09-30): **58**
- Fora do manifest (2021-10 a 2022-12): **15**
- Fora do manifest (>=2023-01-01): **242**

## 4. Mudancas estruturais relevantes realizadas

1. `8gqv` e `8gqw` foram removidas de `manifest.json` e de `val_ids.txt`.
2. `8GQV` e `8GQW` foram inseridas em `scripts/train/assets/test_ids.txt` para manter consistencia temporal do teste.
3. Estado atual dessas IDs:
   - em manifest: nao / nao
   - em validacao: nao / nao
   - em teste formal: sim / sim

### 4.1 Trecho auditavel da alteracao (manifest e teste)

Consulta aplicada no manifest atual para os IDs `8gqv` e `8gqw`:

```python
import json
from pathlib import Path

rows = json.loads(Path("get_subsamples/mhc_samples/manifest.json").read_text())
sel = [r for r in rows if r.get("id", "").lower() in {"8gqv", "8gqw"}]
print(sel)
```

Saida observada:

```text
[]
```

Trecho correspondente no teste formal (confirmando migracao para teste):

```text
scripts/train/assets/test_ids.txt:54:8GQV
scripts/train/assets/test_ids.txt:55:8GQW
```

## 5. Divergencias atuais entre fontes

- CSV sem estrutura processada: **311** IDs
- Manifest sem estrutura correspondente: **0** IDs
- Estruturas fora do manifest: **4** IDs
- Estruturas fora de treino+validacao: **4** IDs

IDs em `structures` mas fora do manifest:

```text
7bh8
7ndt
8gqv
8gqw
```

IDs em `structures` mas fora de treino+validacao:

```text
7bh8
7ndt
8gqv
8gqw
```

## 6. Lista completa - CSV sem estrutura processada

```text
1c16
1hla
1hsb
1nez
1qo3
1r3h
1ypz
1zs8
2cii
2hla
2qri
2qrs
2qrt
2x4o
2x4t
2x4u
3ch1
3hla
3nwm
3p73
3p77
3tf7
4lcy
4nhu
4uq3
5opi
5oqf
5oqg
5oqh
5oqi
5ts1
5wer
5wwj
5wxc
6apn
6d7g
6e1i
6eny
6gb6
6gh1
6j2j
6lah
6lam
6lb2
6lt6
6mp0
6mp1
6nf7
6ss7
6tdo
6tdp
6tdq
6tdr
6tds
7k81
7kgt
7l1d
7n6d
7n6e
7q98
7q99
7q9a
7q9b
7qng
7re8
7sqp
7sr0
7sr3
7sr4
7sr5
7srk
7ssh
7st3
7stf
7stg
7tue
7u1r
7um2
7ur1
7wzz
7x00
7x1b
7x1c
7xf3
7xqs
7xqt
7xqu
7yg3
7zqi
7zqj
7zuc
8dnt
8dvg
8e13
8e2z
8e8i
8ec5
8ek5
8elg
8elh
8emf
8emg
8emi
8emj
8emk
8en8
8enh
8eo8
8erx
8es8
8es9
8esa
8esb
8esh
8f5a
8f7m
8fhl
8fhu
8fja
8fjb
8frt
8fu4
8gom
8gon
8hn4
8hsm
8hso
8hsw
8ht1
8ht9
8i5c
8i5d
8i5e
8isn
8j4g
8jhv
8jhw
8jqt
8jv0
8k4t
8k4v
8k50
8kb0
8kb1
8kcv
8p43
8qfy
8rbu
8rbv
8rcv
8ref
8rh6
8rhq
8rj5
8rjh
8rji
8rlt
8rlu
8rlv
8rne
8rnf
8rng
8rnh
8rni
8roo
8rop
8rro
8rym
8ryn
8ryo
8ryp
8ryq
8sbk
8sbl
8shi
8t6m
8t7r
8tbv
8tbw
8tmu
8tnj
8tq4
8tq5
8tq6
8tq7
8tq8
8tq9
8tqa
8tub
8tuh
8u9g
8udr
8umo
8utc
8v4z
8v50
8v51
8v8q
8vcl
8vjz
8vr9
8vra
8vrb
8w6l
8wo9
8wte
8wul
8xes
8xfz
8xg2
8xkc
8xke
8y74
8ye4
8yiv
8yj2
8yzr
8yzw
8yzz
8z05
8z06
8z07
8z08
8z0h
8zv9
9asf
9asg
9bl2
9bl3
9bl4
9bl5
9bl6
9bl9
9bla
9c3e
9c6v
9c6w
9c6x
9c96
9cwy
9cwz
9cx0
9cx1
9cx2
9d72
9d73
9d74
9d95
9d96
9d97
9dl1
9dy8
9eb2
9eb3
9eb4
9eb5
9eb6
9f13
9fe1
9gv6
9gv7
9hkq
9hlj
9hy4
9iky
9j4s
9j4t
9j4u
9j4v
9k2i
9k2r
9k2s
9k2t
9k2u
9l47
9l48
9l49
9l4a
9l4g
9l4h
9l4i
9lud
9m01
9mda
9mef
9meg
9min
9nfb
9nfc
9nnf
9o55
9o5s
9pix
9pkc
9pkf
9pkv
9qg8
9rcv
9ru5
9rup
9rxm
9sko
9skp
9sl0
9ul1
9uv8
9wbd
9wve
9wvf
9ytd
9ytf
```

## 7. Integridade do conjunto de teste temporal (>=2023-01-01)

- Total >=2023 no CSV: **242**
- >=2023 presentes no teste formal: **242**
- >=2023 ausentes do teste formal: **0**

