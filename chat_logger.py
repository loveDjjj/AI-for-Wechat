from wxauto import WeChat
import time
from datetime import datetime
import os
import re
import sys
import json

class ChatLogger:
    """聊天日志记录器：将微信消息记录到文本文件中"""
    
    def __init__(self, log_file="chat_log.txt", format_file="chat_messages.txt"):
        """初始化聊天日志记录器
        
        Args:
            log_file: 日志文件名（详细日志）
            format_file: 格式化消息文件名（仅包含格式化的消息列表）
        """
        self.log_file = log_file
        self.format_file = format_file
        self.listen_list = []
        self.last_message_time = None
        self.message_list = []  # 存储所有消息的列表
        self.current_chat = None  # 保存当前活跃的聊天对象
        
        # 检查并初始化微信
        try:
            print("正在连接微信，请确保微信已经打开并处于前台...")
            self.wx = WeChat()
            # 尝试获取微信窗口信息，测试连接是否成功
            wx_title = self.wx.GetSessionList()
            print(f"微信连接成功！找到 {len(wx_title) if wx_title else 0} 个会话")
        except Exception as e:
            print(f"连接微信失败: {str(e)}")
            print("请确保：")
            print("1. 微信已经打开并且没有被最小化")
            print("2. 微信窗口处于可见状态（不在其他窗口下方）")
            print("3. 您当前的微信版本与wxauto库兼容")
            sys.exit(1)
            
        self._init_log_file()
        
    def _init_log_file(self):
        """初始化日志文件"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"===== 微信聊天记录 - 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====\n\n")
        
        # 初始化格式化消息文件
        with open(self.format_file, 'w', encoding='utf-8') as f:
            f.write("# 微信聊天记录（格式化）\n\n")
            
        print(f"已创建聊天日志文件: {self.log_file}")
        print(f"已创建格式化消息文件: {self.format_file}")
        self.last_message_time = datetime.now()
        
    def _append_to_file(self, text):
        """追加内容到日志文件"""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(text + "\n")
            
    def _update_formatted_messages(self):
        """更新格式化消息文件，写入完整的消息列表"""
        with open(self.format_file, 'w', encoding='utf-8') as f:
            f.write("# 微信聊天记录（格式化）\n\n")
            f.write(str(self.message_list))
            
    def _add_message(self, msg_type, sender, content):
        """添加消息到消息列表并更新文件
        
        Args:
            msg_type: 消息类型 ('Time', 'Self', 'SYS' 或聊天名称)
            sender: 发送者
            content: 消息内容
        """
        # 添加到消息列表
        if msg_type == 'Time':
            self.message_list.append(['Time', content])
        elif msg_type == 'SYS':
            self.message_list.append(['SYS', content])
        elif msg_type == 'Self':
            self.message_list.append(['Self', content])
        else:
            # 朋友消息，使用聊天名称
            self.message_list.append([sender, content])
            
        # 更新格式化消息文件
        self._update_formatted_messages()
        
        # 记录到详细日志
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if msg_type == 'Time':
            log_text = f"[{current_time}] [时间] {content}"
        elif msg_type == 'SYS':
            log_text = f"[{current_time}] [系统] {content}"
        elif msg_type == 'Self':
            log_text = f"[{current_time}] [自己] {content}"
        else:
            log_text = f"[{current_time}] [{sender}] {content}"
            
        self._append_to_file(log_text)
        
    def _load_history_messages(self, chat_name):
        """加载并保存聊天的历史消息
        
        Args:
            chat_name: 聊天对象名称
            
        Returns:
            bool: 是否成功加载历史消息
        """
        try:
            print(f"正在加载 '{chat_name}' 的历史消息...")
            
            # 确保切换到正确的聊天窗口
            self.wx.ChatWith(chat_name)
            time.sleep(1)  # 等待窗口切换完成
            
            # 加载更多历史消息
            self.wx.LoadMoreMessage()
            time.sleep(1)  # 等待加载完成
            
            # 获取当前聊天窗口的所有消息
            messages = self.wx.GetAllMessage()
            
            if not messages:
                print(f"未找到 '{chat_name}' 的历史消息")
                return False
                
            print(f"成功加载 '{chat_name}' 的 {len(messages)} 条历史消息")
            
            # 记录历史消息到文件
            self._append_to_file(f"\n--- {chat_name} 的历史消息 ---\n")
            
            # 处理历史消息
            for msg in messages:
                # 根据消息类型格式化
                if msg.type == 'time':
                    # 时间类型消息
                    self._add_message('Time', '', msg.time)
                    
                elif msg.type == 'sys':
                    # 系统消息
                    self._add_message('SYS', '', msg.content)
                    
                elif msg.type == 'friend':
                    # 朋友发送的消息
                    self._add_message(chat_name, chat_name, msg.content)
                    
                elif msg.type == 'self':
                    # 自己发送的消息
                    self._add_message('Self', '自己', msg.content)
            
            return True
            
        except Exception as e:
            error_msg = f"加载 '{chat_name}' 历史消息时出错: {str(e)}"
            print(error_msg)
            self._append_to_file(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [系统] 错误: {error_msg}")
            return False
    
    def add_listen_chat(self, who):
        """添加监听的聊天对象
        
        Args:
            who: 好友或群聊的昵称
        """
        try:
            # 先检查会话是否存在
            sessions = self.wx.GetSessionList()
            if not sessions or who not in sessions:
                print(f"警告: 未找到聊天对象 '{who}'，尝试在微信中搜索...")
                # 尝试搜索并打开聊天
                self.wx.Search(who)
                time.sleep(1)
                # 再次检查
                sessions = self.wx.GetSessionList()
                if not sessions or who not in sessions:
                    print(f"无法找到聊天对象 '{who}'，跳过添加")
                    self._append_to_file(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [系统] 警告: 未能添加聊天对象 '{who}'")
                    return False
            
            # 先加载历史消息
            self._load_history_messages(who)
            
            # 添加聊天监听
            chat = self.wx.AddListenChat(who=who)
            self.listen_list.append(who)
            # 设置当前聊天对象，确保后续可以使用
            if self.current_chat is None:
                self.current_chat = chat
            print(f"已添加聊天监听: {who}")
            return True
        except Exception as e:
            print(f"添加聊天监听 '{who}' 时出错: {str(e)}")
            self._append_to_file(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [系统] 错误: 添加聊天对象 '{who}' 失败: {str(e)}")
            return False
    
    def _get_last_message_time(self):
        """从日志文件中获取最后一条消息的时间戳
        
        Returns:
            datetime: 最后一条消息的时间戳，如果没有找到则返回None
        """
        if not os.path.exists(self.log_file):
            return None
            
        try:
            # 读取文件最后几行来查找最后一条消息
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 从后往前遍历，查找包含时间戳的行
            for line in reversed(lines):
                # 使用正则表达式匹配时间戳 [YYYY-MM-DD HH:MM:SS]
                match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
                if match:
                    time_str = match.group(1)
                    return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            
            return None
        except Exception as e:
            print(f"获取最后消息时间时出错: {str(e)}")
            return None
    
    def _check_time_gap(self, chat=None):
        """检查最后一条消息与当前时间的差距，如果超过1分钟则提示
        
        Args:
            chat: 当前聊天对象，用于发送消息
            
        Returns:
            bool: 如果超过1分钟返回True，否则返回False
        """
        current_time = datetime.now()
        last_time = self._get_last_message_time() or self.last_message_time
        
        # 如果没有提供chat参数，使用保存的最后一个活跃聊天对象
        if chat is None:
            chat = self.current_chat
            
        # 如果没有可用的聊天对象，则不执行后续操作
        if chat is None:
            print("无法调用AI: 没有可用的聊天对象")
            return False
        
        if last_time:
            time_diff = current_time - last_time
            # 如果时间差超过1分钟（60秒）
            if time_diff.total_seconds() > 10:
                print(f"需要调用AI！最后消息时间: {last_time.strftime('%Y-%m-%d %H:%M:%S')}, 已过去: {int(time_diff.total_seconds())}秒")
                
                try:
                    # 调用AI生成回复
                    from AI import ChatAI
                    chat_ai = ChatAI()
                    ai_response = chat_ai.run()
                    
                    # 使用传入的聊天对象发送消息
                    if ai_response and not ai_response.startswith("错误:"):
                        
                        print(f"正在发送AI回复: {ai_response[:50]}...")
                        ai_response = ai_response.replace("A: ", "")
                        chat.SendMsg(ai_response)
                        self._add_message('SYS', '', f"已自动发送AI回复: {ai_response}")
                    else:
                        print(f"AI回复生成失败，不发送消息: {ai_response}")
                        self._add_message('SYS', '', f"AI回复生成失败: {ai_response}")
                        
                except Exception as e:
                    error_msg = f"调用AI或发送消息时出错: {str(e)}"
                    print(error_msg)
                    self._add_message('SYS', '', error_msg)
                    
                return True
        
        return False
    
    def start_logging(self, interval=1):
        """开始记录聊天消息
        
        Args:
            interval: 检查新消息的时间间隔(秒)
        """
        # 检查是否有成功添加的聊天
        if not self.listen_list:
            print("错误: 没有添加任何聊天监听，无法开始记录")
            return
            
        print(f"开始记录聊天消息，检查间隔: {interval}秒")
        print(f"正在监听以下聊天: {', '.join(self.listen_list)}")
        self._append_to_file(f"开始记录 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._append_to_file(f"监听的聊天: {', '.join(self.listen_list)}\n")
        
        check_counter = 0  # 计数器，用于控制时间差检查频率
        
        try:
            while True:
                try:
                    msgs = self.wx.GetListenMessage()
                    has_new_message = False
                    current_active_chat = None  # 记录当前循环中的活跃聊天
                    
                    if msgs:
                        for chat in msgs:
                            one_msgs = msgs.get(chat)   # 获取消息内容
                            if not one_msgs:
                                continue
                                
                            chat_name = getattr(chat, 'who', '未知聊天')
                            current_active_chat = chat  # 保存当前活跃的聊天对象
                            
                            for msg in one_msgs:
                                has_new_message = True
                                # 只记录'friend'和'self'类型的消息
                                if msg.type == 'friend':
                                    # 朋友发送的消息
                                    self._add_message(chat_name, chat_name, msg.content)
                                    self.last_message_time = datetime.now()
                                    
                                elif msg.type == 'self':
                                    # 自己发送的消息
                                    self._add_message('Self', '自己', msg.content)
                                    self.last_message_time = datetime.now()
                                
                                elif msg.type == 'time':
                                    # 时间消息
                                    self._add_message('Time', '', msg.time)
                                    
                                elif msg.type == 'sys':
                                    # 系统消息
                                    self._add_message('SYS', '', msg.content)
                    
                    # 更新当前聊天对象（如果有新消息）
                    if current_active_chat:
                        self.current_chat = current_active_chat
                    
                    # 如果没有新消息，每10次循环检查一次时间差
                    if not has_new_message:
                        check_counter += 1
                        if check_counter >= 10:
                            # 使用保存的聊天对象调用检查方法
                            self._check_time_gap()
                            check_counter = 0
                    else:
                        check_counter = 0
                                
                except Exception as e:
                    error_msg = f"获取消息时出错: {str(e)}"
                    print(error_msg)
                    self._append_to_file(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [系统] 错误: {error_msg}")
                    self._add_message('SYS', '', f"错误: {error_msg}")
                    time.sleep(5)  # 发生错误时增加等待时间
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            end_msg = f"结束记录 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            self._append_to_file(f"\n{end_msg}")
            self._add_message('SYS', '', end_msg)
            print(f"聊天记录已保存到: {self.log_file}")
            print(f"格式化消息已保存到: {self.format_file}")
        except Exception as e:
            error_msg = f"处理会话时出错: {str(e)}"
            print(error_msg)
            self._append_to_file(f"\n{error_msg}")
            self._add_message('SYS', '', error_msg)


if __name__ == "__main__":
    # 使用示例
    logger = ChatLogger()
    
    # 添加要监听的聊天
    listen_targets = [
        '关键词',  # 将此替换为您实际想监听的聊天名称
        # 添加更多聊天对象...
    ]
    
    # 记录成功添加的聊天数量
    success_count = 0
    for target in listen_targets:
        if logger.add_listen_chat(target):
            success_count += 1
    
    # 如果成功添加了至少一个聊天，开始记录
    if success_count > 0:
        print(f"成功添加 {success_count} 个聊天监听")
        # 开始记录，每1秒检查一次新消息
        logger.start_logging(interval=1)
    else:
        print("未能添加任何聊天监听，程序退出")