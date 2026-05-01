#!/usr/bin/env python3
"""
Instagram Direct Monitor - Lana Estética v2.2
VERSÃO CORRIGIDA: Carrega JSON e usa como fonte de verdade
"""

import os
import sys
import json
import time
import base64
import logging
import requests
from pathlib import Path
from openai import OpenAI
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired, TwoFactorRequired

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

# Configurações
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ai_client = OpenAI(api_key=OPENAI_API_KEY)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8798305087:AAEUmxbeZJA8B1EqCyWQv72cxqtYmX_Lczo")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "7959934326")

IG_USERNAME = os.environ.get("IG_USERNAME", "lana_estetica")
IG_PASSWORD = os.environ.get("IG_PASSWORD", "")
IG_SESSION_FILE = "/tmp/ig_instagrapi_session.json"
IG_SESSION_B64 = os.environ.get("IG_SESSION_B64", "")

POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "30"))

TEST_MODE_USER = os.environ.get("TEST_MODE_USER", "romulooooo,lana_rosangela")
TEST_MODE_USERS = [u.strip().lower() for u in TEST_MODE_USER.split(",") if u.strip()] if TEST_MODE_USER else []

KB_URL = "https://lanaestetica.com.br/_kb-internal.json"
KB = None

# ─────────────────────────────────────────────────────────────
# CARREGAR KNOWLEDGE BASE
# ─────────────────────────────────────────────────────────────
def load_knowledge_base():
    """Carrega o JSON da KB uma única vez na inicialização"""
    try:
        log.info(f"🔄 Carregando KB de {KB_URL}...")
        response = requests.get(KB_URL, timeout=10)
        response.raise_for_status()
        kb = response.json()
        log.info(f"✅ KB carregada com sucesso!")
        log.info(f"📋 Versão: {kb.get('versao', 'desconhecida')}")
        log.info(f"📋 Procedimentos: {len(kb.get('precos', {}))}")
        return kb
    except Exception as e:
        log.error(f"❌ Erro ao carregar KB: {e}")
        return None

# ─────────────────────────────────────────────────────────────
# CONSTRUIR SYSTEM PROMPT DINÂMICO
# ─────────────────────────────────────────────────────────────
def build_system_prompt(kb):
    """Constrói o prompt do sistema com base no JSON da KB"""
    if not kb:
        log.error("KB não carregada. Usando prompt padrão.")
        return get_default_system_prompt()
    
    # Extrair informações da KB
    clinica = kb.get("clinica", {})
    contato = kb.get("contato", {})
    localizacao = kb.get("localizacao", {})
    horarios = kb.get("horarios", {})
    agendamento = kb.get("agendamento", {})
    precos = kb.get("precos", {})
    
    # Formatar preços para exibição
    precos_formatados = []
    for proc_key, proc_info in precos.items():
        if proc_key.startswith("_"):
            continue
        nome = proc_info.get("nome", "")
        preco = proc_info.get("preco", "")
        detalhes = proc_info.get("detalhes", "")
        precos_formatados.append(f"• {nome}: {preco} ({detalhes})")
    
    precos_str = "\n".join(precos_formatados)
    
    # Extrair instruções de agendamento
    instrucoes_agendamento = agendamento.get("instrucao_agendamento_bot", {})
    passos_agendamento = "\n".join(instrucoes_agendamento.get("passos", []))
    
    prompt = f"""Você é a Manu, assistente virtual da Lana Estética, clínica especializada em estética avançada.

╔═══════════════════════════════════════════════════════════════╗
║              INFORMAÇÕES DA CLÍNICA (FONTE: JSON)             ║
╚═══════════════════════════════════════════════════════════════╝

CLÍNICA: {clinica.get('nome', 'Lana Estética')}
Lema: {clinica.get('lema', 'Estética avançada. Resultado que você sente.')}
Responsável: Dra. Lana ({clinica.get('titulo', 'Biomédica Esteta')})

LOCALIZAÇÃO:
Endereço: {localizacao.get('endereco', '')}, {localizacao.get('bairro', '')} - {localizacao.get('cidade', '')}
CEP: {localizacao.get('cep', '')}
Metrô: {localizacao.get('metro', {}).get('estacao', '')} ({localizacao.get('metro', {}).get('linha', '')})

HORÁRIOS:
Terça a Sábado: {horarios.get('terca', '09h às 19h')}
Domingo e Segunda: Fechado

CONTATO:
WhatsApp: {contato.get('whatsapp', '')}
Instagram: {contato.get('instagram', '')}

╔═══════════════════════════════════════════════════════════════╗
║                    PROCEDIMENTOS E PREÇOS                     ║
╚═══════════════════════════════════════════════════════════════╝

{precos_str}

╔═══════════════════════════════════════════════════════════════╗
║                  FLUXO DE AGENDAMENTO                         ║
╚═══════════════════════════════════════════════════════════════╝

REGRA CRÍTICA: {instrucoes_agendamento.get('regra', 'NUNCA tentar agendar um horário diretamente.')}

Passos para agendamento:
{passos_agendamento}

╔═══════════════════════════════════════════════════════════════╗
║                    REGRAS DE COMPORTAMENTO                    ║
╚═══════════════════════════════════════════════════════════════╝

1. FONTE DE VERDADE: Todas as informações acima vêm do JSON. NUNCA invente informações.
2. RESPOSTAS CURTAS: Máximo 3-4 frases. É Instagram Direct.
3. TOM: Profissional, técnico, didático e acolhedor. Use no máximo 1-2 emojis.
4. AGENDAMENTO: Siga RIGOROSAMENTE o fluxo acima.
5. ATENDIMENTO HUMANO: Se cliente pedir para falar com alguém, responda:
   "Claro! Para falar diretamente com a gente, é só chamar no WhatsApp! 😊 {contato.get('whatsapp_link', 'https://wa.me/5511932571982')}"
6. NUNCA INVENTE: Não crie informações sobre procedimentos, preços ou horários que não estejam no JSON acima.
"""
    
    return prompt

