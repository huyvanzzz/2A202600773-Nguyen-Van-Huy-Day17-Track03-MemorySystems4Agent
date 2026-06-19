from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


@dataclass
class BenchmarkRow:
    agent_name: str
    agent_tokens_only: int
    prompt_tokens_processed: int
    recall_score: float
    response_quality: float
    memory_growth_bytes: int
    compactions: int


def load_conversations(path: Path) -> list[dict[str, Any]]:
    """Student TODO: read JSON conversations from disk."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def recall_points(answer: str, expected: list[str]) -> float:
    """Student TODO: return 0 / 0.5 / 1 depending on how many expected facts appear."""
    if not expected:
        return 1.0
    ans_lower = answer.lower()
    found = 0
    for exp in expected:
        # Check for presence using word bounds/case-insensitive matching
        if exp.lower() in ans_lower:
            found += 1
    return round(found / len(expected), 2)


def heuristic_quality(answer: str, expected: list[str]) -> float:
    """Student TODO: add a lightweight quality score for offline mode."""
    if not answer or "không biết" in answer.lower() or "không tìm thấy" in answer.lower():
        return 0.20
        
    rec = recall_points(answer, expected)
    if rec > 0.8:
        return 0.95
    elif rec > 0.4:
        return 0.75
    return 0.50


def evaluate_quality_with_llm(judge_model, question: str, answer: str, expected: list[str]) -> float:
    """Evaluate answer quality using the LLM judge."""
    try:
        expected_str = ", ".join(expected)
        prompt = (
            "Bạn là giám khảo đánh giá chất lượng câu trả lời của AI Agent.\n"
            f"Câu hỏi: {question}\n"
            f"Câu trả lời của Agent: {answer}\n"
            f"Thông tin cần có (từ khóa): {expected_str}\n\n"
            "Hãy chấm điểm chất lượng từ 0.0 đến 1.0 (ví dụ: 0.85). Điểm số phụ thuộc vào độ chính xác của thông tin cần có, "
            "văn phong tự nhiên, ngắn gọn và mạch lạc. Chỉ trả về duy nhất điểm số dưới dạng số thực."
        )
        res = judge_model.invoke(prompt)
        score_match = re.search(r"[\d.]+", res.content.strip())
        if score_match:
            return float(score_match.group())
    except Exception:
        pass
    return heuristic_quality(answer, expected)


def run_agent_benchmark(agent_name: str, agent, conversations: list[dict[str, Any]], config) -> BenchmarkRow:
    """Student TODO: evaluate one agent over many conversations.

    Pseudocode:
    1. Feed all turns to the agent.
    2. Track `agent tokens only`.
    3. Track `prompt tokens processed`.
    4. Ask recall questions in a fresh thread.
    5. Compute average recall and quality.
    6. Record memory file growth and compaction count.
    """
    # Attempt to build the LLM judge if not offline
    judge_model = None
    if not agent.force_offline:
        try:
            from model_provider import build_chat_model
            judge_model = build_chat_model(config.judge_model)
        except Exception:
            pass

    total_agent_tokens = 0
    total_prompt_tokens = 0
    total_compactions = 0
    all_recalls = []
    all_qualities = []
    users_seen = set()

    for conv in conversations:
        user_id = conv["user_id"]
        users_seen.add(user_id)
        thread_id = conv["id"]
        
        # 1. Feed the conversational turns
        for turn in conv["turns"]:
            agent.reply(user_id, thread_id, turn)
            
        # 2. Ask recall questions in a fresh thread
        recall_thread_id = f"recall-{thread_id}"
        for q_item in conv["recall_questions"]:
            q_text = q_item["question"]
            expected = q_item["expected_contains"]
            
            res = agent.reply(user_id, recall_thread_id, q_text)
            ans_text = res["response"]
            
            # Score recall
            rec = recall_points(ans_text, expected)
            all_recalls.append(rec)
            
            # Score quality
            if judge_model is not None:
                qual = evaluate_quality_with_llm(judge_model, q_text, ans_text, expected)
            else:
                qual = heuristic_quality(ans_text, expected)
            all_qualities.append(qual)
            
        # Accumulate token metrics for both main thread and recall thread
        total_agent_tokens += agent.token_usage(thread_id) + agent.token_usage(recall_thread_id)
        total_prompt_tokens += agent.prompt_token_usage(thread_id) + agent.prompt_token_usage(recall_thread_id)
        total_compactions += agent.compaction_count(thread_id)

    # Estimate memory growth
    memory_growth = 0
    if hasattr(agent, "memory_file_size"):
        for uid in users_seen:
            memory_growth += agent.memory_file_size(uid)

    avg_recall = sum(all_recalls) / len(all_recalls) if all_recalls else 0.0
    avg_quality = sum(all_qualities) / len(all_qualities) if all_qualities else 0.0

    return BenchmarkRow(
        agent_name=agent_name,
        agent_tokens_only=total_agent_tokens,
        prompt_tokens_processed=total_prompt_tokens,
        recall_score=avg_recall,
        response_quality=avg_quality,
        memory_growth_bytes=memory_growth,
        compactions=total_compactions,
    )


def format_rows(rows: list[BenchmarkRow]) -> str:
    """Student TODO: print a markdown table or tabulated output."""
    from tabulate import tabulate
    headers = [
        "Agent Name",
        "Agent Tokens Only",
        "Prompt Tokens Processed",
        "Cross-Session Recall",
        "Response Quality",
        "Memory Growth (bytes)",
        "Compactions"
    ]
    data = []
    for r in rows:
        data.append([
            r.agent_name,
            r.agent_tokens_only,
            r.prompt_tokens_processed,
            f"{r.recall_score:.2%}",
            f"{r.response_quality:.2%}",
            r.memory_growth_bytes,
            r.compactions
        ])
    return tabulate(data, headers=headers, tablefmt="github")


def cleanup_profiles(config) -> None:
    profiles_dir = config.state_dir / "profiles"
    if profiles_dir.exists():
        shutil.rmtree(profiles_dir)
    profiles_dir.mkdir(parents=True, exist_ok=True)


def main() -> None:
    """Student TODO: run both benchmark suites.

    Required benchmark sections:
    - Standard benchmark from `data/conversations.json`
    - Long-context stress benchmark from `data/advanced_long_context.json`

    Compare:
    - Baseline
    - Advanced

    Keep the same output columns as the solved lab:
    - Agent tokens only
    - Prompt tokens processed
    - Cross-session recall
    - Response quality
    - Memory growth (bytes)
    - Compactions
    """
    config = load_config(Path(__file__).resolve().parent.parent)
    
    std_path = config.data_dir / "conversations.json"
    stress_path = config.data_dir / "advanced_long_context.json"
    
    conversations_std = load_conversations(std_path)
    conversations_stress = load_conversations(stress_path)

    # Run in online mode if API keys are configured and valid
    force_offline = True
    if config.model.api_key or config.model.provider == "ollama":
        force_offline = False

    print("=" * 70)
    print(f"RUNNING SUITE: {'ONLINE (Live LLM)' if not force_offline else 'OFFLINE (Deterministic)'}")
    print("=" * 70)

    # 1. Standard Benchmark
    print("\n--- Running Standard Benchmark (conversations.json) ---")
    
    cleanup_profiles(config)
    baseline_std = BaselineAgent(config=config, force_offline=force_offline)
    row_baseline_std = run_agent_benchmark("Baseline Agent", baseline_std, conversations_std, config)
    
    cleanup_profiles(config)
    advanced_std = AdvancedAgent(config=config, force_offline=force_offline)
    row_advanced_std = run_agent_benchmark("Advanced Agent", advanced_std, conversations_std, config)
    
    print("\n[Standard Benchmark Results]")
    print(format_rows([row_baseline_std, row_advanced_std]))

    # 2. Long-Context Stress Benchmark
    print("\n--- Running Long-Context Stress Benchmark (advanced_long_context.json) ---")
    
    cleanup_profiles(config)
    baseline_stress = BaselineAgent(config=config, force_offline=force_offline)
    row_baseline_stress = run_agent_benchmark("Baseline Agent", baseline_stress, conversations_stress, config)
    
    cleanup_profiles(config)
    advanced_stress = AdvancedAgent(config=config, force_offline=force_offline)
    row_advanced_stress = run_agent_benchmark("Advanced Agent", advanced_stress, conversations_stress, config)
    
    print("\n[Long-Context Stress Benchmark Results]")
    print(format_rows([row_baseline_stress, row_advanced_stress]))



if __name__ == "__main__":
    main()
