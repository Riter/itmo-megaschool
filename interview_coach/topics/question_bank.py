"""Question bank with topics and questions by role and grade."""

from typing import Optional


# Topics organized by role and grade level
TOPICS_BY_ROLE = {
    "Backend Developer": {
        "Junior": [
            "python_basics",
            "python_data_structures", 
            "sql_basics",
            "git_basics",
            "http_basics",
            "oop_basics",
        ],
        "Middle": [
            "python_advanced",
            "python_concurrency",
            "sql_optimization",
            "api_design",
            "testing",
            "design_patterns",
            "databases",
        ],
        "Senior": [
            "system_design",
            "scalability",
            "security",
            "microservices",
            "performance",
            "team_leadership",
            "architecture",
        ]
    },
    "ML Engineer": {
        "Junior": [
            "python_basics",
            "numpy_pandas",
            "ml_basics",
            "statistics_basics",
            "data_preprocessing",
        ],
        "Middle": [
            "ml_algorithms",
            "deep_learning",
            "feature_engineering",
            "model_evaluation",
            "ml_pipelines",
        ],
        "Senior": [
            "ml_system_design",
            "mlops",
            "distributed_ml",
            "model_optimization",
            "research_methodology",
        ]
    },
    "Frontend Developer": {
        "Junior": [
            "html_css_basics",
            "javascript_basics",
            "dom_manipulation",
            "git_basics",
            "responsive_design",
        ],
        "Middle": [
            "javascript_advanced",
            "react_basics",
            "state_management",
            "testing_frontend",
            "performance_frontend",
        ],
        "Senior": [
            "architecture_frontend",
            "build_tools",
            "accessibility",
            "security_frontend",
            "team_leadership",
        ]
    }
}