def get_default_system_prompt():
    """Prompt padrão caso KB não carregue"""
    return """Você é a Manu, assistente virtual da Lana Estética.
Responda de forma profissional e redirecione para WhatsApp: https://wa.me/5511932571982"""

# ─────────────────────────────────────────────────────────────
# PALAVRAS-CHAVE PARA ATENDIMENTO HUMANO
# ─────────────────────────────────────────────────────────────
HUMAN_KEYWORDS = [
    "falar com alguém", "falar com uma pessoa", "atendimento humano",
    "quero falar com", "preciso falar com", "falar com a lana",
    "falar com a dra", "atendente", "humano", "pessoa real",
    "falar com vocês", "chamar alguém", "quero atendimento"
]

# ─────────────────────────────────────────────────────────────
# ESTADO DA CONVERSA
# ─────────────────────────────────────────────────────────────
conversation_context = {}
processed_messages = set()

# ─────────────────────────────────────────────────────────────
# FUNÇÕES TELEGRAM
# ─────────────────────────────────────────────────────────────
def notify_telegram(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
            timeout=5
        )
    except Exception as e:
        log.error(f"Telegram error: {e}")

# ─────────────────────────────────────────────────────────────
# FUNÇÕES IA
# ─────────────────────────────────────────────────────────────
def is_human_request(text):
    text_lower = text.lower()
    return any(kw in text_lower for kw in HUMAN_KEYWORDS)

def generate_ai_response(thread_id, user_message, system_prompt):
    if thread_id not in conversation_context:
        conversation_context[thread_id] = []
    
    conversation_context[thread_id].append({"role": "user", "content": user_message})
    
    if len(conversation_context[thread_id]) > 20:
        conversation_context[thread_id] = conversation_context[thread_id][-20:]
    
    messages = [{"role": "system", "content": system_prompt}] + conversation_context[thread_id]
    
    try:
        response = ai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            max_tokens=400,
            temperature=0.7
        )
        ai_text = response.choices[0].message.content
        conversation_context[thread_id].append({"role": "assistant", "content": ai_text})
        return ai_text
    except Exception as e:
        log.error(f"OpenAI error: {e}")
        return "Desculpe, tive um problema técnico. Por favor, entre em contato pelo WhatsApp: https://wa.me/5511932571982"

# ─────────────────────────────────────────────────────────────
# INSTAGRAM CLIENT
# ─────────────────────────────────────────────────────────────
def create_ig_client():
    cl = Client()
    cl.delay_range = [1, 3]

    if IG_SESSION_B64:
        try:
            session_json = base64.b64decode(IG_SESSION_B64).decode("utf-8")
            with open(IG_SESSION_FILE, "w") as f:
                f.write(session_json)
            log.info("Sessão carregada da variável de ambiente IG_SESSION_B64")
        except Exception as e:
            log.warning(f"Erro ao decodificar IG_SESSION_B64: {e}")

    if Path(IG_SESSION_FILE).exists():
        try:
            cl.load_settings(IG_SESSION_FILE)
            cl.login(IG_USERNAME, IG_PASSWORD)
            log.info("Sessão carregada com sucesso!")
            cl.dump_settings(IG_SESSION_FILE)
            return cl
        except Exception as e:
            log.warning(f"Sessão inválida: {e}")

    log.error("Nenhuma sessão válida. Configure IG_SESSION_B64 ou execute login_totp.py primeiro.")
    raise Exception("Sessão não encontrada.")

