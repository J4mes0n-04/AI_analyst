"""Generate use cases from business requirements (heuristic + structured output)."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UseCaseStep:
    """Single step in the main success scenario."""

    order: int
    actor_action: str
    system_response: str


@dataclass
class UseCase:
    """Use case per Wiegers-style naming."""

    id: str
    name: str
    primary_actor: str
    goal: str
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)
    main_success: list[UseCaseStep] = field(default_factory=list)
    extensions: list[str] = field(default_factory=list)
    priority_hint: str = "—"
    source_snippet: str = ""


class UseCaseGenerator:
    """
    Analyzes free-text business requirements: предпроектный анализ (рынок, конкуренты,
    потребности) и черновики UC. Подходит для ревью аналитика; можно подключить LLM.
    """

    _actor_patterns = re.compile(
        r"(?:пользователь|клиент|оператор|администратор|система|гость|покупатель|"
        r"user|customer|admin|operator|system|guest|buyer)\b",
        re.IGNORECASE,
    )

    _goal_kw = (
        "должен",
        "должна",
        "должны",
        "необходимо",
        "требуется",
        "нужно",
        "нужна",
        "нужны",
        "мне нужно",
        "хочу",
        "хотим",
        "создать",
        "разработать",
        "сделать",
        "построить",
        "внедрить",
        "реализовать",
        "must",
        "should",
        "need to",
        "want to",
        "shall",
    )

    def __init__(self) -> None:
        self._last_raw: str = ""

    def analyze(self, text: str) -> dict[str, Any]:
        """Parse input: глубокий предпроектный анализ + варианты использования."""
        self._last_raw = text or ""
        cleaned = self._normalize_text(text)
        tags = self._detect_domain_signals(cleaned)
        goals = self._extract_goals(cleaned)
        actors = self._extract_actors(cleaned)
        deep = self._build_deep_analysis(cleaned, goals, actors, tags)
        use_cases = self._build_use_cases(cleaned, goals, actors, tags)
        return {
            "summary": self._summary(cleaned, len(use_cases), deep),
            "domain_tags": sorted(tags),
            "deep_analysis": deep,
            "actors": sorted(actors),
            "goals": goals,
            "use_cases": [self._uc_to_dict(uc) for uc in use_cases],
        }

    def _normalize_text(self, text: str) -> str:
        t = (text or "").strip()
        t = re.sub(r"\r\n?", "\n", t)
        return t

    def _detect_domain_signals(self, text: str) -> set[str]:
        low = text.lower()
        tags: set[str] = set()
        if any(
            w in low
            for w in (
                "регистрац",
                "аккаунт",
                "логин",
                "авториз",
                "signup",
                "sign up",
                "учётн",
                "учетн",
                "парол",
            )
        ):
            tags.add("account_registration")
        if any(
            w in low
            for w in (
                "магазин",
                "продаж",
                "товар",
                "корзин",
                "заказ",
                "оплат",
                "ecommerce",
                "e-commerce",
                "доставк",
                "каталог",
            )
        ):
            tags.add("ecommerce")
        if any(w in low for w in ("мобильн", "приложени", "ios", "android", "telegram")):
            tags.add("mobile_or_omni")
        if any(w in low for w in ("админ", "модератор", "бэк-офис", "crm")):
            tags.add("admin_backoffice")
        if any(w in low for w in ("отчёт", "отчет", "дашборд", "аналитик", "kpi", "метрик")):
            tags.add("analytics")
        if any(w in low for w in ("api", "интеграц", "вебхук", "webhook", "1с", "erp")):
            tags.add("integrations")
        if any(w in low for w in ("пдн", "152-фз", "gdpr", "cookie", "согласи", "конфиденц")):
            tags.add("privacy_compliance")
        return tags

    def _extract_goals(self, text: str) -> list[str]:
        goals: list[str] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            low = line.lower()
            if any(kw in low for kw in self._goal_kw):
                goals.append(line.rstrip(".;"))
        if not goals and text.strip():
            parts = re.split(r"(?<=[.!?])\s+", text[:4000])
            cand = [p.strip() for p in parts if len(p.strip()) > 12]
            if cand:
                goals.extend(cand[:12])
            elif len(text.strip()) > 12:
                goals.append(text.strip()[:500])
        return goals[:30]

    def _extract_actors(self, text: str) -> set[str]:
        actors: set[str] = set()
        for m in self._actor_patterns.finditer(text):
            word = m.group(0).strip()
            if word:
                actors.add(word[0].upper() + word[1:].lower())
        low = text.lower()
        if "регистрац" in low or "гост" in low:
            actors.add("Гость")
        if "магазин" in low or "покуп" in low or "продаж" in low:
            actors.add("Покупатель")
        if "админ" in low:
            actors.add("Администратор")
        if not actors:
            actors.add("Пользователь")
        return actors

    def _build_deep_analysis(
        self,
        text: str,
        goals: list[str],
        actors: set[str],
        tags: set[str],
    ) -> dict[str, Any]:
        """Черновик предпроектного анализа (структура Вигерса + продуктовый контекст)."""
        primary_goal = goals[0] if goals else (text[:400] if text else "Цель не сформулирована")
        domain_guess = self._infer_domain_line(text, tags)
        stakeholders = self._stakeholders(actors, tags)
        user_needs = self._user_needs(text, tags, primary_goal)
        market = self._market_block(text, tags, domain_guess)
        competitors = self._competitor_block(tags, domain_guess)
        risks = self._risks_block(tags)
        work_packages = self._work_packages(tags, primary_goal)
        open_q = self._open_questions(tags, text)
        metrics = self._suggested_metrics(tags)

        return {
            "problem_and_context": [
                f"Исходная формулировка: «{primary_goal[:350]}{'…' if len(primary_goal) > 350 else ''}».",
                domain_guess,
                "Это черновик для воркшопа: уточните измеримые цели (SMART), границы продукта и критерии успеха.",
            ],
            "stakeholders": stakeholders,
            "user_needs": user_needs,
            "market_overview": market,
            "competitor_landscape": competitors,
            "differentiation_and_positioning": self._differentiation(tags),
            "constraints_and_compliance": self._compliance_block(tags),
            "risks_and_assumptions": risks,
            "recommended_work_packages": work_packages,
            "open_questions": open_q,
            "success_metrics": metrics,
        }

    @staticmethod
    def _infer_domain_line(text: str, tags: set[str]) -> str:
        if "ecommerce" in tags and "account_registration" in tags:
            return (
                "По тексту видно сочетание онлайн-торговли и учётной записи покупателя: "
                "типичны сценарии каталог → корзина → оформление, отдельно — онбординг и профиль."
            )
        if "account_registration" in tags:
            return (
                "Фокус на идентификации пользователя: важны UX формы, безопасность пароля, "
                "подтверждение контакта и политика учётных записей."
            )
        if "ecommerce" in tags:
            return "Контекст электронной коммерции: цепочка заказа, оплаты, доставки и поддержки."
        return "Домен уточните на интервью со стейкхолдерами; ниже — универсальные направления анализа."

    @staticmethod
    def _stakeholders(actors: set[str], tags: set[str]) -> list[dict[str, str]]:
        rows = [
            {
                "role": "Бизнес-владелец / спонсор",
                "interest": "Доход, конверсия, срок вывода фич, управляемость затрат",
                "influence": "высокая",
            },
            {
                "role": "Конечный пользователь (продукт)",
                "interest": "Простота, скорость, доверие, прозрачность условий",
                "influence": "средняя (через метрики и исследования)",
            },
        ]
        if "ecommerce" in tags:
            rows.append(
                {
                    "role": "Операции: склад, доставка, поддержка",
                    "interest": "Корректность заказов, возвраты, SLA обращений",
                    "influence": "средняя",
                }
            )
        if "admin_backoffice" in tags or "ecommerce" in tags:
            rows.append(
                {
                    "role": "Администратор / контент / модерация",
                    "interest": "Каталог, цены, статусы заказов, антифрод",
                    "influence": "средняя",
                }
            )
        if "privacy_compliance" in tags or "account_registration" in tags:
            rows.append(
                {
                    "role": "Юридический / ИБ / DPO",
                    "interest": "ПДн, согласия, хранение, инциденты",
                    "influence": "высокая (блокирующая при нарушениях)",
                }
            )
        for a in sorted(actors):
            if a.lower() in ("пользователь", "user", "гость", "guest"):
                continue
            rows.append(
                {
                    "role": a,
                    "interest": "Уточнить на интервью",
                    "influence": "?",
                }
            )
        return rows

    @staticmethod
    def _user_needs(raw: str, tags: set[str], goal: str) -> list[str]:
        needs = [
            "Сократить время и когнитивную нагрузку при достижении цели (ясные шаги, подсказки ошибок).",
            "Получить предсказуемый результат без скрытых условий (прозрачные правила и статусы).",
        ]
        if "account_registration" in tags:
            needs.extend(
                [
                    "Быстро и безопасно создать учётную запись с понятным подтверждением личности/контакта.",
                    "Контроль над данными: что собираем, зачем, как отозвать согласие (где применимо).",
                ]
            )
        if "ecommerce" in tags:
            needs.extend(
                [
                    "Уверенность в товаре и продавце (отзывы, гарантии, условия возврата).",
                    "Удобная оплата и отслеживание заказа; понятная коммуникация при задержках.",
                ]
            )
        needs.append(f"Связь с вашей целью: {goal[:200]}{'…' if len(goal) > 200 else ''}")
        return needs

    @staticmethod
    def _market_block(text: str, tags: set[str], domain_guess: str) -> list[str]:
        lines = [
            "Сегментация (черновик): кто покупает/пользуется, география, типичный чек, частота покупок — заполнить данными.",
            "Каналы привлечения: органика, платный трафик, маркетплейсы, партнёры, офлайн — что актуально для вашей модели.",
            "Объём и динамика: TAM/SAM/SOM оставить как гипотезы до desk research и интервью.",
            domain_guess,
        ]
        if "ecommerce" in tags:
            lines.insert(
                1,
                "Для e-commerce: сравнить модель (маркетплейс vs собственный магазин vs гибрид) и юнит-экономику доставки.",
            )
        low = text.lower()
        if any(w in low for w in ("чайник", "ниш", "b2c", "b2b")):
            lines.append(
                "Уточнить нишу: массовый рынок vs премиум; B2C/B2B; сезонность и запасы под спрос."
            )
        return lines

    @staticmethod
    def _competitor_block(tags: set[str], domain_guess: str) -> list[str]:
        base = [
            "Косвенные конкуренты: альтернативные способы решить ту же задачу (офлайн, агрегаторы, DIY).",
            "Прямые конкуренты: 3–7 игроков с похожим предложением — заполнить после поиска (Яндекс/Google, Similarweb, отзывы).",
            "Сравнительная матрица: цена, ассортимент, доставка, UX регистрации/чекаута, программа лояльности, поддержка.",
            "Barriers: бренд, эксклюзивные поставки, сервис, скорость, доверие, интеграции.",
            domain_guess,
        ]
        if "account_registration" in tags:
            base.insert(
                2,
                "Для регистрации: сравнить соц.вход, email+пароль, телефон+SMS, обязательность регистрации до покупки (guest checkout).",
            )
        if "ecommerce" in tags:
            base.insert(
                1,
                "Архетипы: крупные маркетплейсы; нишевые D2C-магазины; соцкоммерция; локальные ритейлеры с click&collect.",
            )
        return base

    @staticmethod
    def _differentiation(tags: set[str]) -> list[str]:
        out = [
            "Какое уникальное обещание ценности (UVP) вы можете доказать метриками, а не слоганом?",
            "Что пользователь теряет, если выберет конкурента вместо вас?",
        ]
        if "ecommerce" in tags:
            out.append("Дифференциаторы e-com: ассортимент/эксклюзив, сервис, скорость, цена, контент, сообщество.")
        return out

    @staticmethod
    def _compliance_block(tags: set[str]) -> list[str]:
        lines = [
            "Технические ограничения: интеграции, SLA внешних API, производительность, доступность (WCAG — по политике компании).",
        ]
        if "privacy_compliance" in tags or "account_registration" in tags:
            lines.extend(
                [
                    "ПДн / согласия / политика конфиденциальности; хранение и сроки; ответы на запросы субъектов.",
                    "152-ФЗ / GDPR (если есть иностранные пользователи): правовая основа обработки, трансграничная передача.",
                ]
            )
        if "ecommerce" in tags:
            lines.append("Права потребителей (возврат, оферта), платёжные требования PCI DSS при работе с картами.")
        return lines

    @staticmethod
    def _risks_block(tags: set[str]) -> list[str]:
        r = [
            "Риск неверных гипотез о сегменте — смягчение: интервью, прототипы, A/B.",
            "Риск недооценки интеграций и сроков — буфер и поэтапный релиз (MVP → итерации).",
        ]
        if "account_registration" in tags:
            r.append("Безопасность: перебор паролей, утечки, фейковые регистрации — rate limit, капча, мониторинг.")
        if "ecommerce" in tags:
            r.append("Операционные риски: остатки, фрод-заказы, логистика, возвраты.")
        return r

    @staticmethod
    def _work_packages(tags: set[str], goal: str) -> list[str]:
        pk = [
            "Уточнение vision и границ MVP (in/out of scope).",
            "Пользовательские исследования / CJM для ключевых сценариев.",
            "Нефункциональные требования: производительность, безопасность, наблюдаемость.",
        ]
        if "account_registration" in tags:
            pk.insert(1, "Поток регистрации: поля, валидации, подтверждение, восстановление доступа, гостевой режим.")
        if "ecommerce" in tags:
            pk.insert(1, "Каталог, карточка товара, корзина, оформление, оплата, уведомления, ЛК заказов.")
        pk.append(f"Декомпозиция под вашу цель: {goal[:120]}{'…' if len(goal) > 120 else ''}")
        return pk

    @staticmethod
    def _open_questions(tags: set[str], text: str) -> list[str]:
        q = [
            "Кто принимает решение о покупке и кто платит (если B2B)?",
            "Какие обязательные отчёты и интеграции на старте vs позже?",
            "Какие метрики успеха фиксируем до разработки (baseline)?",
        ]
        if "account_registration" in tags:
            q.append("Нужна ли обязательная регистрация до покупки или допускаем гостевой заказ?")
        if "ecommerce" in tags:
            q.append("Модель доставки и склад: свой, 3PL, дропшиппинг?")
        if len(text.split()) < 25:
            q.append("Входной текст короткий — какие детали домена и ограничений добавить?")
        return q

    @staticmethod
    def _suggested_metrics(tags: set[str]) -> list[str]:
        m = [
            "Воронка: визит → ключевое действие → конверсия в целевое событие.",
            "Удовлетворённость: CSAT/NPS по критическим шагам (опрос точечный).",
        ]
        if "account_registration" in tags:
            m.append("Регистрация: completion rate, время до успеха, доля ошибок валидации, bounce на форме.")
        if "ecommerce" in tags:
            m.extend(
                [
                    "AOV, частота покупок, доля возвратов, доля брошенных корзин.",
                    "CAC vs LTV (когда есть стабильный трафик).",
                ]
            )
        return m

    def _build_use_cases(
        self,
        text: str,
        goals: list[str],
        actors: set[str],
        tags: set[str],
    ) -> list[UseCase]:
        primary = self._pick_primary_actor(actors, tags)
        use_cases: list[UseCase] = []
        for i, goal in enumerate(goals[:25]):
            name = self._goal_to_name(goal)
            uc_id = f"UC-{i + 1:03d}"
            steps, pre, post, ext = self._infer_scenario(goal, primary, tags)
            uc = UseCase(
                id=uc_id,
                name=name,
                primary_actor=primary,
                goal=goal[:500],
                preconditions=pre,
                postconditions=post,
                main_success=steps,
                extensions=ext,
                source_snippet=goal[:200],
            )
            use_cases.append(uc)
        if not use_cases and text.strip():
            steps, pre, post, ext = self._infer_scenario(text, primary, tags)
            uc = UseCase(
                id="UC-001",
                name="Обработка введённых требований",
                primary_actor=primary,
                goal="Структурировать и уточнить бизнес-требования",
                preconditions=pre,
                postconditions=post,
                main_success=steps,
                extensions=ext,
                source_snippet=text[:200],
            )
            use_cases.append(uc)
        return use_cases

    @staticmethod
    def _pick_primary_actor(actors: set[str], tags: set[str]) -> str:
        if "Гость" in actors and "account_registration" in tags:
            return "Гость"
        if "Покупатель" in actors:
            return "Покупатель"
        return next(iter(sorted(actors)), "Пользователь")

    def _infer_scenario(
        self,
        goal: str,
        actor: str,
        tags: set[str],
    ) -> tuple[list[UseCaseStep], list[str], list[str], list[str]]:
        if "account_registration" in tags and "ecommerce" in tags:
            return self._uc_registration_shop(actor)
        if "account_registration" in tags:
            return self._uc_registration_generic(actor)
        if "ecommerce" in tags:
            return self._uc_ecommerce_browse(actor)
        return self._uc_generic(actor, goal)

    @staticmethod
    def _uc_registration_shop(actor: str) -> tuple[list[UseCaseStep], list[str], list[str], list[str]]:
        steps = [
            UseCaseStep(1, f"{actor} открывает страницу регистрации", "Система показывает форму, ссылки на политику и оферту"),
            UseCaseStep(2, f"{actor} вводит email, пароль и обязательные поля профиля", "Клиентская валидация формата и силы пароля"),
            UseCaseStep(3, f"{actor} отмечает согласия (ПДн, рассылка — по политике)", "Система фиксирует отметки времени и версии документов"),
            UseCaseStep(4, f"{actor} отправляет форму регистрации", "Сервер проверяет уникальность email и бизнес-правила"),
            UseCaseStep(5, "Система создаёт учётную запись в статусе «ожидает подтверждения»", "Отправлено письмо/SMS со ссылкой или кодом"),
            UseCaseStep(6, f"{actor} подтверждает контакт по ссылке или коду", "Аккаунт активирован, создаётся сессия или редирект в ЛК"),
            UseCaseStep(7, f"{actor} проходит краткий онбординг (адрес, предпочтения — опционально)", "Профиль дополнен; готово к покупкам в каталоге"),
        ]
        pre = [
            "Сайт доступен; формы локализованы; настроены почтовый/SMS-провайдер.",
            "Утверждены тексты согласий и политика конфиденциальности.",
        ]
        post = [
            "Учётная запись активна; событие регистрации записано в журнал; сегменты для маркетинга обновлены (если применимо).",
        ]
        ext = [
            "Альт. 4a: email уже занят — сообщение и сценарий входа/восстановления пароля.",
            "Альт. 4b: слабый пароль или невалидный email — подсветка полей без создания записи.",
            "Альт. 5a: истёк срок ссылки подтверждения — повторная отправка с rate limit.",
            "Альт. 6a: подозрение на бота — CAPTCHA или дополнительная проверка.",
        ]
        return steps, pre, post, ext

    @staticmethod
    def _uc_registration_generic(actor: str) -> tuple[list[UseCaseStep], list[str], list[str], list[str]]:
        steps = [
            UseCaseStep(1, f"{actor} открывает форму регистрации", "Система отображает поля и требования к паролю"),
            UseCaseStep(2, f"{actor} заполняет идентификатор (email/телефон) и пароль", "Валидация формата на клиенте и сервере"),
            UseCaseStep(3, f"{actor} подтверждает согласия", "Версии документов зафиксированы"),
            UseCaseStep(4, f"{actor} отправляет форму", "Создаётся запись пользователя; отправлено подтверждение"),
            UseCaseStep(5, f"{actor} завершает подтверждение", "Учётная запись активирована"),
        ]
        pre = ["Доступен канал доставки кода/ссылки; политика паролей определена."]
        post = ["Пользователь может аутентифицироваться согласно политике продукта."]
        ext = [
            "Дубликат идентификатора; неверный код; brute-force — блокировка и оповещение.",
        ]
        return steps, pre, post, ext

    @staticmethod
    def _uc_ecommerce_browse(actor: str) -> tuple[list[UseCaseStep], list[str], list[str], list[str]]:
        steps = [
            UseCaseStep(1, f"{actor} открывает каталог или поиск", "Система показывает выдачу с фильтрами и наличием"),
            UseCaseStep(2, f"{actor} открывает карточку товара", "Отображаются цена, условия, отзывы, доставка"),
            UseCaseStep(3, f"{actor} добавляет товар в корзину", "Корзина пересчитана; сохранены выбранные опции"),
            UseCaseStep(4, f"{actor} переходит к оформлению", "Система запрашивает доставку, контакты, оплату"),
            UseCaseStep(5, f"{actor} подтверждает заказ", "Создан заказ; отправлены уведомления; резерв/оплата по правилам"),
        ]
        pre = ["Каталог и цены актуальны; платёжный шлюз в тесте или бою."]
        post = ["Заказ в учётной системе; пользователь видит статус в ЛК или письме."]
        ext = ["Нет в наличии; отказ оплаты; ошибка адреса — понятные сообщения и откат состояния."]
        return steps, pre, post, ext

    @staticmethod
    def _uc_generic(actor: str, goal: str) -> tuple[list[UseCaseStep], list[str], list[str], list[str]]:
        gshort = goal[:60] + ("…" if len(goal) > 60 else "")
        steps = [
            UseCaseStep(1, f"{actor} формулирует намерение: {gshort}", "Система уточняет входные данные и контекст"),
            UseCaseStep(2, f"{actor} предоставляет необходимые данные", "Система валидирует и сохраняет черновик"),
            UseCaseStep(3, f"{actor} запускает основное действие", "Система выполняет бизнес-логику и проверки прав"),
            UseCaseStep(4, f"{actor} получает результат и обратную связь", "Система отображает итог, коды ошибок, следующие шаги"),
            UseCaseStep(5, f"{actor} при необходимости корректирует или повторяет", "Система журналирует события для аудита"),
        ]
        pre = ["Система доступна; права акторов определены."]
        post = ["Состояние согласовано с бизнес-правилами; аудит доступен."]
        ext = [
            "Недостаточно прав; сбой внешней службы; таймаут — понятные сообщения и политика повтора.",
        ]
        return steps, pre, post, ext

    def _goal_to_name(self, goal: str) -> str:
        g = goal.strip()
        if len(g) > 80:
            g = g[:77] + "…"
        return g or "Без названия"

    def _summary(self, text: str, uc_count: int, deep: dict[str, Any]) -> str:
        wc = len(text.split())
        n_st = len(deep.get("stakeholders", []))
        n_q = len(deep.get("open_questions", []))
        return (
            f"Предпроектный анализ: контекст, {n_st} ролей стейкхолдеров, рынок и конкуренты (чек-листы), "
            f"потребности, риски, пакеты работ, {n_q} открытых вопросов. "
            f"Текст: ~{wc} слов. Варианты использования (черновик): {uc_count}. "
            "Данные без внешнего интернета — уточните цифры и имена конкурентов по desk research."
        )

    @staticmethod
    def _uc_to_dict(uc: UseCase) -> dict[str, Any]:
        return {
            "id": uc.id,
            "name": uc.name,
            "primary_actor": uc.primary_actor,
            "goal": uc.goal,
            "preconditions": uc.preconditions,
            "postconditions": uc.postconditions,
            "main_success": [
                {"order": s.order, "actor_action": s.actor_action, "system_response": s.system_response}
                for s in uc.main_success
            ],
            "extensions": uc.extensions,
            "priority_hint": uc.priority_hint,
            "source_snippet": uc.source_snippet,
        }


def new_requirement_id(prefix: str = "BR") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
