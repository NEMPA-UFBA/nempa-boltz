# Guia de Primeiro Acesso: Servidor CMCAD
Este documento fornece as instruções essenciais para a inicialização e configuração do ambiente de trabalho no servidor Linux CMCAD. O ambiente foi estruturado para garantir a segurança dos dados, o isolamento de processos e a rastreabilidade do desenvolvimento contínuo dos pipelines de MLOps e predições estruturais.

## 1. Conexão Inicial
O acesso ao servidor é realizado exclusivamente via protocolo SSH. Utilize o terminal do sistema operacional local e insira o comando abaixo, substituindo `[usuario]` pelo nome de usuário designado (ex: ikaro, roberto) e `[IP]` pelo endereço do servidor:

```Bash
ssh [usuario]@[IP]
```
A senha inicial será fornecida individualmente pela administração do sistema.

## 2. Políticas de Segurança e Limitações do Ambiente
Para garantir a estabilidade do servidor e a integridade dos dados compartilhados, as seguintes políticas estão ativas por padrão:

**Privilégios Administrativos:** Os usuários operam em modo restrito. A execução de comandos com sudo (instalação de pacotes ou alteração de configurações globais do sistema) está desabilitada e registrará um alerta de segurança caso tentada.

**Gestão de Senhas:** A alteração da senha de acesso (passwd) encontra-se bloqueada.

**Isolamento de Diretórios:** O diretório pessoal (/home/[usuario]) é estritamente privado. A leitura ou gravação de arquivos nos diretórios de outros membros da equipe é bloqueada nativamente pelo sistema operacional.

## 3. Configuração do Git (Ação Obrigatória)
Para que as contribuições nos códigos do projeto sejam rastreadas corretamente, é obrigatório configurar a identidade Git logo no primeiro login. Execute os comandos abaixo no terminal:

Definição de Identidade:

```Bash
git config --global user.name "Seu Nome Completo"
git config --global user.email "seu_email@dominio.com"
```

### Autorização do Diretório Compartilhado:
Como os repositórios do projeto residem em uma pasta compartilhada por múltiplos usuários, é necessário instruir o Git de que o diretório é seguro para operações:

```Bash
git config --global --add safe.directory /opt/projeto_cmcad
```
### Chaves SSH para GitHub/GitLab (Opcional, mas recomendado):
Para realizar commits e pushes sem a necessidade de inserir credenciais repetidamente, recomenda-se a geração de uma chave SSH local no servidor e a sua respectiva adição na plataforma de versionamento em nuvem:

```Bash
ssh-keygen -t rsa -b 4096
cat ~/.ssh/id_rsa.pub
```

## 4. Espaço de Trabalho Colaborativo
Todo o desenvolvimento de código, execução de scripts e armazenamento de dados (como os arquivos estruturais e manifestos) deve ocorrer dentro do diretório compartilhado da equipe:

```Bash
cd /opt/projeto_cmcad
```

**Permissões Automáticas:** Este diretório está configurado com regras de herança (SetGID). Qualquer arquivo ou subdiretório criado dentro de /opt/projeto_cmcad pertencerá automaticamente ao grupo técnico, garantindo que todos os membros tenham acesso de leitura e escrita sem a ocorrência de erros de permissão.

**Boas Práticas:** Evite processar dados volumosos diretamente no diretório /home. Utilize sempre o espaço de trabalho colaborativo para garantir que o progresso seja acessível aos demais desenvolvedores.

*Para requisições de instalação de pacotes (Python, dependências do sistema) ou dúvidas operacionais adicionais, os chamados devem ser direcionados à administração do servidor.*