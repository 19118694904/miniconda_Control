# mysqlcontroller.py
import pymysql
from typing import Dict, List, Tuple, Optional

# 检查是否存在环境表
def env_table_exist() -> bool:
    """
    检查是否存在环境表，以判断是否可以直接从数据库获取数据
    """
    try:
        # 创建数据库连接
        connection = pymysql.connect(
            host='localhost',            # 数据库地址
            user='chiruno',              # 用户名
            password='123456',           # 密码
            database='condaControlor',   # 数据库名
            charset='utf8mb4',           # 字符编码
        )

        with connection.cursor() as cursor:
            # 检查环境表是否存在
            sql = "SHOW TABLES LIKE 'environments'"
            cursor.execute(sql)
            result = cursor.fetchone()
            return result is not None
    except Exception as e:
        print(f"检查表存在性时出错: {e}")
        return False
    finally:
        try:
            if 'connection' in locals():
                connection.close()
        except:
            pass

# 第一次运行则创建数据库和表
def create_databaseANDTable():
    """
    创建数据库和表结构（首次运行时）
    数据库名：condaControlor
    表名：environments，包含环境名称、路径、Python版本等信息
    """
    # 连接MySQL服务器
    connection = pymysql.connect(
        host='localhost',       # 数据库地址
        user='chiruno',         # 用户名
        password='123456',      # 密码
        charset='utf8mb4',      # 字符编码
    )

    try:
        with connection.cursor() as cursor:
            # 创建数据库（使用utf8mb4字符集）
            sql = "CREATE DATABASE IF NOT EXISTS `condaControlor` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            cursor.execute(sql)
            connection.commit()
            
            # 使用数据库
            cursor.execute("USE condaControlor")
            
            # 创建环境表
            create_env_table = """CREATE TABLE IF NOT EXISTS environments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                env_name VARCHAR(255) UNIQUE NOT NULL,
                path VARCHAR(512) NOT NULL,
                python_version VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"""
            cursor.execute(create_env_table)

            # 创建包表
            create_package_table = """CREATE TABLE IF NOT EXISTS packages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                env_name VARCHAR(255) NOT NULL,
                package_name VARCHAR(255) NOT NULL,
                version VARCHAR(100) NOT NULL,
                build_channel VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_env_name_package_name (env_name, package_name),
                UNIQUE KEY uk_env_name_package_name_ver (env_name, package_name, version),
                FOREIGN KEY (env_name) REFERENCES environments(env_name) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"""
            cursor.execute(create_package_table)
            connection.commit()
            
    except Exception as e:
        print(f"创建数据库时出错: {e}")
        raise
    finally:
        connection.close()

