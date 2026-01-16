# 刷题系统 (DoPractice)

基于 Flask 的刷题 Web 应用，支持背题、顺序练习、随机练习三种模式。

## 功能特点

- **三种练习模式**：
  - 📖 **背题模式**：不记录成绩，直接显示答案，适合背诵学习
  - 📝 **顺序练习**：按顺序答题，记录正确与否
  - 🎲 **随机练习**：每次从未答题目中随机抽取

- **答题卡**：类似日历的小方块视图，颜色区分：未答/正确/错误/当前

- **响应式设计**：适配电脑大屏和手机小屏

- **用户管理**：口令登录，管理员后台管理口令

## 安装与运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行应用

```bash
python app.py
```

应用将在 `http://localhost:5000` 启动

### 3. 访问应用

- **用户入口**：`http://localhost:5000/`
- **管理员入口**：`http://localhost:5000/admin/login`

## 默认账户

- **用户口令**：`user123` 或 `student`
- **管理员密码**：`admin123`

> ⚠️ 请在首次使用后修改默认密码和口令！

## 题目数据格式

题目文件放在 `data/` 目录下，格式为 JSON：

```json
[
  {
    "Q": "题目文本，包含选项 A. xxx B. xxx C. xxx D. xxx",
    "A": "A"
  },
  {
    "Q": "多选题示例 A. xxx B. xxx C. xxx D. xxx",
    "A": "ABC"
  }
]
```

## 目录结构

```
DoPractice/
├── app.py              # Flask 主应用
├── requirements.txt    # Python 依赖
├── data/               # 题目数据 (JSON 文件)
├── usr/                # 用户数据存储
├── static/
│   ├── style.css       # 样式表
│   └── practice.js     # 练习页面脚本
└── templates/
    ├── base.html       # 基础模板
    ├── login.html      # 用户登录
    ├── projects.html   # 项目选择
    ├── practice.html   # 练习页面
    ├── admin_login.html # 管理员登录
    └── admin.html      # 管理员面板
```

## 键盘快捷键

在练习页面可使用以下快捷键：

- `←` / `→`：上一题/下一题
- `1-8`：选择对应选项
- `Enter`：提交答案

## 许可证

MIT License
