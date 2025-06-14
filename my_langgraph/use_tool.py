from langchain_community.tools import DuckDuckGoSearchRun

search = DuckDuckGoSearchRun()

print(search.invoke("比特币今日新闻"))
