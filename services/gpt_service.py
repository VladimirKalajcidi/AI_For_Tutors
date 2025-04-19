'''from openai import AsyncOpenAI
import config
import json

client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)


async def generate_study_plan(student, language="en"):
    subject_name = student.subject or "предмет"
    try:
        extra = json.loads(student.other_inf or "{}")
        profile_info = extra.get("profile") or f"{extra.get('goal', '')}, уровень: {extra.get('level', '')}"
    except Exception:
        profile_info = student.other_inf or ""

    if language == "ru":
        prompt = f"Составь подробный учебный план по предмету {subject_name} для ученика."
        if profile_info:
            prompt += f" Исходные данные об ученике: {profile_info}."
        prompt += " Распредели темы по занятиям и укажи цели каждого этапа."
    else:
        prompt = f"Create a detailed study plan for {subject_name} for a student."
        if profile_info:
            prompt += f" Student info: {profile_info}."
        prompt += " Outline topics by session and state the objectives for each stage."

    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1024
    )
    return response.choices[0].message.content.strip()


async def generate_assignment(student, topic=None, num_questions=5, language="en"):
    subject_name = student.subject or "предмет"
    if language == "ru":
        prompt = f"Составь {num_questions} задач по теме {topic or subject_name} для ученика. Сначала перечисли вопросы, затем предоставь ответы."
    else:
        prompt = f"Create {num_questions} practice questions for the topic {topic or subject_name}. Provide the questions first, then the answers."

    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1024
    )
    content = response.choices[0].message.content.strip()
    parts = content.split("\n\n")
    if len(parts) >= 2:
        questions = parts[0]
        answers = "\n\n".join(parts[1:])
    else:
        questions = content
        answers = ""
    return questions, answers'''

'''
import httpx
import json
import config  # положи свой OpenRouter API-ключ в config.OPENROUTER_API_KEY

OPENROUTER_API_KEY = "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"

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-3.5-turbo"  # можно заменить на "openai/gpt-4o" или другой поддерживаемый

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "ai-for-tutors",  # любое уникальное название, не url
    "X-Title": "AI for Tutors"
}


async def generate_study_plan(student, language="ru"):
    subject_name = student.subject or "предмет"
    try:
        extra = json.loads(student.other_inf or "{}")
        profile_info = extra.get("profile") or f"{extra.get('goal', '')}, уровень: {extra.get('level', '')}"
    except Exception:
        profile_info = student.other_inf or ""

    if language == "ru":
        prompt = f"Составь подробный учебный план по предмету {subject_name} для ученика."
        if profile_info:
            prompt += f" Исходные данные об ученике: {profile_info}."
        prompt += " Распредели темы по занятиям и укажи цели каждого этапа."
    else:
        prompt = f"Create a detailed study plan for {subject_name} for a student."
        if profile_info:
            prompt += f" Student info: {profile_info}."
        prompt += " Outline topics by session and state the objectives for each stage."

    json_data = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1024
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(OPENROUTER_API_URL, headers=HEADERS, json=json_data)
        result = response.json()
        print("🧠 OpenRouter ответ:", result)

        if "choices" in result and result["choices"]:
            return result["choices"][0]["message"]["content"].strip()
        else:
            return "⚠️ Не удалось сгенерировать учебный план (OpenRouter не ответил)."

async def generate_assignment(student, topic=None, num_questions=5, language="ru"):
    subject_name = student.subject or "предмет"
    if language == "ru":
        prompt = f"Составь {num_questions} задач по теме {topic or subject_name} для ученика. Сначала перечисли вопросы, затем предоставь ответы."
    else:
        prompt = f"Create {num_questions} practice questions for the topic {topic or subject_name}. Provide the questions first, then the answers."

    json_data = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1024
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(OPENROUTER_API_URL, headers=HEADERS, json=json_data)
        result = response.json()
        if "choices" in result and result["choices"]:
            content = result["choices"][0]["message"]["content"].strip()
            parts = content.split("\n\n")
            if len(parts) >= 2:
                questions = parts[0]
                answers = "\n\n".join(parts[1:])
            else:
                questions = content
                answers = ""
            return questions, answers
        else:
            return "⚠️ Не удалось сгенерировать задание (OpenRouter не ответил).", ""
'''


import time
import httpx
import json
import config

API_URL = "https://api.proxyapi.ru/openai/v1/chat/completions"
API_KEY = config.PROXYAPI_KEY
MODEL = "gpt-4.1"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

async def generate_study_plan(student, language="ru"):
    subject_name = student.subject or "предмет"
    try:
        extra = json.loads(student.other_inf or "{}")
        profile_info = extra.get("profile") or f"{extra.get('goal', '')}, уровень: {extra.get('level', '')}"
    except Exception:
        profile_info = student.other_inf or ""

    if language == "ru":
        prompt = f"Составь подробный учебный план по предмету {subject_name} для ученика. "
        if profile_info:
            prompt += f"Исходные данные об ученике: {profile_info}. "
        prompt += "Распредели темы по занятиям и укажи цели каждого этапа."
    else:
        prompt = f"Create a detailed study plan for {subject_name} for a student. "
        if profile_info:
            prompt += f"Student info: {profile_info}. "
        prompt += "Outline topics by session and state the objectives for each stage."

    json_data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": 4000  # обязательный параметр вместо max_tokens
    }

    try:
        start_time = time.time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(API_URL, headers=HEADERS, json=json_data)
        duration = time.time() - start_time

        print(f"🧠 proxyapi.ru ответ за {duration:.2f} секунд: {response.status_code}")
        print(response.text)

        if response.status_code != 200:
            return f"⚠️ Ошибка {response.status_code}: {response.text}"

        try:
            result = response.json()
        except Exception as e:
            return f"⚠️ Ошибка обработки JSON: {e}"

        if "choices" in result and result["choices"]:
            return result["choices"][0]["message"]["content"].strip()
        else:
            return "⚠️ Не удалось сгенерировать учебный план (ответ пустой)."
    except httpx.ReadTimeout:
        return "⏱ Превышено время ожидания ответа от proxyapi. Запрос мог быть платным. Попробуйте позже."
    except Exception as e:
        return f"❌ Не удалось выполнить запрос: {e}"

