from __future__ import annotations

from pathlib import Path

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


def make_config(tmp_path: Path):
    """Student TODO: build an isolated config for tests."""
    from model_provider import ProviderConfig
    from config import LabConfig
    
    model_cfg = ProviderConfig(
        provider="custom",
        model_name="mock-model",
        temperature=0.0,
    )
    return LabConfig(
        base_dir=tmp_path,
        data_dir=tmp_path / "data",
        state_dir=tmp_path / "state",
        compact_threshold_tokens=250,   # sensible threshold for tests
        compact_keep_messages=2,       # keep last 2 messages (1 user + 1 assistant)
        model=model_cfg,
        judge_model=model_cfg,
    )


def test_user_markdown_read_write_edit(tmp_path: Path) -> None:
    """Student TODO: verify `User.md` can be created, updated, and edited."""
    from memory_store import UserProfileStore
    
    store = UserProfileStore(tmp_path / "state" / "profiles")
    user_id = "test_user"
    
    # Test writing
    content = "# Profile\n- **Tên**: DũngCT"
    path = store.write_text(user_id, content)
    assert path.exists()
    assert store.read_text(user_id) == content
    assert store.file_size(user_id) > 0
    
    # Test editing
    store.edit_text(user_id, "DũngCT", "DũngCT Stress")
    assert "DũngCT Stress" in store.read_text(user_id)
    assert "DũngCT" not in store.read_text(user_id).replace("DũngCT Stress", "")


def test_compact_trigger(tmp_path: Path) -> None:
    """Student TODO: verify long threads trigger compaction."""
    cfg = make_config(tmp_path)
    agent = AdvancedAgent(config=cfg, force_offline=True)
    user_id = "user_test_compact"
    thread_id = "thread_compact"
    
    # Send a long message (~35 tokens)
    long_msg = "Đây là thông điệp rất dài nhằm mục đích tăng lượng token của phiên hội thoại để vượt ngưỡng nén."
    
    # First message should not trigger compaction
    agent.reply(user_id, thread_id, long_msg)
    assert agent.compaction_count(thread_id) == 0
    
    # Loop to send messages until compaction is triggered
    for _ in range(8):
        agent.reply(user_id, thread_id, long_msg)
        if agent.compaction_count(thread_id) > 0:
            break
            
    assert agent.compaction_count(thread_id) > 0


def test_cross_session_recall(tmp_path: Path) -> None:
    """Student TODO: verify advanced remembers across sessions and baseline does not."""
    cfg = make_config(tmp_path)
    baseline = BaselineAgent(config=cfg, force_offline=True)
    advanced = AdvancedAgent(config=cfg, force_offline=True)
    
    user_id = "dungct"
    
    # Thread 1: feed profile facts
    baseline.reply(user_id, "thread1", "Chào bạn, mình tên là DũngCT.")
    advanced.reply(user_id, "thread1", "Chào bạn, mình tên là DũngCT.")
    
    # Thread 2: ask recall question
    res_baseline = baseline.reply(user_id, "thread2", "Tên mình là gì?")
    res_advanced = advanced.reply(user_id, "thread2", "Tên mình là gì?")
    
    # Baseline has no cross-session memory
    assert "DũngCT" not in res_baseline["response"]
    # Advanced has cross-session memory from User.md
    assert "DũngCT" in res_advanced["response"]


def test_compact_reduces_prompt_load_on_long_thread(tmp_path: Path) -> None:
    """Student TODO: compare prompt load of baseline vs advanced on a long thread."""
    cfg = make_config(tmp_path)
    baseline = BaselineAgent(config=cfg, force_offline=True)
    advanced = AdvancedAgent(config=cfg, force_offline=True)
    
    user_id = "user_stress"
    thread_id = "thread_stress"
    
    # Send multiple messages to both agents (long thread)
    msg = "Thảo luận về cách thiết kế tên lửa hàng không vũ trụ hiện đại đạt hiệu năng đỉnh và giảm sonic boom."
    for _ in range(15):
        baseline.reply(user_id, thread_id, msg)
        advanced.reply(user_id, thread_id, msg)
        
    last_baseline_load = baseline.prompt_token_usage(thread_id)
    last_advanced_load = advanced.prompt_token_usage(thread_id)
    
    # Baseline load accumulates linearly/quadratically, while Advanced compacts the history
    assert last_advanced_load < last_baseline_load