# 数据库控制器类
class MySQLController:
    """
    MySQL数据库控制器，用于管理conda环境信息
    """
    
    def __init__(self, host='localhost', user='chiruno', password='123456', database='condaControlor'):
        """
        初始化数据库连接参数
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None          # 数据库连接对象
    
    # 连接默认数据库
    def connect(self) -> bool:
        """
        建立数据库连接
        """
        try:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor      # 使用字典游标
            )
            return True
        except Exception as e:
            print(f"数据库连接失败: {e}")
            self.connection = None
            return False
    
    # 断开默认数据库连接
    def disconnect(self):
        """
        关闭数据库连接
        """
        try:
            if self.connection:
                self.connection.close()
        except:
            pass
        finally:
            self.connection = None

    # 保存全部环境信息
    def save_environments(self, env_data: Dict[str, List]) -> bool:
        """
        保存环境信息到数据库
        
        参数:
            env_data: 环境数据字典，格式为 {env_name: [env_path, [packages_name, packages_version, packages_BuildChannel]]}
        
        返回:
            bool: 操作是否成功
        """
        if not self.connect():
            print("保存环境信息error: 无法连接数据库")
            return False

        try:
            with self.connection.cursor() as cursor:
                # 判断表是否为空
                cursor.execute("SELECT * FROM environments")
                if cursor.fetchone() is not None:
                    # 清空数据表内现有的数据，直接删母表，子表的外键连接会让它一起被删除
                    cursor.execute("DELETE FROM environments")                   
                
                # 重新插入环境数据
                for env_name, env_info in env_data.items():
                    env_path = env_info[0]  # 环境路径列表
                    packages = env_info[1] if len(env_info) > 1 else [[], [], []]   # 包信息列表
                    
                    # 获取Python版本
                    python_version = None
                    if packages and len(packages) == 3:
                        package_names = packages[0]
                        package_versions = packages[1]
                        try:
                            python_idx = package_names.index('python')
                            python_version = package_versions[python_idx]
                        except (ValueError, IndexError):
                            pass
                    
                    # 插入环境信息到环境表（先插母表）
                    cursor.execute(
                        "INSERT INTO environments (env_name, path, python_version) VALUES (%s, %s, %s)",
                        (env_name, env_path, python_version)
                    )
                    
                    # 插入包信息到包表
                    if packages and len(packages) == 3:
                        package_names = packages[0]
                        package_versions = packages[1]
                        package_channels = packages[2]
                        
                        for i in range(len(package_names)):
                            cursor.execute(
                                "INSERT INTO packages (env_name, package_name, version, build_channel) VALUES (%s, %s, %s, %s)",
                                (env_name, package_names[i], 
                                 package_versions[i] if i < len(package_versions) else None,
                                 package_channels[i] if i < len(package_channels) else None)
                            )
                
                # 提交事务
                self.connection.commit()
                return True
                
        except Exception as e:
            # 回滚事务（确保连接仍然存在）
            try:
                if self.connection:
                    self.connection.rollback()
            except:
                pass
            print(f"保存环境数据时出错: {e}")
            return False
        finally:
            self.disconnect()
    
    # 加载全部环境信息
    def load_environments(self) -> Optional[Dict[str, List]]:
        """
        从数据库加载环境信息
        
        return:
            Dict[str, List]: 环境数据字典，格式为 {env_name: [env_path, [packages_name, packages_version, packages_BuildChannel]]}
            None: 加载失败
        """
        if not self.connect():
            print("加载环境信息error：无法连接数据库")
            return None
            
        try:
            with self.connection.cursor() as cursor:
                # 查询所有环境
                cursor.execute("SELECT * FROM environments")
                environments = cursor.fetchall()    # 环境表的行字典的列表
                
                if not environments:
                    print("加载环境信息error：没有找到任何环境")
                    return {}
                
                env_data = {}   # 最后返回的环境数据字典
                # 查询每个环境的包信息
                for env in environments:
                    env_name = env['env_name']
                    env_path = env['path']
                    
                    # 查询该环境的包
                    cursor.execute("SELECT * FROM packages WHERE env_name = %s", (env_name,))
                    packages = cursor.fetchall()    # 包表的行字典的列表
                    
                    # 整理包信息
                    package_names = []
                    package_versions = []
                    package_channels = []
                    
                    for pkg in packages:
                        package_names.append(pkg['package_name'])
                        package_versions.append(pkg['version'] or '')
                        package_channels.append(pkg['build_channel'] or '')
                    
                    # 存储环境数据
                    env_data[env_name] = [env_path, [package_names, package_versions, package_channels]]
                
                return env_data
                
        except Exception as e:
            print(f"加载环境数据时出错: {e}")
            return None
        finally:
            self.disconnect()
    
    # 获取所有环境的Python版本信息
    def get_python_versions(self) -> Optional[Dict[str, str]]:
        """
        获取所有环境的Python版本信息
        
        返回:
            Dict[str, str]: 环境名到Python版本的映射
            None: 查询失败
        """
        if not self.connect():
            print("获取Python版本信息error：无法连接数据库")
            return None
            
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT env_name, python_version FROM environments WHERE python_version IS NOT NULL")
                results = cursor.fetchall()
                
                python_versions = {}    # 同于返回的Python版本信息字典
                for row in results:
                    python_versions[row['env_name']] = row['python_version']
                
                return python_versions
                
        except Exception as e:
            print(f"获取Python版本时出错: {e}")
            return None
        finally:
            self.disconnect()
    
    # 清空所有数据和包
    def clear_data(self) -> bool:
        """
        清空所有环境和包数据
        
        返回:
            bool: 操作是否成功
        """
        if not self.connect():
            return False
            
        try:
            with self.connection.cursor() as cursor:
                # 清空数据
                cursor.execute("DELETE FROM packages")
                cursor.execute("DELETE FROM environments")
                
                # 提交事务
                self.connection.commit()
                return True
                
        except Exception as e:
            # 回滚事务
            try:
                if self.connection:
                    self.connection.rollback()
            except:
                pass
            print(f"清空数据时出错: {e}")
            return False
        finally:
            self.disconnect()
    
    # 根据环境名称获取包信息
    def get_packages_by_env(self, env_name: str) -> Optional[List[Dict]]:
        """
        根据环境名称获取包信息
        
        参数:
            env_name (str): 环境名称
            
        返回:
            List[Dict]: 包信息列表,每个元素是一个字典，包含包名称、版本和构建渠道
            None: 查询失败
        """
        if not self.connect():
            print("获取包信息error：无法连接数据库")
            return None
            
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT * FROM packages WHERE env_name = %s", (env_name,))
                return cursor.fetchall()
        except Exception as e:
            print(f"查询环境包信息时出错: {e}")
            return None
        finally:
            self.disconnect()
    
    # 获取特定环境、包名称的包信息
    def get_package_by_env_and_name(self, env_name: str, package_name: str) -> Optional[Dict]:
        """
        根据环境名称和包名称获取特定包信息
        
        参数:
            env_name (str): 环境名称
            package_name (str): 包名称
            
        返回:
            Dict: 包信息字典，包含包名称、版本和构建渠道
            None: 查询失败或未找到
        """
        if not self.connect():
            print("获取包信息error：无法连接数据库")
            return None
            
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT * FROM packages WHERE env_name = %s AND package_name = %s", 
                              (env_name, package_name))
                return cursor.fetchone()
        except Exception as e:
            print(f"查询特定包信息时出错: {e}")
            return None
        finally:
            self.disconnect()
    
    # 检查包是否存在
    def package_exists(self, env_name: str, package_name: str) -> bool:
        """
        检查特定包是否存在于指定环境中
        
        参数:
            env_name (str): 环境名称
            package_name (str): 包名称
            
        返回:
            bool: 包是否存在
        """
        return self.get_package_by_env_and_name(env_name, package_name) is not None
    
    # 更新包版本
    def update_package_version(self, env_name: str, package_name: str, version: str) -> bool:
        """
        更新包的版本信息
        
        参数:
            env_name (str): 环境名称
            package_name (str): 包名称
            version (str): 新版本
            
        返回:
            bool: 操作是否成功
        """
        if not self.connect():
            print("更新包版本error：无法连接数据库")
            return False
            
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("UPDATE packages SET version = %s, updated_at = CURRENT_TIMESTAMP WHERE env_name = %s AND package_name = %s",
                              (version, env_name, package_name))
                
                # 提交事务
                if self.connection:
                    self.connection.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            # 回滚事务
            try:
                if self.connection:
                    self.connection.rollback()
            except:
                pass
            print(f"更新包版本时出错: {e}")
            return False
        finally:
            self.disconnect()