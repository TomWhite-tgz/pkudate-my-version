import json
from app import app
from models import db, Question


def init_database():
    with app.app_context():
        db.create_all()

        # 如果已有题目就跳过
        if Question.query.first():
            print("题目已存在，跳过初始化")
            return

        questions = [
            # ===== 性格类 =====
            {
                "text": "周末你更愿意？",
                "category": "lifestyle",
                "weight": 1.5,
                "options": json.dumps(["宅在家看剧/打游戏", "出去逛街看电影", "参加社交活动/聚会", "运动/户外活动"], ensure_ascii=False),
                "order": 1
            },
            {
                "text": "你认为自己是？",
                "category": "personality",
                "weight": 2.0,
                "options": json.dumps(["内向安静", "偏内向但熟了话多", "偏外向但也享受独处", "外向活泼"], ensure_ascii=False),
                "order": 2
            },
            {
                "text": "对另一半的颜值要求？",
                "category": "preference",
                "weight": 1.0,
                "options": json.dumps(["颜值即正义", "好看优先但也看内在", "内在更重要", "眼缘对了就行"], ensure_ascii=False),
                "order": 3
            },
            {
                "text": "你的作息时间？",
                "category": "lifestyle",
                "weight": 1.5,
                "options": json.dumps(["早睡早起(11点前)", "正常作息(12点左右)", "轻度夜猫(1点左右)", "重度夜猫(2点以后)"], ensure_ascii=False),
                "order": 4
            },
            {
                "text": "恋爱中你更偏向？",
                "category": "love_style",
                "weight": 2.0,
                "options": json.dumps(["每天都要联系", "保持适当联系就好", "各自独立偶尔约会", "顺其自然不刻意"], ensure_ascii=False),
                "order": 5
            },
            {
                "text": "吵架了你会？",
                "category": "love_style",
                "weight": 2.0,
                "options": json.dumps(["主动道歉和好", "冷静一下再沟通", "等对方来找我", "冷战到对方服软"], ensure_ascii=False),
                "order": 6
            },
            {
                "text": "你对游戏的态度？",
                "category": "hobby",
                "weight": 1.0,
                "options": json.dumps(["重度游戏玩家", "偶尔玩玩", "不玩但不反感", "不喜欢玩游戏"], ensure_ascii=False),
                "order": 7
            },
            {
                "text": "理想的约会方式？",
                "category": "preference",
                "weight": 1.5,
                "options": json.dumps(["一起吃好吃的", "看电影/展览", "公园散步聊天", "一起宅着各干各的"], ensure_ascii=False),
                "order": 8
            },
            {
                "text": "你怎么看待恋爱中的经济问题？",
                "category": "values",
                "weight": 2.0,
                "options": json.dumps(["AA制", "谁有钱谁出", "男生多出一些", "一起存钱理财"], ensure_ascii=False),
                "order": 9
            },
            {
                "text": "你期望的恋爱节奏？",
                "category": "love_style",
                "weight": 1.5,
                "options": json.dumps(["快速确定关系", "先做朋友慢慢发展", "暧昧期长一点没关系", "看感觉随缘"], ensure_ascii=False),
                "order": 10
            },
        ]

        for q_data in questions:
            q = Question(**q_data)
            db.session.add(q)

        db.session.commit()
        print(f"✅ 数据库初始化完成，已添加 {len(questions)} 道题目")


if __name__ == '__main__':
    init_database()