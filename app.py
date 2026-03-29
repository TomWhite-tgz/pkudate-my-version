import re
import os
import json
import random
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from config import Config
from models import db, User, Question, QuestionnaireAnswer, MatchResult, VerificationCode
from matching import run_matching
import bleach
from collections import defaultdict
from threading import Lock

# ==================== App 初始化 ====================
app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response
# ==================== 工具函数 ====================

class SimpleRateLimiter:
    def __init__(self):
        self._attempts = defaultdict(list)
        self._lock = Lock()

    def is_limited(self, key, max_attempts, window_seconds):
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)
        with self._lock:
            self._attempts[key] = [t for t in self._attempts[key] if t > cutoff]
            if len(self._attempts[key]) >= max_attempts:
                return True
            self._attempts[key].append(now)
            return False

limiter = SimpleRateLimiter()

def clean(text, max_length=500):
    """清洗用户输入"""
    if not text:
        return ""
    return bleach.clean(text, tags=[], strip=True)[:max_length].strip()

def is_valid_edu_email(email):
    """校验教育邮箱"""
    if app.config.get('DEV_MODE') and app.config.get('DEV_ALLOW_ANY_EMAIL'):
        return re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email) is not None

    domain = app.config['ALLOWED_EMAIL_DOMAIN']
    pattern = rf'^[a-zA-Z0-9_.+-]+@{re.escape(domain)}$'
    return re.match(pattern, email.lower()) is not None


