from flask import session
from services.logger_service import logger_service
from services.kernel_service import kernel_service
from services.chat_history_service import chat_history_service

class cache_service:
    @staticmethod
    def get_logger_service():
        return session.get('logger_svc')

    @staticmethod
    def get_kernel_service():
        return session.get('sk_service')

    @staticmethod
    def get_chat_history_service():
        return session.get('chat_history_svc')
    
    @staticmethod
    def initialize_services():
        # Initialize services and store them in the session
        session['logger_svc'] = logger_service()
        session['sk_service'] = kernel_service()
        session['chat_history_svc'] = chat_history_service()