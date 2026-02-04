import json
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from dotenv import load_dotenv
import os

# Importing your DB functions
# Ensure setup_database returns a fresh sqlite3 connection object
from db import setup_database, get_untagged_messages, update_message_type

load_dotenv()
# --- CONFIGURATION ---
API_KEY = os.getenv("API_KEY")
BASE_URL = "https://api.deepseek.com"
MAX_WORKERS = 10       # Number of simultaneous threads (Don't set too high to avoid API rate limits)
BATCH_SIZE = 25       # Messages per API call
TOTAL_FETCH_LIMIT = 273 # How many messages to fetch from DB in the "big get"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

SYSTEM_PROMPT = """Você é um classificador especializado em grupos de Whatsapp de Medicina. 
Sua tarefa é CLASSIFICAR mensagens em categorias numeradas.
Analise a intenção do usuário e retorne o JSON.

### GUIA DE CLASSIFICAÇÃO COM EXEMPLOS

PRIMEIRO, SEPARE UMA MENSAGEM ENTRE [CONVERSA] E [SPAM/ANÚNCIOS]. ESSA É A PARTE MAIS IMPORTANTE.
SE NÃO SOUBER O QUE COLOCAR DENTRO DESSAS CATEGORIAS, USE 6 PARA CONVERSA E 11 PARA SPAM/ANÚNCIOS.

[CONVERSA - Interações sociais ou dúvidas]
1 -> PROVA/PROFESSOR
   - "Alguém já fez prova com tal professor?"
   - "Como é a prova do professor fulano?"

2 -> CONTATO DE ALGUÉM
   - "Alguém tem o wpp do Flavio de nefro?"
   - "Preciso falar com o residente de cirurgia"
   - "Passa o contato da Duda?"

3 -> LOCALIZAÇÃO/PLANTÃO (Onde alguém está AGORA)
   - "Alguém no HUCFF agora?"
   - "Quem tá de plantão na UPA?"
   - "Tem alguém no fundão?"

6 -> CONVERSAS GENÉRICAS (Dúvidas gerais, perdidos e achados, avisos de aula)
   - "Alguém achou um casaco azul?"
   - "A aula vai ser em qual sala?"
   - "O bandejão tá aberto?"
   - "Gente, que dia cai a P1?"
   - "Alguém vai na festa hoje?" (Isso é conversa, não venda)
   - "Procuro alguém pra dividir AP"

[SPAM/ANÚNCIOS - Ofertas e Divulgação]
7 -> PROPAGANDA DE LIGAS (Processo seletivo, aula aberta)
   - "Venha para a aula inaugural da LAC"
   - "Inscrições abertas para a liga de Trauma"
   - "Sessão aberta hoje as 18h"

8 -> PROPAGANDA DE FESTAS (Divulgação do evento)
   - "Vem aí a Maior Calourada da história"
   - "Chopada de medicina é sexta feira!"
   - "Link para comprar a festa X"

9 -> VENDA/COMPRA DE INGRESSOS (Transações de festas)
   - "Vendo ingresso da prefa no precinho"
   - "Compro 2 ingressos área VIP"
   - "Alguém vendendo ingresso pra hoje?"

10 -> CURSOS E MATERIAIS (Medcurso, Medway, Livros Médicos)
   - "Vendo Medcurso 2024 completo"
   - "Alguém quer dividir o Sanar?"
   - "Vendo Whitebook vitalício"
   - "Vendo Guyton e Hall usado"

11 -> ANÚNCIOS GERAIS (Moradia, Eletrônicos, Serviços)
   - "Vaga para menina quarto em Copacabana"
   - "Vendo iPhone 13 novo"
   - "Faço fretes e mudanças"


### FORMATO DE RESPOSTA
Responda APENAS com um JSON válido contendo a lista classificada. Não explique.
Exemplo de entrada: [{"id": 1, "text": "vendo ingresso"}, {"id": 2, "text": "alguem no hospital?"}]
Exemplo de saída: [{"id": 1, "codigo": "09"}, {"id": 2, "codigo": "03"}]

NÃO RESPONDA COM O TEXTO DA MENSAGEM, APENAS O JSON COM O CÓDIGO DE CLASSIFICAÇÃO!
"""

def classify_batch(messages_batch):
    """
    Sends the batch to the LLM.
    Added try/except to prevent one API failure from crashing the whole script.
    """
    user_content = f"Classifique:\n{json.dumps(messages_batch, ensure_ascii=False)}"
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False,
            temperature=0.1 # Lower temp for more consistent formatting
        )
        content = response.choices[0].message.content
        # Remove markdown code blocks if the AI adds them (common issue)
        clean_content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_content)
    except Exception as e:
        print(f"Error in API call: {e}")
        return []

def process_batch_worker(batch_data):
    """
    This function runs inside a thread.
    1. Calls API
    2. Opens its OWN database connection (Crucial for SQLite)
    3. Updates records
    """
    if not batch_data:
        return

    # 1. Network Operation (Slow - Good for threading)
    print(f"[Thread-{threading.get_ident()}] Classifying {len(batch_data)} messages...")
    results = classify_batch(batch_data)

    if not results:
        return

    # 2. Database Operation (Fast - Must have own connection)
    # We open a new connection per thread because SQLite objects are not thread-safe.
    try:
        local_conn = setup_database() 
        for result in results:
            try:
                # Ensure we handle cases where AI might miss a field
                if "id" in result and "codigo" in result:
                    update_message_type(local_conn, result["id"], int(result["codigo"]))
            except Exception as row_error:
                print(f"Error updating row {result.get('id')}: {row_error}")
        
        # Commit usually happens in update_message_type or we can force it here
        local_conn.commit() 
    except Exception as db_e:
        print(f"Database error in thread: {db_e}")
    finally:
        local_conn.close()
        print(f"[Thread-{threading.get_ident()}] exiting")

def chunk_list(data, chunk_size):
    """Yield successive chunks from data."""
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print(f"Starting Process at {datetime.now().strftime('%H:%M:%S')}")

    # 1. The 'Big Get' - Fetch raw data in the main thread
    main_conn = setup_database()
    raw_data = get_untagged_messages(main_conn, limit=TOTAL_FETCH_LIMIT)
    main_conn.close() # Close immediately so threads don't fight over this connection

    if not raw_data:
        print("No untagged messages found.")
        exit()

    print(f"Fetched {len(raw_data)} messages. Splitting into threads...")

    # 2. Format Data
    # Assuming row is (id, text, ...)
    formatted_data = [{"id": row[0], "text": row[1][:200]} for row in raw_data]

    # 3. Create Batches
    batches = list(chunk_list(formatted_data, BATCH_SIZE))

    # 4. Process in Parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all batches to the pool
        futures = [executor.submit(process_batch_worker, batch) for batch in batches]
        
        # Wait for completion (optional, strictly for UI/Progress monitoring)
        for future in as_completed(futures):
            try:
                future.result() # Check for exceptions
            except Exception as e:
                print(f"Thread generated an exception: {e}")

    print(f"Finished at {datetime.now().strftime('%H:%M:%S')}")