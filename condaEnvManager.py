import subprocess
import os
from PySide6.QtCore import Qt, QSize, QObject, QThread, Signal
from PySide6.QtWidgets import (QMessageBox, QFileDialog, QApplication, QWidget, QMainWindow)

class CondaEnvManager:
    def __init__(self, conda_path: str = None):
        # 初始化xonda路径
        self.conda_path = conda_path    # conda的安装路径

    #运行命令通用函数
    def run_command(self, args):
        """
        运行指定的命令
        
        参数:
            args (list): 命令行参数列表
        
        返回值:
            list: 命令执行结果，包含输出结果、错误信息、返回码
        """
        result = subprocess.run(args, capture_output=True, text=True)  #运行命令，设置捕获输出结果，设置自动解码为字符串
        return [result.stdout, result.stderr, result.returncode]
    
    # 获取环境列表
    def get_conda_envs(self):
        """
        获取conda环境中所有环境的列表
            
        返回值:
            list: 嵌套列表，包含环境名称的列表和路径列表，如果执行失败则返回空列表
        """
        # 执行 'conda env list' 命令获取所有环境
        command = [os.path.join(self.conda_path, "Scripts", "conda.exe"), "env", "list"]
        result = self.run_command(command) 
        if result[2] == 0:  #返回码为0，则表示命令执行成功
            # 解析命令输出，提取环境名称
            envs = result[0].splitlines()  #返回结果是按行的，固按行分割输出
            envNameList = []
            envPathList = []
            
            # 对每行内容进行处理
            for env in envs:
                # 跳过空行和注释行（通常以#开头的行是注释）
                if env.strip() and not env.startswith('#'):
                    parts = env.split()
                    # 确保至少有两个部分（环境名和路径）
                    if len(parts) >= 2:
                        envNameList.append(parts[0])
                        envPathList.append(parts[1])
            
            return [envNameList, envPathList]
        else:
            print("Failed to get environment list:", result[1])
            return []

    # 获取指定环境的包列表
    def get_packages_in_env(self, env_name: str):
        """
        获取指定环境的包列表
        
        参数:
            env_name (str): 环境名称
        
        返回值:
            list: 包列表，包含包名称、版本和构建渠道列表，如果执行失败则返回空列表
        """

        # 判断传入的是环境名称还是路径（偶尔有只能获得路径而没有名字的环境，如vscode创建的）
        if any(char in env_name for char in [':', '/', '\\', '#']):
            # 包含不允许的字符，应该是路径
            command = [os.path.join(self.conda_path, "Scripts", "conda.exe"), "list", "-p", env_name]
        else:
            # 环境名称
            command = [os.path.join(self.conda_path, "Scripts", "conda.exe"), "list", "-n", env_name]

        result = self.run_command(command)
        if result[2] == 0:
            packages = result[0].splitlines()
            packages_name = []
            packages_version = []
            packages_BuildChannel = []

            # 对每行内容进行处理
            for package in packages:
                # 跳过空行和注释行（通常以#开头的行是注释）
                if package.strip() and not package.startswith('#'):
                    packages_name.append(package.split()[0]   )       # 包名称
                    packages_version.append(package.split()[1])       # 包版本
                    packages_BuildChannel.append(package.split()[2])  # 包构建渠道

            return [packages_name, packages_version, packages_BuildChannel]
        else:
            print(f"Failed to get packages for environment {env_name}:", result[1])
            return []

    # 获取所有环境的python版本
    def get_python_version(self):
        """
        获取指定环境的Python版本
        
        参数:
            env_name (str): 环境名称
        
        返回值:
            str: 环境名称为键，python版本为值
        """
        # 先获取所有环境
        envs = self.get_conda_envs()
        env_python_version = {}

        # 获取每个环境的Python版本
        for env in envs[0]:
            packages = self.get_packages_in_env(env)   # 先获取包的列表
            # 一一查找，直到找到Python包
            for package in packages[0]:
                if package == "python":
                    index = packages[0].index(package)
                    env_python_version[env] = packages[1][index]
        return env_python_version


    # 获取所有环境及其包
    def get_all_envs_and_packages(self):
        """
        获取所有环境及其包
        
        返回值:
            dict: 环境名称为键，包含环境路径和包列表为值的字典，格式为 {env_name: [env_path, [packages_name, packages_version, packages_BuildChannel]]}
            如果执行失败则返回空字典
        """
        
        # 获取环境
        envs = self.get_conda_envs()
        if not envs:  # 检查是否成功获取环境
            return {}
        
        env_packages = {}   # 存储环境及其包的字典
        # 获取每个环境的包，并添加到字典中
        for i, env in enumerate(envs[0]):
            # 确保索引不会越界
            if i < len(envs[1]):
                env_path = envs[1][i]
            else:
                env_path = "Unknown"
                
            packages = self.get_packages_in_env(env)
            # 存储环境路径和包信息
            env_packages[env] = [env_path, packages]
        return env_packages

    # 创建环境
    def create_env(self, env_name: str, python_version: str = None):
        """
        创建一个新的环境
        
        参数:
            env_name (str): 环境名称
            python_version (str, optional): Python版本，默认为None
        
        返回值:
            bool: 创建成功返回True，否则返回False
        """

        # 判断是否传入Python版本，没有则默认为最新版
        if not python_version:
            command = [os.path.join(self.conda_path, "Scripts", "conda.exe"), "create", "-n", env_name, "python", "-y"]
        else:
            command = [os.path.join(self.conda_path, "Scripts", "conda.exe"), "create", "-n", env_name, "python=" + python_version, "-y"]
        
        result = self.run_command(command)
        if result[2] == 0:
            return True
        else:
            return False
        
    # 删除环境
    def remove_env(self, env_name: str):
        """
        删除指定的环境
        
        参数:
            env_name (str): 环境名称
        
        返回值:
            bool: 删除成功返回True，否则返回False
        """
        command = [os.path.join(self.conda_path, "Scripts", "conda.exe"), "remove", "-n", env_name, "--all", "-y"]
        result = self.run_command(command)
        if result[2] == 0:
            return True
        else:
            return False
        
    # 安装包
    def install_package(self, env_name: str, package: str, version: str = None):
        """
        在指定环境中安装包
        
        参数:
            env_name (str): 环境名称
            package (str): 要安装的包名称
            version (str, optional): 包版本，默认为None
        
        返回值:
            bool: 安装成功返回True，否则返回False
        """

        #判断包是否输入及是否包含版本
        if not package: return False
        if not version:
            command = [os.path.join(self.conda_path, "Scripts", "conda.exe"), "install", "-n", env_name, package, "-y"]
        else:
            command = [os.path.join(self.conda_path, "Scripts", "conda.exe"), "install", "-n", env_name, package, "=" + version, "-y"]
        
        result = self.run_command(command)
        if result[2] == 0:
            return True
        else:
            return False

    # 卸载包
    def uninstall_package(self, env_name: str, package: str):
        """
        在指定环境中卸载包
        
        参数:
            env_name (str): 环境名称
            package (str): 要卸载的包名称
        
        返回值:
            bool: 卸载成功返回True，否则返回False
        """
        if not package: return False
        command = [os.path.join(self.conda_path, "Scripts", "conda.exe"), "remove", "-n", env_name, package, "-y"]
        result = self.run_command(command)
        if result[2] == 0:
            return True
        else:
            return False
        
