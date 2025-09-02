from transformers import AutoModelForCausalLM, AutoTokenizer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

model_name = "swiss-ai/Apertus-8B-Instruct-2509"
#model_name = "swiss-ai/Apertus-8B-2509"
device = "cuda"  # for GPU usage or "cpu" for CPU usage

# load the tokenizer and the model
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
).to(device)

# prepare the model input
prompt = """
Give a simple explanation of what gravity is for a high school 
level physics course with a few typical formulas.
Use lots of emojis and do it in French, Swiss German, Italian and Romansh.
"""

messages_think = [
    {"role": "user", "content": prompt}
]

text = tokenizer.apply_chat_template(
    messages_think,
    tokenize=False,
    add_generation_prompt=True,
)
model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

# Generate the output
generated_ids = model.generate(**model_inputs, max_new_tokens=32768)

# Get and decode the output
output_ids = generated_ids[0][len(model_inputs.input_ids[0]) :]

console = Console()
console.print(Panel(prompt, title="Prompt"))
console.print(Panel(Markdown(tokenizer.decode(output_ids, skip_special_tokens=True)), title="Response"))