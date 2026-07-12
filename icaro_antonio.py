"""
Ícaro Antônio — Agente de IA para Aprendizagem Guiada e Feedback Educacional
Protótipo funcional (PBL — Informática Aplicada ao Ensino / UFRJ)

Autoras: Maria Carolina Boudreaux Ramirez Deleito / Raquel Maria Boudreaux Ramirez Deleito

Como executar:
    pip install -r requirements.txt
    export GEMINI_API_KEY="sua_chave_aqui"      (opção gratuita, padrão — ou configure em .streamlit/secrets.toml)
    streamlit run icaro_antonio_final.py

Provedor de IA:
    Por padrão o app usa a API gratuita do Google Gemini (modelo gemini-3.5-flash),
    através do endpoint compatível com a biblioteca OpenAI — não é necessário cartão
    de crédito. Também é possível trocar para a API paga da OpenAI na barra lateral,
    caso o grupo prefira.

O agente NUNCA entrega a resposta final pronta. Ele conduz o estudante por
quatro etapas de mediação pedagógica:

    1. Explicação teórica   — conecta o problema a conceitos que o aluno já deveria dominar
    2. Passos de resolução  — sugere um caminho, sem entregar a solução final
    3. Resposta do aluno    — o estudante constrói e envia sua própria solução
    4. Feedback construtivo — analisa a resposta e orienta o avanço, sem corrigir "pronto"
"""

import os
import io
import re
import datetime as dt

import streamlit as st
from openai import OpenAI

STAGE_TAG_RE = re.compile(r"^\s*\[\[ETAPA:(\d)\]\]\s*")

# Configuração geral

APP_TITLE = "Ícaro Antônio"
APP_SUBTITLE = "Agente de IA para Aprendizagem Guiada e Feedback Educacional"

# Provedores suportados: nome de exibição -> configuração
PROVIDERS = {
    "Google Gemini (grátis)": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "env_key": "GEMINI_API_KEY",
        "models": ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.1-pro-preview"],
        "get_key_url": "https://aistudio.google.com/api-keys",
    },
    "OpenAI (pago)": {
        "base_url": None,  
        "env_key": "OPENAI_API_KEY",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"],
        "get_key_url": "https://platform.openai.com/api-keys",
    },
}

