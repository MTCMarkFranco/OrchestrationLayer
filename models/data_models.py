from typing import List
from dataclasses import dataclass

@dataclass
class Record:
    publisheddate: str
    filename: str
    summary: str

@dataclass
class AssistantAction:
    records: List[Record]
    question: str

@dataclass
class Action:
    action: str