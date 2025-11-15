# main.py
import sys
import os
import time
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QLabel, QTextEdit,
    QPushButton, QToolBar, QStatusBar, QMessageBox, QLineEdit, QFormLayout, QFileDialog, QInputDialog
)
from PySide6.QtCore import Qt, QSize, Slot, QObject, QThread, Signal

from condaEnvManager import CondaEnvManager
from mysqlcontroller import MySQLController
import mysqlcontroller

# 高耗时后台任务类 CondaWorker 
class CondaWorker(QObject):
    """
    在子线程中执行，用来执行 conda 创建/删除环境操作，安装/卸载包操作
    """
    finished = Signal(bool, str)  # 定义信号 finished(是否成功, 环境名/包名)

    # 构造函数，传入conda安装路径、环境名、Python版本、操作类型
    def __init__(self, conda_path, env_name, py_version=None, operation=None, package_name=None, package_version=None):
        super().__init__()
        self.conda_path = conda_path
        self.env_name = env_name
        self.py_version = py_version
        self.operation = operation
        self.package_name = package_name
        self.package_version = package_version

    # 运行函数
    def run(self):
        """
        根据传入的操作类型执行对应指令
        """
        conda_manager = CondaEnvManager(self.conda_path)    # 创建CondaEnvManager对象
        success = False
        
        if self.operation == 'create':       # 创建环境
            success = conda_manager.create_env(self.env_name, self.py_version)
            result_name = self.env_name
        elif self.operation == 'remove':     # 删除环境
            success = conda_manager.remove_env(self.env_name)
            result_name = self.env_name
        elif self.operation == 'install':    # 安装包
            success = conda_manager.install_package(self.env_name, self.package_name, self.package_version)
            result_name = self.package_name
        elif self.operation == 'uninstall':  # 卸载包
            success = conda_manager.uninstall_package(self.env_name, self.package_name)
            result_name = self.package_name
        else:
            success = False
            result_name = ""

        self.finished.emit(success, result_name)  # 运行完成，发送信号


