import time
import httpx
import json
from config import PROXYAPI_KEY
from services.storage_service import list_student_materials_by_name

API_URL = "https://api.proxyapi.ru/openai/v1/chat/completions"
MODEL = "gpt-4.1"
HEADERS = {
    "Authorization": f"Bearer {PROXYAPI_KEY}",
    "Content-Type": "application/json"
}


async def generate_study_plan(student, language="ru"):
    name = student.name
    subject_name = student.subject or "предмет"
    try:
        extra = json.loads(student.other_inf or "{}")
        profile_info = extra.get("profile") or f"{extra.get('goal', '')}, уровень: {extra.get('level', '')}"
    except Exception:
        profile_info = student.other_inf or ""

    materials = await list_student_materials_by_name(name)
    context = "\n".join([f"- {f}" for f in materials]) if materials else "(нет данных)"

    if language == "ru":
        prompt = f"Составь подробный учебный план по предмету {subject_name} для ученика {name}. "
        if profile_info:
            prompt += f"Исходные данные об ученике: {profile_info}. "
        prompt += f"Ранее выданные материалы:\n{context}\n"
        prompt += "Распредели темы по занятиям и укажи цели каждого этапа."
    else:
        prompt = f"Create a detailed study plan for {subject_name} for the student {name}. "
        if profile_info:
            prompt += f"Student info: {profile_info}. "
        prompt += f"Previously provided materials:\n{context}\n"
        prompt += "Outline topics by session and state the objectives for each stage."

    return await send_proxyapi_request({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": 3000
    })


async def generate_assignment(student, language="ru"):
    name = student.name
    subject_name = student.subject or "предмет"
    try:
        extra = json.loads(student.other_inf or "{}")
        profile_info = extra.get("profile") or f"{extra.get('goal', '')}, уровень: {extra.get('level', '')}"
    except Exception:
        profile_info = student.other_inf or ""

    topic = "предыдущие темы"

    materials = await list_student_materials_by_name(name)
    context = "\n".join([f"- {f}" for f in materials]) if materials else "(нет данных)"

    if language == "ru":
        prompt = f"Составь задание по предмету {subject_name} для ученика {name}. "
        if profile_info:
            prompt += f"Уровень: {profile_info}. "
        prompt += f"Тема последнего урока: {topic}. "
        prompt += f"Ранее выданные материалы:\n{context}\n"
        prompt += "Задания должны включать теоретическую часть и практические упражнения."
    else:
        prompt = f"Create an assignment in {subject_name} for student {name}. "
        if profile_info:
            prompt += f"Level: {profile_info}. "
        prompt += f"Last lesson topic: {topic}. "
        prompt += f"Previously provided materials:\n{context}\n"
        prompt += "Include both theoretical and practical exercises."

    return await send_proxyapi_request({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": 3000
    })


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
