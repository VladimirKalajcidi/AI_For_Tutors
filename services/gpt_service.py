import json
import httpx
from aiogram import Bot
from config import BOT_TOKEN
from services.storage_service import (
    list_student_materials_by_name,
    get_last_student_file_text
)
import database.crud as crud
from database.crud import add_token_usage, get_report_text, mark_topic_completed

client = Bot(token=BOT_TOKEN)
TG_ADMIN_ID = 922135759
FOREIGN_GPT_ENDPOINT = "http://80.74.26.222:8000/gpt"

def build_prompt_context(student, language="ru"):
    name = student.name
    subject = student.subject or "предмет"
    try:
        extra = json.loads(student.other_inf or "{}")
        profile = extra.get("profile") or f"{extra.get('goal', '')}, уровень: {extra.get('level', '')}"
    except Exception:
        profile = student.other_inf or ""
    return name, subject, profile

async def ask_gpt(
    prompt: str,
    system_prompt: str,
    temperature: float = 0.7,
    model: str = "gpt-3.5-turbo",
    student_id: int | None = None
) -> str:
    payload = {
        "prompt": prompt,
        "system_prompt": system_prompt,
        "temperature": temperature,
        "model": model
    }
    async with httpx.AsyncClient(timeout=240) as client:
        resp = await client.post(FOREIGN_GPT_ENDPOINT, json=payload)
        resp.raise_for_status()
        data = resp.json()

    content = data.get("content", "").strip()
    usage = data.get("usage", {})

    if student_id and isinstance(usage, dict):
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        await add_token_usage(
            student_id=student_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )

    return content

async def get_next_topic(student):
    extra = json.loads(student.other_inf or "{}")
    topics = extra.get("topics_plan", [])
    completed = student.lessons_completed or 0
    return topics[completed] if completed < len(topics) else "следующей теме из учебного плана"

async def summarize_lesson(tex_code: str, model: str, student_id: int) -> str:
    prompt = (
        "Вот содержание задания. Напиши 3–5 предложений, начиная со слов 'Мы уже сделали',"
        "Ты должен написать сжатый текст, что мы сделали по предмету изучения(на какие темы нарешали задачи, какие ошибки у ученика выявили так далее) "
        f"\n\n{tex_code}"
    )
    return await ask_gpt(
        prompt=prompt,
        system_prompt="Ты — преподаватель, пиши краткое описание урока по LaTeX-коду.",
        temperature=0.7,
        model=model,
        student_id=student_id
    )

async def generate_homework(student, model: str, topic: str | None = None, num_questions: int = 5, language: str = "ru", output_format: str = "text", feedback: str | None = None) -> str:
    name, subject, profile = build_prompt_context(student)

    if not topic:
        topic = await get_next_topic(student)

    if feedback:
        previous = await get_last_student_file_text(student, "homework")
        if previous:
            prompt = (
                f"Ниже предыдущее домашнее задание по предмету {subject} для ученика {name}:\n\n{previous}\n\n"
                f"Внеси правки по замечанию:{feedback}\nСохрани структуру и стиль документа."
            )
        else:
            prompt = (
                f"Составь новое задание по теме «{topic}» по предмету {subject} для ученика {name}, "
                f"уровень: {profile}. Включи {num_questions} нестандартных задач."
            )
    else:
        report_text = await get_report_text(student.students_id)
        prompt = (
            f"Текущий отчёт по ученику:{report_text}\n\n"
            f"Составь задание по теме «{topic}» по предмету {subject} для ученика {name}, "
            f"уровень: {profile}. Включи {num_questions} нестандартных задач."
        )

    if output_format == "tex":
        prompt += "\nСделай форматирование в стиле LaTeX."

    tex_code = await ask_gpt(
        prompt=prompt,
        system_prompt="Ты — ассистент-преподаватель, пиши задания в LaTeX.",
        temperature=0.7,
        model=model,
        student_id=student.students_id
    )

    summary_text = await summarize_lesson(tex_code, model, student.students_id)
    await crud.append_to_report(student.students_id, "Домашняя работа", summary_text)
    await mark_topic_completed(student.students_id)

    return tex_code

# Другие функции генерации: аналогично переписываются с вызовом summarize_lesson и append_to_report
# generate_assignment, generate_classwork, generate_learning_materials, generate_study_plan, generate_report,
# generate_diagnostic_test, generate_diagnostic_answer_key, generate_report_summary, chat_with_gpt, check_solution
# Их можно переписать в отдельных функциях по аналогичной логике выше при необходимости.



