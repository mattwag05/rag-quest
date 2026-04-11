# AGENTS.md - LLM Provider Integration Guide

This document describes how RAG-Quest integrates different LLM providers and how the AI narrator agent works within the game engine.

## Overview

RAG-Quest uses a **provider-agnostic** architecture that treats OpenAI, OpenRouter, and Ollama as first-class citizens. The system abstracts provider-specific APIs behind a common interface, allowing seamless switching between models and providers.

## LLM Provider Architecture

### Provider Abstraction Layer

All providers implement `BaseLLMProvider` (llm/base.py):

```python
class BaseLLMProvider(ABC):
    """Base class for all LLM providers."""
    
    def __init__(self, config: dict):
        """Initialize with config dict containing:
        - model: model name/ID
        - api_key: API key or None
        - base_url: custom endpoint (optional)
        - temperature: default temperature
        - max_tokens: default max tokens
        """
        self.config = config
    
    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        temperature: float = None,
        max_tokens: int = None,
    ) -> str:
        """Generate a completion.
        
        Args:
            messages: List of {'role': 'system'|'user'|'assistant', 'content': str}
            temperature: Override default temperature (0-2 range)
            max_tokens: Override default max tokens
        
        Returns:
            Generated text response
        
        Raises:
            ValueError: Invalid API key or model
            ConnectionError: API unreachable
            RuntimeError: Other API errors
        """
        pass
    
    def lightrag_complete_func(self) -> callable:
        """Return a callable that LightRAG can use.
        
        LightRAG expects: fn(prompt, **kwargs) -> str
        This method adapts our async interface to that expectation.
        
        Returns:
            Callable: (prompt: str) -> str
        """
        pass
```

### Provider Implementations

#### 1. OpenAI Provider

**File**: `llm/openai_provider.py`

```python
class OpenAIProvider(BaseLLMProvider):
    """Direct OpenAI API integration."""
    
    # Expected config:
    # {
    #     'model': 'gpt-4-turbo' or 'gpt-3.5-turbo',
    #     'api_key': 'sk-...',
    #     'temperature': 0.85,  # Narrative tone
    #     'max_tokens': 2048
    # }
    
    async def complete(self, messages, temperature=None, max_tokens=None):
        # 1. Build JSON payload
        # 2. POST to https://api.openai.com/v1/chat/completions
        # 3. Parse response
        # 4. Return content of first choice
        pass
```

**Features**:
- Latest models: GPT-4 Turbo, GPT-4, GPT-3.5-turbo
- Token streaming not yet implemented
- Supports system prompts, function calling (not used)
- Requires valid OpenAI API key

**Cost**: ~$0.05-0.30 per complex game turn (depending on model)

**Latency**: 1-10 seconds per request

**Tips**:
- GPT-4 is most consistent for narrative (higher cost)
- GPT-3.5-turbo is cheaper but less coherent
- Set temperature 0.8-0.9 for creative narration

#### 2. OpenRouter Provider

**File**: `llm/openrouter_provider.py`

```python
class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter.ai multi-model integration."""
    
    # Expected config:
    # {
    #     'model': 'anthropic/claude-sonnet-4' | 'openai/gpt-4' | 'meta-llama/llama-2-70b',
    #     'api_key': 'sk-or-...',
    #     'temperature': 0.85,
    #     'max_tokens': 2048
    # }
    
    async def complete(self, messages, temperature=None, max_tokens=None):
        # 1. Build JSON payload with model parameter
        # 2. POST to https://openrouter.ai/api/v1/chat/completions
        # 3. Handle response (compatible with OpenAI format)
        # 4. Return content
        pass
```

**Features**:
- 100+ models available (Claude, GPT, Llama, Mistral, etc.)
- Single API for multiple providers
- Automatic fallback (optional)
- Pricing varies per model
- Request logging available

**Recommended Models**:
- `anthropic/claude-sonnet-4` - Excellent narrative coherence
- `openai/gpt-4-turbo` - Strong performance
- `meta-llama/llama-2-70b` - Good open-source alternative

**Cost**: Varies; Claude ~$0.15 per turn, Llama ~$0.01 per turn

