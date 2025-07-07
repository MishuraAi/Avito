"""
🔧 ИСПРАВЛЕНИЕ MESSENGER API
Версия: 3.1 с исправленными endpoints

Проблема: 404 ошибка при доступе к чатам
Решение: Используем правильные endpoints и scope
"""

import os
import asyncio
import json
import time
import base64
from datetime import datetime
from typing import List, Dict, Optional

# Устанавливаем зависимости
required_packages = {
    'aiohttp': 'aiohttp',
    'dotenv': 'python-dotenv', 
    'google.generativeai': 'google-generativeai'
}

for module, package in required_packages.items():
    try:
        if module == 'dotenv':
            from dotenv import load_dotenv
            load_dotenv()
        elif module == 'google.generativeai':
            import google.generativeai as genai
        else:
            __import__(module)
    except ImportError:
        print(f"📦 Устанавливаем {package}...")
        os.system(f"pip install {package}")
        if module == 'dotenv':
            from dotenv import load_dotenv
            load_dotenv()
        elif module == 'google.generativeai':
            import google.generativeai as genai

import aiohttp

class AvitoAutoResponderFixed:
    """Исправленный автоответчик для Avito"""
    
    def __init__(self):
        self.client_id = os.getenv('AVITO_CLIENT_ID')
        self.client_secret = os.getenv('AVITO_CLIENT_SECRET')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        self.access_token = None
        self.token_expires_at = None
        self.base_url = "https://api.avito.ru"
        self.processed_messages = set()
        
        # Ваше объявление
        self.item_id = "7464870989"
        self.item_title = "Разработка ботов: увеличим прибыль, сократим расходы"
        self.item_price = 3000
        
        print(f"🔧 Авито Автоответчик (ИСПРАВЛЕННАЯ ВЕРСИЯ)")
        print(f"📦 Объявление: {self.item_title}")
        print(f"💰 Цена: {self.item_price}₽")
        print(f"🆔 ID: {self.item_id}")
        
        # Настройка Gemini AI
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.ai_model = genai.GenerativeModel('gemini-pro')
            print(f"🧠 Gemini AI подключен")
        else:
            print(f"⚠️ GEMINI_API_KEY не найден")
    
    async def get_access_token(self) -> Optional[str]:
        """Получение access token с расширенными правами"""
        if self.access_token and self.token_expires_at and time.time() < self.token_expires_at:
            return self.access_token
        
        print("🔄 Получение access token с messenger scope...")
        
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # Пробуем разные комбинации scope
        scope_variants = [
            'messenger autoload',
            'messenger', 
            'autoload messenger',
            'messenger:read messenger:write',
            'items:read messenger:read messenger:write'
        ]
        
        timeout = aiohttp.ClientTimeout(total=30)
        
        for scope in scope_variants:
            data = {
                'grant_type': 'client_credentials',
                'scope': scope
            }
            
            print(f"🔍 Пробуем scope: {scope}")
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                try:
                    async with session.post(f"{self.base_url}/token", headers=headers, data=data) as response:
                        if response.status == 200:
                            token_data = await response.json()
                            self.access_token = token_data['access_token']
                            expires_in = token_data.get('expires_in', 3600)
                            self.token_expires_at = time.time() + expires_in - 60
                            
                            print(f"✅ Token получен с scope: {scope}")
                            print(f"🔑 Token: {self.access_token[:20]}...")
                            
                            # Проверяем какие права есть у токена
                            actual_scope = token_data.get('scope', 'неизвестно')
                            print(f"📋 Полученные права: {actual_scope}")
                            
                            return self.access_token
                        else:
                            error_text = await response.text()
                            print(f"❌ Ошибка для scope '{scope}': {response.status}")
                            continue
                except Exception as e:
                    print(f"❌ Ошибка запроса: {e}")
                    continue
        
        print("❌ Не удалось получить токен ни с одним scope!")
        return None
    
    async def test_messenger_endpoints(self):
        """Тестирование разных messenger endpoints"""
        token = await self.get_access_token()
        if not token:
            return []
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Список endpoints для тестирования
        endpoints = [
            '/messenger/v1/chats',
            '/messenger/v2/chats', 
            '/messenger/v1/conversations',
            '/core/v1/messenger/chats',
            '/autoload/v1/messenger/chats',
            f'/messenger/v1/chats?item_id={self.item_id}',
            f'/core/v1/items/{self.item_id}/messages'
        ]
        
        print("🔍 Тестирование messenger endpoints...")
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for endpoint in endpoints:
                try:
                    print(f"🔗 Тестируем: {endpoint}")
                    async with session.get(f"{self.base_url}{endpoint}", headers=headers) as response:
                        print(f"📊 Статус: {response.status}")
                        
                        if response.status == 200:
                            data = await response.json()
                            print(f"✅ РАБОТАЕТ! Данные: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
                            return data
                        elif response.status == 403:
                            print(f"🔒 Нет доступа (403) - нужны дополнительные права")
                        elif response.status == 404:
                            print(f"❌ Endpoint не найден (404)")
                        else:
                            error_text = await response.text()
                            print(f"⚠️ Ошибка {response.status}: {error_text[:100]}...")
                            
                except Exception as e:
                    print(f"❌ Ошибка запроса: {e}")
                
                print()  # Пустая строка для читаемости
        
        print("❌ Ни один messenger endpoint не работает!")
        return []
    
    async def alternative_message_check(self):
        """Альтернативный способ проверки сообщений"""
        print("🔄 Пробуем альтернативные способы получения сообщений...")
        
        token = await self.get_access_token()
        if not token:
            return []
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Попытка получить статистику по объявлению
        endpoints_to_try = [
            f'/core/v1/items/{self.item_id}',
            f'/core/v1/items/{self.item_id}/stats',
            f'/autoload/v1/items/{self.item_id}',
            f'/autoload/v1/items/{self.item_id}/contacts'
        ]
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for endpoint in endpoints_to_try:
                try:
                    print(f"🔍 Проверяем: {endpoint}")
                    async with session.get(f"{self.base_url}{endpoint}", headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            print(f"✅ Получены данные: {json.dumps(data, indent=2, ensure_ascii=False)[:300]}...")
                        else:
                            print(f"❌ Статус: {response.status}")
                except Exception as e:
                    print(f"❌ Ошибка: {e}")
        
        return []
    
    def generate_ai_response(self, message_text: str) -> str:
        """Генерация ответа через Gemini AI"""
        try:
            prompt = f"""
Ты продавец услуг по разработке ботов на Авито. К тебе обратился потенциальный клиент.

ТВОЕ ОБЪЯВЛЕНИЕ:
Название: "Разработка ботов: увеличим прибыль, сократим расходы"
Цена: 3000₽

СООБЩЕНИЕ КЛИЕНТА: {message_text}

Ответь профессионально, подчеркни выгоды автоматизации. Не более 2-3 предложений.

ОТВЕТ:
"""
            
            response = self.ai_model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            print(f"❌ Ошибка ИИ: {e}")
            return f"Спасибо за интерес к разработке ботов! 🤖 Готов обсудить ваш проект. Когда удобно созвониться?"

async def main():
    """Диагностика и тестирование"""
    print("🔧 ДИАГНОСТИКА MESSENGER API")
    print("=" * 50)
    
    bot = AvitoAutoResponderFixed()
    
    # Тестируем подключение
    print("\n1️⃣ Тестирование авторизации...")
    token = await bot.get_access_token()
    
    if not token:
        print("❌ Проблема с авторизацией!")
        return
    
    # Тестируем messenger endpoints
    print("\n2️⃣ Тестирование messenger endpoints...")
    await bot.test_messenger_endpoints()
    
    # Альтернативные способы
    print("\n3️⃣ Альтернативные способы получения данных...")
    await bot.alternative_message_check()
    
    print("\n" + "=" * 50)
    print("📊 ДИАГНОСТИКА ЗАВЕРШЕНА")
    print("=" * 50)
    
    print("\n💡 ВОЗМОЖНЫЕ РЕШЕНИЯ:")
    print("1. 🔑 Запросить доступ к Messenger API у Avito")
    print("2. 🌐 Использовать веб-парсинг вместо API")
    print("3. 📞 Связаться с поддержкой Avito API")
    print("4. 🔄 Использовать webhook для получения сообщений")
    
    print(f"\n📧 Ваш аккаунт: shaodubaki@gmail.com")
    print(f"📱 Телефон: 79221800911")
    print(f"🆔 ID: 306348203")
    print(f"📦 Объявление ID: {bot.item_id}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Диагностика прервана")
    except Exception as e:
        print(f"\n💥 Ошибка: {e}")