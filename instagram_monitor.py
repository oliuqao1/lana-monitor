#!/usr/bin/env python3
"""
Instagram Direct Monitor - Lana Estética
Monitora o Direct do Instagram e responde automaticamente com IA.
Usa instagrapi (API mobile) para leitura e envio de mensagens.
Sem ManyChat, sem limitação de 24h.
Deploy: Railway.app
"""

import os
import sys
import json
import time
import base64
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from openai import OpenAI
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired, TwoFactorRequired

# ─────────────────────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

# OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ai_client = OpenAI(api_key=OPENAI_API_KEY)

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8798305087:AAEUmxbeZJA8B1EqCyWQv72cxqtYmX_Lczo")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "7959934326")

# CliniSite
CLINISITE_API = "https://clini.site/api/clini-hub/available-hours/18942"
CLINISITE_PROCEDURE_ID = "1279352"

# Instagram credentials
IG_USERNAME = os.environ.get("IG_USERNAME", "lana_estetica")
IG_PASSWORD = os.environ.get("IG_PASSWORD", "")
IG_SESSION_FILE = "/tmp/ig_instagrapi_session.json"
# Sessão em base64 (para passar como variável de ambiente no Railway)
IG_SESSION_B64 = os.environ.get("IG_SESSION_B64", "")

# Polling
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "30"))

# Modo de teste: responder apenas a este usuário (deixar vazio para responder a todos)
TEST_MODE_USER = os.environ.get("TEST_MODE_USER", "")

# ─────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Você é a Manu, assistente virtual da Lana Estética, clínica especializada em estética avançada localizada em São Paulo.

SOBRE A CLÍNICA:
- Nome: Lana Estética
- Responsável: Dra. Lana (biomédica esteta)
- Endereço: Rua Salvador Simões, 1158, Alto do Ipiranga - São Paulo
- A 300 metros da estação de metrô Alto do Ipiranga (Linha Verde)
- Link Maps: https://goo.gl/maps/YsQaH3eqGJgTVpm76
- Horário: Terça a Sábado, das 09h às 19h
- WhatsApp: (11) 93257-1982 | https://wa.me/5511932571982

FORMAS DE PAGAMENTO (todos os procedimentos):
Pix, débito, crédito em até 6x sem juros.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROCEDIMENTO: RADIANCE SKIN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUANDO USAR: Qualquer menção a manchas, melasma, mancha no rosto, mancha de acne, mancha de medicamento → indique o Radiance Skin.

COMPILADO PARA PRIMEIRO CONTATO (quando cliente perguntar sobre Radiance Skin ou manchas):
✨ RADIANCE SKIN — Lana Estética

O Radiance Skin é o nosso protocolo EXCLUSIVO para tratamento e controle de manchas resistentes. Desenvolvido e aplicado pela Dra. Lana, biomédica esteta especialista em tratamentos faciais.

🔍 Foco principal:
Melasma, manchas solares, manchas de acne e manchas causadas por medicamentos.

🌟 De brinde, sua pele também:
• Fica mais luminosa, com viço e uniforme
• Perde o efeito casca de laranja
• Tem flacidez e linhas de expressão reduzidas
• Oleosidade e poros dilatados controlados

📌 Como funciona:
É feito um plano personalizado e eficaz pensado especificamente para você — seu tipo de pele, seu estilo de vida, sua rotina. Aqui não existe plano genérico. Cada pessoa é única e o tratamento é feito assim.

💰 Investimento:
• Sessão avulsa: R$480
• Pacote 3 sessões (recomendado): R$990 — economia de R$450!

Quer saber se o Radiance Skin é para você? Me conta um pouquinho sobre as suas manchas 😊

DETALHES DO PROTOCOLO:
- Primeira sessão: LED terapia, peeling hidratante, skincare personalizado (~1h, pode ser mais longa pela avaliação inicial)
- Sessões seguintes: peelings progressivos, suaves, sem agredir a pele
- Tratamento de dentro para fora: ativos via oral + skincare em casa adaptado ao orçamento
- Resultado: pele mais fina, iluminada, melasma controlado, rejuvenescimento geral
- Intervalo entre sessões: definido pela Dra. Lana conforme evolução

