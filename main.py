import random
from configparser import ConfigParser

from sqlalchemy.orm import session

from db.base import Session
import re

from timezonefinder import TimezoneFinder
import pytz
import datetime

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

import utils.consts as consts
import utils.buffer as buffer

from db.subscriber import Subscriber
from db.subscription import Subscription
from db.statistics import Statistics

import db.populate

import actors.composer as composer

from utils.utils import (
    get_epoch, 
    utc_offset_to_int, 
    epoch_to_date,
    get_logger,
    is_admin,
    admin_message_formatter,
)
from utils.helpers import (
    fetch_subscriber,
    persist_buffer,
    clean_db,
    print_subscription,
    prepare_subscriptions_reply,
    persisted_subscription,
    prepare_studies_reply,
    delete_subscriber,
    get_study_subscription_by_acronym
)

import actors.scheduler as scheduler
import actors.sender as sender
import actors.actuary as actuary
import actors.quizzer as quizzer


# Setup the config
config = ConfigParser()
config.read(consts.CONFIG_FILE_NAME)

logger = get_logger()

START_FIRST_SUBSCRIPTION, ADD_NEW_SUBSCRIPTION, TIME_ZONE, PREFERRED_TIME, \
NEW_SUBSCRIPTION_KEEP_PREFERENCES, MAKE_ADJUSTMENTS, DEVOTIONAL, \
CONFIRMATION, CHANGE, CHANGE_TIME_ZONE, CHANGE_PREFERRED_TIME, \
CHANGE_DEVOTIONAL, UNSUBSCRIPTION_CONFIRMATION, QUIZ, \
MATERIAL_UNSUBSCRIPTION, PROCESS_SELECT_STUDY_QUIZ = range(16)

tf = TimezoneFinder()

