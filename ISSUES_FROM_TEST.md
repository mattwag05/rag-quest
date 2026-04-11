# Issues Found During Comprehensive Test (2026-04-11)

## P1 - CRITICAL BLOCKERS

### P1.1: Package Installation Fails - setuptools Error
**Status:** UNRESOLVED  
**Severity:** CRITICAL  
**Component:** Build/Installation  

**Description:**
The project cannot be installed via `pip install -e .` due to setuptools package discovery error.

**Error:**
```
setuptools error: Multiple top-level packages discovered in a flat-layout: 
['lore', 'saves', 'rag_quest']

setuptools will not proceed with this build.
```

**Root Cause:**
The `pyproject.toml` uses automatic package discovery but the `lore/` and `saves/` directories at root level are being incorrectly identified as packages. These are data directories, not Python packages.

**Impact:**
- Cannot install package in development mode
- Blocks all development workflows
- Automated testing cannot run
- CI/CD cannot build the project

**Solution:**
Add explicit package configuration to `pyproject.toml`:
```toml
[tool.setuptools]
packages = ["rag_quest"]

[tool.setuptools.package-data]
rag_quest = ["*.py"]
```

Or use `src/` layout structure.

**Files to Modify:**
- `pyproject.toml` - Add packages configuration
- Optionally: Move `rag_quest/` to `src/rag_quest/`

---

### P1.2: Async/Await Mismatch - LLM Providers Return Coroutines
**Status:** UNRESOLVED  
**Severity:** CRITICAL  
**Component:** LLM Integration  

**Description:**
All LLM provider methods are defined as `async` but are called synchronously throughout the codebase. This causes coroutine objects to be returned instead of actual text.

**Error:**
```
Response: <coroutine object OllamaProvider.complete at 0x10fc04540>
RuntimeWarning: coroutine 'OllamaProvider.complete' was never awaited
```

**Root Cause:**
Methods like `OllamaProvider.complete()` are `async def` but:
1. Narrator calls them without `await`
2. Game loop doesn't use `asyncio.run()`
3. No event loop management

**Impact:**
- **TOTAL FAILURE** of all LLM-based features
- No narration/dialogue generation
- No DM responses
- No game progression
- Game is completely non-functional

**Solution Options:**
1. **Synchronous approach** (simpler for text RPG):
   - Convert all async methods to sync
   - Use `httpx` in sync mode
   - Remove `async`/`await` keywords

2. **Async approach** (more complex):
   - Make game loop async: `async def main()`
   - Use `asyncio.run(main())`
   - Add `await` to all provider calls
   - Wrap stdin with async wrapper

**Recommended:** Option 1 (synchronous) for a turn-based text RPG

**Files to Modify:**
- `rag_quest/llm/ollama_provider.py` - Remove async
- `rag_quest/llm/openai_provider.py` - Remove async
- `rag_quest/llm/openrouter_provider.py` - Remove async
- `rag_quest/engine/narrator.py` - Add await or convert to sync
- `rag_quest/engine/game.py` - Update game loop

---

### P1.3: Interactive Configuration Blocks Non-Interactive Environments
**Status:** UNRESOLVED  
**Severity:** CRITICAL  
**Component:** Configuration  

**Description:**
The `get_config()` function calls `setup_first_run()` which uses Rich's `Prompt.ask()` for interactive setup. This fails when input is not a TTY (automated tests, CI/CD, piped input).

**Error:**
```
EOFError: EOF when reading a line
File "/rag_quest/config.py", line 82, in _setup_llm_provider
    provider = Prompt.ask(
        "Select LLM provider",
        choices=["openai", "openrouter", "ollama"],
        default="openrouter",
    )
```

**Root Cause:**
No check for whether config file already exists or environment variables are set before prompting. `setup_first_run()` is called unconditionally.

**Impact:**
- Cannot run automated tests
- Cannot run in CI/CD environments
- Cannot run headless/no-terminal
- Blocks all testing workflows

**Solution:**
1. Check if config file exists before prompting
2. Check environment variables (LLM_PROVIDER, OLLAMA_MODEL, etc.)
3. Only prompt if neither config file nor env vars exist
4. Add `--non-interactive` flag that skips prompts

**Implementation:**
```python
def get_config():
    # Check config file first
    if CONFIG_FILE.exists():
        return load_config_file(CONFIG_FILE)
    
    # Check environment variables
    if os.getenv('LLM_PROVIDER'):
        return load_config_from_env()
    
    # Only then ask user
    if sys.stdin.isatty():  # Only if interactive
        return setup_first_run()
    else:
        raise ConfigError("Config not found and running non-interactively")
```

**Files to Modify:**
- `rag_quest/config.py` - Add checks before prompting

---

## P2 - MAJOR ISSUES

### P2.1: PDF Ingestion Function Signature Mismatch
**Status:** UNRESOLVED  
**Severity:** MAJOR  
**Component:** Knowledge Ingestion  

**Description:**
The `ingest_file()` function signature doesn't match how it's being called throughout the codebase.

**Error:**
```
TypeError: ingest_file() takes 1 positional argument but 2 were given
```

**Current Code (ingest.py):**
```python
def ingest_file(file_path):  # Takes only path
    # Implementation
```

**Expected Usage (from test):**
```python
ingest_file(rag, file_path)  # Pass RAG instance and path
```

