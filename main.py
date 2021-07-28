from configparser import ConfigParser
import re
from sqlalchemy.sql.sqltypes import TIME

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
    prepare_subscription_select,
)

from db.subscriber import Subscriber
from db.subscription import Subscription
from db.statistics import Statistics

import db.populate

import actors.scheduler as scheduler
import actors.sender as sender
import actors.actuary as actuary


# Setup the config
config = ConfigParser()
config.read(consts.CONFIG_FILE_NAME)

logger = get_logger()

START_FIRST_SUBSCRIPTION, ADD_NEW_SUBSCRIPTION, TIME_ZONE, PREFERRED_TIME, \
NEW_SUBSCRIPTION_KEEP_PREFERENCES, MAKE_ADJUSTMENTS, \
DEVOTIONAL, CONFIRMATION, CHANGE, CHANGE_TIME_ZONE, \
CHANGE_PREFERRED_TIME, CHANGE_DEVOTIONAL, UNSUBSCRIPTION_CONFIRMATION = range(13)

tf = TimezoneFinder()

def start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation and asks the user about their time_zone."""
    user = update.message.from_user

    subscriber = fetch_subscriber(user.id)

    if subscriber == None:
        buffer.add_subscriber(Subscriber(id=user.id, creation_utc=get_epoch()))

        update.message.reply_text(
            f'¡Hola, {user.first_name}! Soy el bot del ministerio Una Mirada de Fe y Esperanza. '
            'Mi función es enviar devocionales o lecturas de su elección a su hora preferida. '
            'Vamos a tener una pequeña conversación para apuntar el devocional de su elección y su hora preferida.\n\n'
            '¿Quere recibir las matutinas/lecturas?',
            reply_markup=ReplyKeyboardMarkup(
                consts.YES_NO_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Sí?'
            ),
        )
        return START_FIRST_SUBSCRIPTION
    else:
        buffer.add_subscriber(subscriber)
        if subscriber.subscriptions != []:
            update.message.reply_text(
                f'¡Me alegra verle de vuelta, {user.first_name}!\n\n'
                '¿Quere hacer una nueva suscripción?',
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
            '¿Quere recibir las matutinas? (Sí/No)',
            reply_markup=ReplyKeyboardMarkup(
                consts.YES_NO_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Sí?'
            ),
        )
        return START_FIRST_SUBSCRIPTION

    if update.message.text == 'Sí':
        update.message.reply_text(
            'Para enviar las matutinas a su hora de preferencia, necesitamos saber su zona horaria. '
            'Para ello me puede enviar su ubicación. '
            'Nosotros no guardamos sus datos, solo extraemos la zona horaria.\n\n'
            'Si no quiere hacerlo marque /saltar. En tal caso su matutina le llegaría a las '
            '10pm Pacific Standard Time (PST) del día anterior.',
            reply_markup=ReplyKeyboardRemove(),
        )
        return TIME_ZONE
    elif update.message.text == 'No':
        buffer.clean(user.id)

        update.message.reply_text(
            'De acuerdo. ¡Esperamos verle de vuelta pronto!', reply_markup=ReplyKeyboardRemove()
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
        update.message.reply_text(
            f'¡Estupendo, {user.first_name}! ¿Quiere mantener las preferencias de envío de su última suscripción? '
            'La puede ver abajo: \n\n'
            f'{print_subscription(buffer.subscribers[user.id].subscriptions[-1])}',
            reply_markup=ReplyKeyboardMarkup(
                consts.YES_NO_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Sí?'
            ),
        )
        return NEW_SUBSCRIPTION_KEEP_PREFERENCES
    elif update.message.text == 'No':
        buffer.clean(user.id)

        update.message.reply_text(
            'De acuerdo. ¡Esperamos verle de vuelta pronto!', reply_markup=ReplyKeyboardRemove()
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
                f'De acuerdo. Ya sabemos que su zona horaria es {buffer.subscribers[user.id].time_zone} y '
                f'quiere recibir el devocional a la(s) {buffer.subscriptions[user.id].preferred_time_local}.\n\n'
                '¿Qué devocional/lectura querría recibir? Estamos trabajando para añadir más libros.',
                reply_markup=ReplyKeyboardMarkup(
                    consts.DEVOTIONALS_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Maranata?'
                ),
            )
        else:
            update.message.reply_text(
                f'De acuerdo. Ya sabemos que usted no ha indicado su zona horaria anteriormente y '
                f'por lo tanto va a recibir el devocional a la(s) {buffer.subscriptions[user.id].preferred_time_local} del PST.\n\n'
                '¿Qué devocional/lectura querría recibir? Estamos trabajando para añadir más libros.',
                reply_markup=ReplyKeyboardMarkup(
                    consts.DEVOTIONALS_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Maranata?'
                ),
            )
        return DEVOTIONAL
    elif update.message.text == 'No':
        if buffer.subscribers[user.id].skipped_timezone():
            update.message.reply_text(
                f'{user.first_name}, para poder enviarle el devocional a su hora preferida necesitamos extraer su zona horaria '
                'y la forma más conveniente es hacerlo a través de su ubicación. '
                'Usted no nos ha enviado su ubicación anteriormente. Para poder extraer su zona horaria mándenos su '
                'ubicación o marque /saltar para seguir con la última configuración.', 
                reply_markup=ReplyKeyboardRemove()
            )
            return TIME_ZONE
        else:
            buffer.add_subscription(Subscription(subscriber_id=last_subscription.subscriber_id, \
                                             preferred_time_local=last_subscription.preferred_time_local, \
                                             utc_offset=last_subscription.utc_offset, \
                                             creation_utc=get_epoch()))
            update.message.reply_text(
                'No hay problema, hemos pensado de que podría querer elegir una hora diferente.\n\n'
                '¿A qué hora querría recibir el devocional? (am - mañana, pm - tarde)', 
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
        f'¡{user.first_name}, no hay problema. Usted recibirá la matutina/lectura a las 10pm PST del día anterior. '
        '¡Nos queda un paso para terminar!\n\n'
        '¿Qué devocional querría recibir? Estamos trabajando para añadir más devocionales.',
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
            'Envíenos su ubicación o salte este paso marcando /saltar.',
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
            f'¡Estupendo! Ya sabemos que su zona horaria es {buffer.subscribers[user.id].time_zone}.\n\n'
            '¿A qué hora querría recibir el devocional/la lectura? (am - mañana, pm - tarde)',
            reply_markup=ReplyKeyboardMarkup(
                consts.HOUR_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Cuál es su hora preferida?'
            ),
        )
    else:
        update.message.reply_text(
            '¡Estupendo! Usted recibirá las matutinas a las 10pm Pacific Standard Time (PST) del día anterior.\n\n'
            '¿Qué devocional querría recibir?',
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
            '¿A qué hora querría recibir el devocional? (am - mañana, pm - tarde)',
            reply_markup=ReplyKeyboardMarkup(
                consts.HOUR_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Cuál es su hora preferida?'
            ),
        )
        return PREFERRED_TIME

    buffer.subscriptions[user.id].update_preferred_time_local(update.message.text)

    update.message.reply_text(
        f'¡{user.first_name}, nos queda un paso para terminar! '
        f'Ya sabemos que su zona horaria es {buffer.subscribers[user.id].time_zone} y '
        f'quiere recibir el devocional a la(s) {buffer.subscriptions[user.id].preferred_time_local}.\n\n'
        '¿Qué devocional/lectura querría recibir? Estamos trabajando para añadir más material.',
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

    # if buffer.subscribers[user.id].subscribed(update.message.text):
    #     update.message.reply_text(
    #         f'{user.first_name}, Usted ya está suscrito/a a esta lectura. '
    #         'Marque /estado para ver el estado de sus suscripciones,\n'
    #         '/ajustar para cambiar las preferencias de sus suscripciones,\n'
    #         '/start para hacer una nueva suscripción.',
    #         reply_markup=ReplyKeyboardRemove()
    #     )
    #     return ConversationHandler.END

    buffer.subscriptions[user.id].devotional_name = update.message.text

    if not buffer.subscribers[user.id].skipped_timezone():
        update.message.reply_text(
            '¡Ya estamos listos! Ya sabemos que ' 
            f'su zona horaria es {buffer.subscribers[user.id].time_zone} y '
            f'quiere recibir el devocional {buffer.subscriptions[user.id].devotional_name} '
            f'cada día a la(s) {buffer.subscriptions[user.id].preferred_time_local}.\n\n'
            '¿Es correcto?',
            reply_markup=ReplyKeyboardMarkup(
                consts.YES_NO_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Sí?'
            ),
        )
    else:
        update.message.reply_text(
            '¡Ya estamos listos! Ya sabemos que ' 
            f'Usted quiere recibir el devocional {buffer.subscriptions[user.id].devotional_name} a las 10pm PST (Pacific Standard Time) del día anterior.\n\n'
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
        update.message.reply_text(
            '¡Ya está todo configurado! Puede siempre marcar lo siguiente:\n'
            '/start para hacer una nueva y diferente suscripcón,\n'
            '/ajustar para ajustar su suscripción,\n'
            '/estado para ver el estado de su suscripción,\n'
            '/ayuda para obtener lista de comandos,\n'
            '/contacto para contactar con nosotros,\n'
            '/recuento para ver las estadísticas,\n'
            '/baja para dejar de recibir los devocionales.\n\n'
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
                'Mándenos de nuevo su ubicación o marque /eliminar para eliminar la información actual.',
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            update.message.reply_text(
                f'{user.first_name}, hasta encontes sabía que Usted ha preferido no compartir su ubicación. '
                'Por lo tanto, Usted iba a recibir las matutinas a las 10pm PST.\n\n'
                'Mándenos de nuevo su ubicación si quiere recibir el devocional a su hora de preferencia.',
                reply_markup=ReplyKeyboardRemove(),
            )
        return CHANGE_TIME_ZONE
    elif update.message.text == 'Hora':
        if not buffer.subscribers[user.id].skipped_timezone():
            subscriptions = buffer.subscriptions[user.id]
            update.message.reply_text(
                f'{user.first_name}, hasta encontes sabía que Usted quería recibir el devocional a la(s) {subscriptions.preferred_time_local}.\n\n'
                '¿A qué hora quiere cambiar?',
                reply_markup=ReplyKeyboardMarkup(
                    consts.HOUR_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿A qué hora?'
                ),
            )
        else:
            update.message.reply_text(
                f'{user.first_name}, para cambiar la hora Usted me tiene que enviar su ubicación pinchando \'País\'. '
                'De otro modo no puedo saber cuál es su zona horaria para enviarle el devocional a su hora.\n\n',
                reply_markup=ReplyKeyboardMarkup(
                    consts.PREFERENCE_CHANGE_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Qué cambio?'
                ),
            )
            return CHANGE
        return CHANGE_PREFERRED_TIME
    elif update.message.text == 'Devocional':
        subscriptions = buffer.subscriptions[user.id]
        update.message.reply_text(
            f'{user.first_name}, hasta encontes sabía que Usted quería recibir el devocional {subscriptions.devotional_name}\n\n'
            '¿A qué devocional quiere cambiar?',
            reply_markup=ReplyKeyboardMarkup(
                consts.DEVOTIONALS_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Maranata?'
            ),
        )
        return CHANGE_DEVOTIONAL
    elif update.message.text == 'Nada' or update.message.text == 'Listo':
        subscriptions = buffer.subscriptions[user.id]
        if not buffer.subscribers[user.id].skipped_timezone():
            update.message.reply_text(
                '¡Muy bien, recapitulemos!\n' 
                f'Su zona horaria es {buffer.subscribers[user.id].time_zone} y '
                f'quiere recibir el devocional {subscriptions.devotional_name} '
                f'cada día a la(s) {subscriptions.preferred_time_local}.\n\n'
                '¿Es correcto?',
                reply_markup=ReplyKeyboardMarkup(
                    consts.YES_NO_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Sí?'
                ),
            )
        else:
            update.message.reply_text(
                '¡Muy bien, recapitulemos!\n' 
                f'Usted va a recibir el devocional {subscriptions.devotional_name} a las 10pm PST del día anterior.\n\n'
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
            'Envíenos su ubicación o elimine su información actual marcando /eliminar.',
            reply_markup=ReplyKeyboardRemove()
        )
        return TIME_ZONE

    buffer.subscribers[user.id].time_zone = tf.timezone_at(lat=user_location.latitude, lng=user_location.longitude)
    logger.info(f'User {user.first_name} time zone is {buffer.subscribers[user.id].time_zone}')
    
    now_utc = pytz.utc.localize(datetime.datetime.utcnow())
    now_user = now_utc.astimezone(pytz.timezone(buffer.subscribers[user.id].time_zone))
    
    subscriptions = buffer.subscriptions[user.id]
    subscriptions.update_utc_offset(utc_offset_to_int(now_user.isoformat()[-6:]))

    update.message.reply_text(
        f'¡Estupendo! A partir de ahora sabemos que su zona horaria es {buffer.subscribers[user.id].time_zone}, '
        f'quiere recibir el devocional {subscriptions.devotional_name} '
        f'cada día a la(s) {subscriptions.preferred_time_local}.\n\n'
        '¿Quiere cambiar algo más?',
        reply_markup=ReplyKeyboardMarkup(
            consts.CONT_PREFERENCE_CHANGE_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Qué cambio?'
        ),
    )

    return CHANGE

def geo_remove(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    buffer.subscribers[user.id].time_zone = 'skipped'

    subscriptions = buffer.subscriptions[user.id]
    subscriptions.update_preferred_time_local('10pm')
    subscriptions.update_utc_offset(-700)

    update.message.reply_text(
        f'¡Hecho! He eliminado su zona horaria. A partir de ahora recibirá el devocional a las 10pm PST del día anterior.\n\n'
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

    subscriptions = buffer.subscriptions[user.id]
    subscriptions.update_preferred_time_local(update.message.text)

    update.message.reply_text(
        f'¡Bien! Con ese cambio sabemos que su zona horaria es {buffer.subscribers[user.id].time_zone}, '
        f'quiere recibir el devocional {subscriptions.devotional_name} '
        f'cada día a la(s) {subscriptions.preferred_time_local}.\n\n'
        '¿Desear realizar algún cambio más?',
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
            'Por favor, seleccione algún devocional disponible.',
            reply_markup=ReplyKeyboardMarkup(
                consts.DEVOTIONALS_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿Qué devocional apunto ahora?'
            ),
        )
        return CHANGE_DEVOTIONAL
    
    subscriptions = buffer.subscriptions[user.id]
    subscriptions.devotional_name = update.message.text

    if not buffer.subscribers[user.id].skipped_timezone():
        update.message.reply_text(
            f'¡Bien! Actualmente sabemos que su zona horaria es {buffer.subscribers[user.id].time_zone}, '
            f'quiere recibir el devocional {subscriptions.devotional_name} '
            f'cada día a la(s) {subscriptions.preferred_time_local}.\n\n'
            '¿Desea cambiar algo más?',
            reply_markup=ReplyKeyboardMarkup(
                consts.CONT_PREFERENCE_CHANGE_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Qué cambio?'
            ),
        )
    else:
        update.message.reply_text(
            f'¡Bien! Actualmente sabemos que va a recibir el devocional {subscriptions.devotional_name} '
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

        subscriptions_str, subscriptions_kb = prepare_subscription_select(subscriber.subscriptions)

        update.message.reply_text(
            f'{user.first_name}, elija la suscripción que quiere modificar según su número:\n\n'
            f'{subscriptions_str}',
            reply_markup=ReplyKeyboardMarkup(
                subscriptions_kb, one_time_keyboard=True, input_field_placeholder='¿1? ¿2? ...'
            ),
        )
        return MAKE_ADJUSTMENTS
    else:
        update.message.reply_text(
            f'Lo sentimos, pero usted tiene que suscribirse primero para hacer ajustes.\n\n'
            'Marque /start para suscribirse.',
            reply_markup=ReplyKeyboardRemove()
        )
    return ConversationHandler.END


def make_adjustments(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    if not re.match(consts.SUBSCRIPTION_SELECT_PATTERN, update.message.text):
        subscriptions_str, subscriptions_kb = prepare_subscription_select(buffer.subscribers[user.id].subscriptions)

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

    update.message.reply_text(
        f'¡Ya lo tenemos! {user.first_name}, ¿qué le gustaría cambiar en esta ocasión?',
        reply_markup=ReplyKeyboardMarkup(
            consts.PREFERENCE_CHANGE_KEYBOARD, one_time_keyboard=True, input_field_placeholder='¿Qué cambio?'
        ),
    )
    return CHANGE


def get_status(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    subscriber = fetch_subscriber(user.id)

    if subscriber != None:
        subscriptions = subscriber.subscriptions[0]
        if not subscriber.skipped_timezone():
            update.message.reply_text(
                'Aquí tiene el estado de su suscripción.\n'
                f'Su zona horaria es {subscriber.time_zone} y '
                f'quiere recibir el devocional {subscriptions.devotional_name} '
                f'cada día a la(s) {subscriptions.preferred_time_local}.\n\n'
                'Para hacer algún cambio marque /ajustar.'
            )
        else:
            update.message.reply_text(
                'Aquí tiene el estado de su suscripción.\n' 
                f'Usted recibe el devocional {subscriptions.devotional_name} cada día a las 10pm PST.\n\n'
                'Para hacer algún cambio marque /ajustar.'
            )
    else:
        update.message.reply_text(
            f'Lo sentimos, pero usted tiene que suscribirse primero para ver su estado.\n\n'
            'Marque /start para suscribirse.',
            reply_markup=ReplyKeyboardRemove()
        )
    return ConversationHandler.END


def get_help(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        'Puede marcar lo siguiente:\n'
        '/start para hacer una suscripción,\n'
        '/estado para ver el estado de su suscripción,\n'
        '/ajustar para ajustar su suscripción,\n'
        '/baja para dejar de recibir los devocionales,\n'
        '/ayuda para recibir ayuda,\n'
        '/contacto para contactarse con nosotros,\n'
        '/recuento para ver las estadisticas.',
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def cancelar(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user

    buffer.clean(user.id)

    update.message.reply_text(
        'Si ha hecho algún cambio durante esta conversación no ha sido guardado.\n\n'
        '¡Adiós! Esperamos verte de vuelta pronto...', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

def unsubscribe(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    subscriber = fetch_subscriber(user.id)
    
    if subscriber != None:
        buffer.add_subscriber(fetch_subscriber(user.id))
        buffer.add_subscription(buffer.subscribers[user.id].subscriptions[0])

        update.message.reply_text(
            f'{user.first_name}, nos da mucha lástima que se vaya...\n\n'
            '¿Está completamente seguro?',
            reply_markup=ReplyKeyboardMarkup(
                consts.YES_NO_KEYBOARD, one_time_keyboard=False, input_field_placeholder='¿No?'
            ),
        )
        actuary.add_unsubscribed()
        return UNSUBSCRIPTION_CONFIRMATION
    else:
        update.message.reply_text(
            f'{user.first_name}, no tenemos ninguna suscripción activa de Usted.',
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
            'De acuerdo. Su suscripción ha sido eliminada.\n\n'
            'Esperamos que vuelva pronto...',
            reply_markup=ReplyKeyboardRemove()
        )
        clean_db(user.id)
        buffer.clean(user.id)
    elif update.message.text == 'No':
        update.message.reply_text(
            '¡Nos alegra saber su cambio de opinión! Si puedo ayudar con algo, marque /ayuda.'
        )

    return ConversationHandler.END

def get_statistics(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    subscriber = fetch_subscriber(user.id)
    if subscriber != None:
        by_devotional = ''
        sbd = actuary.subscriptions_by_devotional()
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
            f'Lo sentimos, {user.first_name}, solo usuarios registrados '
            'pueden ver las estadisticas.\n\n'
            'Marque /start para suscribirse.',
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END

def get_admin_statistics(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    if is_admin(user.id):
        by_devotional = ''
        sbd = actuary.subscriptions_by_devotional()
        stats = actuary.statistics()
        for s, c in sbd.items():
            by_devotional += f'  {s} : {c}\n'
        update.message.reply_text(
            f'Suscriptores : {actuary.subscribers()}\n'
            f'Suscripciones : {actuary.subscriptions()}\n'
            f'{by_devotional}'
            f'Sin ubicación : {actuary.geo_skipped()}\n'
            f'Enviado : {stats.sent}\n'
            f'Dieron de baja : {stats.unsubscribed}\n'
            f'Último registrado : {epoch_to_date(stats.last_registered)}\n'
            f'Último suscrito : {epoch_to_date(stats.last_subscribed)}',
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        update.message.reply_text(
            f'Lo sentimos, {user.first_name}, solo administradores '
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

def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(config['bot']['token'])

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
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
            CommandHandler('admin_recuento', get_admin_statistics)],
        states={
            START_FIRST_SUBSCRIPTION: [MessageHandler(Filters.text & ~Filters.command, start_first_subscription)],
            ADD_NEW_SUBSCRIPTION: [MessageHandler(Filters.text & ~Filters.command, add_new_subscription)],
            NEW_SUBSCRIPTION_KEEP_PREFERENCES: [
                MessageHandler(Filters.text & ~Filters.command, new_subscription_keep_preferences),
                CommandHandler('saltar', geo_skip)],
            TIME_ZONE: [
                MessageHandler((Filters.text & ~Filters.command) | Filters.location, time_zone), 
                CommandHandler('saltar', geo_skip)
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