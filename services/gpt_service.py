import json
import httpx
from aiogram import Bot
from config import OPENAI_API_KEY, BOT_TOKEN
from services.storage_service import list_student_materials_by_name

client = Bot(token=BOT_TOKEN)
TG_ADMIN_ID = 922135759
FOREIGN_GPT_ENDPOINT = "http://80.74.26.222:8000/gpt"



def build_prompt_context(student, language="ru"):
    name = student.name
    subject = student.subject or ("предмет" if language == "ru" else "subject")
    try:
        extra = json.loads(student.other_inf or "{}")
        profile = extra.get("profile") or f"{extra.get('goal', '')}, уровень: {extra.get('level', '')}"
    except Exception:
        profile = student.other_inf or ""
    return name, subject, profile

async def ask_gpt(prompt: str,
                  system_prompt: str = "",
                  temperature: float = 0.7,
                  model: str = "gpt-3.5-turbo") -> str:
    """
    Отправляет запрос на сторонний прокси-сервер GPT и возвращает content.
    """
    payload = {
        "prompt": prompt,
        "system_prompt": system_prompt or "You are ChatGPT, always respond in Russian.",
        "temperature": temperature,
        "model": model
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(FOREIGN_GPT_ENDPOINT, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("content", "").strip()
    except Exception:
        return "⚠️ GPT недоступен. Попробуйте позже."

async def generate_study_plan(student,
                              model: str,
                              language: str = "ru",
                              output_format: str = "text") -> str:
    """
    Генерирует учебный план. Если output_format == "tex", просит GPT вернуть LaTeX-код.
    """
    name, subject, profile = build_prompt_context(student, language)
    materials = await list_student_materials_by_name(name)
    context = "\n".join(f"- {m}" for m in materials) if materials else "(нет данных)"
    if language == "ru":
        prompt = (
            f"Составь подробный учебный план по предмету {subject} для ученика {name}. "
            f"Исходные данные об ученике: {profile}. "
            f"Ранее выданные материалы:\n{context}\n"
            "Распредели темы по занятиям и укажи цели каждого этапа."
        )
    else:
        prompt = (
            f"Create a detailed study plan for {subject} for student {name}. "
            f"Student info: {profile}. "
            f"Previously provided materials:\n{context}\n"
            "Outline topics by session and state the objectives."
        )
    if output_format == "tex":
        prompt += "\nОтформатируй ответ как LaTeX документ, используя секции и окружения для заголовков и списков."
    return await ask_gpt(prompt,
                         system_prompt="You are an experienced educational methodologist.",
                         temperature=0.7,
                         model=model)

async def generate_assignment(student,
                              model: str,
                              topic: str = None,
                              num_questions: int = 5,
                              language: str = "ru",
                              output_format: str = "text") -> str:
    """
    Генерирует задание. Если output_format == "tex", просит GPT вернуть LaTeX-код.
    """
    name, subject, profile = build_prompt_context(student, language)
    topic = topic or ("последняя изученная тема" if language == "ru" else "last topic covered")
    if language == "ru":
        prompt = (
            f"Составь задание по теме {topic} по предмету {subject} для ученика {name}. "
            f"Уровень ученика: {profile}. Включи {num_questions} вопросов с повышенной сложностью."
        )
    else:
        prompt = (
            f"Create an assignment on the topic {topic} for {subject} for student {name}. "
            f"Include {num_questions} challenging questions."
        )
    if output_format == "tex":
        prompt += "\nОтформатируй ответ как LaTeX документ, с окружением для вопросов."
    return await ask_gpt(prompt,
                         system_prompt="You are a helpful assistant that outputs valid LaTeX.",
                         temperature=0.7,
                         model=model)

async def generate_homework(student,
                            model: str,
                            language: str = "ru",
                            output_format: str = "text") -> str:
    """
    Генерирует домашнее задание. Если output_format == "tex", просит GPT вернуть LaTeX-код.
    """
    name, subject, profile = build_prompt_context(student, language)
    if language == "ru":
        prompt = (
            f"Составь домашнее задание по предмету {subject} для ученика {name}. "
            f"Уровень ученика: {profile}. Включи несколько задач для самостоятельной работы."
        )
    else:
        prompt = (
            f"Create homework for {subject} for student {name}. "
            f"Include several exercises for independent work."
        )
    if output_format == "tex":
        prompt += "\nОтформатируй ответ как LaTeX документ, с окружениями для задач."
    return await ask_gpt(prompt,
                         system_prompt="You are a helpful assistant that outputs valid LaTeX.",
                         temperature=0.7,
                         model=model)

async def generate_classwork(student,
                             model: str,
                             language: str = "ru",
                             output_format: str = "text") -> str:
    """
    Генерирует классную работу (контрольную). Если output_format == "tex", просит GPT вернуть LaTeX-код.
    """
    name, subject, profile = build_prompt_context(student, language)
    if language == "ru":
        prompt = (
            f"Составь контрольную работу по предмету {subject} для ученика {name}. "
            f"Уровень ученика: {profile}. Включи несколько заданий повышенной сложности."
        )
    else:
        prompt = (
            f"Create a test for {subject} for student {name}. "
            f"Include challenging questions."
        )
    if output_format == "tex":
        prompt += "\nОтформатируй ответ как LaTeX документ, с окружениями для заданий."
    return await ask_gpt(prompt,
                         system_prompt="You are a helpful assistant that outputs valid LaTeX.",
                         temperature=0.7,
                         model=model)

async def generate_learning_materials(student,
                                      model: str,
                                      language: str = "ru",
                                      output_format: str = "text") -> str:
    """
    Рекомендует учебные материалы. Если output_format == "tex", просит GPT вернуть LaTeX-код.
    """
    name, subject, profile = build_prompt_context(student, language)
    if language == "ru":
        prompt = (
            f"Подбери дополнительные учебные материалы (статьи, книги, онлайн-ресурсы) по предмету {subject} "
            f"для ученика {name}. Уровень: {profile}."
        )
    else:
        prompt = (
            f"Recommend additional learning materials for {subject} for student {name}. "
            f"Consider student info: {profile}."
        )
    if output_format == "tex":
        prompt += "\nОтформатируй ответ как LaTeX документ, с окружением itemize для списка материалов."
    return await ask_gpt(prompt,
                         system_prompt="You are a helpful assistant that outputs valid LaTeX.",
                         temperature=0.7,
                         model=model)

async def generate_report(student,
                          model: str,
                          language: str = "ru",
                          output_format: str = "text") -> str:
    """
    Генерирует отчёт об успеваемости. Если output_format == "tex", просит GPT вернуть LaTeX-код.
    """
    name, subject, profile = build_prompt_context(student, language)
    notes = getattr(student, "progress_notes", "")
    if language == "ru":
        prompt = (
            f"Составь родителям отчёт об успеваемости ученика {name} по предмету {subject}. "
            f"Данные об ученике: {profile}. Прогресс: {notes}."
        )
    else:
        prompt = (
            f"Create a progress report for student {name} in {subject}. "
            f"Student info: {profile}. Progress notes: {notes}."
        )
    if output_format == "tex":
        prompt += "\nОтформатируй ответ как LaTeX документ, с секцией результатов и рекомендаций."
    return await ask_gpt(prompt,
                         system_prompt="You are a helpful assistant that outputs valid LaTeX.",
                         temperature=0.7,
                         model=model)
