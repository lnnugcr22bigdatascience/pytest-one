from openai import OpenAI

client = OpenAI(
    base_url="https://token.sensenova.cn/v1",
    api_key="sk-roWCoHc1b4veHWyeC8RLzMnFyOvxqBEj",
)

resp = client.chat.completions.create(
    model="sensenova-6.7-flash-lite",
    messages=[{"role": "user", "content": "Hello!"}],
)

print(resp.choices[0].message.content)
