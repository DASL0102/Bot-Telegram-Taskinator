import logging
from telegram.ext import Updater, CommandHandler
from database2 import init_db, add_user, get_users, remove_user, get_tasks
import schedule
import time
import threading
from datetime import datetime
import os
import google.generativeai as genai
from flask import Flask

# Configura la API de Google Generative AI
genai.configure(api_key=os.environ.get("API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

# Configuración del token de tu bot de Telegram
TOKEN = os.getenv('TELEGRAM_TOKEN')

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Lista de chat_id permitidos
AUTHORIZED_IDS = [958392218, 6231783748]  # Agrega aquí los chat_id autorizados

# Inicializa Flask para vincularlo a un puerto
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot de Telegram ejecutándose correctamente."

# Función para verificar si el usuario está autorizado
def is_authorized(update):
    return update.message.chat_id in AUTHORIZED_IDS

# Función para manejar el comando /start con restricción
def start(update, context):
    if not is_authorized(update):
        update.message.reply_text("🚫 No estás autorizado para usar este bot.")
        return

    update.message.reply_text(
        'Hola! 👋 Soy tu bot de recordatorios.\n\n'
        'Usa los siguientes comandos para interactuar conmigo:\n'
        '/add <tarea> @ YYYY-MM-DD - Añadir una nueva tarea\n'
        '/list - Listar todas tus tareas\n'
        '/delete <id> - Eliminar una tarea por su ID\n'
        '/chat <pregunta> - Obtener una respuesta de forma inteligente'
    )

# Función para manejar el comando /add con restricción
def addTask(update, context):
    if not is_authorized(update):
        update.message.reply_text("🚫 No estás autorizado para usar este bot.")
        return
    try:
        # Obtener el texto completo del mensaje
        full_message = ' '.join(context.args)
        
        # Dividir el mensaje en partes
        task_name, date_str = full_message.rsplit('@', 1)

        # Limpiar el nombre de la tarea
        task_name = task_name.strip()
        
        # Limpiar y obtener la fecha
        date_str = date_str.strip()

        # Convertir a datetime para validarlo (solo la fecha)
        notify_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Agregar el usuario y la tarea a la base de datos
        add_user(update.message.chat_id, notify_date, task_name)
        telegram_id = update.message.chat_id
        
        update.message.reply_text(f'📅 Notificación para "{task_name}" programada para {notify_date}.')
        
        # Generar información adicional sobre la tarea
        prompt = f"puedes darme información sobre la tarea: {task_name} y podrías darme recursos como links, imágenes o videos"
        response = process_question(prompt)
        if response:
            update.message.reply_text(f"ℹ️ {response}")
    except ValueError:
        update.message.reply_text('❌ Formato incorrecto. Usa: /add tarea @ YYYY-MM-DD')
    except Exception as e:
        update.message.reply_text('❌ Ocurrió un error al programar la notificación.')
        logger.error(f"Error en addTask: {e}")

# Función para manejar el comando /list con restricción
def listTasks(update, context):
    if not is_authorized(update):
        update.message.reply_text("🚫 No estás autorizado para usar este bot.")
        return
    try:
        if update.message is None:
            logger.error('El objeto update.message es None')
            return
        
        telegram_id = update.message.chat_id
        logger.info(f'Obtención de tareas para chat_id: {telegram_id}')
        tasks = get_tasks(telegram_id)
        
        if not tasks:
            update.message.reply_text('📭 No tienes tareas programadas.')
            return
        
        message = '📋 **Tus tareas:**\n\n'
        
        for task in tasks:
            task_name, date_task, task_id = task
            message += f"**Tarea:** {task_name}\n**Fecha de entrega:** {date_task}\n**ID:** {task_id}\n\n"
        
        update.message.reply_text(message, parse_mode='Markdown')
    
    except Exception as e:    
        logger.error(f'Error al obtener las tareas: {e}')
        update.message.reply_text('❌ Ocurrió un error al obtener las tareas.')

# Función para manejar el comando /delete con restricción
def remove_task(update, context):
    if not is_authorized(update):
        update.message.reply_text("🚫 No estás autorizado para usar este bot.")
        return
    try:
        if not context.args:
            update.message.reply_text('❌ Por favor, proporciona el ID de la tarea a eliminar.')
            return

        task_id = context.args[0]
        telegram_id = update.message.chat_id
        
        # Eliminar la tarea de la base de datos
        removed = remove_user(task_id, telegram_id)
        if removed:
            update.message.reply_text('✅ Tarea eliminada exitosamente.')
        else:
            update.message.reply_text('❌ No se encontró una tarea con ese ID.')
    except Exception as e:
        update.message.reply_text('❌ Ocurrió un error al eliminar la tarea.')
        logger.error(f"Error en remove_task: {e}")

# Función para manejar el comando /chat con restricción
def chat(update, context):
    if not is_authorized(update):
        update.message.reply_text("🚫 No estás autorizado para usar este bot.")
        return
    try:
        if not context.args:
            update.message.reply_text('❌ Por favor, proporciona una pregunta.')
            return

        question = ' '.join(context.args)
      
        # Generar la respuesta del modelo
        prompt = (
            f"Responde de manera inteligente esta pregunta, no inventes cosas si no lo sabes, "
            f"además suministra recursos como links, videos y más cosas relacionadas con el tema, "
            f"y responde de manera casual pero precisa y un poco científica: {question}"
        )
        response = process_question(prompt)
        
        if response:
            update.message.reply_text(response)
        else:
            update.message.reply_text('❌ No se pudo generar una respuesta en este momento.')
    except Exception as e:
        update.message.reply_text('❌ Ocurrió un error al conectar con el modelo.')
        logger.error(f"Error en chat: {e}")

# Función para procesar preguntas usando el modelo de Google Generative AI
def process_question(question):
    try:
        response = model.generate_content(question)
        texto = response.text
        return texto
    except Exception as e:
        logger.error(f"Error procesando la pregunta: {e}")
        return None

# Función para enviar las notificaciones
def send_notifications(updater):
    try:
        users = get_users()
        now = datetime.now().date()  # Obtener solo la fecha actual

        logger.info(f'Hora actual: {now}')

        for user in users:
            telegram_id, notify_date, task, task_id = user
            logger.info(f'Comprobando usuario: {telegram_id}, Notificación: {notify_date}, Tarea: {task}')

            # Asegurarse de que notify_date sea de tipo date
            if isinstance(notify_date, datetime):
                notify_date = notify_date.date()

            # Calcular la diferencia en días
            days_difference = (notify_date - now).days
            
            if days_difference == 0:
                updater.bot.send_message(chat_id=telegram_id, text=f"⏰ ¡Debes entregar la tarea: {task} hoy!")
                remove_user(task_id, telegram_id)
            elif days_difference == 1:
                updater.bot.send_message(chat_id=telegram_id, text=f"🔔 ¡Debes entregar la tarea: {task} mañana!")
            elif days_difference == 3:
                updater.bot.send_message(chat_id=telegram_id, text=f"📅 ¡Recuerda que debes entregar la tarea: {task} en {days_difference} días!")
            elif days_difference == 7:
                updater.bot.send_message(chat_id=telegram_id, text=f"🗓️ ¡Debes entregar la tarea: {task} en una semana!")
                prompt = f"puedes darme información sobre la tarea: {task} y podrías darme recursos como links, imágenes o videos"
                response = process_question(prompt)
                if response:
                    updater.bot.send_message(chat_id=telegram_id, text=f"ℹ️ {response}")
            else:
                logger.info(f'No hay coincidencia para {telegram_id}. Se esperaba {notify_date}.')
    except Exception as e:
        logger.error(f"Error en send_notifications: {e}")

# Scheduler para ejecutar las notificaciones en intervalos definidos
def notification_scheduler(updater):
    while True:
        schedule.run_pending()
        time.sleep(1)

# Inicializa y configura el bot de Telegram
def main():
    # Iniciar la base de datos
    init_db()

    # Iniciar el bot de Telegram
    updater = Updater(TOKEN, use_context=True)

    # Registrar los comandos
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("add", addTask))
    dp.add_handler(CommandHandler("list", listTasks))
    dp.add_handler(CommandHandler("delete", remove_task))
    dp.add_handler(CommandHandler("chat", chat))

    # Iniciar el bot
    updater.start_polling()
    logger.info("Bot de Telegram iniciado y escuchando comandos.")

    # Configurar el horario para verificar notificaciones cada día a medianoche
    schedule.every().day.at("00:00").do(lambda: send_notifications(updater))
    logger.info("Scheduler configurado para enviar notificaciones diariamente a medianoche.")

    # Ejecutar el scheduler en un hilo separado
    notification_thread = threading.Thread(target=notification_scheduler, args=(updater,))
    notification_thread.daemon = True  # Permite que el hilo se cierre al finalizar el programa
    notification_thread.start()
    logger.info("Thread del scheduler iniciado.")

    # Iniciar el servidor Flask para que Render detecte el puerto
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == '__main__':
    main()
