# AI-Powered Self-Marketing
import openai

def generate_marketing_content(product_name):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": f"Generate a promotional tweet for {product_name}."}]
    )
    return response["choices"][0]["message"]["content"]
