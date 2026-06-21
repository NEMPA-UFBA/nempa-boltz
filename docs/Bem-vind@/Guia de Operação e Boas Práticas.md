# Guia de Operação e Boas Práticas: Servidor CMCAD (Ambiente GPU)

Este documento estabelece as diretrizes de acesso, a arquitetura de diretórios e o protocolo de utilização de hardware para as execuções de rotinas de Machine Learning e docking estrutural.

## 1. Arquitetura de Diretórios Compartilhados
Todo o fluxo de trabalho, códigos-fonte e dados devem ser mantidos estritamente dentro do ecossistema centralizado `/opt/projeto_cmcad/`. A estrutura está subdividida para assegurar a organização e proteger os arquivos contra edições acidentais cruzadas:

`/opt/projeto_cmcad/datasets/`: Repositório central de dados estáticos. Destinado ao armazenamento de bancos PDB/CIF originais, arquivos de alinhamento múltiplo (MSA) e manifestos validados. Permissão: Leitura e gravação para toda a equipe.

`/opt/projeto_cmcad/modelos/`: Repositório de saídas e aprendizado. Destinado a abrigar os pesos de rede neural e arquivos finais preditos. Permissão: Leitura e gravação para toda a equipe.

`/opt/projeto_cmcad/workspaces/{nome_do_usuario}/`: Ambientes de desenvolvimento isolados. Os clones de repositórios Git, scripts Python em fase de testes e rascunhos devem ser executados dentro da pasta respectiva de cada integrante. Permissão: Apenas o proprietário pode editar ou excluir arquivos; os demais integrantes possuem acesso estrito de leitura.

## 2. Protocolo de Utilização da Placa de Vídeo (GPU)
Para impedir interrupções críticas e falhas de alocação de memória (Out of Memory - OOM) causadas por colisões de processamento concorrente, o servidor conta com um sistema de bloqueio de hardware (Mutex).

A execução de qualquer processo intensivo na GPU requer obrigatoriamente a adição do prefixo `usar_gpu` ao comando padrão.

Exemplos de execução padronizada:

```Bash
# Execução de fine-tuning via script Python:
usar_gpu boltz train .......

# Execução nativa de predição em lote:
usar_gpu boltz predict /opt/projeto_cmcad/datasets/testes --out_dir /opt/projeto_cmcad/modelos/resultados
```

### Comportamento do Gerenciador de Processos:

Em cenários onde a GPU encontra-se ociosa, a execução do comando inicia o processamento imediatamente.

Em cenários onde o hardware encontra-se ocupado por um processamento de outro integrante, a execução é abortada no mesmo instante, exibindo a mensagem ACESSO NEGADO: A placa de vídeo já está em uso. Deve-se aguardar a conclusão do processo anterior.

## 3. Configurações Iniciais (Primeiro Login)
No primeiro acesso ao terminal, a execução dos comandos abaixo é obrigatória para habilitar o rastreamento adequado das contribuições no controle de versão (Git).

```Bash
# 1. Definição de identidade de commits
git config --global user.name "Nome Completo"
git config --global user.email "usuario@dominio.com"

# 2. Concessão de confiabilidade ao diretório raiz
git config --global --add safe.directory /opt/projeto_cmcad
```

A navegação para as pastas de trabalho deve ser efetuada imediatamente após a conexão via SSH:

```Bash
cd /opt/projeto_cmcad/workspaces/ikaro  # (Substituir pelo respectivo perfil)
```

## 4. Isolamento de Dependências (Ambientes Virtuais)
A instalação de pacotes Python (pip install) de forma global no servidor é estritamente proibida. A alteração de versões de bibliotecas globais pode quebrar os pipelines de predição do Boltz ou os scripts dos demais desenvolvedores.

Cada membro da equipe deve criar e gerenciar seus próprios ambientes virtuais dentro de seu respectivo workspace:

```Bash
# Criação do ambiente virtual (exemplo com venv)
python3 -m venv /opt/projeto_cmcad/workspaces/nome_do_usuario/meu_ambiente

# Ativação do ambiente antes de instalar pacotes ou rodar scripts
source /opt/projeto_cmcad/workspaces/nome_do_usuario/meu_ambiente/bin/activate
```

Com o ambiente ativado, qualquer comando pip install ficará restrito àquela pasta específica, garantindo isolamento total de dependências.

## 5. Persistência de Processos (Prevenção contra Quedas de SSH)
Treinamentos de rede neural e predições em lote podem demorar horas ou dias. Se o comando for executado diretamente no terminal padrão, o processo será aniquilado sumariamente caso a conexão de internet do usuário oscile ou o computador local seja desligado (fechamento da sessão SSH).

Para processos longos, deve-se utilizar obrigatoriamente um multiplexador de terminal, como o tmux ou screen:

```Bash
# 1. Inicia uma sessão persistente chamada "treino_boltz"
tmux new -s treino_boltz

# 2. Dentro da sessão, executa-se o comando normalmente
usar_gpu boltz train ....

# 3. Para sair do terminal e deixar rodando (Detach): Pressione Ctrl+B, solte, e aperte D.

# 4. Para voltar à sessão no dia seguinte:
tmux attach -t treino_boltz
```
## 6. Monitoramento de Fila da GPU
Quando o sistema negar acesso à placa de vídeo informando que ela já está em uso, a equipe dispõe de ferramentas para verificar qual integrante está alocando o recurso e o status do processamento, facilitando o alinhamento interno (em breve).

Para visualizar o consumo de VRAM e os processos ativos em tempo real, executa-se o comando:

```Bash
watch -n 2 nvidia-smi
```

(Para sair da tela de monitoramento, utiliza-se o atalho Ctrl+C).