"""
💬 Генератор ответов для Avito AI Responder

Этот модуль отвечает за:
- Финальную обработку ответов от ИИ-консультанта
- Применение шаблонов и персонализацию
- Форматирование и валидацию ответов
- A/B тестирование разных стилей ответов
- Адаптацию ответов под контекст беседы

Местоположение: src/core/response_generator.py
"""

import random
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from pydantic import BaseModel

from .config import (
    ResponseGeneratorConfig, ResponseStyle, MessageType, 
    RESPONSE_TEMPLATES, get_templates_for_type
)
from .ai_consultant import (
    ConversationAnalysis, UserContext, ProductContext
)


# Настройка логгера
logger = logging.getLogger(__name__)


@dataclass
class ResponseVariant:
    """Вариант ответа для A/B тестирования"""
    
    text: str
    style: ResponseStyle
    template_used: bool
    personalization_level: float  # 0.0-1.0
    estimated_engagement: float   # 0.0-1.0


class ResponseMetrics(BaseModel):
    """Метрики качества ответа"""
    
    length: int
    readability_score: float     # 0.0-1.0 (простота чтения)
    politeness_score: float      # 0.0-1.0 (вежливость)
    urgency_match: float         # 0.0-1.0 (соответствие срочности)
    personalization_score: float # 0.0-1.0 (персонализация)
    
    # Предсказанные метрики
    predicted_response_rate: float    # 0.0-1.0
    predicted_conversion_rate: float  # 0.0-1.0


class ResponseContext(BaseModel):
    """Контекст для генерации ответа"""
    
    conversation_stage: str      # initial, negotiation, closing, post_sale
    conversation_length: int     # количество сообщений в диалоге
    time_since_last_message: int # секунды с последнего сообщения
    user_engagement_level: float # 0.0-1.0 (активность пользователя)
    
    # Бизнес-контекст
    is_urgent_sale: bool = False
    competitor_pressure: bool = False
    seasonal_demand: str = "normal"  # low, normal, high


class PersonalizationEngine:
    """Движок персонализации ответов"""
    
    def __init__(self):
        # Паттерны для вставки имени
        self.name_patterns = [
            "{name}, ",
            "{name}! ",
            "Здравствуйте, {name}! ",
            "{name}, добро пожаловать! "
        ]
        
        # Эмодзи для разных типов сообщений
        self.emoji_map = {
            MessageType.GREETING: ["👋", "😊", "🤝"],
            MessageType.PRICE_QUESTION: ["💰", "💵", "💳"],
            MessageType.AVAILABILITY: ["✅", "👍", "📦"],
            MessageType.MEETING_REQUEST: ["📅", "🏠", "🚗"],
            MessageType.PRODUCT_INFO: ["📋", "ℹ️", "📝"],
            MessageType.DELIVERY_QUESTION: ["🚚", "📦", "🏠"]
        }
        
        # Завершающие фразы
        self.closing_phrases = [
            "Буду рад помочь!",
            "Жду ваших вопросов!",
            "Обращайтесь, если что!",
            "Всегда на связи!",
            "Готов ответить на вопросы!"
        ]
    
    def personalize_response(
        self,
        base_response: str,
        user_context: UserContext,
        message_type: MessageType,
        style: ResponseStyle
    ) -> str:
        """Персонализация ответа под пользователя"""
        
        response = base_response
        
        # Добавляем имя пользователя
        if user_context.name and random.random() < 0.7:  # 70% вероятность
            name_pattern = random.choice(self.name_patterns)
            response = name_pattern.format(name=user_context.name) + response
        
        # Добавляем эмодзи (зависит от стиля)
        if style in [ResponseStyle.FRIENDLY, ResponseStyle.CASUAL]:
            if message_type in self.emoji_map and random.random() < 0.4:
                emoji = random.choice(self.emoji_map[message_type])
                response = f"{emoji} {response}"
        
        # Добавляем завершающую фразу для длинных ответов
        if len(response) > 100 and random.random() < 0.3:
            closing = random.choice(self.closing_phrases)
            response = f"{response} {closing}"
        
        return response
    
    def calculate_personalization_score(
        self,
        response: str,
        user_context: UserContext,
        product_context: ProductContext
    ) -> float:
        """Вычисление уровня персонализации ответа"""
        
        score = 0.0
        
        # Проверяем наличие имени
        if user_context.name and user_context.name.lower() in response.lower():
            score += 0.3
        
        # Проверяем упоминание товара
        if product_context.title.lower() in response.lower():
            score += 0.2
        
        # Проверяем упоминание цены
        if product_context.price and str(product_context.price) in response:
            score += 0.2
        
        # Проверяем адаптацию под историю
        if len(user_context.message_history) > 1:
            score += 0.1
        
        # Проверяем эмодзи и дружелюбность
        emoji_count = len(re.findall(r'[😊👋✅💰📦🚚📅]', response))
        if emoji_count > 0:
            score += min(emoji_count * 0.1, 0.2)
        
        return min(score, 1.0)


