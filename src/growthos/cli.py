import argparse
from datetime import date
from pathlib import Path
from .config import Config
from .context_builder import build_context
from .deepseek import ask_json, DeepSeekError
from .file_utils import atomic_write, read_json, read_text
from .knowledge import capability_concepts, curriculum, knowledge_map, record_result, recommended_next, select_concept
from .practice import analyze_daily
from .reviews import monthly_review, quarterly_question, quarterly_assessment

def _scores(answer: dict) -> tuple[int, int]:
    return int(answer["concept_score"]), int(answer["application_score"])

def study(root: Path, config: Config, capability: str | None, concept_id: str | None) -> None:
    concept = select_concept(root, capability, concept_id); context = build_context(root, concept["capability"])
    system = read_text(root / "prompts/teacher.md")
    questions = ask_json(config, system, f"Context:\n{context}\n\nConcept:\n{concept}\n\nAsk the two diagnostic questions now.", {"recall_question", "application_question"})
    print(f"\nRecall: {questions['recall_question']}"); recall = input("Your answer: ").strip()
    print(f"\nApplication: {questions['application_question']}"); application = input("Your answer: ").strip()
    answer = ask_json(config, system, f"Context:\n{context}\n\nConcept:\n{concept}\n\nRecall answer: {recall}\nApplication answer: {application}\n\nEvaluate, teach, and score now.", {"teaching", "concept_score", "application_score", "rationale"})
    print(f"\nTeacher feedback: {answer['teaching']}\nReasoning: {answer['rationale']}")
    c, a = _scores(answer); progress = record_result(root, concept, c, a)
    path = root / "logs/study" / f"{date.today().isoformat()}_{concept['id']}.md"
    atomic_write(path, f"# Study Session — {concept['title']}\n\n## Recall Question\n{questions['recall_question']}\n\n## User Recall Answer\n{recall}\n\n## Application Question\n{questions['application_question']}\n\n## User Application Answer\n{application}\n\n## Teacher Feedback\n{answer['teaching']}\n\n## Result\n{progress}\n")
    print(f"\nSaved {path}. Next review: {progress['next_review_at']}.")

def quiz(root: Path, config: Config) -> None:
    progress = read_json(root / "state/knowledge_progress.json", {}); due = [k for k,v in progress.items() if v.get("next_review_at", "9999") <= date.today().isoformat()]
    study(root, config, None, due[0] if due else None)

def choose_capability() -> str | None:
    options = [("Business", "商业理解"), ("Finance", "财务与经营数字"), ("Strategy", "战略与决策"), ("Execution", "执行与项目管理"), ("Leadership", "领导力"), ("Influence", "影响力")]
    print("请选择学习领域：\n")
    for i, (name, chinese) in enumerate(options, 1): print(f"{i}. {name} {chinese}")
    selected = input("输入编号或能力名称（q 退出）：").strip()
    if selected.lower() == "q": return None
    if selected.isdigit() and 1 <= int(selected) <= len(options): return options[int(selected)-1][0]
    return next((name for name, _ in options if name.lower() == selected.lower()), None)

def browse_study(root: Path, config: Config, capability: str) -> None:
    items = capability_concepts(root, capability); print(knowledge_map(root, capability))
    selected = input("\n输入知识点编号开始学习，输入 q 退出：").strip()
    if selected.lower() == "q" or not selected: return
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
            if args.capability == "next":
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
