# Ícaro Antônio (v. 1.5 - Protótipo)

Agente de IA educacional (chat) que guia estudantes de exatas por 4 etapas:

explicação teórica; passos de resolução; resposta do aluno e feedback
construtivo, sem entregar a resposta pronta. 
Ver seção 6
(Autenticidade) e Referencial Teórico do relatório do projeto.

Stack: Python + Streamlit + API da OpenAI

## Arquivos

- `icaro_antonio.py` — aplicativo Streamlit (interface de chat + lógica do agente)
- `requirements.txt` — dependências
- `secrets.toml.example` — modelo para configurar a chave de API

## Como executar localmente

```bash
pip install -r requirements.txt

# opção 1: variável de ambiente
export OPENAI_API_KEY="sua_chave_aqui"

# opção 2: crie a pasta .streamlit/ e copie o exemplo como secrets.toml
mkdir .streamlit
cp secrets.toml.example .streamlit/secrets.toml
# edite .streamlit/secrets.toml e cole sua chave

streamlit run icaro_antonio.py
```

O app abre em `http://localhost:8501`. Se nenhuma chave for encontrada em
variável de ambiente ou secrets, a barra lateral pede a chave manualmente
(não é salva, fica só na sessão do navegador).

## Personalização

O comportamento pedagógico do agente está inteiramente definido na
constante `SYSTEM_PROMPT` em `icaro_antonio.py`. Ajustar esse texto é a
forma mais direta de refinar tom, rigor das etapas ou nível de exigência
das respostas, sinta-se livre para alterar conforme sua necessidade.