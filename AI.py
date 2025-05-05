import os
import time
import re
import traceback
from datetime import datetime

import openai 

class ChatAI:
    """聊天AI处理器，读取聊天记录并调用AI模型生成回复"""
    
    def __init__(self, log_file='chat_log.txt'):
        """初始化聊天AI处理器
        
        Args:
            log_file: 聊天日志文件路径
        """
        self.log_file = log_file
        
        # 固定API密钥设置
        self.api_key = 'sk-4e3469a3dd8f493e83f683218cbbbb7c'
        
        # 设置OpenAI API
        self.setup_openai()
        
    def setup_openai(self):
        """设置OpenAI API客户端"""
        # 设置环境变量
        os.environ['OPENAI_API_KEY'] = self.api_key
        
        # 初始化OpenAI客户端
        self.client = openai.OpenAI(
            api_key=self.api_key, # 如果你没有配置环境变量，使用 api_key="your-api-key" 替换
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", # 这里使用的是阿里云的大模型，如果需要使用其他平台，请参考对应的开发文档后对应修改
        )
        print(f"AI客户端初始化成功")
        
    def parse_chat_messages(self):
        """解析聊天日志文件
        
        Returns:
            list: 解析后的聊天消息列表
        """
        messages = []
        current_time = None
        
        try:
            if not os.path.exists(self.log_file):
                print(f"聊天日志文件 {self.log_file} 不存在")
                return []
                
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 匹配时间消息
                time_match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[时间\] (.+)', line)
                if time_match:
                    current_time = time_match.group(2)
                    messages.append(['Time', current_time])
                    continue
                
                # 匹配自己发送的消息
                self_match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[自己\] (.+)', line)
                if self_match:
                    content = self_match.group(2)
                    messages.append(['Self', content])
                    continue
                
                # 匹配系统消息
                sys_match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[系统\] (.+)', line)
                if sys_match:
                    content = sys_match.group(2)
                    if not content.startswith('错误:'):  # 忽略错误消息
                        messages.append(['SYS', content])
                    continue
                
                # 匹配聊天消息 [时间] [聊天名称] 内容
                chat_match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[([^\]]+)\] (.+)', line)
                if chat_match:
                    chat_name = chat_match.group(2)
                    content = chat_match.group(3)
                    if chat_name not in ['时间', '系统', '自己']:
                        messages.append([chat_name, content])
            
            print(f"从聊天日志文件解析出 {len(messages)} 条消息")
            return messages
        
        except Exception as e:
            print(f"解析聊天日志文件时出错: {str(e)}")
            traceback.print_exc()
            return []
    
    def format_messages_for_ai(self, messages, max_messages=20):
        """将聊天消息格式化为AI输入格式
        
        Args:
            messages: 聊天消息列表
            max_messages: 最大消息数量
            
        Returns:
            list: OpenAI格式的消息列表
        """
        # 系统提示词
        system_prompt = "给你一段对话，是A正在和B进行对话。请一句话一句话的思考A下一句会说什么，然后直接返回要发送的内容。不要在返回的内容里出现A和B，只返回要发送的内容。"
        
        # 初始化消息列表，添加系统消息
        ai_messages = [{"role": "system", "content": system_prompt}]
        
        # 如果消息超过限制，只取最后max_messages条
        if len(messages) > max_messages:
            messages = messages[-max_messages:]
        
        # 跳过Time和SYS类型的消息，将其他消息添加到AI输入中
        for msg in messages:
            msg_type = msg[0]
            content = msg[1]
            
            # 跳过Time和空消息
            if msg_type == 'Time' or not content:
                continue
                
            # 跳过系统消息
            if msg_type == 'SYS':
                continue
                
            # 所有消息都使用user角色，但添加标识符区分
            if msg_type == 'Self':
                ai_messages.append({"role": "user", "content": f"A: {content}"})
            else:
                # 其他消息也是user角色，但用B标识
                ai_messages.append({"role": "user", "content": f"B: {content}"})
        
        return ai_messages
    
    def call_ai_model(self, messages=None, stream=True):
        """调用AI模型生成回复
        
        Args:
            messages: 消息列表，如果为None则自动从文件加载
            stream: 是否使用流式输出
            
        Returns:
            str: AI模型的回复
        """
        # 如果没有提供消息，从文件加载
        if messages is None:
            chat_messages = self.parse_chat_messages()
            messages = self.format_messages_for_ai(chat_messages)
        
        # 打印发送给AI的消息
        print("\n-------- 发送给AI的消息 --------")
        for i, msg in enumerate(messages):
            role = msg['role']
            content_preview = msg['content'][:50] + ('...' if len(msg['content']) > 50 else '')
            print(f"{i+1}. [{role}]: {content_preview}")
        print("--------------------------------\n")
        
        try:
            # 调用AI模型
            print(f"正在调用AI模型...")
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model="qwen-turbo",  # 使用默认模型
                messages=messages,
                stream=stream
            )
            
            # 处理响应
            if stream:
                # 流式响应
                full_response = ""
                print("\n-------- AI回复 --------")
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        print(content, end='', flush=True)
                print("\n-------------------------\n")
                
                elapsed_time = time.time() - start_time
                print(f"AI响应完成，用时: {elapsed_time:.2f}秒")
                
                # 记录AI回复到文件
                self.log_ai_response(full_response)
                
                return full_response
            else:
                # 非流式响应
                response_content = response.choices[0].message.content
                elapsed_time = time.time() - start_time
                
                print("\n-------- AI回复 --------")
                print(response_content)
                print("-------------------------\n")
                print(f"AI响应完成，用时: {elapsed_time:.2f}秒")
                
                # 记录AI回复到文件
                self.log_ai_response(response_content)
                
                return response_content
                
        except Exception as e:
            error_msg = f"调用AI模型时出错: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            return f"错误: {error_msg}"
    
    def log_ai_response(self, response):
        """记录AI的回复到日志文件
        
        Args:
            response: AI的回复内容
        """
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n[{current_time}] [AI回复]\n{response}\n")
            print(f"AI回复已记录到日志文件: {self.log_file}")
        except Exception as e:
            print(f"记录AI回复时出错: {str(e)}")
    
    def run(self):
        """执行AI调用流程"""
        print(f"开始运行聊天AI处理，读取聊天记录: {self.log_file}")
        
        # 解析聊天记录
        chat_messages = self.parse_chat_messages()
        
        if not chat_messages:
            print("未找到有效的聊天记录，无法调用AI")
            return
        
        # 格式化消息并调用AI
        ai_messages = self.format_messages_for_ai(chat_messages)
        return self.call_ai_model(ai_messages)


# 如果直接运行此脚本
if __name__ == "__main__":
    try:
        chat_ai = ChatAI()
        chat_ai.run()
    except Exception as e:
        print(f"运行ChatAI时出错: {str(e)}")
        traceback.print_exc() 