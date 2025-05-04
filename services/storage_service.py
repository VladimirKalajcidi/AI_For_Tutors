import os
import subprocess
import uuid
import logging
import tempfile 
from io import BytesIO
from datetime import datetime

import yadisk
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

# Базовые пути для временных PDF
BASE_PATH    = os.path.dirname(os.path.dirname(__file__))
PDF_TEMP_DIR = os.path.join(BASE_PATH, "storage", "pdfs")
os.makedirs(PDF_TEMP_DIR, exist_ok=True)


# services/storage_service.py

BASE_PATH = os.path.dirname(os.path.dirname(__file__))
STORAGE_ROOT = os.path.join(BASE_PATH, "storage")


async def get_last_student_file_text(student, category: str) -> str:
    base_path = os.path.join(STORAGE_ROOT, "tex", category)

    # 🛠 Создаём папку, если её нет
    os.makedirs(base_path, exist_ok=True)

    student_prefix = f"{student.name}_{student.surname}".strip()

    candidates = [
        f for f in os.listdir(base_path)
        if f.endswith(".tex") and student_prefix in f
    ]
    if not candidates:
        return "(предыдущая версия не найдена)"

    candidates.sort(reverse=True)
    latest_file = os.path.join(base_path, candidates[0])
    return open(latest_file, encoding="utf-8").read()


def generate_text_pdf(text: str, file_name: str, category: str) -> str:
    """
    Генерирует PDF из простого текста и сохраняет исходник.
    """
    # Сохраняем исходный текст в storage/tex/<category>/
    tex_folder = os.path.join("storage", "tex", category)
    os.makedirs(tex_folder, exist_ok=True)
    
    tex_path = os.path.join(tex_folder, f"{file_name}.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(text)

    # Генерация PDF
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


# services/storage_service.py

import yadisk
from yadisk.exceptions import PathExistsError

async def upload_bytes_to_yandex(
    file_obj,  # file-like, уже в позицию 0
    teacher,
    student,
    category: str,
    filename_base: str
) -> bool:
    """
    Загружает байты на Яндекс.Диск в папку /TutorBot/<Фамилия_Имя>/<category>/
    Автоматически перезаписывает, если уже есть файл с таким именем.
    """
    token = teacher.yandex_token
    if not token:
        return False
    y = yadisk.YaDisk(token=token)

    # Формируем пути
    root = "/TutorBot"
    student_name = f"{student.surname}_{student.name}"
    folder = f"{root}/{student_name}/{category}"
    remote_path = f"{folder}/{filename_base}_{datetime.now().strftime('%d_%m_%Y')}.pdf"

    # Создаём папки, если нужно
    for p in (root, f"{root}/{student_name}", folder):
        if not y.exists(p):
            y.mkdir(p)

    # Сохраняем временный файл
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_obj.read())
        tmp.flush()
        tmp_path = tmp.name

    # Пытаемся загрузить, при коллизии — перезаписываем
    try:
        y.upload(tmp_path, remote_path)
    except PathExistsError:
        # Удаляем старый и грузим новый
        y.remove(remote_path)
        y.upload(tmp_path, remote_path)
    finally:
        os.remove(tmp_path)

    return True



async def list_student_materials_by_name(name: str) -> list[str]:
    """
    Возвращает список загруженных материалов студента (синхронно).
    """
    materials_dir = os.path.join(BASE_PATH, "storage", "materials", name)
    if not os.path.isdir(materials_dir):
        return []
    return os.listdir(materials_dir)
