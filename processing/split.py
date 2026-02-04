import re
from db import setup_database, store_message


connection = setup_database()
with open('cvs.txt', 'r', encoding='utf-8') as file:
    content = file.read()
    result = re.split(r"\d{2}\/\d{2}\/\d{4} \d{2}:\d{2} - ", content)
    timestamps = re.findall(r"\d{2}\/\d{2}\/\d{4} \d{2}:\d{2} - ", content)
    result.pop(0)

    for i in range(len(result)):
        s = result[i]
        if ":" in s:
            userName = s.split(": ")[0]
            content = s.split(": ")[1][:-1]

            if len(content) == 0:
                continue

            type = None
            if "STK" in content and ".webp" in content:
                type = 4
            elif content.endswith("<Mídia oculta>") or content.endswith("(arquivo anexado)"):
                type = 5

            time = timestamps[i][0:16]
            store_message(connection, userName, time, content, type)

# Verify the stored ISO format
# cursor = connection.cursor()
# cursor.execute("SELECT timestamp, content FROM messages")
# print("Stored Data:", cursor.fetchall())

connection.close()