from openai import OpenAI
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class DeepSeekBot:
    def __init__(self):
        # 配置
        self.api_key = "" # 填写你的API密钥
        self.base_url = "https://api.deepseek.com"
        self.max_history = 20  # 限制历史消息数量

        # 初始化 OpenAI 客户端
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

        # 角色设定
        self.character_setting = """
            你是一个微信聊天助手，你将获取一部分聊天记录，格式为一个从旧到新排列的列表数据：[{'boundingBox': 'x1,y1,x2,y2,x3,y3,x4,y4(此消息四个角的x,y位置坐标)', 'text': '此消息内容', , 'type': 1为己方消息 2为对方消息 3为其他消息 },.....]。
            如果最新的一条消息是对方的消息，则联系上下文对其进行回复。
        """
        # 初始化消息历史
        self.messages = [
            {"role": "system", "content": self.character_setting}
        ]

    def get_ai_reply(self, user_msg):
        # 添加用户消息
        self.messages.append({"role": "user", "content": str(user_msg)})

        # 历史消息截断（保留 System Prompt）
        if len(self.messages) > self.max_history:
            # 保留 system prompt (index 0) 和最近的消息
            self.messages = [self.messages[0]] + self.messages[-(self.max_history - 1):]

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=self.messages,
                max_tokens=1024,
                temperature=0.5,
                stream=False
            )
            reply_content = response.choices[0].message.content
            logging.info(f"收到来自 DeepSeek 的回复: {reply_content}")

            # 记录助手回复
            self.messages.append({"role": "assistant", "content": reply_content})
            return reply_content
        except Exception as e:
            logging.error(f"API 请求失败: {e}")
            return "（逻辑演算单元连接中断...）"
