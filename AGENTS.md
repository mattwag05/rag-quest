# AGENTS.md - LLM Provider Integration Guide

This document describes how RAG-Quest integrates different LLM providers and how the AI narrator agent works within the game engine.

## Overview

RAG-Quest uses a **provider-agnostic** architecture that treats OpenAI, OpenRouter, and Ollama as first-class citizens. The system abstracts provider-specific APIs behind a common interface, allowing seamless switching between models and providers.

**The Architectural Philosophy**: The LLM is not expected to be a large or sophisticated model. LightRAG's knowledge graph retrieval injects all necessary context per query. A ~3B parameter model (Ollama neural-chat, Mistral, or even smaller) paired with strong RAG context performs as well as much larger models running blind. This enables consumer-hardware deployment and dramatically reduces costs.

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
    #     'max_tokens': 1024    # Lightweight context assumption
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
- **Note**: Even GPT-3.5 works well with good RAG context

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
    #     'max_tokens': 1024
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
- `mistralai/mistral-7b` - Fast, lighter, excellent with RAG

**Cost**: Varies; Claude ~$0.15 per turn, Llama ~$0.01 per turn, Mistral ~$0.005 per turn

**Latency**: 1-15 seconds depending on provider load

**Tips**:
- Different models have different personalities
- Sonnet is best for consistent narration
- Llama and Mistral are fast and cheap—excellent for testing
- Check OpenRouter.ai/status for provider uptime
- **Key insight**: Llama-7B with RAG often rivals Claude quality

#### 3. Ollama Provider

**File**: `llm/ollama_provider.py`

```python
class OllamaProvider(BaseLLMProvider):
    """Local Ollama inference engine."""
    
    # Expected config:
    # {
    #     'model': 'neural-chat' | 'mistral' | 'llama2' | 'orca' | 'zephyr',
    #     'base_url': 'http://localhost:11434',
    #     'temperature': 0.85,
    #     'max_tokens': 1024
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
- **Perfect for consumer hardware when paired with RAG**

**Recommended Models**:
- `neural-chat` - Best narrative for game dialogue
- `mistral` - Fast and capable, good balance
- `orca-mini` - Fast, good for testing
- `llama2` - Good general purpose
- `zephyr` - Newer, good reasoning

**Setup**:
```bash
# Install Ollama from ollama.ai
# Start the server
ollama serve

# In another terminal, pull a model
ollama pull neural-chat
ollama pull mistral
```

**Performance**:
- GPU: 2-10 seconds per response
- CPU: 10-60 seconds per response
- Depends heavily on model size and hardware

**Tips**:
- Use smaller models (7B is often sufficient with RAG)
- GPU recommended for playable experience
- Cold start is slower (~30s); subsequent queries faster
- Great for development/testing without API costs
- **Philosophy**: A 7B local model with RAG beats a 70B model without RAG

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

**Design Philosophy**: The Narrator is intentionally simple. LightRAG does the complexity work (knowledge graph retrieval, entity matching, context relevance). The Narrator just orchestrates: query RAG, build messages, call LLM, parse response.

### Narrator Flow

The narrator implements a sophisticated pipeline for generating contextual, consistent responses:

```
┌─────────────────────────────────────────────────────┐
│  Player Action: "I search the desk for clues"       │
└────────────────┬────────────────────────────────────┘
                 │
        ┌────────▼─────────┐
        │  RAG Query        │
        │ (knowledge graph) │ ← This does the heavy lifting
        └────────┬──────────┘
                 │
   ┌─────────────────────────────────────┐
   │ "I found these relevant facts:       │
   │  - Desk in study contains books      │
   │  - Secret compartments common here"  │
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
        │  (call provider)  │ ← Small model is fine here
        └────────┬──────────┘
                 │
   ┌─────────────────────────────────┐
   │ Generated Response:               │
   │ "You find old journals and       │
   │  a small jewelry box..."         │
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
    
    # 3. Call LLM (can be lightweight model)
    response = await self.llm_provider.complete(
        messages,
        temperature=0.85,
        max_tokens=1024
    )
    
    # 4. Parse state changes
    self._parse_and_apply_changes(response)
    
    # 5. Record to RAG
    await self.world_rag.record_event(f"{self.game_state.character.name} {action}")
    
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

| Provider | Model | Params | Temp | Use Case | Cost | Speed |
|----------|-------|--------|------|----------|------|-------|
| Ollama | neural-chat | 7B | 0.85 | Excellent local | Free | 5-15s |
| OpenRouter | Llama-2 | 70B | 0.85 | Great + cheap | $0.01 | Fast |
| OpenRouter | Mistral | 7B | 0.85 | Great + very cheap | $0.005 | Fast |
| OpenRouter | Claude-Sonnet-4 | N/A | 0.85 | Excellent | $0.15 | Med |
| OpenAI | GPT-3.5 | N/A | 0.85 | Good balance | $0.05 | Fast |
| OpenAI | GPT-4 | N/A | 0.85 | Best quality | $0.30 | Slow |

**Temperature Notes**:
- 0.85 is ideal for balancing creativity and consistency
- Lower (0.5-0.7) = more predictable, less creative
- Higher (0.9-1.0) = more creative, less consistent

**Key Insight**: With RAG context, a 7B model often rivals a 70B model. A 3-7B local model with good RAG frequently outperforms a 100B model without RAG.

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
- For Ollama: Use smaller model (7B) or GPU
- For OpenAI: Use GPT-3.5 instead of GPT-4
- For OpenRouter: Try Llama 7B instead of 70B
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
- **Model**: Llama-2-7B or Mistral-7B or neural-chat
- **Cost**: Free (Ollama) or $0.005-0.01 per turn
- **Speed**: Fast
- **Quality**: Excellent (with RAG)

### Testing (Balanced)
- **Provider**: OpenRouter
- **Model**: Claude-Sonnet-4 or Llama-70b
- **Cost**: $0.15 or $0.01 per turn
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
- **Model**: neural-chat, mistral, or zephyr
- **Cost**: Free
- **Speed**: 5-30 seconds (depends on hardware)
- **Quality**: Excellent (with RAG)

## Provider Comparison Matrix

| Aspect | OpenAI | OpenRouter | Ollama |
|--------|--------|-----------|--------|
| Setup Complexity | Easy | Easy | Medium |
| Models Available | 5 | 100+ | 30+ |
| Cost | Higher | Varies | Free |
| Speed | 1-10s | 1-15s | 5-60s |
| Quality | Excellent | Excellent | Good-Excellent |
| Offline Support | No | No | Yes |
| API Key Req'd | Yes | Yes | No |
| Rate Limits | Yes | Generous | No |
| Streaming | Yes | Yes | Yes |
| **RAG Friendly** | Yes | Yes | **Ideal** |

---

**Last Updated**: April 2026

**Core Philosophy**: LightRAG does the knowledge work. The LLM is just the narrator. Keep it lightweight.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
