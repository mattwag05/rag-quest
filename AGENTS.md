# AGENTS.md — LLM Provider Guide for RAG-Quest v0.6.0

> **v0.6 note:** The AI Notetaker (`engine/notetaker.py`) reuses the same LLM provider via
> a dedicated `NOTETAKER_SYSTEM` prompt and calls `complete()` with the same message
> format. Auto-summary runs on every save event; set `notetaker.auto_summary=false` in
> config to disable it for paid providers.

---

# AGENTS.md — original content

This document describes RAG-Quest's LLM provider architecture, how each provider works, and how to add new providers.

## Architecture Overview

All LLM providers inherit from **BaseLLMProvider** and implement a synchronous `complete()` method:

```python
class BaseLLMProvider(ABC):
    def complete(self,
                messages: list[dict],
                temperature: float = None,
                max_tokens: int = None,
                **kwargs) -> str:
        """Call LLM synchronously and return response text."""
```

**Key Design Decision**: All providers are **synchronous** (not async), even though they make HTTP calls. This is intentional for a turn-based game—no async complexity needed.

**Lightweight Narrator**: The game is designed so the LLM can be small (Gemma 4 E2B/E4B, 2-4B parameters). LightRAG provides the knowledge; the LLM provides the narration.

## Recommended Setup

**For Consumer Hardware** (laptops, desktops):
- **Provider**: Ollama (local, private, free)
- **Model**: Gemma 4 E4B (4B parameters, GPU-friendly)
- **RAG Profile**: balanced
- **Expected latency**: 2-10 seconds per response

**For CPU-Only Systems**:
- **Model**: Gemma 4 E2B (2B parameters, CPU-friendly)
- **RAG Profile**: fast
- **Expected latency**: 10-60 seconds per response

**For Quality** (if you have GPU or want cloud):
- **Provider**: OpenAI (GPT-4 or GPT-3.5-turbo)
- **RAG Profile**: deep
- **Expected latency**: 1-3 seconds per response (faster API)

**For Flexibility** (100+ models):
- **Provider**: OpenRouter (pay-per-use cloud)
- **Any model**: Your choice from 100+ models

## Provider Implementations

### 1. Ollama (Recommended for Local Play)

**File**: `rag_quest/llm/ollama_provider.py`

**What it does**: Calls a local Ollama instance running on your computer.

**Setup**:
```bash
# Download and install Ollama
brew install ollama  # or download from https://ollama.ai

# Pull the model
ollama pull gemma4:e4b

# Start Ollama (runs in background)
ollama serve
```

**Configuration**:
```python
from rag_quest.llm.ollama_provider import OllamaProvider

provider = OllamaProvider({
    "model": "gemma4:e4b",
    "base_url": "http://localhost:11434",
})

response = provider.complete(messages=[
    {"role": "system", "content": "You are a dungeon master..."},
    {"role": "user", "content": "I attack the goblin."},
])
```

**Environment Variables**:
```bash
export OLLAMA_MODEL=gemma4:e4b
export OLLAMA_BASE_URL=http://localhost:11434
```

**Advantages**:
- Completely local and private
- Free
- No internet required for gameplay
- Works offline
- Fast on GPU (2-10 sec with M1/M2 Mac)

