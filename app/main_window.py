"""Main PyQt6 shell: navigation, modules, autosave, themes, help."""

from __future__ import annotations

import webbrowser
from pathlib import Path

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import QStyle
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QSystemTrayIcon,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolTip,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import __version__
from app.document_builder import build_docx, build_pdf
from app.project_store import (
    ProjectData,
    load_autosave,
    load_project,
    save_autosave,
    save_project,
)
from app.themes import stylesheet_for_theme
from app.update_checker import check_for_updates
from core import (
    PriorityManager,
    RequirementConverter,
    RequirementVisualizer,
    TraceabilityMatrix,
    UseCaseGenerator,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"AI Analyst — ТЗ по Вигерсу v{__version__}")
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)

        self._data = ProjectData()
        self._matrix = TraceabilityMatrix()
        self._generator = UseCaseGenerator()
        self._converter = RequirementConverter()
        self._visualizer = RequirementVisualizer()
        self._priority = PriorityManager()
        self._dark = False

        self._build_menu()
        self._build_ui()
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(90_000)
        self._autosave_timer.timeout.connect(self._do_autosave)
        self._autosave_timer.start()

        self._tray: QSystemTrayIcon | None = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray = QSystemTrayIcon(self)
            self._tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
            self._tray.setToolTip("AI Analyst")
            self._tray.show()

        self._offer_autosave_recovery()

    # ——— persistence ———
    def _sync_matrix_from_data(self) -> None:
        self._matrix.from_serializable(self._data.matrix_rows)

    def _flush_matrix_to_data(self) -> None:
        self._data.matrix_rows = self._matrix.to_serializable()

    def _do_autosave(self) -> None:
        self._flush_matrix_to_data()
        save_autosave(self._data)

    def _offer_autosave_recovery(self) -> None:
        prev = load_autosave()
        if not prev or not (prev.business_text or prev.analysis or prev.matrix_rows):
            self._sync_matrix_from_data()
            return
        r = QMessageBox.question(
            self,
            "Автосохранение",
            "Найден файл автосохранения. Восстановить проект?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if r == QMessageBox.StandardButton.Yes:
            self._data = prev
            self._sync_matrix_from_data()
            self._reload_all_views()
        else:
            self._sync_matrix_from_data()

    def _reload_all_views(self) -> None:
        self._analysis_input.setPlainText(self._data.business_text)
        self._refresh_analysis_tree()
        self._refresh_matrix_table()
        self._converter_input.setPlainText(self._data.converter_input)
        idx = {"text": 0, "user_stories": 1, "functional": 2}.get(self._data.converter_source, 0)
        self._src_fmt.setCurrentIndex(idx)
        idx2 = {"text": 0, "user_stories": 1, "functional": 2}.get(self._data.converter_target, 1)
        self._tgt_fmt.setCurrentIndex(idx2)
        self._refresh_priority_table()

    # ——— UI ———
    def _build_menu(self) -> None:
        mb = self.menuBar()
        file_m = mb.addMenu("Файл")
        act_new = QAction("Новый проект", self)
        act_new.triggered.connect(self._new_project)
        file_m.addAction(act_new)
        act_open = QAction("Открыть…", self)
        act_open.triggered.connect(self._open_project)
        file_m.addAction(act_open)
        act_save = QAction("Сохранить", self)
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self._save_project)
        file_m.addAction(act_save)
        act_save_as = QAction("Сохранить как…", self)
        act_save_as.triggered.connect(self._save_project_as)
        file_m.addAction(act_save_as)
        file_m.addSeparator()
        act_exit = QAction("Выход", self)
        act_exit.triggered.connect(self.close)
        file_m.addAction(act_exit)

        view_m = mb.addMenu("Вид")
        act_theme = QAction("Тёмная тема", self, checkable=True)
        act_theme.toggled.connect(self._set_dark_theme)
        view_m.addAction(act_theme)
        self._act_dark = act_theme

        help_m = mb.addMenu("Справка")
        act_help = QAction("Руководство…", self)
        act_help.setShortcut("F1")
        act_help.triggered.connect(self._show_help)
        help_m.addAction(act_help)
        act_updates = QAction("Проверить обновления…", self)
        act_updates.triggered.connect(self._check_updates)
        help_m.addAction(act_updates)
        help_m.addSeparator()
        act_about = QAction("О программе", self)
        act_about.triggered.connect(self._about)
        help_m.addAction(act_about)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # Sidebar
        side = QFrame()
        side.setObjectName("card")
        side.setFixedWidth(220)
        sv = QVBoxLayout(side)
        title = QLabel("Модули")
        f = QFont()
        f.setPointSize(11)
        f.setBold(True)
        title.setFont(f)
        sv.addWidget(title)
        self._nav = QListWidget()
        self._nav.setSpacing(2)
        nav_help = {
            "analysis": "Ввод BR, генерация UC (UseCaseGenerator), дерево результатов.",
            "viz": "Диаграммы: последовательности, состояния, ER; экспорт PNG/SVG/PDF.",
            "matrix": "TraceabilityMatrix и PriorityManager, правка в таблице.",
            "convert": "Текст, user stories, функциональные требования (RequirementConverter).",
            "docs": "Сборка ТЗ по Вигерсу: экспорт DOCX и PDF.",
        }
        for key, label in [
            ("analysis", "Анализ требований"),
            ("viz", "Визуализация"),
            ("matrix", "Трассировка и приоритеты"),
            ("convert", "Конвертация форматов"),
            ("docs", "Документация ТЗ"),
        ]:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setToolTip(nav_help[key])
            self._nav.addItem(item)
        self._nav.currentRowChanged.connect(self._on_nav)
        sv.addWidget(self._nav, 1)
        splitter.addWidget(side)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._page_analysis())
        self._stack.addWidget(self._page_viz())
        self._stack.addWidget(self._page_matrix())
        self._stack.addWidget(self._page_convert())
        self._stack.addWidget(self._page_docs())
        splitter.addWidget(self._stack)
        splitter.setStretchFactor(1, 1)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Готово")
        self._apply_theme()
        self._nav.setCurrentRow(0)

    def _card_wrap(self, inner: QWidget) -> QWidget:
        w = QFrame()
        w.setObjectName("card")
        lay = QVBoxLayout(w)
        lay.addWidget(inner)
        return w

    def _page_analysis(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(10)
        hint = QLabel(
            "Введите бизнес-требования или загрузите текстовый файл. «Анализировать» формирует "
            "предпроектный разбор: контекст, стейкхолдеры, потребности, рынок, конкуренты (чек-листы), "
            "риски, пакеты работ, метрики и развёрнутые сценарии UC. Цифры по рынку и имена конкурентов "
            "нужно дополнить desk research — модель работает без доступа в интернет."
        )
        hint.setWordWrap(True)
        v.addWidget(hint)

        self._analysis_input = QTextEdit()
        self._analysis_input.setPlaceholderText("Бизнес-требования, цели, ограничения…")
        self._analysis_input.setMinimumHeight(200)
        self._analysis_input.textChanged.connect(self._on_business_changed)
        v.addWidget(self._analysis_input, 1)

        row = QHBoxLayout()
        btn_load = QPushButton("Загрузить файл…")
        btn_load.setObjectName("secondary")
        btn_load.setToolTip("Импорт .txt или .md")
        btn_load.clicked.connect(self._load_requirements_file)
        row.addWidget(btn_load)
        btn_run = QPushButton("Анализировать")
        btn_run.setToolTip("Запуск UseCaseGenerator")
        btn_run.clicked.connect(self._run_analysis)
        row.addWidget(btn_run)
        row.addStretch()
        v.addLayout(row)

        self._analysis_tree = QTreeWidget()
        self._analysis_tree.setHeaderLabels(["Поле", "Значение"])
        self._analysis_tree.setAlternatingRowColors(True)
        self._analysis_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._analysis_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        v.addWidget(self._analysis_tree, 2)
        return self._card_wrap(w)

    def _page_viz(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(
            QLabel(
                "Диаграммы строятся на основе последнего анализа (RequirementVisualizer). "
                "Экспорт: PNG, SVG, PDF."
            )
        )
        tabs = QTabWidget()
        for kind, title in [
            ("sequence", "Последовательности"),
            ("state", "Состояния"),
            ("er", "ER (концептуальная)"),
        ]:
            tab = QWidget()
            tv = QVBoxLayout(tab)
            lbl = QLabel(f"Вкладка «{title}»: нажмите «Обновить предпросмотр» после анализа.")
            lbl.setWordWrap(True)
            tv.addWidget(lbl)
            btn_row = QHBoxLayout()
            btn_prev = QPushButton("Обновить предпросмотр")
            btn_prev.setProperty("diagram_kind", kind)
            btn_prev.clicked.connect(self._refresh_diagram_tab)
            btn_row.addWidget(btn_prev)
            for ext in ("PNG", "SVG", "PDF"):
                b = QPushButton(f"Экспорт {ext}")
                b.setObjectName("secondary")
                b.setProperty("diagram_kind", kind)
                b.setProperty("export_fmt", ext.lower())
                b.clicked.connect(self._export_diagram)
                btn_row.addWidget(b)
            btn_row.addStretch()
            tv.addLayout(btn_row)
            note = QTextEdit()
            note.setReadOnly(True)
            note.setMaximumHeight(120)
            note.setPlaceholderText("Путь к последнему экспорту появится здесь.")
            note.setObjectName(f"viz_note_{kind}")
            tv.addWidget(note)
            tabs.addTab(tab, title)
        v.addWidget(tabs)
        return self._card_wrap(w)

    def _page_matrix(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(
            QLabel(
                "Матрица трассировки (TraceabilityMatrix): связь бизнес-требований с UC и тестами. "
                "Приоритизация — PriorityManager (MoSCoW + взвешенный балл)."
            )
        )
        row = QHBoxLayout()
        btn_sync = QPushButton("Импорт из анализа")
        btn_sync.setToolTip("Добавить строки из сгенерированных вариантов использования")
        btn_sync.clicked.connect(self._matrix_sync)
        row.addWidget(btn_sync)
        btn_add = QPushButton("Добавить строку")
        btn_add.setObjectName("secondary")
        btn_add.clicked.connect(self._matrix_add_row)
        row.addWidget(btn_add)
        btn_del = QPushButton("Удалить выбранную")
        btn_del.setObjectName("secondary")
        btn_del.clicked.connect(self._matrix_delete_row)
        row.addWidget(btn_del)
        btn_prio = QPushButton("Пересчитать приоритеты")
        btn_prio.clicked.connect(self._run_priorities)
        row.addWidget(btn_prio)
        row.addStretch()
        v.addLayout(row)

        self._matrix_table = QTableWidget(0, 6)
        self._matrix_table.setHorizontalHeaderLabels(
            ["BR-ID", "Описание", "User Req", "UC", "Тесты", "Статус"]
        )
        self._matrix_table.horizontalHeader().setStretchLastSection(True)
        self._matrix_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._matrix_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.SelectedClicked
        )
        self._matrix_table.itemChanged.connect(self._on_matrix_cell_changed)
        v.addWidget(self._matrix_table, 2)

        self._prio_table = QTableWidget(0, 4)
        self._prio_table.setHorizontalHeaderLabels(["ID / текст", "Группа", "Балл", "Обоснование"])
        self._prio_table.horizontalHeader().setStretchLastSection(True)
        v.addWidget(QLabel("Результаты приоритизации"))
        v.addWidget(self._prio_table, 1)
        return self._card_wrap(w)

    def _page_convert(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(
            QLabel("RequirementConverter: текст ↔ пользовательские истории ↔ функциональные требования.")
        )
        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("Исходный формат:"))
        self._src_fmt = QComboBox()
        self._src_fmt.addItems(["Текст", "Пользовательские истории", "Функциональные"])
        self._src_fmt.setToolTip("Входной формат")
        fmt_row.addWidget(self._src_fmt)
        fmt_row.addWidget(QLabel("Целевой формат:"))
        self._tgt_fmt = QComboBox()
        self._tgt_fmt.addItems(["Текст", "Пользовательские истории", "Функциональные"])
        fmt_row.addWidget(self._tgt_fmt)
        fmt_row.addStretch()
        v.addLayout(fmt_row)

        self._converter_input = QTextEdit()
        self._converter_input.setPlaceholderText("Вставьте требования…")
        self._converter_input.textChanged.connect(self._on_converter_changed)
        v.addWidget(self._converter_input, 1)

        btn = QPushButton("Конвертировать")
        btn.clicked.connect(self._run_convert)
        v.addWidget(btn)
        self._converter_output = QTextEdit()
        self._converter_output.setReadOnly(True)
        self._converter_output.setPlaceholderText("Результат конвертации…")
        v.addWidget(self._converter_output, 1)
        return self._card_wrap(w)

    def _page_docs(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(
            QLabel(
                "Полное ТЗ: разделы по Вигерсу (контекст, UC, трассировка, приоритеты). "
                "Экспорт в DOCX и PDF."
            )
        )
        row = QHBoxLayout()
        b1 = QPushButton("Экспорт DOCX…")
        b1.clicked.connect(lambda: self._export_spec("docx"))
        row.addWidget(b1)
        b2 = QPushButton("Экспорт PDF…")
        b2.setObjectName("secondary")
        b2.clicked.connect(lambda: self._export_spec("pdf"))
        row.addWidget(b2)
        row.addStretch()
        v.addLayout(row)
        prev = QTextEdit()
        prev.setReadOnly(True)
        prev.setPlaceholderText("Краткое превью будет после экспорта (путь к файлу).")
        self._doc_preview = prev
        v.addWidget(prev, 1)
        return self._card_wrap(w)

    def _on_nav(self, row: int) -> None:
        if row >= 0:
            self._stack.setCurrentIndex(row)

    def _apply_theme(self) -> None:
        qapp = QApplication.instance()
        if qapp:
            qapp.setStyleSheet(stylesheet_for_theme(self._dark))

    def _set_dark_theme(self, on: bool) -> None:
        self._dark = on
        self._apply_theme()

    # ——— slots ———
    def _on_business_changed(self) -> None:
        self._data.business_text = self._analysis_input.toPlainText()

    def _on_converter_changed(self) -> None:
        self._data.converter_input = self._converter_input.toPlainText()

    def _new_project(self) -> None:
        self._data = ProjectData()
        self._matrix = TraceabilityMatrix()
        self._reload_all_views()
        self.statusBar().showMessage("Новый проект")

    def _open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Открыть проект", "", "JSON (*.json)")
        if not path:
            return
        try:
            self._data = load_project(path)
            self._sync_matrix_from_data()
            self._reload_all_views()
            self._notify("Проект загружен", path)
            self.statusBar().showMessage(f"Открыто: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _save_project(self) -> None:
        if self._data.file_path:
            self._flush_matrix_to_data()
            try:
                save_project(self._data.file_path, self._data)
                self.statusBar().showMessage("Сохранено")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))
        else:
            self._save_project_as()

    def _save_project_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить проект", "", "JSON (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        self._flush_matrix_to_data()
        try:
            save_project(path, self._data)
            self._notify("Проект сохранён", path)
            self.statusBar().showMessage(f"Сохранено: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _load_requirements_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Загрузить документ", "", "Text (*.txt *.md);;All (*)")
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
            self._analysis_input.setPlainText(text)
            self._data.business_text = text
            self.statusBar().showMessage(f"Загружено: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _run_analysis(self) -> None:
        text = self._analysis_input.toPlainText()
        self._data.business_text = text
        self._data.analysis = self._generator.analyze(text)
        self._refresh_analysis_tree()
        self._notify("Анализ завершён", self._data.analysis.get("summary", ""))
        self.statusBar().showMessage("Анализ выполнен")

    def _refresh_analysis_tree(self) -> None:
        self._analysis_tree.clear()
        a = self._data.analysis
        if not a:
            return
        root = QTreeWidgetItem(["Результат анализа", ""])
        self._analysis_tree.addTopLevelItem(root)
        QTreeWidgetItem(root, ["Сводка", a.get("summary", "")])
        tags = a.get("domain_tags") or []
        if tags:
            QTreeWidgetItem(root, ["Теги домена", ", ".join(tags)])

        deep = a.get("deep_analysis") or {}
        if deep:
            deep_node = QTreeWidgetItem(root, ["Предпроектный анализ", ""])
            self._add_deep_section(deep_node, "Проблема и контекст", deep.get("problem_and_context"))
            self._add_deep_stakeholders(deep_node, deep.get("stakeholders"))
            self._add_deep_section(deep_node, "Потребности пользователей", deep.get("user_needs"))
            self._add_deep_section(deep_node, "Рынок и сегменты", deep.get("market_overview"))
            self._add_deep_section(deep_node, "Конкуренты и сравнение", deep.get("competitor_landscape"))
            self._add_deep_section(deep_node, "Позиционирование", deep.get("differentiation_and_positioning"))
            self._add_deep_section(deep_node, "Ограничения и комплаенс", deep.get("constraints_and_compliance"))
            self._add_deep_section(deep_node, "Риски и допущения", deep.get("risks_and_assumptions"))
            self._add_deep_section(deep_node, "Рекомендуемые пакеты работ", deep.get("recommended_work_packages"))
            self._add_deep_section(deep_node, "Открытые вопросы", deep.get("open_questions"))
            self._add_deep_section(deep_node, "Метрики успеха", deep.get("success_metrics"))

        actors = a.get("actors") or []
        QTreeWidgetItem(root, ["Акторы (UC)", ", ".join(actors)])
        uc_root = QTreeWidgetItem(root, ["Варианты использования", ""])
        for uc in a.get("use_cases") or []:
            u = QTreeWidgetItem(uc_root, [uc.get("id", ""), uc.get("name", "")])
            QTreeWidgetItem(u, ["Цель", uc.get("goal", "")])
            QTreeWidgetItem(u, ["Актор", uc.get("primary_actor", "")])
            pre = uc.get("preconditions") or []
            if pre:
                p_item = QTreeWidgetItem(u, ["Предусловия", ""])
                for line in pre:
                    QTreeWidgetItem(p_item, ["•", line])
            for s in uc.get("main_success") or []:
                QTreeWidgetItem(
                    u,
                    [
                        f"Шаг {s.get('order')}",
                        f"{s.get('actor_action')} → {s.get('system_response')}",
                    ],
                )
            post = uc.get("postconditions") or []
            if post:
                po = QTreeWidgetItem(u, ["Постусловия", ""])
                for line in post:
                    QTreeWidgetItem(po, ["•", line])
            ext = uc.get("extensions") or []
            if ext:
                ex = QTreeWidgetItem(u, ["Расширения / исключения", ""])
                for line in ext:
                    QTreeWidgetItem(ex, ["•", line])

        self._analysis_tree.expandToDepth(1)

    def _add_deep_section(self, parent: QTreeWidgetItem, title: str, items: list | None) -> None:
        if not items:
            return
        node = QTreeWidgetItem(parent, [title, ""])
        for line in items:
            if isinstance(line, str):
                QTreeWidgetItem(node, ["•", line])
            else:
                QTreeWidgetItem(node, ["•", str(line)])

    def _add_deep_stakeholders(self, parent: QTreeWidgetItem, rows: list | None) -> None:
        if not rows:
            return
        node = QTreeWidgetItem(parent, ["Стейкхолдеры", ""])
        for r in rows:
            if not isinstance(r, dict):
                continue
            label = r.get("role", "")
            detail = f"Интерес: {r.get('interest', '')}. Влияние: {r.get('influence', '')}."
            QTreeWidgetItem(node, [label, detail])

    def _refresh_diagram_tab(self) -> None:
        btn = self.sender()
        if not isinstance(btn, QPushButton):
            return
        kind = btn.property("diagram_kind")
        # Preview: export to temp and show path in note — simplified: message only
        self.statusBar().showMessage(f"Диаграмма «{kind}» обновлена (экспортируйте в файл для просмотра).")
        self._notify("Диаграмма", f"Тип {kind}: используйте экспорт PNG/SVG/PDF для файла.")

    def _export_diagram(self) -> None:
        btn = self.sender()
        if not isinstance(btn, QPushButton):
            return
        kind = str(btn.property("diagram_kind") or "sequence")
        fmt = str(btn.property("export_fmt") or "png")
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить диаграмму", "", f"{fmt.upper()} (*.{fmt});;All (*)"
        )
        if not path:
            return
        if not path.lower().endswith(f".{fmt}"):
            path += f".{fmt}"
        try:
            p = self._visualizer.export(kind, path, self._data.analysis)  # type: ignore[arg-type]
            self._notify("Экспорт диаграммы", str(p))
            self.statusBar().showMessage(f"Сохранено: {p}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))

    def _matrix_sync(self) -> None:
        n = self._matrix.sync_from_analysis(self._data.analysis)
        self._flush_matrix_to_data()
        self._refresh_matrix_table()
        self._notify("Трассировка", f"Добавлено строк: {n}")

    def _matrix_add_row(self) -> None:
        self._matrix.add_row("Новое бизнес-требование (отредактируйте)")
        self._flush_matrix_to_data()
        self._refresh_matrix_table()

    def _matrix_delete_row(self) -> None:
        r = self._matrix_table.currentRow()
        if r < 0:
            return
        it = self._matrix_table.item(r, 0)
        if not it:
            return
        rid = it.data(Qt.ItemDataRole.UserRole)
        if rid and self._matrix.remove_row(str(rid)):
            self._flush_matrix_to_data()
            self._refresh_matrix_table()

    def _on_matrix_cell_changed(self, item: QTableWidgetItem) -> None:
        row = item.row()
        col = item.column()
        rows = self._matrix.rows()
        if row >= len(rows):
            return
        mr = rows[row]
        text = self._matrix_table.item(row, 1)
        st = self._matrix_table.item(row, 5)
        if col == 1 and text:
            self._matrix.update_row(mr.row_id, business_text=text.text())
        if col == 5 and st:
            self._matrix.update_row(mr.row_id, status=st.text())
        self._flush_matrix_to_data()

    def _refresh_matrix_table(self) -> None:
        self._matrix_table.blockSignals(True)
        self._matrix_table.setRowCount(0)
        for mr in self._matrix.rows():
            r = self._matrix_table.rowCount()
            self._matrix_table.insertRow(r)
            id_item = QTableWidgetItem(mr.business_req_id)
            id_item.setData(Qt.ItemDataRole.UserRole, mr.row_id)
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._matrix_table.setItem(r, 0, id_item)
            self._matrix_table.setItem(r, 1, QTableWidgetItem(mr.business_text))
            self._matrix_table.setItem(r, 2, QTableWidgetItem(", ".join(mr.user_req_ids)))
            self._matrix_table.setItem(r, 3, QTableWidgetItem(", ".join(mr.use_case_ids)))
            self._matrix_table.setItem(r, 4, QTableWidgetItem(", ".join(mr.test_ids)))
            self._matrix_table.setItem(r, 5, QTableWidgetItem(mr.status))
        self._matrix_table.blockSignals(False)

    def _run_priorities(self) -> None:
        items: list[dict] = []
        for mr in self._matrix.rows():
            items.append({"id": mr.business_req_id, "text": mr.business_text})
        if not items:
            for line in self._data.business_text.splitlines():
                t = line.strip()
                if len(t) > 10:
                    items.append({"id": f"LINE-{len(items)}", "text": t})
        results = self._priority.prioritize_batch(items)
        self._data.priority_items = [
            {
                "id": p.requirement_id,
                "text": p.text,
                "band": p.band.value,
                "score": round(p.score, 1),
                "rationale": p.rationale,
            }
            for p in results
        ]
        self._refresh_priority_table()
        self._notify("Приоритизация", f"Обработано элементов: {len(results)}")

    def _refresh_priority_table(self) -> None:
        self._prio_table.setRowCount(0)
        for it in self._data.priority_items:
            r = self._prio_table.rowCount()
            self._prio_table.insertRow(r)
            self._prio_table.setItem(r, 0, QTableWidgetItem(f"{it.get('id', '')} {it.get('text', '')[:80]}"))
            self._prio_table.setItem(r, 1, QTableWidgetItem(str(it.get("band", ""))))
            self._prio_table.setItem(r, 2, QTableWidgetItem(str(it.get("score", ""))))
            self._prio_table.setItem(r, 3, QTableWidgetItem(str(it.get("rationale", ""))))

    def _fmt_map(self, idx: int) -> str:
        return ["text", "user_stories", "functional"][idx]

    def _run_convert(self) -> None:
        src = self._fmt_map(self._src_fmt.currentIndex())
        tgt = self._fmt_map(self._tgt_fmt.currentIndex())
        self._data.converter_source = src
        self._data.converter_target = tgt
        text = self._converter_input.toPlainText()
        self._data.converter_input = text
        out = self._converter.convert(text, src, tgt)  # type: ignore[arg-type]
        self._converter_output.setPlainText(out)

    def _export_spec(self, kind: str) -> None:
        self._flush_matrix_to_data()
        if kind == "docx":
            path, _ = QFileDialog.getSaveFileName(self, "DOCX", "", "Word (*.docx)")
            if not path:
                return
            if not path.lower().endswith(".docx"):
                path += ".docx"
            try:
                p = build_docx(self._data, path)
                self._doc_preview.setPlainText(str(p))
                self._notify("Документация", f"Сохранено: {p}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))
        else:
            path, _ = QFileDialog.getSaveFileName(self, "PDF", "", "PDF (*.pdf)")
            if not path:
                return
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            try:
                p = build_pdf(self._data, path)
                self._doc_preview.setPlainText(str(p))
                self._notify("Документация", f"Сохранено: {p}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def _notify(self, title: str, msg: str) -> None:
        self.statusBar().showMessage(f"{title}: {msg[:120]}", 8000)
        if self._tray:
            self._tray.showMessage(title, msg[:256], QSystemTrayIcon.MessageIcon.Information, 4000)
        QToolTip.showText(self.mapToGlobal(self.rect().center()), f"{title}\n{msg}", self, self.rect(), 3000)

    def _show_help(self) -> None:
        text = """
<h2>AI Analyst</h2>
<p><b>Анализ</b> — предпроектный разбор (контекст, стейкхолдеры, рынок, конкуренты, риски, метрики) и развёрнутые UC через <code>UseCaseGenerator</code>. Реальные данные о рынке и конкурентах добавьте вручную после desk research.</p>
<p><b>Визуализация</b> — диаграммы последовательностей, состояний и ER через <code>RequirementVisualizer</code>; экспорт PNG/SVG/PDF.</p>
<p><b>Трассировка</b> — <code>TraceabilityMatrix</code>, редактирование в таблице, импорт из анализа; <code>PriorityManager</code> для приоритетов.</p>
<p><b>Конвертация</b> — <code>RequirementConverter</code> между текстом, user stories и FR.</p>
<p><b>Документация</b> — сборка ТЗ по структуре Вигерса в DOCX/PDF.</p>
<p>Горячие клавиши: Ctrl+S — сохранить, F1 — эта справка. Автосохранение каждые ~90 с в каталог данных приложения.</p>
"""
        box = QMessageBox(self)
        box.setWindowTitle("Справка")
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(text)
        box.exec()

    def _check_updates(self) -> None:
        ok, msg, url = check_for_updates()
        if ok and url:
            r = QMessageBox.question(
                self,
                "Обновление",
                msg + "\nОткрыть страницу загрузки?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if r == QMessageBox.StandardButton.Yes:
                webbrowser.open(url)
        else:
            QMessageBox.information(self, "Обновления", msg)

    def _about(self) -> None:
        QMessageBox.about(
            self,
            "О программе",
            f"AI Analyst v{__version__}\n"
            "Десктопное приложение для черновиков ТЗ по методологии К. Вигерса.\n"
            "Python, PyQt6.",
        )

    def closeEvent(self, event) -> None:
        self._do_autosave()
        super().closeEvent(event)
