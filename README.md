# ObservAR — Flask + biometria facial

ObservAR é uma aplicação para consulta controlada de dados públicos de qualidade do ar provenientes do MonitorAr. O frontend foi convertido de um protótipo React/TypeScript para Flask, Jinja2, HTML, CSS e JavaScript simples. **Nenhum dado oficial é distribuído no projeto.**

## O que havia no ZIP
O protótipo usa Vite 8, React 19, TypeScript, Tailwind CSS 4, `lucide-react` e `recharts`. As páginas/componentes principais eram `Login`, `Sidebar`, `Dashboard`, `DataTable`, `RecordDetail`, `RecordForm`, `MapView`, `Settings` e `DesignSystem`. O estado, a navegação e os dados eram locais no React. Login e biometria eram demonstrativos (senha fixa e `setTimeout`); tabelas, mapa e auditoria continham arrays fictícios. A identidade usa verdes/azuis, Nunito/DM Mono, cards claros, sidebar verde escura e layout responsivo.

## Conversão
A aplicação final não executa Node, React ou TypeScript. JSX virou templates Jinja2; sidebar virou include; estado de autenticação virou sessão Flask; tabelas usam consultas SQLAlchemy; permissões são verificadas em decorators no backend; câmera usa `getUserMedia`; mapa usa Leaflet/OpenStreetMap. O CSS convencional reproduz os tokens visuais do protótipo. O mapa usa CDN apenas para Leaflet/tiles e é não essencial; para uma demonstração totalmente offline, baixe Leaflet e hospede os assets em `static/`.

## Instalação
```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```
Para reconhecimento real, o backend padrão usa `face_recognition` (embeddings de 128 dimensões) e OpenCV para detecção inicial. Essa biblioteca pode exigir CMake/dlib e toolchain nativo:
```bash
pip install face-recognition
```
A escolha privilegia armazenamento de representação biométrica em vez de fotografia. Se a dependência não puder ser instalada, a aplicação **falha de forma explícita** na etapa biométrica; não há aprovação simulada em produção. Os testes automatizados mockam somente a comparação facial.

## MySQL
Crie um banco UTF-8 e um usuário com privilégios apenas sobre ele. Configure `DATABASE_URL` no `.env`, por exemplo:
`mysql+pymysql://usuario:senha@127.0.0.1:3306/monitorar_aps?charset=utf8mb4`.
Depois:
```bash
python scripts/criar_banco.py
python scripts/criar_usuarios_demo.py
```
As credenciais de desenvolvimento criadas pelo segundo script têm senha `TroqueEstaSenha123!`; altere-a antes da apresentação. Em evolução de schema, recomenda-se adicionar Flask-Migrate/Alembic; esta entrega inclui criação idempotente via `db.create_all()`.

## Execução
```bash
python app.py
```
Abra `http://127.0.0.1:5000`. O login exige senha e, em seguida, biometria facial. Um administrador pode cadastrar a referência em **Usuários → Cadastrar face**.

## Níveis
- **1 — Usuário geral:** dashboard, medições resumidas, estações e mapa.
- **2 — Responsável técnico:** nível 1 + detalhes técnicos e análises internas.
- **3 — Autoridade administrativa:** tudo + usuários, cadastro biométrico e auditoria.

As análises internas são rotuladas como conteúdo da própria aplicação, não como informação oficial MonitorAr.

## Importação MonitorAr
Baixe o CSV oficial separadamente e execute:
```bash
python scripts/importar_monitorar.py dados/arquivo.csv --sep "," --encoding utf-8
```
Filtros opcionais: `--municipio`, `--estacao`, `--inicio`, `--fim`. O importador valida colunas obrigatórias, converte datas/números, aceita colunas opcionais ausentes e impede duplicação por SHA-256 de **estação + parâmetro + data/hora + fonte**. Essa chave é uma hipótese documentada e deve ser revista contra a granularidade do arquivo anual antes de uso definitivo.

## Segurança
Senhas usam hash Werkzeug; cookies são HttpOnly/SameSite; sessão expira; formulários usam token CSRF simples; autorização é feita nas rotas; falhas de senha/biometria e acessos negados são auditados. Fotos, senhas e templates faciais não são escritos em logs. Para produção, adicione HTTPS, rotação de chaves, rate limiting persistente, CSP e proteção/criptografia do template biométrico em repouso.

## Testes
```bash
pytest -q
```
Os testes usam SQLite em memória para isolamento e cobrem senha válida/incorreta, usuário sem biometria, biometria aprovada/divergente via mock, níveis 1/2/3, URL protegida, CSV válido, colunas faltantes, data inválida e duplicidade. Testes físicos de câmera e acurácia do modelo dependem de hardware/modelo real e não são automatizados.

## Limitações conhecidas
`face_recognition` é opcional porque dlib pode ser difícil de instalar em alguns ambientes. Não foi anexado CSV oficial, portanto não foi feita importação real nem são exibidos números fictícios como oficiais. Leaflet/tiles dependem de rede na configuração atual. O cadastro/gestão completa de contas (criação/edição de perfil pela UI) pode ser ampliado; a base de modelos e autorização já está pronta.


## Importação administrativa

Usuários de nível 3 podem acessar **Importação de dados** no menu lateral e enviar
arquivos CSV da base MonitorAr diretamente pelo ObservAR.

Antes do primeiro uso em um banco já existente, execute:

```powershell
python scripts/atualizar_banco_importacao.py
```

A importação usa lotes de 1.000 registros por padrão, calcula SHA-256 do arquivo
e mantém histórico de execução. Registros de medição continuam protegidos pela
chave `chave_importacao`, que possui restrição `UNIQUE` no banco.

Configurações opcionais no `.env`:

```text
IMPORT_CHUNK_SIZE=1000
IMPORT_MAX_FILE_MB=1024
```
