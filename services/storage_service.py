import io
import os
import yadisk
import config
import logging
from fpdf import FPDF
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


def get_client(token: str = None):
    token_to_use = token or config.YANDEX_DISK_TOKEN
    if not token_to_use:
        logger.warning("No Yandex.Disk token provided.")
        return None
    return yadisk.Client(token=token_to_use)


def ensure_folder_exists(client, path: str):
    if not client.exists(path):
        client.mkdir(path)


def get_student_folder(student) -> str:
    return f"{student.name}_{student.surname}_{student.students_id}"


async def upload_bytes_to_yandex(
    file_obj: io.BytesIO,
    teacher,
    student,
    category: str,  # Примеры: "Домашняя_работа", "Контрольная", "План", "Материалы", "Проверено"
    filename_base: str  # не используется — оставлен для совместимости
) -> bool:
    token = teacher.yandex_token or config.YANDEX_DISK_TOKEN
    client = get_client(token)
    if not client:
        return False

    # Папка: /TutorBot/Иван_Иванов_7/Категория
    student_folder = get_student_folder(student)
    base_path = "/TutorBot"
    student_path = f"{base_path}/{student_folder}"
    category_path = f"{student_path}/{category}"

    try:
        # Создание всех нужных папок
        await asyncio.to_thread(ensure_folder_exists, client, base_path)
        await asyncio.to_thread(ensure_folder_exists, client, student_path)
        await asyncio.to_thread(ensure_folder_exists, client, category_path)

        # Имя файла: "Домашняя_работа_25_02_2024.pdf"
        today = datetime.now().strftime("%d_%m_%Y")
        final_filename = f"{category}_{today}.pdf"
        remote_path = f"{category_path}/{final_filename}"

        # Загрузка
        await asyncio.to_thread(client.upload, file_obj, remote_path)
        return True

    except Exception as e:
        logger.error(f"[YandexDisk Upload Error]: {e}")
        return False


def generate_plan_pdf(plan_text: str, student_name: str):
    pdf = FPDF()
    pdf.add_page()

    font_path = os.path.join("assets", "fonts", "DejaVuSans.ttf")
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", size=12)

    for line in plan_text.split("\n"):
        pdf.multi_cell(0, 10, line)

    os.makedirs("storage", exist_ok=True)
    filename = f"plan_{student_name}.pdf"
    filepath = os.path.join("storage", filename)
    pdf.output(filepath)

    return filepath


def generate_text_pdf(text: str, filename: str, folder="storage"):
    path = os.path.join(folder, f"{filename}.pdf")
    os.makedirs(folder, exist_ok=True)

    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("DejaVu", "", "assets/fonts/DejaVuSans.ttf", uni=True)
    pdf.set_font("DejaVu", size=12)

    for line in text.split("\n"):
        pdf.multi_cell(0, 10, line)

    pdf.output(path)
    return path
