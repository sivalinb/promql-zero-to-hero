from pathlib import Path
from functools import lru_cache
import json
from pydantic import BaseModel, Field, model_validator

ROOT = Path(__file__).resolve().parents[1]
CURRICULUM_VERSION = "foundations-v2"


class Question(BaseModel):
    id: str
    prompt: str
    options: list[str] = Field(min_length=3, max_length=5)
    answer: int = Field(ge=0)
    explanation: str
    concept: str

    @model_validator(mode="after")
    def valid_answer(self):
        if self.answer >= len(self.options):
            raise ValueError("Answer must refer to an option")
        return self


class Lesson(BaseModel):
    id: str
    title: str
    definition: str
    analogy: str
    body: str
    sql_connection: str
    animation: dict
    check: Question
    terms: list[str]
    remember: str
    promql: str = ""


class Level(BaseModel):
    id: int = Field(ge=0, le=10)
    title: str
    subtitle: str
    badge: str
    icon: str
    minutes: int
    stage: str
    lessons: list[Lesson] = Field(min_length=2)
    takeaways: list[str]
    pitfalls: list[str]
    promql: str
    sql: str
    equivalence: str
    lab: str
    lab_query: str
    lab_hint: str
    sources: list[str]
    questions: list[Question] = Field(min_length=6)
    animation: dict = Field(default_factory=dict)


@lru_cache
def curriculum() -> tuple[Level, ...]:
    data = json.loads((ROOT / "content/curriculum.json").read_text())
    levels = tuple(Level.model_validate(item) for item in data)
    if [x.id for x in levels] != list(range(11)):
        raise ValueError("Curriculum must contain exactly levels 0 through 10")
    ids = [q.id for level in levels for q in level.questions]
    if len(ids) != len(set(ids)):
        raise ValueError("Question identifiers must be unique")
    lesson_ids = [lesson.id for level in levels for lesson in level.lessons]
    if len(lesson_ids) != len(set(lesson_ids)):
        raise ValueError("Lesson identifiers must be unique")
    return levels


@lru_cache
def glossary() -> dict:
    return json.loads((ROOT / "content/glossary.json").read_text())