**Latency**: 1-15 seconds depending on provider load

**Tips**:
- Different models have different personalities
- Sonnet is best for consistent narration
- Llama is fast and cheap for testing
- Check OpenRouter.ai/status for provider uptime

#### 3. Ollama Provider

**File**: `llm/ollama_provider.py`

```python
class OllamaProvider(BaseLLMProvider):
    """Local Ollama inference engine."""
    
    # Expected config:
    # {
    #     'model': 'llama2' | 'neural-chat' | 'orca' | 'mistral',
    #     'base_url': 'http://localhost:11434',
    #     'temperature': 0.85,
    #     'max_tokens': 2048
    # }
    
    async def complete(self, messages, temperature=None, max_tokens=None):
        # 1. Build JSON payload
        # 2. POST to base_url/api/chat
        # 3. Handle streaming response
        # 4. Return accumulated response
        pass
```

**Features**:
- Runs completely locally (no API keys needed)
- Requires Ollama daemon running (`ollama serve`)
- Models: Llama 2, Mistral, Neural Chat, Orca, Zephyr, etc.
- No rate limits, no costs (just CPU/GPU)
- Streaming response support

**Recommended Models**:
- `neural-chat` - Best narrative for game dialogue
- `mistral` - Fast and capable
- `orca-mini` - Fast, good for testing
- `llama2` - Good general purpose

**Setup**:
```bash
# Install Ollama from ollama.ai
# Start the server
ollama serve

# In another terminal, pull a model
ollama pull neural-chat
```

**Performance**:
- GPU: 2-10 seconds per response
- CPU: 10-60 seconds per response
- Depends heavily on model size and hardware

**Tips**:
- Use smaller models (7B) for faster responses
- GPU recommended for playable experience
- Cold start is slower (~30s); subsequent queries faster
- Great for development/testing without API costs

### Adding a New Provider

To add support for a new LLM provider (e.g., Anthropic direct, Hugging Face, etc.):

1. **Create the provider file**:
   ```
   rag_quest/llm/my_provider.py
   ```

2. **Implement BaseLLMProvider**:
   ```python
   from .base import BaseLLMProvider
   
   class MyProvider(BaseLLMProvider):
       async def complete(self, messages, temperature=None, max_tokens=None) -> str:
           # Implementation here
           pass
       
       def lightrag_complete_func(self):
           # Return sync wrapper for LightRAG
           pass
   ```

3. **Add to config setup** in `config.py`:
   ```python
   def setup_first_run():
       # Add to provider selection:
       # "my_provider": "My Provider Name"
   ```

4. **Register in llm/__init__.py**:
   ```python
   from .my_provider import MyProvider
   ```

5. **Document in README.md** and this file

## The Narrator Agent

### Overview

The Narrator is the AI "Dungeon Master" that generates story responses. It's not a separate agent running independently, but rather an orchestrator that uses the LLM provider to generate narrative content based on game context.

**Key Class**: `Narrator` in `engine/narrator.py`

### Narrator Flow

The narrator implements a sophisticated pipeline for generating contextual, consistent responses:

```
┌─────────────────────────────────────────────────────┐
│  Player Action: "I search the desk for clues"       │
└────────────────┬────────────────────────────────────┘
                 │
        ┌────────▼─────────┐
        │  RAG Query        │
        │ (knowledge graph) │
        └────────┬──────────┘
                 │
   ┌─────────────────────────────────────┐
   │ "I found these relevant facts:       │
   │  - Desk contains old books, jewels   │
   │  - Secret compartments in antique    │
   │    desks are common in this region"  │
   └─────────────────────────────────────┘
                 │
        ┌────────▼──────────────┐
        │  Build Message List   │
        │  - System prompt      │
        │  - RAG context        │
        │  - Character status   │
        │  - History (last 3)   │
        │  - Current action     │
        └────────┬──────────────┘
                 │
        ┌────────▼──────────┐
        │  LLM Complete     │
        │  (call provider)  │
        └────────┬──────────┘
                 │
   ┌─────────────────────────────────┐
   │ Generated Response:               │
   │ "You carefully pull open the      │
   │  drawer. Inside, you find old     │
   │  leather journals and a small     │
   │  jewelry box..."                  │
   └─────────────────────────────────┘
                 │
        ┌────────▼────────────────┐
        │  Parse for State Changes│
        │  - Location changes?    │
        │  - New NPCs?            │
        │  - Items gained?        │
        └────────┬────────────────┘
                 │
        ┌────────▼──────────────┐
        │  Record to RAG        │
        │  - New facts          │
        │  - Events             │
        └────────┬──────────────┘
                 │
        ┌────────▼──────────────┐
        │  Update Game State    │
        │  - Add to history     │
        │  - Auto-save          │
        └────────┬──────────────┘
                 │
        ┌────────▼──────────┐
        │  Display Response │
        └───────────────────┘
```

