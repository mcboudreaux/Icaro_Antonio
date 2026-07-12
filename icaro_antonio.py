"""
Ícaro Antônio — Agente de IA para Aprendizagem Guiada e Feedback Educacional
Protótipo funcional (PBL — Informática Aplicada ao Ensino / UFRJ)

Autoras: Maria Carolina Boudreaux Ramirez Deleito / Raquel Maria Boudreaux Ramirez Deleito

Como executar:
    pip install -r requirements.txt
    export OPENAI_API_KEY="sua_chave_aqui"      (ou configure em .streamlit/secrets.toml)
    streamlit run icaro_antonio.py

O agente não entrega a resposta final pronta. Ele conduz o estudante por
quatro etapas de mediação pedagógica:

    1. Explicação teórica: conecta o problema a conceitos que o aluno já deveria dominar
    2. Passos de resolução: sugere um caminho, sem entregar a solução final
    3. Resposta do aluno: o estudante constrói e envia sua própria solução
    4. Feedback construtivo: analisa a resposta e orienta o avanço, sem corrigir "pronto"
"""

import os
import io
import datetime as dt

import streamlit as st
from openai import OpenAI

# Configuração geral

APP_TITLE = "Ícaro Antônio"
APP_SUBTITLE = "Agente de IA para Aprendizagem Guiada e Feedback Educacional"
DEFAULT_MODEL = "gpt-4o-mini"

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
"""

STAGE_LABELS = [
    "1. Explicação teórica",
    "2. Passos de resolução",
    "3. Resposta do aluno",
    "4. Feedback construtivo",
]

# Utilidades

def get_client():
    """Obtém a chave de API a partir de st.secrets, variável de ambiente ou input manual."""
    api_key = None
    try:
        api_key = st.secrets.get("OPENAI_API_KEY")
    except Exception:
        api_key = None
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        api_key = st.session_state.get("manual_api_key")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def export_conversation_txt() -> str:
    """Gera um .txt com a conversa completa, para uso na análise qualitativa do relatório."""
    buf = io.StringIO()
    buf.write(f"Conversa com Ícaro Antônio: exportado em {dt.datetime.now():%Y-%m-%d %H:%M}\n")
    buf.write("=" * 70 + "\n\n")
    for msg in st.session_state.messages:
        if msg["role"] == "system":
            continue
        speaker = "ESTUDANTE" if msg["role"] == "user" else "ÍCARO ANTÔNIO"
        buf.write(f"[{speaker}]\n{msg['content']}\n\n")
    return buf.getvalue()



# Interface Streamlit

st.set_page_config(page_title=APP_TITLE, page_icon="👼", layout="centered")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

if "turn_count" not in st.session_state:
    st.session_state.turn_count = 0

with st.sidebar:
    st.header("⚙️ Configuração")

    has_env_key = bool(os.environ.get("OPENAI_API_KEY"))
    has_secret_key = False
    try:
        has_secret_key = bool(st.secrets.get("OPENAI_API_KEY", None))
    except Exception:
        has_secret_key = False

    if not has_env_key and not has_secret_key:
        st.session_state.manual_api_key = st.text_input(
            "Chave da API OpenAI", type="password",
            help="Necessária apenas se OPENAI_API_KEY não estiver configurada como variável de ambiente ou secret.",
        )

    model = st.selectbox("Modelo", [DEFAULT_MODEL, "gpt-4o", "gpt-4.1-mini"], index=0)
    temperature = st.slider("Temperatura", 0.0, 1.0, 0.4, 0.1)

    st.divider()
    st.caption("Etapa atual do fluxo pedagógico")
    stage_idx = min(st.session_state.turn_count, 3)
    for i, label in enumerate(STAGE_LABELS):
        st.markdown(f"{'✅' if i < stage_idx else ('▶️' if i == stage_idx else '⬜')} {label}")

    st.divider()
    if st.button("🔄 Reiniciar conversa"):
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.session_state.turn_count = 0
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
        "Após a sessão, responda ao questionário de avaliação (Google Forms) "
        "sobre utilidade, clareza e contribuição para o aprendizado."
    )

st.title(f"👼 {APP_TITLE}")
st.caption(APP_SUBTITLE)
st.info(
    "Traga uma questão de exatas (cálculo, física, programação, álgebra "
    "linear...). Ícaro Antônio não dará a resposta pronta — ele vai te "
    "guiar até você mesmo chegar lá.",
    icon="💡",
)

for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    with st.chat_message("user" if msg["role"] == "user" else "assistant", avatar="🧑‍🎓" if msg["role"] == "user" else "👼"):
        st.markdown(msg["content"])

prompt = st.chat_input("Digite sua questão ou sua resposta...")

if prompt:
    client = get_client()
    if client is None:
        st.error(
            "Nenhuma chave de API configurada. Defina OPENAI_API_KEY como "
            "variável de ambiente, em .streamlit/secrets.toml, ou informe-a "
            "na barra lateral."
        )
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.turn_count += 1
    with st.chat_message("user", avatar="🧑‍🎓"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="👼"):
        placeholder = st.empty()
        full_response = ""
        try:
            stream = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=st.session_state.messages,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                full_response += delta
                placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)
        except Exception as e:
            full_response = f"⚠️ Erro ao chamar a API: {e}"
            placeholder.error(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