def send_email(to_email, subject, body):
    """发送邮件"""
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = f'PKU Date <{app.config["MAIL_DEFAULT_SENDER"]}>'
    msg['To'] = to_email

    with smtplib.SMTP_SSL(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.sendmail(app.config['MAIL_DEFAULT_SENDER'], to_email, msg.as_string())


def send_verification_code(email, purpose='login'):
    """发送验证码的通用函数"""
    # 冷却检查（这部分完全不动）
    recent = VerificationCode.query.filter_by(email=email)\
        .order_by(VerificationCode.created_at.desc()).first()
    if recent:
        elapsed = (datetime.utcnow() - recent.created_at).total_seconds()
        if elapsed < app.config['CODE_COOLDOWN_SECONDS']:
            remaining = int(app.config['CODE_COOLDOWN_SECONDS'] - elapsed)
            return False, f'请{remaining}秒后重试'

    code = str(random.randint(100000, 999999))

    vc = VerificationCode(email=email, code=code, purpose=purpose)
    db.session.add(vc)
    db.session.commit()

    # 开发模式：打印到终端（这部分完全不动）
    print("\n" + "=" * 50)
    print(f"  📧 验证码（{purpose}）")
    print(f"  邮箱: {email}")
    print(f"  验证码: {code}")
    print("=" * 50 + "\n")

    # ===== 只改这里：把邮件正文写好看 =====
    if not app.config.get('DEV_MODE'):
        try:
            send_email(
                to_email=email,
                subject='【PKU Date】你的验证码',
                body=f'''你好！

你的 PKU Date 验证码是：

    {code}

有效期 5 分钟，请尽快使用。
如非本人操作，请忽略此邮件。

—— PKU Date · 让算法帮你找到燕园里的 TA'''
            )
        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False, '发送失败，请稍后重试'

    return True, '验证码已发送'


def verify_code(email, code, purpose='login'):
    """验证验证码"""
    vc = VerificationCode.query.filter_by(
        email=email, code=code, purpose=purpose, is_used=False
    ).order_by(VerificationCode.created_at.desc()).first()

    if not vc:
        return False, '验证码错误'

    # 检查过期
    if (datetime.utcnow() - vc.created_at).total_seconds() > app.config['CODE_EXPIRE_SECONDS']:
        return False, '验证码已过期，请重新获取'

    vc.is_used = True
    db.session.commit()
    return True, 'OK'


# ==================== API 接口 ====================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', bg_image='pku.jpg'), 404

@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return render_template('404.html', bg_image='pku.jpg'), 500

@app.route('/api/send-code', methods=['POST'])
def api_send_code():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    purpose = data.get('purpose', 'login')
    client_ip = request.remote_addr

    if not is_valid_edu_email(email):
        return jsonify({'error': f'请使用 @{app.config["ALLOWED_EMAIL_DOMAIN"]} 邮箱'}), 400

    # IP 限流：每小时最多15次
    if limiter.is_limited(f"code_ip:{client_ip}", 15, 3600):
        return jsonify({'error': '请求过于频繁，请稍后再试'}), 429

    # 邮箱限流：每天最多8次
    if limiter.is_limited(f"code_email:{email}", 8, 86400):
        return jsonify({'error': '今日验证码次数已用完'}), 429

    success, message = send_verification_code(email, purpose)
    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 429



@app.route('/api/stats')
def api_stats():
    """返回平台统计数据"""
    total_users = User.query.filter_by(is_verified=True).count()
    total_matches = MatchResult.query.count() // 2
    return jsonify({
        'total_users': total_users,
        'total_matches': total_matches
    })


# ==================== 首页 ====================

@app.route('/')
def index():
    return render_template('index.html')


# ==================== 注册 ====================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        code = request.form.get('code', '').strip()
        nickname = request.form.get('nickname', '').strip()

        if not is_valid_edu_email(email):
            flash(f'请使用 @{app.config["ALLOWED_EMAIL_DOMAIN"]} 邮箱', 'error')
            return render_template('register.html', bg_image='register.jpg')

        if User.query.filter_by(email=email).first():
            flash('该邮箱已注册，请直接登录', 'error')
            return render_template('register.html', bg_image='register.jpg')

        ok, msg = verify_code(email, code, purpose='register')
        if not ok:
            flash(msg, 'error')
            return render_template('register.html', bg_image='register.jpg')

        if not nickname or len(nickname) > 50:
            flash('请输入昵称（50字以内）', 'error')
            return render_template('register.html', bg_image='register.jpg')

        user = User(email=email, nickname=nickname, is_verified=True)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash('注册成功！请完善个人资料', 'success')
        return redirect(url_for('profile'))

    return render_template('register.html', bg_image='register.jpg')


# ==================== 登录 ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        code = request.form.get('code', '').strip()

        if not is_valid_edu_email(email):
            flash(f'请使用 @{app.config["ALLOWED_EMAIL_DOMAIN"]} 邮箱', 'error')
            return render_template('login.html', bg_image='register.jpg')

        ok, msg = verify_code(email, code, purpose='login')
        if not ok:
            flash(msg, 'error')
            return render_template('login.html', bg_image='register.jpg')

        user = User.query.filter_by(email=email).first()
        if not user:
            flash('该邮箱未注册，请先注册', 'error')
            return render_template('login.html', bg_image='register.jpg')

        login_user(user)
        return redirect(url_for('dashboard'))

    return render_template('login.html', bg_image='register.jpg')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
# ==================== Dashboard ====================
@app.route('/dashboard')
@login_required
def dashboard():
    matches = MatchResult.query.filter_by(user_id=current_user.id)\
        .order_by(MatchResult.score.desc()).all()
    user_count = User.query.filter_by(questionnaire_done=True, is_verified=True).count()

    last = MatchResult.query.order_by(MatchResult.round_number.desc()).first()
    next_round = (last.round_number + 1) if last else 1

    return render_template('dashboard.html', user=current_user, matches=matches,
                           user_count=user_count, next_round=next_round, bg_image='profile.jpg')


# ==================== 个人资料 ====================
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.nickname = clean(request.form.get('nickname', ''), 50)
        current_user.gender = request.form.get('gender')
        current_user.target_gender = request.form.get('target_gender')
        current_user.grade = request.form.get('grade', '').strip()
        current_user.department = request.form.get('department', '').strip()
        current_user.bio = clean(request.form.get('bio', ''), 500)
        current_user.wechat = clean(request.form.get('wechat', ''), 50)

        db.session.commit()
        flash('资料已更新', 'success')
        return redirect(url_for('dashboard'))

    return render_template('profile.html', user=current_user, bg_image='profile.jpg')


# ==================== 问卷 ====================
@app.route('/questionnaire', methods=['GET', 'POST'])
@login_required
def questionnaire():
    questions = Question.query.order_by(Question.order).all()

    if request.method == 'POST':
        try:
            QuestionnaireAnswer.query.filter_by(user_id=current_user.id).delete()

            answered_count = 0
            for q in questions:
                answer_val = request.form.get(f'q_{q.id}')
                if answer_val is not None:
                    ans = QuestionnaireAnswer(
                        user_id=current_user.id,
                        question_id=q.id,
                        answer=int(answer_val)
                    )
                    db.session.add(ans)
                    answered_count += 1

            # 确保所有题都答了
            if answered_count < len(questions):
                db.session.rollback()
                flash('请回答所有问题', 'error')
                for q in questions:
                    q.options_list = json.loads(q.options)
                return render_template('questionnaire.html', questions=questions, bg_image='questionnaire.jpg')

            current_user.questionnaire_done = True
            db.session.commit()
            flash('问卷提交成功！等待匹配结果', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            print(f"问卷提交错误: {e}")
            flash('提交失败，请重试', 'error')

    for q in questions:
        q.options_list = json.loads(q.options)

    return render_template('questionnaire.html', questions=questions, bg_image='questionnaire.jpg')


# ==================== 匹配结果 ====================
@app.route('/results')
@login_required
def results():
    matches = MatchResult.query.filter_by(user_id=current_user.id)\
        .order_by(MatchResult.score.desc()).all()
    return render_template('results.html', matches=matches, bg_image='register.jpg')


# ==================== 注销账号 ====================
@app.route('/account/delete', methods=['GET', 'POST'])
@login_required
def delete_account():
    if request.method == 'POST':
        confirm = request.form.get('confirm', '')

        if confirm != 'DELETE':
            flash('请输入 DELETE 确认', 'error')
            return render_template('delete_account.html', bg_image='profile.jpg')

        user_id = current_user.id
        QuestionnaireAnswer.query.filter_by(user_id=user_id).delete()
        MatchResult.query.filter(
            (MatchResult.user_id == user_id) |
            (MatchResult.matched_user_id == user_id)
        ).delete(synchronize_session=False)

        user = User.query.get(user_id)
        logout_user()
        db.session.delete(user)
        db.session.commit()

        flash('账号已注销，所有数据已删除', 'success')
        return redirect(url_for('index'))

    return render_template('delete_account.html', bg_image='profile.jpg')


# ==================== 管理员：触发匹配 ====================

@app.route('/admin/run-matching', methods=['POST'])
@login_required
def admin_run_matching():
    admin_emails = ['your_email@stu.pku.edu.cn']  # 改成你的邮箱
    if current_user.email not in admin_emails:
        flash('无权操作', 'error')
        return redirect(url_for('dashboard'))

    last = MatchResult.query.order_by(MatchResult.round_number.desc()).first()
    round_num = (last.round_number + 1) if last else 1

    pairs = run_matching(round_number=round_num)

    # 匹配完成后通知每个用户
    for uid1, uid2, score in pairs:
        u1 = User.query.get(uid1)
        u2 = User.query.get(uid2)

        if app.config.get('DEV_MODE'):
            print(f"  📧 通知 {u1.nickname}({u1.email}): 匹配成功")
            print(f"  📧 通知 {u2.nickname}({u2.email}): 匹配成功")
        else:
            try:
                for u in [u1, u2]:
                    send_email(
                        to_email=u.email,
                        subject='【PKU Date】你的匹配结果来啦 💕',
                        body=f'{u.nickname}，你好！\n\n'
                             f'第 {round_num} 轮匹配已完成，你已成功匹配！\n'
                             f'请登录 PKU Date 查看你的匹配对象。\n\n'
                             f'祝好运 💕'
                    )
            except Exception as e:
                print(f"通知邮件发送失败: {e}")

    flash(f'匹配完成！本轮共匹配 {len(pairs)} 对，已通知所有用户', 'success')
    return redirect(url_for('dashboard'))

@app.route('/privacy')
def privacy():
    return render_template('privacy.html', bg_image='pku.jpg')

# ==================== 启动 ====================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)