async def generate_homework(student, topic: str = "", language="ru"):
    subject_name = student.subject or "предмет"
    try:
        extra = json.loads(student.other_inf or "{}")
        profile_info = extra.get("profile") or f"{extra.get('goal', '')}, уровень: {extra.get('level', '')}"
    except Exception:
        profile_info = student.other_inf or ""

    if language == "ru":
        prompt = f"Составь домашнее задание по предмету {subject_name}."
        if topic:
            prompt += f" Тема урока: {topic}."
        if profile_info:
            prompt += f" Данные об ученике: {profile_info}."
        prompt += " Задание должно быть разноплановым: теория, практика, и творческий элемент."
    else:
        prompt = f"Create homework for the subject {subject_name}."
        if topic:
            prompt += f" Topic: {topic}."
        if profile_info:
            prompt += f" Student info: {profile_info}."
        prompt += " Include theoretical, practical and creative tasks."

    json_data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": 3000
    }

    return await send_proxyapi_request(json_data)

async def generate_classwork(student, topic: str = "", language="ru"):
    subject_name = student.subject or "предмет"
    try:
        extra = json.loads(student.other_inf or "{}")
        profile_info = extra.get("profile") or f"{extra.get('goal', '')}, уровень: {extra.get('level', '')}"
    except Exception:
        profile_info = student.other_inf or ""

    if language == "ru":
        prompt = f"Составь контрольную работу по предмету {subject_name}."
        if topic:
            prompt += f" Тема: {topic}."
        if profile_info:
            prompt += f" Уровень ученика: {profile_info}."
        prompt += " Включи задания разного уровня сложности и укажи критерии оценки."
    else:
        prompt = f"Create a test for {subject_name}."
        if topic:
            prompt += f" Topic: {topic}."
        if profile_info:
            prompt += f" Student profile: {profile_info}."
        prompt += " Include questions of various difficulty levels and specify assessment criteria."

    json_data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": 3000
    }

    return await send_proxyapi_request(json_data)


async def generate_learning_materials(student, topic: str = "", language="ru"):
    subject_name = student.subject or "предмет"
    try:
        extra = json.loads(student.other_inf or "{}")
        profile_info = extra.get("profile") or f"{extra.get('goal', '')}, уровень: {extra.get('level', '')}"
    except Exception:
        profile_info = student.other_inf or ""

    if language == "ru":
        prompt = f"Подбери обучающие материалы (статьи, видео, сайты, PDF) по теме {topic} по предмету {subject_name}."
        if profile_info:
            prompt += f" Уровень ученика: {profile_info}."
        prompt += " Укажи ссылки, если возможно."
    else:
        prompt = f"Find study materials (articles, videos, websites, PDFs) for the topic {topic} in {subject_name}."
        if profile_info:
            prompt += f" Student level: {profile_info}."
        prompt += " Include links if possible."

    json_data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": 2500
    }

    return await send_proxyapi_request(json_data)


async def send_proxyapi_request(json_data):
    try:
        start_time = time.time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(API_URL, headers=HEADERS, json=json_data)
        duration = time.time() - start_time

        print(f"🧠 Ответ proxyapi за {duration:.2f} сек: {response.status_code}")
        print(response.text)

        if response.status_code != 200:
            return f"⚠️ Ошибка {response.status_code}: {response.text}"

        result = response.json()

        if "choices" in result and result["choices"]:
            return result["choices"][0]["message"]["content"].strip()
        else:
            return "⚠️ Пустой ответ от модели."
    except httpx.ReadTimeout:
        return "⏱ Время ожидания истекло. Попробуйте позже."
    except Exception as e:
        return f"❌ Ошибка запроса: {e}"

# services/gpt_service.py

async def generate_assignment(student, language="ru"):
    subject_name = student.subject or "предмет"
    try:
        extra = json.loads(student.other_inf or "{}")
        profile_info = extra.get("profile") or f"{extra.get('goal', '')}, уровень: {extra.get('level', '')}"
    except Exception:
        profile_info = student.other_inf or ""

    if language == "ru":
        prompt = f"Составь задания по предмету {subject_name} для ученика."
        if profile_info:
            prompt += f" Исходные данные об ученике: {profile_info}. "
        prompt += "Задания должны включать теоретическую часть и практические упражнения."
    else:
        prompt = f"Create assignments for the subject {subject_name} for the student."
        if profile_info:
            prompt += f" Student info: {profile_info}. "
        prompt += "The assignments should include theoretical and practical exercises."

    json_data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": 3000
    }

    return await send_proxyapi_request(json_data)
