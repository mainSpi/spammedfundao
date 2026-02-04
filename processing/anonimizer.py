import sqlite3

def anonimizar_tabela(db_path):
    # Conecta ao banco de dados
    # 'db_path' deve ser o caminho para o seu arquivo .db ou .sqlite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Selecionamos apenas os IDs ordenados. 
        # Isso garante que a "Pessoa 1" seja o ID mais baixo (1), a "Pessoa 2" o ID (2), etc.
        print("Lendo registros...")
        cursor.execute("SELECT id FROM users ORDER BY id")
        rows = cursor.fetchall()

        # 2. Preparamos os dados para a atualização em massa
        # Criamos uma lista de tuplas no formato: (novo_valor_ssn, id_do_usuario)
        atualizacoes = []
        
        for index, row in enumerate(rows, start=1):
            user_id = row[0]
            novo_nome = f"Pessoa {index}"
            atualizacoes.append((novo_nome, user_id))

        # 3. Executamos o UPDATE
        # O executemany é muito mais rápido que rodar um update por vez dentro do loop
        print(f"Atualizando {len(atualizacoes)} registros...")
        cursor.executemany("UPDATE users SET ssn = ? WHERE id = ?", atualizacoes)

        # 4. Salvar as alterações
        conn.commit()
        print("Sucesso! Tabela atualizada.")

    except sqlite3.Error as e:
        print(f"Ocorreu um erro: {e}")
        conn.rollback() # Desfaz alterações se der erro
    finally:
        conn.close()

# --- Configuração ---
# Substitua 'meu_banco.db' pelo nome real do seu arquivo
arquivo_banco = 'chat_data.db' 

# Executar
if __name__ == "__main__":
    anonimizar_tabela(arquivo_banco)