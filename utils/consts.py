# Global constants

## config file name
CONFIG_FILE_NAME = 'config.ini'

## Statistics table entry unique ID
STATISTICS_UNIQUE_ID = 1

## time format 24-hour to 12-hour mapper
TF_24TO12 = ['12pm', '1am', '2am', '3am', '4am', '5am', '6am', '7am', '8am', '9am', '10am', '11am',
             '12am', '1pm', '2pm', '3pm', '4pm', '5pm', '6pm', '7pm', '8pm', '9pm', '10pm', '11pm']

## Keyboards
### Yes/No keyboard and re pattern
YES_NO_KEYBOARD = [['Sí'],['No']]
YES_NO_RE_PATTERN = '^(Sí|No)$'
### Available devotionals keyboard
DEVOTIONALS_KEYBOARD = [['¡Maranata: El Señor Viene!']]
DEVOTIONALS_RE_PATTERN = '^(¡Maranata: El Señor Viene!)$'
### Pick up hours for sending devotional
HOUR_KEYBOARD = [['12pm', '1am', '2am', '3am'], ['4am', '5am', '6am', '7am'], ['8am', '9am', '10am', '11am'],
                 ['12am', '1pm', '2pm', '3pm'], ['4pm', '5pm', '6pm', '7pm'], ['8pm', '9pm', '10pm', '11pm']]
### Hours format re pattern
HOUR_RE_PATTERN = '^\d(\d)?(a|p)+m$'
### Preference pickup and change keyboards
PREFERENCE_CHANGE_KEYBOARD = [['País'], ['Hora'], ['Devocional'], ['Nada']]
CONT_PREFERENCE_CHANGE_KEYBOARD = [['País'], ['Hora'], ['Devocional'], ['Listo']]
### Preference pickup and change pattern
PREFERENCE_CHANGE_RE_PATTERN = '^(País|Hora|Devocional|Nada|Listo)$'

## Max message send retries
MAX_SEND_RETRIES = 20