**Root Cause:**
Function signature doesn't accept RAG instance parameter, but the system needs to ingest into a specific RAG instance.

**Impact:**
- Cannot ingest knowledge from PDFs
- RAG system cannot be populated with lore
- Game world has no knowledge base
- Cannot test RAG retrieval features

**Solution:**
Update function signature:
```python
def ingest_file(rag: WorldRAG, file_path: Path) -> None:
    """Ingest a file into the RAG system."""
    # Implementation
```

**Files to Modify:**
- `rag_quest/knowledge/ingest.py` - Fix signature
- Any callers of `ingest_file()` - Ensure they pass RAG instance

---

### P2.2: Narrator Constructor Signature Mismatch
**Status:** UNRESOLVED  
**Severity:** MAJOR  
**Component:** Game Engine  

**Description:**
The `Narrator.__init__()` method doesn't accept expected parameters for game initialization.

**Error:**
```
TypeError: Narrator.__init__() got an unexpected keyword argument 'llm_provider'
```

**Expected Signature:**
```python
narrator = Narrator(character=char, world=world, llm_provider=provider)
```

**Root Cause:**
Constructor signature doesn't match documented/expected API.

**Impact:**
- Cannot instantiate Narrator
- Cannot create game DM narrator
- Game loop cannot initialize
- Cannot test narration features

**Solution:**
Check actual Narrator `__init__()` signature in `narrator.py` and align with:
1. Document actual expected parameters, OR
2. Update constructor to accept expected parameters

**Files to Modify:**
- `rag_quest/engine/narrator.py` - Verify/fix constructor
- `rag_quest/engine/game.py` - Update instantiation calls

---

### P2.3: Missing World.description Attribute
**Status:** UNRESOLVED  
**Severity:** MAJOR  
**Component:** World System  

**Description:**
Code references `world.description` but the World class doesn't define this attribute.

**Error:**
```
AttributeError: 'World' object has no attribute 'description'
```

**Root Cause:**
World class incomplete or attribute naming mismatch.

**Impact:**
- Cannot access world descriptions
- Narrator/DM descriptions incomplete
- Gameplay narration broken

**Solution:**
1. Add `description` attribute to World class, OR
2. Find correct attribute name and update references

**Files to Modify:**
- `rag_quest/engine/world.py` - Add description attribute
- All files that reference `world.description` - Update if needed

---

## P3 - IMPROVEMENTS

### P3.1: No Error Handling in Game Loop
**Severity:** MEDIUM  
**Component:** Game Engine  

**Description:**
Game loop has minimal error handling, causing crashes on unexpected input or state errors.

**Solution:**
Add try/catch blocks around:
- LLM completions with timeout/retry
- User input validation
- State transitions
- Game state checks

---

### P3.2: No Comprehensive Test Suite
**Severity:** MEDIUM  
**Component:** Testing  

**Description:**
Project lacks unit tests, integration tests, and fixtures for testing.

**Solution:**
Create:
- Unit tests for each component
- Integration tests for component interaction
- Fixtures for game state/character/world
- Mock LLM provider for testing

---

### P3.3: API Documentation Outdated
**Severity:** MEDIUM  
**Component:** Documentation  

**Description:**
README and docstrings don't match actual function signatures.

**Solution:**
1. Audit all public APIs
2. Update docstrings to match implementation
3. Update README with correct examples
4. Add parameter descriptions and return types

---

### P3.4: Inconsistent LLM Provider Configuration
**Severity:** MEDIUM  
**Component:** LLM Integration  

**Description:**
Different providers (OpenAI, OpenRouter, Ollama) have inconsistent initialization patterns.

**Solution:**
Create common base class with consistent interface:
- Consistent parameter names
- Consistent error handling
- Consistent async patterns (once P1.2 fixed)

---

## Testing Artifacts

### Generated During Test
- `docs/TEST_REPORT.md` - Comprehensive test report
- `test_playthrough.py` - Full 30+ turn test script (blocked by P1.x)
- `simple_test.py` - Component isolation tests
- `.env` - Configuration file for Ollama

### Test Findings
- Character system: FULLY FUNCTIONAL
- World system: FULLY FUNCTIONAL  
- RAG initialization: FUNCTIONAL
- LLM providers: BROKEN (async/await)
- Configuration: BROKEN (interactive)
- Package installation: BROKEN (setuptools)
- PDF ingestion: BROKEN (API mismatch)
- Game loop: UNTESTABLE (depends on P1.x fixes)

## Summary

### Critical Path to Functionality
1. Fix P1.1 (package installation)
2. Fix P1.2 (async/await mismatch) **[HIGHEST PRIORITY]**
3. Fix P1.3 (interactive config)
4. Fix P2.1 (ingest_file signature)
5. Fix P2.2 (Narrator signature)
6. Fix P2.3 (World.description)

### Estimated Effort
- P1.1: 15 minutes
- P1.2: 1-2 hours (requires careful refactoring)
- P1.3: 30 minutes
- P2.1: 15 minutes
- P2.2: 30 minutes
- P2.3: 15 minutes
- **Total:** ~3-4 hours to restore basic functionality

Once P1 issues are fixed, the project can be tested end-to-end with 30+ turn gameplay.

---

**Generated:** 2026-04-11  
**Test Environment:** macOS, Python 3.14, Ollama (gemma4)
