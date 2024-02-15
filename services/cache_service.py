class cache_service:

    from services.logger_service import logger_service
    from services.kernel_service import kernel_service
    from services.chat_history_service import chat_history_service

    logger_service = logger_service()
    kernel_service = kernel_service()
    chat_history_service = chat_history_service()

    @staticmethod
    def get_logger_service():
        return cache_service.logger_service

    @staticmethod
    def get_kernel_service():
        return cache_service.kernel_service

    @staticmethod
    def get_chat_history_service():
        return cache_service.chat_history_service    