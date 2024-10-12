import logging
from telegram.ext import Updater, CommandHandler
#from databaseBot import init_db, add_user, get_users, remove_user, get_tasks
from database2 import init_db, add_user, get_users, remove_user, get_tasks
import schedule
import time
import threading
from datetime import datetime
import os
import google.generativeai as genai
import os


genai.configure(api_key=os.environ["API_KEY"])

model = genai.GenerativeModel("gemini-1.5-flash")

TOKEN = os.getenv('TELEGRAM_TOKEN')

# Configuración del token de tu bot de Telegram


# Configurar logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Lista de chat_id permitidos
AUTHORIZED_IDS = [958392218, 6231783748]  # Agrega aquí los chat_id autorizados

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
        
        update.message.reply_text(f'Notificación para "{task_name}" programada para {notify_date}.')
        prompt = f"puedes darme informacion sobre la tarea: {task_name} y podrias darme recursos como links, imagenes o videos"
        response =process_question(prompt)
        update.message.reply_text(f"{response}")
    except ValueError:
        update.message.reply_text('Formato incorrecto. Usa: /add tarea @ YYYY-MM-DD')
    except Exception as e:
        update.message.reply_text('Ocurrió un error al programar la notificación.')
        print(e)

# Función para manejar el comando /list con restricción
def listTasks(update, context):
    if not is_authorized(update):
        update.message.reply_text("🚫 No estás autorizado para usar este bot.")
        return
    try:
        # Verificar si update.message es None
        if update.message is None:
            logging.error('El objeto update.message es None')
            return
        
        logger.info(f'chat_id: {update.message.chat_id}')  # Log de chat_id
        tasks = get_tasks(update.message.chat_id)
        
        # Manejo de la respuesta cuando no hay tareas
        if not tasks:  # Si la lista de tareas está vacía
            update.message.reply_text('No tienes tareas programadas.')
            return
        
        message = '📋 **Tus tareas:**\n\n'
        
        # Iterar sobre todas las tareas
        for task in tasks:
            task_name, date_task, id = task
            message += f"**Tarea:** {task_name}\n**Fecha de entrega:** {date_task}\n**ID:** {id}\n\n"
        
        update.message.reply_text(message, parse_mode='Markdown')
    
    except Exception as e:    
        logger.error(f'Error al obtener las tareas: {e}')  # Log del error
        update.message.reply_text('Ocurrió un error al obtener las tareas.')

# Función para manejar el comando /delete con restricción
def remove_task(update, context):
    if not is_authorized(update):
        update.message.reply_text("🚫 No estás autorizado para usar este bot.")
        return
    try:
        # Obtener el ID de la tarea
        task_id = context.args[0]
        telegram_id = update.message.chat_id
        # Eliminar la tarea de la base de datos
        remove_user(task_id, telegram_id)
        
        update.message.reply_text('Tarea eliminada exitosamente.')
    except Exception as e:
        update.message.reply_text('Ocurrió un error al eliminar la tarea.')
        print(e)
                

# El resto del código sigue igual...

# Función para enviar las notificaciones
def send_notifications(updater):
    users = get_users()
    now = datetime.now().date()  # Obtener solo la fecha actual

    logger.info(f'Hora actual: {now}')  # Log de la fecha actual

    for user in users:
        telegram_id, notify_date, task, id = user
        logger.info(f'Comprobando usuario: {telegram_id}, Notificación: {notify_date}, Tarea: {task}')  # Log de usuario y tarea

        # Asegurarse de que notify_date sea de tipo date
        if isinstance(notify_date, datetime):
            notify_date = notify_date.date()

        # Calcular la diferencia en días
        days_difference = (notify_date - now).days
        
        if days_difference == 0:
            updater.bot.send_message(chat_id=telegram_id, text=f"¡Debes entregar la tarea: {task}!")
            remove_user(id, telegram_id)
        elif days_difference == 1:
            updater.bot.send_message(chat_id=telegram_id, text=f"¡Debes entregar la tarea: {task} mañana!")
        elif days_difference == 3:
            updater.bot.send_message(chat_id=telegram_id, text=f"¡Recuerda debes entregar la tarea: {task} en {days_difference} días!")
        elif days_difference > 8:
            prompt = f"puedes darme informacion sobre la tarea: {task} y podrias darme recursos como links, imagenes o videos"
            response =process_question(prompt)
            updater.bot.send_message(chat_id=telegram_id, text=f"¡Debes entregar la tarea: {task} en una semana!") 
            updater.bot.send_message(chat_id=telegram_id, text=f"{response}")
        else:
            logger.info(f'No hay coincidencia para {telegram_id}. Se esperaba {notify_date}.')




def chat(update, context):
    if not is_authorized(update):
        update.message.reply_text("🚫 No estás autorizado para usar este bot.")
        return
    try:
        # Obtener el ID de la tarea
        question = ' '.join(context.args)
      
        # Generar la respuesta del modelo
        prompt = f"responde de manera inteligente esta pregunta, no inventes cosas si no lo sabes, ademas suministra recursos como links, videos y mas cosas relacionadas con el tema y responde de manera casual pero precisa y un poco cientifica: {question}"
        response = process_question(prompt)
        
        update.message.reply_text(response)
    except Exception as e:
        update.message.reply_text('Ocurrió un error al conectar con el modelo.')
        print(e)


def process_question(question):
    try:
        # Generar la respuesta del modelo (simulado)
        response = model.generate_content(question)
        texto = response.text
        
        
        return texto

    except Exception as e:
        print(f"Error procesando la pregunta: {e}")
        return None



# Mantén el resto del código igual

def notification_scheduler(updater):
    while True:
        schedule.run_pending()
        time.sleep(1)

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

    # Configurar el horario para verificar notificaciones cada día
    schedule.every().day.at("00:00").do(lambda: send_notifications(updater))  # Revisa cada día a medianoche
    #schedule.every(60).seconds.do(lambda: send_notifications(updater))
    #schedule.every(5).minutes.do(lambda: send_notifications(updater))
    # Ejecutar el scheduler en un hilo separado
    notification_thread = threading.Thread(target=lambda: notification_scheduler(updater))
    notification_thread.start()

    updater.idle()

if __name__ == '__main__':
    main()
