import openai

openai.api_key = "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"

models = openai.models.list()
print([m.id for m in models.data])