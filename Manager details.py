import sys
import sqlite3
import shutil
import os
import logging
import zipfile
import tempfile
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

# Настройка логгера
if not os.path.exists('Logs'):
    os.makedirs('Logs')

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'Logs/errors_{datetime.now().strftime("%Y-%m-%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Создаем папки для данных
if not os.path.exists('images'):
    os.makedirs('images')

class Database:
    def __init__(self):
        """Класс для работы с базой данных"""
        self.conn = sqlite3.connect('details.db')
        self.create_table()

    def create_table(self):
        """Создание таблицы деталей"""
        query = '''
        CREATE TABLE IF NOT EXISTS details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            area TEXT,
            image_path TEXT
        )
        '''
        self.conn.execute(query)
        self.conn.commit()

    def backup(self, backup_path):
        """Создание резервной копии базы данных и изображений"""
        try:
            # Создаем временную папку
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Копируем базу данных
                db_backup_path = os.path.join(tmp_dir, 'details.db')
                shutil.copyfile('details.db', db_backup_path)
                
                # Копируем папку с изображениями
                images_backup_dir = os.path.join(tmp_dir, 'images')
                if os.path.exists('images'):
                    shutil.copytree('images', images_backup_dir)
                
                # Создаем ZIP-архив
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                backup_file = os.path.join(backup_path, f'backup_{timestamp}.zip')
                
                with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(tmp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, tmp_dir)
                            zipf.write(file_path, arcname)
                            
                return backup_file
                
        except Exception as e:
            logger.error(f"Ошибка создания бэкапа: {str(e)}")
            raise

