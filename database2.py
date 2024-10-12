from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import BigInteger
from datetime import datetime
import os

# USERNSAME = os.getenv('DBUSERNAME')
# PASSWORD = os.getenv('DBPASSWORD')
# DBNAME = os.getenv('DBNAME')

# print(USERNSAME, PASSWORD, DBNAME)

# # Configuración de la base de datos PostgreSQL
# DATABASE_URL = f'postgresql://{USERNSAME}:{PASSWORD}@localhost:5432/{DBNAME}'


# URL de conexión a la base de datos

DATABASE_URL = os.getenv('DATABASE_URL')


# Creación del motor de la base de datos
engine = create_engine(DATABASE_URL)

# Creación de la base de datos base
Base = declarative_base()

# Definición del modelo de usuarios
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, nullable=False)
    task = Column(String, nullable=False)
    notify_date = Column(DateTime, nullable=False)

# Creación de la sesión
Session = sessionmaker(bind=engine)
session = Session()

# Función para inicializar la base de datos
def init_db():
    Base.metadata.create_all(engine)

# Función para añadir un usuario
def add_user(telegram_id, notify_date, task_name):
    new_user = User(telegram_id=telegram_id, task=task_name, notify_date=notify_date)
    session.add(new_user)
    session.commit()

# Función para obtener todos los usuarios con notificaciones pendientes
def get_users():
    users = session.query(User).all()
    return [(user.telegram_id, user.notify_date, user.task, user.id) for user in users]

# Función para eliminar usuarios después de la notificación
def remove_user(task_id, telegram_id):
    session.query(User).filter_by(id=task_id, telegram_id=telegram_id).delete()
    session.commit()

# Función para obtener las tareas de un usuario específico
def get_tasks(telegram_id):
    tasks = session.query(User).filter_by(telegram_id=telegram_id).all()
    return [(task.task, task.notify_date, task.id) for task in tasks]