**Disadvantages**:
- Requires download (~6 GB for Gemma 4)
- Slower on CPU-only systems (10-60 sec)
- Limited model selection (Ollama's library)

**Supported Models**:
- Gemma 4 (E2B, E4B) — Recommended
- Mistral 7B
- Llama 2
- Any model available via `ollama pull`

**API Integration**:
- Endpoint: `POST {base_url}/api/generate`
- Request format: `{"model": "...", "prompt": "...", "temperature": ..., "num_predict": ...}`
- Response: Streaming JSON with `response` field containing generated text

**Known Issues**: None currently.

### 2. OpenAI (Highest Quality)

**File**: `rag_quest/llm/openai_provider.py`

**What it does**: Calls OpenAI's API (GPT-4, GPT-3.5-turbo).

**Setup**:
```bash
# Get API key from https://platform.openai.com/api-keys
export OPENAI_API_KEY=sk-...
```

**Configuration**:
```python
from rag_quest.llm.openai_provider import OpenAIProvider

provider = OpenAIProvider({
    "api_key": "sk-...",
    "model": "gpt-3.5-turbo",  # or gpt-4 for higher quality
})

response = provider.complete(messages=[...])
```

**Environment Variables**:
```bash
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-3.5-turbo  # or gpt-4
```

**Available Models**:
- `gpt-4` — Most capable, most expensive
- `gpt-3.5-turbo` — Good balance of quality and cost

**Advantages**:
- Highest narrative quality
- Fastest responses (1-3 sec)
- No local setup needed
- Works from anywhere

**Disadvantages**:
- Requires paid API key (pay-per-use)
- Internet required
- Response quality varies by model cost
- Privacy: prompts sent to OpenAI

**API Integration**:
- Endpoint: `https://api.openai.com/v1/chat/completions`
- Uses standard OpenAI chat format
- Streaming support available

**Cost**: Roughly $0.01-$0.20 per response depending on model and response length.

### 3. OpenRouter (Maximum Flexibility)

**File**: `rag_quest/llm/openrouter_provider.py`

**What it does**: Calls OpenRouter.ai, which provides access to 100+ models.

**Setup**:
```bash
# Get API key from https://openrouter.ai
export OPENROUTER_API_KEY=sk-or-...
```

**Configuration**:
```python
from rag_quest.llm.openrouter_provider import OpenRouterProvider

provider = OpenRouterProvider({
    "api_key": "sk-or-...",
    "model": "mistralai/mistral-7b-instruct",  # or any OpenRouter model
})

response = provider.complete(messages=[...])
```

**Available Models** (partial list):
- `gpt-4-turbo-preview` — OpenAI
- `claude-3-opus` — Anthropic
- `mistralai/mistral-7b-instruct` — Mistral
- `meta-llama/llama-2-70b-chat` — Meta
- `nousresearch/nous-hermes-2-mixtral-8x7b` — Nous Research
- And 90+ more...

**Advantages**:
- 100+ model choices
- Compare models with single API key
- No vendor lock-in
- Pay-per-use (cheap for testing)
- Good for research/experimentation

**Disadvantages**:
- Requires API key (and payment)
- Internet required
- Slightly slower than direct provider APIs
- Response quality varies by model

**API Integration**:
- Endpoint: `https://openrouter.ai/api/v1/chat/completions`
- Uses OpenAI-compatible format (easy switching)

**Cost**: Varies by model, roughly $0.01-$0.50 per response.

## How Providers Are Used in the Game

The narrator calls the provider's `complete()` method during gameplay:

```python
# In narrator.py
def process_action(self, action: str, game_state: GameState) -> str:
    # 1. Query RAG for world context
    world_context = self.world_rag.query_world(action)
    
    # 2. Build messages
    messages = [
        {
            "role": "system",
            "content": NARRATOR_SYSTEM + world_context,
        },
        {
            "role": "user",
            "content": action,
        },
    ]
    
    # 3. Call LLM provider (synchronous)
    response = self.llm_provider.complete(messages)
    
    # 4. Record event to RAG
    self.world_rag.record_event(response)
    
    return response
```

**Key Point**: The LLM is called with **game state + RAG context + player action**. The RAG knowledge graph ensures consistency, so even a small model produces coherent narratives.

## Adding a New Provider

To add a new LLM provider (e.g., Anthropic Claude, Cohere, etc.):

### 1. Create the Provider Class

```python
# rag_quest/llm/my_provider.py

from .base import BaseLLMProvider

class MyProvider(BaseLLMProvider):
    def __init__(self, config: dict):
        self.api_key = config.get("api_key")
        self.model = config.get("model", "default-model")
        self.base_url = config.get("base_url", "https://api.my-provider.com")
    
    def complete(self,
                messages: list[dict],
                temperature: float = None,
                max_tokens: int = None,
                **kwargs) -> str:
        """Call MyProvider API synchronously."""
        import httpx
        
        client = httpx.Client()
        response = client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature or 0.7,
                "max_tokens": max_tokens or 500,
            },
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"API error: {response.text}")
        
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    def lightrag_complete_func(self):
        """Return async function for LightRAG compatibility."""
        # LightRAG expects an async function
        async def async_complete(prompt: str, **kwargs) -> str:
            return self.complete([{"role": "user", "content": prompt}], **kwargs)
        return async_complete
```

### 2. Register in config.py

```python
# In setup_first_run() or get_config_section():
providers = {
    "ollama": ("rag_quest.llm.ollama_provider", "OllamaProvider"),
    "openai": ("rag_quest.llm.openai_provider", "OpenAIProvider"),
    "openrouter": ("rag_quest.llm.openrouter_provider", "OpenRouterProvider"),
    "my_provider": ("rag_quest.llm.my_provider", "MyProvider"),  # Add here
}
```

### 3. Update Setup Wizard (optional)

```python
# In config.py, add to provider descriptions:
provider_info = {
    "ollama": "Free, local, no API key needed",
    "openai": "Highest quality (paid API)",
    "openrouter": "100+ models (paid API)",
    "my_provider": "My custom provider",  # Add description
}
```

### 4. Document in AGENTS.md

Add section for your new provider with:
- File location
- Setup instructions
- Available models
- Advantages/disadvantages
- Cost (if paid)

## Provider Comparison

| Provider | Quality | Cost | Setup | Speed | Privacy |
|----------|---------|------|-------|-------|---------|
| Ollama Gemma 4 | Good | Free | Moderate | Medium | Excellent |
| Ollama Mistral | Good | Free | Moderate | Medium | Excellent |
| OpenAI GPT-4 | Excellent | Paid | Easy | Fast | Poor |
| OpenAI GPT-3.5 | Good | Paid | Easy | Fast | Poor |
| OpenRouter | Variable | Paid | Easy | Medium | Poor |

## Debugging Provider Issues

### "Connection refused"

**Ollama not running**:
```bash
# Start Ollama
ollama serve
# or on Mac: open -a Ollama
```

**OpenAI/OpenRouter API unreachable**:
```bash
# Check internet connection
curl https://api.openai.com
```

### "Model not found"

**Ollama**:
```bash
# Pull the model
ollama pull gemma4:e4b

# List available
ollama list
```

**OpenAI**:
- Check API key at https://platform.openai.com/api-keys
- Verify model name (e.g., `gpt-3.5-turbo`)

**OpenRouter**:
- Check model slug at https://openrouter.ai/models
- Common mistake: model name vs model slug (e.g., `mistralai/mistral-7b-instruct`)

### "API key invalid"

- Copy/paste key exactly (no spaces)
- Verify via `/config` or environment variable
- Check key has required permissions (API access, not just dashboard)

### "Rate limited"

- OpenAI: Wait a few seconds, check billing
- OpenRouter: Check rate limits at https://openrouter.ai/keys
- Ollama: No rate limits (local)

### "Slow responses"

- **Ollama on CPU**: Expected to be slow (10-60 sec). Switch to GPU or use E2B model.
- **OpenAI**: Unusual, check network. Expected <3 sec.
- **OpenRouter**: Check model (some models are slow). Try a different model.

## Provider Best Practices

1. **Always use try/except** for HTTP calls—APIs fail
2. **Default temperature to 0.7** for good balance of creativity and consistency
3. **Limit max_tokens** to prevent runaway responses
4. **Validate config** in `__init__()` (raise if missing required keys)
5. **Accept **kwargs** from LightRAG without error
6. **Document** your provider's models and costs

## Performance Tuning

### Temperature & max_tokens

```python
# More creative/varied responses
response = provider.complete(messages, temperature=1.0, max_tokens=500)

# More consistent/focused
response = provider.complete(messages, temperature=0.3, max_tokens=300)
```

### For Faster Responses

1. Use OpenAI (cloud) instead of local Ollama
2. Use smaller model (E2B instead of E4B)
3. Use "fast" RAG profile (less context injected)
4. Increase temperature (fewer recomputes)

### For Better Responses

1. Use GPT-4 instead of GPT-3.5
2. Use "deep" RAG profile (more context)
3. Use lower temperature (more consistency)
4. Increase max_tokens (more space to think)

## Resources

- **Ollama Models**: https://ollama.ai/library
- **OpenAI Models**: https://platform.openai.com/docs/models
- **OpenRouter Models**: https://openrouter.ai/models
- **Gemma**: https://blog.google/technology/developers/gemma-open-models/

---

**Last Updated**: April 2026  
**For**: Developers adding providers or configuring RAG-Quest
