from pydantic import BaseModel


class CommitMessage(BaseModel):
    message: str
    details: list[str]
