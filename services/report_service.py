# services/report_service.py

import os
import tempfile
from datetime import datetime
import yadisk
from services.gpt_service import ask_gpt
import database.crud as crud

REPORT_FILENAME = "text_report.txt"
SERVICE_FOLDER = "сервисные данные"
PLAN_MARKER = "---END PLAN---"

async def append_to_text_report(
    teacher_id: int,
    student_id: int,
    section: str,
    content: str
) -> None:
    """
    Добавляет раздел в текстовый отчёт ученика на Яндекс.Диске.

    Структура файла:
      1) Блок плана (до PLAN_MARKER) – неизменяемый после первой вставки.
      2) Сводка GPT – вставляется раз в каждые 5 записей.
      3) Все остальные разделы в порядке добавления.
    """
    # 1) Проверяем преподавателя и ученика
    teacher = await crud.get_teacher_by_id(teacher_id)
    if not teacher:
        raise RuntimeError("Преподаватель не найден.")

    # предполагаем, что в crud есть такая функция:
    student = await crud.get_student_by_id_and_teacher(student_id, teacher_id)
    if not student:
        raise RuntimeError("Ученик не найден или не принадлежит этому преподавателю.")

    token = teacher.yandex_token
    if not token:
        raise RuntimeError("Нет токена Яндекс.Диска у преподавателя.")

    # 2) Инициализируем клиент YaDisk
    y = yadisk.YaDisk(token=token)

    # 3) Путь на диске
    root         = "/TutorBot"
    student_name = f"{student.surname}_{student.name}"
    service_dir  = f"{root}/{student_name}/{SERVICE_FOLDER}"
    remote_path  = f"{service_dir}/{REPORT_FILENAME}"

    # 4) Создаём папки
    for path in (root, f"{root}/{student_name}", service_dir):
        if not y.exists(path):
            y.mkdir(path)

    # 5) Подготовка локального файла
    fd, local_path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)

    if y.exists(remote_path):
        y.download(remote_path, local_path)
        with open(local_path, "r", encoding="utf-8") as f:
            old_text = f.read()
    else:
        old_text = ""

    # 6) Разделяем план и остальное
    if PLAN_MARKER in old_text:
        plan_part, rest = old_text.split(PLAN_MARKER + "\n", 1)
        plan_part += PLAN_MARKER + "\n"
    else:
        plan_part = ""
        rest = ""

    # 7) Вставка первого плана
    if section.lower() == "план" and PLAN_MARKER not in old_text:
        header = f"### План уроков ({datetime.now().date()}):\n"
        plan_part = header + content + "\n" + PLAN_MARKER + "\n"

    # 8) Добавляем новый раздел
    entry = f"\n### {section} ({datetime.now().isoformat()}):\n{content}\n"
    rest += entry

    new_text = plan_part + rest

    # 9) Каждые 5 записей – вставляем сводку
    count = new_text.count("### ")
    if count % 5 == 0:
        summary_prompt = (
            "Сформируй краткий обзор прогресса ученика по следующему текстовому отчёту:\n"
            + new_text
        )
        summary = await ask_gpt(
            summary_prompt,
            system_prompt="You are a succinct summarizer.",
            temperature=0.5,
            model=teacher.model
        )

        if PLAN_MARKER in new_text:
            before, after = new_text.split(PLAN_MARKER + "\n", 1)
            summary_block = f"\n**Итоговый обзор:**\n{summary}\n"
            new_text = before + PLAN_MARKER + "\n" + summary_block + after

    # 10) Сохраняем локально и заливаем с перезаписью
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(new_text)

    # перезаписываем существующий файл
    y.upload(local_path, remote_path, overwrite=True)

    os.remove(local_path)
