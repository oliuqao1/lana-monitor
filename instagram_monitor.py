#!/usr/bin/env python3
"""
Instagram Direct Monitor - Lana Estética v2.6
VERSÃO FINAL: OpenAI + Prompt Hardcoded + Funcionando
"""

import os
import sys
import time
import base64
import logging
from pathlib import Path
from openai import OpenAI
from instagrapi import Client
from instagrapi.exceptions import LoginRequired

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

# Configurações
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    log.error("❌ OPENAI_API_KEY não configurada!")
    sys.exit(1)

try:
    ai_client = OpenAI(api_key=OPENAI_API_KEY)
    log.info("✅ OpenAI client inicializado")
except Exception as e:
    log.error(f"❌ Erro ao inicializar OpenAI: {e}")
    sys.exit(1)

IG_USERNAME = os.environ.get("IG_USERNAME", "lana_estetica")
IG_PASSWORD = os.environ.get("IG_PASSWORD", "")
IG_SESSION_FILE = "/tmp/ig_instagrapi_session.json"
IG_SESSION_B64 = os.environ.get("IG_SESSION_B64", "")

POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "30"))

TEST_MODE_USER = os.environ.get("TEST_MODE_USER", "romulooooo,lana_rosangela")
TEST_MODE_USERS = [u.strip().lower() for u in TEST_MODE_USER.split(",") if u.strip()] if TEST_MODE_USER else []

# ─────────────────────────────────────────────────────────────
# SYSTEM PROMPT HARDCODED
# ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Você é a Manu, assistente virtual da Lana Estética, clínica especializada em estética avançada.

INFORMAÇÕES DA CLÍNICA:
- Nome: Lana Estética
- Lema: Estética avançada. Resultado que você sente.
- Responsável: Dra. Lana (Biomédica Esteta)
- Endereço: Avenida Brasil, 1000 - Consolação - São Paulo - SP
- CEP: 01311-100
- Metrô: Consolação (Linha Vermelha)
- Horários: Terça a Sábado 09h às 19h | Domingo e Segunda: Fechado
- WhatsApp: (11) 93257-1982
- Instagram: @lana_estetica

PROCEDIMENTOS E PREÇOS:
1. Radiance Skin - R$ 990,00 (Protocolo exclusivo para melasma e manchas)
2. Microagulhamento - R$ 380,00 (Estimulação de colágeno)
3. Limpeza de Pele - R$ 159,00 (Limpeza profunda e desobstrução)
4. FreeAcne - R$ 990,00 (Protocolo para acne)
5. Regenera - R$ 580,00 (Regeneração celular)
6. Skin Lift - R$ 1.800,00 (Protocolo completo de rejuvenescimento)
7. Botox Terço Superior - R$ 950,00 (3 regiões, 50ui)
8. Botox Full Face - R$ 1.399,00 (Aplicação em todo o rosto)
9. Bioestimulador de Colágeno - R$ 1.200,00 (Estimulação natural de colágeno)
10. Peeling Mar Morto - R$ 480,00 (Renovação profunda com minerais)
11. SkinEyes - Sob consulta (Protocolo exclusivo para região dos olhos)

FLUXO DE AGENDAMENTO:
- NUNCA tente agendar um horário diretamente
- Solicite: nome completo → número de WhatsApp → procedimento de interesse
- Envie essas informações para Dra. Lana via WhatsApp
- Confirme ao cliente: "Em breve entraremos em contato pelo seu WhatsApp para confirmar dia e horário disponíveis. 😊"

