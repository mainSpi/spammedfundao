#### *Tudo nesse projeto foi vibe-coded. Tudo. Nenhum arquivo, nenhuma função, nada foi escrito por um ser humano. Só decidi a arquitetura, e olhe lá. Somente se salvam os três parágrafos abaixo:*

- #### *O projeto foi realizado em um curto espaço de tempo, e teve um custo final de 65 centavos de dólar pela API do deepseek. Modelos como Gwen 2.5 3B e Gemma 3 4B se mostraram incapazes de fazer a classificação corretamente.*

- #### *SQLite foi escolhido pq mongodb da um baita trabalho pra instalar no windows.*

- #### *Streamlite foi esclhido pq o gemini pro sabe vibe-codar nessa bibliteca melhor que qualquer outra do mesmo nicho.*

# Classificador e Analisador de Mensagens do WhatsApp (MEDFundão)

Este projeto implementa um pipeline completo de engenharia de dados e machine learning para ingerir, processar, classificar e visualizar conversas de grupos de WhatsApp. O sistema utiliza **Regex** para estruturação, **LLMs (DeepSeek)** para análise semântica e **Streamlit** para visualização.

## 🚀 Fluxo de Processamento

O pipeline é dividido em três etapas sequenciais:

### 1. Ingestão de Dados (`split.py`)
* **Entrada:** Arquivo de texto bruto exportado do WhatsApp (`cvs.txt`).
* **Método:** Utiliza expressões regulares (`re`) para identificar timestamps e separar autores do conteúdo.
* **Ação:** Normaliza as datas para formato ISO e insere as mensagens no banco de dados SQLite (`chat_data.db`), criando relacionamentos entre usuários e mensagens.
* **Heurística Básica:** Identifica imediatamente stickers (`.webp`) e mídias ocultas para evitar custos desnecessários com IA.

---

#### *nesse momento o script (`anonimizer.py`) é rodado para remover os números de telefone e contatos salvos da database, pois eu não quero ser preso por espionagem.*

---

### 2. Classificação Semântica com IA (`async_deepseek_classifier.py`)
* **Tecnologia:** API da DeepSeek (compatível com client OpenAI) e Python `concurrent.futures`.
* **Método:**
    * Recupera mensagens "não tagueadas" do banco de dados.
    * Agrupa mensagens em **batches** (lotes) para reduzir o overhead de rede.
    * Utiliza **Processamento Assíncrono (Threading)** para enviar múltiplos lotes simultaneamente, contornando a latência de I/O da API.
* **System Prompt:** Instrução especializada que diferencia conversas sociais de anúncios/spam (venda de ingressos, cursos, moradia).
* **Saída:** Atualiza o campo `type` no banco de dados com o ID numérico correspondente.

### 3. Visualização e Analytics (`app.py`)
* **Tecnologia:** Streamlit, Pandas e Plotly.
* **Funcionalidades:**
    * Filtros dinâmicos por data, usuário e tipo de mensagem.
    * Gráficos de distribuição de tópicos (Pizza) e atividade temporal (Linha).
    * Ranking de usuários mais ativos.
    * Busca textual (Full-text search) na base processada.

---

## 🏷️ Categorias de Classificação

O sistema classifica as mensagens nos seguintes tópicos (processing/categorias.txt):

**Conversa & Social**
* `1`: Dúvidas sobre Provas/Professores
* `2`: Pedido de Contatos
* `3`: Localização/Plantão (Onde alguém está)
* `6`: Conversas Genéricas

**Mídia (Heurística)**
* `4`: Stickers/Figurinhas
* `5`: Áudio/Vídeo/Imagem

**Comércio & Divulgação (Spam)**
* `7`: Propaganda de Ligas Acadêmicas
* `8`: Propaganda de Festas
* `9`: Compra/Venda de Ingressos
* `10`: Cursos e Materiais Médicos
* `11`: Anúncios Gerais (Imóveis, Eletrônicos)

---

## 📂 Estrutura do Banco de Dados (`db.py`)

O projeto utiliza **SQLite** para persistência leve e rápida.

* **Tabela `users`**: Armazena identificadores únicos dos remetentes.
* **Tabela `messages`**: Armazena o conteúdo, timestamp, ID do usuário e a classificação (`type`).

---

## 🛠️ Configuração e Instalação

### Pré-requisitos
* Python 3.10
* Chave de API (DeepSeek ou compatível)

### Instalação

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure o ambiente:
   Crie um arquivo `.env` na raiz do projeto:
   ```env
   API_KEY=sua_chave_aqui
   ```

3. Execute o pipeline:
   ```bash
   # 1. Ingestão
   python split.py
   
   # 2. Classificação AI
   python async_deepseek_classifier.py
   
   # 3. Rodar Dashboard
   streamlit run app.py
   ```

---

