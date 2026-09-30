from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.llm import structured_call


class Ticket(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    email: str | None
    issue: str
    category: Literal["billing", "technical", "return", "other"]


text = """Hello my name is Kartik. Yesterday I broke up with my girlfriend.
I have an iPhone which is not working at all. My email is abc@gmail.com"""

ticket = structured_call(
    system_prompt="Extract support ticket details from the customer message.",
    user_prompt=f"<message>\n{text}\n</message>",
    output_model=Ticket,
    reasoning_effort="low",
)

print(ticket)
print(type(ticket))
print(ticket.category)
