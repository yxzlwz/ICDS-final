from openai import OpenAI

# client = OpenAI(api_key='sk-a3159d7e810d43ec91794b2c155840ec', base_url='https://api.deepseek.com')
client = OpenAI(
    api_key='652752df-dd85-496c-82b2-53b9e588cf06', base_url='https://ark.cn-beijing.volces.com/api/v3'
)


def get_response(messages):
    response = client.chat.completions.create(
        model='doubao-seed-1-6-251015', messages=messages, temperature=0.8, max_tokens=512, stream=False
    )
    return response.choices[0].message.content


if __name__ == '__main__':
    print(
        get_response(
            [
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': 'Hello, how are you?'},
            ]
        )
    )