class DetailDialog(QDialog):
    def __init__(self, parent=None, detail=None):
        super().__init__(parent)
        self.setWindowTitle('Добавить деталь' if not detail else 'Редактировать деталь')
        self.setFixedSize(400, 300)

        # Настройка валидатора для числового ввода
        self.validator = QDoubleValidator(0.0, 9999.0, 2)
        self.validator.setLocale(QLocale(QLocale.English))  # Важное изменение
        self.validator.setNotation(QDoubleValidator.StandardNotation)

        # Создание элементов формы
        self.name_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.area_edit = QLineEdit()
        self.area_edit.setValidator(self.validator)
        self.image_path_edit = QLineEdit()
        
        # Обработчик изменения текста
        self.area_edit.textChanged.connect(self.fix_decimal_input)

        # Создание элементов формы
        self.name_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.area_edit = QLineEdit()
        self.area_edit.setValidator(self.validator)
        self.image_path_edit = QLineEdit()
        
        # Кнопка выбора изображения
        browse_btn = QPushButton('Обзор...')
        browse_btn.clicked.connect(self.browse_image)
        
        # Кнопки OK/Cancel
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Компоновка элементов
        layout = QFormLayout()
        layout.addRow('Наименование:', self.name_edit)
        self.name_edit.setPlaceholderText('Детали')
        layout.addRow('Описание:', self.description_edit)
        self.description_edit.setPlaceholderText('Или заметки')
        layout.addRow('Площадь (дм²):', self.area_edit)
        self.area_edit.setPlaceholderText('0.0')
        layout.addRow('Изображение:', self.image_path_edit)
        self.image_path_edit.setPlaceholderText('Путь к изображению/фото...')
        layout.addRow(browse_btn)
        layout.addRow(button_box)
        
        self.setLayout(layout)

        # Заполнение данных при редактировании
        if detail:
            self.name_edit.setText(detail['name'])
            self.description_edit.setText(detail['description'])
            self.area_edit.setText(f"{float(detail['area']):.2f}")
            self.image_path_edit.setText(detail['image_path'])

    def fix_decimal_input(self, text):
        """Автоматическая корректировка ввода"""
        new_text = text.replace(',', '.').lstrip('0')
        if new_text != text:
            self.area_edit.setText(new_text)

    def browse_image(self):
        """Выбор изображения и копирование в папку images"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, 
            'Выберите изображение', 
            '', 
            'Images (*.png *.jpg *.jpeg)'
        )
        if file_name:
            new_path = os.path.join('images', os.path.basename(file_name))
            shutil.copyfile(file_name, new_path)
            self.image_path_edit.setText(new_path)

class MainWindow(QMainWindow):
    def __init__(self):
        """Главное окно приложения"""
        super().__init__()
        self.db = Database()
        self.init_ui()
        self.load_details()

    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle('Manager details v0.2 (Бета)')
        self.setGeometry(100, 100, 1200, 800)
        
        # Установка базового шрифта
        font = QFont()
        font.setPointSize(10)  # Увеличенный размер шрифта
        QApplication.setFont(font)
        
        # Создание вкладок
        self.tabs = QTabWidget()
        self.main_tab = QWidget()
        self.about_tab = QWidget()
        
        self.init_main_tab()
        self.init_about_tab()
        
        self.tabs.addTab(self.main_tab, 'Детали')
        self.tabs.addTab(self.about_tab, 'О программе')
        self.setCentralWidget(self.tabs)
        
        # Настройка меню
        menubar = self.menuBar()
        file_menu = menubar.addMenu('Файл')
        backup_action = QAction('Создать бэкап', self)
        backup_action.triggered.connect(self.create_backup)
        file_menu.addAction(backup_action)

    def init_main_tab(self):
        """Инициализация основной вкладки"""
        # Поисковая строка
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('Поиск по названию...')
        self.search_edit.textChanged.connect(self.load_details)
        
        # Стиль для кнопок
        btn_style = '''
            QPushButton {
                background-color: #5c5e61;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #323940; }
        '''
        
        # Кнопки управления
        add_btn = QPushButton('Добавить')
        add_btn.setStyleSheet(btn_style)
        add_btn.clicked.connect(self.add_detail)
        
        edit_btn = QPushButton('Редактировать')
        edit_btn.setStyleSheet(btn_style)
        edit_btn.clicked.connect(self.edit_detail)
        
        delete_btn = QPushButton('Удалить')
        delete_btn.setStyleSheet(btn_style)
        delete_btn.clicked.connect(self.delete_detail)
        
        # Список деталей с прокруткой
        self.details_list = QListWidget()
        self.details_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.details_list.itemClicked.connect(self.show_detail)
        
        # Область просмотра с разделителем
        splitter = QSplitter(Qt.Horizontal)
        
        # Левая панель
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.details_list)
        left_widget.setLayout(left_layout)
        
        # Правая панель
        right_widget = QWidget()
        self.detail_image = QLabel()
        self.detail_image.setAlignment(Qt.AlignCenter)
        self.detail_name = QLabel()
        self.detail_description = QTextBrowser()
        self.detail_area = QLabel()
        
        # Компоновка правой панели
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.detail_image)
        right_layout.addWidget(self.detail_name)
        right_layout.addWidget(self.detail_description)
        right_layout.addWidget(self.detail_area)
        right_widget.setLayout(right_layout)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 400])
        
        # Основная компоновка
        main_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.search_edit)
        top_layout.addWidget(add_btn)
        top_layout.addWidget(edit_btn)
        top_layout.addWidget(delete_btn)
        
        main_layout.addLayout(top_layout)
        main_layout.addWidget(splitter)
        self.main_tab.setLayout(main_layout)

    def init_about_tab(self):
        """Инициализация вкладки 'О программе' с рамками и блоками"""
        # Основной контейнер
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)  # Отступы от краев

        # Стиль для рамок
        frame_style = """
            QFrame {
                border: 2px solid #5c5e61;
                border-radius: 5px;
                padding: 5px;
                margin: 5px;
                background-color: #f8f9fa;
            }
            QLabel {
                font-size: 16px;
                color: #333;
            }
        """

        # Блок основной информации
        about_frame = QFrame()
        about_frame.setStyleSheet(frame_style)
        about_text = """<b>Менеджер для учета деталей электрохимической обработки</b>

        <p><u>Основные функции:</u></p>
        <ul>
            <li>Учет площадей деталей с изображениями</li>
            <li>Реализована система резервного копирования</li>
            <li>Система поиска</li>
            <li>Система добавления, редактирования, удаления деталей</li>
        </ul>

        <p><b>Автор:</b> Mertan (Александр)<br>
        <b>Эл. почта:</b> crossfiree2014@mail.ru<br>
        <b>Лицензия:</b> GNU GPL v3.0</p>"""

        about_label = QLabel(about_text)
        about_label.setAlignment(Qt.AlignLeft)
        about_layout = QVBoxLayout(about_frame)
        about_layout.addWidget(about_label)

        # Блок обновлений
        updates_frame = QFrame()
        updates_frame.setStyleSheet(frame_style)
        updates_text = """<b>История обновлений</b>

                <p><u>В разработке:</u></p>
        <ul>
            <li>Активная стадия бета теста</li>
        </ul>

        <p><u>Версия 0.2 (30.03.2025):</u></p>
        <ul>
            <li>Добавлена система резервного копирования</li>
            <li>Улучшен интерфейс управления деталями</li>
        </ul>

        <p><u>Версия 0.1 (29.03.2025):</u></p>
        <ul>
            <li>Полный редизайн интерфейса</li>
            <li>Добавлена система поиска</li>
        </ul>"""

        updates_label = QLabel(updates_text)
        updates_label.setAlignment(Qt.AlignLeft)
        updates_layout = QVBoxLayout(updates_frame)
        updates_layout.addWidget(updates_label)

        # Добавляем блоки в основной макет
        layout.addWidget(about_frame)
        layout.addWidget(updates_frame)
        layout.addStretch()  # Добавляем растягивающееся пространство

        # Настройка шрифта
        font = QFont()
        font.setPointSize(12)
        about_label.setFont(font)
        updates_label.setFont(font)
    
        self.about_tab.setLayout(layout)

    def create_backup(self):
        """Создание резервной копии базы данных"""
        path = QFileDialog.getExistingDirectory(self, 'Выберите папку для бэкапа')
        if path:
            self.db.backup(path)
            QMessageBox.information(self, 'Успех', 'Бэкап создан успешно!')

    def load_details(self, search_text=''):
        """Загрузка списка деталей"""
        self.details_list.clear()
        query = 'SELECT * FROM details WHERE name LIKE ?'
        cursor = self.db.conn.execute(query, (f'%{search_text}%',))
        for row in cursor:
            item = QListWidgetItem(row[1])
            item.setData(Qt.UserRole, {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'area': row[3],
                'image_path': row[4]
            })
            self.details_list.addItem(item)

    def show_detail(self):
        """Отображение выбранной детали"""
        item = self.details_list.currentItem()
        if item:
            data = item.data(Qt.UserRole)
            pixmap = QPixmap(data['image_path'])
            self.detail_image.setPixmap(pixmap.scaled(400, 400, Qt.KeepAspectRatio))
            self.detail_name.setText(data['name'])
            self.detail_description.setText(data['description'])
            self.detail_area.setText(f"Площадь: {float(data['area']):.2f} дм²")

    def add_detail(self):
        """Добавление новой детали"""
        dialog = DetailDialog(self)
        if dialog.exec_():
            try:
                # Валидация данных
                area = float(dialog.area_edit.text().strip())
                image_path = dialog.image_path_edit.text()
                
                if not os.path.exists(image_path):
                    raise FileNotFoundError("Файл изображения не найден")
                
                # Сохранение в БД
                self.db.conn.execute('''
                    INSERT INTO details (name, description, area, image_path)
                    VALUES (?, ?, ?, ?)
                ''', (
                    dialog.name_edit.text().strip(),
                    dialog.description_edit.toPlainText().strip(),
                    area,
                    image_path
                ))
                self.db.conn.commit()
                self.load_details()
                
            except Exception as e:
                QMessageBox.warning(self, 'Ошибка', str(e))

    def edit_detail(self):
        """Редактирование существующей детали"""
        item = self.details_list.currentItem()
        if item:
            data = item.data(Qt.UserRole)
            dialog = DetailDialog(self, data)
            if dialog.exec_():
                try:
                    # Валидация данных
                    area = float(dialog.area_edit.text().strip())
                    image_path = dialog.image_path_edit.text()
                    
                    if not os.path.exists(image_path):
                        raise FileNotFoundError("Файл изображения не найден")
                    
                    # Обновление записи
                    self.db.conn.execute('''
                        UPDATE details SET
                            name = ?,
                            description = ?,
                            area = ?,
                            image_path = ?
                        WHERE id = ?
                    ''', (
                        dialog.name_edit.text().strip(),
                        dialog.description_edit.toPlainText().strip(),
                        area,
                        image_path,
                        data['id']
                    ))
                    self.db.conn.commit()
                    self.load_details()
                    
                except Exception as e:
                    QMessageBox.warning(self, 'Ошибка', str(e))

    def delete_detail(self):
        """Удаление детали с удалением изображения"""
        item = self.details_list.currentItem()
        if item:
            data = item.data(Qt.UserRole)
            confirm = QMessageBox.question(
                self, 
                'Удалить', 
                'Вы уверены, что хотите удалить эту деталь?'
            )
            
            if confirm == QMessageBox.Yes:
                try:
                    # Удаление изображения
                    if os.path.exists(data['image_path']):
                        os.remove(data['image_path'])
                    
                    # Удаление из БД
                    self.db.conn.execute(
                        'DELETE FROM details WHERE id = ?', 
                        (data['id'],)
                    )
                    self.db.conn.commit()
                    self.load_details()
                    
                except Exception as e:
                    QMessageBox.warning(self, 'Ошибка', str(e))

    def excepthook(self, exctype, value, traceback):
        """Обработчик неотловленных исключений"""
        logger.exception("Uncaught exception", exc_info=(exctype, value, traceback))
        QMessageBox.critical(
            self, 
            'Критическая ошибка',
            f'Произошла непредвиденная ошибка:\n{str(value)}'
        )

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Установка шрифта для всего приложения
    font = QFont()
    font.setPointSize(18)
    app.setFont(font)
    
    window = MainWindow()
    sys.excepthook = window.excepthook
    window.show()
    sys.exit(app.exec_())