### Key Methods

#### `process_action(action: str) -> tuple[str, GameState]`

Main entry point. Processes player input and returns narrative response.

```python
async def process_action(self, action: str) -> tuple[str, GameState]:
    # 1. Query RAG for context
    context = await self.world_rag.query_world(
        question=action,
        context=self.game_state.world.get_context()
    )
    
    # 2. Build message list
    messages = self._build_messages(action, context)
    
    # 3. Call LLM
    response = await self.llm_provider.complete(
        messages,
        temperature=0.85,
        max_tokens=1024
    )
    
    # 4. Parse state changes
    self._parse_and_apply_changes(response)
    
    # 5. Record to RAG
    await self.world_rag.record_event(f"{self.game_state.character.name} {action}")
    
    # 6. Save history
    self.conversation_history.append({"role": "user", "content": action})
    self.conversation_history.append({"role": "assistant", "content": response})
    
    return response, self.game_state
```

#### `_build_messages(action: str, context: str) -> list[dict]`

Constructs the message list sent to the LLM.

```python
def _build_messages(self, action: str, context: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": templates.NARRATOR_SYSTEM
        },
        {
            "role": "system",
            "content": f"World: {self.game_state.world.name}, "
                      f"Setting: {self.game_state.world.setting}, "
                      f"Tone: {self.game_state.world.tone}"
        },
        {
            "role": "system",
            "content": f"Character: {self.game_state.character.name}, "
                      f"Race: {self.game_state.character.race}, "
                      f"Class: {self.game_state.character.class_}, "
                      f"Location: {self.game_state.character.location}, "
                      f"HP: {self.game_state.character.hp}"
        },
        {
            "role": "system",
            "content": f"Relevant World Knowledge:\n{context}"
        },
        # Add conversation history (last 6 messages)
        *self.conversation_history[-6:],
        {
            "role": "user",
            "content": action
        }
    ]
```

#### `_parse_and_apply_changes(response: str) -> None`

Detects and applies state changes mentioned in the response.

Uses regex patterns to detect:
- **Location changes**: `move to|go to|enter|arrive|travel|journey`
- **NPC meetings**: `meet|encounter|find|see|talk to`
- **Item discovery**: `find|discover|gain|pick up|receive|obtain`

Example:

```python
# If response contains "You enter the tavern"
# - Detect location change
# - Update character.location = "tavern"
# - Add to world.visited_locations

# If response contains "You meet the innkeeper"
# - Detect NPC
# - Add to world.npcs_met
```

### System Prompts

The narrator uses carefully crafted system prompts to shape AI behavior.

**NARRATOR_SYSTEM** (prompts/templates.py):

Key characteristics:
- Emphasizes D&D-style narration
- Requests third-person perspective
- Instructs AI to ground narrative in provided context
- Encourages creative but consistent world-building
- Sets expectations for response length

**Example prompt structure**:
```
You are an experienced Dungeon Master narrating an AI-powered D&D-style adventure...

Instructions:
1. Use third-person perspective
2. Ground the narrative in the provided world knowledge
3. Generate vivid, contextual descriptions
4. Describe the immediate consequences of the player's action
5. Hint at nearby opportunities or challenges
6. Respect established lore and character state
7. Maintain consistent tone and setting
...
```

### Temperature & Model Selection

Different models and temperatures serve different purposes:

