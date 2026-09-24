import argparse
from datetime import date
from pathlib import Path
from .config import Config
from .context_builder import build_context
from .deepseek import ask_json, DeepSeekError
from .file_utils import read_json, read_text
from .knowledge import calculate_progress_result, capability_concepts, curriculum, knowledge_map, recommended_next, select_concept
from .practice import analyze_daily
from .reviews import monthly_review, quarterly_question, quarterly_assessment
from .study_history import commit_session, find_session, is_exit_command, latest_valid_session, list_sessions, rebuild_all_progress, session_summary, set_validity

def _scores(answer: dict) -> tuple[int, int]:
    return int(answer["concept_score"]), int(answer["application_score"])

def _cancel_study() -> None:
    print("本次学习已取消。\n不会保存本次回答，也不会更新Knowledge Progress。")

def study(root: Path, config: Config, capability: str | None, concept_id: str | None) -> None:
    try:
        concept = select_concept(root, capability, concept_id); context = build_context(root, concept["capability"])
        system = read_text(root / "prompts/teacher.md")
        questions = ask_json(config, system, f"Context:\n{context}\n\nConcept:\n{concept}\n\nAsk the two diagnostic questions now.", {"recall_question", "application_question"})
        print(f"\nRecall: {questions['recall_question']}"); recall = input("Your answer: ").strip()
        if is_exit_command(recall): return _cancel_study()
        print(f"\nApplication: {questions['application_question']}"); application = input("Your answer: ").strip()
        if is_exit_command(application): return _cancel_study()
        answer = ask_json(config, system, f"Context:\n{context}\n\nConcept:\n{concept}\n\nRecall answer: {recall}\nApplication answer: {application}\n\nEvaluate, teach, and score now.", {"teaching", "concept_score", "application_score", "rationale"})
        c, a = _scores(answer); prior = read_json(root / "state/knowledge_progress.json", {}).get(concept["id"], {})
        result = calculate_progress_result(prior, concept, c, a)
        print(f"\nConcept Score: {c}\nApplication Score: {a}\nStatus: {result['status']}\nNext Review: {result['next_review_at']}\nAI Feedback: {answer['teaching']}\nReasoning: {answer['rationale']}")
        decision = input("\n保存本次学习结果？ [Y/n] ").strip()
        if is_exit_command(decision) or decision.casefold() in {"n", "no"}: return _cancel_study()
        if decision and decision.casefold() not in {"y", "yes"}:
            print("无法识别确认输入，本次结果未保存。"); return _cancel_study()
        path = commit_session(root, concept, questions, recall, application, answer, result)
        print(f"\nSaved {path}. Next review: {result['next_review_at']}.")
    except (KeyboardInterrupt, EOFError):
        print(); _cancel_study()

def quiz(root: Path, config: Config) -> None:
    progress = read_json(root / "state/knowledge_progress.json", {}); due = [k for k,v in progress.items() if v.get("next_review_at", "9999") <= date.today().isoformat()]
    study(root, config, None, due[0] if due else None)

def show_history(root: Path, capability: str | None = None) -> None:
    sessions = list_sessions(root, capability)
    if not sessions: print("没有 Study Session 记录。"); return
    for index, record in enumerate(sessions, 1):
        print(f"{index:02d} {record['metadata']['id']}  {session_summary(record)}")

def show_session(root: Path, session_id: str) -> None:
    print(find_session(root, session_id)["path"].read_text(encoding="utf-8"))

def invalidate_session(root: Path, session_id: str) -> None:
    record = find_session(root, session_id); print(session_summary(record))
    if not record["metadata"]["valid"]: print("该记录已经是 Invalid。"); return
    if input("确认将该学习记录标记为无效？ [y/N] ").strip().casefold() not in {"y", "yes"}: print("未作修改。"); return
    reason = input("作废原因（可留空）：").strip()
    set_validity(root, session_id, False, reason)
    print("记录已标记为 Invalid，Knowledge Progress 已重新计算。")

def restore_session(root: Path, session_id: str) -> None:
    record = find_session(root, session_id); print(session_summary(record))
    if record["metadata"]["valid"]: print("该记录已经是 Valid。"); return
    set_validity(root, session_id, True)
    print("记录已恢复为 Valid，Knowledge Progress 已重新计算。")

def undo_latest(root: Path) -> None:
    record = latest_valid_session(root); print(session_summary(record))
    if input("撤销这次学习记录？ [y/N] ").strip().casefold() not in {"y", "yes"}: print("未作修改。"); return
    set_validity(root, record["metadata"]["id"], False, "study undo")
    print("最近一次有效 Study Session 已标记为 Invalid，Knowledge Progress 已回滚。")