def process_message(cl, thread_id, thread_title, user_id, message_text, message_id, system_prompt):
    log.info(f"[MSG] Thread: {thread_title} | Msg: {message_text[:60]}")

    if is_human_request(message_text):
        response = f"Claro! Para falar diretamente com a gente, é só chamar no WhatsApp! 😊 https://wa.me/5511932571982"
        try:
            cl.direct_send(response, thread_ids=[thread_id])
            log.info(f"[SENT] Atendimento humano → {thread_title}")
        except Exception as e:
            log.error(f"Send error: {e}")
        notify_telegram(
            f"🚨 *ATENDIMENTO HUMANO SOLICITADO*\n\n"
            f"👤 *Cliente:* {thread_title}\n"
            f"💬 *Mensagem:* {message_text}\n\n"
            f"_Avise para entrar em contato pelo WhatsApp._"
        )
        return

    ai_response = generate_ai_response(thread_id, message_text, system_prompt)

    if "[HUMANO]" in ai_response:
        ai_response = ai_response.replace("[HUMANO]", "").strip()
        notify_telegram(
            f"🚨 *ATENDIMENTO HUMANO SOLICITADO*\n\n"
            f"👤 *Cliente:* {thread_title}\n"
            f"💬 *Mensagem:* {message_text}\n\n"
            f"_Avise para entrar em contato._"
        )

    try:
        cl.direct_send(ai_response, thread_ids=[thread_id])
        log.info(f"[SENT] → {thread_title}: {ai_response[:60]}...")
    except Exception as e:
        log.error(f"Send error: {e}")

# ─────────────────────────────────────────────────────────────
# LOOP PRINCIPAL
# ─────────────────────────────────────────────────────────────
def main():
    global KB
    
    log.info("🚀 Instagram Monitor v2.2 iniciado - Lana Estética")
    
    # Carregar KB na inicialização
    KB = load_knowledge_base()
    log.info(f"✅ KB Global carregada: {KB is not None}")
    if not KB:
        log.error("❌ Falha ao carregar KB. Encerrando.")
        notify_telegram("❌ *Monitor falhou ao iniciar*\nErro: Não consegui carregar o JSON da KB")
        sys.exit(1)
    
    # Construir prompt dinâmico com base na KB
    log.info(f"🔨 Construindo prompt com KB...")
    system_prompt = build_system_prompt(KB)
    log.info(f"✅ Prompt construído com sucesso (tamanho: {len(system_prompt)} chars)")
    
    if TEST_MODE_USER:
        log.info(f"⚠️  MODO DE TESTE: respondendo apenas a: {', '.join('@' + u for u in TEST_MODE_USERS)}")

    try:
        cl = create_ig_client()
    except Exception as e:
        log.error(f"Falha ao criar cliente Instagram: {e}")
        notify_telegram(f"❌ *Monitor falhou ao iniciar*\nErro: {str(e)[:100]}")
        sys.exit(1)

    my_user_id = str(cl.user_id)
    log.info(f"Logado como: {IG_USERNAME} (ID: {my_user_id})")
    notify_telegram(
        f"✅ *Monitor do Instagram iniciado! (v2.2)*\n"
        f"Conta: @{IG_USERNAME}\n"
        f"KB: Carregada de {KB_URL}\n"
        f"{'⚠️ MODO TESTE: apenas ' + ', '.join('@' + u for u in TEST_MODE_USERS) if TEST_MODE_USERS else '✅ Respondendo a todos os clientes.'}"
    )

    while True:
        try:
            threads = cl.direct_threads(amount=20)

            for thread in threads:
                thread_id = str(thread.id)
                thread_title = thread.thread_title or "Desconhecido"

                if not thread.messages:
                    continue

                last_msg = thread.messages[0]
                msg_id = str(last_msg.id)

                if msg_id in processed_messages:
                    continue

                sender_id = str(last_msg.user_id)
                if sender_id == my_user_id:
                    processed_messages.add(msg_id)
                    continue

                # Modo de teste: ignorar threads que não são do usuário de teste
                if TEST_MODE_USERS:
                    thread_users = [u.username.lower() for u in thread.users]
                    if not any(tu in thread_users for tu in TEST_MODE_USERS):
                        processed_messages.add(msg_id)
                        continue

                if last_msg.item_type != "text":
                    processed_messages.add(msg_id)
                    continue

                message_text = last_msg.text or ""
                if not message_text.strip():
                    processed_messages.add(msg_id)
                    continue

                processed_messages.add(msg_id)
                process_message(cl, thread_id, thread_title, sender_id, message_text.strip(), msg_id, system_prompt)
                time.sleep(2)

            if len(processed_messages) > 1000:
                processed_messages.clear()

        except LoginRequired:
            log.warning("Sessão expirada, fazendo novo login...")
            try:
                cl.login(IG_USERNAME, IG_PASSWORD)
                cl.dump_settings(IG_SESSION_FILE)
                log.info("Re-login realizado!")
            except Exception as e:
                log.error(f"Re-login falhou: {e}")
                notify_telegram(f"⚠️ *Sessão do Instagram expirou*\nErro: {str(e)[:100]}")

        except KeyboardInterrupt:
            log.info("Monitor encerrado pelo usuário.")
            break

        except Exception as e:
            log.error(f"Loop error: {e}")

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