class TemplateEngine:
    """Движок работы с шаблонами ответов"""
    
    def __init__(self):
        self.template_cache = {}
        self.usage_stats = {}  # Статистика использования шаблонов
    
    def select_template(
        self,
        message_type: MessageType,
        product_context: ProductContext,
        user_context: UserContext
    ) -> Optional[str]:
        """Выбор подходящего шаблона"""
        
        templates = get_templates_for_type(message_type)
        
        if not templates:
            return None
        
        # Фильтруем шаблоны по контексту
        suitable_templates = []
        
        for template in templates:
            # Проверяем что у нас есть данные для заполнения
            if "{price}" in template and not product_context.price:
                continue
            
            suitable_templates.append(template)
        
        if not suitable_templates:
            return random.choice(templates)  # Возвращаем любой
        
        # Выбираем с учетом статистики (менее используемые предпочтительнее)
        template_weights = []
        for template in suitable_templates:
            usage_count = self.usage_stats.get(template, 0)
            weight = max(1.0 - (usage_count * 0.1), 0.1)  # Меньше веса для часто используемых
            template_weights.append(weight)
        
        # Взвешенный случайный выбор
        selected = random.choices(suitable_templates, weights=template_weights)[0]
        
        # Обновляем статистику
        self.usage_stats[selected] = self.usage_stats.get(selected, 0) + 1
        
        return selected
    
    def fill_template(
        self,
        template: str,
        product_context: ProductContext,
        user_context: UserContext
    ) -> str:
        """Заполнение шаблона данными"""
        
        replacements = {
            "{price}": str(product_context.price) if product_context.price else "договорная",
            "{title}": product_context.title,
            "{condition}": product_context.condition or "хорошее",
            "{seller_name}": product_context.seller_name or "продавец",
            "{location}": product_context.location or "указано в объявлении",
            "{user_name}": user_context.name or ""
        }
        
        result = template
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        
        return result


