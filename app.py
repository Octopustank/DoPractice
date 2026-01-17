#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
刷题 Web App - 基于 Flask
支持背题、顺序练习、随机练习三种模式
"""

import os
import json
import random
import hashlib
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# 配置文件路径
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
USR_DIR = os.path.join(os.path.dirname(__file__), 'usr')

# 确保用户数据目录存在
os.makedirs(USR_DIR, exist_ok=True)

# 管理员配置文件
ADMIN_CONFIG_FILE = os.path.join(USR_DIR, 'admin_config.json')

def get_admin_config():
    """获取管理员配置"""
    if os.path.exists(ADMIN_CONFIG_FILE):
        with open(ADMIN_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    # 默认配置
    default_config = {
        'admin_password': hashlib.sha256('admin123'.encode()).hexdigest(),
        'allowed_tokens': ['user123', 'student']  # 默认允许的口令
    }
    save_admin_config(default_config)
    return default_config

def save_admin_config(config):
    """保存管理员配置"""
    with open(ADMIN_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def get_announcements():
    """获取所有公告"""
    config = get_admin_config()
    return config.get('announcements', [])

def add_announcement(title, content):
    """添加新公告
    返回：(success, message, announcement_hash)
    """
    config = get_admin_config()
    
    if 'announcements' not in config:
        config['announcements'] = []
    
    # 生成公告哈希（使用时间戳+标题+内容的MD5前10位）
    timestamp = datetime.now().isoformat()
    hash_source = f"{timestamp}{title}{content}".encode('utf-8')
    announcement_hash = hashlib.md5(hash_source).hexdigest()[:10]
    
    # 检查哈希是否已存在（防止极低概率的碰撞）
    existing_hashes = {ann['hash'] for ann in config['announcements']}
    attempt = 0
    while announcement_hash in existing_hashes and attempt < 10:
        # 如果碰撞，添加随机因子重新生成
        attempt += 1
        hash_source = f"{timestamp}{title}{content}{attempt}".encode('utf-8')
        announcement_hash = hashlib.md5(hash_source).hexdigest()[:10]
    
    if announcement_hash in existing_hashes:
        return False, "公告哈希生成失败", None
    
    # 创建公告
    announcement = {
        'hash': announcement_hash,
        'title': title,
        'content': content,
        'timestamp': timestamp
    }
    
    # 添加到列表开头（最新的在前面）
    config['announcements'].insert(0, announcement)
    save_admin_config(config)
    
    return True, "公告发布成功", announcement_hash

def delete_announcement(announcement_hash):
    """删除公告"""
    config = get_admin_config()
    
    if 'announcements' not in config:
        return False, "没有公告"
    
    announcements = config['announcements']
    original_len = len(announcements)
    config['announcements'] = [ann for ann in announcements if ann['hash'] != announcement_hash]
    
    if len(config['announcements']) < original_len:
        save_admin_config(config)
        return True, "公告已删除"
    
    return False, "公告不存在"

def get_unread_announcements(token):
    """获取用户未读的公告"""
    user_data = get_user_data(token)
    read_list = user_data.get('read_announcements', [])
    
    all_announcements = get_announcements()
    unread = [ann for ann in all_announcements if ann['hash'] not in read_list]
    
    return unread

def mark_announcement_read(token, announcement_hash):
    """标记公告为已读"""
    user_data = get_user_data(token)
    
    if 'read_announcements' not in user_data:
        user_data['read_announcements'] = []
    
    if announcement_hash not in user_data['read_announcements']:
        user_data['read_announcements'].append(announcement_hash)
        save_user_data(token, user_data)

def get_user_data_file(token):
    """获取用户数据文件路径"""
    token_hash = hashlib.md5(token.encode()).hexdigest()[:16]
    return os.path.join(USR_DIR, f'user_{token_hash}.json')

def get_user_data(token):
    """获取用户练习数据"""
    filepath = get_user_data_file(token)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_user_data(token, data):
    """保存用户练习数据"""
    filepath = get_user_data_file(token)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def chinese_number_to_int(text):
    """将中文数字转换为阿拉伯数字，用于排序
    支持：一、二、三...九、十、十一...十九、二十...九十九
    """
    # 特殊情况：导论排在最前面
    if '导论' in text:
        return 0
    
    # 提取"第X章"中的X
    import re
    match = re.search(r'第(.+?)章', text)
    if not match:
        return 999  # 无法识别的放在最后
    
    num_text = match.group(1)
    
    # 中文数字映射
    cn_num = {
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        '零': 0
    }
    
    # 如果直接是阿拉伯数字
    if num_text.isdigit():
        return int(num_text)
    
    # 单个字符的情况
    if len(num_text) == 1:
        return cn_num.get(num_text, 999)
    
    # "十X" 的情况（十一、十二...十九）
    if num_text.startswith('十') and len(num_text) == 2:
        return 10 + cn_num.get(num_text[1], 0)
    
    # "X十" 的情况（二十、三十...九十）
    if num_text.endswith('十') and len(num_text) == 2:
        return cn_num.get(num_text[0], 0) * 10
    
    # "X十Y" 的情况（二十一、三十五...九十九）
    if '十' in num_text and len(num_text) == 3:
        tens = cn_num.get(num_text[0], 0) * 10
        ones = cn_num.get(num_text[2], 0)
        return tens + ones
    
    return 999  # 无法识别的放在最后

def get_available_projects():
    """获取所有可用的题目项目，支持文件夹结构"""
    projects = []
    folders = {}
    
    # 遍历data目录
    for item in os.listdir(DATA_DIR):
        item_path = os.path.join(DATA_DIR, item)
        
        # 如果是文件夹
        if os.path.isdir(item_path):
            folder_name = item
            folder_projects = []
            
            # 遍历文件夹中的JSON文件
            for filename in os.listdir(item_path):
                if filename.endswith('.json'):
                    file_name = filename[:-5]  # 去掉 .json 后缀
                    # 记录格式：文件夹名+文件名
                    project_id = folder_name + file_name
                    folder_projects.append({
                        'id': project_id,
                        'display_name': file_name,
                        'folder': folder_name,
                        'file': filename
                    })
            
            if folder_projects:
                # 使用中文数字智能排序
                folders[folder_name] = sorted(folder_projects, key=lambda x: chinese_number_to_int(x['display_name']))
        
        # 如果是JSON文件（直接在data目录下）
        elif item.endswith('.json'):
            project_name = item[:-5]
            projects.append({
                'id': project_name,
                'display_name': project_name,
                'folder': None,
                'file': item
            })
    
    # 返回排序后的文件夹和独立项目
    return {
        'folders': dict(sorted(folders.items())),
        'standalone': sorted(projects, key=lambda x: x['display_name'])
    }

def load_project_questions(project_id):
    """加载项目题目，支持文件夹结构
    project_id格式：
    - 独立文件：文件名（不含.json）
    - 文件夹内文件：文件夹名+文件名（不含.json）
    """
    # 先尝试直接加载（独立文件）
    filepath = os.path.join(DATA_DIR, f'{project_id}.json')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # 尝试在文件夹中查找
    for folder in os.listdir(DATA_DIR):
        folder_path = os.path.join(DATA_DIR, folder)
        if os.path.isdir(folder_path):
            # 检查project_id是否以该文件夹名开头
            if project_id.startswith(folder):
                # 提取文件名部分
                file_name = project_id[len(folder):] + '.json'
                filepath = os.path.join(folder_path, file_name)
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return json.load(f)
    
    return []

def parse_question(q_text):
    """解析题目文本，分离题干和选项"""
    lines = q_text.strip()
    # 找到选项开始的位置
    options = []
    question_text = lines
    
    # 匹配选项模式: A. B. C. D. E. F. G. H.
    import re
    option_pattern = r'([A-H])\.\s*(.+?)(?=\s+[A-H]\.|$)'
    matches = re.findall(option_pattern, lines)
    
    if matches:
        # 找到第一个选项的位置，截取题干
        first_option_match = re.search(r'\s+A\.', lines)
        if first_option_match:
            question_text = lines[:first_option_match.start()].strip()
        
        for letter, content in matches:
            options.append({
                'letter': letter,
                'content': content.strip()
            })
    
    return {
        'text': question_text,
        'options': options
    }

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'token' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """管理员验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== 路由 ====================

