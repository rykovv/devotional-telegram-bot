FROM python:3
LABEL maintainer = "Vladislav Rykov <rykovinternational@gmail.com>"
COPY devotional-telegram-bot /devotional-telegram-bot
WORKDIR devotional-telegram-bot
RUN pip install -r requirements.txt
CMD [ "python", "./main.py" ]