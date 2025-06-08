import os
import base64
from volcenginesdkarkruntime import Ark

class VolcEngineAI:
    def __init__(self, api_key):
        """
        初始化火山引擎大模型客户端
        :param api_key: 火山方舟API Key
        """
        self.api_key = api_key
        self.client = Ark(
            # 此为默认路径，您可根据业务所在地域进行配置
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=self.api_key
        )
    
    def chat_completion(self, prompt="这是哪里？", model="doubao-1.5-pro-32k-250115", max_tokens=1000, temperature=0.7, stream=False):
        """
        与火山引擎大模型对话
        :param prompt: 输入提示
        :param model: 模型ID
        :param max_tokens: 最大输出token数
        :param temperature: 温度参数，控制输出的随机性
        :param stream: 是否使用流式输出
        :return: 模型响应
        """
        try:
            # 构建消息列表
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            # 调用模型
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream
            )
            
            # 处理流式响应
            if stream:
                response_text = ""
                for chunk in completion:
                    if not chunk.choices:
                        continue
                    delta_content = chunk.choices[0].delta.content
                    if delta_content:
                        response_text += delta_content
                        print(delta_content, end="")
                print()  # 换行
                return {"choices": [{"message": {"content": response_text}}]}
            
            return completion
        except Exception as e:
            print(f"API请求失败: {e}")
            return None
    
    def encode_image(self, image_path):
        """
        将指定路径的图片转为Base64编码
        :param image_path: 图片路径
        :return: Base64编码后的图片数据
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"图片编码失败: {e}")
            return None
    
    def vision_chat_completion(self, text_prompt="这是哪里？", image_url="", image_path=None, image_format="jpeg", model="doubao-1.5-vision-lite-250315"):
        """
        与支持视觉的火山引擎大模型对话
        :param text_prompt: 文本提示
        :param image_url: 图片URL（与image_path二选一）
        :param image_path: 本地图片路径（与image_url二选一）
        :param image_format: 图片格式，支持jpeg、png、webp等
        :param model: 模型ID
        :return: 模型响应
        """
        try:
            # 构建消息列表
            content = []
            
            # 处理图片内容
            if image_path:
                # 如果提供了本地图片路径，将图片转为Base64编码
                base64_image = self.encode_image(image_path)
                if base64_image:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{image_format};base64,{base64_image}"
                        }
                    })
            elif image_url:
                # 如果提供了图片URL，直接使用
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                })
            
            # 添加文本内容
            content.append({"type": "text", "text": text_prompt})
            
            # 调用模型
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            )
            
            return response
        except Exception as e:
            print(f"视觉API请求失败: {e}")
            return None


# 示例用法
if __name__ == "__main__":
    # 在这里填入您的API密钥，或从环境变量获取
    API_KEY = os.environ.get("ARK_API_KEY", "your_api_key_here")
    
    ai = VolcEngineAI(api_key=API_KEY)
    
    # 文本对话示例
    result = ai.chat_completion("你好，请介绍一下你自己")
    if result:
        print("模型回复:", result.choices[0].message.content)
    
    # 视觉对话示例 - 使用URL
    # vision_result = ai.vision_chat_completion(
    #     text_prompt="这是哪里？", 
    #     image_url="https://ark-project.tos-cn-beijing.ivolces.com/images/view.jpeg"
    # )
    # if vision_result:
    #     print("视觉模型回复:", vision_result.choices[0].message.content)
    
    # 视觉对话示例 - 使用本地图片
    # vision_result_local = ai.vision_chat_completion(
    #     text_prompt="图片里讲了什么?",
    #     image_path="testpng/screenshot.png",
    #     image_format="png"
    # )
    # if vision_result_local:
    #     print("视觉模型回复(本地图片):", vision_result_local.choices[0].message.content)