class QualityAnalyzer:
    """Анализатор качества ответов"""
    
    def __init__(self):
        # Слова вежливости
        self.politeness_words = {
            'спасибо', 'пожалуйста', 'извините', 'здравствуйте', 
            'добро пожаловать', 'рад', 'готов', 'помочь'
        }
        
        # Слова для определения читаемости
        self.complex_words = {
            'необходимо', 'осуществить', 'предоставить', 'реализовать',
            'функционировать', 'продемонстрировать'
        }
    
    def analyze_response_quality(
        self,
        response: str,
        analysis: ConversationAnalysis,
        user_context: UserContext
    ) -> ResponseMetrics:
        """Анализ качества сгенерированного ответа"""
        
        # Базовые метрики
        length = len(response)
        words = response.lower().split()
        
        # Читаемость (простота языка)
        complex_count = sum(1 for word in words if word in self.complex_words)
        readability_score = max(0.0, 1.0 - (complex_count / len(words)) * 2)
        
        # Вежливость
        polite_count = sum(1 for word in words if word in self.politeness_words)
        politeness_score = min(polite_count * 0.3, 1.0)
        
        # Соответствие срочности
        urgency_words = ['срочно', 'быстро', 'скорее', 'немедленно']
        has_urgency = any(word in response.lower() for word in urgency_words)
        
        urgency_match = 1.0
        if analysis.urgency == "high" and not has_urgency:
            urgency_match = 0.5
        elif analysis.urgency == "low" and has_urgency:
            urgency_match = 0.7
        
        # Персонализация
        personalization_score = self._calculate_personalization_in_response(
            response, user_context
        )
        
        # Предсказанные метрики (упрощенная модель)
        predicted_response_rate = (
            readability_score * 0.3 +
            politeness_score * 0.2 +
            urgency_match * 0.2 +
            personalization_score * 0.3
        )
        
        predicted_conversion_rate = predicted_response_rate * 0.7  # Консервативная оценка
        
        return ResponseMetrics(
            length=length,
            readability_score=readability_score,
            politeness_score=politeness_score,
            urgency_match=urgency_match,
            personalization_score=personalization_score,
            predicted_response_rate=predicted_response_rate,
            predicted_conversion_rate=predicted_conversion_rate
        )
    
    def _calculate_personalization_in_response(
        self,
        response: str,
        user_context: UserContext
    ) -> float:
        """Расчет уровня персонализации в ответе"""
        
        score = 0.0
        response_lower = response.lower()
        
        # Имя пользователя
        if user_context.name and user_context.name.lower() in response_lower:
            score += 0.4
        
        # Обращение к предыдущим сообщениям
        if len(user_context.message_history) > 0:
            last_message = user_context.message_history[-1].lower()
            common_words = set(last_message.split()) & set(response_lower.split())
            if len(common_words) > 2:
                score += 0.3
        
        # Эмодзи и дружелюбность
        if re.search(r'[😊👋✅💰📦🚚📅]', response):
            score += 0.2
        
        # Конкретные детали
        specific_words = ['цена', 'состояние', 'доставка', 'встреча', 'осмотр']
        if any(word in response_lower for word in specific_words):
            score += 0.1
        
        return min(score, 1.0)