# Question templates by topic and difficulty (1-5)
QUESTION_TEMPLATES = {
    # Python Basics
    "python_basics": {
        1: [
            "Какие базовые типы данных есть в Python?",
            "Что такое переменная в Python?",
            "Как создать список в Python?",
        ],
        2: [
            "Чем отличается list от tuple в Python?",
            "Что такое словарь (dict) и для чего он используется?",
            "Как работает индексация в Python?",
        ],
        3: [
            "Объясни, как работает цикл for в Python. Приведи пример.",
            "Что такое list comprehension? Когда его стоит использовать?",
            "Как обрабатывать исключения в Python?",
        ],
        4: [
            "Что такое генераторы в Python? Чем они отличаются от обычных функций?",
            "Объясни разницу между `is` и `==` в Python.",
            "Как работает механизм управления памятью в Python?",
        ],
        5: [
            "Расскажи про GIL и его влияние на многопоточность в Python.",
            "Что такое метаклассы в Python? Приведи пример использования.",
            "Объясни, как работает сборщик мусора в Python.",
        ]
    },
    
    # Python Data Structures
    "python_data_structures": {
        1: [
            "Какие структуры данных встроены в Python?",
            "Как добавить элемент в список?",
        ],
        2: [
            "Чем set отличается от list?",
            "Как проверить, есть ли ключ в словаре?",
        ],
        3: [
            "Какая сложность операций поиска в list, set и dict?",
            "Когда лучше использовать tuple вместо list?",
        ],
        4: [
            "Что такое collections.defaultdict и когда его использовать?",
            "Объясни, как работает хеширование в dict.",
        ],
        5: [
            "Как реализовать собственную хеш-таблицу?",
            "Расскажи про структуру данных deque и её применение.",
        ]
    },
    
    # OOP Basics
    "oop_basics": {
        1: [
            "Что такое класс и объект в ООП?",
            "Как создать класс в Python?",
        ],
        2: [
            "Что такое наследование? Приведи пример.",
            "Что такое инкапсуляция?",
        ],
        3: [
            "Объясни принцип полиморфизма на примере.",
            "Что такое абстрактные классы в Python?",
        ],
        4: [
            "Расскажи про множественное наследование и проблему ромба.",
            "Что такое MRO (Method Resolution Order)?",
        ],
        5: [
            "Как реализовать паттерн Singleton в Python?",
            "Объясни принципы SOLID на примерах.",
        ]
    },
    
    # SQL Basics
    "sql_basics": {
        1: [
            "Что такое SQL? Для чего он используется?",
            "Как выбрать все данные из таблицы?",
        ],
        2: [
            "Что такое PRIMARY KEY и FOREIGN KEY?",
            "Как отфильтровать данные с помощью WHERE?",
        ],
        3: [
            "Объясни разницу между INNER JOIN и LEFT JOIN.",
            "Как сгруппировать данные и посчитать агрегаты?",
        ],
        4: [
            "Что такое индексы и зачем они нужны?",
            "Объясни, что такое транзакции и ACID.",
        ],
        5: [
            "Как оптимизировать медленный SQL-запрос?",
            "Расскажи про уровни изоляции транзакций.",
        ]
    },
    
    # Git Basics
    "git_basics": {
        1: [
            "Что такое Git и зачем он нужен?",
            "Как создать новый репозиторий?",
        ],
        2: [
            "Объясни разницу между git add, git commit и git push.",
            "Что такое ветка (branch) в Git?",
        ],
        3: [
            "Как разрешить конфликт при merge?",
            "Чем отличается merge от rebase?",
        ],
        4: [
            "Что такое git stash и когда его использовать?",
            "Как откатить последний коммит?",
        ],
        5: [
            "Расскажи про Git Flow и другие стратегии ветвления.",
            "Как работает git bisect?",
        ]
    },
    
    # HTTP Basics
    "http_basics": {
        1: [
            "Что такое HTTP?",
            "Какие HTTP-методы ты знаешь?",
        ],
        2: [
            "Чем отличается GET от POST?",
            "Что означают коды ответов 200, 404, 500?",
        ],
        3: [
            "Что такое REST API? Какие принципы REST?",
            "Как работают cookies и сессии?",
        ],
        4: [
            "Чем отличается HTTP от HTTPS?",
            "Что такое CORS и зачем он нужен?",
        ],
        5: [
            "Расскажи про HTTP/2 и его отличия от HTTP/1.1.",
            "Как работает WebSocket?",
        ]
    },
    
    # Python Advanced
    "python_advanced": {
        3: [
            "Что такое декораторы? Напиши пример.",
            "Как работают контекстные менеджеры (with)?",
        ],
        4: [
            "Объясни, как работает async/await в Python.",
            "Что такое дескрипторы в Python?",
        ],
        5: [
            "Как работает import system в Python?",
            "Расскажи про профилирование и оптимизацию Python-кода.",
        ]
    },
    
    # Python Concurrency
    "python_concurrency": {
        3: [
            "Чем отличается threading от multiprocessing?",
            "Когда использовать asyncio?",
        ],
        4: [
            "Как избежать race conditions в многопоточном коде?",
            "Что такое ThreadPoolExecutor?",
        ],
        5: [
            "Как масштабировать Python-приложение для CPU-bound задач?",
            "Расскажи про concurrent.futures и его паттерны.",
        ]
    },
    
    # SQL Optimization
    "sql_optimization": {
        3: [
            "Как понять, что запрос работает медленно?",
            "Что показывает EXPLAIN?",
        ],
        4: [
            "Какие типы индексов существуют и когда какой использовать?",
            "Как оптимизировать JOIN на больших таблицах?",
        ],
        5: [
            "Расскажи про шардинг и репликацию баз данных.",
            "Как организовать эффективное кеширование данных?",
        ]
    },
    
    # API Design
    "api_design": {
        3: [
            "Какие best practices при проектировании REST API?",
            "Как версионировать API?",
        ],
        4: [
            "Как реализовать пагинацию в API?",
            "Что такое rate limiting и как его реализовать?",
        ],
        5: [
            "Сравни REST, GraphQL и gRPC. Когда что использовать?",
            "Как спроектировать API для микросервисной архитектуры?",
        ]
    },
    
    # Testing
    "testing": {
        3: [
            "Какие виды тестов ты знаешь?",
            "Что такое unit-тесты? Напиши пример.",
        ],
        4: [
            "Что такое mock и когда его использовать?",
            "Как тестировать асинхронный код?",
        ],
        5: [
            "Как организовать CI/CD пайплайн с тестами?",
            "Расскажи про TDD и BDD подходы.",
        ]
    },
    
    # Design Patterns
    "design_patterns": {
        3: [
            "Какие паттерны проектирования ты знаешь?",
            "Объясни паттерн Factory на примере.",
        ],
        4: [
            "Когда использовать Strategy vs Template Method?",
            "Расскажи про паттерн Observer.",
        ],
        5: [
            "Как применить CQRS в реальном проекте?",
            "Расскажи про Event Sourcing.",
        ]
    },
    
    # System Design (Senior)
    "system_design": {
        4: [
            "Как бы ты спроектировал систему сокращения URL?",
            "Какие компоненты нужны для простого чат-приложения?",
        ],
        5: [
            "Спроектируй систему типа Twitter с миллионами пользователей.",
            "Как обеспечить high availability для критичного сервиса?",
        ]
    },
    
    # Scalability (Senior)
    "scalability": {
        4: [
            "Как масштабировать веб-приложение горизонтально?",
            "Что такое load balancing и какие алгоритмы существуют?",
        ],
        5: [
            "Как организовать кеширование на разных уровнях?",
            "Расскажи про CAP-теорему и её применение.",
        ]
    },
    
    # Security (Senior)
    "security": {
        4: [
            "Какие основные уязвимости веб-приложений ты знаешь?",
            "Как защититься от SQL injection?",
        ],
        5: [
            "Как организовать безопасное хранение паролей?",
            "Расскажи про OAuth 2.0 и JWT.",
        ]
    },
}


