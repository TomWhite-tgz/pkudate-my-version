from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """用户表 —— 无密码版"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    nickname = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)

    # 基本资料
    gender = db.Column(db.String(10))
    target_gender = db.Column(db.String(10))
    grade = db.Column(db.String(20))
    department = db.Column(db.String(100))
    bio = db.Column(db.Text)
    wechat = db.Column(db.String(50))

    # 问卷
    questionnaire_done = db.Column(db.Boolean, default=False)

    # 关联
    answers = db.relationship('QuestionnaireAnswer', backref='user', lazy=True)


class Question(db.Model):
    """问卷题目表"""
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50))
    weight = db.Column(db.Float, default=1.0)
    options = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, default=0)


class QuestionnaireAnswer(db.Model):
    """用户答卷表"""
    __tablename__ = 'answers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    answer = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    question = db.relationship('Question')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'question_id', name='uq_user_question'),
    )


class MatchResult(db.Model):
    """匹配结果表"""
    __tablename__ = 'match_results'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    matched_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    round_number = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])
    matched_user = db.relationship('User', foreign_keys=[matched_user_id])


class VerificationCode(db.Model):
    """邮箱验证码表"""
    __tablename__ = 'verification_codes'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    code = db.Column(db.String(6), nullable=False)
    purpose = db.Column(db.String(20), default='login')  # login / register
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_used = db.Column(db.Boolean, default=False)