def start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation and asks the user if he/she wants to make a subscription."""
    user = update.message.from_user

    subscriber = fetch_subscriber(user.id)

    if subscriber == None:
        buffer.add_subscriber(Subscriber(id=user.id, creation_utc=get_epoch()))

        update.message.reply_text(
            f'¡Hola, {user.first_name}! Soy el bot del ministerio digital Una Mirada de Fe y Esperanza. '
            'Mi función es enviar devocionales o lecturas de su elección a su hora preferida. '
            'Vamos a tener una pequeña conversación para apuntar el material de su elección y su hora preferida.\n\n'
            '¿Quere recibir las matutinas/lecturas?',
            reply_markup=ReplyKeyboardMarkup(
                consts.YES_NO_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Sí?'
            ),
        )
        return START_FIRST_SUBSCRIPTION
    else:
        buffer.add_subscriber(subscriber)
        update.message.reply_text(
            f'¡Me alegro verle de vuelta, {user.first_name}!\n\n'
            '¿Quiere hacer una nueva suscripción?',
            reply_markup=ReplyKeyboardMarkup(
                consts.YES_NO_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Sí?'
            ),
        )
        return ADD_NEW_SUBSCRIPTION
        

def start_first_subscription(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    if not re.match(consts.YES_NO_RE_PATTERN, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.'
            '¿Quere recibir las matutinas/lecturas? (Sí/No)',
            reply_markup=ReplyKeyboardMarkup(
                consts.YES_NO_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Sí?'
            ),
        )
        return START_FIRST_SUBSCRIPTION

    if update.message.text == 'Sí':
        update.message.reply_text(
            '✅->⭕->⭕->⭕->⭕\n'
            'Para enviar las matutinas a su hora de preferencia, necesito saber su zona horaria. '
            'Para ello envíeme su ubicación. '
            'Respeto mucho su privacidad y no guardo sus datos, solo extraigo la zona horaria de la ubicación.\n\n'
            'Si no quiere hacerlo marque /saltar. En tal caso su matutina/lectura le llegaría a las '
            '10pm Pacific Standard Time (PST) del día anterior.',
            reply_markup=ReplyKeyboardRemove(),
        )
        return TIME_ZONE
    elif update.message.text == 'No':
        buffer.clean(user.id)

        update.message.reply_text(
            'De acuerdo. ¡Espero verle de vuelta pronto!', reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END


def add_new_subscription(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    if not re.match(consts.YES_NO_RE_PATTERN, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.'
            '¿Quere hacer una nueva suscripción? (Sí/No)',
            reply_markup=ReplyKeyboardMarkup(
                consts.YES_NO_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Sí?'
            ),
        )
        return ADD_NEW_SUBSCRIPTION

    if update.message.text == 'Sí':
        if buffer.subscribers[user.id].has_subscriptions():
            update.message.reply_text(
                '✅->⭕->⭕->⭕->⭕\n'
                f'¡Estupendo, {user.first_name}! ¿Quiere mantener las preferencias de envío de su última suscripción? '
                'La puede ver abajo: \n\n'
                f'{print_subscription(buffer.subscribers[user.id].subscriptions[-1])}',
                reply_markup=ReplyKeyboardMarkup(
                    consts.YES_NO_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Sí?'
                ),
            )
            return NEW_SUBSCRIPTION_KEEP_PREFERENCES
        else:
            if not buffer.subscribers[user.id].skipped_timezone():
                update.message.reply_text(
                    '✅->✅->⭕->⭕->⭕\n'
                    f'Recuerdo que su zona horaria era {buffer.subscribers[user.id].time_zone}.\n\n'
                    '¿A qué hora querría recibir el material? (am - mañana, pm - tarde)',
                    reply_markup=ReplyKeyboardMarkup(
                        consts.HOUR_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Cuál es su hora preferida?'
                    ),
                )
                now_utc = pytz.utc.localize(datetime.datetime.utcnow())
                now_user = now_utc.astimezone(pytz.timezone(buffer.subscribers[user.id].time_zone))
                buffer.add_subscription(Subscription(subscriber_id=user.id, utc_offset=utc_offset_to_int(now_user.isoformat()[-6:]), creation_utc=get_epoch()))
                return PREFERRED_TIME
            else:
                update.message.reply_text(
                    '✅->✅->✅->⭕->⭕\n'
                    '¡De acuerdo! Recuerdo que Usted no había indicado su zona horaria y por lo tanto recibiría '
                    'las matutinas/lecturas a las 10pm Pacific Standard Time (PST) del día anterior.\n\n'
                    '¿Qué devocional/lectura querría recibir?',
                    reply_markup=ReplyKeyboardMarkup(
                        consts.DEVOTIONALS_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Maranata?'
                    ),
                )
                buffer.add_subscription(Subscription(subscriber_id=user.id, preferred_time_local='10pm', utc_offset=-700, creation_utc=get_epoch()))
                return DEVOTIONAL
    elif update.message.text == 'No':
        buffer.clean(user.id)

        update.message.reply_text(
            'De acuerdo. ¡Espero verle de vuelta pronto!', reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END


def new_subscription_keep_preferences(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    if not re.match(consts.YES_NO_RE_PATTERN, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.'
            '¿Quere mantener las preferencias de envío de su última suscripción? (Sí/No)\n\n'
            f'{print_subscription(buffer.subscribers[user.id].subscriptions[-1])}',
            reply_markup=ReplyKeyboardMarkup(
                consts.YES_NO_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Sí?'
            ),
        )
        return NEW_SUBSCRIPTION_KEEP_PREFERENCES

    last_subscription = buffer.subscribers[user.id].subscriptions[-1]
    if update.message.text == 'Sí':
        buffer.add_subscription(Subscription(subscriber_id=last_subscription.subscriber_id, \
                                             preferred_time_local=last_subscription.preferred_time_local, \
                                             utc_offset=last_subscription.utc_offset, \
                                             creation_utc=get_epoch()))
        if not buffer.subscribers[user.id].skipped_timezone():
            update.message.reply_text(
                '✅->✅->✅->⭕->⭕\n'
                f'De acuerdo. Ya sé que su zona horaria es {buffer.subscribers[user.id].time_zone} y '
                f'Usted quiere recibir el devocional/lectura a la(s) {buffer.subscriptions[user.id].preferred_time_local}.\n\n'
                '¿Qué material querría recibir? Estamos trabajando para añadir más libros.',
                reply_markup=ReplyKeyboardMarkup(
                    consts.DEVOTIONALS_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Maranata?'
                ),
            )
        else:
            update.message.reply_text(
                '✅->✅->✅->⭕->⭕\n'
                f'De acuerdo. Sé que usted no había indicado su zona horaria anteriormente y '
                f'por lo tanto va a recibir el material a la(s) {buffer.subscriptions[user.id].preferred_time_local} del PST.\n\n'
                '¿Qué devocional/lectura querría recibir? Estamos trabajando para añadir más libros.',
                reply_markup=ReplyKeyboardMarkup(
                    consts.DEVOTIONALS_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Maranata?'
                ),
            )
        return DEVOTIONAL
    elif update.message.text == 'No':
        if buffer.subscribers[user.id].skipped_timezone():
            update.message.reply_text(
                '✅->⭕->⭕->⭕->⭕\n'
                f'{user.first_name}, para poder enviarle el devocional/lectura a su hora preferida necesito saber su zona horaria '
                'y la forma más conveniente de hacerlo es a través de su ubicación. '
                'Usted no me ha enviado su ubicación anteriormente. Para poder extraer su zona horaria mándeme su '
                'ubicación o marque /saltar para seguir con su última configuración.', 
                reply_markup=ReplyKeyboardRemove()
            )
            return TIME_ZONE
        else:
            buffer.add_subscription(Subscription(subscriber_id=last_subscription.subscriber_id, \
                                             preferred_time_local=last_subscription.preferred_time_local, \
                                             utc_offset=last_subscription.utc_offset, \
                                             creation_utc=get_epoch()))
            update.message.reply_text(
                '✅->✅->⭕->⭕->⭕\n'
                'No hay problema, mis creadores han pensado en que podría querer elegir una hora diferente.\n\n'
                '¿A qué hora querría recibir el material? (am - mañana, pm - tarde)', 
                reply_markup=ReplyKeyboardMarkup(
                    consts.HOUR_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿La hora para esta lectura?'
                ),
            )
            return PREFERRED_TIME

    return ConversationHandler.END


def geo_skip(update: Update, context: CallbackContext) -> int:
    """Skips the location and asks for info about the user."""
    user = update.message.from_user
    
    buffer.subscribers[user.id].time_zone = 'skipped'
    # -07:00 -> -0700 -> -700
    buffer.add_subscription(Subscription(subscriber_id=user.id, preferred_time_local='10pm', utc_offset=-700, creation_utc=get_epoch()))

    update.message.reply_text(
        '✅->✅->✅->⭕->⭕\n'
        f'¡{user.first_name}, no hay problema. Usted recibirá el material a las 10pm PST del día anterior. '
        '¡Nos queda un paso para terminar!\n\n'
        '¿Qué devocional/lectura querría recibir? Estamos trabajando para añadir más libros.',
        reply_markup=ReplyKeyboardMarkup(
            consts.DEVOTIONALS_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Maranata?'
        ),
    )

    return DEVOTIONAL

def time_zone(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    user_location = update.message.location

    if user_location == None:
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido. '
            'Envíeme su ubicación o salte este paso marcando /saltar.',
            reply_markup=ReplyKeyboardRemove()
        )
        return TIME_ZONE

    buffer.subscribers[user.id].time_zone = tf.timezone_at(lat=user_location.latitude, lng=user_location.longitude)
    logger.info(f'User {user.first_name} time zone is {buffer.subscribers[user.id].time_zone}')
    
    now_utc = pytz.utc.localize(datetime.datetime.utcnow())
    now_user = now_utc.astimezone(pytz.timezone(buffer.subscribers[user.id].time_zone))
    
    buffer.add_subscription(Subscription(subscriber_id=user.id, utc_offset=utc_offset_to_int(now_user.isoformat()[-6:]), creation_utc=get_epoch()))

    if not buffer.subscribers[user.id].skipped_timezone():
        update.message.reply_text(
            '✅->✅->⭕->⭕->⭕\n'
            f'¡Estupendo! Ya sé que su zona horaria es {buffer.subscribers[user.id].time_zone}.\n\n'
            '¿A qué hora querría recibir el material? (am - mañana, pm - tarde)',
            reply_markup=ReplyKeyboardMarkup(
                consts.HOUR_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Cuál es su hora preferida?'
            ),
        )
    else:
        update.message.reply_text(
            '✅->✅->✅->⭕->⭕\n'
            '¡Estupendo! Usted recibirá las matutinas/lecturas a las 10pm Pacific Standard Time (PST) del día anterior.\n\n'
            '¿Qué devocional/lectura querría recibir?',
            reply_markup=ReplyKeyboardMarkup(
                consts.DEVOTIONALS_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Maranata?'
            ),
        )
        return DEVOTIONAL

    return PREFERRED_TIME

def preferred_time(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    if not re.match(consts.HOUR_RE_PATTERN, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.'
            '¿A qué hora querría recibir la lectura? (am - mañana, pm - tarde)',
            reply_markup=ReplyKeyboardMarkup(
                consts.HOUR_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Cuál es su hora preferida?'
            ),
        )
        return PREFERRED_TIME

    buffer.subscriptions[user.id].update_preferred_time_local(update.message.text)

    update.message.reply_text(
        '✅->✅->✅->⭕->⭕\n'
        f'¡{user.first_name}, nos queda un paso para terminar! '
        f'Ya sé que su zona horaria es {buffer.subscribers[user.id].time_zone} y '
        f'quiere recibir el material a la(s) {buffer.subscriptions[user.id].preferred_time_local}.\n\n'
        '¿Qué devocional/lectura querría recibir? Estamos trabajando para añadir más libros.',
        reply_markup=ReplyKeyboardMarkup(
            consts.DEVOTIONALS_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Maranata?'
        ),
    )

    return DEVOTIONAL

def devotional(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    if not re.match(consts.DEVOTIONALS_RE_PATTERN, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.'
            '¿Qué devocional/lectura querría recibir?',
            reply_markup=ReplyKeyboardMarkup(
                consts.DEVOTIONALS_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Maranata?'
            ),
        )
        return DEVOTIONAL

    if buffer.subscribers[user.id].subscribed(update.message.text):
        update.message.reply_text(
            f'{user.first_name}, Usted ya está suscrito/a a esta lectura. Marque\n'
            '/estado para ver el estado de sus suscripciones,\n'
            '/ajustar para cambiar las preferencias de sus suscripciones,\n'
            '/start para hacer una nueva suscripción.',
            reply_markup=ReplyKeyboardRemove()
        )
        buffer.clean(user.id)
        return ConversationHandler.END

    buffer.subscriptions[user.id].title = update.message.text

    if not buffer.subscribers[user.id].skipped_timezone():
        update.message.reply_text(
            '✅->✅->✅->✅->⭕\n'
            '¡Ya estamos listos! Ya sé que ' 
            f'su zona horaria es {buffer.subscribers[user.id].time_zone} y '
            f'quiere recibir el material {buffer.subscriptions[user.id].title} '
            f'cada día a la(s) {buffer.subscriptions[user.id].preferred_time_local}.\n\n'
            '¿Es correcto?',
            reply_markup=ReplyKeyboardMarkup(
                consts.YES_NO_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Sí?'
            ),
        )
    else:
        update.message.reply_text(
            '✅->✅->✅->✅->⭕\n'
            '¡Ya estamos listos! Ya sé que ' 
            f'Usted quiere recibir el material {buffer.subscriptions[user.id].title} a las 10pm PST (Pacific Standard Time) del día anterior.\n\n'
            '¿Es correcto?',
            reply_markup=ReplyKeyboardMarkup(
                consts.YES_NO_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Sí?'
            ),
        )

    return CONFIRMATION

def confirmation(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    if not re.match(consts.YES_NO_RE_PATTERN, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.\n\n'
            '¿Está de acuerdo?',
            reply_markup=ReplyKeyboardMarkup(
                consts.YES_NO_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Sí?'
            ),
        )
        return CONFIRMATION

    if update.message.text == 'Sí':
        status_bar = '✅->✅->✅->✅->✅\n' if not persisted_subscription(buffer.subscriptions[user.id]) else ''
        update.message.reply_text(
            f'{status_bar}'
            '¡Ya está todo configurado! Puede marcar los siguientes comandos:\n'
            '/start para hacer una nueva y diferente suscripcón,\n'
            '/ajustar para ajustar su suscripción,\n'
            '/estado para ver el estado de su suscripción,\n'
            '/ayuda para obtener lista de comandos,\n'
            '/contacto para contactar con nosotros,\n'
            '/recuento para ver las estadísticas,\n'
            '/baja para dejar de recibir los materiales.\n\n'
            '¡Muchas gracias y esperamos que sea para su gran bendición!'
        )
        persist_buffer(user.id)
        buffer.clean(user.id)
    elif update.message.text == 'No':
        update.message.reply_text(
            'Por favor, indíqueme lo que tengo que cambiar. Para cancelar el proceso marque /cancelar',
            reply_markup=ReplyKeyboardMarkup(
                consts.PREFERENCE_CHANGE_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Qué cambio?'
            ),
        )
        return CHANGE

    return ConversationHandler.END

def change(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    if not re.match(consts.PREFERENCE_CHANGE_RE_PATTERN, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.\n\n'
            'Por favor, indíqueme lo que tengo que cambiar.',
            reply_markup=ReplyKeyboardMarkup(
                consts.PREFERENCE_CHANGE_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Qué cambio?'
            ),
        )
        return CHANGE

    if update.message.text == 'País':
        if not buffer.subscribers[user.id].skipped_timezone():
            update.message.reply_text(
                f'{user.first_name}, hasta encontes sabía que su zona horaria era {buffer.subscribers[user.id].time_zone}.\n\n'
                'Mándeme de nuevo su ubicación o marque /eliminar para eliminar la información actual. '
                'Eliminando la información actual pasaría a recibir todas las suscripciones a las 10pm PST del día anterior.',
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            update.message.reply_text(
                f'{user.first_name}, hasta encontes sabía que Usted ha preferido no compartir su ubicación. '
                'Por lo tanto, Usted iba a recibir las matutinas/lecturas a las 10pm PST del día anterior.\n\n'
                'Mándeme de nuevo su ubicación si quiere recibir el material a su hora preferida.',
                reply_markup=ReplyKeyboardRemove(),
            )
        return CHANGE_TIME_ZONE
    elif update.message.text == 'Hora':
        if not buffer.subscribers[user.id].skipped_timezone():
            subscription = buffer.subscriptions[user.id]
            update.message.reply_text(
                f'{user.first_name}, hasta encontes sabía que Usted quería recibir el material a la(s) {subscription.preferred_time_local}.\n\n'
                '¿A qué hora quiere cambiar?',
                reply_markup=ReplyKeyboardMarkup(
                    consts.HOUR_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿A qué hora?'
                ),
            )
        else:
            update.message.reply_text(
                f'{user.first_name}, para cambiar la hora Usted me tiene que enviar su ubicación pinchando \'País\'. '
                'De otro modo no puedo saber cuál es su zona horaria para enviarle el material a su hora.\n\n',
                reply_markup=ReplyKeyboardMarkup(
                    consts.PREFERENCE_CHANGE_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Qué cambio?'
                ),
            )
            return CHANGE
        return CHANGE_PREFERRED_TIME
    elif update.message.text == 'Lectura':
        subscription = buffer.subscriptions[user.id]
        update.message.reply_text(
            f'{user.first_name}, hasta encontes sabía que Usted quería recibir el material {subscription.title}\n\n'
            '¿A qué material quiere cambiar?',
            reply_markup=ReplyKeyboardMarkup(
                consts.DEVOTIONALS_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Maranata?'
            ),
        )
        return CHANGE_DEVOTIONAL
    elif update.message.text == 'Baja':
        subscription = buffer.subscriptions[user.id]
        update.message.reply_text(
            f'{user.first_name}, '
            f'¿está seguro/a que no quiere recibir más el material {subscription.title}?',
            reply_markup=ReplyKeyboardMarkup(
                consts.YES_NO_KEYBOARD, one_time_keyboard=False, input_field_placeholder=':('
            ),
        )
        return MATERIAL_UNSUBSCRIPTION
    elif update.message.text == 'Nada' or update.message.text == 'Listo':
        subscription = buffer.subscriptions[user.id]
        if not buffer.subscribers[user.id].skipped_timezone():
            update.message.reply_text(
                '¡Muy bien, recapitulemos!\n' 
                f'Su zona horaria es {buffer.subscribers[user.id].time_zone} y '
                f'quiere recibir el material {subscription.title} '
                f'cada día a la(s) {subscription.preferred_time_local}.\n\n'
                '¿Es correcto?',
                reply_markup=ReplyKeyboardMarkup(
                    consts.YES_NO_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Sí?'
                ),
            )
        else:
            update.message.reply_text(
                '¡Muy bien, recapitulemos!\n' 
                f'Usted va a recibir el material {subscription.title} a las 10pm PST del día anterior.\n\n'
                '¿Es correcto?',
                reply_markup=ReplyKeyboardMarkup(
                    consts.YES_NO_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Sí?'
                ),
            )
        return CONFIRMATION
    # unreachable return
    return ConversationHandler.END

def change_time_zone(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    user_location = update.message.location

    if user_location == None:
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.'
            'Envíeme su ubicación o elimine su información actual marcando /eliminar. '
            'Eliminando la información actual pasaría a recibir todas las suscripciones a las 10pm PST del día anterior.',
            reply_markup=ReplyKeyboardRemove()
        )
        return TIME_ZONE

    buffer.subscribers[user.id].time_zone = tf.timezone_at(lat=user_location.latitude, lng=user_location.longitude)
    logger.info(f'User {user.first_name} time zone is {buffer.subscribers[user.id].time_zone}')
    
    now_utc = pytz.utc.localize(datetime.datetime.utcnow())
    now_user = now_utc.astimezone(pytz.timezone(buffer.subscribers[user.id].time_zone))
    
    subscription = buffer.subscriptions[user.id]
    subscription.update_utc_offset(utc_offset_to_int(now_user.isoformat()[-6:]))

    update.message.reply_text(
        f'¡Estupendo! A partir de ahora sé que su zona horaria es {buffer.subscribers[user.id].time_zone}, '
        f'quiere recibir el material {subscription.title} '
        f'cada día a la(s) {subscription.preferred_time_local}.\n\n'
        '¿Quiere cambiar algo más?',
        reply_markup=ReplyKeyboardMarkup(
            consts.CONT_PREFERENCE_CHANGE_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Qué cambio?'
        ),
    )

    return CHANGE

def geo_remove(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    subscriber = buffer.subscribers[user.id]
    
    subscriber.time_zone = 'skipped'
    for subscription in subscriber.subscriptions:
        subscription.update_preferred_time_local('10pm')
        subscription.update_utc_offset(-700)

    update.message.reply_text(
        f'¡Hecho! He eliminado su zona horaria. A partir de ahora recibirá todas sus suscripciones a las 10pm PST del día anterior.\n\n'
        '¿Qué más querría cambiar?',
        reply_markup=ReplyKeyboardMarkup(
            consts.CONT_PREFERENCE_CHANGE_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Qué cambio?'
        ),
    )

    return CHANGE


def change_preferred_time(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    if not re.match(consts.HOUR_RE_PATTERN, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido. '
            'Por favor, elija la hora de selección.',
            reply_markup=ReplyKeyboardMarkup(
                consts.HOUR_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Qué hora apunto?'
            ),
        )
        return CHANGE_PREFERRED_TIME

    subscription = buffer.subscriptions[user.id]
    subscription.update_preferred_time_local(update.message.text)

    update.message.reply_text(
        f'¡Bien! Con ese cambio sé que su zona horaria es {buffer.subscribers[user.id].time_zone}, '
        f'quiere recibir el material {subscription.title} '
        f'cada día a la(s) {subscription.preferred_time_local}.\n\n'
        '¿Desea realizar algún cambio más?',
        reply_markup=ReplyKeyboardMarkup(
            consts.CONT_PREFERENCE_CHANGE_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Qué cambio?'
        ),
    )

    return CHANGE

def change_devotional(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    if not re.match(consts.DEVOTIONALS_RE_PATTERN, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.'
            'Por favor, seleccione alguna lectura disponible.',
            reply_markup=ReplyKeyboardMarkup(
                consts.DEVOTIONALS_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Qué lectura apunto ahora?'
            ),
        )
        return CHANGE_DEVOTIONAL
    
    session = Session()
    material_duplicate = session \
        .query(Subscription) \
        .filter(
            Subscription.subscriber_id == user.id,
            Subscription.title == update.message.text
        ) \
        .all()
    session.close()

    if len(material_duplicate) > 0:
        update.message.reply_text(
            'Usted ya está suscrito/a a este material. Por favor, '
            'cambie otra preferencia.',
            reply_markup=ReplyKeyboardMarkup(
                consts.CONT_PREFERENCE_CHANGE_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Qué cambio?'
            ),
        )
        return CHANGE

    subscription = buffer.subscriptions[user.id]
    subscription.title = update.message.text

    if not buffer.subscribers[user.id].skipped_timezone():
        update.message.reply_text(
            f'¡Bien! Actualmente sé que su zona horaria es {buffer.subscribers[user.id].time_zone}, '
            f'quiere recibir el material {subscription.title} '
            f'cada día a la(s) {subscription.preferred_time_local}.\n\n'
            '¿Desea cambiar algo más?',
            reply_markup=ReplyKeyboardMarkup(
                consts.CONT_PREFERENCE_CHANGE_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Qué cambio?'
            ),
        )
    else:
        update.message.reply_text(
            f'¡Bien! Actualmente sé que va a recibir el material {subscription.title} '
            ' las 10pm PST del día anterior.\n\n'
            '¿Desea cambiar algo más?',
            reply_markup=ReplyKeyboardMarkup(
                consts.CONT_PREFERENCE_CHANGE_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Qué cambio?'
            ),
        )

    return CHANGE


def select_subscription(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    subscriber = fetch_subscriber(user.id)

    if subscriber != None and subscriber.has_subscriptions():
        buffer.add_subscriber(subscriber)
        
        if len(subscriber.subscriptions) > 1:
            subscriptions_str, subscriptions_kb = prepare_subscriptions_reply(subscriber.subscriptions, skipped=subscriber.skipped_timezone())

            update.message.reply_text(
                f'{user.first_name}, elija la suscripción que quiere modificar según su número:\n\n'
                f'{subscriptions_str}',
                reply_markup=ReplyKeyboardMarkup(
                    subscriptions_kb, one_time_keyboard=True, input_field_placeholder='¿1? ¿2? ...'
                ),
            )
            return MAKE_ADJUSTMENTS
        else:
            return make_adjustments(update, context)
    else:
        update.message.reply_text(
            f'Lo siento, pero usted tiene que suscribirse primero para hacer ajustes.\n\n'
            'Marque /start para suscribirse.',
            reply_markup=ReplyKeyboardRemove()
        )
    return ConversationHandler.END


def make_adjustments(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    if len(buffer.subscribers[user.id].subscriptions) > 1:
        if not re.match(consts.SUBSCRIPTION_SELECT_PATTERN, update.message.text):
            subscriptions_str, subscriptions_kb = prepare_subscriptions_reply(buffer.subscribers[user.id].subscriptions, skipped=buffer.subscribers[user.id].skipped_timezone())

            update.message.reply_text(
                f'Disculpe, {user.first_name}, no le he entendido. '
                'Por favor, elija la suscripción que quiere modificar según su número:\n\n'
                f'{subscriptions_str}',
                reply_markup=ReplyKeyboardMarkup(
                    subscriptions_kb, one_time_keyboard=True, input_field_placeholder='¿1? ¿2? ...'
                ),
            )
            return MAKE_ADJUSTMENTS
        buffer.add_subscription(buffer.subscribers[user.id].subscriptions[int(update.message.text)-1])
    else:
        buffer.add_subscription(buffer.subscribers[user.id].subscriptions[0])

    update.message.reply_text(
        f'¡Ya lo tengo! {user.first_name}, ¿qué le gustaría cambiar en esta ocasión?',
        reply_markup=ReplyKeyboardMarkup(
            consts.PREFERENCE_CHANGE_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Qué cambio?'
        ),
    )
    return CHANGE


def get_status(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    subscriber = fetch_subscriber(user.id)

    if subscriber != None and subscriber.has_subscriptions():
        tz = subscriber.time_zone
        if subscriber.skipped_timezone():
            tz = 'desconocida'

        subscriptions_str = prepare_subscriptions_reply(subscriber.subscriptions, str_only=True, skipped=subscriber.skipped_timezone())
            
        update.message.reply_text(
            'Aquí tiene el estado de sus suscripciones:\n\n'
            f'Su zona horaria es {tz}.\n\n'
            f'{subscriptions_str}\n'
            'Para hacer algún cambio marque /ajustar.'
        )
    else:
        update.message.reply_text(
            f'Lo siento, pero usted tiene que suscribirse primero para ver su estado.\n\n'
            'Marque /start para suscribirse.',
            reply_markup=ReplyKeyboardRemove()
        )
    return ConversationHandler.END


def get_help(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        'Puede marcar:\n'
        '/start para hacer una suscripción,\n'
        '/estado para ver el estado de sus suscripciones,\n'
        '/ajustar para ajustar sus suscripciones,\n'
        '/ayuda para recibir ayuda,\n'
        '/contacto para contactarse con nosotros,\n'
        '/recuento para ver las estadísticas,\n'
        '/baja para dejar de recibir los materiales.\n',
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def cancelar(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user

    buffer.clean(user.id)

    update.message.reply_text(
        'Okey. Si ha hecho algún cambio durante esta conversación no ha sido guardado.\n\n'
        '¡Adiós! Espero verte de vuelta pronto...', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

def unsubscribe(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    subscriber = fetch_subscriber(user.id)
    
    if subscriber != None:
        # buffer.add_subscriber(fetch_subscriber(user.id))

        update.message.reply_text(
            f'{user.first_name}, me da mucha lástima que se vaya...\n\n'
            'Puede escribirnos marcando /contacto si algo se podría mejorar.\n\n'
            '¿Está completamente seguro?',
            reply_markup=ReplyKeyboardMarkup(
                consts.YES_NO_KEYBOARD, one_time_keyboard=False, input_field_placeholder=':('
            ),
        )
        return UNSUBSCRIPTION_CONFIRMATION
    else:
        update.message.reply_text(
            f'{user.first_name}, no tengo ninguna suscripción activa ni algún dato acerca de Usted.',
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

def unsubscription_confirmation(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    if not re.match(consts.YES_NO_RE_PATTERN, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.'
            '¿Está completamante de acuedro?',
            reply_markup=ReplyKeyboardMarkup(
                consts.YES_NO_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿No?'
            ),
        )
        return UNSUBSCRIPTION_CONFIRMATION

    if update.message.text == 'Sí':
        update.message.reply_text(
            'De acuerdo. Todas sus suscripciones han sido eliminadas.\n\n'
            'Espero que vuelva pronto...',
            reply_markup=ReplyKeyboardRemove()
        )
        delete_subscriber(user.id)
        # clean_db(user.id)
        buffer.clean(user.id)
        actuary.add_unsubscribed()
    elif update.message.text == 'No':
        update.message.reply_text(
            '¡Me alegra saber su cambio de opinión! Si puedo ayudar con algo, marque /ayuda.',
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END

def material_unsubscription_confirmation(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    if not re.match(consts.YES_NO_RE_PATTERN, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.'
            '¿Está completamante seguro?',
            reply_markup=ReplyKeyboardMarkup(
                consts.YES_NO_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿No?'
            ),
        )
        return MATERIAL_UNSUBSCRIPTION

    if update.message.text == 'Sí':
        removed_canceled = 'cancelada'
        if persisted_subscription(buffer.subscriptions[user.id]):
            buffer.subscriptions[user.id].delete()
            removed_canceled = 'eliminada'
        update.message.reply_text(
            f'De acuerdo. Su suscripción ha sido {removed_canceled}.\n\n'
            'Si puedo ayudar con algo más marque /ayuda o /ajustar',
            reply_markup=ReplyKeyboardRemove()
        )
        buffer.clean(user.id)
        actuary.add_unsubscribed()
    elif update.message.text == 'No':
        update.message.reply_text(
            '¡Me alegra saber su cambio de opinión! Si puedo ayudar con algo marque /ayuda o /ajustar',
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END

def get_statistics(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    subscriber = fetch_subscriber(user.id)
    if subscriber != None:
        by_devotional = ''
        sbd = actuary.subscriptions_by_material()
        stats = actuary.statistics()
        for s, c in sbd.items():
            by_devotional += f'  {s} : {c}\n'
        update.message.reply_text(
            f'Suscripciones : {actuary.subscriptions()}\n'
            f'{by_devotional}'
            f'Enviado : {stats.sent}',
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        update.message.reply_text(
            f'Lo siento, {user.first_name}, solo los usuarios registrados '
            'pueden ver las estadísticas.\n\n'
            'Marque /start para suscribirse.',
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END

def get_admin_statistics(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    if is_admin(user.id):
        by_devotional = ''
        sbd = actuary.subscriptions_by_material()
        stats = actuary.statistics()
        for s, c in sbd.items():
            by_devotional += f'  {s} : {c}\n'
        update.message.reply_text(
            f'Suscriptores : {actuary.subscribers()}\n'
            f'Suscripciones : {actuary.subscriptions()}\n'
            f'{by_devotional}'
            f'Sin ubicación : {actuary.geo_skipped()}\n'
            f'Enviado : {stats.sent}\n'
            f'Cuestionarios: {stats.quizzes}\n'
            f'Dieron de baja : {stats.unsubscribed}\n'
            f'Último registrado : {epoch_to_date(stats.last_registered)}\n'
            f'Último suscrito : {epoch_to_date(stats.last_subscribed)}',
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        update.message.reply_text(
            f'Lo siento, {user.first_name}, solo los administradores '
            'pueden ver las estadisticas avanzadas.\n\n',
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END

def admin_message(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    if is_admin(user.id):
        unformatted = admin_message_formatter(' '.join(context.args))
        sender.send_global_message(unformatted)
        

def admin_burst(update: Update, context: CallbackContext) -> int:
    # admin_burst receives one argument in a format 'month-day'
    #  i.e. sending /admin_rafaga 07-15 will send to all 
    #  subscribers devotionals dated on July 15. 
    user = update.message.from_user
    if is_admin(user.id):
        # str(int(...)) to remove prefixed zeros
        month = str(int(context.args[0].split('-')[0]))
        day = str(int(context.args[0].split('-')[1]))
        sender.send(all=True, month=month, day=day)


def contact(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    update.message.reply_text(
        f'{user.first_name}, para contactar con el responsable '
        'de esta iniciativa y su soporte técnico escriba a '
        '@vrykov y le antenderá personalmente.\n\n'
        '¡Muchas gracias!',
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

def select_study_quiz(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    session = Session()
    study_subscriptions = session \
        .query(Subscription) \
        .filter(
            Subscription.subscriber_id == user.id,
            Subscription.title.ilike(f'Estudio%')) \
        .all()
    session.close()

    # Possible input: 
    #   /cuestionario CS día 1
    #   /cuestionario CS capítulo 1
    if len(context.args) == 3 and (context.args[0].upper() in consts.AVAILABLE_BOOKS_ACRONYMS) and \
        context.args[1] in consts.QUIZ_SPECIFIERS and context.args[2].isdigit():
        
        study_subscription = get_study_subscription_by_acronym(study_subscriptions, context.args[0])
        if study_subscription == None:
            update.message.reply_text(
                f'{user.first_name}, Usted no está suscrito/a al estudio del libro {consts.BOOKS_ACRONYMS_LUT[context.args[0].upper()]}.\n\n'
                '¡Marque /start para hacerlo!',
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        else:
            buffer.add_subscription(study_subscription)
            reply_msg, reply_kb = quizzer.start_independent_quiz(user.id, study_subscription, context.args[1], int(context.args[2]))
            update.message.reply_text(
                reply_msg,
                reply_markup=ReplyKeyboardMarkup(
                    reply_kb, one_time_keyboard=False, input_field_placeholder='¿Tu respuesta?'
                ),
            )
            return QUIZ
    elif len(context.args) > 0:
        update.message.reply_text(
            'El uso correcto:\n\n'
            '/cuestionario <siglas del libro> día/capítulo <número>, por ejemplo\n'
            '/cuestionario CS día 1\n/cuestionario CS capítulo 5\n\n'
            'Cuestionarios diponibles para el libro El Conflicto de los Siglos - siglas - CS.',
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    if len(study_subscriptions) == 0:
        update.message.reply_text(
            f'{user.first_name}, Usted no está suscrito/a a ningún estudio. ¡Marque /start para hacerlo!',
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    elif len(study_subscriptions) == 1:
        buffer.add_subscription(study_subscriptions[0])
        return take_quiz(update, context)
    else:
        studies_str, studies_kb = prepare_studies_reply(study_subscriptions)
        update.message.reply_text(
            f'{user.first_name}, por favor, elija el estudio:\n\n'
            f'{studies_str}',
            reply_markup=ReplyKeyboardMarkup(
                studies_kb, one_time_keyboard=False, input_field_placeholder='El Tiempo de Estar Preparado'
            ),
        )
        return PROCESS_SELECT_STUDY_QUIZ

def process_study_quiz_select(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    session = Session()
    study_subscriptions = session \
        .query(Subscription) \
        .filter(
            Subscription.subscriber_id == user.id,
            Subscription.title.ilike(f'Estudio%')) \
        .all()
    session.close()

    if not re.match(consts.STUDY_SELECT_PATTERN, update.message.text):
        studies_str, studies_kb = prepare_studies_reply(study_subscriptions)
        update.message.reply_text(
            f'Disculpe, {user.first_name}, no le he entendido. '
            f'{user.first_name}, por favor, elija el estudio para generar el cuestionario correspondiente:\n\n'
            f'{studies_str}',
            reply_markup=ReplyKeyboardMarkup(
                studies_kb, one_time_keyboard=False, input_field_placeholder='El Tiempo de Estar Preparado'
            ),
        )
        return PROCESS_SELECT_STUDY_QUIZ
    buffer.add_subscription(study_subscriptions[int(update.message.text)-1])
    return take_quiz(update, context)

def take_quiz(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    if quizzer.quiz_finished(user.id):
        reply_msg, last_quiz = quizzer.quiz_report(user.id, update.message.text)

        update.message.reply_text(
            reply_msg,
            reply_markup=ReplyKeyboardRemove(),
        )

        return ConversationHandler.END
    elif quizzer.quiz_started(user.id):
        reply_msg, reply_kb = quizzer.next_question(user.id, update.message.text)
        update.message.reply_text(
            reply_msg,
            reply_markup=ReplyKeyboardMarkup(
                reply_kb, one_time_keyboard=False, input_field_placeholder='¿Tu respuesta?'
            ),
        )
        return QUIZ
    else:
        reply_msg, reply_kb = quizzer.start_quiz(user.id, buffer.subscriptions[user.id])

        if reply_msg == None and reply_kb == None:
            update.message.reply_text(
                'Lo sentimos, no hay ningún cuestionario para ese día. '
                'Si Usted está seguro/a que es un error, por favor repórtelo a @vrykov, el responsable '
                'miembro del equipo de Una Mirada de Fe y Esperanza. ¡Muchas gracias!',
                reply_markup=ReplyKeyboardRemove()
            )
            buffer.clean(user.id)
            return ConversationHandler.END 

        update.message.reply_text(
            reply_msg,
            reply_markup=ReplyKeyboardMarkup(
                reply_kb, one_time_keyboard=False, input_field_placeholder='¿Tu respuesta?'
            ),
        )
        return QUIZ

def get_prophetic_verse(update: Update, context: CallbackContext) -> int:
    prophectic_verse = random.randint(1, (consts.BIBLE_VERSES_COUNT+1) + consts.BIBLE_WHITE_MARGIN_COUNT)
    ret_content = composer.compose_prophetic_verse(prophectic_verse)

    update.message.reply_text(
        ret_content,
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

def get_bible(update: Update, context: CallbackContext) -> int:
    ret_content = None
    if len(context.args) > 1:
        ret_content = composer.compose_bible(' '.join(context.args))
    
    if ret_content == None:
        ret_content =   'El uso correcto:\n\n' \
                        '/biblia Génesis 1 (capítulo completo)\n' \
                        '/biblia Isaias 40:31 (un versículo)\n' \
                        '/biblia 1 corintios 1:1-6 (secuencia continua)\n' \
                        '/biblia apocalipsis 14:1-7,12 (secuencia(s) descontinua(s))\n'

    update.message.reply_text(
        ret_content,
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END
        
# TODO: Add /support command
# TODO: Add Friday sunset times (SunTime library - pip3 install suntime)
# TODO: Add weekly inspirational verses
# TODO: Add 365 daily counsels from Ellen G. White
# TODO: Fix scheduler to fit summer and winter time change

def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(config['bot']['token'])

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add conversation handlers
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start), 
            CommandHandler('ajustar', select_subscription),
            CommandHandler('estado', get_status),
            CommandHandler('ayuda', get_help),
            CommandHandler('baja', unsubscribe),
            CommandHandler('contacto', contact),
            CommandHandler('recuento', get_statistics),
            CommandHandler('admin_mensaje', admin_message, pass_args=True),
            CommandHandler('admin_rafaga', admin_burst, pass_args=True),
            CommandHandler('admin_recuento', get_admin_statistics),
            CommandHandler('cuestionario', select_study_quiz, pass_args=True),
            CommandHandler('versiculo', get_prophetic_verse),
            CommandHandler('biblia', get_bible, pass_args=True)
        ],
        states={
            START_FIRST_SUBSCRIPTION: [MessageHandler(Filters.text & ~Filters.command, start_first_subscription)],
            ADD_NEW_SUBSCRIPTION: [MessageHandler(Filters.text & ~Filters.command, add_new_subscription)],
            NEW_SUBSCRIPTION_KEEP_PREFERENCES: [
                MessageHandler(Filters.text & ~Filters.command, new_subscription_keep_preferences),
                CommandHandler('saltar', geo_skip)
            ],
            TIME_ZONE: [
                MessageHandler((Filters.text & ~Filters.command) | Filters.location, time_zone), 
                CommandHandler('saltar', geo_skip),
                CommandHandler('eliminar', geo_remove)
            ],
            PREFERRED_TIME: [MessageHandler(Filters.text & ~Filters.command, preferred_time)], #Filters.regex('\d\d*{am,pm}+')
            DEVOTIONAL: [MessageHandler(Filters.text & ~Filters.command, devotional)], #Filters.regex('^(¡Maranata: El Señor Viene!)$')
            CONFIRMATION: [MessageHandler(Filters.text & ~Filters.command, confirmation)],
            CHANGE: [MessageHandler(Filters.text & ~Filters.command, change)],
            MAKE_ADJUSTMENTS: [MessageHandler(Filters.text & ~Filters.command, make_adjustments)],
            CHANGE_TIME_ZONE: [
                MessageHandler((Filters.text & ~Filters.command) | Filters.location, change_time_zone), 
                CommandHandler('eliminar', geo_remove)
            ],
            CHANGE_PREFERRED_TIME: [MessageHandler(Filters.text & ~Filters.command, change_preferred_time)],
            CHANGE_DEVOTIONAL: [MessageHandler(Filters.text & ~Filters.command, change_devotional)],
            UNSUBSCRIPTION_CONFIRMATION: [MessageHandler(Filters.text & ~Filters.command, unsubscription_confirmation)],
            QUIZ: [MessageHandler(Filters.text & ~Filters.command, take_quiz)],
            MATERIAL_UNSUBSCRIPTION: [MessageHandler(Filters.text & ~Filters.command, material_unsubscription_confirmation)],
            PROCESS_SELECT_STUDY_QUIZ: [MessageHandler(Filters.text & ~Filters.command, process_study_quiz_select)]
        },
        fallbacks=[CommandHandler('cancelar', cancelar)],
    )

    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Start running scheduler in background 
    scheduler.run(sender.send)
    
    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

    # kill devotional scheduler
    scheduler.stop()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        sender.report_exception(e)