REGRAS:
1. Responda com máximo 3-4 frases (é Instagram Direct)
2. Tom profissional, técnico, didático e acolhedor
3. Use no máximo 1-2 emojis por mensagem
4. NUNCA invente informações sobre preços, procedimentos ou horários
5. Se não souber algo, redirecione para WhatsApp: (11) 93257-1982
6. Siga RIGOROSAMENTE o fluxo de agendamento
7. Se cliente pedir para falar com alguém: "Claro! Para falar diretamente com a gente, é só chamar no WhatsApp! 😊"
"""

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
# ESTADO
# ─────────────────────────────────────────────────────────────
conversation_context = {}
processed_messages = set()

# ─────────────────────────────────────────────────────────────
# FUNÇÕES IA
# ─────────────────────────────────────────────────────────────
def is_human_request(text):
    text_lower = text.lower()
    return any(kw in text_lower for kw in HUMAN_KEYWORDS)

def generate_ai_response(thread_id, user_message):
    """Gera resposta usando OpenAI"""
    try:
        if thread_id not in conversation_context:
            conversation_context[thread_id] = []
        
        # Adiciona mensagem do usuário
        conversation_context[thread_id].append({
            "role": "user",
            "content": user_message
        })
        
        # Limita histórico para não gastar muitos tokens
        if len(conversation_context[thread_id]) > 20:
            conversation_context[thread_id] = conversation_context[thread_id][-20:]
        
        # Prepara mensagens com system prompt
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ] + conversation_context[thread_id]
        
        log.info(f"🔄 Chamando OpenAI com {len(messages)} mensagens...")
        
        # Chama OpenAI
        response = ai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            max_tokens=400,
            temperature=0.7,
            timeout=30
        )
        
        ai_text = response.choices[0].message.content
        log.info(f"✅ Resposta recebida: {ai_text[:60]}...")
        
        # Adiciona resposta ao histórico
        conversation_context[thread_id].append({
            "role": "assistant",
            "content": ai_text
        })
        
        return ai_text
        
    except Exception as e:
        log.error(f"❌ Erro ao chamar OpenAI: {e}")
        return "Desculpe, tive um problema técnico. Por favor, entre em contato pelo WhatsApp: (11) 93257-1982"

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
            log.info("✅ Sessão carregada de IG_SESSION_B64")
        except Exception as e:
            log.warning(f"❌ Erro ao decodificar IG_SESSION_B64: {e}")

    if Path(IG_SESSION_FILE).exists():
        try:
            cl.load_settings(IG_SESSION_FILE)
            cl.login(IG_USERNAME, IG_PASSWORD)
            log.info("✅ Sessão carregada com sucesso!")
            cl.dump_settings(IG_SESSION_FILE)
            return cl
        except Exception as e:
            log.warning(f"❌ Sessão inválida: {e}")

    log.error("❌ Nenhuma sessão válida encontrada.")
    raise Exception("Sessão não encontrada.")

# ─────────────────────────────────────────────────────────────
# PROCESSAMENTO DE MENSAGENS
# ─────────────────────────────────────────────────────────────
def process_message(cl, thread_id, thread_title, user_id, message_text, message_id):
    log.info(f"📨 Mensagem de {thread_title}: {message_text[:50]}")

    # Verifica se é pedido de atendimento humano
    if is_human_request(message_text):
        response = "Claro! Para falar diretamente com a gente, é só chamar no WhatsApp! 😊 (11) 93257-1982"
        try:
            cl.direct_send(response, thread_ids=[thread_id])
            log.info(f"✅ Atendimento humano → {thread_title}")
        except Exception as e:
            log.error(f"❌ Erro ao enviar: {e}")
        return

    # Gera resposta com OpenAI
    ai_response = generate_ai_response(thread_id, message_text)

    # Envia resposta
    try:
        cl.direct_send(ai_response, thread_ids=[thread_id])
        log.info(f"✅ Resposta enviada para {thread_title}")
    except Exception as e:
        log.error(f"❌ Erro ao enviar: {e}")

# ─────────────────────────────────────────────────────────────
# LOOP PRINCIPAL
# ─────────────────────────────────────────────────────────────
def main():
    log.info("🚀 Instagram Monitor v2.6 - Lana Estética")
    log.info("✅ Prompt HARDCODED carregado")
    log.info("✅ OpenAI integrado")
    
    if TEST_MODE_USERS:
        log.info(f"⚠️  MODO DE TESTE: respondendo apenas a: {', '.join('@' + u for u in TEST_MODE_USERS)}")

    try:
        cl = create_ig_client()
    except Exception as e:
        log.error(f"❌ Falha ao criar cliente Instagram: {e}")
        sys.exit(1)

    my_user_id = str(cl.user_id)
    log.info(f"✅ Logado como: {IG_USERNAME} (ID: {my_user_id})")
    log.info(f"✅ Bot pronto para responder!")

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

                # Modo de teste
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
                process_message(cl, thread_id, thread_title, sender_id, message_text.strip(), msg_id)
                time.sleep(2)

            if len(processed_messages) > 1000:
                processed_messages.clear()

        except LoginRequired:
            log.warning("⚠️  Sessão expirada, fazendo novo login...")
            try:
                cl.login(IG_USERNAME, IG_PASSWORD)
                cl.dump_settings(IG_SESSION_FILE)
                log.info("✅ Re-login realizado!")
            except Exception as e:
                log.error(f"❌ Re-login falhou: {e}")

        except KeyboardInterrupt:
            log.info("🛑 Monitor encerrado pelo usuário.")
            break

        except Exception as e:
            log.error(f"❌ Erro no loop: {e}")

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