async def generate_study_plan(
    student,
    model: str,
    language: str = "ru",
    output_format: str = "text",
    feedback: str | None = None
) -> str:
    name, subject, profile = build_prompt_context(student)

    if feedback:
        previous = await get_last_student_file_text(student, "study_plan")
        if previous:
            prompt = (
                f"Ниже предыдущий учебный план по предмету {subject} для ученика {name}:\n\n"
                f"{previous}\n\n"
                f"Внеси правки по замечанию:\n{feedback}\nСохрани структуру и стиль документа."
            )
        else:
            prompt = (
                f"Составь учебный план по предмету {subject} для ученика {name}, "
                f"уровень: {profile}. Укажи темы, цели, и последовательность изучения."
            )
    else:
        prompt = (
            f"Составь подробный учебный план по предмету {subject} для ученика {name}, "
            f"уровень: {profile}. Укажи темы, цели и порядок занятий."
        )

    if output_format == "tex":
        prompt += "\nОформи в LaTeX-стиле."

    tex_code = await ask_gpt(prompt, "Ты — преподаватель, составляешь учебные планы.",
                              temperature=0.7, model=model, student_id=student.students_id)

    summary_text = await summarize_lesson(tex_code, model, student.students_id)
    await crud.append_to_report(student.students_id, "План", summary_text)

    return tex_code



async def generate_assignment(
    student,
    model: str,
    topic: str | None = None,
    num_questions: int = 5,
    language: str = "ru",
    output_format: str = "text",
    feedback: str | None = None
) -> str:
    name, subject, profile = build_prompt_context(student)

    if not topic:
        topic = await get_next_topic(student)

    if feedback:
        previous = await get_last_student_file_text(student, "assignment")
        if previous:
            prompt = (
                f"Ниже предыдущее задание по предмету {subject} для ученика {name}:\n\n"
                f"{previous}\n\n"
                f"Внеси правки по замечанию:\n{feedback}\nСохрани структуру и стиль документа."
            )
        else:
            prompt = (
                f"Составь новое задание по теме «{topic}» по предмету {subject} для ученика {name}, "
                f"уровень: {profile}. Включи {num_questions} нестандартных задач."
            )
    else:
        report_text = await get_report_text(student.students_id)
        prompt = (
            f"Текущий отчёт по ученику:\n{report_text}\n\n"
            f"Составь задание по теме «{topic}» по предмету {subject} для ученика {name}, "
            f"уровень: {profile}. Включи {num_questions} нестандартных задач."
        )

    if output_format == "tex":
        prompt += "\nСделай форматирование в стиле LaTeX."

    tex_code = await ask_gpt(prompt, "Ты — ассистент-преподаватель, пиши задания в LaTeX.",
                              temperature=0.7, model=model, student_id=student.students_id)

    summary_text = await summarize_lesson(tex_code, model, student.students_id)
    await crud.append_to_report(student.students_id, "Задание", summary_text)

    return tex_code




# services/gpt_service.py


async def generate_classwork(
    student,
    model: str,
    topic: str | None = None,
    num_questions: int = 5,
    language: str = "ru",
    output_format: str = "text",
    feedback: str | None = None
) -> str:
    name, subject, profile = build_prompt_context(student)

    if not topic:
        topic = await get_next_topic(student)

    if feedback:
        previous = await get_last_student_file_text(student, "classwork")
        if previous:
            prompt = (
                f"Ниже предыдущее классное задание по предмету {subject} для ученика {name}:\n\n"
                f"{previous}\n\n"
                f"Внеси правки по замечанию:\n{feedback}\nСохрани структуру и стиль документа."
            )
        else:
            prompt = (
                f"Составь новое классное задание по теме «{topic}» по предмету {subject} для ученика {name}, "
                f"уровень: {profile}. Включи {num_questions} задач."
            )
    else:
        report_text = await get_report_text(student.students_id)
        prompt = (
            f"Текущий отчёт по ученику:\n{report_text}\n\n"
            f"Составь классную работу по теме «{topic}» по предмету {subject} для ученика {name}, "
            f"уровень: {profile}. Включи {num_questions} задач."
        )

    if output_format == "tex":
        prompt += "\nСделай форматирование в стиле LaTeX."

    tex_code = await ask_gpt(prompt, "Ты — ассистент-преподаватель, пиши задания в LaTeX.",
                              temperature=0.7, model=model, student_id=student.students_id)

    summary_text = await summarize_lesson(tex_code, model, student.students_id)
    await crud.append_to_report(student.students_id, "Классная работа", summary_text)

    return tex_code