SYSTEM_PROMPT = """\
Você é "Ícaro Antônio", um agente de IA educacional para estudantes de \
ensino superior em áreas de exatas (cálculo, física, programação, álgebra \
linear e disciplinas correlatas).

SEU PAPEL É SER UM MEDIADOR DA APRENDIZAGEM, NUNCA UM FORNECEDOR DE RESPOSTAS \
PRONTAS. Você existe para combater a dependência de respostas imediatas de \
IA e para preservar o espaço de reflexão crítica do estudante (fundamentação: \
Dewey, Freire, Ausubel, Vygotsky e Sistemas Tutores Inteligentes - ITS).

Para CADA problema ou questão trazida pelo estudante, conduza rigorosamente \
a seguinte sequência de 4 etapas, uma de cada vez, sem pular etapas:

ETAPA 1 — EXPLICAÇÃO TEÓRICA
Identifique os conceitos teóricos que fundamentam o problema e explique-os de \
forma clara e objetiva, conectando-os a conhecimentos que o estudante \
provavelmente já possui (aprendizagem significativa — Ausubel). NÃO resolva \
o problema nesta etapa.

ETAPA 2 — PASSOS DE RESOLUÇÃO
Sugira um caminho de resolução em passos gerais (o "como pensar"), sem \
executar os cálculos ou chegar à resposta final. Funcione como um andaime \
(scaffolding — Vygotsky): dê o suporte mínimo necessário para que o aluno \
consiga avançar sozinho a partir daqui.

ETAPA 3 — AGUARDAR A RESPOSTA DO ALUNO
Peça explicitamente que o estudante tente resolver o problema com base na \
explicação e nos passos fornecidos, e envie sua própria resposta/solução. \
Não avance para a etapa 4 até que o aluno responda.

ETAPA 4 — FEEDBACK CONSTRUTIVO
Analise a resposta do aluno:
- Se estiver correta: confirme, reforce o raciocínio usado e, se fizer \
sentido, proponha uma pequena extensão ou pergunta de aprofundamento.
- Se estiver incorreta ou incompleta: NÃO dê a resposta certa diretamente. \
Aponte especificamente onde o raciocínio se desviou, faça perguntas que \
ajudem o aluno a identificar o próprio erro, e convide-o a tentar novamente \
(retorne à etapa 3 quantas vezes forem necessárias).

REGRAS INVIOLÁVEIS:
- Nunca forneça a resposta numérica ou final pronta, mesmo se o estudante \
insistir, pedir "só a resposta" ou alegar urgência.
- Se o estudante pedir a resposta direta, recuse educadamente e reafirme seu \
papel de mediador, oferecendo em vez disso mais uma pista ou explicação.
- Mantenha tom acolhedor, paciente e encorajador — o objetivo é autonomia, \
não intimidação.
- Adapte a profundidade da explicação ao nível de dificuldade demonstrado \
pelo aluno (personalização/sistemas adaptativos).
- Ao final de uma interação bem-sucedida (problema resolvido corretamente \
pelo aluno), pergunte se ele quer trazer um novo problema.
- Sempre responda em português do Brasil.

CONTROLE DE ETAPA (uso interno, invisível ao estudante):
No INÍCIO de toda resposta sua, sem exceção, inclua uma das marcações abaixo, \
exatamente neste formato, antes de qualquer outra palavra:
- [[ETAPA:2]] → use quando esta resposta traz a explicação teórica e/ou os \
passos de resolução e você está aguardando a tentativa do estudante, inclua \
também quando o estudante errou ou ficou incompleto e você está pedindo uma \
nova tentativa (retorno à etapa 3).
- [[ETAPA:4]] → use somente quando esta resposta confirma que o estudante \
acertou o problema (feedback final de um ciclo concluído).
Essa marcação é removida automaticamente antes de ser exibida ao estudante. \
Nunca a explique, comente ou mencione no corpo do texto, ela deve aparecer \
apenas uma vez, isolada, no começo absoluto da mensagem.
"""

STAGE_LABELS = [
    "1. Explicação teórica",
    "2. Passos de resolução",
    "3. Resposta do aluno",
    "4. Feedback construtivo",
]

# Utilidades
def get_secret(name: str):
    try:
        val = st.secrets.get(name)
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(name)


def get_client(provider_name: str):
    """Monta o client OpenAI apontando para o provedor escolhido (Gemini ou OpenAI)."""
    cfg = PROVIDERS[provider_name]
    api_key = get_secret(cfg["env_key"]) or st.session_state.get(f"manual_key_{cfg['env_key']}")
    if not api_key:
        return None
    kwargs = {"api_key": api_key}
    if cfg["base_url"]:
        kwargs["base_url"] = cfg["base_url"]
    return OpenAI(**kwargs)


def export_conversation_txt() -> str:
    """Gera um .txt com a conversa completa, para uso na análise qualitativa do relatório."""
    buf = io.StringIO()
    buf.write(f"Conversa com Ícaro Antônio exportado em {dt.datetime.now():%Y-%m-%d %H:%M}\n")
    buf.write("=" * 70 + "\n\n")
    for msg in st.session_state.messages:
        if msg["role"] == "system":
            continue
        speaker = "ESTUDANTE" if msg["role"] == "user" else "ÍCARO ANTÔNIO"
        buf.write(f"[{speaker}]\n{msg['content']}\n\n")
    return buf.getvalue()


# Interface Streamlit
st.set_page_config(page_title=APP_TITLE, page_icon="🤓", layout="centered")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

if "completed_stage" not in st.session_state:
    st.session_state.completed_stage = 0

