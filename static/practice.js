/**
 * 刷题系统 - 练习页面 JavaScript
 */

(function() {
    'use strict';
    
    // 获取页面数据
    const { projectName, mode, questions, userAnswers, total } = window.practiceData;
    
    // 状态管理
    const state = {
        currentIndex: 0,
        selectedOptions: [],
        localAnswers: { ...userAnswers },  // 本地答案缓存
        isSubmitted: false
    };
    
    // DOM 元素
    const elements = {
        currentNum: document.getElementById('currentNum'),
        totalNum: document.getElementById('totalNum'),
        questionType: document.getElementById('questionType'),
        questionText: document.getElementById('questionText'),
        optionsContainer: document.getElementById('optionsContainer'),
        feedbackArea: document.getElementById('feedbackArea'),
        feedbackContent: document.getElementById('feedbackContent'),
        prevBtn: document.getElementById('prevBtn'),
        nextBtn: document.getElementById('nextBtn'),
        submitBtn: document.getElementById('submitBtn'),
        resetBtn: document.getElementById('resetBtn'),
        toggleCard: document.getElementById('toggleCard'),
        closeCard: document.getElementById('closeCard'),
        answerCard: document.getElementById('answerCard'),
        cardOverlay: document.getElementById('cardOverlay'),
        cardGrid: document.getElementById('cardGrid'),
        statTotal: document.getElementById('statTotal'),
        statAnswered: document.getElementById('statAnswered'),
        statCorrect: document.getElementById('statCorrect')
    };
    
    // 初始化
    function init() {
        // 设置初始题目索引
        if (mode === 'random') {
            // 随机模式：从未答题目中随机选择
            const unanswered = getUnansweredIndices();
            if (unanswered.length > 0) {
                state.currentIndex = unanswered[Math.floor(Math.random() * unanswered.length)];
            }
        }
        
        renderQuestion();
        renderAnswerCard();
        updateStats();
        bindEvents();
    }
    
    // 获取未答题目索引
    function getUnansweredIndices() {
        const indices = [];
        for (let i = 0; i < questions.length; i++) {
            if (!state.localAnswers[String(i)]) {
                indices.push(i);
            }
        }
        return indices;
    }
    
    // 渲染题目
    function renderQuestion() {
        const question = questions[state.currentIndex];
        if (!question) return;
        
        // 更新题号
        elements.currentNum.textContent = state.currentIndex + 1;
        
        // 更新题型
        elements.questionType.textContent = question.is_multi ? '多选题' : '单选题';
        
        // 更新题干
        elements.questionText.textContent = question.text;
        
        // 检查是否已答过此题
        const previousAnswer = state.localAnswers[String(state.currentIndex)];
        state.isSubmitted = !!previousAnswer;
        
        // 清空选中状态
        state.selectedOptions = previousAnswer ? previousAnswer.answer.split('') : [];
        
        // 渲染选项
        renderOptions(question, previousAnswer);
        
        // 渲染反馈区
        renderFeedback(question, previousAnswer);
        
        // 更新按钮状态
        updateButtonStates();
        
        // 更新答题卡当前项
        updateCardCurrent();
    }
    
    // 渲染选项
    function renderOptions(question, previousAnswer) {
        elements.optionsContainer.innerHTML = '';
        
        question.options.forEach(option => {
            const div = document.createElement('div');
            div.className = 'option-item';
            div.dataset.letter = option.letter;
            
            // 根据模式和状态添加类
            if (mode === 'memorize') {
                // 背题模式：直接显示正确答案
                if (question.answer.includes(option.letter)) {
                    div.classList.add('correct');
                }
                div.classList.add('disabled');
            } else if (previousAnswer) {
                // 已答过：显示结果
                const userSelected = previousAnswer.answer.includes(option.letter);
                const isCorrect = question.answer.includes(option.letter);
                
                if (userSelected && isCorrect) {
                    div.classList.add('correct');
                } else if (userSelected && !isCorrect) {
                    div.classList.add('wrong');
                } else if (isCorrect) {
                    div.classList.add('correct');
                }
                
                if (userSelected) {
                    div.classList.add('selected');
                }
                div.classList.add('disabled');
            } else {
                // 未答：可选择
                if (state.selectedOptions.includes(option.letter)) {
                    div.classList.add('selected');
                }
            }
            
            div.innerHTML = `
                <span class="option-letter">${option.letter}</span>
                <span class="option-content">${option.content}</span>
            `;
            
            // 添加点击事件（仅在可选择时）
            if (mode !== 'memorize' && !previousAnswer) {
                div.addEventListener('click', () => toggleOption(option.letter, question.is_multi));
            }
            
            elements.optionsContainer.appendChild(div);
        });
    }
    
    // 切换选项选中状态
    function toggleOption(letter, isMulti) {
        if (state.isSubmitted) return;
        
        if (isMulti) {
            // 多选题：切换选中状态
            const index = state.selectedOptions.indexOf(letter);
            if (index > -1) {
                state.selectedOptions.splice(index, 1);
            } else {
                state.selectedOptions.push(letter);
            }
            state.selectedOptions.sort();
        } else {
            // 单选题：只能选一个
            state.selectedOptions = [letter];
        }
        
        // 更新选项显示
        document.querySelectorAll('.option-item').forEach(item => {
            if (state.selectedOptions.includes(item.dataset.letter)) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
        
        updateButtonStates();
    }
    
    // 渲染反馈区
    function renderFeedback(question, previousAnswer) {
        elements.feedbackArea.classList.remove('hidden', 'correct', 'wrong', 'memorize');
        
        if (mode === 'memorize') {
            // 背题模式：直接显示答案
            elements.feedbackArea.classList.add('memorize');
            elements.feedbackContent.innerHTML = `<strong>正确答案：</strong>${question.answer}`;
        } else if (previousAnswer) {
            // 已答过：显示结果
            if (previousAnswer.correct) {
                elements.feedbackArea.classList.add('correct');
                elements.feedbackContent.innerHTML = `<strong>✓ 回答正确！</strong> 正确答案：${question.answer}`;
            } else {
                elements.feedbackArea.classList.add('wrong');
                elements.feedbackContent.innerHTML = `<strong>✗ 回答错误</strong><br>你的答案：${previousAnswer.answer}<br>正确答案：${question.answer}`;
            }
        } else {
            // 未答：隐藏反馈区
            elements.feedbackArea.classList.add('hidden');
        }
    }
    
    // 更新按钮状态
    function updateButtonStates() {
        // 上一题按钮
        if (mode === 'random') {
            elements.prevBtn.disabled = true;  // 随机模式禁用上一题
        } else {
            elements.prevBtn.disabled = state.currentIndex === 0;
        }
        
        // 下一题按钮
        if (mode === 'random') {
            // 随机模式：根据是否还有未答题目决定
            const unanswered = getUnansweredIndices();
            elements.nextBtn.disabled = unanswered.length === 0;
        } else {
            // 顺序/背题模式：根据题目索引决定
            elements.nextBtn.disabled = state.currentIndex === questions.length - 1;
        }
        
        // 提交按钮
        if (mode === 'memorize') {
            elements.submitBtn.style.display = 'none';
        } else if (state.isSubmitted) {
            elements.submitBtn.textContent = '已提交';
            elements.submitBtn.disabled = true;
        } else {
            elements.submitBtn.style.display = '';
            elements.submitBtn.textContent = '提交答案';
            elements.submitBtn.disabled = state.selectedOptions.length === 0;
        }
    }
    
    // 提交答案
    async function submitAnswer() {
        if (state.selectedOptions.length === 0 || state.isSubmitted) return;
        
        const answer = state.selectedOptions.join('');
        const submitIndex = state.currentIndex;  // 🔒 锁定当前题目索引
        
        // 🔒 立即标记为已提交，防止重复提交
        state.isSubmitted = true;
        updateButtonStates();  // 立即更新按钮状态
        
        try {
            const response = await fetch('/api/submit_answer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    project: projectName,
                    index: submitIndex,  // 使用锁定的索引
                    answer: answer
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 更新本地状态（使用锁定的索引）
                state.localAnswers[String(submitIndex)] = {
                    answer: answer,
                    correct: result.correct
                };
                
                // 只有当前还在同一题时才重新渲染
                if (state.currentIndex === submitIndex) {
                    renderQuestion();
                }
                
                renderAnswerCard();
                updateStats();
            } else {
                // 提交失败，恢复状态
                state.isSubmitted = false;
                updateButtonStates();
            }
        } catch (error) {
            console.error('提交答案失败:', error);
            alert('提交失败，请重试');
            // 提交失败，恢复状态
            state.isSubmitted = false;
            updateButtonStates();
        }
    }
    
    // 跳转到指定题目
    function goToQuestion(index) {
        if (index < 0 || index >= questions.length) return;
        
        state.currentIndex = index;
        state.selectedOptions = [];
        state.isSubmitted = false;
        
        renderQuestion();
        
        // 移动端关闭答题卡
        if (window.innerWidth <= 768) {
            closeAnswerCard();
        }
    }
    
    // 上一题
    function goPrev() {
        if (state.currentIndex > 0) {
            goToQuestion(state.currentIndex - 1);
        }
    }
    
    // 下一题
    function goNext() {
        if (mode === 'random') {
            // 随机模式：从未答题目中随机选择下一题
            const unanswered = getUnansweredIndices();
            if (unanswered.length > 0) {
                const randomIndex = unanswered[Math.floor(Math.random() * unanswered.length)];
                goToQuestion(randomIndex);
            } else {
                // 所有题目已答完
                alert('恭喜！所有题目已完成！');
            }
        } else {
            // 顺序模式和背题模式
            if (state.currentIndex < questions.length - 1) {
                goToQuestion(state.currentIndex + 1);
            }
        }
    }
    
    // 渲染答题卡
    function renderAnswerCard() {
        elements.cardGrid.innerHTML = '';
        
        let prevIsMulti = null;
        
        questions.forEach((question, index) => {
            // 检测题目类型变化，插入分隔符
            if (prevIsMulti !== null && question.is_multi !== prevIsMulti) {
                const separator = document.createElement('div');
                separator.className = 'card-separator';
                elements.cardGrid.appendChild(separator);
            }
            prevIsMulti = question.is_multi;
            
            const div = document.createElement('div');
            div.className = 'card-item';
            div.textContent = index + 1;
            div.dataset.index = index;
            
            const answer = state.localAnswers[String(index)];
            if (answer) {
                div.classList.add(answer.correct ? 'correct' : 'wrong');
            }
            
            if (index === state.currentIndex) {
                div.classList.add('current');
            }
            
            div.addEventListener('click', () => goToQuestion(index));
            
            elements.cardGrid.appendChild(div);
        });
    }
    
    // 更新答题卡当前项
    function updateCardCurrent() {
        document.querySelectorAll('.card-item').forEach((item, index) => {
            if (index === state.currentIndex) {
                item.classList.add('current');
            } else {
                item.classList.remove('current');
            }
        });
    }
    
    // 更新统计信息
    function updateStats() {
        const answered = Object.keys(state.localAnswers).length;
        const correct = Object.values(state.localAnswers).filter(a => a.correct).length;
        
        elements.statTotal.textContent = total;
        elements.statAnswered.textContent = answered;
        elements.statCorrect.textContent = correct;
    }
    
    // 重置进度
    async function resetProgress() {
        if (!confirm('确定要重置本项目的所有答题进度吗？此操作不可恢复！')) {
            return;
        }
        
        try {
            const response = await fetch('/api/reset_progress', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    project: projectName
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 重置本地状态
                state.localAnswers = {};
                state.selectedOptions = [];
                state.isSubmitted = false;
                state.currentIndex = 0;
                
                // 重新渲染
                renderQuestion();
                renderAnswerCard();
                updateStats();
                
                alert('进度已重置');
            }
        } catch (error) {
            console.error('重置失败:', error);
            alert('重置失败，请重试');
        }
    }
    
    // 打开答题卡（移动端）
    function openAnswerCard() {
        elements.answerCard.classList.add('active');
        elements.cardOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
    
    // 关闭答题卡（移动端）
    function closeAnswerCard() {
        elements.answerCard.classList.remove('active');
        elements.cardOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }
    
    // 绑定事件
    function bindEvents() {
        elements.prevBtn.addEventListener('click', goPrev);
        elements.nextBtn.addEventListener('click', goNext);
        elements.submitBtn.addEventListener('click', submitAnswer);
        elements.resetBtn.addEventListener('click', resetProgress);
        
        // 答题卡切换（移动端）
        elements.toggleCard.addEventListener('click', openAnswerCard);
        elements.closeCard.addEventListener('click', closeAnswerCard);
        elements.cardOverlay.addEventListener('click', closeAnswerCard);
        
        // 键盘快捷键
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
            
            switch (e.key) {
                case 'ArrowLeft':
                    goPrev();
                    break;
                case 'ArrowRight':
                    goNext();
                    break;
                case 'Enter':
                    if (!state.isSubmitted && state.selectedOptions.length > 0) {
                        submitAnswer();
                    }
                    break;
                case '1':
                case '2':
                case '3':
                case '4':
                case '5':
                case '6':
                case '7':
                case '8':
                    // 数字键选择选项
                    const optionIndex = parseInt(e.key) - 1;
                    const question = questions[state.currentIndex];
                    if (question && question.options[optionIndex] && !state.isSubmitted && mode !== 'memorize') {
                        toggleOption(question.options[optionIndex].letter, question.is_multi);
                    }
                    break;
            }
        });
    }
    
    // 启动应用
    init();
})();
