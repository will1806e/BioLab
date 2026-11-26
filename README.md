# BioLab — controle interno de qualidade

Aplicação acadêmica com páginas HTML, JavaScript modular por página e API Python/Flask. Usa MySQL na execução local e Neon Postgres na implantação Vercel. O gráfico de **Levey-Jennings** aparece no dashboard e pode ser selecionado pelos filtros de equipamento, lote e analito em “Controle de qualidade”. Não há importação de CSV nesta etapa.

## Integração com as novidades do repositório

Base atualizada até o commit `8706656` de [will1806e/BioLab](https://github.com/will1806e/BioLab). A integração mantém as novas telas, menus e folhas de estilo, adicionando a API e o JavaScript funcional da entrega anterior.

- Cadastro agora recebe e valida CPF (incluindo dígitos verificadores), armazenado sem pontuação e com unicidade.
- Equipamentos usam os novos modais e persistem nome, modelo, número de série e observações. O botão Informações preenche o modal e o histórico pode ser filtrado pela máquina.
- Lotes permitem cadastrar, listar, editar e excluir, com validade, fabricante e associação a analitos. Gerenciar amostras cadastra/exclui analitos; exclusões com vínculos ao lote ou histórico são bloqueadas.
- Registrar Corrida usa lotes cadastrados e filtra os analitos pelo lote. Lotes vencidos ou sem validade não podem receber novas corridas. O servidor repete essas validações.
- Para séries novas, o projeto trata os limites da bula como ±3 DP e calcula o desvio padrão automaticamente. O formulário CSV novo foi preservado, mas está desabilitado até a definição do formato.
- O dashboard mantém os gráficos e o filtro. O histórico mostra lote **e** resultado, além dos registros legados que não possuem resultado numérico.
- O SQL remoto foi ampliado para armazenar séries, resultados e regras. O campo `senha_hash`, antes limitado a 15 caracteres, comporta agora 255.

`css/style.css`, `css/equipamentos.css`, `css/lotes.css` e `css/registrarCorridas.css` são os estilos novos do repositório, sem reescrita. Os complementos do gráfico continuam em `css/index.css`.

## Executar localmente no Windows

Requer Python 3.10+ e MySQL 8+ ou MariaDB 10.4+ (por exemplo, o MySQL do XAMPP). Inicie o serviço do banco na porta 3306. Na pasta do projeto:

```powershell
$senha = Read-Host 'Senha do MySQL local (Enter se vazia)' -AsSecureString
$env:DB_PASSWORD = [System.Net.NetworkCredential]::new('', $senha).Password
py -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m flask --app python/app.py init-db
.\.venv\Scripts\python python/app.py
```

Abra **http://127.0.0.1:5000**. Para usar a prévia do Live Server, mantenha o Flask na porta 5000, abra a pasta `Sistema_biomedicina` sozinha em uma janela do VS Code e clique em **Go Live**. O proxy configurado em `.vscode/settings.json` encaminha `/api` para o Flask. Para conferir, abra `/api/sessao` na porta da prévia. Antes do login, o resultado esperado é HTTP 401 com JSON.

Conexão padrão: host `127.0.0.1`, porta `3306`, usuário `root`, senha vazia, banco `biolab`. `init-db` cria o banco e as tabelas ausentes e adapta os esquemas anteriores; não apaga registros. Não há contas, equipamentos ou corridas fictícios pré-cadastrados. Para um banco existente, faça backup antes da atualização e consulte a seção de migração abaixo.

É possível personalizar com variáveis de ambiente, por exemplo `$env:DB_NAME='biolab'`. O arquivo `.env.example` apenas documenta as opções; não é carregado automaticamente. `SECRET_KEY` é opcional para uso local: sem ela, as sessões expiram ao reiniciar o servidor. Ao abrir outro terminal, defina novamente `DB_PASSWORD` antes de iniciar o Flask. Se o seu Python já tem Flask e PyMySQL, execute `py python/app.py` na pasta do projeto. O Flask escuta em `127.0.0.1`.

## Hospedagem no Vercel

O `app.py` na raiz expõe a aplicação Flask como Vercel Function. O `vercel.json` fixa a região `gru1`, próxima ao banco Neon Postgres. Páginas e API usam a mesma origem, então o navegador continua chamando `/api/...` sem configuração de CORS.

O projeto Vercel precisa das variáveis de produção `DATABASE_URL` e `DATABASE_URL_UNPOOLED` fornecidas pela integração Neon, além de `SECRET_KEY` persistente. O esquema inicial está em `database/schema_postgres.sql` e é criado uma vez com `python -m flask --app python/app.py init-db` sob as variáveis de produção. O inicializador usa `CREATE TABLE IF NOT EXISTS` e não insere contas ou dados demonstrativos. Para executar o comando localmente com o ambiente do projeto vinculado, use `vercel env run -e production -- python -m flask --app python/app.py init-db`.

O Neon criado para a implantação começa vazio: **dados de um MySQL local não são copiados automaticamente**. Para levar dados existentes à nuvem, é necessária uma migração separada e conferida. O arquivo `.env.example` continua descrevendo somente o MySQL local; nunca publique credenciais no repositório.

Depois de conectar o repositório Git ao projeto Vercel, pushes na branch de produção podem gerar novas implantações automaticamente. Sem essa conexão, publique pelo CLI a partir de um checkout limpo.

## Fluxo de uso

1. Abra Cadastro, informe usuário, CPF válido, senha de pelo menos oito caracteres e função; faça login.
2. Cadastre o equipamento, com modelo e número de série. Em Lotes, abra Novo Lote → Gerenciar amostras para cadastrar os analitos; volte e salve o lote com validade e os analitos selecionados.
3. Em Registrar Corrida, informe o resultado, a unidade, o alvo central e os dois limites da bula. Selecione o nível visual de 1 a 3. Números aceitam vírgula decimal.
4. Ao salvar, o Python calcula as regras e grava a corrida em uma transação. O dashboard abre no gráfico correspondente.
5. A mesma combinação **equipamento + analito + lote** continua o gráfico. Alterar qualquer parte cria uma nova série. O formulário identifica os itens pelos IDs do catálogo.
6. Nas corridas seguintes, unidade, alvo e limites vêm da série e permanecem travados. O dashboard permite alterar o nível de visualização sem registrar uma nova corrida.
7. Histórico, irregularidades e indicadores consultam registros reais. Aceitas, alertas e rejeitadas no dashboard referem-se ao dia de São Paulo; alertas recentes exibem as últimas ocorrências de todo o histórico.

O último nível salvo na série realça todos os pontos a partir de ±1, ±2 ou ±3 DP, inclusive a fronteira. O tooltip mostra a classificação original de Westgard de cada corrida. Séries anteriores à mudança mantêm o DP original e começam com o nível visual 2. Irregularidades são ocorrências registradas; ainda não há fluxo de encerramento de ações corretivas.

## Banco e organização

```text
usuarios 1 ── N corridas N ── 1 series N ── 1 equipamentos
```

- `usuarios`: `nome_usu` e CPF únicos, hash de senha e `funcao`. Sessão HTTP com cookie HttpOnly; senhas não ficam no navegador.
- `equipamentos`: `nome_equipamento`, modelo, número de série, observações e estado ativo.
- `analitos`, `lotes` e `lote_analito`: catálogo de analitos e suas associações aos lotes.
- `historico`: preserva o modelo do repositório; novos registros têm `corrida_id` e são gravados na mesma transação dos resultados. Seus status são Normal/Alerta/Não Conformidade, correspondentes a Aceito/Alerta/Rejeitado na análise.
- `series`: chave única composta `(equipamento_id, analito, lote)` e parâmetros fixos de controle.
- `corridas`: resultado, z-score, regras, status, indicador de bula, usuário e instante UTC. A ordem de registro (`id`) determina a sequência de avaliação.

Chaves estrangeiras mantêm os vínculos. A gravação bloqueia o equipamento durante a transação, garantindo que registros concorrentes considerem a corrida anterior e não dupliquem uma série. Consultas utilizam parâmetros SQL. Cada usuário autenticado pode consultar os registros do laboratório; as funções são informativas, sem matriz de permissões nesta etapa.

```text
python/app.py               Rotas, validação, sessões e transações
python/db.py                Conexão MySQL e inicialização
app.py                      Entrada Flask para Vercel
database/schema_postgres.sql Esquema inicial do Neon Postgres
python/migrations.py        Adaptação dos bancos existentes
python/catalog.py           CPF, lotes e analitos
python/quality.py           Cálculos e regras de Westgard
database/schema.sql         Esquema usado pelo inicializador
bd/Banco_biolab.sql         Esquema consolidado para um banco novo
javaScript/app.js           Requisições e funções compartilhadas
javaScript/<página>.js      Comportamento específico de cada HTML
css/index.css               Complementos exclusivos do dashboard
tests/                     Testes de cálculos e integração
```

## Atualização do banco existente

Execute o mesmo comando `init-db` com o servidor da aplicação parado. A migração reconhece:

1. **O SQL novo do repositório** (`usuarios`, `analitos`, `lotes`, `lote_analito`, `equipamentos`, `historico`): amplia os campos, acrescenta índices e tabelas de cálculos e mantém os IDs e registros antigos. Registros de histórico sem resultados são exibidos como legado; não geram pontos de gráfico fictícios nem recebem fuso horário presumido.
2. **A primeira entrega desta implementação**: renomeia `usuarios.nome/cargo` para `nome_usu/funcao` e `equipamentos.nome` para `nome_equipamento`, mantendo as contas e senhas. Reconstitui lotes e analitos das séries existentes e vincula suas corridas ao histórico. Como a primeira versão não guardava validade, os lotes migrados ficam com validade pendente; edite-os em Lotes antes de adicionar corridas.

O inicializador pode ser repetido e preserva os tipos dos IDs existentes (INT ou BIGINT). CPF pode permanecer vazio apenas em contas migradas; novos cadastros exigem CPF válido. Duplicidades de nomes/códigos/CPF no banco antigo interrompem a criação dos índices com mensagem para correção, sem escolher nem excluir registros automaticamente. O MySQL pode confirmar alterações DDL individualmente: mantenha um backup antes de migrar.

Hashes já truncados pelo campo antigo de 15 caracteres não podem ser recuperados. Essas contas precisam ter sua senha redefinida pelo responsável pelo banco; o sistema não aceita texto puro como se fosse hash.

`bd/Banco_biolab.sql` é o esquema consolidado **para banco novo**. Não substitui a migração Python de um banco já criado com o SQL original. Os SQLs de origem foram preservados como fixtures de teste. Não execute o SQL original antigo depois de inicializar a aplicação.

Lotes usados em corridas não podem ser excluídos, ter seu código alterado ou perder analitos vinculados ao histórico. Fabricante e validade podem ser corrigidos. Um lote pode conter vários analitos, cada qual com sua própria série por equipamento. Não há exclusão de resultados nem importação CSV nesta etapa.

## Cálculos e regras implementadas

`z = (resultado − alvo) / desvio padrão`. O desvio deve ser positivo; resultados e referências precisam ser finitos. O dashboard recebe as corridas em JSON de `/api/series/<id>` e usa o Chart.js distribuído com o projeto para desenhar um ponto por corrida. O gráfico mostra alvo e limites de ±1, ±2 e ±3 DP calculados em Python. A média observada e o desvio amostral (`n−1`, quando `n ≥ 2`) são descritivos e **não recalibram os limites**. Ao passar o mouse sobre um ponto, aparecem data, resultado, alerta visual, status e regras de Westgard.

| Regra | Condição | Classificação |
| --- | --- | --- |
| 1₂s | Último resultado além de ±2 DP | Alerta |
| 1₃s | Último resultado além de ±3 DP | Rejeitado |
| 2₂s | Dois consecutivos além de 2 DP do mesmo lado | Rejeitado |
| 4₁s | Quatro consecutivos além de 1 DP do mesmo lado | Rejeitado |
| 10x | Dez consecutivos do mesmo lado do alvo | Rejeitado |

Usa-se a interpretação moderna: 4₁s e 10x não dependem de alerta 1₂s prévio. Os limites são estritos: igualdade não é ultrapassagem. A rejeição tem prioridade sobre alerta, e todas as regras detectadas ficam registradas. Resultados rejeitados continuam no histórico para preservar a sequência; não há reinício automático após ação corretiva nesta etapa.

**R₄s não é aplicada**: o formulário atual tem uma única medição por corrida. Essa regra exige comparação dentro da mesma corrida, não entre corridas sucessivas. Para implementá-la, será necessário modelar múltiplos controles por corrida. Referência: [Westgard — definição das regras e distinção entre interpretações clássica e moderna](https://www.westgard.com/westgard-rules).

A convenção desta aplicação usa mínimo e máximo simétricos em torno do alvo para séries novas. O DP é `(máximo − mínimo) / 6`. Uma faixa de 90 a 110 com alvo 100 resulta em DP de 3,333…. O histórico preserva a indicação “Fora da bula” e a classificação de Westgard.

Em um banco existente, execute `init-db` antes de servir esta versão. O comando adiciona `series.nivel_visual` no MySQL ou no PostgreSQL da Vercel.

## Verificação

```powershell
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest -q
# Integração com o banco disponível nas configurações de conexão:
$env:BIOLAB_TEST_MYSQL='1'
.\.venv\Scripts\python -m pytest -q
```

Os testes de integração criam bancos com prefixo `biolab_test_` e identificadores aleatórios. Não usam o banco de trabalho e não executam exclusões automáticas. Cobrem identidade da série, isolamento das regras, transações concorrentes, validação, autenticação e limites de bula. Sem a variável, a suíte do banco é ignorada explicitamente.

Para conferir a API com Postgres, `BIOLAB_TEST_POSTGRES=1` habilita `tests/test_postgres_live.py`. O teste cria um esquema `qa_` com identificador aleatório no banco indicado por `DATABASE_URL_UNPOOLED`, exercita cadastro, login, catálogos, corrida e consultas, e remove somente esse esquema ao terminar. Execute apenas com credenciais de um banco de teste ou de uma instância controlada.

Validação desta integração: 29 testes automatizados aprovados em MariaDB/XAMPP, incluindo migrações dos dois esquemas, repetição da inicialização, concorrência, CPF, relações lote/analito e proteção de exclusão. Fluxos novos também verificados no navegador Edge, incluindo dashboard em largura móvel. MySQL 8 não foi executado separadamente neste ambiente.
