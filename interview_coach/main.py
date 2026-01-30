#!/usr/bin/env python3
"""Main entry point for Interview Coach CLI."""

from .schemas import CandidateProfile
from .graph import InterviewSession


def print_banner():
    """Print the application banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║           🎯 Multi-Agent Interview Coach System 🎯            ║
║                                                               ║
║  Система технического интервью с AI-агентами                  ║
║  - Observer: анализирует ответы (скрытая рефлексия)           ║
║  - Interviewer: ведёт диалог                                  ║
║  - HiringManager: генерирует финальный отчёт                  ║
╚═══════════════════════════════════════════════════════════════╝
""")


def get_candidate_info() -> CandidateProfile:
    """Get candidate information interactively.
    
    Returns:
        CandidateProfile with user input
    """
    print("\n📋 Введите данные кандидата:\n")
    
    name = input("Имя: ").strip()
    if not name:
        name = "Кандидат"
    
    print("\nДоступные позиции:")
    print("  1. Backend Developer")
    print("  2. ML Engineer")
    print("  3. Frontend Developer")
    role_choice = input("Выберите позицию (1-3) [1]: ").strip()
    
    role_map = {
        "1": "Backend Developer",
        "2": "ML Engineer", 
        "3": "Frontend Developer",
        "": "Backend Developer"
    }
    role = role_map.get(role_choice, "Backend Developer")
    
    print("\nУровень:")
    print("  1. Junior")
    print("  2. Middle")
    print("  3. Senior")
    grade_choice = input("Выберите уровень (1-3) [1]: ").strip()
    
    grade_map = {
        "1": "Junior",
        "2": "Middle",
        "3": "Senior",
        "": "Junior"
    }
    grade = grade_map.get(grade_choice, "Junior")
    
    experience = input("\nОпишите кратко опыт (или Enter для пропуска): ").strip()
    if not experience:
        experience = "Не указан"
    
    return CandidateProfile(
        name=name,
        role=role,
        grade_target=grade,
        experience=experience
    )


def run_interview(
    profile: CandidateProfile, 
    output_path: str = None,
    use_hybrid_observer: bool = True
):
    """Run an interactive interview session.
    
    Args:
        profile: Candidate profile
        output_path: Path for the output log file (auto-generates if None)
        use_hybrid_observer: If True, use the hybrid Observer pipeline (default)
    """
    print(f"\n{'='*60}")
    print(f"🎤 Начинаем интервью")
    print(f"   Кандидат: {profile.name}")
    print(f"   Позиция: {profile.role} ({profile.grade_target})")
    if use_hybrid_observer:
        print(f"   Observer: Hybrid Pipeline (parallel steps)")
    print(f"{'='*60}")
    print("\n💡 Подсказки:")
    print("   - Отвечайте на вопросы интервьюера")
    print("   - Можете задавать встречные вопросы")
    print("   - Для завершения напишите 'стоп' или 'стоп игра'")
    print(f"{'='*60}\n")
    
    # Initialize session
    session = InterviewSession(profile, use_hybrid_observer=use_hybrid_observer)
    
    # First message - greeting from candidate
    print("👤 Вы: ", end="")
    user_input = input().strip()
    
    if not user_input:
        user_input = f"Привет! Меня зовут {profile.name}."
        print(f"   (использован ввод по умолчанию: {user_input})")
    
    while True:
        try:
            # Process the message
            print("\n⏳ Интервьюер думает...")
            response = session.process_message(user_input)
            
            # Display the response
            print(f"\n🤖 Интервьюер:\n{response}\n")
            
            # Check if interview is finished
            if session.is_finished():
                print(f"\n{'='*60}")
                print("📊 Интервью завершено. Генерирую отчёт...")
                print(f"{'='*60}\n")
                
                # Display final feedback
                feedback = session.get_final_feedback()
                if feedback:
                    print("📝 ФИНАЛЬНЫЙ ОТЧЁТ:\n")
                    print(feedback)
                
                # Save the log
                log_path = session.save_log(output_path)
                print(f"\n✅ Лог сохранён в: {log_path}")
                break
            
            # Get next input
            print("👤 Вы: ", end="")
            user_input = input().strip()
            
            if not user_input:
                print("   (пустой ввод, введите ваш ответ)")
                continue
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Интервью прервано пользователем.")
            # Save partial log (will auto-generate path if output_path is None)
            log_path = session.save_log(output_path)
            print(f"   Частичный лог сохранён в: {log_path}")
            break
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            print("   Попробуйте ещё раз или завершите интервью командой 'стоп'")
            print("👤 Вы: ", end="")
            user_input = input().strip()


def run_scripted_interview(
    profile: CandidateProfile, 
    messages: list[str],
    output_path: str = None,
    verbose: bool = True,
    use_hybrid_observer: bool = True
):
    """Run an interview with pre-scripted messages (for testing).
    
    Args:
        profile: Candidate profile
        messages: List of candidate messages to send
        output_path: Path for the output log file (auto-generates if None)
        verbose: Whether to print the conversation
        use_hybrid_observer: If True, use the hybrid Observer pipeline (default)
    """
    session = InterviewSession(profile, use_hybrid_observer=use_hybrid_observer)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"🎤 Скриптовое интервью: {profile.name}")
        print(f"   Позиция: {profile.role} ({profile.grade_target})")
        if use_hybrid_observer:
            print(f"   Observer: Hybrid Pipeline (parallel steps)")
        print(f"{'='*60}\n")
    
    for i, message in enumerate(messages):
        if verbose:
            print(f"\n👤 [{i+1}] Кандидат: {message}")
        
        response = session.process_message(message)
        
        if verbose:
            print(f"\n🤖 Интервьюер: {response}")
        
        if session.is_finished():
            break
    
    # Get final feedback
    feedback = session.get_final_feedback()
    if verbose and feedback:
        print(f"\n{'='*60}")
        print("📝 ФИНАЛЬНЫЙ ОТЧЁТ:")
        print(f"{'='*60}\n")
        print(feedback)
    
    # Save log
    log_path = session.save_log(output_path)
    if verbose:
        print(f"\n✅ Лог сохранён в: {log_path}")
    
    return session


def main():
    """Main entry point."""
    print_banner()
    profile = get_candidate_info()
    run_interview(profile)
    print("\n👋 Спасибо за использование Interview Coach!")


if __name__ == "__main__":
    main()
