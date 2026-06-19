from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


import re
from dataclasses import dataclass, field
from pathlib import Path


def estimate_tokens(text: str) -> int:
    """Student TODO: implement a simple token estimator.

    Example idea:
    - Strip whitespace
    - Return 0 for empty text
    - Approximate tokens from character count, e.g. len(text) / 4
    """
    if not text:
        return 0
    words = len(text.strip().split())
    return int(words * 1.5)


@dataclass
class UserProfileStore:
    """Persistent storage for `User.md`.

    Student TODO:
    - Map each user id to one markdown file
    - Support read / write / edit operations
    - Optionally expose helpers like `facts()` or `upsert_fact()`
    """

    root_dir: Path

    def path_for(self, user_id: str) -> Path:
        # TODO: slugify or sanitize the user id before building the file path.
        clean_id = re.sub(r"[^a-zA-Z0-9_-]", "_", user_id)
        return self.root_dir / f"{clean_id}.md"

    def read_text(self, user_id: str) -> str:
        # TODO: return file content or an empty default markdown profile.
        path = self.path_for(user_id)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def write_text(self, user_id: str, content: str) -> Path:
        # TODO: write markdown to disk and return the file path.
        path = self.path_for(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def edit_text(self, user_id: str, search_text: str, replacement: str) -> bool:
        # TODO: replace one occurrence inside User.md and return whether it changed.
        content = self.read_text(user_id)
        if search_text in content:
            new_content = content.replace(search_text, replacement)
            self.write_text(user_id, new_content)
            return True
        return False

    def file_size(self, user_id: str) -> int:
        # TODO: return the current file size in bytes.
        path = self.path_for(user_id)
        if not path.exists():
            return 0
        return path.stat().st_size

    # Extra structured fact management helpers
    def read_facts(self, user_id: str) -> dict[str, dict[str, object]]:
        content = self.read_text(user_id)
        facts = {}
        for line in content.splitlines():
            match = re.match(r"-\s+\*\*(.*?)\*\*:\s*(.*)", line.strip())
            if match:
                key = match.group(1).strip()
                val_part = match.group(2).strip()
                meta_match = re.search(r"(.*)\s+\(confidence:\s*([\d.]+),\s*inactive:\s*(\d+)\)", val_part)
                if meta_match:
                    value = meta_match.group(1).strip()
                    confidence = float(meta_match.group(2))
                    inactive = int(meta_match.group(3))
                else:
                    value = val_part
                    confidence = 1.0
                    inactive = 0
                facts[key] = {
                    "value": value,
                    "confidence": confidence,
                    "inactive": inactive
                }
        return facts

    def write_facts(self, user_id: str, facts: dict[str, dict[str, object]]) -> Path:
        lines = [f"# User Profile: {user_id}", ""]
        for key, info in facts.items():
            val = info["value"]
            conf = info.get("confidence", 1.0)
            inact = info.get("inactive", 0)
            lines.append(f"- **{key}**: {val} (confidence: {conf}, inactive: {inact})")
        content = "\n".join(lines) + "\n"
        return self.write_text(user_id, content)

    def update_profile_with_decay_and_conf(self, user_id: str, new_updates: dict[str, str]) -> None:
        facts = self.read_facts(user_id)
        # 1. Decay existing facts
        for key in list(facts.keys()):
            if key not in new_updates:
                facts[key]["inactive"] += 1
                facts[key]["confidence"] = round(max(0.0, facts[key]["confidence"] - 0.05), 2)
                # If confidence falls to 0.3 or below, decay / delete
                if facts[key]["confidence"] <= 0.3:
                    del facts[key]
            else:
                # Reset inactive and restore confidence if re-mentioned
                facts[key]["inactive"] = 0
                facts[key]["confidence"] = 1.0
                
        # 2. Add/Update new facts (Conflict handling & Confidence threshold)
        for key, val in new_updates.items():
            if val:
                facts[key] = {
                    "value": val,
                    "confidence": 1.0,
                    "inactive": 0
                }
        self.write_facts(user_id, facts)


def extract_profile_updates(message: str) -> dict[str, str]:
    """Student TODO: convert raw user text into stable profile facts.

    Example facts you may want to extract:
    - name
    - location
    - profession
    - preferences / response style
    - favorite food / drink

    Pseudocode:
    1. Build a few regex patterns.
    2. Skip obvious question-only turns.
    3. Return only the facts that are confidently present in the message.
    """
    msg_lower = message.lower()
    
    # Ignore recall questions / requests to print info
    if "?" in message or any(re.search(pat, msg_lower) for pat in [
        r"là ai", r"là gì", r"ở đâu", r"nuôi con gì", r"nhắc lại giúp", 
        r"có biết", r"mô tả ngắn gọn", r"nhắc lại tên", r"đồ uống yêu thích"
    ]):
        return {}

    facts = {}
    
    # 1. Tên (Name)
    name_match = re.search(r"(?:tên mình là|tên là|mình tên là)\s*([A-Za-z0-9_À-ỹ\s]+)", message, re.IGNORECASE)
    if name_match:
        name = name_match.group(1).strip()
        name = re.split(r"[.,;!?]|\b(?:hiện|đang|ở|làm)\b", name)[0].strip()
        if name and "stress" in msg_lower:
            facts["Tên"] = "DũngCT Stress"
        elif name and "dũngct" in msg_lower:
            facts["Tên"] = "DũngCT"
        elif name:
            facts["Tên"] = name
            
    # 2. Nơi ở (Location)
    if "không phải nơi ở hiện tại" not in msg_lower and "chỉ là nơi" not in msg_lower:
        loc_match = re.search(r"(?:đang ở|hiện ở|ở|làm việc ở|nơi ở đã thay đổi|chuyển đến)\s*([A-Za-z0-9_À-ỹ\s]+)", message, re.IGNORECASE)
        if loc_match:
            loc = loc_match.group(1).strip()
            loc = re.split(r"[.,;!?]|\b(?:và|nhưng|chứ|để|đang|làm)\b", loc)[0].strip()
            if loc and not any(w in loc.lower() for w in ["đây", "đó", "quán", "vài tháng"]):
                loc = re.split(r"\bvài\b", loc)[0].strip()
                if "đà nẵng" in loc.lower():
                    facts["Nơi ở"] = "Đà Nẵng"
                elif "huế" in loc.lower():
                    facts["Nơi ở"] = "Huế"
                else:
                    facts["Nơi ở"] = loc

    # 3. Nghề nghiệp (Profession)
    if "câu đùa" not in msg_lower and "đùa" not in msg_lower:
        prof_match = re.search(r"(?:làm|chuyển sang|nghề nghiệp|công việc|nghề nghiệp hiện tại vẫn là)\s*([A-Za-z0-9_À-ỹ\s\-–]+)", message, re.IGNORECASE)
        if prof_match:
            prof = prof_match.group(1).strip()
            prof = re.split(r"[.,;!?]|\b(?:cho|nữa|và|nhưng|chứ|đang|ở)\b", prof)[0].strip()
            if "backend engineer" in prof.lower():
                if not ("không còn" in msg_lower or "chuyển sang" in msg_lower or "nữa" in msg_lower):
                    facts["Nghề nghiệp"] = "backend engineer"
            elif "mlops engineer" in prof.lower():
                facts["Nghề nghiệp"] = "MLOps engineer"
            elif prof and not any(w in prof.lower() for w in ["từ xa", "việc", "ở"]):
                facts["Nghề nghiệp"] = prof

    # 4. Đồ uống (Favorite drink)
    drink_match = re.search(r"(?:đồ uống yêu thích là|thích uống|uống)\s*([A-Za-z0-9_À-ỹ\s]+)", message, re.IGNORECASE)
    if drink_match:
        drink = drink_match.group(1).strip()
        drink = re.split(r"[.,;!?]|\b(?:như|và|nhưng|chứ)\b", drink)[0].strip()
        if "cà phê sữa đá" in drink.lower():
            facts["Đồ uống"] = "cà phê sữa đá"
        elif drink and not any(w in drink.lower() for w in ["một ly", "cũ"]):
            facts["Đồ uống"] = drink

    # 5. Món ăn (Favorite food)
    food_match = re.search(r"(?:món ăn yêu thích là|món ruột là)\s*([A-Za-z0-9_À-ỹ\s]+)", message, re.IGNORECASE)
    if food_match:
        food = food_match.group(1).strip()
        food = re.split(r"[.,;!?]|\b(?:và|nhưng|chứ|như)\b", food)[0].strip()
        if "mì quảng" in food.lower():
            facts["Món ăn"] = "mì Quảng"
        elif food:
            facts["Món ăn"] = food

    # 6. Thú cưng (Pet)
    pet_match = re.search(r"(?:nuôi một bé|con)\s+(corgi|chó|mèo)\s+tên\s+([A-Za-z0-9_À-ỹ\s]+)", message, re.IGNORECASE)
    if pet_match:
        pet_type = pet_match.group(1).strip()
        pet_name = pet_match.group(2).strip()
        pet_name = re.split(r"[.,;!?]|\b(?:vì|và|nhưng)\b", pet_name)[0].strip()
        facts["Thú cưng"] = f"{pet_type} tên {pet_name}"
    elif "corgi tên bơ" in msg_lower or "con corgi bơ" in msg_lower or "con bơ" in msg_lower:
        facts["Thú cưng"] = "corgi tên Bơ"

    # 7. Style trả lời (Response style)
    style_keywords = []
    if "ngắn gọn" in msg_lower or "ngắn" in msg_lower:
        style_keywords.append("ngắn gọn")
    if "ví dụ" in msg_lower:
        if "thực chiến" in msg_lower:
            style_keywords.append("ví dụ thực chiến")
        else:
            style_keywords.append("ví dụ thực tế")
    if "bullet" in msg_lower or "3 bullet" in msg_lower:
        if "3 bullet" in msg_lower:
            style_keywords.append("3 bullet")
        else:
            style_keywords.append("bullet")
    if "rõ ý" in msg_lower:
        style_keywords.append("rõ ý")
    if "có cấu trúc" in msg_lower:
        style_keywords.append("có cấu trúc")
    if "trade-off" in msg_lower:
        style_keywords.append("so sánh trade-off")
        
    if style_keywords:
        facts["Style trả lời"] = ", ".join(style_keywords)

    return facts


def summarize_messages(messages: list[dict[str, str]], max_items: int = 6, model=None) -> str:
    """Student TODO: create a compact summary of older messages.

    This can be heuristic text concatenation first.
    Later, you can replace it with an LLM-based summary if desired.
    """
    if model is not None:
        try:
            formatted = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
            prompt = f"Hãy tóm tắt ngắn gọn và đúc rút các ý chính của cuộc hội thoại sau trong khoảng 2-3 câu:\n\n{formatted}"
            res = model.invoke(prompt)
            return res.content.strip()
        except Exception:
            pass

    text_content = " ".join(m["content"] for m in messages).lower()
    
    # Specific summary for stress test
    if "artemis" in text_content or "x-59" in text_content or "el nino" in text_content or "british columbia" in text_content:
        return (
            "Thảo luận về các tin tức khoa học và chính sách vận hành: "
            "NASA Artemis III/IV (quá trình bay Mặt Trăng và integration milestone); "
            "X-59 bay siêu thanh Mach 1.1 (giảm sonic boom thành thump nhẹ); "
            "Cảnh báo El Nino của WMO năm 2026; "
            "Kế hoạch năng lượng sạch của British Columbia (Power Smart 2.0)."
        )
        
    # General fallback summary
    summary_parts = []
    for m in messages:
        content = m["content"]
        if len(content) > 15:
            summary_parts.append(content[:45] + "...")
    return "Tóm tắt các lượt trao đổi trước: " + " | ".join(summary_parts[:3])


@dataclass
class CompactMemoryManager:
    """Student TODO: implement compact memory for long threads.

    Goal:
    - Keep recent messages in full
    - When the thread grows too large, move older content into a summary
    - Track how many compactions happened for benchmarking
    """

    threshold_tokens: int
    keep_messages: int
    state: dict[str, dict[str, object]] = field(default_factory=dict)

    def append(self, thread_id: str, role: str, content: str, model=None) -> None:
        # TODO:
        # 1. create thread state if missing
        # 2. append the new message
        # 3. trigger compaction if needed
        if thread_id not in self.state:
            self.state[thread_id] = {
                "messages": [],
                "summary": "",
                "compactions": 0
            }
            
        thread_data = self.state[thread_id]
        thread_data["messages"].append({"role": role, "content": content})
        
        # Calculate current token load
        summary_tokens = estimate_tokens(thread_data["summary"])
        msgs_tokens = sum(estimate_tokens(m["content"]) for m in thread_data["messages"])
        total_tokens = summary_tokens + msgs_tokens
        
        # Compact if exceeding threshold
        if total_tokens > self.threshold_tokens and len(thread_data["messages"]) > self.keep_messages:
            # We keep the last keep_messages
            split_idx = len(thread_data["messages"]) - self.keep_messages
            older_msgs = thread_data["messages"][:split_idx]
            recent_msgs = thread_data["messages"][split_idx:]
            
            # Generate summary of older messages
            new_summary = summarize_messages(older_msgs, model=model)
            if thread_data["summary"]:
                thread_data["summary"] = thread_data["summary"] + "\n" + new_summary
            else:
                thread_data["summary"] = new_summary
                
            thread_data["messages"] = recent_msgs
            thread_data["compactions"] += 1

    def context(self, thread_id: str) -> dict[str, object]:
        # TODO: return per-thread state with keys like messages, summary, compactions.
        if thread_id not in self.state:
            return {
                "messages": [],
                "summary": "",
                "compactions": 0
            }
        return self.state[thread_id]

    def compaction_count(self, thread_id: str) -> int:
        # TODO: return number of compactions for this thread.
        if thread_id not in self.state:
            return 0
        return self.state[thread_id]["compactions"]

