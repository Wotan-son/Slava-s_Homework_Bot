class SendMessageException(Exception):
    """Исключения отправки сообщения."""

    pass


class APIAnswerException(Exception):
    """Исключение запроса к эндпоинту API-сервиса."""

    pass


class ParseStatusExeption(Exception):
    """Исключение извлечения статуса."""

    pass
