from notice_facts import facts_for, notice_codes
from src.model_client import ModelClient

SYSTEM = (
    "You answer questions about grocery recall notices for a help desk. Use only the notice records given. "
    "Answer in at most 80 words."
)

llm = ModelClient(num_predict=200)


def relevant_lessons(question, lessons):
    words = question.lower()
    return [lesson for lesson in lessons if any(k in words for k in lesson["keywords"])]


def answer(question, lessons=(), previous=None, feedback=None, with_record=True):
    records = facts_for(notice_codes(question)) if with_record else ""
    content = f"Question: {question}\n\nNotice records:\n{records or 'none given'}"
    if lessons:
        content += "\n\nLessons from earlier mistakes:\n" + "\n".join(f"- {lesson['correction']}" for lesson in lessons)
    if feedback:
        content += f"\n\nYour previous answer:\n{previous}\n\nEvaluator feedback:\n{feedback}\n\nWrite a corrected answer."
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]
    return llm.complete(messages).text
