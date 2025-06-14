from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.checkpoint.memory import MemorySaver
import os

# 清除代理（可选）
for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(key, None)

# 初始化 LLM
llm = ChatOpenAI(
    model_name="deepseek-chat",
    base_url="https://api.deepseek.com/v1",
    api_key="sk-f0904a96b7654c8d811ec4ffefc88bd1",  # 替换为你自己的 key
)

# 定义工具
search = DuckDuckGoSearchRun()
tools = [search]

# 工具节点
tool_node = ToolNode(tools=tools)

# 定义状态类型
class State(TypedDict):
    messages: Annotated[list, lambda old, new: old + new]

# Chatbot 节点：LLM 响应（不绑定工具）
def chatbot(state: State):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

# 构建图
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", tool_node)

# 路由逻辑：LLM 判断是否调用工具
graph_builder.set_entry_point("chatbot")
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge("chatbot", END)

memory = MemorySaver()
# 编译
graph = graph_builder.compile(checkpointer=memory)

# 执行对话
config = {"configurable": {"thread_id": "1"}}
def stream_graph_updates(user_input: str):
    events = graph.stream(
        {"messages": [{"role": "user", "content": user_input}]},
        config,
        #stream_mode="values",
    )
    for event in events:
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)

# 运行主循环
while True:
    try:
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit", "q"]:
            print("Goodbye!")
            break
        stream_graph_updates(user_input)
    except Exception as e:
        print(f"错误：{e}")
        break
