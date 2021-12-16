# This Python file uses the following encoding: utf-8
import os
import sys
from types import TracebackType
from typing import Dict, List
import logging
import requests
from PySide6.QtWidgets import (
    QMainWindow, QCheckBox, QFileDialog, QProgressBar,
    QPushButton, QVBoxLayout, QWidget, QGridLayout, QGroupBox, QLabel,
    QLineEdit, QMessageBox, QLayout, QApplication, QTabWidget)
from PySide6.QtCore import (QObject, Signal, QThread, Qt, QThreadPool)
from PySide6.QtGui import QFont, QIcon
from exceptions import InvalidCredentials, InvalidLoginParameters
from qt_custom_widget import PyToggle, PyLogOutput, PyCheckableComboBox
from ceiba import Ceiba
from course import Course
import strings
        
def exception_handler(type, value, tb):
    logging.getLogger().error("{}: {}".format(type.__name__, str(value)))
    
class CeibaWorker(QObject):
    finished = Signal()
    success = Signal()
    failed = Signal()
    progress = Signal(int)

    def __init__(self, ceiba: Ceiba):
        QObject.__init__(self)
        self.ceiba = ceiba

    def login(self):
        try:
            self.ceiba.login()
        except (InvalidCredentials, InvalidLoginParameters):
            self.failed.emit()
        else:
            self.success.emit()
        self.finished.emit()

    def download_courses(self):
        try:
            if len(self.path) == 0:
                raise FileNotFoundError
            os.makedirs(self.path, exist_ok=True)
        except FileNotFoundError:
            logging.error('路徑錯誤！請檢查路徑是否空白與錯誤！')
            self.failed.emit()
     
        for course in self.courses:
            if course.cname in self.cname_filter_list:
                logging.info(strings.course_download_info.format(course.cname))
                course.download(
                    self.path, self.session, self.modules_filter_list, self.progress)
                logging.info(strings.course_finish_info.format(course.cname))
        self.success.emit()
        self.finished.emit()

    def set_download_param(self, courses: List[Course], path: str, session: requests.Session, cname_filter_list, modules_filter_list):
        self.courses = courses
        self.path = path
        self.session = session
        self.cname_filter_list = cname_filter_list
        self.modules_filter_list = modules_filter_list

