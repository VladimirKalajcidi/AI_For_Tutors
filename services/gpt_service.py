import json
import httpx
from aiogram import Bot
from config import OPENAI_API_KEY, BOT_TOKEN
from openai import AsyncOpenAI
from services.storage_service import list_student_materials_by_name

client = AsyncOpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=BOT_TOKEN)
TG_ADMIN_ID = 922135759
FOREIGN_GPT_ENDPOINT = "http://80.74.26.222/gpt"


def build_prompt_context(student, language="ru"):
    name = student.name
    subject = student.subject or ("предмет" if language == "ru" else "subject")
    try:
        extra = json.loads(student.other_inf or "{}")
        profile = extra.get("profile") or f"{extra.get('goal', '')}, уровень: {extra.get('level', '')}"
    except Exception:
        profile = student.other_inf or ""
    return name, subject, profile


import httpx

FOREIGN_GPT_ENDPOINT = "http://80.74.26.222:8000/gpt"

async def ask_gpt(prompt: str, system_prompt: str = "", temperature=0.7):
    print("📤 [ask_gpt] Отправка запроса на иностранный сервер...")

    try:
        payload = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "temperature": temperature
        }
        print("📦 Payload:", payload)

        async with httpx.AsyncClient(timeout=30) as client_http:
            response = await client_http.post(FOREIGN_GPT_ENDPOINT, json=payload)
            print(f"✅ Ответ от сервера: {response.status_code}")

            response.raise_for_status()
            json_data = response.json()
            print("📥 Получено JSON:", json_data)

            return json_data["content"]
    except Exception as e:
        print("❌ Ошибка при обращении к серверу:", repr(e))
        return "⚠️ GPT недоступен. Попробуйте позже."


async def generate_study_plan(student, language="ru"):
    name, subject, profile = build_prompt_context(student, language)
    materials = await list_student_materials_by_name(name)
    context = "\n".join(f"- {m}" for m in materials) if materials else "(нет данных)"
    prompt = (
        f"Составь подробный учебный план по предмету {subject} для ученика {name}. "
        f"Исходные данные об ученике: {profile}. "
        f"Ранее выданные материалы:\n{context}\n"
        f"Распредели темы по занятиям и укажи цели каждого этапа."
        if language == "ru" else
        f"Create a detailed study plan for {subject} for student {name}. "
        f"Student info: {profile}. "
        f"Previously provided materials:\n{context}\n"
        f"Outline topics by session and state the objectives."
    )
    return await ask_gpt(prompt, system_prompt="You are an experienced educational methodologist.", temperature=0.7)


async def generate_assignment(student, topic=None, num_questions=5, language="ru"):
    name, subject, profile = build_prompt_context(student, language)
    topic = topic or ("последняя изученная тема" if language == "ru" else "last studied topic")
    prompt = (
        f"Составь {num_questions} заданий по теме '{topic}' для ученика {name}. "
        f"Сначала выведи задания, затем ответы отдельно. "
        f"Уровень знаний: {profile}."
        if language == "ru" else
        f"Create {num_questions} exercises on the topic '{topic}' for student {name}. "
        f"First list the questions, then the answers separately. "
        f"Level: {profile}."
    )
    return await ask_gpt(prompt, system_prompt="You are a helpful AI that creates educational exercises.", temperature=0.7)


async def check_answer(answer, expected, language="ru"):
    prompt = (
        f"Ученик дал такой ответ: {answer}.\n"
        f"Правильный ответ: {expected}.\n"
        f"Проверь решение ученика, оцени правильность, объясни ошибки и дай рекомендации."
        if language == "ru" else
        f"The student answered: {answer}.\n"
        f"The correct answer is: {expected}.\n"
        f"Evaluate the response, explain any mistakes, and give advice."
    )
    return await ask_gpt(prompt, system_prompt="You are an assistant that evaluates student work.", temperature=0.5)


async def generate_report(student, language="ru"):
    name, subject, profile = build_prompt_context(student, language)
    notes = getattr(student, "progress_notes", "")
    prompt = (
        f"Составь родителям отчёт об успеваемости ученика {name} по предмету {subject}. "
        f"Данные: {profile}. Прогресс: {notes}."
        if language == "ru" else
        f"Write a report for the parents on student {name}'s performance in {subject}. "
        f"Profile: {profile}. Progress: {notes}."
    )
    return await ask_gpt(prompt, system_prompt="You are a professional education analyst.", temperature=0.6)


async def generate_homework(student, language="ru"):
    name, subject, profile = build_prompt_context(student, language)
    study_plan = student.report_student or "(учебный план отсутствует)"
    all_materials = await list_student_materials_by_name(student.name)
    last_homework = next((m for m in reversed(all_materials) if "задание" in m.lower() or "домашнее" in m.lower()), None)
    last_homework_text = last_homework or "(нет предыдущего задания)"
    prompt = (
        f"На основе учебного плана:\n{study_plan}\n"
        f"И предыдущего задания:\n{last_homework_text}\n"
        f"Сгенерируй новое домашнее задание для ученика {name} по предмету {subject}. "
        f"Оно должно логично продолжать предыдущую тему и соответствовать уровню: {profile}. "
        f"Выведи сначала задания, затем — ответы."
        if language == "ru" else
        f"Based on the study plan:\n{study_plan}\n"
        f"And the previous assignment:\n{last_homework_text}\n"
        f"Create a new homework assignment for student {name} in {subject}. "
        f"It should logically follow the previous topic and match the level: {profile}. "
        f"List the tasks first, then the answers."
    )
    return await ask_gpt(prompt, system_prompt="You are an educational assistant for creating homework.", temperature=0.7)