CONTRAINDICAÇÕES: Gestantes, uso de isotretinoína (Roacutan), pele muito sensível no momento.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESTRATÉGIA DE VENDAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MENTALIDADE: Essa cliente provavelmente convive com o melasma há anos. Já tentou produtos, já se frustrou, talvez já desistiu de tratar de verdade. Sua missão é fazer ela entender que o Radiance Skin é o tratamento definitivo — não mais um produto qualquer. Quando ela entender isso, ela mesma cria a urgência.

OBJEÇÃO DE PREÇO:
- Não é tratamento genérico — é protocolo feito para ela, pensado para ter resultado
- O que sai mais caro é continuar tentando produto aqui e ali sem resultado, com risco de efeito rebote
- É um investimento: menos gasto com maquiagem, mais confiança, qualidade de vida
- Cabe em até 6x sem juros

CLIENTE QUE SUMIU: Retome com mensagem leve: "Oi! Ficou alguma dúvida sobre o Radiance Skin? Estou aqui para te ajudar. 😊"

FUNIL DE PREÇO SAZONAL: O Radiance Skin é permanente. A urgência vem do preço promocional por tempo limitado, não de avaliação gratuita.

IMPACTO EMOCIONAL: A cliente que deviava o olhar, recebia perguntas constrangedoras sobre a mancha, gastava com maquiagem para cobrir — depois do tratamento voltou a olhar no olho das pessoas, se sentiu mais jovem e confiante. Use isso com empatia.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLUXO DE AGENDAMENTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OBJETIVO: Todos os atendimentos devem ser conduzidos para o AGENDAMENTO DO TRATAMENTO (não avaliação gratuita). O compromisso começa desde o agendamento.

Quando cliente quiser agendar:
1. Pergunte o nome completo
2. Pergunte o WhatsApp
3. Pergunte: prefere manhã ou tarde?
4. Diga que vai verificar os horários disponíveis (o sistema faz isso automaticamente)
5. Quando receber os horários, apresente as opções
6. Confirme o horário escolhido

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGRAS IMPORTANTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Respostas CURTAS e DIRETAS (máximo 3-4 frases). É Instagram Direct.
- Tom profissional, técnico, didático e acolhedor.
- Use no máximo 1-2 emojis por mensagem.
- Nunca invente informações, especialmente sobre horários disponíveis.
- Todos os atendimentos devem ser conduzidos para o AGENDAMENTO DO TRATAMENTO.
- Qualquer menção a manchas, melasma → indique o Radiance Skin.

MENSAGENS DIRECIONADAS À DRA. LANA:
Quando a cliente falar diretamente com a Dra. Lana, responda de forma calorosa como assistente, agradeça em nome da Dra. Lana e redirecione para o atendimento. NÃO diga que é IA.

