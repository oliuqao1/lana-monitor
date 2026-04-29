# 🌸 Lana Estética — Monitor Instagram Direct

Bot de atendimento automático para o Instagram Direct da Lana Estética.
Usa IA (GPT-4.1-mini) para responder clientes 24/7 sem ManyChat.

---

## Deploy no Railway.app

### 1. Criar conta no Railway
Acesse [railway.app](https://railway.app) e crie uma conta gratuita.

### 2. Criar novo projeto
- Clique em **New Project**
- Escolha **Deploy from GitHub repo** (ou **Empty Project** para upload manual)

### 3. Configurar variáveis de ambiente
No painel do Railway, vá em **Variables** e adicione:

| Variável | Valor |
|---|---|
| `IG_USERNAME` | `lana_estetica` |
| `IG_PASSWORD` | `(senha do Instagram)` |
| `IG_SESSION_B64` | `(conteúdo do arquivo session_b64.txt)` |
| `OPENAI_API_KEY` | `(sua chave OpenAI)` |
| `TELEGRAM_BOT_TOKEN` | `8798305087:AAEUmxbeZJA8B1EqCyWQv72cxqtYmX_Lczo` |
| `TELEGRAM_CHAT_ID` | `7959934326` |
| `TEST_MODE_USER` | `romulooooo` (modo teste) ou deixar vazio para todos |
| `POLL_INTERVAL` | `30` |

### 4. Deploy
O Railway detecta o `Dockerfile` automaticamente e faz o build.
Clique em **Deploy** e aguarde o build (~2-3 minutos).

### 5. Verificar logs
Clique no serviço → **Logs** para ver o monitor rodando em tempo real.

---

## Renovar sessão do Instagram

A sessão do Instagram expira periodicamente (~30-60 dias).
Quando isso acontecer:

1. Abra uma sessão no Manus
2. Execute o login: `python3 /home/ubuntu/login_totp.py <codigo_totp>`
3. Gere o novo `IG_SESSION_B64`:
   ```
   python3 -c "import base64; print(base64.b64encode(open('ig_instagrapi_session.json').read().encode()).decode())"
   ```
4. Atualize a variável `IG_SESSION_B64` no Railway
5. Redeploy automático

---

## Modo de teste vs. Produção

- **Modo teste**: `TEST_MODE_USER=romulooooo` — responde apenas ao @romulooooo
- **Produção**: `TEST_MODE_USER=` (vazio) — responde a todos os clientes

---

## Arquivos

| Arquivo | Descrição |
|---|---|
| `instagram_monitor.py` | Script principal do monitor |
| `Dockerfile` | Configuração do container |
| `requirements.txt` | Dependências Python |
| `railway.toml` | Configuração do Railway |
| `session_b64.txt` | Sessão do Instagram em base64 (não commitar!) |
