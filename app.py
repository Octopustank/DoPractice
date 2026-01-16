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

def get_available_projects():
    """获取所有可用的题目项目"""
    projects = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json'):
            project_name = filename[:-5]  # 去掉 .json 后缀
            projects.append(project_name)
    return sorted(projects)

def load_project_questions(project_name):
    """加载项目题目"""
    filepath = os.path.join(DATA_DIR, f'{project_name}.json')
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
    available_projects = get_available_projects()
    user_data = get_user_data(session['token'])
    
    # 计算每个项目的进度
    project_info = []
    for project in available_projects:
        questions = load_project_questions(project)
        total = len(questions)
        
        # 获取用户在该项目的进度
        project_data = user_data.get(project, {})
        answered = len(project_data.get('answers', {}))
        correct = sum(1 for v in project_data.get('answers', {}).values() if v.get('correct'))
        
        project_info.append({
            'name': project,
            'total': total,
            'answered': answered,
            'correct': correct
        })
    
    return render_template('projects.html', projects=project_info)

@app.route('/practice/<project_name>/<mode>')
@login_required
def practice(project_name, mode):
    """练习页面"""
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
            for project_data in user_data.values():
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
                         users_stats=users_stats)

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