# 主窗口类
class CondaEnvManagerGUI(QMainWindow):
    """
    Miniconda 环境管理器主窗口类
    提供图形界面用于查看、创建、删除、管理 Conda 环境
    并展示环境列表及基本信息
    """

    def __init__(self):
        """
        初始化主窗口界面布局及组件——包括左侧环境树形视图、右侧详情标签页、顶部工具栏和底部状态栏
        读取并打印初始信息
        """
        super().__init__()

        # 初始化界面布局
        self.UIConstruct()

        # 禁用部分按钮（初始无选中环境）
        self.update_button_states()

        # === 底部状态栏 ===
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

        # 全局变量
        self.conda_path = None                      # str，存储conda安装路径
        self.envdir = {}                            # dict，存储环境信息 —— key: 环境名称, value: 环境信息
        self.python_version = {}                    # dict，存储Python版本 —— key:环境名称, value:Python版本
        self.running_dialog = None                  # 用于“运行中”弹窗
        self.sql_controller = MySQLController()     # 数据库控制对象
        self.read_DataBase = False                  # bool，判断是否要读数据库 —— 数据不存在或落后，就设定False
        
        # 判断是否为第一次运行
        if mysqlcontroller.env_table_exist() == False:
            self.read_DataBase = False
            mysqlcontroller.create_databaseANDTable()   # 创建空数据库和表
        else:
            self.read_DataBase = True

        # 初始化树
        self.on_refresh_envsList()

    # 界面布局
    def UIConstruct(self):
        """
        初始化界面布局,并进行信号与槽的连接
        """
        # 主窗口设置
        self.setWindowTitle("Miniconda 环境管理器")
        self.resize(1000, 700)

        # 中央部件 —— 用于放置布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # === 左侧：环境树形列表 ===
        self.env_tree = QTreeWidget()
        self.env_tree.setHeaderLabels(["环境名称", "Python 版本", "路径"])
        self.env_tree.setColumnWidth(0, 180)
        self.env_tree.setColumnWidth(1, 100)
        self.env_tree.setAlternatingRowColors(True)
        self.env_tree.setSelectionMode(QTreeWidget.SingleSelection)
        self.env_tree.itemSelectionChanged.connect(self.on_env_selected_showDetail)
        main_layout.addWidget(self.env_tree, 2)

        # === 右侧：搜索栏和详情面板 ===
        # 创建右侧的垂直布局
        right_layout = QVBoxLayout()

        # 创建搜索栏区域
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("请输入包名进行搜索..")
        self.search_button = QPushButton("搜索")
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)

        # 连接搜索功能
        self.search_button.clicked.connect(self.on_search_pak)
        self.search_input.returnPressed.connect(self.on_search_pak)  # 支持回车搜索

        # 添加搜索栏到右侧布局
        right_layout.addLayout(search_layout)

        # 创建标签页控件
        self.detail_tabs = QTabWidget()
        right_layout.addWidget(self.detail_tabs)

        # 将右侧布局添加到主布局
        main_layout.addLayout(right_layout, 3)

        # 标签页1：基本信息
        self.info_widget = QWidget()
        info_layout = QFormLayout(self.info_widget)
        self.name_label = QLabel()
        self.path_label = QLabel()
        self.python_version_label = QLabel()
        self.introduction_label = QLabel()
        info_layout.addRow("环境名称:", self.name_label)
        info_layout.addRow("路径:", self.path_label)
        info_layout.addRow("Python 版本:", self.python_version_label)
        info_layout.addRow("简介:", self.introduction_label)
        self.detail_tabs.addTab(self.info_widget, "基本信息")

        # 标签页2：包列表（只读）
        self.packages_text = QTextEdit()
        self.packages_text.setReadOnly(True)
        self.detail_tabs.addTab(self.packages_text, "已安装包")

        # 标签页3：操作日志（只读）
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.detail_tabs.addTab(self.log_text, "操作日志")

        # === 顶部工具栏 ===
        toolbar = QToolBar("操作")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)

        self.refresh_btn = QPushButton("刷新数据库和列表")
        self.create_btn = QPushButton("创建环境")
        self.remove_btn = QPushButton("删除环境")
        self.installPAK_btn = QPushButton("安装包")
        self.uninstallAPK_btn = QPushButton("卸载包")

        self.refresh_btn.clicked.connect(self.on_force_refresh_dataBase)
        self.create_btn.clicked.connect(self.on_create_env)
        self.remove_btn.clicked.connect(self.on_remove_env)
        self.installPAK_btn.clicked.connect(self.on_install_package)
        self.uninstallAPK_btn.clicked.connect(self.on_uninstall_package)

        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.create_btn)
        toolbar.addWidget(self.remove_btn)
        toolbar.addWidget(self.installPAK_btn)
        toolbar.addWidget(self.uninstallAPK_btn)

    # 显示运行窗口
    def show_running_dialog(self, operation):
        """
        显示“运行中”的对话框
        
        参数：
            operation: str 对象，操作类型
        """
        self.running_dialog = QMessageBox(
            QMessageBox.Information,
            "请稍候", 
            f"正在进行 {operation} 操作",
            QMessageBox.NoButton,
            self
        )
        self.running_dialog.setModal(True)  # 设置为模态对话框
        self.running_dialog.show()          # 进行模态运行
        QApplication.processEvents()        # 立即处理该请求

    # 关闭运行窗口
    def close_running_dialog(self):
        """
        关闭运行中的对话框
        """
        if self.running_dialog:
            self.running_dialog.close()
            self.running_dialog = None

    # 加载环境数据
    def load_envs_inf(self):
        """
        加载环境数据
        先让用户选择conda的地址，然后检查是否读取数据库的标志 —— True则从数据库读取，False则调用 conda 命令获取真实环境数据字典，然后将数据保存到数据库中
        
        返回值：
            bool: 获取成功返回True，否则返回False
        """
        # 开始运行时，获取conda安装路径
        target_path = os.path.join(os.environ['USERPROFILE'], 'Documents', 'conda_path.txt')
        if os.path.exists(target_path):     # 存在文件则读取
            with open(target_path, 'r') as f:
                self.conda_path = f.read().strip()
        elif not self.conda_path or not os.path.exists(self.conda_path):    # 否则，让用户选择
            QMessageBox.information(self, "提示", "请选择conda(miniconda)的根目录")
            self.conda_path = QFileDialog.getExistingDirectory(None, "选择conda的安装路径", "", QFileDialog.ShowDirsOnly)

            if not self.conda_path:
                QMessageBox.warning(self, "错误", "请选择conda安装路径")
                return False

            #保存 conda安装路径信息到用户文档的.txt文件中
            with open(target_path, 'w') as f:
                f.write(self.conda_path)

        # 创建运行对话框
        self.show_running_dialog("获取环境信息")

        # 是否要从数据库中读取数据
        if self.read_DataBase:
            self.envdir = self.sql_controller.load_environments()
            self.python_version = self.sql_controller.get_python_versions()
        else:
            # 创建conda环境管理器，并获取环境信息
            conda_manager = CondaEnvManager(self.conda_path)
            self.envdir = conda_manager.get_all_envs_and_packages()
            if not self.envdir:
                QMessageBox.warning(self, "错误", "无法获取环境信息")
                return False
            self.python_version = conda_manager.get_python_version()
            if not self.python_version:
                QMessageBox.warning(self, "错误", "无法获取Python版本")
                return False
            
            # 将数据写入数据库
            result = self.sql_controller.save_environments(self.envdir)
            if not result:
                QMessageBox.warning(self, "错误", "数据写入数据库失败")
            else:
                self.read_DataBase = True   # 设置读取数据库标志为True

        # 如果对话框还存在（运行），则关闭运行对话框，并弹出提示
        self.close_running_dialog()
        #QMessageBox.information(self, "提示", "数据导入成功")

        return True

    # 清除详情页
    def clear_details(self):
        self.name_label.setText("")
        self.path_label.setText("")
        self.python_version_label.setText("")
        self.introduction_label.setText("")
        self.packages_text.clear()

    # 根据是否选中环境更新按钮状态
    def update_button_states(self):
        has_selection = bool(self.env_tree.selectedItems())
        self.remove_btn.setEnabled(has_selection)
        self.installPAK_btn.setEnabled(has_selection)
        self.uninstallAPK_btn.setEnabled(has_selection)

    # === 按钮事件===

    # 强制刷新数据库和环境树
    def on_force_refresh_dataBase(self):
        """
        强制刷新数据库
        """

        #读取数据库标志设为False，再调用on_refresh_envsListf()刷新数据库和环境树
        self.read_DataBase = False
        result = self.on_refresh_envsList()

        # 重新设置读取数据库标志为True，并弹出提示
        self.read_DataBase = True  
        QMessageBox.information(self, "提示", "刷新成功")

    # 刷新环境字典和环境树
    def on_refresh_envsList(self):
        """
        刷新环境字典，并刷新环境树
        """

        # 重新加载环境数据
        result = self.load_envs_inf()
        if not result:
            QMessageBox.warning(self, "错误", "刷新环境树error：无法获取环境信息")
            return
        if not self.envdir:
            QMessageBox.warning(self, "错误", "刷新环境树error：无法获取环境信息")
            return

        # 更新环境树
        self.env_tree.clear()
        for env, inf in self.envdir.items():
            item = QTreeWidgetItem(self.env_tree)
            item.setText(0, env)
            item.setText(1, self.python_version.get(env, "未知"))
            item.setText(2, inf[0])

    # 搜索包名
    def on_search_pak(self):
        """
        根据搜索框中的包名搜索对应包，将QTextEdite对象的光标移动到对应的行
        """
        # 获取内容
        search_text = self.search_input.text().strip()
        
        # 如果搜索文本为空，则不执行搜索
        if not search_text:
            return

        # 创建一个 QTextCursor 对象，然后定位到文档开头
        cursor = self.packages_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)  # 移动到文档开头
        
        # 设置文档和光标
        document = self.packages_text.document()
        
        # 调用 find 方法
        found_cursor = document.find(search_text, cursor)
        
        if not found_cursor.isNull():
            # 找到匹配，移动光标并选中文本
            self.packages_text.setTextCursor(found_cursor)
            # 滚动到可见区域
            self.packages_text.ensureCursorVisible() 
        else:  
            QMessageBox.warning(self, "错误", "未找到匹配项")
        
    # 创建环境
    def on_create_env(self):
        # 检查conda路径
        if not self.conda_path:
            QMessageBox.warning(self, "错误", "请先刷新并选择 conda 路径！")
            return

        # 获取环境名称
        env_name, ok = QInputDialog.getText(self, "创建环境", "请输入环境名称：")
        if not ok or not env_name.strip():
            return

        # 确认Python版本
        reply = QMessageBox.question(self, "确认", "您需要指定 Python 版本吗？")
        py_version = None
        if reply == QMessageBox.Yes:
            py_version, ok = QInputDialog.getText(self, "Python 版本", "请输入版本（如 3.9）：")
            if not ok or not py_version.strip():
                return

        # 启动线程——创建环境
        self._start_conda_operation('create', env_name, py_version)

    # 移除环境
    def on_remove_env(self):
        # 检查conda路径
        if not self.conda_path:
            QMessageBox.warning(self, "错误", "请先刷新并选择 conda 路径！")
            return

        # 获取当前选中环境
        item = self.env_tree.currentItem()
        if not item:
            return

        # 确认删除
        env_name = item.text(0)
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除环境 '{env_name}' 吗？此操作不可逆！",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # 启动线程——删除环境
        self._start_conda_operation('remove', env_name)

    # 安装包
    def on_install_package(self):
        # 检查conda路径
        if not self.conda_path:
            QMessageBox.warning(self, "错误", "请先刷新并选择 conda 路径！")
            return
        
        # 获取当前选中环境名称
        item = self.env_tree.currentItem()
        if not item:
            return
        env_name = item.text(0)
            
        # 获取包名称
        package_name, ok = QInputDialog.getText(self, "安装包", "请输入包名称：")
        if not ok or not package_name.strip():
            return
        
                    
        # 确认包版本
        reply = QMessageBox.question(self, "确认", f"您需要指定 {package_name} 版本吗？")
        pak_version = None
        if reply == QMessageBox.Yes:
            pak_version, ok = QInputDialog.getText(self, f"{package_name} 版本", "请输入版本：")
            if not ok or not pak_version.strip():
                return
        
        # 启动线程——安装包
        self._start_conda_operation('install', env_name, package_name=package_name, package_version=pak_version)

    # 卸载包
    def on_uninstall_package(self):
        # 检查conda路径
        if not self.conda_path:
            QMessageBox.warning(self, "错误", "请先刷新并选择 conda 路径！")
            return
    
        # 获取当前选中环境名称
        item = self.env_tree.currentItem()
        if not item:
            return
        env_name = item.text(0)

        # 获取包名称
        package_name, ok = QInputDialog.getText(self, "卸载包", "请输入包名称：")
        if not ok or not package_name.strip():
            return    

        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除包 '{package_name}' 吗？此操作不可逆！",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        
        # 启动线程——卸载包
        self._start_conda_operation('uninstall', env_name, package_name=package_name)

    # 启动线程
    def _start_conda_operation(self, op_type: str, env_name: str, py_version: str = None, 
                            package_name: str = None, package_version: str = None):
        """启动 conda 操作线程
        
            参数：
                op_type: 操作类型（为create/remove/install/uninstall）
                env_name: 环境名称
                py_version: Python版本        
                package_name: 包名称
                package_version: 包版本
        """
        # 禁用所有按钮
        self._disable_all_buttons()

        # 创建运行对话框
        if op_type == 'create':
            operation_text = "创建环境"
        elif op_type == 'remove':
            operation_text = "删除环境"
        elif op_type == 'install':
            operation_text = f"安装 '{package_name}'"
        elif op_type == 'uninstall':
            operation_text = f"卸载 '{package_name}'"
        else:
            operation_text = "操作"
            
        self.show_running_dialog(operation_text)    # 创建运行对话框

        # 创建QThread对象，开启新线程用于执行耗时操作
        self.thread = QThread()
        
        # 创建CondaWorker工作对象，以负责具体的conda环境操作
        self.worker = CondaWorker(self.conda_path, env_name, py_version, op_type, package_name, package_version)
        
        # 将worker对象移动到新创建的线程中执行
        self.worker.moveToThread(self.thread)

        # 建立信号与槽的连接关系
        # 当线程启动时，自动执行worker的run方法
        self.thread.started.connect(self.worker.run)
        
        # 当worker完成操作后，根据 finished 信号执行完成回调处理
        self.worker.finished.connect(self._on_operation_finished)  # 执行完毕，执行回调函数
        self.worker.finished.connect(self.thread.quit)  #执行完毕，退出线程
        
        # 当worker完成操作后，延迟删除worker对象，函数继承自 QObject
        self.worker.finished.connect(self.worker.deleteLater)
        
        # 当线程完成后，延迟删除线程对象
        self.thread.finished.connect(self.thread.deleteLater)

        # 启动线程
        self.thread.start()

    # 操作完成回调
    def _on_operation_finished(self, success: bool, name: str):
        """操作完成回调
        
            参数：接收 finished 信号传来的两个参数
                success: 操作是否成功
                name: 环境名称或包名称
        """
        # 如果对话框还存在（运行），则关闭运行对话框
        self.close_running_dialog()

        if success:
            self.read_DataBase = False  # 有数据更新，数据库的数据过期，设置标志为不读
            self.on_refresh_envsList()  # 自动刷新，同时更新数据库
            QMessageBox.information(self, "成功", f"操作 '{name}' 成功！")
        else:
            QMessageBox.critical(self, "失败", f"操作 '{name}' 失败！请检查权限或网络。")

        self._enable_all_buttons()  # 启用所有按钮

    # 禁用所有按钮
    def _disable_all_buttons(self):
        self.create_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        self.installPAK_btn.setEnabled(False)
        self.uninstallAPK_btn.setEnabled(False)

    # 启用所有按钮
    def _enable_all_buttons(self):
        self.create_btn.setEnabled(True)
        self.update_button_states()

    # 显示当前选中环境的详情信息
    def on_env_selected_showDetail(self):
            """更新右侧详情信息
            """
            self.clear_details()    # 先清空详情

            # 获取当前选中环境名称
            item = self.env_tree.currentItem()
            if item:
                env_name = item.text(0)
                env_path = self.envdir[env_name][0]

                # 读取简介
                intro_path = os.path.join(env_path, "introduction.txt")
                if os.path.exists(intro_path):
                    try:
                        with open(intro_path, "r", encoding="utf-8") as f:
                            self.introduction_label.setText(f.read())
                    except Exception:
                        self.introduction_label.setText("读取简介失败")
                else:
                    self.introduction_label.setText("无")

                # 更新环境信息
                self.name_label.setText(env_name)
                self.path_label.setText(env_path)
                self.python_version_label.setText(self.python_version.get(env_name, "未知"))

                # 更新包信息
                packages = self.envdir[env_name][1]
                if packages and len(packages) >= 3:
                    names, versions, _ = packages
                    self.packages_text.clear()  # 先清空
                    for name, ver in zip(names, versions):
                        self.packages_text.append(f"{name} = {ver}")
                else:
                    self.packages_text.setPlainText("无包信息")

            self.update_button_states()  # 更新按钮状态


# === 启动应用 ===
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CondaEnvManagerGUI()
    window.show()
    sys.exit(app.exec())