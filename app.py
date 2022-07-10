import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from exceptions import (
    APIAnswerException, ParseStatusExeption, SendMessageException
)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    handlers=[logging.StreamHandler()],
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
)
logger = logging.getLogger(__name__)


sent_errors = []


def send_message(bot, message):
    """Отправка сообщений в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Отправлено сообщение: {message}')
    except SendMessageException:
        logger.error(f'Ошибка отправки сообщения: {message}')


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except Exception:
        message = 'Сбой в получении ответа'
        logger.error(message)
        raise APIAnswerException(message)
    if response.status_code != HTTPStatus.OK:
        message = 'Недоступность эндпоинта'
        logger.error(message)
        raise APIAnswerException(message)
    return response.json()


def check_response(response):
    """Проверка ответа на корректность."""
    if not isinstance(response, dict):
        message = 'Ответ не словарь'
        raise TypeError(message)
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        message = 'Homework не список'
        raise TypeError(message)
    if len(homework) != 0:
        return homework
    message = 'В ответе нет домашней работы'
    raise IndexError(message)


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        message = 'Нет ключа homework_name'
        logger.error(message)
        raise KeyError(message)
    try:
        homework_status = homework['status']
    except KeyError:
        message = 'Нет ключа status'
        logger.error(message)
        raise KeyError(message)
    verdict = HOMEWORK_VERDICTS[homework_status]
    if verdict is None:
        message = 'Отсутствует сообщение о статусе проверки'
        logger.error(message)
        raise ParseStatusExeption(message)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    if not PRACTICUM_TOKEN:
        logger.error('Не задан практикум-токен')
        return False
    if not TELEGRAM_TOKEN:
        logger.error('Не задан токен для телеграма')
        return False
    if not TELEGRAM_CHAT_ID:
        logger.error('Не задан идентификатор чата')
        return False
    return True


def main():
    """Основная логика работы бота."""
    token_checking = check_tokens()
    if token_checking is False:
        message = 'Переменная(-ые) окружения недоступны'
        logger.critical(message)
        raise SystemExit(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    old_response = 0
    while True:
        try:
            response = get_api_answer(current_timestamp)
            check_response(response)
            if response != old_response:
                old_response = response
                check_response(response)
                message = parse_status((response.get('homeworks')[0]))
                send_message(bot, message)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.critical(message)
            if message not in sent_errors:
                send_message(bot, message)
                sent_errors.append(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
