import json
import httpx
from aiogram import Bot
from config import BOT_TOKEN
from services.storage_service import list_student_materials_by_name
import database.crud as crud

client = Bot(token=BOT_TOKEN)
TG_ADMIN_ID = 922135759
FOREIGN_GPT_ENDPOINT = "http://80.74.26.222:8000/gpt"


def build_prompt_context(student, language="ru"):
    """
    Собирает базовый контекст по студенту: имя, предмет, профиль (цель+уровень).
    """
    name = student.name
    subject = student.subject or "предмет"
    try:
        extra = json.loads(student.other_inf or "{}")
        profile = extra.get("profile") or f"{extra.get('goal', '')}, уровень: {extra.get('level', '')}"
    except Exception:
        profile = student.other_inf or ""
    return name, subject, profile


# services/gpt_service.py

import httpx
from database import crud

async def ask_gpt(
    prompt: str,
    system_prompt: str,
    temperature: float = 0.7,
    model: str = "gpt-3.5-turbo",
    student_id: int | None = None
) -> str:
    """
    Отправляет запрос на GPT-прокси, возвращает текст ответа.
    Если передан student_id и в ответе есть поля usage,
    добавляет их в базу через crud.add_token_usage.
    """
    payload = {
        "prompt": prompt,
        "system_prompt": system_prompt,
        "temperature": temperature,
        "model": model
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(FOREIGN_GPT_ENDPOINT, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        # если что-то пошло не так с сетью или прокси
        return "⚠️ GPT недоступен. Попробуйте позже."

    content = data.get("content", "").strip()
    usage   = data.get("usage", {})

    if student_id and isinstance(usage, dict):
        # Сохраняем использованные токены
        prompt_tokens     = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        # В crud.add_token_usage: добавляет токены к студенту
        await crud.add_token_usage(
            student_id=student_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )

    return content



async def generate_study_plan(student,
                              model: str,
                              language: str = "ru",
                              output_format: str = "text",
                              feedback: str | None = None) -> str:
    """
    Генерирует учебный план (или правки по feedback).
    """
    name, subject, profile = build_prompt_context(student)
    materials = await list_student_materials_by_name(name)
    context = "\n".join(f"- {m}" for m in materials) if materials else "(нет данных)"

    prompt = (
        f"Составь подробный учебный план по предмету {subject} для ученика {name}. "
        f"Исходные данные об ученике: {profile}. "
        f"Ранее выданные материалы:\n{context}\n"
        "Распредели темы по занятиям и укажи цели каждого этапа."
    )
    if feedback:
        prompt += f"\n\nУчитывай замечания: {feedback}"
    if output_format == "tex":
        prompt += "\nОтформатируй ответ как LaTeX документ, используя секции и окружения для заголовков и списков."

    return await ask_gpt(
        prompt=prompt,
        system_prompt="Ты — опытный методист, формируй подробный учебный план по шагам.",
        temperature=0.7,
        model=model,
        student_id=student.students_id
    )


# services/gpt_service.py
import json
from services.storage_service import list_student_materials_by_name
import database.crud as crud

async def generate_assignment(
    student,
    model: str,
    topic: str | None = None,
    num_questions: int = 5,
    language: str = "ru",
    output_format: str = "text",
    feedback: str | None = None
) -> str:
    """
    Генерирует задание (контрольное или классную работу),
    учитывая уже накопленный текстовый отчёт по ученику.
    """
    # 1) Собираем контекст по ученику
    name, subject, profile = build_prompt_context(student, language)

    # 2) Достаём текущий текстовый отчёт из БД
    report_text = await crud.get_report_text(student.students_id)
    report_intro = ("Текущий отчёт по ученику (план + все предыдущие разделы):\n"
                    f"{report_text}\n\n")

    # 3) Определяем тему, если её нет
    if not topic:
        topic = "следующей теме из учебного плана, указанной в отчёте"

    # 4) Собираем базовый промпт
    if language == "ru":
        base = (
            report_intro +
            f"Составь задание по теме «{topic}» по предмету {subject} для ученика {name}. "
            f"Уровень ученика: {profile}. "
            f"Включи {num_questions} вопросов повышенной сложности. "
            "Старайся затронуть разные аспекты темы."
        )
    else:
        # (оставляем на будущее, сейчас только русский)
        base = (
            report_intro +
            f"Create an assignment on the topic {topic} for {subject} for student {name}. "
            f"Include {num_questions} challenging questions."
        )

    # 5) Добавляем обратную связь, если есть
    prompt = base
    if feedback:
        prompt += f"\n\nУчитывай замечания: {feedback}"

    # 6) LaTeX-формат, если нужно
    if output_format == "tex":
        prompt += "\nОтформатируй ответ как LaTeX документ, с окружением для вопросов."

    # 7) Шлём запрос и сохраняем статистику токенов
    return await ask_gpt(
        prompt,
        system_prompt="You are a helpful assistant that outputs valid LaTeX.",
        temperature=0.7,
        model=model,
        student_id=student.students_id
    )

# services/gpt_service.py

import json
from services.storage_service import list_student_materials_by_name
import database.crud as crud

async def generate_homework(
    student,
    model: str,
    language: str = "ru",
    output_format: str = "text",
    feedback: str | None = None
) -> str:
    """
    Генерирует домашнее задание (15–25 задач), учитывая текущий отчёт.
    """
    name, subject, profile = build_prompt_context(student, language)

    # достаём накопленный отчёт
    report_text = await crud.get_report_text(student.students_id)
    prompt = (
        f"Текущий отчёт по ученику:\n{report_text}\n\n"
        f"Составь домашнее задание по предмету {subject} для ученика {name}. "
        f"Уровень ученика: {profile}. "
        "Включи 15–25 разнообразных задач для самостоятельной работы."
    )
    if feedback:
        prompt += f"\n\nУчитывай замечания: {feedback}"
    if output_format == "tex":
        prompt += "\nОтформатируй ответ как LaTeX документ, с окружениями для задач."

    return await ask_gpt(
        prompt=prompt,
        system_prompt="Ты — полезный ассистент, генерируй домашние задания.",
        temperature=0.7,
        model=model,
        student_id=student.students_id
    )


async def generate_classwork(
    student,
    model: str,
    language: str = "ru",
    output_format: str = "text",
    feedback: str | None = None
) -> str:
    """
    Генерирует контрольную / классную работу (15–25 задач), учитывая отчёт.
    """
    name, subject, profile = build_prompt_context(student, language)

    report_text = await crud.get_report_text(student.students_id)
    prompt = (
        f"Текущий отчёт по ученику:\n{report_text}\n\n"
        f"Составь контрольную работу по предмету {subject} для ученика {name}. "
        f"Уровень ученика: {profile}. "
        "Включи 15–25 заданий повышенной сложности."
    )
    if feedback:
        prompt += f"\n\nУчитывай замечания: {feedback}"
    if output_format == "tex":
        prompt += "\nОтформатируй ответ как LaTeX документ, с окружениями для заданий."

    return await ask_gpt(
        prompt=prompt,
        system_prompt="Ты — эксперт по составлению тестов, создавай контрольные работы.",
        temperature=0.7,
        model=model,
        student_id=student.students_id
    )


async def generate_learning_materials(
    student,
    model: str,
    language: str = "ru",
    output_format: str = "text",
    feedback: str | None = None
) -> str:
    """
    Рекомендует дополнительные учебные материалы, учитывая отчёт.
    """
    name, subject, profile = build_prompt_context(student, language)

    report_text = await crud.get_report_text(student.students_id)
    prompt = (
        f"Текущий отчёт по ученику:\n{report_text}\n\n"
        f"Подбери дополнительные учебные материалы (статьи, книги, ресурсы) "
        f"по предмету {subject} для ученика {name}. Уровень: {profile}."
    )
    if feedback:
        prompt += f"\n\nУчитывай замечания: {feedback}"
    if output_format == "tex":
        prompt += "\nОтформатируй ответ как LaTeX документ, с окружением itemize для списка."

    return await ask_gpt(
        prompt=prompt,
        system_prompt="Ты — полезный ассистент, рекомендую качественные материалы.",
        temperature=0.7,
        model=model,
        student_id=student.students_id
    )


async def generate_report(
    student,
    model: str,
    language: str = "ru",
    output_format: str = "text",
    feedback: str | None = None
) -> str:
    """
    Генерирует отчёт об успеваемости на основе накопленного текста.
    """
    name, subject, profile = build_prompt_context(student, language)

    report_text = await crud.get_report_text(student.students_id)
    prompt = (
        f"Составь родителям отчёт об успеваемости ученика {name} по предмету {subject}. "
        f"Профиль: {profile}.\n\n"
        f"Текущий текстовый отчёт:\n{report_text}"
    )
    if feedback:
        prompt += f"\n\nУчитывай замечания: {feedback}"
    if output_format == "tex":
        prompt += "\nОтформатируй ответ как LaTeX документ, с секциями результатов и рекомендаций."

    return await ask_gpt(
        prompt=prompt,
        system_prompt="Ты — ассистент по составлению отчётов, пиши чётко и структурированно.",
        temperature=0.7,
        model=model,
        student_id=student.students_id
    )


async def generate_diagnostic_test(
    student,
    model: str,
    language: str = "ru"
) -> str:
    """
    При создании нового ученика: генерирует масштабный диагностический тест.
    """
    name, subject, profile = build_prompt_context(student, language)

    prompt = (
        f"Составь масштабный диагностический тест для ученика {name} по предмету {subject}. "
        "Тест должен охватить ключевые темы, трудные случаи и «ловушки», "
        "чтобы выявить пробелы в знаниях. "
        "Включи разнообразные типы вопросов."
    )

    return await ask_gpt(
        prompt=prompt,
        system_prompt="Ты — эксперт по диагностике знаний, создавай полный тест.",
        temperature=0.7,
        model=model,
        student_id=student.students_id
    )


async def generate_report_summary(
    student,
    model: str,
    report_text: str,
    language: str = "ru"
) -> str:
    """
    Суммирует текстовый отчёт, сохраняя план уроков в начале.
    """
    name, subject, profile = build_prompt_context(student, language)

    prompt = (
        "Ниже текущий текстовый отчёт по ученику. "
        "Сохрани план уроков (первую часть) без изменений, "
        "а остальную информацию обобщи, выделив основные достижения и пройденные темы.\n\n"
        f"{report_text}"
    )

    return await ask_gpt(
        prompt=prompt,
        system_prompt="Ты — ассистент по обобщению отчётов, делай стиль сжатым.",
        temperature=0.7,
        model=model,
        student_id=student.students_id
    )


async def chat_with_gpt(
    student,
    model: str,
    user_message: str,
    language: str = "ru"
) -> str:
    """
    Простая сессия диалога с GPT про данного ученика.
    """
    name, subject, profile = build_prompt_context(student, language)

    system = (
        f"Ты — ассистент-педагог по ученику {name} ({subject}). "
        f"Профиль: {profile}. "
        "Отвечай на вопросы преподавателя, подсказывай подходы и объясняй темы."
    )

    return await ask_gpt(
        prompt=user_message,
        system_prompt=system,
        temperature=0.7,
        model=model,
        student_id=student.students_id
    )



async def check_solution(
    student,
    model: str,
    solution: str,
    expected: str,
    language: str = "ru"
) -> str:
    """
    Сравнивает ответ ученика с эталоном и возвращает анализ.
    """
    # Собираем контекст
    name, subject, profile = build_prompt_context(student, language)

    if language == "ru":
        prompt = (
            f"Ты — опытный преподаватель по предмету {subject}. "
            f"Профиль ученика {name}: {profile}.\n\n"
            f"Ответ ученика:\n{solution}\n\n"
            f"Правильный ответ или критерии оценки:\n{expected}\n\n"
            "Проверь решение: укажи, что выполнено правильно, где допущены ошибки, "
            "и дай рекомендации, как улучшить."
        )
        system = "Ты — строгий, но справедливый учитель, подробно разбирай решения."
    else:
        prompt = (
            f"You are an experienced {subject} teacher. "
            f"Student {name} profile: {profile}.\n\n"
            f"Student's solution:\n{solution}\n\n"
            f"Expected answer or grading criteria:\n{expected}\n\n"
            "Check the solution: indicate what's correct, what's wrong, and provide improvement tips."
        )
        system = "You are a helpful teacher assistant, give thorough feedback."

    return await ask_gpt(
        prompt=prompt,
        system_prompt=system,
        temperature=0.5,
        model=model
    )
