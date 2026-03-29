import random
from app import app
from models import db, User, Question, QuestionnaireAnswer


def create_test_users(count=10):
    with app.app_context():
        questions = Question.query.order_by(Question.id).all()

        names_male = ['王磊', '刘洋', '陈浩', '赵明', '周杰',
                      '吴斌', '孙鹏', '杨帆', '黄涛', '马骏']
        names_female = ['林小溪', '王诗涵', '陈雨薇', '赵晴', '周悦',
                        '吴婷', '孙雅', '杨柳', '黄莺', '马琳']
        departments = ['信息科学技术学院', '数学科学学院', '中国语言文学系',
                       '光华管理学院', '法学院', '物理学院',
                       '化学与分子工程学院', '生命科学学院', '外国语学院', '新闻与传播学院']

        created = 0
        for i in range(count):
            gender = random.choice(['male', 'female'])
            target_gender = 'female' if gender == 'male' else 'male'

            if gender == 'male':
                nickname = names_male[i % len(names_male)]
            else:
                nickname = names_female[i % len(names_female)]

            email = f'testuser{i}@stu.pku.edu.cn'

            if User.query.filter_by(email=email).first():
                continue

            user = User(
                email=email,
                nickname=nickname,
                gender=gender,
                target_gender=target_gender,
                grade=random.choice(['大一', '大二', '大三', '大四', '研一', '研二']),
                department=random.choice(departments),
                bio=f'大家好，我是{nickname}，希望在这里遇到有趣的灵魂～',
                wechat=f'wx_{nickname}',
                is_verified=True,
                questionnaire_done=True
            )
            db.session.add(user)
            db.session.flush()

            for q in questions:
                ans = QuestionnaireAnswer(
                    user_id=user.id,
                    question_id=q.id,
                    answer=random.randint(0, 3)
                )
                db.session.add(ans)

            created += 1

        db.session.commit()
        total = User.query.count()
        print(f"✅ 新建 {created} 个测试用户，当前共 {total} 个用户")


def test_matching():
    from matching import run_matching
    with app.app_context():
        pairs = run_matching(round_number=99)
        print(f"\n匹配结果（共 {len(pairs)} 对）:")
        for uid1, uid2, score in pairs:
            u1 = User.query.get(uid1)
            u2 = User.query.get(uid2)
            print(f'  {u1.nickname}({u1.gender}) ❤️  {u2.nickname}({u2.gender})  匹配度: {score:.2%}')


if __name__ == '__main__':
    create_test_users(10)
    test_matching()