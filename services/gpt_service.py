import json
import httpx
from aiogram import Bot
from config import BOT_TOKEN
from services.storage_service import (
    list_student_materials_by_name,
    get_last_student_file_text
)

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
from database.crud import add_token_usage

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
    # выбросим исключение наружу, чтобы не прятать ошибки сети/прокси
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(FOREIGN_GPT_ENDPOINT, json=payload)
        resp.raise_for_status()
        data = resp.json()

    content = data.get("content", "").strip()
    usage   = data.get("usage", {})

    if student_id and isinstance(usage, dict):
        prompt_tokens     = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        # сразу пишем в БД
        await add_token_usage(
            student_id=student_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )

    return content


async def generate_study_plan(
    student,
    model: str,
    language: str = "ru",
    output_format: str = "text",
    feedback: str | None = None
) -> str:
    name, subject, profile = build_prompt_context(student)
    materials = await list_student_materials_by_name(name)
    context = "\n".join(f"- {m}" for m in materials) if materials else "(нет данных)"

    if feedback:
        previous = await get_last_student_file_text(student, "study_plan")
        if previous:
            prompt = (
                f"Ниже предыдущий учебный план по предмету {subject} для ученика {name}:\n\n"
                f"{previous}\n\n"
                f"Внеси правки по следующему замечанию:\n{feedback}\n"
                "Сохрани структуру и стиль документа."
            )
        else:
            prompt = (
                f"Составь новый учебный план по предмету {subject} для ученика {name}. "
                f"Профиль: {profile}. Ранее выданные материалы:\n{context}"
            )
    else:
        prompt = (
            f"Составь подробный учебный план по предмету {subject} для ученика {name}. "
            f"Профиль: {profile}. Ранее выданные материалы:\n{context}\n"
            "Распредели темы по занятиям и укажи цели каждого этапа."
        )

    if output_format == "tex":
        prompt += "\nОтформатируй ответ как LaTeX документ."

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
    import os
    name, subject, profile = build_prompt_context(student)

    if feedback:
        previous = await get_last_student_file_text(student, "assignment")
        if previous:
            print("[DEBUG] Предыдущее задание:\n", previous)
            prompt = (
                f"Ниже предыдущее задание по предмету {subject} для ученика {name}:\n\n"
                f"{previous}\n\n"
                f"Внеси правки по замечанию:\n{feedback}\n"
                "Сохрани структуру и стиль документа."
            )
        else:
            prompt = (
                f"Составь новое задание по теме «{topic or 'из учебного плана'}» "
                f"по предмету {subject} для ученика {name}, уровень: {profile}. "
                f"Включи {num_questions} нестандартных задач."
            )
    else:
        report_text = await crud.get_report_text(student.students_id)
        topic = topic or "следующей теме из учебного плана"
        prompt = (
            f"Текущий отчёт по ученику:\n{report_text}\n\n"
            f"Составь задание по теме «{topic}» по предмету {subject} для ученика {name}, "
            f"уровень: {profile}. Включи {num_questions} нестандартных задач."
        )

    if output_format == "tex":
        prompt += "\nСделай форматирование в стиле LaTeX."

    # 📤 Отправляем запрос в GPT
    tex_code = await ask_gpt(
        prompt=prompt,
        system_prompt="Ты — ассистент-преподаватель, пиши задания в LaTeX.",
        temperature=0.7,
        model=model,
        student_id=student.students_id
    )

    # 📁 Сохраняем .tex-файл для последующих правок
    if output_format == "tex":
        dir_path = os.path.join("storage", "tex", "assignment")
        os.makedirs(dir_path, exist_ok=True)
        filename = f"Assignment_{student.name}_{student.surname or ''}.tex"
        file_path = os.path.join(dir_path, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(tex_code)
        print(f"[DEBUG] Сохранён .tex-файл: {file_path}")

    return tex_code



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
    Генерирует домашнее задание или вносит правки в предыдущее.
    """
    from services.storage_service import get_last_student_file_text

    name, subject, profile = build_prompt_context(student, language)
    prompt_parts = []

    if feedback:
        previous = await get_last_student_file_text(student, category="homework")
        prompt_parts.append(f"Предыдущее домашнее задание:\n{previous}")
        prompt_parts.append("Внеси правки по замечаниям, сохранив структуру документа:")
        prompt_parts.append(feedback)
    else:
        report_text = await crud.get_report_text(student.students_id)
        prompt_parts.append(
            f"Текущий отчёт по ученику:\n{report_text}\n\n"
            f"Составь домашнее задание по предмету {subject} для ученика {name}. "
            f"Уровень ученика: {profile}. "
            "Включи 15–25 разнообразных задач для самостоятельной работы."
        )

    if output_format == "tex":
        prompt_parts.append("Отформатируй результат как LaTeX-документ с окружениями для задач.")

    full_prompt = "\n\n".join(prompt_parts)

    return await ask_gpt(
        prompt=full_prompt,
        system_prompt="Ты — полезный ассистент, генерируй или правь домашние задания.",
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
    name, subject, profile = build_prompt_context(student)

    if feedback:
        previous = await get_last_student_file_text(student, "classwork")
        if previous:
            prompt = (
                f"Ниже предыдущая контрольная работа по предмету {subject} для ученика {name}:\n\n"
                f"{previous}\n\n"
                f"Внеси правки согласно замечанию:\n{feedback}\n"
                "Сохрани структуру документа."
            )
        else:
            prompt = (
                f"Составь контрольную работу по предмету {subject} для ученика {name}. "
                f"Профиль: {profile}. Включи 15–25 заданий."
            )
    else:
        report_text = await crud.get_report_text(student.students_id)
        prompt = (
            f"Текущий отчёт по ученику:\n{report_text}\n\n"
            f"Составь контрольную работу по предмету {subject} для ученика {name}. "
            f"Профиль: {profile}. Включи 15–25 заданий."
        )

    if output_format == "tex":
        prompt += "\nОтформатируй как LaTeX-документ."

    return await ask_gpt(
        prompt=prompt,
        system_prompt="Ты — эксперт по тестам, создавай контрольные работы.",
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
    name, subject, profile = build_prompt_context(student)

    if feedback:
        previous = await get_last_student_file_text(student, "materials")
        if previous:
            prompt = (
                f"Ниже предыдущая подборка учебных материалов по предмету {subject} для ученика {name}:\n\n"
                f"{previous}\n\n"
                f"Внеси правки с учётом следующего замечания:\n{feedback}"
            )
        else:
            prompt = (
                f"Подбери подборку учебных материалов по предмету {subject} для ученика {name}, "
                f"уровень: {profile}. Включи теорию, примеры и ресурсы."
            )
    else:
        report_text = await crud.get_report_text(student.students_id)
        prompt = (
            f"Текущий отчёт по ученику:\n{report_text}\n\n"
            f"Подбери учебные материалы по предмету {subject} для ученика {name}, "
            f"уровень: {profile}."
        )

    if output_format == "tex":
        prompt += "\nОформи как LaTeX-документ со списком материалов."

    return await ask_gpt(
        prompt=prompt,
        system_prompt="Ты — методист, подбирай качественные материалы.",
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
    name, subject, profile = build_prompt_context(student)

    if feedback:
        previous = await get_last_student_file_text(student, "report")
        if previous:
            prompt = (
                f"Ниже предыдущий отчёт по ученику {name} по предмету {subject}:\n\n"
                f"{previous}\n\n"
                f"Внеси правки по следующему замечанию:\n{feedback}\n"
                "Сохрани структуру документа и ясность изложения."
            )
        else:
            prompt = (
                f"Составь новый отчёт об успеваемости ученика {name} по предмету {subject}. "
                f"Профиль: {profile}."
            )
    else:
        report_text = await crud.get_report_text(student.students_id)
        prompt = (
            f"Составь родителям отчёт об успеваемости ученика {name} по предмету {subject}. "
            f"Профиль: {profile}.\n\n"
            f"Текущий отчёт:\n{report_text}"
        )

    if output_format == "tex":
        prompt += "\nОформи как структурированный LaTeX-документ."

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


# services/gpt_service.py



async def generate_diagnostic_answer_key(student, model: str, language: str = "ru") -> str:
    """
    Генерирует ответ-ключ к только что сгенерированному диагностическому тесту.
    """
    name, subject, profile = build_prompt_context(student, language)
    prompt = (
        f"Дан диагностический тест для ученика {name} по предмету {subject}.\n"
        "Сформируй для каждого вопроса ответ или решение в виде подробного ключа.\n"
        "Верни ключи в формате Markdown."
    )
    return await ask_gpt(
        prompt=prompt,
        system_prompt="Ты — эксперт, дающий подробные ответ-ключи.",
        temperature=0.0,  # детерминированность
        model=model,
        student_id=student.students_id
    )

# services/gpt_service.py (добавить в конец)

async def generate_diagnostic_answer_key(
    student,
    test_tex: str,
    model: str,
    language: str = "ru"
) -> str:
    """
    Генерирует ключ ответов к диагностическому тесту.
    :param student: объект Student
    :param test_tex: LaTeX-код теста, возвращённый generate_diagnostic_test
    :param model: модель GPT
    :param language: 'ru' или 'en'
    """
    name, subject, profile = build_prompt_context(student, language)
    if language == "ru":
        prompt = (
            f"Ниже приведён диагностический тест по предмету {subject} для ученика {name}:\n\n"
            + test_tex +
            "\n\nСоставь подробный ключ ответов ко всем вопросам этого теста. "
            "Отформатируй результат как полный LaTeX-документ."
        )
        system = "Ты — эксперт по генерации ключей ответов, давай точные ответы в LaTeX."
    else:
        prompt = (
            f"Here is a diagnostic test in LaTeX for {subject} for student {name}:\n\n"
            + test_tex +
            "\n\nGenerate a detailed answer key for every question as a complete LaTeX document."
        )
        system = "You are an expert answer-key generator, output full LaTeX."
    return await ask_gpt(
        prompt=prompt,
        system_prompt=system,
        temperature=0.7,
        model=model,
        student_id=student.students_id
    )
