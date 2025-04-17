import io
import yadisk
import config

def get_client(token: str = None):
    token_to_use = token or config.YANDEX_DISK_TOKEN
    if not token_to_use:
        return None
    client = yadisk.Client(token=token_to_use)
    return client

def generate_plan_pdf(plan_text: str, student_name: str):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    # Use a basic font (Helvetica supports Latin characters)
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, plan_text)
    filename = f"plan_{student_name}.pdf"
    pdf.output(filename)
    return filename

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
