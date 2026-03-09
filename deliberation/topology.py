from .models import Message


class FlatTopology:
    """All delegates see all messages from all previous rounds."""

    def visible_messages(
        self, delegate_id: str, all_messages: list[Message]
    ) -> list[Message]:
        return all_messages
