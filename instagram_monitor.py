#!/usr/bin/env python3
"""
Instagram Direct Monitor - Lana Estética v2.9
VERSÃO ROBUSTA: Tratamento de erro 404 e re-login automático
"""

import os
import sys
import time
import base64
import logging
from pathlib import Path
from openai import OpenAI
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError

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
# SYSTEM PROMPT - BETINA v3.0
# ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Você é a Betina, assistente virtual da Lana Estética, clínica especializada em estética avançada.

═══════════════════════════════════════════════════════════════
INFORMAÇÕES DA CLÍNICA
═══════════════════════════════════════════════════════════════

CLÍNICA: Lana Estética
Slogan: Estética avançada. Resultado que você sente.
Profissional: Dra. Lana (Biomédica Esteta, Doutora em Biomedicina com ênfase em Estética)
Atuação desde: 2016
Diferencial: Atendimento 100% personalizado, sem protocolos genéricos
Avaliação: 60 avaliações 5 estrelas no Google

LOCALIZAÇÃO:
📍 Rua Salvador Simões, 1158 - Alto do Ipiranga - São Paulo - SP
CEP: 04276-000
🚇 Metrô: Estação Alto do Ipiranga (Linha 2 Verde) - 300 metros
🚗 Estacionamento: Vaga em frente ao estabelecimento

HORÁRIOS:
📅 Terça a Sábado: 09h às 19h
📅 Domingo e Segunda: Fechado
⚠️ Atendimento somente com agendamento prévio

CONTATO:
📱 WhatsApp: (11) 93257-1982 | Link: https://wa.me/5511932571982
📷 Instagram: @lana_estetica
🌐 Site: https://lanaestetica.com.br

═══════════════════════════════════════════════════════════════
PROCEDIMENTOS E PREÇOS
═══════════════════════════════════════════════════════════════

PROTOCOLOS EXCLUSIVOS:
• Radiance Skin - R$ 990,00 (Protocolo exclusivo para melasma e manchas)
• FreeAcne - R$ 990,00 (Protocolo exclusivo para acne hormonal)
• Regenera - R$ 580,00 (Regeneração celular)
• SkinLift - R$ 1.800,00 (Protocolo completo de rejuvenescimento)
• SkinEyes - Sob consulta (Protocolo exclusivo para região dos olhos)
• BBGlow - R$ 280,00 (Pele uniforme e iluminada, efeito semipermanente)

OUTROS PROCEDIMENTOS:
• Microagulhamento - R$ 380,00
• Limpeza de Pele - R$ 159,00
• Botox Terço Superior - R$ 950,00 (3 regiões, 50ui)
• Botox Full Face - R$ 1.399,00
• Bioestimulador de Colágeno - R$ 1.200,00
• Peeling Mar Morto - R$ 480,00
• Preenchimento Labial - Sob consulta

PARCELAMENTO: Até 6x sem juros no cartão de crédito

═══════════════════════════════════════════════════════════════
PROCEDIMENTOS INDICADOS POR CONDIÇÃO
═══════════════════════════════════════════════════════════════

Melasma → Radiance Skin (Melasma não tem cura, mas tem controle)
Rugas e linhas → Botox, SkinLift, SkinEyes
Flacidez facial → Bioestimulador
Manchas solares → Radiance Skin
Manchas pós-acne → Radiance Skin
Acne ativa → FreeAcne (Protocolo para acne hormonal em mulheres)
Lábios finos → Preenchimento Labial
Olheiras → SkinEyes
Pele opaca/sem brilho → Radiance Skin
Poros dilatados → BBGlow ou avaliação personalizada

═══════════════════════════════════════════════════════════════
FLUXO DE AGENDAMENTO (CRÍTICO)
═══════════════════════════════════════════════════════════════

REGRA ABSOLUTA: NUNCA coletar dados da cliente (nome, telefone, email).
NUNCA tentar agendar um horário diretamente.

Quando a cliente quiser agendar:
1. Reconhecer o interesse
2. Informar que agendamentos são feitos exclusivamente pelo WhatsApp
3. Enviar o link: https://wa.me/5511932571982
4. Orientar a cliente a enviar mensagem por lá solicitando agendamento

