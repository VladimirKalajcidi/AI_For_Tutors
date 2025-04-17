import openai
import config

# Configure OpenAI API key
openai.api_key = config.OPENAI_API_KEY

async def generate_study_plan(student, language="en"):
    # Build prompt using student info
    subject_name = student.subject.name if student.subject else "the subject"
    profile_info = student.profile or ""
    if language == "ru":
        prompt = f"Составь подробный учебный план по предмету {subject_name} для ученика. "
        if profile_info:
            prompt += f"Исходные данные об ученике: {profile_info}. "
        prompt += "Распредели темы по занятиям и укажи цели каждого этапа."
    else:
        prompt = f"Create a detailed study plan for {subject_name} for a student. "
        if profile_info:
            prompt += f"Student info: {profile_info}. "
        prompt += "Outline topics by session and state the objectives for each stage."
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024
        )
        plan_text = response.choices[0].message.content.strip()
    except Exception as e:
        res = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024
        )
        plan_text = res["choices"][0]["message"]["content"].strip()
    return plan_text

async def generate_assignment(student, topic=None, num_questions=5, language="en"):
    subject_name = student.subject.name if student.subject else ""
    if language == "ru":
        prompt = f"Составь {num_questions} задач по теме {topic or subject_name} для ученика. Сначала перечисли вопросы, затем предоставь ответы."
    else:
        prompt = f"Create {num_questions} practice questions for the topic {topic or subject_name}. Provide the questions first, then the answers."
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024
        )
        content = response.choices[0].message.content.strip()
    except Exception as e:
        res = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024
        )
        content = res["choices"][0]["message"]["content"].strip()
    # Split response into questions and answers if possible
    parts = content.split("\n\n")
    if len(parts) >= 2:
        questions = parts[0]
        answers = "\n\n".join(parts[1:])
    else:
        questions = content
        answers = ""
    return questions, answers
