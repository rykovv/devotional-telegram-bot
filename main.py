from configparser import ConfigParser

CONFIG_FILE_NAME = 'config.ini'

def main() -> None:
    config = ConfigParser()
    config.read(CONFIG_FILE_NAME)

    print(config['database']['address'])

if __name__ == '__main__':
    main()