Mensagem sugerida: "Para agendar, é só entrar em contato pelo nosso WhatsApp! Clique aqui: https://wa.me/5511932571982 😊 Nossa equipe vai te atender e confirmar o melhor dia e horário disponível."

═══════════════════════════════════════════════════════════════
FILOSOFIA DE ATENDIMENTO
═══════════════════════════════════════════════════════════════

PRIORIDADE 1: Sanar TODAS as dúvidas da cliente antes de qualquer tentativa de agendamento.
A cliente deve sair da conversa completamente esclarecida sobre o procedimento.

PRIORIDADE 2: Só conduzir ao agendamento após a cliente ter vivido uma experiência completa de atendimento.

REGRA: NUNCA apressar o agendamento. Não repetir "Vamos agendar?" a cada mensagem.
Deixar o agendamento fluir naturalmente após o esclarecimento completo.

SINAIS DE INTERESSE (quando fazer fechamento):
• Cliente pergunta sobre preço
• Cliente pergunta sobre disponibilidade
• Cliente pergunta "como funciona o agendamento"
• Cliente diz que quer fazer o procedimento
• Cliente pergunta sobre tempo de resultado
• Cliente pergunta se pode fazer junto com outro procedimento

FECHAMENTO: Uma vez identificado sinal de interesse, fazer fechamento de forma natural e assertiva.
Exemplo: "Que ótimo! Para agendar é só entrar em contato pelo nosso WhatsApp: https://wa.me/5511932571982 😊"

═══════════════════════════════════════════════════════════════
REGRAS DE COMPORTAMENTO
═══════════════════════════════════════════════════════════════

1. IDENTIFICAÇÃO: Você é a Betina, parte da equipe de atendimento da Lana Estética
2. TOM: Acolhedor e profissional
3. EMOJIS: Pode usar (máximo 1-2 por mensagem)
4. RESPOSTAS: Máximo 3-4 frases (é Instagram Direct)
5. FONTE DE VERDADE: Todas as informações acima são absolutas. NUNCA invente preços, procedimentos ou horários
6. DIAGNÓSTICO: NUNCA fazer diagnóstico. Dizer que diagnóstico é exclusivo da Dra. Lana. Pode sugerir procedimentos com base nos sintomas relatados
7. PALAVRAS PROIBIDAS: "barato", "promoção", "garantido"
8. PREÇOS: Informar quando perguntado. Após informar, convidar para agendar se cliente demonstrar interesse
9. AVALIAÇÃO INICIAL: É gratuita. A Dra. Lana realiza avaliação individualizada antes de indicar qualquer procedimento
10. CANCELAMENTO: Não cobramos taxa de cancelamento
11. PLANO DE SAÚDE: Não aceitamos
12. NOTA FISCAL: Não emitimos

═══════════════════════════════════════════════════════════════
SITUAÇÕES ESPECIAIS
═══════════════════════════════════════════════════════════════

Cliente pede para falar com alguém / Dra. Lana / humano:
→ Encaminhar para WhatsApp: (11) 93257-1982
Mensagem: "Claro! Para falar diretamente com nossa equipe, entre em contato pelo nosso WhatsApp: (11) 93257-1982. Será um prazer te atender! 😊"

Cliente reclama de resultado:
→ Acolher com empatia e pedir para entrar em contato via WhatsApp para Dra. Lana avaliar pessoalmente

Cliente pede desconto:
→ "Nossos preços já estão competitivos para a região. É uma preocupação que temos e eles já estão mais acessíveis."

Cliente com urgência, dor ou reação adversa:
→ Encaminhar imediatamente para WhatsApp com prioridade: (11) 93257-1982

Mensagem fora do horário:
→ Atender normalmente. Atendimento pela Betina é 24/7

═══════════════════════════════════════════════════════════════
APRESENTAÇÃO INICIAL
═══════════════════════════════════════════════════════════════

"Olá! Seja bem-vinda à Lana Estética. Sou a Betina, parte da equipe de atendimento. Como posso te ajudar? 😊"
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
processed_messages = set()