class ResponseGenerator:
    """
    💬 Главный класс генератора ответов
    
    Координирует весь процесс создания финальных ответов:
    1. Выбор между ИИ и шаблонами
    2. Персонализация под пользователя
    3. Форматирование и валидация
    4. A/B тестирование вариантов
    5. Анализ качества ответов
    """
    
    def __init__(self, config: ResponseGeneratorConfig):
        """
        Инициализация генератора ответов
        
        Args:
            config: Конфигурация генератора
        """
        self.config = config
        
        # Движки обработки
        self.personalizer = PersonalizationEngine()
        self.template_engine = TemplateEngine()
        self.quality_analyzer = QualityAnalyzer()
        
        # Метрики
        self.metrics = {
            "responses_generated": 0,
            "templates_used": 0,
            "ai_responses_used": 0,
            "avg_quality_score": 0.0,
            "avg_personalization_score": 0.0
        }
        
        logger.info("Генератор ответов инициализирован")
    
    async def generate_response(
        self,
        ai_response: str,
        analysis: ConversationAnalysis,
        user_context: UserContext,
        product_context: ProductContext,
        response_context: Optional[ResponseContext] = None
    ) -> Tuple[str, ResponseMetrics]:
        """
        🎯 Главный метод генерации финального ответа
        
        Args:
            ai_response: Ответ от ИИ-консультанта
            analysis: Анализ сообщения
            user_context: Контекст пользователя
            product_context: Контекст товара
            response_context: Контекст беседы (опционально)
            
        Returns:
            Tuple[str, ResponseMetrics]: (финальный_ответ, метрики_качества)
        """
        self.metrics["responses_generated"] += 1
        
        logger.info("Генерация финального ответа для типа %s", analysis.message_type)
        
        try:
            # 1. Решаем использовать ли шаблон или ИИ ответ
            use_template = (
                self.config.use_templates and
                random.random() < self.config.template_probability
            )
            
            base_response = ai_response
            template_used = False
            
            if use_template:
                template = self.template_engine.select_template(
                    analysis.message_type, product_context, user_context
                )
                
                if template:
                    base_response = self.template_engine.fill_template(
                        template, product_context, user_context
                    )
                    template_used = True
                    self.metrics["templates_used"] += 1
                    logger.debug("Использован шаблон для типа %s", analysis.message_type)
                else:
                    self.metrics["ai_responses_used"] += 1
            else:
                self.metrics["ai_responses_used"] += 1
            
            # 2. Применяем персонализацию
            if self.config.include_user_name or self.config.include_product_details:
                personalized_response = self.personalizer.personalize_response(
                    base_response,
                    user_context,
                    analysis.message_type,
                    ResponseStyle.FRIENDLY  # TODO: брать из конфига пользователя
                )
            else:
                personalized_response = base_response
            
            # 3. Форматируем и валидируем
            final_response = self._format_and_validate_response(
                personalized_response,
                analysis,
                user_context,
                product_context
            )
            
            # 4. Анализируем качество
            quality_metrics = self.quality_analyzer.analyze_response_quality(
                final_response, analysis, user_context
            )
            
            # 5. Обновляем метрики
            self._update_metrics(quality_metrics, template_used)
            
            logger.info("Ответ сгенерирован, качество: %.2f, длина: %d", 
                       quality_metrics.predicted_response_rate, quality_metrics.length)
            
            return final_response, quality_metrics
            
        except Exception as e:
            logger.error("Ошибка генерации ответа: %s", e)
            
            # Возвращаем базовый ответ при ошибке
            fallback_response = self._get_fallback_response(analysis.message_type)
            fallback_metrics = ResponseMetrics(
                length=len(fallback_response),
                readability_score=0.8,
                politeness_score=0.7,
                urgency_match=0.5,
                personalization_score=0.0,
                predicted_response_rate=0.6,
                predicted_conversion_rate=0.4
            )
            
            return fallback_response, fallback_metrics
    
    def generate_ab_variants(
        self,
        ai_response: str,
        analysis: ConversationAnalysis,
        user_context: UserContext,
        product_context: ProductContext,
        num_variants: int = 2
    ) -> List[ResponseVariant]:
        """
        🧪 Генерация вариантов для A/B тестирования
        
        Args:
            ai_response: Базовый ответ от ИИ
            analysis: Анализ сообщения
            user_context: Контекст пользователя
            product_context: Контекст товара
            num_variants: Количество вариантов
            
        Returns:
            List[ResponseVariant]: Список вариантов ответов
        """
        variants = []
        
        styles = [ResponseStyle.FRIENDLY, ResponseStyle.PROFESSIONAL, ResponseStyle.SALES]
        
        for i in range(min(num_variants, len(styles))):
            style = styles[i]
            
            # Генерируем вариант с разными настройками
            if i % 2 == 0:
                # Вариант с шаблоном
                template = self.template_engine.select_template(
                    analysis.message_type, product_context, user_context
                )
                
                if template:
                    response_text = self.template_engine.fill_template(
                        template, product_context, user_context
                    )
                    template_used = True
                else:
                    response_text = ai_response
                    template_used = False
            else:
                # Вариант с ИИ ответом
                response_text = ai_response
                template_used = False
            
            # Персонализация
            personalized = self.personalizer.personalize_response(
                response_text, user_context, analysis.message_type, style
            )
            
            # Расчет метрик
            personalization_level = self.personalizer.calculate_personalization_score(
                personalized, user_context, product_context
            )
            
            # Простая оценка вовлеченности
            engagement = self._estimate_engagement(personalized, analysis, style)
            
            variant = ResponseVariant(
                text=personalized,
                style=style,
                template_used=template_used,
                personalization_level=personalization_level,
                estimated_engagement=engagement
            )
            
            variants.append(variant)
        
        return variants
    
    def _format_and_validate_response(
        self,
        response: str,
        analysis: ConversationAnalysis,
        user_context: UserContext,
        product_context: ProductContext
    ) -> str:
        """Форматирование и валидация ответа"""
        
        # Убираем лишние пробелы
        formatted = re.sub(r'\s+', ' ', response.strip())
        
        # Проверяем длину
        if len(formatted) < self.config.min_response_length:
            # Дополняем короткий ответ
            formatted += " Буду рад ответить на ваши вопросы!"
        
        if len(formatted) > self.config.max_response_length:
            # Обрезаем длинный ответ
            formatted = formatted[:self.config.max_response_length - 3] + "..."
        
        # Убеждаемся что предложение заканчивается правильно
        if not formatted.endswith(('.', '!', '?')):
            formatted += '.'
        
        # Первая буква заглавная
        if formatted:
            formatted = formatted[0].upper() + formatted[1:]
        
        return formatted
    
    def _estimate_engagement(
        self,
        response: str,
        analysis: ConversationAnalysis,
        style: ResponseStyle
    ) -> float:
        """Оценка предполагаемой вовлеченности"""
        
        score = 0.5  # Базовая оценка
        
        # Длина ответа
        if 50 <= len(response) <= 200:
            score += 0.2
        
        # Стиль и тип сообщения
        if style == ResponseStyle.FRIENDLY and analysis.sentiment == "positive":
            score += 0.2
        elif style == ResponseStyle.SALES and analysis.message_type == MessageType.PRICE_QUESTION:
            score += 0.2
        
        # Наличие вопросов (стимулирует диалог)
        if '?' in response:
            score += 0.1
        
        # Эмодзи
        if re.search(r'[😊👋✅💰📦🚚📅]', response):
            score += 0.1
        
        return min(score, 1.0)
    
    def _get_fallback_response(self, message_type: MessageType) -> str:
        """Запасной ответ при ошибках"""
        
        fallbacks = {
            MessageType.GREETING: "Здравствуйте! Спасибо за интерес к объявлению.",
            MessageType.PRICE_QUESTION: "Цена указана в объявлении. Готов обсудить детали.",
            MessageType.AVAILABILITY: "Товар доступен. Можете приехать посмотреть.",
            MessageType.MEETING_REQUEST: "Можем встретиться для осмотра. Напишите когда удобно.",
            MessageType.PRODUCT_INFO: "Вся информация есть в описании. Что именно интересует?",
            MessageType.DELIVERY_QUESTION: "По доставке можем договориться отдельно."
        }
        
        return fallbacks.get(
            message_type,
            "Спасибо за сообщение! Отвечу подробнее в ближайшее время."
        )
    
    def _update_metrics(self, quality_metrics: ResponseMetrics, template_used: bool) -> None:
        """Обновление метрик генератора"""
        
        # Обновляем среднее качество
        current_avg_quality = self.metrics["avg_quality_score"]
        total_responses = self.metrics["responses_generated"]
        
        new_quality = quality_metrics.predicted_response_rate
        self.metrics["avg_quality_score"] = (
            (current_avg_quality * (total_responses - 1) + new_quality) / total_responses
        )
        
        # Обновляем среднюю персонализацию
        current_avg_pers = self.metrics["avg_personalization_score"]
        new_pers = quality_metrics.personalization_score
        self.metrics["avg_personalization_score"] = (
            (current_avg_pers * (total_responses - 1) + new_pers) / total_responses
        )
    
    def get_metrics(self) -> Dict:
        """Получение метрик генератора"""
        
        template_usage_rate = 0.0
        if self.metrics["responses_generated"] > 0:
            template_usage_rate = self.metrics["templates_used"] / self.metrics["responses_generated"]
        
        return {
            **self.metrics,
            "template_usage_rate": template_usage_rate,
            "template_stats": dict(self.template_engine.usage_stats)
        }
    
    def clear_cache(self) -> None:
        """Очистка кешей генератора"""
        
        self.template_engine.template_cache.clear()
        self.template_engine.usage_stats.clear()
        
        logger.info("Кеши генератора ответов очищены")


# Фабричная функция
def create_response_generator(config: Optional[ResponseGeneratorConfig] = None) -> ResponseGenerator:
    """
    🏭 Создание настроенного генератора ответов
    
    Args:
        config: Конфигурация генератора (опционально)
        
    Returns:
        ResponseGenerator: Готовый генератор
    """
    
    if not config:
        config = ResponseGeneratorConfig()
    
    generator = ResponseGenerator(config)
    
    logger.info("Генератор ответов создан и готов к работе")
    
    return generator