def handle_study_admin(root: Path, action: str, argument: str | None) -> bool:
    if action == "history": show_history(root, argument)
    elif action == "show":
        if not argument: raise ValueError("Usage: growthos study show <id>")
        show_session(root, argument)
    elif action == "invalidate":
        if not argument: raise ValueError("Usage: growthos study invalidate <id>")
        invalidate_session(root, argument)
    elif action == "restore":
        if not argument: raise ValueError("Usage: growthos study restore <id>")
        restore_session(root, argument)
    elif action == "undo": undo_latest(root)
    elif action == "rebuild":
        progress = rebuild_all_progress(root); print(f"已从有效 Study History 重建 {len(progress)} 个 Concept Progress。")
    else: return False
    return True

def choose_capability() -> str | None:
    options = [("Business", "商业理解"), ("Finance", "财务与经营数字"), ("Strategy", "战略与决策"), ("Execution", "执行与项目管理"), ("Leadership", "领导力"), ("Influence", "影响力")]
    print("请选择学习领域：\n")
    for i, (name, chinese) in enumerate(options, 1): print(f"{i}. {name} {chinese}")
    selected = input("输入编号或能力名称（q 退出）：").strip()
    if is_exit_command(selected): return None
    if selected.isdigit() and 1 <= int(selected) <= len(options): return options[int(selected)-1][0]
    return next((name for name, _ in options if name.lower() == selected.lower()), None)

def browse_study(root: Path, config: Config, capability: str) -> None:
    items = capability_concepts(root, capability); print(knowledge_map(root, capability))
    selected = input("\n输入知识点编号开始学习，输入 q 退出：").strip()
    if is_exit_command(selected) or not selected: return
    if not selected.isdigit() or not 1 <= int(selected) <= len(items): raise ValueError("请输入知识地图中的有效编号。")
    study(root, config, capability, items[int(selected)-1]["id"])

def topics(root: Path, capability: str | None) -> None:
    if capability: print(knowledge_map(root, capability)); return
    all_items = curriculum(root); print("Executive Growth OS Knowledge Map\n")
    for name in ("Business", "Finance", "Strategy", "Execution", "Leadership", "Influence"):
        print(f"{name:<14} {len([c for c in all_items if c['capability'] == name])} concepts")
    print(f"\nTotal          {len(all_items)} concepts")

def learning_path(root: Path, capability: str) -> None:
    items = capability_concepts(root, capability)
    print(f"{items[0]['capability']} Learning Path\n")
    print(knowledge_map(root, capability))

def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="growthos"); sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status"); p_study = sub.add_parser("study"); p_study.add_argument("capability", nargs="?"); p_study.add_argument("concept", nargs="?")
    p_topics = sub.add_parser("topics"); p_topics.add_argument("capability", nargs="?")
    sub.add_parser("quiz"); sub.add_parser("daily"); sub.add_parser("reflect"); p_review = sub.add_parser("review"); p_review.add_argument("period", choices=["monthly", "quarterly"])
    args = parser.parse_args(); root = Path.cwd(); config = Config.load(root)
    try:
        if args.command == "status":
            print(read_text(root / "state/current_state.md")); print(f"\nCurriculum concepts: {len(curriculum(root))}")
        elif args.command == "topics": topics(root, args.capability)
        elif args.command == "study":
            if args.capability in {"history", "show", "invalidate", "restore", "undo", "rebuild"}:
                handle_study_admin(root, args.capability, args.concept)
            elif args.capability == "next":
                concept, reason = recommended_next(root); print(f"推荐学习：\n\n{concept['capability']} → {concept['title']}\n{concept['title_zh']}\n\n推荐原因：\n{reason}")
                if input("\n开始学习？ [Y/n] ").strip().lower() not in ("n", "no"): study(root, config, concept["capability"], concept["id"])
            elif args.capability == "path":
                if not args.concept: raise ValueError("Usage: growthos study path <capability>")
                learning_path(root, args.concept)
            elif args.capability is None:
                selected = choose_capability()
                if selected: browse_study(root, config, selected)
            elif args.concept is None: browse_study(root, config, args.capability)
            else: study(root, config, args.capability, args.concept)
        elif args.command == "quiz": quiz(root, config)
        elif args.command in ("daily", "reflect"):
            raw = input("Describe today's real work experience:\n").strip()
            if raw:
                path, evidence = analyze_daily(root, config, raw, build_context(root)); print(f"Saved {path}; evidence files: {len(evidence)}")
        elif args.period == "monthly": print(f"Saved {monthly_review(root, config)}")
        else:
            transcript = []; question = quarterly_question(root, config)
            for turn in range(3):
                print(f"\nInterviewer: {question['question']}"); transcript.append(("Question", question["question"]))
                reply = input("Your answer: ").strip(); transcript.append(("User Answer", reply))
                question = quarterly_question(root, config)
            print(f"Saved {quarterly_assessment(root, config, transcript)}")
    except (ValueError, DeepSeekError) as exc:
        parser.error(str(exc))