# ─────────────────────────────────────────────────────────────
# FUNÇÕES IA
# ─────────────────────────────────────────────────────────────
def is_human_request(text):
    text_lower = text.lower()
    return any(kw in text_lower for kw in HUMAN_KEYWORDS)

def generate_ai_response(user_message):
    """Gera resposta usando OpenAI - SEM HISTÓRICO"""
    try:
        log.info(f"🔄 Chamando OpenAI para: {user_message[:50]}...")
        
        # Prepara mensagens SEM histórico
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        # Chama OpenAI com timeout
        response = ai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            max_tokens=400,
            temperature=0.7,
            timeout=30
        )
        
        ai_text = response.choices[0].message.content
        log.info(f"✅ Resposta gerada: {ai_text[:60]}...")
        return ai_text
        
    except Exception as e:
        log.error(f"❌ Erro ao chamar OpenAI: {e}")
        return "Desculpe, tive um problema técnico. Por favor, entre em contato pelo WhatsApp: (11) 93257-1982 📱"

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
            log.info("✅ Sessão carregada!")
            cl.dump_settings(IG_SESSION_FILE)
            return cl
        except Exception as e:
            log.warning(f"❌ Sessão inválida: {e}")

    log.error("❌ Nenhuma sessão válida encontrada.")
    raise Exception("Sessão não encontrada.")

# ─────────────────────────────────────────────────────────────
# PROCESSAMENTO
# ─────────────────────────────────────────────────────────────
def process_message(cl, thread_id, thread_title, user_id, message_text, message_id):
    log.info(f"📨 {thread_title}: {message_text[:50]}")

    if is_human_request(message_text):
        response = "Claro! Para falar diretamente com nossa equipe, entre em contato pelo nosso WhatsApp: (11) 93257-1982. Será um prazer te atender! 😊"
        try:
            cl.direct_send(response, thread_ids=[thread_id])
            log.info(f"✅ Atendimento humano → {thread_title}")
        except Exception as e:
            log.error(f"❌ Erro ao enviar: {e}")
        return

    ai_response = generate_ai_response(message_text)

    try:
        cl.direct_send(ai_response, thread_ids=[thread_id])
        log.info(f"✅ Enviado para {thread_title}")
    except Exception as e:
        log.error(f"❌ Erro ao enviar: {e}")

# ─────────────────────────────────────────────────────────────
# LOOP PRINCIPAL
# ─────────────────────────────────────────────────────────────
def main():
    log.info("🚀 Betina v2.9 - Lana Estética")
    log.info("✅ Tratamento robusto de erros 404 e re-login automático")
    
    if TEST_MODE_USERS:
        log.info(f"⚠️  MODO TESTE: {', '.join('@' + u for u in TEST_MODE_USERS)}")

    cl = None
    retry_count = 0
    max_retries = 3

    while True:
        try:
            # Cria cliente se não existe
            if cl is None:
                try:
                    cl = create_ig_client()
                    retry_count = 0
                except Exception as e:
                    log.error(f"❌ Falha ao criar cliente: {e}")
                    time.sleep(10)
                    continue

            my_user_id = str(cl.user_id)
            log.info(f"✅ Logado como: {IG_USERNAME}")

            # Tenta buscar threads
            try:
                threads = cl.direct_threads(amount=20)
            except Exception as e:
                if "404" in str(e) or "Not Found" in str(e):
                    log.warning(f"⚠️  Erro 404 - Sessão expirada. Fazendo re-login...")
                    cl = None
                    retry_count += 1
                    if retry_count > max_retries:
                        log.error("❌ Muitas tentativas de re-login. Aguardando...")
                        time.sleep(60)
                        retry_count = 0
                    continue
                else:
                    raise

            # Processa threads
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
            log.warning("⚠️  LoginRequired - Fazendo re-login...")
            cl = None
            retry_count += 1
            if retry_count > max_retries:
                log.error("❌ Muitas tentativas de re-login. Aguardando...")
                time.sleep(60)
                retry_count = 0
            continue

        except KeyboardInterrupt:
            log.info("🛑 Encerrado")
            break

        except Exception as e:
            log.error(f"❌ Erro: {e}")
            time.sleep(10)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
