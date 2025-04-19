import io
import yadisk
import config

def get_client(token: str = None):
    token_to_use = token or config.YANDEX_DISK_TOKEN
    if not token_to_use:
        return None
    client = yadisk.Client(token=token_to_use)
    return client

from fpdf import FPDF
import os

def generate_plan_pdf(plan_text: str, student_name: str):
    pdf = FPDF()
    pdf.add_page()

    font_path = os.path.join("assets", "fonts", "DejaVuSans.ttf")
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", size=12)

    lines = plan_text.split("\n")
    for line in lines:
        pdf.multi_cell(0, 10, line)

    # 📁 Гарантируем, что папка существует
    os.makedirs("storage", exist_ok=True)

    filename = f"plan_{student_name}.pdf"
    filepath = os.path.join("storage", filename)
    pdf.output(filepath)

    return filepath


async def upload_file(file_path: str, teacher, remote_filename: str, folder: str = ""):
    token = teacher.yandex_token or config.YANDEX_DISK_TOKEN
    client = get_client(token)
    if not client:
        return False
    base_folder = "/TutorBot"
    try:
        if not client.exists(base_folder):
            client.mkdir(base_folder)
    except:
        pass
    remote_path = base_folder
    if folder:
        remote_path += f"/{folder}"
        try:
            if not client.exists(remote_path):
                client.mkdir(remote_path)
        except:
            pass
    remote_file_path = f"{remote_path}/{remote_filename}"
    try:
        # Upload file (execute in thread to avoid blocking)
        await __import__("asyncio").to_thread(client.upload, file_path, remote_file_path)
        return True
    except Exception as e:
        return False

async def upload_bytes(file_obj: io.BytesIO, teacher, remote_filename: str, folder: str = ""):
    token = teacher.yandex_token or config.YANDEX_DISK_TOKEN
    client = get_client(token)
    if not client:
        return False
    base_folder = "/TutorBot"
    try:
        if not client.exists(base_folder):
            client.mkdir(base_folder)
    except:
        pass
    remote_path = base_folder
    if folder:
        remote_path += f"/{folder}"
        try:
            if not client.exists(remote_path):
                client.mkdir(remote_path)
        except:
            pass
    remote_file_path = f"{remote_path}/{remote_filename}"
    try:
        await __import__("asyncio").to_thread(client.upload, file_obj, remote_file_path)
        return True
    except Exception as e:
        return False


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