async def generate_learning_materials(
    student,
    model: str,
    topic: str | None = None,
    language: str = "ru",
    output_format: str = "text",
    feedback: str | None = None
) -> str:
    name, subject, profile = build_prompt_context(student)

    if not topic:
        topic = await get_next_topic(student)

    if feedback:
        previous = await get_last_student_file_text(student, "materials")
        if previous:
            prompt = (
                f"Ниже предыдущие учебные материалы по предмету {subject} для ученика {name}:\n\n"
                f"{previous}\n\n"
                f"Внеси правки по замечанию:\n{feedback}\nСохрани структуру и стиль документа."
            )
        else:
            prompt = (
                f"Создай учебные материалы по теме «{topic}» по предмету {subject} для ученика {name}, "
                f"уровень: {profile}. Объясни теорию, приведи примеры и задачи."
            )
    else:
        report_text = await get_report_text(student.students_id)
        prompt = (
            f"Текущий отчёт по ученику:\n{report_text}\n\n"
            f"Создай обучающие материалы по теме «{topic}» по предмету {subject} для ученика {name}, "
            f"уровень: {profile}. Объясни теорию, приведи примеры и упражнения."
        )

    if output_format == "tex":
        prompt += "\nОформи в формате LaTeX."

    tex_code = await ask_gpt(prompt, "Ты — преподаватель, создаёшь обучающие материалы.",
                              temperature=0.7, model=model, student_id=student.students_id)

    summary_text = await summarize_lesson(tex_code, model, student.students_id)
    await crud.append_to_report(student.students_id, "Материалы", summary_text)

    return tex_code



# services/gpt_service.py

from services.storage_service import get_last_student_file_text
import database.crud as crud

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
    Генерирует диагностический тест и сразу пишет в report.txt только его краткую сводку.
    """
    name, subject, profile = build_prompt_context(student, language)

    # 1) Собираем сам тест в LaTeX
    test_prompt = (
        f"Составь масштабный диагностический тест для ученика {name} "
        f"по предмету {subject}. Тест должен охватить ключевые темы, "
        "трудные случаи и «ловушки», чтобы выявить пробелы в знаниях. "
        "Включи разные типы вопросов."
    )
    tex_code = await ask_gpt(
        prompt=test_prompt,
        system_prompt="Ты — эксперт по диагностике знаний, создавай полный тест.",
        temperature=0.7,
        model=model,
        student_id=student.students_id
    )

    # 2) Генерируем только человекочитаемую сводку для отчёта
    summary_prompt = (
        f"Вот диагностический тест по предмету {subject} в LaTeX:\n\n{tex_code}\n\n"
        "Напиши 3–5 предложений, начиная со слов «Мы уже сделали», "
        "чтобы кратко описать, какие темы и типы заданий включены в этот тест. "
        "Не используй LaTeX-разметку."
    )
    summary_text = await ask_gpt(
        prompt=summary_prompt,
        system_prompt="Ты — преподаватель, составляющий краткое описание диагностического теста.",
        temperature=0.5,
        model=model,
        student_id=student.students_id
    )

    # 3) Записываем в report.txt только сводку по тесту
    await crud.append_to_report(
        student_id=student.students_id,
        section="Диагностический тест",
        content=summary_text
    )

    return tex_code


async def generate_report_summary(
    student,
    model: str,
    report_text: str,
    language: str = "ru"
) -> str:
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

    feedback = await ask_gpt(
        prompt=prompt,
        system_prompt=system,
        temperature=0.5,
        model=model,
        student_id=student.students_id
    )

    summary = f"Мы уже сделали разбор решения. {feedback.strip()}"
    await crud.append_to_report(
        student_id=student.students_id,
        section="Разбор решения",
        content=summary
    )

    return feedback


async def generate_diagnostic_answer_key(
    student,
    test_tex: str,
    model: str,
    language: str = "ru"
) -> str:
    """
    Генерирует ключ ответов к диагностическому тесту, 
    но НЕ пишет его свёрнутую версию в report.txt.
    """
    name, subject, profile = build_prompt_context(student, language)

    if language == "ru":
        prompt = (
            f"Ниже приведён диагностический тест по предмету {subject} для ученика {name}:\n\n"
            f"{test_tex}\n\n"
            "Составь подробный ключ ответов ко всем вопросам этого теста. "
            "Отформатируй результат как полный LaTeX-документ."
        )
        system = "Ты — эксперт по генерации ключей ответов, давай точные ответы в LaTeX."
    else:
        prompt = (
            f"Here is a diagnostic test in LaTeX for {subject} for student {name}:\n\n"
            f"{test_tex}\n\n"
            "Generate a detailed answer key for every question as a complete LaTeX document."
        )
        system = "You are an expert answer-key generator, output full LaTeX."

    tex_code = await ask_gpt(
        prompt=prompt,
        system_prompt=system,
        temperature=0.7,
        model=model,
        student_id=student.students_id
    )

    return tex_code
