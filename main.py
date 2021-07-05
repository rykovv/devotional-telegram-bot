from configparser import ConfigParser
import re

import logging
from typing import Dict

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

# Setup the config
CONFIG_FILE_NAME = 'config.ini'

config = ConfigParser()
config.read(CONFIG_FILE_NAME)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

START_CONVERSATION, TIME_ZONE, PREFERRED_TIME, DEVOTIONAL, CONFIRMATION, CHANGE, CHANGE_TIME_ZONE, CHANGE_PREFERRED_TIME, CHANGE_DEVOTIONAL = range(9)

buffer_dict = {}

tf = TimezoneFinder()


def start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation and asks the user about their time_zone."""
    reply_keyboard = [['Sí'],['No']]
    user = update.message.from_user    
    buffer_dict[user.id] = { "first_name" : user.first_name }

    update.message.reply_text(
        f'¡Hola, {user.first_name}! Soy el bot del ministerio de Una Mirada de Fe y Esperanza. '
        'Mi functión es enviar devocionales de su elección a su hora preferida. '
        'Vamos a tener una pequeña conversación para apuntar el devocional de su elección y su hora preferida.\n\n'
        '¿Quere recibir las matutinas?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=False, input_field_placeholder='¿Sí?'
        ),
    )

    return START_CONVERSATION

def start_conversation(update: Update, context: CallbackContext) -> int:
    wrong_reply_keyboard = [['Sí'],['No']]
    user = update.message.from_user

    pattern = '^(Sí|No)$'
    if not re.match(pattern, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.'
            '¿Quere recibir las matutinas? (Sí/No)',
            reply_markup=ReplyKeyboardMarkup(
                wrong_reply_keyboard, one_time_keyboard=False, input_field_placeholder='¿Sí?'
            ),
        )
        return START_CONVERSATION

    if update.message.text == 'Sí':
        update.message.reply_text(
            #'¿De dónde es Usted? Lo necesitamos para saber su hora.\nPor ejemplo, Estados Unidos, Chile...',
            'Para enviar las matutinas a su hora de preferencia, necesitamos saber su zona horaria. '
            'Para ello me puede enviar su ubicación. '
            'Nosotros no guardamos sus datos, solo extraemos la zona horaria.\n\n'
            'Si no quiere hacerlo marque /saltar. En tal caso su matutina le llegaría a las 10pm PST.',
            reply_markup=ReplyKeyboardRemove(),
        )
        return TIME_ZONE
    elif update.message.text == 'No':
        buffer_dict.pop(user.id, None)

        update.message.reply_text(
            'De acuerdo. ¡Esperamos verle de vuelta pronto!', reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END

def geo_skip(update: Update, context: CallbackContext) -> int:
    """Skips the location and asks for info about the user."""
    reply_keyboard = [['¡Maranata: El Señor Viene!']]

    user = update.message.from_user
    buffer_dict[user.id]['time_zone'] = 'skipped'
    buffer_dict[user.id]['utc_offset'] = '-07:00'
    buffer_dict[user.id]['preferred_time'] = '10pm'

    #logger.info("User %s did not send a location.", user.first_name)
    
    update.message.reply_text(
        f'¡{user.first_name}, no hay problema. Usted recibirá la matutina a las 10pm PST cada día. '
        'Nos queda un paso para terminar!\n\n'
        '¿Qué devocional querría recibir? Estamos trabajando para añadir más devocionales.',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=False, input_field_placeholder='¿Maranata?'
        ),
    )

    return DEVOTIONAL

def time_zone(update: Update, context: CallbackContext) -> int:
    reply_keyboard = [  ['12am', '1am', '2am', '3am'], ['4am', '5am', '6am', '7am'], ['8am', '9am', '10am', '11am'],
                        ['12pm', '1pm', '2pm', '3pm'], ['4pm', '5pm', '6pm', '7pm'], ['8pm', '9pm', '10pm', '11pm']]
    geo_skipped_keyboard = [['¡Maranata: El Señor Viene!']]

    user = update.message.from_user
    user_location = update.message.location
    if user_location == None:
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido. '
            'Envíenos su ubicación o salte este paso marcando /saltar.',
            reply_markup=ReplyKeyboardRemove()
        )
        return TIME_ZONE

    buffer_dict[user.id]['time_zone'] = tf.timezone_at(lat=user_location.latitude, lng=user_location.longitude)
    print(f'User time zone is {buffer_dict[user.id]["time_zone"]}')
    
    now_utc = pytz.utc.localize(datetime.datetime.utcnow())
    now_user = now_utc.astimezone(pytz.timezone(buffer_dict[user.id]['time_zone']))
    
    buffer_dict[user.id]['utc_offset'] = now_user.isoformat()[-6:]

    print(f'UTC offset of {user.first_name}: {buffer_dict[user.id]["utc_offset"]}')
    # logger.info("Country of %s: %s", user.first_name, update.message.text)

    if buffer_dict[user.id]['time_zone'] != 'skipped':
        update.message.reply_text(
            f'¡Estupendo! Ya sabemos que su zona horaria es {buffer_dict[user.id]["time_zone"]}.\n\n'
            '¿A qué hora querría recibir el devocional?',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, input_field_placeholder='¿Cuál es su hora preferida?'
            ),
        )
    else:
        update.message.reply_text(
            '¡Estupendo! Usted recibirá las matutinas a las 10pm PST.\n\n'
            '¿Qué devocional querría recibir?',
            reply_markup=ReplyKeyboardMarkup(
                geo_skipped_keyboard, one_time_keyboard=True, input_field_placeholder='¿Maranata?'
            ),
        )
        return DEVOTIONAL

    return PREFERRED_TIME

def preferred_time(update: Update, context: CallbackContext) -> int:
    reply_keyboard = [['¡Maranata: El Señor Viene!']]
    wrong_reply_keyboard = [['12am', '1am', '2am', '3am'], ['4am', '5am', '6am', '7am'], ['8am', '9am', '10am', '11am'],
                            ['12pm', '1pm', '2pm', '3pm'], ['4pm', '5pm', '6pm', '7pm'], ['8pm', '9pm', '10pm', '11pm']]

    user = update.message.from_user

    pattern = '^\d(\d)?(a|p)+m$'
    if not re.match(pattern, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.'
            '¿A qué hora querría recibir el devocional?',
            reply_markup=ReplyKeyboardMarkup(
                wrong_reply_keyboard, one_time_keyboard=False, input_field_placeholder='¿Cuál es su hora preferida?'
            ),
        )
        return PREFERRED_TIME

    buffer_dict[user.id]['preferred_time'] = update.message.text
    
    print("Preferred time of {}: {}".format(user.first_name, update.message.text))
    # logger.info("Country of %s: %s", user.first_name, update.message.text)

    update.message.reply_text(
        f'¡{user.first_name}, nos queda un paso para terminar! '
        f'Ya sabemos que su zona horaria es {buffer_dict[user.id]["time_zone"]} y '
        f'quiere recibir el devocional a la(s) {buffer_dict[user.id]["preferred_time"]}.\n\n'
        '¿Qué devocional querría recibir? Estamos trabajando para añadir más devocionales.',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=False, input_field_placeholder='¿Maranata?'
        ),
    )

    return DEVOTIONAL

def devotional(update: Update, context: CallbackContext) -> int:
    reply_keyboard = [['Sí'],['No']]
    wrong_reply_keyboard = [['¡Maranata: El Señor Viene!']]
    user = update.message.from_user

    pattern = '^(¡Maranata: El Señor Viene!)$'
    if not re.match(pattern, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.'
            '¿Qué devocional querría recibir?',
            reply_markup=ReplyKeyboardMarkup(
                wrong_reply_keyboard, one_time_keyboard=False, input_field_placeholder='¿Maranata?'
            ),
        )
        return DEVOTIONAL

    buffer_dict[user.id]['devotional'] = update.message.text

    if buffer_dict[user.id]['time_zone'] != 'skipped':
        update.message.reply_text(
            '¡Ya estamos listos! Ya sabemos que ' 
            f'su zona horaria es {buffer_dict[user.id]["time_zone"]} y '
            f'quiere recibir el devocional {buffer_dict[user.id]["devotional"]} '
            f'cada día a la(s) {buffer_dict[user.id]["preferred_time"]}.\n\n'
            '¿Es correcto?',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, input_field_placeholder='¿Sí?'
            ),
        )
    else:
        update.message.reply_text(
            '¡Ya estamos listos! Ya sabemos que ' 
            f'Usted recibirá el devocional {buffer_dict[user.id]["devotional"]} a las 10pm PST.\n\n'
            '¿Es correcto?',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, input_field_placeholder='¿Sí?'
            ),
        )

    return CONFIRMATION

def confirmation(update: Update, context: CallbackContext) -> int:
    no_reply_keyboard = [['País'], ['Hora'], ['Devocional'], ['Nada']]
    wrong_reply_keyboard = [['Sí'],['No']]
    user = update.message.from_user

    pattern = '^(Sí|No)$'
    if not re.match(pattern, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.'
            '¿Está de acuerdo?',
            reply_markup=ReplyKeyboardMarkup(
                wrong_reply_keyboard, one_time_keyboard=False, input_field_placeholder='¿Sí?'
            ),
        )
        return CONFIRMATION

    if update.message.text == 'Sí':
        update.message.reply_text(
            '¡Ya está todo configurado! Puede siempre marcar lo siguiente:\n'
            '/ajustar para ajustar su suscripción,\n'
            '/estado para ver el estado de su suscripción,\n'
            '/ayuda para obtener ayuda.\n\n'
            '¡Muchas gracias y esperamos que sea para su gran bendición!'
        )
    elif update.message.text == 'No':
        update.message.reply_text(
            'Por favor, indíqueme lo que tengo que cambiar.',
            reply_markup=ReplyKeyboardMarkup(
                no_reply_keyboard, one_time_keyboard=False, input_field_placeholder='¿Qué cambio?'
            ),
        )
        return CHANGE

    return ConversationHandler.END

def change(update: Update, context: CallbackContext) -> int:
    wrong_reply_keyboard = [['País'], ['Hora'], ['Devocional'], ['Nada']]
    time_reply_keyboard = [ ['12am', '1am', '2am', '3am'], ['4am', '5am', '6am', '7am'], ['8am', '9am', '10am', '11am'],
                            ['12pm', '1pm', '2pm', '3pm'], ['4pm', '5pm', '6pm', '7pm'], ['8pm', '9pm', '10pm', '11pm']]
    devotional_reply_keyboard = [['¡Maranata: El Señor Viene!']]
    confirmation_reply_keyboard = [['Sí'],['No']]
    user = update.message.from_user

    pattern = '^(País|Hora|Devocional|Nada|Listo)$'
    if not re.match(pattern, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.'
            'Por favor, indíqueme lo que tengo que cambiar.',
            reply_markup=ReplyKeyboardMarkup(
                wrong_reply_keyboard, one_time_keyboard=False, input_field_placeholder='¿Qué cambio?'
            ),
        )
        return CHANGE

    if update.message.text == 'País':
        if buffer_dict[user.id]['time_zone'] != 'skipped':
            update.message.reply_text(
                f'{user.first_name}, hasta encontes sabía que su zona horaria era {buffer_dict[user.id]["time_zone"]}.\n\n'
                'Mándenos de nuevo su ubicación o marque /eliminar para eliminar la información actual.',
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            update.message.reply_text(
                f'{user.first_name}, hasta encontes sabía que Usted iba a recibir las matutinas a las 10pm PST.\n\n'
                'Mándenos de nuevo su ubicación si quiere recibir el devocional a su hora de preferencia.',
                reply_markup=ReplyKeyboardRemove(),
            )
        return CHANGE_TIME_ZONE
    elif update.message.text == 'Hora':
        if buffer_dict[user.id]['time_zone'] != 'skipped':
            update.message.reply_text(
                f'{user.first_name}, hasta encontes sabía que Usted quería recibir el devocional a la(s) {buffer_dict[user.id]["preferred_time"]}.\n\n'
                '¿A qué hora quiere cambiar?',
                reply_markup=ReplyKeyboardMarkup(
                    time_reply_keyboard, one_time_keyboard=False, input_field_placeholder='¿A qué hora?'
                ),
            )
        else:
            update.message.reply_text(
                f'{user.first_name}, para cambiar la hora Usted me tiene que enviar su ubicación pinchando \'País\'. '
                'De otro modo no puedo saber cuál es su zona horaria para enviarle el devocional a su hora.\n\n',
                reply_markup=ReplyKeyboardMarkup(
                    wrong_reply_keyboard, one_time_keyboard=False, input_field_placeholder='¿Qué cambio?'
                ),
            )
            return CHANGE
        return CHANGE_PREFERRED_TIME
    elif update.message.text == 'Devocional':
        update.message.reply_text(
            f'{user.first_name}, hasta encontes sabía que Usted quería recibir el devocional {buffer_dict[user.id]["devotional"]}\n\n'
            '¿A qué devocional quiere cambiar?',
            reply_markup=ReplyKeyboardMarkup(
                devotional_reply_keyboard, one_time_keyboard=False, input_field_placeholder='¿Maranata?'
            ),
        )
        return CHANGE_DEVOTIONAL
    elif update.message.text == 'Nada' or update.message.text == 'Listo':
        if buffer_dict[user.id]['time_zone'] != 'skipped':
            update.message.reply_text(
                '¡Muy bien, recapitulemos!\n' 
                f'Su zona horaria es {buffer_dict[user.id]["time_zone"]} y '
                f'quiere recibir el devocional {buffer_dict[user.id]["devotional"]} '
                f'cada día a la(s) {buffer_dict[user.id]["preferred_time"]}.\n\n'
                '¿Es correcto?',
                reply_markup=ReplyKeyboardMarkup(
                    confirmation_reply_keyboard, one_time_keyboard=True, input_field_placeholder='¿Sí?'
                ),
            )
        else:
            update.message.reply_text(
                '¡Muy bien, recapitulemos!\n' 
                f'Usted va a recibir el devocional {buffer_dict[user.id]["devotional"]} a las 10pm PST.\n\n'
                '¿Es correcto?',
                reply_markup=ReplyKeyboardMarkup(
                    confirmation_reply_keyboard, one_time_keyboard=True, input_field_placeholder='¿Sí?'
                ),
            )
        return CONFIRMATION
    # unreachable return
    return ConversationHandler.END

def change_time_zone(update: Update, context: CallbackContext) -> int:
    reply_keyboard = [['País'], ['Hora'], ['Devocional'], ['Listo']]
    user = update.message.from_user
    user_location = update.message.location

    if user_location == None:
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.'
            'Envíenos su ubicación o elimine su información actual marcando /eliminar.',
            reply_markup=ReplyKeyboardRemove()
        )
        return TIME_ZONE

    buffer_dict[user.id]['time_zone'] = tf.timezone_at(lat=user_location.latitude, lng=user_location.longitude)
    print(f'User time zone is {buffer_dict[user.id]["time_zone"]}')
    
    now_utc = pytz.utc.localize(datetime.datetime.utcnow())
    now_user = now_utc.astimezone(pytz.timezone(buffer_dict[user.id]['time_zone']))
    
    buffer_dict[user.id]['utc_offset'] = now_user.isoformat()[-6:]

    # logger.info("Country of %s: %s", user.first_name, update.message.text)

    update.message.reply_text(
        f'¡Estupendo! A partir de ahora sabemos que su zona horaria es {buffer_dict[user.id]["time_zone"]}, '
        f'quiere recibir el devocional {buffer_dict[user.id]["devotional"]} '
        f'cada día a la(s) {buffer_dict[user.id]["preferred_time"]}.\n\n'
        '¿Quiere cambiar algo más?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='¿Qué cambio?'
        ),
    )

    return CHANGE

def geo_remove(update: Update, context: CallbackContext) -> int:
    reply_keyboard = [['País'], ['Hora'], ['Devocional'], ['Listo']]
    user = update.message.from_user

    buffer_dict[user.id]['time_zone'] = 'skipped'
    buffer_dict[user.id]['utc_offset'] = '-07:00'
    buffer_dict[user.id]['preferred_time'] = '10pm'

    update.message.reply_text(
        f'¡Hecho! He eliminado su zona horaria. A partir de ahora recibirá el devocional a las 10pm PST.\n\n'
        '¿Qué más querría cambiar?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='¿Qué cambio?'
        ),
    )

    return CHANGE


def change_preferred_time(update: Update, context: CallbackContext) -> int:
    reply_keyboard = [['País'], ['Hora'], ['Devocional'], ['Listo']]
    wrong_reply_keyboard = [['12am', '1am', '2am', '3am'], ['4am', '5am', '6am', '7am'], ['8am', '9am', '10am', '11am'],
                            ['12pm', '1pm', '2pm', '3pm'], ['4pm', '5pm', '6pm', '7pm'], ['8pm', '9pm', '10pm', '11pm']]
    user = update.message.from_user

    pattern = '^\d(\d)?(a|p)+m$'
    if not re.match(pattern, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido. '
            'Por favor, elija la hora de selección.',
            reply_markup=ReplyKeyboardMarkup(
                wrong_reply_keyboard, one_time_keyboard=False, input_field_placeholder='¿Qué hora apunto?'
            ),
        )
        return CHANGE_PREFERRED_TIME

    buffer_dict[user.id]['preferred_time'] = update.message.text

    update.message.reply_text(
        f'¡Bien! Con ese cambio sabemos que su zona horaria es {buffer_dict[user.id]["time_zone"]}, '
        f'quiere recibir el devocional {buffer_dict[user.id]["devotional"]} '
        f'cada día a la(s) {buffer_dict[user.id]["preferred_time"]}.\n\n'
        '¿Desear realizar algún cambio más?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='¿Qué cambio?'
        ),
    )

    return CHANGE

def change_devotional(update: Update, context: CallbackContext) -> int:
    reply_keyboard = [['País'], ['Hora'], ['Devocional'], ['Listo']]
    wrong_reply_keyboard = [['¡Maranata: El Señor Viene!']]
    user = update.message.from_user

    pattern = '^(¡Maranata: El Señor Viene!)$'
    if not re.match(pattern, update.message.text):
        update.message.reply_text(
            f'Disculpe {user.first_name}, no le he entendido.'
            'Por favor, seleccione algún devocional disponible.',
            reply_markup=ReplyKeyboardMarkup(
                wrong_reply_keyboard, one_time_keyboard=False, input_field_placeholder='¿Qué devocional apunto ahora?'
            ),
        )
        return CHANGE_DEVOTIONAL

    buffer_dict[user.id]['devotional'] = update.message.text

    if buffer_dict[user.id]['time_zone'] != 'skipped':
        update.message.reply_text(
            f'¡Bien! Actualmente sabemos que su zona horaria es {buffer_dict[user.id]["time_zone"]}, '
            f'quiere recibir el devocional {buffer_dict[user.id]["devotional"]} '
            f'cada día a la(s) {buffer_dict[user.id]["preferred_time"]}.\n\n'
            '¿Desea cambiar algo más?',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, input_field_placeholder='¿Qué cambio?'
            ),
        )
    else:
        update.message.reply_text(
            f'¡Bien! Actualmente sabemos que va a recibir el devocional {buffer_dict[user.id]["devotional"]} '
            'cada día a las 10pm PST.\n\n'
            '¿Desea cambiar algo más?',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, input_field_placeholder='¿Qué cambio?'
            ),
        )

    return CHANGE

def make_adjustments(update: Update, context: CallbackContext) -> int:
    reply_keyboard = [['País'], ['Hora'], ['Devocional'], ['Nada']]
    user = update.message.from_user

    update.message.reply_text(
        '¿Qué le gustaría cambiar en esta ocasión?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='¿Qué cambio?'
        ),
    )

    return CHANGE

def get_status(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    if buffer_dict[user.id]['time_zone'] != 'skipped':
        update.message.reply_text(
            'Aquí tiene el estado de su suscripción. \n' 
            f'Su zona horaria es {buffer_dict[user.id]["time_zone"]} y '
            f'quiere recibir el devocional {buffer_dict[user.id]["devotional"]} '
            f'cada día a la(s) {buffer_dict[user.id]["preferred_time"]}.\n\n'
            'Para hacer algún cambio marque /ajustar.'
        )
    else:
        update.message.reply_text(
            'Aquí tiene el estado de su suscripción. \n' 
            f'Usted recibe el devocional {buffer_dict[user.id]["devotional"]} cada día a las 10pm PST.\n\n'
            'Para hacer algún cambio marque /ajustar.'
        )

    return ConversationHandler.END

def get_help(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user

    if buffer_dict[user.id]['time_zone'] != 'skipped':
        update.message.reply_text(
            'Aquí tiene el estado de su suscripción. \n' 
            f'Su zona horaria es {buffer_dict[user.id]["time_zone"]} y '
            f'quiere recibir el devocional {buffer_dict[user.id]["devotional"]} '
            f'cada día a la(s) {buffer_dict[user.id]["preferred_time"]}.\n\n'
            'Puede marcar lo siguiente:\n'
            '/ajustar para ajustar su suscripción,\n'
            '/estado para ver el estado de su suscripción.\n\n'
        )
    else:
        update.message.reply_text(
            'Aquí tiene el estado de su suscripción. \n' 
            f'Usted recibe el devocional {buffer_dict[user.id]["devotional"]} cada día a las 10pm PST.\n\n'
            'Puede marcar lo siguiente:\n'
            '/ajustar para ajustar su suscripción,\n'
            '/estado para ver el estado de su suscripción.\n\n'
        )

    return ConversationHandler.END


def cancelar(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)

    buffer_dict.pop(user.id, None)

    update.message.reply_text(
        '¡Adiós! Esperamos verte de vuelta pronto...', reply_markup=ReplyKeyboardRemove()
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
            CommandHandler('ajustar', make_adjustments), 
            CommandHandler('estado', get_status),
            CommandHandler('ayuda', get_help)],
        states={
            START_CONVERSATION: [MessageHandler(Filters.text & ~Filters.command, start_conversation)],
            TIME_ZONE: [
                MessageHandler((Filters.text & ~Filters.command) | Filters.location, time_zone), 
                CommandHandler('saltar', geo_skip)
            ],
            PREFERRED_TIME: [MessageHandler(Filters.text & ~Filters.command, preferred_time)], #Filters.regex('\d\d*{am,pm}+')
            DEVOTIONAL: [MessageHandler(Filters.text & ~Filters.command, devotional)], #Filters.regex('^(¡Maranata: El Señor Viene!)$')
            CONFIRMATION: [MessageHandler(Filters.text & ~Filters.command, confirmation)],
            CHANGE: [MessageHandler(Filters.text & ~Filters.command, change)],
            CHANGE_TIME_ZONE: [
                MessageHandler((Filters.text & ~Filters.command) | Filters.location, change_time_zone), 
                CommandHandler('eliminar', geo_remove)
            ],
            CHANGE_PREFERRED_TIME: [MessageHandler(Filters.text & ~Filters.command, change_preferred_time)],
            CHANGE_DEVOTIONAL: [MessageHandler(Filters.text & ~Filters.command, change_devotional)],
        },
        fallbacks=[CommandHandler('cancelar', cancelar)],
    )

    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

def test() -> None:
    pattern = '^\d(\d)?(a|p)+m$'
    test_string = '5pm'
    result = re.match(pattern, test_string)

    if result:
        print("Search successful.")
    else:
        print("Search unsuccessful.")

if __name__ == '__main__':
    main()
    #test()