@app.route('/')
def index():
    """首页 - 重定向到登录或项目选择"""
    if 'token' in session:
        return redirect(url_for('projects'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录页面"""
    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        if not token:
            flash('请输入口令', 'error')
            return render_template('login.html')
        
        config = get_admin_config()
        if token not in config['allowed_tokens']:
            flash('口令无效', 'error')
            return render_template('login.html')
        
        session['token'] = token
        return redirect(url_for('projects'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """退出登录"""
    session.pop('token', None)
    return redirect(url_for('login'))

@app.route('/projects')
@login_required
def projects():
    """项目选择页面"""
    project_structure = get_available_projects()
    user_data = get_user_data(session['token'])
    
    # 清理已删除公告的阅读记录
    if 'read_announcements' in user_data and user_data['read_announcements']:
        # 获取所有存在的公告哈希
        existing_hashes = {ann['hash'] for ann in get_announcements()}
        
        # 过滤掉不存在的公告哈希
        original_read_list = user_data['read_announcements']
        user_data['read_announcements'] = [h for h in user_data['read_announcements'] if h in existing_hashes]
        
        # 如果有删除，保存更新
        if len(user_data['read_announcements']) < len(original_read_list):
            save_user_data(session['token'], user_data)
    
    # 计算每个项目的进度
    def add_progress(project):
        project_id = project['id']
        questions = load_project_questions(project_id)
        total = len(questions)
        
        # 获取用户在该项目的进度
        project_data = user_data.get(project_id, {})
        answered = len(project_data.get('answers', {}))
        correct = sum(1 for v in project_data.get('answers', {}).values() if v.get('correct'))
        
        return {
            **project,
            'total': total,
            'answered': answered,
            'correct': correct
        }
    
    # 为文件夹中的项目添加进度
    folders_with_progress = {}
    for folder_name, folder_projects in project_structure['folders'].items():
        folders_with_progress[folder_name] = [add_progress(p) for p in folder_projects]
    
    # 为独立项目添加进度
    standalone_with_progress = [add_progress(p) for p in project_structure['standalone']]
    
    return render_template('projects.html',
                         folders=folders_with_progress,
                         standalone_projects=standalone_with_progress)

@app.route('/practice/<project_name>/<mode>')
@login_required
def practice(project_name, mode):
    """练习页面
    project_name是project_id，格式：
    - 独立文件：文件名（不含.json）
    - 文件夹内文件：文件夹名+文件名（不含.json）
    """
    if mode not in ['memorize', 'sequential', 'random']:
        return redirect(url_for('projects'))
    
    questions = load_project_questions(project_name)
    if not questions:
        flash('项目不存在或没有题目', 'error')
        return redirect(url_for('projects'))
    
    # 解析所有题目
    parsed_questions = []
    for i, q in enumerate(questions):
        parsed = parse_question(q['Q'])
        parsed['index'] = i
        parsed['answer'] = q['A']
        parsed['is_multi'] = len(q['A']) > 1
        parsed_questions.append(parsed)
    
    # 获取用户数据
    user_data = get_user_data(session['token'])
    project_data = user_data.get(project_name, {'answers': {}})
    
    return render_template('practice.html',
                         project_name=project_name,
                         mode=mode,
                         questions=parsed_questions,
                         user_answers=project_data.get('answers', {}),
                         total=len(questions))

@app.route('/api/submit_answer', methods=['POST'])
@login_required
def submit_answer():
    """提交答案"""
    data = request.get_json()
    project_name = data.get('project')
    question_index = data.get('index')
    user_answer = data.get('answer')  # 用户选择的答案，如 'A' 或 'ABC'
    
    if not all([project_name, question_index is not None, user_answer]):
        return jsonify({'success': False, 'message': '参数不完整'})
    
    questions = load_project_questions(project_name)
    if question_index < 0 or question_index >= len(questions):
        return jsonify({'success': False, 'message': '题目不存在'})
    
    correct_answer = questions[question_index]['A']
    # 排序后比较，确保顺序无关
    is_correct = ''.join(sorted(user_answer)) == ''.join(sorted(correct_answer))
    
    # 保存用户答案
    token = session['token']
    user_data = get_user_data(token)
    
    if project_name not in user_data:
        user_data[project_name] = {'answers': {}}
    
    user_data[project_name]['answers'][str(question_index)] = {
        'answer': user_answer,
        'correct': is_correct,
        'timestamp': datetime.now().isoformat()
    }
    
    save_user_data(token, user_data)
    
    return jsonify({
        'success': True,
        'correct': is_correct,
        'correct_answer': correct_answer
    })

@app.route('/api/reset_progress', methods=['POST'])
@login_required
def reset_progress():
    """重置项目进度"""
    data = request.get_json()
    project_name = data.get('project')
    
    if not project_name:
        return jsonify({'success': False, 'message': '参数不完整'})
    
    token = session['token']
    user_data = get_user_data(token)
    
    if project_name in user_data:
        user_data[project_name] = {'answers': {}}
        save_user_data(token, user_data)
    
    return jsonify({'success': True})

@app.route('/api/get_random_unanswered', methods=['POST'])
@login_required
def get_random_unanswered():
    """获取随机未答题目"""
    data = request.get_json()
    project_name = data.get('project')
    
    questions = load_project_questions(project_name)
    user_data = get_user_data(session['token'])
    project_data = user_data.get(project_name, {'answers': {}})
    answered = set(project_data.get('answers', {}).keys())
    
    # 找出未答题目
    unanswered = [i for i in range(len(questions)) if str(i) not in answered]
    
    if not unanswered:
        return jsonify({'success': True, 'index': None, 'all_answered': True})
    
    random_index = random.choice(unanswered)
    return jsonify({'success': True, 'index': random_index, 'all_answered': False})

# ==================== 公告相关路由 ====================

@app.route('/api/get_unread_announcements', methods=['GET'])
@login_required
def api_get_unread_announcements():
    """获取未读公告"""
    unread = get_unread_announcements(session['token'])
    return jsonify({'success': True, 'announcements': unread})

@app.route('/api/get_all_announcements', methods=['GET'])
@login_required
def api_get_all_announcements():
    """获取所有公告"""
    all_announcements = get_announcements()
    user_data = get_user_data(session['token'])
    read_list = user_data.get('read_announcements', [])
    
    # 为每个公告添加已读标记
    for ann in all_announcements:
        ann['is_read'] = ann['hash'] in read_list
    
    return jsonify({'success': True, 'announcements': all_announcements})

@app.route('/api/mark_announcement_read', methods=['POST'])
@login_required
def api_mark_announcement_read():
    """标记公告为已读"""
    data = request.get_json()
    announcement_hash = data.get('hash')
    
    if not announcement_hash:
        return jsonify({'success': False, 'message': '参数不完整'})
    
    mark_announcement_read(session['token'], announcement_hash)
    return jsonify({'success': True})

# ==================== 管理员路由 ====================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """管理员登录"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        config = get_admin_config()
        
        if hashlib.sha256(password.encode()).hexdigest() == config['admin_password']:
            session['is_admin'] = True
            return redirect(url_for('admin_panel'))
        else:
            flash('密码错误', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """管理员退出"""
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin_panel():
    """管理员面板"""
    config = get_admin_config()
    
    # 获取所有用户的数据统计
    users_stats = []
    for filename in os.listdir(USR_DIR):
        if filename.startswith('user_') and filename.endswith('.json'):
            filepath = os.path.join(USR_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
            
            total_answered = 0
            total_correct = 0
            # 遍历用户数据，只处理字典类型的项目数据
            for key, project_data in user_data.items():
                # 跳过非项目数据（如read_announcements等）
                if not isinstance(project_data, dict) or 'answers' not in project_data:
                    continue
                
                answers = project_data.get('answers', {})
                total_answered += len(answers)
                total_correct += sum(1 for v in answers.values() if v.get('correct'))
            
            users_stats.append({
                'file': filename,
                'total_answered': total_answered,
                'total_correct': total_correct
            })
    
    return render_template('admin.html',
                         tokens=config['allowed_tokens'],
                         users_stats=users_stats,
                         announcements=get_announcements())

@app.route('/admin/add_token', methods=['POST'])
@admin_required
def add_token():
    """添加新口令"""
    token = request.form.get('token', '').strip()
    if token:
        config = get_admin_config()
        if token not in config['allowed_tokens']:
            config['allowed_tokens'].append(token)
            save_admin_config(config)
            flash(f'口令 "{token}" 已添加', 'success')
        else:
            flash('口令已存在', 'error')
    return redirect(url_for('admin_panel'))

@app.route('/admin/remove_token', methods=['POST'])
@admin_required
def remove_token():
    """删除口令"""
    token = request.form.get('token', '').strip()
    if token:
        config = get_admin_config()
        if token in config['allowed_tokens']:
            config['allowed_tokens'].remove(token)
            save_admin_config(config)
            flash(f'口令 "{token}" 已删除', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/change_password', methods=['POST'])
@admin_required
def change_password():
    """修改管理员密码"""
    new_password = request.form.get('new_password', '').strip()
    if new_password:
        config = get_admin_config()
        config['admin_password'] = hashlib.sha256(new_password.encode()).hexdigest()
        save_admin_config(config)
        flash('密码已修改', 'success')
    else:
        flash('密码不能为空', 'error')
    return redirect(url_for('admin_panel'))
@app.route('/admin/add_announcement', methods=['POST'])
@admin_required
def admin_add_announcement():
    """发布新公告"""
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    
    if not title or not content:
        flash('标题和内容不能为空', 'error')
    else:
        success, message, _ = add_announcement(title, content)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_announcement', methods=['POST'])
@admin_required
def admin_delete_announcement():
    """删除公告"""
    announcement_hash = request.form.get('hash', '').strip()
    
    if announcement_hash:
        success, message = delete_announcement(announcement_hash)
        flash(message, 'success' if success else 'error')
    
    return redirect(url_for('admin_panel'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
