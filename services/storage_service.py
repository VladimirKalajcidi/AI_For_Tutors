import os
import subprocess
import uuid
import logging
from io import BytesIO
from datetime import datetime

import yadisk
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

# Базовый путь к проекту и директория для временного хранения PDF
BASE_PATH = os.path.dirname(os.path.dirname(__file__))
PDF_TEMP_DIR = os.path.join(BASE_PATH, "storage", "pdfs")
# создаём директорию, если не существует
os.makedirs(PDF_TEMP_DIR, exist_ok=True)


def generate_text_pdf(text: str, file_name: str) -> str:
    """
    Генерирует PDF из простого текста (ReportLab).
    """
    pdf_path = os.path.join(PDF_TEMP_DIR, f"{file_name}.pdf")
    c = canvas.Canvas(pdf_path)
    y = 800
    for line in text.splitlines():
        c.drawString(40, y, line)
        y -= 15
        if y < 40:
            c.showPage()
            y = 800
    c.save()
    return pdf_path


def generate_plan_pdf(text: str, student_name: str) -> str:
    """
    Обёртка над generate_text_pdf для планов.
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_name = f"Plan_{student_name}_{timestamp}"
    return generate_text_pdf(text, file_name)


def generate_tex_pdf(tex_code: str, file_name: str) -> str:
    """
    Собирает LaTeX-код в PDF при помощи pdflatex.
    Всегда оборачивает в минимальный шаблон.
    """
    # Создаём уникальную папку сборки
    build_id = uuid.uuid4().hex
    build_dir = os.path.join(PDF_TEMP_DIR, build_id)
    os.makedirs(build_dir, exist_ok=True)

    tex_path = os.path.join(build_dir, f"{file_name}.tex")
    # минимальный LaTeX шаблон
    preamble = r"""\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage[russian]{babel}
\usepackage{geometry}
\geometry{a4paper, margin=25mm}
\begin{document}
"""
    ending = r"\end{document}"
    full_code = preamble + "\n" + tex_code + "\n" + ending

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(full_code)
    # вызываем pdflatex
    subprocess.run(
        ["pdflatex", "-interaction=batchmode", tex_path],
        cwd=build_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    pdf_path = os.path.join(build_dir, f"{file_name}.pdf")
    if not os.path.exists(pdf_path):
        log_path = os.path.join(build_dir, f"{file_name}.log")
        raise RuntimeError(f"PDF не сгенерирован, проверьте код LaTeX. Смотрите лог: {log_path}")
    return pdf_path


async def upload_bytes_to_yandex(
    file_obj: BytesIO,
    teacher,
    student,
    category: str,
    filename_base: str
) -> str:
    """
    Загружает байты из BytesIO в указанную папку на Яндекс.Диске учителя.
    Возвращает удалённый путь.
    """
    token = getattr(teacher, 'yandex_token', None)
    if not token:
        raise RuntimeError("Нет токена Яндекс.Диска в профиле преподавателя.")
    y = yadisk.YaDisk(token=token)
    # создаём корневую папку преподавателя, если её нет
    teacher_dir = f"/{teacher.telegram_id}"
    try:
        if not y.exists(teacher_dir):
            y.mkdir(teacher_dir)
    except Exception as e:
        logger.warning(f"Не удалось создать папку преподавателя на Диске: {e}")
    # создаём папку категории
    remote_dir = f"{teacher_dir}/{category}"
    try:
        if not y.exists(remote_dir):
            y.mkdir(remote_dir)
    except Exception as e:
        logger.warning(f"Не удалось создать папку категории на Диске: {e}")
    # формируем имя файла и загружаем
    filename = f"{filename_base}_{student.students_id}_{uuid.uuid4().hex}.pdf"
    remote_path = f"{remote_dir}/{filename}"
    try:
        y.upload(file_obj, remote_path)
    except Exception as e:
        logger.error(f"Ошибка при загрузке на Яндекс.Диск: {e}")
        raise
    return remote_path


def list_student_materials_by_name(name: str) -> list[str]:
    """
    Список файлов в storage/materials/{name}
    """
    materials_dir = os.path.join(BASE_PATH, "storage", "materials", name)
    if not os.path.isdir(materials_dir):
        return []
    return os.listdir(materials_dir)
