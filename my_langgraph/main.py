import os
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI  # 假设 deepseek-chat 有类似的接口
from langchain_core.messages import AnyMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt.chat_agent_executor import AgentState
# 如果 deepseek-chat 有 OpenAI 兼容的 API
# 你需要替换 base_url 和 api_key 为 deepseek-chat 的实际值
for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy","ALL_PROXY", "all_proxy"]:
    os.environ.pop(key, None)
llm = ChatOpenAI(
    model_name="deepseek-chat",
    base_url="https://api.deepseek.com/v1",  # 假设的 API 地址
    api_key="sk-xxxxx",
)

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_react_agent(
    model=llm,  # 直接传入 LLM 实例
    tools=[get_weather],
    prompt="You are a helpful assistant"
)

def prompt(state: AgentState, config: RunnableConfig) -> list[AnyMessage]:  
    user_name = config["configurable"].get("user_name")
    system_msg = f"You are a helpful assistant. Address the user as {user_name}."
    return [{"role": "system", "content": system_msg}] + state["messages"]

# Run the agent
response = agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather in sf"}]},
    config={"configurable": {"user_name": "John Smith"}}
)
for message in response['messages']:
    print(message.content)
