# Ícaro Antônio - Protótipo

Agente de IA educacional que guia estudantes de exatas por 4 etapas:

explicação teórica; passos de resolução; resposta do aluno e feedback
construtivo, sem nunca entregar a resposta pronta.

Stack: Python + Streamlit, com a API gratuita do Google Gemini como
provedor padrão. 
A API paga da OpenAI
também esta disponível como alternativa, selecionável na barra lateral do app.

## Arquivos

- `icaro_antonio.py` - aplicativo Streamlit (interface de chat + logica do agente)
- `requirements.txt` - dependências
- `secrets.toml.example` - modelo para configurar a chave de API


## Como obter uma chave gratuita do Gemini

1. Acesse https://aistudio.google.com/api-keys
2. Faca login com uma conta Google e clique em "Create API key"
3. Copie a chave gerada

## Como executar localmente

```bash
pip install -r requirements.txt

# opcao 1: variavel de ambiente
export GEMINI_API_KEY="sua_chave_aqui"

# opcao 2: crie a pasta .streamlit/ e copie o exemplo como secrets.toml
mkdir .streamlit
cp secrets.toml.example .streamlit/secrets.toml
# edite .streamlit/secrets.toml e cole sua chave

streamlit run icaro_antonio.py
```

Se nenhuma chave for encontrada em variável de ambiente ou secrets, a barra
lateral pede a chave manualmente (não e salva, fica só na sessão do
navegador).

## Uso na aplicação piloto

- Cada estudante conversa livremente com o agente sobre uma questão de
  exatas.
- O botão **"Baixar conversa (.txt)"** na barra lateral exporta o histórico
  completo - use esses arquivos (ou prints) para a analise qualitativa da
  seção de resultados do relatório.
- Depois da sessão, aplique o questionário de avaliação sobre utilidade, clareza e contribuição ao
  aprendizado.

## Trocar para a API paga da OpenAI (opcional)

Na barra lateral do app, selecione "OpenAI (pago)" no campo "Provedor de
IA" e informe uma chave `OPENAI_API_KEY` (ou configure-a como variável de
ambiente / secret, do mesmo jeito que a do Gemini).

## Personalização

O comportamento pedagógico do agente esta inteiramente definido na
constante `SYSTEM_PROMPT` em `icaro_antonio.py`. Ajustar esse texto e a
forma mais direta de refinar tom, rigor das etapas ou nível de exigência
das respostas, sinta-se livre para editar localmente conforme necessário
