import numpy as np
from models import db, User, QuestionnaireAnswer, Question, MatchResult


def get_user_vector(user_id):
    """获取用户的答题向量"""
    answers = QuestionnaireAnswer.query.filter_by(user_id=user_id)\
        .order_by(QuestionnaireAnswer.question_id).all()
    if not answers:
        return None

    questions = Question.query.order_by(Question.id).all()
    question_weights = {q.id: q.weight for q in questions}

    vector = []
    weights = []
    for ans in answers:
        vector.append(ans.answer)
        weights.append(question_weights.get(ans.question_id, 1.0))

    return np.array(vector, dtype=float), np.array(weights, dtype=float)


def cosine_similarity_weighted(vec1, vec2, weights):
    """加权余弦相似度"""
    weighted_v1 = vec1 * weights
    weighted_v2 = vec2 * weights

    dot = np.dot(weighted_v1, weighted_v2)
    norm1 = np.linalg.norm(weighted_v1)
    norm2 = np.linalg.norm(weighted_v2)

    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(dot / (norm1 * norm2))


def compute_similarity(user1_id, user2_id):
    """计算两个用户的匹配度"""
    data1 = get_user_vector(user1_id)
    data2 = get_user_vector(user2_id)

    if data1 is None or data2 is None:
        return 0.0

    vec1, weights1 = data1
    vec2, weights2 = data2

    # 取两人权重的平均
    weights = (weights1 + weights2) / 2

    if len(vec1) != len(vec2):
        return 0.0

    return cosine_similarity_weighted(vec1, vec2, weights)


def run_matching(round_number=1):
    """
    执行全局匹配
    简单贪心策略：按相似度从高到低配对
    """
    # 获取所有完成问卷的用户
    users = User.query.filter_by(questionnaire_done=True, is_verified=True).all()

    # 按性别偏好分组
    candidates = {}
    for u in users:
        key = (u.gender, u.target_gender)
        candidates.setdefault(key, []).append(u)

    matched_pairs = []
    already_matched = set()

    # 为每个用户找最佳匹配
    all_pairs = []
    for u in users:
        if u.id in already_matched:
            continue
        # 找对方池：对方性别=我想要的 且 对方想要的=我的性别
        potential = [
            p for p in users
            if p.id != u.id
            and p.id not in already_matched
            and p.gender == u.target_gender
            and p.target_gender == u.gender
        ]

        for p in potential:
            score = compute_similarity(u.id, p.id)
            all_pairs.append((score, u.id, p.id))

    # 按分数降序排列，贪心匹配
    all_pairs.sort(reverse=True, key=lambda x: x[0])

    for score, uid1, uid2 in all_pairs:
        if uid1 in already_matched or uid2 in already_matched:
            continue

        # 存储匹配结果（双向）
        result1 = MatchResult(
            user_id=uid1,
            matched_user_id=uid2,
            score=score,
            round_number=round_number
        )
        result2 = MatchResult(
            user_id=uid2,
            matched_user_id=uid1,
            score=score,
            round_number=round_number
        )
        db.session.add(result1)
        db.session.add(result2)

        already_matched.add(uid1)
        already_matched.add(uid2)
        matched_pairs.append((uid1, uid2, score))

    db.session.commit()
    return matched_pairs