class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Ceiba Downloader by Jameshwc")
        self.setWindowIcon(QIcon('ceiba.ico'))

        self.create_login_group_box()
        self.create_courses_group_box()
        self.create_status_group_box()
        self.setCentralWidget(QWidget(self))

        main_layout = QGridLayout(self.centralWidget())
        main_layout.addWidget(self.login_group_box, 0, 0)
        main_layout.addWidget(self.courses_group_box, 1, 0)
        main_layout.addWidget(self.status_group_box, 2, 0)
        main_layout.setRowStretch(1, 1)
        # main_layout.setRowStretch(2, 1)
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 1)

    def create_login_group_box(self):
        self.login_group_box = QGroupBox("使用者")

        username_label = QLabel('帳號 (學號):')
        self.username_edit = QLineEdit('')

        password_label = QLabel('密碼 :')
        self.password_edit = QLineEdit('')
        self.password_edit.setEchoMode(QLineEdit.Password)

        self.login_button = QPushButton('登入')
        self.login_button.clicked.connect(self.login)

        self.method_toggle = PyToggle(width=80)

        def switch_method():
            if self.method_toggle.isChecked():
                username_label.setText('Cookie [user]:')
                password_label.setText('Cookie [PHPSESSID]:')
            else:
                username_label.setText('帳號 (學號):')
                password_label.setText('密碼 :')

        self.method_toggle.clicked.connect(switch_method)

        method_left_label = QLabel('登入方式：帳號 / 密碼（不安全）')
        method_right_label = QLabel('cookies （安全）')

        self.login_layout = QGridLayout()

        self.login_layout.addWidget(method_left_label, 0, 0, 1, 1)
        self.login_layout.addWidget(self.method_toggle, 0, 1, 1, 1)
        self.login_layout.addWidget(method_right_label, 0, 2, 1, 1)

        self.login_layout.addWidget(username_label, 1, 0)
        self.login_layout.addWidget(self.username_edit, 1, 1, 1, 2)
        self.login_layout.addWidget(password_label, 2, 0)
        self.login_layout.addWidget(self.password_edit, 2, 1, 1, 2)
        self.login_layout.addWidget(self.login_button, 3, 1, 1, 2)
        self.login_layout.setColumnStretch(0, 0)
        self.login_layout.setColumnStretch(1, 1)
        self.login_group_box.setLayout(self.login_layout)

    def create_courses_group_box(self):
        self.courses_group_box = QGroupBox("課程")
        self.courses_group_box.setDisabled(True)

    def create_status_group_box(self):
        self.status_group_box = QGroupBox("狀態")
        self.status_layout = QGridLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)

        self.log_output = PyLogOutput(self)
        self.log_output.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'))
            
        logging.getLogger().addHandler(self.log_output)
        logging.getLogger().setLevel(logging.INFO)
        sys.excepthook = exception_handler

        self.status_layout.addWidget(self.log_output.widget)
        self.status_layout.addWidget(self.progress_bar)
        self.status_group_box.setLayout(self.status_layout)

    def login(self):

        if self.method_toggle.isChecked():
            self.ceiba = Ceiba(cookie_user=self.username_edit.text(
            ), cookie_PHPSESSID=self.password_edit.text())
        else:
            self.ceiba = Ceiba(username=self.username_edit.text(),
                               password=self.password_edit.text())

        def fail_handler():
            if self.method_toggle.isChecked():
                QMessageBox.critical(
                    self, '登入失敗！', '登入失敗！請檢查 Cookies 有沒有輸入正確！', QMessageBox.Retry)
            else:
                QMessageBox.critical(
                    self, '登入失敗！', '登入失敗！請檢查帳號（學號）與密碼輸入是否正確！', QMessageBox.Retry)
            self.login_button.setEnabled(True)
            self.password_edit.clear()
        self.login_thread = QThread()
        self.worker = CeibaWorker(self.ceiba)
        self.worker.moveToThread(self.login_thread)
        self.login_thread.started.connect(self.worker.login)
        self.worker.failed.connect(fail_handler)
        self.worker.success.connect(self.after_login_successfully)
        self.worker.finished.connect(self.login_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.login_thread.finished.connect(self.login_thread.deleteLater)
        self.login_thread.start()
        self.login_button.setDisabled(True)

    def after_login_successfully(self):
        for i in reversed(range(self.login_layout.count())):
            self.login_layout.itemAt(i).widget().setParent(None)

        welcome_label = QLabel(self.ceiba.student_name + "，歡迎你！")
        welcome_label.setFont(QFont('', 32))
        self.login_layout.addWidget(welcome_label, 0, 0)
        self.login_group_box.setLayout(self.login_layout)

        # TODO: [low priority] it can be handled in multi-thread
        courses = self.ceiba.get_courses_list()
        self.fill_course_group_box(courses)

    def fill_course_group_box(self, courses: List[Course]):
        self.courses_group_box.setDisabled(False)

        courses_main_layout = QGridLayout()
        courses_by_semester_layouts: Dict[str, QLayout] = {}
        self.courses_checkboxes: List[QCheckBox] = []

        for course in courses:
            if course.semester not in courses_by_semester_layouts:
                layout = QGridLayout()
                courses_by_semester_layouts[course.semester] = layout
            checkbox = QCheckBox("&" + course.cname)
            self.courses_checkboxes.append(checkbox)
            courses_by_semester_layouts[course.semester].addWidget(checkbox)

        tabWidget = QTabWidget()
        for semester in courses_by_semester_layouts:
            semester_widget = QWidget()
            semester_widget.setLayout(courses_by_semester_layouts[semester])
            tabWidget.addTab(semester_widget, "&" + semester)

        options_and_download_groupbox = QGroupBox()
        options_and_download_layout = QGridLayout()
        self.download_button = QPushButton('下載')
        self.download_button.clicked.connect(self.download)

        def click_all_courses_checkbox(state):
            for checkbox in self.courses_checkboxes:
                if state == Qt.Checked:
                    checkbox.setCheckState(Qt.Checked)
                elif state == Qt.Unchecked:
                    checkbox.setCheckState(Qt.Unchecked)

        check_all_courses_button = QCheckBox('勾選全部')
        check_all_courses_button.stateChanged.connect(
            click_all_courses_checkbox)

        self.download_item_combo_box = PyCheckableComboBox()
        self.download_item_combo_box.setPlaceholderText('<---點我展開--->')
        for item_name in Course.cname_map.values():
            self.download_item_combo_box.addItem(item_name)
        self.download_item_combo_box.setCurrentIndex(-1)
        download_item_label = QLabel('下載項目：')
        download_item_layout = QVBoxLayout()
        download_item_layout.addWidget(download_item_label)
        download_item_layout.addWidget(self.download_item_combo_box)

        filepath_label = QLabel('存放路徑：')
        self.filepath_line_edit = QLineEdit()
        file_browse_button = QPushButton('瀏覽')
        file_browse_button.clicked.connect(self.get_save_directory)

        options_and_download_layout.addWidget(check_all_courses_button, 0, 0)
        options_and_download_layout.addWidget(download_item_label, 0, 1)
        options_and_download_layout.addWidget(
            self.download_item_combo_box, 0, 2)
        options_and_download_layout.addWidget(filepath_label, 1, 0)
        options_and_download_layout.addWidget(self.filepath_line_edit, 1, 1)
        options_and_download_layout.addWidget(file_browse_button, 1, 2)
        options_and_download_layout.addWidget(self.download_button, 2, 0)
        options_and_download_groupbox.setLayout(options_and_download_layout)

        courses_main_layout.addWidget(tabWidget, 0, 0)
        courses_main_layout.addWidget(options_and_download_groupbox, 1, 0)

        self.courses_group_box.setLayout(courses_main_layout)

    def download(self):
        items = []
        for i in range(self.download_item_combo_box.count()):
            if self.download_item_combo_box.itemChecked(i):
                module_cname = self.download_item_combo_box.model().item(i, 0).text()
                for ename, cname in Course.cname_map.items():
                    if cname == module_cname:
                        items.append(ename)
                        break

        cname_list = [x.text()[1:]
                      for x in self.courses_checkboxes if x.isChecked()]

        self.progress_bar.setMaximum(len(cname_list) * len(items))
        self.download_thread = QThread()
        self.worker = CeibaWorker(self.ceiba)
        self.worker.set_download_param(self.ceiba.courses, self.filepath_line_edit.text(),
                self.ceiba.sess, cname_list, items,)
        self.worker.moveToThread(self.download_thread)
        self.download_thread.started.connect(self.worker.download_courses)
        self.worker.progress.connect(self.update_progressbar)
        self.worker.finished.connect(self.download_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.after_download_successfully)
        self.download_thread.finished.connect(self.download_thread.deleteLater)
        self.download_thread.start()
        self.download_button.setDisabled(True)

    def get_save_directory(self):
        filepath = QFileDialog.getExistingDirectory(self)
        self.filepath_line_edit.setText(filepath)

    def after_download_successfully(self):
        QMessageBox.information(self, '下載完成！', '下載完成！', QMessageBox.Ok) # TODO: open directory
        self.download_button.setEnabled(True)
        self.progress_bar.reset()

    def update_progressbar(self, add_value: int):
        self.progress_bar.setValue(self.progress_bar.value() + add_value)

if __name__ == "__main__":
    
    app = QApplication([])

    widget = MyApp()
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec())