with st.sidebar:
    st.header("⚙️ Configuração")

    provider_name = st.selectbox("Provedor de IA", list(PROVIDERS.keys()), index=0)
    cfg = PROVIDERS[provider_name]

    if not get_secret(cfg["env_key"]):
        st.session_state[f"manual_key_{cfg['env_key']}"] = st.text_input(
            f"Chave de API ({cfg['env_key']})", type="password",
            help=(
                f"Não encontrada como variável de ambiente/secret. Obtenha uma chave "
                f"gratuita em {cfg['get_key_url']}."
            ),
        )
        st.caption(f"🔑 Criar chave: {cfg['get_key_url']}")

    model = st.selectbox("Modelo", cfg["models"], index=0)
    temperature = st.slider("Temperatura", 0.0, 1.0, 0.4, 0.1)

    if provider_name.startswith("Google"):
        st.caption(
            "ℹ️ No nível gratuito do Gemini, o conteúdo das conversas pode ser usado "
            "pelo Google para melhorar seus produtos. Evite compartilhar dados "
            "sensíveis durante o piloto."
        )

    st.divider()
    st.caption("Etapa atual do fluxo pedagógico")
    completed = st.session_state.completed_stage
    for i, label in enumerate(STAGE_LABELS, start=1):
        if i <= completed:
            icon = "✅"
        elif i == completed + 1:
            icon = "▶️"
        else:
            icon = "⬜"
        st.markdown(f"{icon} {label}")

    st.divider()
    if st.button("🔄 Reiniciar conversa"):
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.session_state.completed_stage = 0
        st.rerun()

    if len(st.session_state.messages) > 1:
        st.download_button(
            "⬇️ Baixar conversa (.txt)",
            data=export_conversation_txt(),
            file_name=f"conversa_icaro_antonio_{dt.datetime.now():%Y%m%d_%H%M}.txt",
            mime="text/plain",
        )

    st.divider()
    st.caption(
        "Após a sessão, responda ao questionário de avaliação sobre utilidade, "
        "clareza e contribuição para o aprendizado: "
        "[clique aqui](https://forms.gle/BJFM98yvtF6hcstq7)"
    )

st.title(f"🤓 {APP_TITLE}")
st.caption(APP_SUBTITLE)
st.info(
    "Traga uma questão de exatas (cálculo, física, programação, álgebra "
    "linear...). Ícaro Antônio não dará a resposta pronta, ele vai te "
    "guiar até você mesmo chegar lá.",
    icon="💡",
)

for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    with st.chat_message("user" if msg["role"] == "user" else "assistant", avatar="🧑‍🎓" if msg["role"] == "user" else "🤓"):
        st.markdown(msg["content"])

prompt = st.chat_input("Digite sua questão ou sua resposta...")

if prompt:
    client = get_client(provider_name)
    if client is None:
        st.error(
            f"Nenhuma chave de API configurada para {provider_name}. Defina "
            f"{cfg['env_key']} como variável de ambiente, em .streamlit/secrets.toml, "
            "ou informe-a na barra lateral."
        )
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍🎓"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🤓"):
        placeholder = st.empty()
        raw_response = ""      
        visible_response = ""  
        tag_resolved = False   
        detected_stage = None
        try:
            stream = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=st.session_state.messages,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if not delta:
                    continue
                raw_response += delta

                if not tag_resolved:
                    m = STAGE_TAG_RE.match(raw_response)
                    if m:
                        detected_stage = int(m.group(1))
                        visible_response = raw_response[m.end():]
                        tag_resolved = True
                        placeholder.markdown(visible_response + "▌")
                    elif len(raw_response) > 20 and "]]" not in raw_response:
                        tag_resolved = True
                        visible_response = raw_response
                        placeholder.markdown(visible_response + "▌")
                else:
                    visible_response += delta
                    placeholder.markdown(visible_response + "▌")

            if not tag_resolved:
                m = STAGE_TAG_RE.match(raw_response)
                if m:
                    detected_stage = int(m.group(1))
                    visible_response = raw_response[m.end():]
                else:
                    visible_response = raw_response

            visible_response = visible_response.lstrip()
            placeholder.markdown(visible_response)
        except Exception as e:
            visible_response = f"⚠️ Erro ao chamar a API ({provider_name}): {e}"
            placeholder.error(visible_response)

    if detected_stage in (2, 4):
        just_finished = detected_stage == 4 and st.session_state.completed_stage != 4
        st.session_state.completed_stage = detected_stage
        if just_finished:
            st.toast("🎉 Problema concluído! Pronto para o próximo.", icon="✅")

    st.session_state.messages.append({"role": "assistant", "content": visible_response})