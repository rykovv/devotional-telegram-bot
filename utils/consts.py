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
DEVOTIONALS_KEYBOARD = [
    ['Devocional: ¡Maranata: El Señor Viene!'],
    ['Devocional: A Fin de Conocerle'],
    ['Libro: El Conflicto de los Siglos'], 
    ['Estudio: El Conflicto de los Siglos']
]
DEVOTIONALS_RE_PATTERN = '^(Devocional: ¡Maranata: El Señor Viene!|Devocional: A Fin de Conocerle|Libro: El Conflicto de los Siglos|Estudio: El Conflicto de los Siglos)$'
### Pick up hours for sending devotional
HOUR_KEYBOARD = [['12pm', '1am', '2am', '3am'], ['4am', '5am', '6am', '7am'], ['8am', '9am', '10am', '11am'],
                 ['12am', '1pm', '2pm', '3pm'], ['4pm', '5pm', '6pm', '7pm'], ['8pm', '9pm', '10pm', '11pm']]
### Hours format re pattern
HOUR_RE_PATTERN = '^\d(\d)?(a|p)+m$'
### Preference pickup and change keyboards
PREFERENCE_CHANGE_KEYBOARD = [['País'], ['Hora'], ['Lectura'], ['Baja', 'Nada']]
CONT_PREFERENCE_CHANGE_KEYBOARD = [['País'], ['Hora'], ['Lectura'], ['Baja', 'Listo']]
### Preference pickup and change pattern
PREFERENCE_CHANGE_RE_PATTERN = '^(País|Hora|Lectura|Baja|Nada|Listo)$'

## Max message send retries
MAX_SEND_RETRIES = 3
## Max reachable delay in seconds between successive message resendings
MAX_RESEND_DELAY = 300

## Least necessary inter-message time interval in ms posed by the Telegram Bot API
##  see https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this
LEAST_BOT_SEND_MS = 33

## Number of subscriptions appeared by row when selecting a subscription for modifications
SUBSCRIPTIONS_BY_ROW = 4

## RE to recognize a two-digit pattern for selecting subscription to modify
SUBSCRIPTION_SELECT_PATTERN = '^\d(\d)?$'
STUDY_SELECT_PATTERN = '^\d(\d)?$'

## number of question options appeared per row during quiz taking
QUESTIONS_BY_ROW = 2

## [chapters, days] counts for materials
### Maranatha: The Lord is Coming!
MARANATHA_DAYS_COUNT = 365
AFC_DAYS_COUNT = 365
### Great Controversy
GREAT_CONTROVERSY_CHAPTERS_COUNT = 43
GREAT_CONTROVERSY_STUDY_DAYS_COUNT = 1
GREAT_CONTROVERSY_QUESTIONS_COUNT = 13
BIBLE_VERSES_COUNT = 31102
BIBLE_WHITE_MARGIN_COUNT = 3000

## Dictionary with material types
MATERIAL_TYPES = {
    'Devocional: ¡Maranata: El Señor Viene!': 'Devotional',
    'Devocional: A Fin de Conocerle'        : 'Devotional',
    'Libro: El Conflicto de los Siglos'     : 'Book',
    'Estudio: El Conflicto de los Siglos'   : 'Study'
}

## Dictionary with books acronyms in Spanish
BOOKS_ACRONYMS_LUT = {
    'CS' : 'El Conflicto de los Siglos'
}
BIBLE_BOOKS_ACRONYMS_LUT = {
    'gn' : 'Génesis',
    'ex' : 'Éxodo',
    'lv' : 'Levítico',
    'nm' : 'Números',
    'dt' : 'Deuteronomio',
    'js' : 'Josué',
    'jud': 'Jueces',
    'rt' : 'Rut',
    '1sm': '1 de Samuel',
    '2sm': '2 de Samuel',
    '1kgs':'1 de Reyes',
    '2kgs':'2 de Reyes',
    '1ch': '1 de Crónicas',
    '2ch': '2 de Crónicas',
    'ezr': 'Esdras',
    'ne' : 'Nehemías',
    'et' : 'Ester',
    'job': 'Job',
    'ps' : 'Salmos',
    'prv': 'Proverbios',
    'ec' : 'Eclesiastés',
    'so' : 'El Cantar de los Cantares',
    'is' : 'Isaías',
    'jr' : 'Jeremías',
    'lm' : 'Lamentaciones',
    'ez' : 'Ezequiel',
    'dn' : 'Daniel',
    'ho' : 'Oseas',
    'jl' : 'Joel',
    'am' : 'Amós',
    'ob' : 'Abdías',
    'jn' : 'Jonás',
    'mi' : 'Miqueas',
    'na' : 'Nahúm',
    'hk' : 'Habacuc',
    'zp' : 'Sofonías',
    'hg' : 'Ageo',
    'zc' : 'Zacarías',
    'ml' : 'Malaqías',
    'mt' : 'Mateo',
    'mk' : 'Marcos',
    'lk' : 'Lucas',
    'jo' : 'Juan',
    'act': 'Hechos',
    'rm' : 'Romanos',
    '1co': '1 de Corintios',
    '2co': '2 de Corintios',
    'gl' : 'Gálatas',
    'eph': 'Efesios',
    'ph' : 'Filipenses',
    'cl' : 'Colosenses',
    '1ts': '1 de Tesalonisenses',
    '2ts': '2 de Tesalonisenses',
    '1tm': '1 de Timoteo',
    '2tm': '2 de Timoteo',
    'tt' : 'Tito',
    'phm': 'Filemón',
    'hb' : 'Hebreos',
    'jm' : 'Santiago',
    '1pe': '1 de Pedro',
    '2pe': '2 de Pedro',
    '1jo': '1 de Juan',
    '2jo': '2 de Juan',
    '3jo': '3 de Juan',
    'jd' : 'Judas',
    're' : 'Apocalipsis'
}
## Available book acronyms
AVAILABLE_BOOKS_ACRONYMS = ['CS']

## Quiz related
### Number of questions in a chapter quiz
CHAPTER_QUIZ_TOTAL_QUESTIONS = 10
### Number of questions in a day quiz
DAY_QUIZ_TOTAL_QUESTIONS = 5
### persentage of average day quizzes counted for general knowledge 
QUIZ_DAY_PONDERATION = .3
### persentage of average chapter quizzes counted for general knowledge
QUIZ_CHAPTER_PONDERATION = .7
### Independent quiz day constant
QUIZ_INDEPEPENDENT_DAY = 999
### Acceptable independent quiz specifires
QUIZ_SPECIFIERS = ['dia', 'capitulo', 'día', 'capítulo']