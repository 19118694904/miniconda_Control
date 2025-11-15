# Miniconda 环境管理器

一个基于 **PySide6** 和 **MySQL** 的图形化 Conda 环境管理工具，支持环境的创建、删除、包安装/卸载，并自动将环境信息持久化到本地数据库中，便于快速加载和查询。

---

## ✨ 功能特性

- 📦 **环境管理**：列出、创建、删除 Conda 环境  
- 🔧 **包管理**：在指定环境中安装或卸载 Python 包  
- 💾 **数据持久化**：自动将环境与包信息保存至本地 MySQL 数据库（`condaControlor`）  
- 🔍 **包搜索**：在已安装包列表中实时搜索包名  
- 📝 **环境简介**：支持在每个环境目录下放置 `introduction.txt` 作为环境说明  
- ⚡ **异步操作**：所有耗时操作（如创建环境、安装包）均在后台线程执行，避免界面卡死  
- 🔄 **一键刷新**：强制从 Conda 重新获取最新数据并更新数据库  

---

## 🛠 技术栈

- **前端界面**：PySide6 (Qt for Python)  
- **后端逻辑**：Python 3.12(3.9+以上应该都行)  
- **数据库**：MySQL（通过 `pymysql 1.1.2` 驱动）  
- **依赖工具**：Miniconda / Anaconda（需已安装）

---

## 📁 项目结构

```
.
├── main.py                 # 主程序入口，GUI 界面逻辑
├── condaEnvManager.py      # 封装 Conda 命令行操作（环境/包管理）
├── mysqlcontroller.py      # MySQL 数据库操作封装（CRUD + 初始化）
└── README.md               # 本文件
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install PySide6 pymysql
```

> 确保系统已安装 **MySQL 服务** 并运行（默认连接 `localhost`）。

### 2. 配置数据库用户（首次运行前）

脚本默认使用以下数据库凭据：

- **Host**: `localhost`
- **User**: `chiruno`
- **Password**: `123456`
- **Database**: `condaControlor`

请确保 MySQL 中存在该用户并拥有建库权限，或修改 `mysqlcontroller.py` 和 `main.py` 中的连接参数。   
也就是需要创建一个新的SQL用户，	   用户名：chiruno，密码：123456   
`什么？为什么是 chiruno？ 你怎么睡傻了，咱马上去找大酱来给你看看（误）`   
不知道怎么创建的话，运行 MySQL 8.0 Command Line Client - Unicode，输入 root 用户的密码（大概率也是 123456），然后使用：   
```CREATE USER 'chiruno'@'localhost' IDENTIFIED BY '123456';```

### 3. 运行程序

> 💡 首次运行时，程序会自动创建数据库和表结构。

```bash
python main.py
```

首次启动时：
1. 会提示选择 **Miniconda 安装根目录**（如 `C:\Users\<user>\miniconda3`）
2. 自动扫描所有 Conda 环境并写入数据库
3. 后续启动将直接从数据库加载，速度更快

Conda 路径会被保存在本地文档，以免去每次都要手动选择：
```
%USERPROFILE%\Documents\conda_path.txt
```

---

## 🗃 数据库设计

### 数据库名
`condaControlor`

### 表结构

#### `environments`（环境表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT (PK, AI) | 主键 |
| env_name | VARCHAR(255) (UNIQUE) | 环境名称 |
| path | VARCHAR(512) | 环境路径 |
| python_version | VARCHAR(50) | Python 版本 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

#### `packages`（包表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT (PK, AI) | 主键 |
| env_name | VARCHAR(255) (FK → environments.env_name) | 所属环境 |
| package_name | VARCHAR(255) | 包名 |
| version | VARCHAR(100) | 版本号 |
| build_channel | VARCHAR(100) | 构建渠道（如 `conda-forge`） |
| created_at / updated_at | TIMESTAMP | 时间戳 |

> 删除环境时，关联的包会自动级联删除（`ON DELETE CASCADE`）。

---

## 🔐 安全提示

- 默认数据库密码为 `123456`，**仅建议用于本地开发环境**
- 如需进一步开发部署或加强安全，请修改代码中的数据库凭据

---

## 📌 注意事项
- 所有conda指令通过 `subprocess` 类执行
- 程序依赖 `conda.exe`，路径为 `<conda_path>/Scripts/conda.exe`（Windows）
- 若 Conda 环境路径包含空格或特殊字符，可能影响部分命令解析
- 所有操作功能均使用 `conda.exe`，如 `conda remove -nenv_name package -y`
- 搜索功能区分大小写，且仅在当前选中环境的包列表中查找

---

---

## 📜 许可证

本项目仅供学习与个人使用。代码中涉及的数据库密码等敏感信息请勿用于生产环境。

---

> ❤️ 来自雾之湖最聪明的冰妖精(天才です)