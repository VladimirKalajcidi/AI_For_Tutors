# services/report_service.py

import os
import tempfile
import re
from datetime import datetime

import yadisk
from services.gpt_service import ask_gpt
import database.crud as crud

REPORT_FILENAME = "text_report.txt"
SERVICE_FOLDER = "сервисные данные"
PLAN_MARKER = "---END PLAN---"
MAX_TOKENS = 7000  # максимально допустимое число токенов в отчёте


async def append_to_text_report(
    teacher_id: int,
    student_id: int,
    section: str,
    content: str
) -> None:
    """
    Добавляет новый раздел в текстовый отчёт ученика на Яндекс.Диске,
    сохраняет неизменным блок плана, формирует автоматическую сводку
    по количеству проведённых уроков и следующей теме, при переполнении
    отчёта — сжимает его GPT до <= MAX_TOKENS токенов.
    """
    # 1) Проверяем преподавателя и ученика
    teacher = await crud.get_teacher_by_id(teacher_id)
    if not teacher:
        raise RuntimeError("Преподаватель не найден.")
    student = await crud.get_student_by_id_and_teacher(student_id, teacher_id)
    if not student:
        raise RuntimeError("Ученик не найден или не принадлежит этому преподавателю.")
    if not teacher.yandex_token:
        raise RuntimeError("Нет токена Яндекс.Диска у преподавателя.")

    # 2) Настраиваем YaDisk и пути
    y = yadisk.YaDisk(token=teacher.yandex_token)
    root         = "/TutorBot"
    student_dir  = f"{root}/{student.surname}_{student.name}"
    service_dir  = f"{student_dir}/{SERVICE_FOLDER}"
    remote_path  = f"{service_dir}/{REPORT_FILENAME}"
    for p in (root, student_dir, service_dir):
        if not y.exists(p):
            y.mkdir(p)

    # 3) Загружаем или инициализируем локальный файл
    fd, local_path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    if y.exists(remote_path):
        y.download(remote_path, local_path)
        with open(local_path, "r", encoding="utf-8") as f:
            old_text = f.read()
    else:
        old_text = ""

    # 4) Разделяем блок плана и остальной текст
    if PLAN_MARKER in old_text:
        plan_part, rest = old_text.split(PLAN_MARKER + "\n", 1)
        plan_part += PLAN_MARKER + "\n"
    else:
        plan_part, rest = "", ""

    # 5) Если это первый раздел "План", вставляем его
    if section.lower() == "план" and PLAN_MARKER not in old_text:
        header = f"### План уроков ({datetime.now().date()}):\n"
        plan_part = header + content + "\n" + PLAN_MARKER + "\n"
        rest = ""

    # 6) Добавляем новый раздел
    timestamp = datetime.now().isoformat()
    rest += f"\n### {section} ({timestamp}):\n{content}\n"

    # 7) Извлекаем темы из плана (строки вида "1. Тема..."/"- Тема...")
    themes = re.findall(r"^[\-\d]+\.\s*(.+)$", plan_part, flags=re.MULTILINE)

    # 8) Считаем, сколько уроков уже проведено
    lessons_done = rest.count("### ")
    past_themes  = themes[:lessons_done]
    next_theme   = themes[lessons_done] if lessons_done < len(themes) else None

    # 9) Формируем краткую сводку прогресса
    summary = f"Проведено уроков: {lessons_done}."
    if past_themes:
        summary += " Пройденные темы: " + ", ".join(past_themes) + "."
    if next_theme:
        summary += f" Следующая тема: {next_theme}."

    # 10) Собираем итоговый текст
    new_text = plan_part + summary + "\n\n" + rest

    # 11) Если объём текста превышает MAX_TOKENS, сжимаем его через GPT
    approx_tokens = len(new_text.split()) * 0.75  # грубая оценка
    if approx_tokens > MAX_TOKENS:
        compress_prompt = (
            f"Сократи следующий текст до не более {MAX_TOKENS} токенов, "
            "оставь только русский связный текст, убери любую разметку:\n\n"
            + new_text
        )
        new_text = await ask_gpt(
            compress_prompt,
            system_prompt="Ты — экспертный редактор, сокращай тексты без потери смысла.",
            temperature=0.5,
            model=teacher.model,
            student_id=student_id
        )

    # 12) Сохраняем локально и загружаем отчёт с перезаписью
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(new_text)
    y.upload(local_path, remote_path, overwrite=True)
    os.remove(local_path)