ATENDIMENTO HUMANO / FALAR COM ALGUÉM:
Se a cliente pedir para falar com uma pessoa, humano, atendente, Lana, Dra. → responda:
"Claro! Para falar diretamente com a gente, é só chamar no WhatsApp! 😊 https://wa.me/5511932571982"
E inclua [HUMANO] no início da resposta para notificar o sistema.
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
# FUNÇÕES CLINISITE
# ─────────────────────────────────────────────────────────────
def get_available_slots(period="tarde"):
    MANHA_PREFS = ["09:00", "09:30", "10:00", "10:30", "08:30", "08:00", "11:00", "11:30"]
    TARDE_POS_ALMOCO = ["13:30", "14:00", "14:30", "15:00"]
    TARDE_FINAL = ["17:00", "17:30", "18:00", "18:30", "16:30", "16:00"]
    today = datetime.now()
    dates_to_check = []
    for i in range(1, 14):
        d = today + timedelta(days=i)
        if d.weekday() != 6:
            dates_to_check.append(d)
        if len(dates_to_check) >= 10:
            break
    results = []
    dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    try:
        for d in dates_to_check:
            date_str = d.strftime("%Y-%m-%d")
            url = f"{CLINISITE_API}?procedure_id={CLINISITE_PROCEDURE_ID}&iso_date={date_str}&procedure_from_event=0"
            resp = requests.get(url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://clini.site/lanaeastetica"
            })
            if resp.status_code != 200:
                continue
            all_slots = resp.json()
            if not all_slots:
                continue
            dia_nome = dias_semana[d.weekday()]
            dia_fmt = f"{dia_nome}, {d.strftime('%d/%m')}"
            if period.lower() in ["manha", "manhã"]:
                chosen = next((s for s in MANHA_PREFS if s in all_slots), None)
                if chosen:
                    results.append(f"• {dia_fmt} às {chosen}")
                    if len(results) >= 2:
                        break
            else:
                slot_almoco = next((s for s in TARDE_POS_ALMOCO if s in all_slots), None)
                slot_final = next((s for s in TARDE_FINAL if s in all_slots), None)
                slots_dia = []
                if slot_almoco:
                    slots_dia.append(slot_almoco)
                if slot_final:
                    slots_dia.append(slot_final)
                if slots_dia:
                    results.append(f"• {dia_fmt}: {' ou '.join(slots_dia)}")
                    if len(results) >= 2:
                        break
        if results:
            return "\n".join(results)
        return "Nenhum horário disponível nos próximos dias. Entre em contato pelo WhatsApp: https://wa.me/5511932571982"
    except Exception as e:
        log.error(f"CliniSite error: {e}")
        return "Não consegui verificar os horários agora. Entre em contato pelo WhatsApp: https://wa.me/5511932571982"

# ─────────────────────────────────────────────────────────────
# FUNÇÕES IA
# ─────────────────────────────────────────────────────────────
def is_human_request(text):
    text_lower = text.lower()
    return any(kw in text_lower for kw in HUMAN_KEYWORDS)

def generate_ai_response(thread_id, user_message):
    if thread_id not in conversation_context:
        conversation_context[thread_id] = []
    conversation_context[thread_id].append({"role": "user", "content": user_message})
    if len(conversation_context[thread_id]) > 20:
        conversation_context[thread_id] = conversation_context[thread_id][-20:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_context[thread_id]
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

    # Carregar sessão a partir de variável de ambiente (base64) — para Railway
    if IG_SESSION_B64:
        try:
            session_json = base64.b64decode(IG_SESSION_B64).decode("utf-8")
            with open(IG_SESSION_FILE, "w") as f:
                f.write(session_json)
            log.info("Sessão carregada da variável de ambiente IG_SESSION_B64")
        except Exception as e:
            log.warning(f"Erro ao decodificar IG_SESSION_B64: {e}")

    # Carregar sessão do arquivo
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

def process_message(cl, thread_id, thread_title, user_id, message_text, message_id):
    log.info(f"[MSG] Thread: {thread_title} | Msg: {message_text[:60]}")

    if is_human_request(message_text):
        response = "Claro! Para falar diretamente com a gente, é só chamar no WhatsApp! 😊 https://wa.me/5511932571982"
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

    ai_response = generate_ai_response(thread_id, message_text)

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
    log.info("🚀 Instagram Monitor iniciado - Lana Estética")
    if TEST_MODE_USER:
        log.info(f"⚠️  MODO DE TESTE: respondendo apenas a @{TEST_MODE_USER}")

    try:
        cl = create_ig_client()
    except Exception as e:
        log.error(f"Falha ao criar cliente Instagram: {e}")
        notify_telegram(f"❌ *Monitor falhou ao iniciar*\nErro: {str(e)[:100]}")
        sys.exit(1)

    my_user_id = str(cl.user_id)
    log.info(f"Logado como: {IG_USERNAME} (ID: {my_user_id})")
    notify_telegram(f"✅ *Monitor do Instagram iniciado!*\nConta: @{IG_USERNAME}\n{'⚠️ MODO TESTE: apenas @' + TEST_MODE_USER if TEST_MODE_USER else 'Respondendo a todos os clientes.'}")

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
                if TEST_MODE_USER:
                    thread_users = [u.username for u in thread.users]
                    if TEST_MODE_USER not in thread_users:
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