def get_topics_for_role(role: str, grade: str) -> list[str]:
    """Get list of topics for a specific role and grade.
    
    Args:
        role: Job role (e.g., "Backend Developer")
        grade: Grade level ("Junior", "Middle", "Senior")
    
    Returns:
        List of topic identifiers
    """
    if role not in TOPICS_BY_ROLE:
        # Default to Backend Developer
        role = "Backend Developer"
    
    role_topics = TOPICS_BY_ROLE[role]
    
    if grade not in role_topics:
        grade = "Junior"
    
    return role_topics[grade]


def get_questions_for_topic(topic: str, difficulty: int) -> list[str]:
    """Get questions for a topic at a specific difficulty level.
    
    Args:
        topic: Topic identifier
        difficulty: Difficulty level 1-5
    
    Returns:
        List of question templates
    """
    if topic not in QUESTION_TEMPLATES:
        return [f"Расскажи, что ты знаешь о {topic}?"]
    
    topic_questions = QUESTION_TEMPLATES[topic]
    
    # Try exact difficulty, then nearby
    if difficulty in topic_questions:
        return topic_questions[difficulty]
    
    # Find closest available difficulty
    available = sorted(topic_questions.keys())
    closest = min(available, key=lambda x: abs(x - difficulty))
    return topic_questions[closest]


def get_topic_description(topic: str) -> str:
    """Get a human-readable description of a topic.
    
    Args:
        topic: Topic identifier
    
    Returns:
        Human-readable topic name
    """
    descriptions = {
        "python_basics": "Основы Python",
        "python_data_structures": "Структуры данных Python",
        "python_advanced": "Продвинутый Python",
        "python_concurrency": "Многопоточность и асинхронность",
        "sql_basics": "Основы SQL",
        "sql_optimization": "Оптимизация SQL",
        "git_basics": "Основы Git",
        "http_basics": "HTTP и веб-протоколы",
        "oop_basics": "ООП",
        "api_design": "Проектирование API",
        "testing": "Тестирование",
        "design_patterns": "Паттерны проектирования",
        "databases": "Базы данных",
        "system_design": "Системный дизайн",
        "scalability": "Масштабирование",
        "security": "Безопасность",
        "microservices": "Микросервисы",
        "performance": "Производительность",
        "team_leadership": "Лидерство",
        "architecture": "Архитектура",
    }
    return descriptions.get(topic, topic.replace("_", " ").title())