| Provider | Model | Temp | Use Case | Cost | Speed |
|----------|-------|------|----------|------|-------|
| OpenAI | GPT-4 | 0.85 | Best consistency | High | Slow |
| OpenAI | GPT-3.5 | 0.85 | Good balance | Low | Fast |
| OpenRouter | Claude-Sonnet-4 | 0.85 | Excellent narrative | Med | Med |
| OpenRouter | Llama-2-70b | 0.85 | Good, fast | Low | Fast |
| Ollama | neural-chat | 0.85 | Free, local | None | Varies |

**Temperature Notes**:
- 0.85 is ideal for balancing creativity and consistency
- Lower (0.5-0.7) = more predictable, less creative
- Higher (0.9-1.0) = more creative, less consistent

### Troubleshooting Narrator Issues

**Problem**: Responses are repetitive or dull

**Solution**:
- Check conversation history isn't too long
- Increase temperature slightly (to 0.9)
- Improve lore ingestion for better RAG context
- Try different model (Claude more creative than GPT-3.5)

**Problem**: Responses contradict previous story

**Solution**:
- Improve lore document clarity
- Check RAG query is specific enough
- Verify system prompt is being used
- Consider updating character/world context

**Problem**: LLM takes too long to respond

**Solution**:
- For Ollama: Use smaller model or GPU
- For OpenAI: Use GPT-3.5 instead of GPT-4
- For OpenRouter: Try Llama instead of Claude
- Reduce max_tokens parameter

**Problem**: Response isn't grounding in RAG context

**Solution**:
- Check RAG query result in debug mode
- Verify context is being included in messages
- Try more specific action description
- Check lore file quality

## Integration with LightRAG

### LightRAG Completion Function

LightRAG needs a callable with signature: `fn(prompt: str, **kwargs) -> str`

RAG-Quest adapts the async provider interface via:

```python
def lightrag_complete_func(self):
    """Create a sync wrapper for LightRAG.
    
    LightRAG expects synchronous function, but our providers
    are async. This wrapper handles the adaptation.
    """
    def sync_complete(prompt: str, **kwargs) -> str:
        # Run async function in event loop
        import asyncio
        response = asyncio.run(
            self.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get('temperature', 0.7),
                max_tokens=kwargs.get('max_tokens', 1024)
            )
        )
        return response
    
    return sync_complete
```

### RAG Query Process

When narrator calls `world_rag.query_world(question, context)`:

1. LightRAG receives the question
2. LightRAG uses provider's `lightrag_complete_func()` for analysis
3. Provider processes the question (via LLM)
4. RAG performs hybrid entity + theme matching
5. Relevant facts returned to narrator
6. Narrator includes facts in system message

## Multi-Provider Recommendations

### Development (Low Cost)
- **Provider**: OpenRouter or Ollama
- **Model**: Llama-2-70b or neural-chat
- **Cost**: Free (Ollama) or $0.01-0.05 per turn
- **Speed**: Fast
- **Quality**: Good

### Testing (Balanced)
- **Provider**: OpenRouter
- **Model**: Claude-Sonnet-4
- **Cost**: $0.15 per turn
- **Speed**: 2-5 seconds
- **Quality**: Excellent

### Production (Best Quality)
- **Provider**: OpenAI
- **Model**: GPT-4-Turbo
- **Cost**: $0.30 per turn
- **Speed**: 3-10 seconds
- **Quality**: Excellent

### Hobby Play (Local)
- **Provider**: Ollama
- **Model**: neural-chat or mistral
- **Cost**: Free
- **Speed**: 5-30 seconds (depends on hardware)
- **Quality**: Good

## Provider Comparison Matrix

| Aspect | OpenAI | OpenRouter | Ollama |
|--------|--------|-----------|--------|
| Setup Complexity | Easy | Easy | Medium |
| Models Available | 5 | 100+ | 30+ |
| Cost | Higher | Varies | Free |
| Speed | 1-10s | 1-15s | 5-60s |
| Quality | Best | Excellent | Good |
| Offline Support | No | No | Yes |
| API Key Req'd | Yes | Yes | No |
| Rate Limits | Yes | Generous | No |
| Streaming | Yes | Yes | Yes |

---

**Last Updated**: April 2026

