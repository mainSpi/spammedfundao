from db import setup_database, get_messages, update_message_type

connection = setup_database()
messages = get_messages(connection, limit=50000)

for message_id, content, type in messages:
    new_type = None
    if "STK" in content and ".webp" in content:
        new_type = 4
    elif content.endswith("<Mídia oculta>") or content.endswith("(arquivo anexado)"):
        new_type = 5

    if new_type is not None and new_type == type:
        print(f"Updating message {content} from type {type} to {new_type}")
        # update_message_type(connection, message_id, new_type)