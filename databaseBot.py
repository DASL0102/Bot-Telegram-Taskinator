import sqlite3

# Función para crear la tabla de usuarios
def init_db():
    conn = sqlite3.connect('notifications.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER,
                    task TEXT,
                    notify_date TEXT
                )''')
    conn.commit()
    conn.close()

# Función para añadir un usuario
def add_user(telegram_id, notify_date, task_name):
    conn = sqlite3.connect('notifications.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (telegram_id, task, notify_date) VALUES (?, ?, ?)", (telegram_id,task_name, notify_date))
    conn.commit()
    conn.close()

# Función para obtener todos los usuarios con notificaciones pendientes
def get_users():
    conn = sqlite3.connect('notifications.db')
    c = conn.cursor()
    c.execute("SELECT telegram_id, notify_date, task, id FROM users")
    users = c.fetchall()
    conn.close()
    return users

# Función para eliminar usuarios después de la notificación
def remove_user(task_id, telegram_id):
    conn = sqlite3.connect('notifications.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ? AND telegram_id = ?", (task_id,telegram_id))
    conn.commit()
    conn.close()



def get_tasks(telegram_id):
    conn = sqlite3.connect('notifications.db')
    c = conn.cursor()
    c.execute("SELECT task, notify_date, id FROM users WHERE telegram_id = ?", (telegram_id,))
    
    # Usar fetchall() para obtener todas las tareas
    tasks = c.fetchall()
    conn.close()
    return tasks  # Retorna la lista de tareas