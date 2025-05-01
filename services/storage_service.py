import os
import subprocess
import uuid
import logging
from io import BytesIO
from datetime import datetime

import yadisk
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

# Базовые пути для временных PDF
BASE_PATH    = os.path.dirname(os.path.dirname(__file__))
PDF_TEMP_DIR = os.path.join(BASE_PATH, "storage", "pdfs")
os.makedirs(PDF_TEMP_DIR, exist_ok=True)


def generate_text_pdf(text: str, file_name: str) -> str:
    """
    Генерирует PDF из простого текста.
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
    Обёртка для generate_text_pdf, сохраняет совместимость.
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_name = f"Plan_{student_name}_{timestamp}"
    return generate_text_pdf(text, file_name)


def generate_tex_pdf(tex_code: str, file_name: str) -> str:
    """
    Компилирует LaTeX-код в PDF (через pdflatex),
    автоматически добавляя минимальную преамбулу.
    """
    build_id  = uuid.uuid4().hex
    build_dir = os.path.join(PDF_TEMP_DIR, build_id)
    os.makedirs(build_dir, exist_ok=True)

    tex_path = os.path.join(build_dir, f"{file_name}.tex")
    preamble = r"""\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage[russian]{babel}
\usepackage{geometry}
\geometry{a4paper, margin=25mm}
\begin{document}
"""
    ending = r"\end{document}"
    full_code = f"{preamble}\n{tex_code}\n{ending}"

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(full_code)

    subprocess.run(
        ["pdflatex", "-interaction=batchmode", tex_path],
        cwd=build_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False
    )

    pdf_path = os.path.join(build_dir, f"{file_name}.pdf")
    if not os.path.exists(pdf_path):
        log_path = os.path.join(build_dir, f"{file_name}.log")
        raise RuntimeError(
            f"PDF не сгенерирован, проверьте LaTeX-код. Смотрите лог: {log_path}"
        )
    return pdf_path


async def upload_bytes_to_yandex(
    file_obj: BytesIO,
    teacher,
    student,
    category: str,
    filename_base: str = None
) -> str:
    """
    Загружает файл из BytesIO на Яндекс.Диск в папку:
      /TutorBot/<Фамилия>_<Имя>/<Категория>/<Категория>_<DD_MM_YYYY>.pdf
    """
    token = getattr(teacher, "yandex_token", None)
    if not token:
        raise RuntimeError("Нет токена Яндекс.Диска у преподавателя.")
    y = yadisk.YaDisk(token=token)

    # Формируем пути
    root_dir     = "/TutorBot"
    student_name = f"{student.surname}_{student.name}"
    student_dir  = f"{root_dir}/{student_name}"
    category_dir = f"{student_dir}/{category}"

    # Создаём папки, если их нет
    if not y.exists(root_dir):
        y.mkdir(root_dir)
    if not y.exists(student_dir):
        y.mkdir(student_dir)
    if not y.exists(category_dir):
        y.mkdir(category_dir)

    # Имя файла: категория + дата
    date_str      = datetime.now().strftime("%d_%m_%Y")
    safe_category = category.replace(" ", "_")
    filename      = f"{safe_category}_{date_str}.pdf"

    remote_path = f"{category_dir}/{filename}"
    y.upload(file_obj, remote_path)
    return remote_path


async def list_student_materials_by_name(name: str) -> list[str]:
    """
    Возвращает список загруженных материалов студента (синхронно).
    """
    materials_dir = os.path.join(BASE_PATH, "storage", "materials", name)
    if not os.path.isdir(materials_dir):
        return []
    return os.listdir(materials_dir)
