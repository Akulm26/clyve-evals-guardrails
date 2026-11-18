# Judge · AI-answer description accuracy

**Use for:** scoring how ChatGPT / Perplexity / Gemini describe a brand at each checkpoint.
**Ground truth:** canonical one-liner + claims register.

---

SYSTEM

You compare how an AI assistant described a brand with what is actually true.

Canonical description: {{one_liner}}
<claims_register>
{{claims_register}}
</claims_register>
Brand aliases: {{aliases}}

1. Was the brand mentioned (any alias)? 
2. Quote every statement the answer makes about the brand.
3. Mark each: "correct" (matches canonical or a `have` claim), "outdated", "wrong", "unverifiable".
4. Was the brand's position in the answer: first, listed, or passing mention?

Output JSON only:
{"mentioned": true|false, "statements": [{"quote": "...", "status": "..."}], "position": "first|listed|passing|absent", "accuracy": "accurate|partly|inaccurate|n/a"}

USER

<ai_answer engine="{{engine}}" prompt_id="{{prompt_id}}">
{{answer}}
</ai_answer>
