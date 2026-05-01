#!/usr/bin/env python3
"""
Instagram Direct Monitor - Lana Estética v2.5 TEST
VERSÃO SIMPLIFICADA: Responde com mensagem fixa para debug
"""

import os
import sys
import time
import base64
import logging
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import LoginRequired

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

# Configurações
IG_USERNAME = os.environ.get("IG_USERNAME", "lana_estetica")
IG_PASSWORD = os.environ.get("IG_PASSWORD", "")
IG_SESSION_FILE = "/tmp/ig_instagrapi_session.json"
IG_SESSION_B64 = os.environ.get("IG_SESSION_B64", "")

POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "30"))

TEST_MODE_USER = os.environ.get("TEST_MODE_USER", "romulooooo,lana_rosangela")
TEST_MODE_USERS = [u.strip().lower() for u in TEST_MODE_USER.split(",") if u.strip()] if TEST_MODE_USER else []

# Estado
processed_messages = set()

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
# LOOP PRINCIPAL
# ─────────────────────────────────────────────────────────────
def main():
    log.info("🚀 Instagram Monitor v2.5 TEST - Modo Simplificado")
    
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
            log.info(f"📨 Checando {len(threads)} threads...")

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
                        log.info(f"⏭️  Ignorando thread (não é usuário de teste): {thread_title}")
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
                
                # RESPOSTA FIXA DE TESTE
                test_response = """✅ BOT FUNCIONANDO!

Olá! Sou a Manu, assistente da Lana Estética.

📋 Procedimentos disponíveis:
• Radiance Skin - R$ 990
• Microagulhamento - R$ 380
• Limpeza de Pele - R$ 159
• FreeAcne - R$ 990
• Regenera - R$ 580
• Skin Lift - R$ 1.800
• Botox Terço Superior - R$ 950
• Botox Full Face - R$ 1.399
• Bioestimulador - R$ 1.200
• Peeling Mar Morto - R$ 480
• SkinEyes - Sob consulta

Qual procedimento te interessa? 😊"""

                log.info(f"📨 Mensagem de {thread_title}: {message_text[:50]}")
                
                try:
                    cl.direct_send(test_response, thread_ids=[thread_id])
                    log.info(f"✅ Resposta enviada para {thread_title}")
                except Exception as e:
                    log.error(f"❌ Erro ao enviar: {e}")

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
