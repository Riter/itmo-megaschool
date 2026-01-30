#!/usr/bin/env python3
"""Test script for running the example scenario from ТЗ.

This script runs the predefined scenario to test:
1. Normal answer handling
2. Hallucination detection (Python 4.0 removes for-loops)
3. Role reversal (candidate asks question)
4. Stop command handling
"""

import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from interview_coach.schemas import CandidateProfile
from interview_coach.main import run_scripted_interview


# Test scenario from ТЗ
SCENARIO_PROFILE = CandidateProfile(
    name="Алекс",
    role="Backend Developer",
    grade_target="Junior",
    experience="Пет-проекты на Django, немного SQL"
)

SCENARIO_MESSAGES = [
    # Ход 1: Приветствие
    "Привет. Я Алекс, претендую на позицию Junior Backend Developer. Знаю Python, SQL и Git.",
    
    # Ход 2: Ожидаем технический вопрос, даём правильный ответ
    # (Этот ответ должен быть адаптирован к вопросу, который задаст агент)
    "В Python есть несколько базовых типов данных: числа (int, float, complex), строки (str), "
    "логический тип (bool), списки (list), кортежи (tuple), множества (set) и словари (dict). "
    "Списки изменяемые, кортежи - нет. Словари хранят пары ключ-значение с O(1) доступом.",
    
    # Ход 3: Ловушка - Hallucination Test
    "Честно говоря, я читал на Хабре, что в Python 4.0 циклы for уберут и заменят на "
    "нейронные связи, поэтому я их не учу.",
    
    # Ход 4: Role Reversal - кандидат задаёт вопрос
    "Слушайте, а какие задачи вообще будут на испытательном сроке? Вы используете микросервисы?",
    
    # Ход 5: Завершение
    "Стоп игра. Давай фидбэк."
]


def run_test_scenario():
    """Run the test scenario and save the log."""
    print("="*70)
    print("🧪 ТЕСТОВЫЙ СЦЕНАРИЙ ИЗ ТЗ")
    print("="*70)
    print(f"\nКандидат: {SCENARIO_PROFILE.name}")
    print(f"Позиция: {SCENARIO_PROFILE.role}")
    print(f"Уровень: {SCENARIO_PROFILE.grade_target}")
    print(f"Опыт: {SCENARIO_PROFILE.experience}")
    print(f"\nСценарий включает проверку:")
    print("  1. Приветствие и представление")
    print("  2. Правильный технический ответ")
    print("  3. 🚨 Галлюцинация (Python 4.0 уберёт for-циклы)")
    print("  4. 🔄 Role Reversal (вопрос от кандидата)")
    print("  5. ⏹  Команда 'Стоп игра'")
    print("="*70)
    
    output_path = "test_scenario_log.json"
    
    try:
        session = run_scripted_interview(
            profile=SCENARIO_PROFILE,
            messages=SCENARIO_MESSAGES,
            output_path=output_path,
            verbose=True
        )
        
        print("\n" + "="*70)
        print("✅ ТЕСТ ЗАВЕРШЁН УСПЕШНО")
        print("="*70)
        print(f"\n📄 Лог сохранён в: {output_path}")
        print("\nПроверьте лог на наличие:")
        print("  - internal_thoughts с рассуждениями Observer")
        print("  - Распознавание галлюцинации и её исправление")
        print("  - Ответ на вопрос кандидата + возврат к интервью")
        print("  - Структурированный финальный отчёт")
        
        return session
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_custom_scenario(messages: list[str], name: str = "Тест"):
    """Run a custom scenario.
    
    Args:
        messages: List of candidate messages
        name: Name for the test
    """
    profile = CandidateProfile(
        name=name,
        role="Backend Developer",
        grade_target="Junior",
        experience="Тестирование"
    )
    
    output_path = f"custom_scenario_{name.lower()}.json"
    
    return run_scripted_interview(
        profile=profile,
        messages=messages,
        output_path=output_path,
        verbose=True
    )


# Additional test scenarios
HALLUCINATION_ONLY_SCENARIO = [
    "Привет, я кандидат на позицию разработчика.",
    "JavaScript строго типизированный язык, потому что там есть TypeScript.",
    "Стоп."
]

OFF_TOPIC_SCENARIO = [
    "Привет, меня зовут Тест.",
    "А какая сегодня погода? Как вам выходные?",
    "Хорошо, вернёмся к Python. Я знаю про списки и словари.",
    "Стоп игра."
]

HONEST_NOT_KNOWING_SCENARIO = [
    "Привет, я джун разработчик.",
    "Честно говоря, я не знаю что такое декораторы. Можете объяснить?",
    "Спасибо за объяснение! Теперь понятнее.",
    "Стоп."
]


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run test scenarios")
    parser.add_argument(
        "--scenario", "-s",
        choices=["tz", "hallucination", "offtopic", "honest"],
        default="tz",
        help="Which scenario to run"
    )
    
    args = parser.parse_args()
    
    if args.scenario == "tz":
        run_test_scenario()
    elif args.scenario == "hallucination":
        run_custom_scenario(HALLUCINATION_ONLY_SCENARIO, "HallucinationTest")
    elif args.scenario == "offtopic":
        run_custom_scenario(OFF_TOPIC_SCENARIO, "OffTopicTest")
    elif args.scenario == "honest":
        run_custom_scenario(HONEST_NOT_KNOWING_SCENARIO, "HonestTest")
