import time
import logging
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=3)
def send_transaction_notification(self, transaction: dict):
    try:
        logger.info(
            f"Начинаем отправку уведомления для транзакции {transaction['transaction_id']}"
        )
        time.sleep(5)

        if transaction.get("force_error"):
            raise ConnectionError("Ошибка соединения при отправке уведомления")

        logger.info(
            f"Уведомление для транзакции {transaction['transaction_id']} успешно отправлено"
        )

        return {
            "status": "success",
            "message": "Уведомление отправлено",
            "transaction_id": transaction["transaction_id"],
        }
    except Exception as exc:
        logger.error(
            f"Ошибка при отправке уведомления для {transaction['transaction_id']}: {exc}"
        )

        try:
            raise self.retry(exc=exc, countdown=3)
        except MaxRetriesExceededError:
            logger.error(
                f"Превышено максимальное количество попыток для транзакции {transaction['transaction_id']}"
            )

            return {
                "status": "failed",
                "message": f"Не удалось отправить уведомление после 3 попыток: {exc}",
                "transaction_id": transaction["transaction_id"],
            }
