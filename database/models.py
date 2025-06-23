"""
Модели базы данных для Instagram Automation Bot v2.0
ОБНОВЛЕННЫЙ ФАЙЛ database/models.py
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean, Float
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Admin(Base):
    """Модель администратора"""
    __tablename__ = 'admins'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Admin(id={self.id}, telegram_id={self.telegram_id})>"

class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # Связи
    scenarios = relationship("Scenario", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id})>"

class ProxyServer(Base):
    """Модель прокси сервера"""
    __tablename__ = 'proxy_servers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)  # Название прокси
    proxy_type = Column(String(20), nullable=False)  # http, https, socks5
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(100), nullable=True)
    password_encrypted = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    last_check = Column(DateTime, nullable=True)
    is_working = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)  # Для балансировки нагрузки
    created_at = Column(DateTime, default=datetime.now)
    
    # Связи
    scenarios = relationship("Scenario", back_populates="proxy_server")
    performance = relationship("ProxyPerformance", back_populates="proxy_server", uselist=False)

    @property
    def connection_string(self):
        """Строка подключения к прокси"""
        return f"{self.proxy_type}://{self.host}:{self.port}"

    def __repr__(self):
        return f"<ProxyServer(id={self.id}, name='{self.name}', {self.connection_string})>"

class Scenario(Base):
    """Модель сценария автоматизации"""
    __tablename__ = 'scenarios'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    proxy_id = Column(Integer, ForeignKey('proxy_servers.id'), nullable=True)
    ig_username = Column(String(100), nullable=False)
    ig_password_encrypted = Column(Text, nullable=False)
    post_link = Column(Text, nullable=False)
    trigger_word = Column(String(255), nullable=False)
    dm_message = Column(Text, nullable=False)
    active_until = Column(DateTime, nullable=False)
    status = Column(String(20), default='running')  # running, paused, stopped
    auth_status = Column(String(20), default='waiting')  # waiting, success, failed
    auth_attempt = Column(Integer, default=1)
    error_message = Column(Text, nullable=True)
    comments_processed = Column(Integer, default=0)
    next_check_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # Связи
    user = relationship("User", back_populates="scenarios")
    proxy_server = relationship("ProxyServer", back_populates="scenarios")
    sent_messages = relationship("SentMessage", back_populates="scenario", cascade="all, delete-orphan")
    pending_messages = relationship("PendingMessage", back_populates="scenario", cascade="all, delete-orphan")
    request_logs = relationship("RequestLog", back_populates="scenario", cascade="all, delete-orphan")
    auth_logs = relationship("AuthenticationLog", back_populates="scenario", cascade="all, delete-orphan")
    challenge_sessions = relationship("ChallengeSession", back_populates="scenario", cascade="all, delete-orphan")

    @property
    def is_active(self):
        """Проверка активности сценария"""
        return self.status == 'running' and datetime.now() < self.active_until

    def __repr__(self):
        return f"<Scenario(id={self.id}, username='{self.ig_username}', status='{self.status}')>"

class SentMessage(Base):
    """Модель отправленного сообщения"""
    __tablename__ = 'sent_messages'
    
    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey('scenarios.id'), nullable=False)
    ig_user_id = Column(String(50), nullable=False)
    sent_at = Column(DateTime, default=datetime.now)
    
    # Связи
    scenario = relationship("Scenario", back_populates="sent_messages")

    def __repr__(self):
        return f"<SentMessage(id={self.id}, scenario_id={self.scenario_id}, ig_user_id='{self.ig_user_id}')>"

class PendingMessage(Base):
    """Модель сообщения в очереди"""
    __tablename__ = 'pending_messages'
    
    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey('scenarios.id'), nullable=False)
    ig_user_id = Column(String(50), nullable=False)
    message_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # Связи
    scenario = relationship("Scenario", back_populates="pending_messages")

    def __repr__(self):
        return f"<PendingMessage(id={self.id}, scenario_id={self.scenario_id}, ig_user_id='{self.ig_user_id}')>"

class RequestLog(Base):
    """Модель лога запросов"""
    __tablename__ = 'request_logs'
    
    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey('scenarios.id'), nullable=False)
    request_time = Column(DateTime, default=datetime.now)
    success = Column(Boolean, default=True)
    
    # Связи
    scenario = relationship("Scenario", back_populates="request_logs")

    def __repr__(self):
        return f"<RequestLog(id={self.id}, scenario_id={self.scenario_id}, success={self.success})>"

# === НОВЫЕ МОДЕЛИ ДЛЯ УЛУЧШЕННОЙ АВТОРИЗАЦИИ ===

class AuthenticationLog(Base):
    """Модель лога авторизации"""
    __tablename__ = 'authentication_logs'
    
    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey('scenarios.id'), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    auth_method = Column(String(50), nullable=False)  # fast, slow, safe_mode
    challenge_type = Column(String(50), nullable=True)  # phone_sms, email, etc.
    proxy_used = Column(String(100), nullable=True)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    user_action = Column(String(100), nullable=True)  # retry_now, switch_proxy, etc.
    created_at = Column(DateTime, default=datetime.now)
    
    # Связи
    scenario = relationship("Scenario", back_populates="auth_logs")

    def __repr__(self):
        return f"<AuthenticationLog(id={self.id}, scenario_id={self.scenario_id}, success={self.success})>"

class ChallengeSession(Base):
    """Модель сессии challenge"""
    __tablename__ = 'challenge_sessions'
    
    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey('scenarios.id'), nullable=False)
    challenge_type = Column(String(50), nullable=False)
    status = Column(String(20), default='active')  # active, resolved, timeout, failed
    started_at = Column(DateTime, default=datetime.now)
    resolved_at = Column(DateTime, nullable=True)
    resolution_method = Column(String(50), nullable=True)  # manual, sms_code, safe_mode
    attempts_count = Column(Integer, default=0)
    
    # Связи
    scenario = relationship("Scenario", back_populates="challenge_sessions")

    def __repr__(self):
        return f"<ChallengeSession(id={self.id}, scenario_id={self.scenario_id}, status='{self.status}')>"

class ProxyPerformance(Base):
    """Модель производительности прокси"""
    __tablename__ = 'proxy_performance'
    
    id = Column(Integer, primary_key=True)
    proxy_id = Column(Integer, ForeignKey('proxy_servers.id'), nullable=False)
    auth_attempts = Column(Integer, default=0)
    auth_successes = Column(Integer, default=0)
    challenge_rate = Column(Float, default=0.0)  # Частота проверок
    avg_response_time = Column(Float, default=0.0)
    last_success = Column(DateTime, nullable=True)
    last_failure = Column(DateTime, nullable=True)
    blacklisted_until = Column(DateTime, nullable=True)
    
    # Связи
    proxy_server = relationship("ProxyServer", back_populates="performance")
    
    @property
    def success_rate(self):
        """Процент успешных авторизаций"""
        if self.auth_attempts == 0:
            return 0
        return (self.auth_successes / self.auth_attempts) * 100

    def __repr__(self):
        return f"<ProxyPerformance(id={self.id}, proxy_id={self.proxy_id}, success_rate={self.success_rate:.1f}%)>"