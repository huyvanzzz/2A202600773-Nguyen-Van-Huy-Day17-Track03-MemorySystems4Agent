from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import LabConfig, load_config
from memory_store import estimate_tokens, extract_profile_updates
from model_provider import build_chat_model


@dataclass
class SessionState:
    messages: list[dict[str, str]] = field(default_factory=list)
    token_usage: int = 0
    prompt_tokens_processed: int = 0


class BaselineAgent:
    """Student TODO: implement Agent A.

    Requirements:
    - Within-session memory only
    - No persistent `User.md`
    - Should forget long-term facts across new threads
    """

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.sessions: dict[str, SessionState] = {}

        # TODO: optionally initialize a real LangChain/LangGraph agent when dependencies exist.
        self.langchain_agent = None

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: return the agent response and token accounting.

        Pseudocode:
        - If a live agent exists, call the live path.
        - Otherwise use a deterministic offline path.
        """
        self._maybe_build_langchain_agent()

        if self.langchain_agent is not None and not self.force_offline:
            try:
                if thread_id not in self.sessions:
                    self.sessions[thread_id] = SessionState()
                state = self.sessions[thread_id]

                # Append user message
                state.messages.append({"role": "user", "content": message})

                # Format messages for LangChain
                from langchain_core.messages import HumanMessage, AIMessage
                langchain_msgs = []
                for m in state.messages:
                    if m["role"] == "user":
                        langchain_msgs.append(HumanMessage(content=m["content"]))
                    else:
                        langchain_msgs.append(AIMessage(content=m["content"]))

                # Call LLM
                response_obj = self.langchain_agent.invoke(langchain_msgs)
                response_text = response_obj.content

                # Calculate tokens
                tokens_out = 0
                tokens_in = 0
                if hasattr(response_obj, "usage_metadata") and response_obj.usage_metadata:
                    tokens_out = response_obj.usage_metadata.get("output_tokens", 0)
                    tokens_in = response_obj.usage_metadata.get("input_tokens", 0)
                elif "token_usage" in response_obj.response_metadata:
                    usage = response_obj.response_metadata["token_usage"]
                    tokens_out = usage.get("completion_tokens", 0)
                    tokens_in = usage.get("prompt_tokens", 0)

                if tokens_out == 0:
                    tokens_out = estimate_tokens(response_text)
                if tokens_in == 0:
                    tokens_in = sum(estimate_tokens(m["content"]) for m in state.messages[:-1])

                state.token_usage += tokens_out
                state.prompt_tokens_processed += tokens_in
                state.messages.append({"role": "assistant", "content": response_text})

                return {
                    "response": response_text,
                    "tokens": tokens_out,
                    "prompt_tokens": tokens_in
                }
            except Exception:
                # Fallback to offline on failure
                pass

        return self._reply_offline(thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        # TODO: return cumulative agent token count for one thread.
        if thread_id not in self.sessions:
            return 0
        return self.sessions[thread_id].token_usage

    def prompt_token_usage(self, thread_id: str) -> int:
        # TODO: estimate how much prompt context this baseline kept processing.
        if thread_id not in self.sessions:
            return 0
        return self.sessions[thread_id].prompt_tokens_processed

    def compaction_count(self, thread_id: str) -> int:
        # Baseline has no compact memory.
        return 0

    def _reply_offline(self, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: implement a simple offline behavior.

        Suggested behavior:
        - Store the new user message in the session
        - Generate a short deterministic reply
        - Update token counts
        - Never remember facts across different thread ids
        """
        if thread_id not in self.sessions:
            self.sessions[thread_id] = SessionState()
        state = self.sessions[thread_id]

        state.messages.append({"role": "user", "content": message})
        prompt_tokens = sum(estimate_tokens(m["content"]) for m in state.messages[:-1])

        msg_lower = message.lower()
        response = "Tôi là Baseline Agent, chỉ ghi nhớ thông tin trong cùng cuộc hội thoại này."

        # Simple recall search
        has_question = "?" in message or any(q in msg_lower for q in [
            "là gì", "là ai", "ở đâu", "nuôi con gì", "nhắc lại", " style ", "tên mình"
        ])

        if has_question:
            found_name = None
            found_drink = None
            found_food = None
            found_pet = None
            found_loc = None
            found_job = None
            found_style = None

            for m in state.messages[:-1]:
                if m["role"] == "user":
                    text = m["content"]
                    updates = extract_profile_updates(text)
                    if "Tên" in updates:
                        found_name = updates["Tên"]
                    if "Đồ uống" in updates:
                        found_drink = updates["Đồ uống"]
                    if "Món ăn" in updates:
                        found_food = updates["Món ăn"]
                    if "Thú cưng" in updates:
                        found_pet = updates["Thú cưng"]
                    if "Nơi ở" in updates:
                        found_loc = updates["Nơi ở"]
                    if "Nghề nghiệp" in updates:
                        found_job = updates["Nghề nghiệp"]
                    if "Style trả lời" in updates:
                        found_style = updates["Style trả lời"]

            answers = []
            if "tên" in msg_lower or "ai" in msg_lower:
                if found_name:
                    answers.append(f"Bạn tên là {found_name}.")
                else:
                    answers.append("Tôi không biết bạn tên là gì.")

            if "đồ uống" in msg_lower or "uống" in msg_lower:
                if found_drink:
                    answers.append(f"Đồ uống yêu thích của bạn là {found_drink}.")
                else:
                    answers.append("Tôi không biết đồ uống yêu thích của bạn.")

            if "món ăn" in msg_lower or "ăn" in msg_lower:
                if found_food:
                    answers.append(f"Món ăn yêu thích của bạn là {found_food}.")
                else:
                    answers.append("Tôi không biết món ăn yêu thích của bạn.")

            if "nuôi" in msg_lower or "con gì" in msg_lower:
                if found_pet:
                    answers.append(f"Bạn nuôi {found_pet}.")
                else:
                    answers.append("Tôi không biết bạn nuôi con gì.")

            if "ở đâu" in msg_lower or "nơi ở" in msg_lower:
                if found_loc:
                    answers.append(f"Nơi ở hiện tại của bạn là ở {found_loc}.")
                else:
                    answers.append("Tôi không biết nơi ở hiện tại của bạn.")

            if "nghề" in msg_lower or "làm gì" in msg_lower:
                if found_job:
                    answers.append(f"Nghề nghiệp hiện tại của bạn là {found_job}.")
                else:
                    answers.append("Tôi không biết bạn làm nghề gì.")

            if "style" in msg_lower or "trả lời" in msg_lower:
                if found_style:
                    answers.append(f"Style trả lời bạn thích là {found_style}.")
                else:
                    answers.append("Tôi không biết style trả lời bạn thích.")

            if answers:
                response = " ".join(answers)
            else:
                response = "Tôi không tìm thấy thông tin này trong cuộc hội thoại hiện tại."
        else:
            response = "Tôi đã nhận thông tin. Tôi sẽ nhớ nó trong suốt cuộc trò chuyện này."

        response_tokens = estimate_tokens(response)

        state.token_usage += response_tokens
        state.prompt_tokens_processed += prompt_tokens
        state.messages.append({"role": "assistant", "content": response})

        return {
            "response": response,
            "tokens": response_tokens,
            "prompt_tokens": prompt_tokens
        }

    def _maybe_build_langchain_agent(self):
        """Student TODO: optionally wire `create_agent` + `InMemorySaver` here.

        Use `build_chat_model(self.config.model)` so the baseline can run with any supported provider.
        """
        if self.langchain_agent is not None or self.force_offline:
            return

        try:
            self.langchain_agent = build_chat_model(self.config.model)
        except Exception:
            self.langchain_agent = None

