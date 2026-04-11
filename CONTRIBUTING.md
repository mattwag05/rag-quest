# Contributing to RAG-Quest

We welcome contributions! Whether you're fixing bugs, adding features, or improving documentation, here's how to help.

## Getting Started

1. **Fork or clone the repository**
   ```bash
   git clone https://github.com/yourusername/rag-quest.git
   cd rag-quest
   ```

2. **Install in development mode**
   ```bash
   pip install -e ".[dev]"
   ```

3. **Run tests to verify setup**
   ```bash
   pytest
   ```

## Development Guidelines

### Code Style

- Follow PEP 8
- Use type hints everywhere
- 88-character line limit (black)
- Use meaningful variable names

```bash
# Format code
black rag_quest/

# Sort imports
isort rag_quest/

# Type check
mypy rag_quest/
```

### Structure

- Keep modules focused and single-purpose
- Add docstrings to all functions and classes
- Use async/await consistently
- Prefer composition over inheritance

### Adding New Features

1. **New LLM Provider**: 
   - Extend `BaseLLMProvider` in `llm/`
   - Implement `complete()` method
   - Add tests

2. **New Game System**:
   - Add to `engine/` module
   - Update `GameState` if needed
   - Add serialization support

3. **New Commands**:
   - Add handler to `_handle_command()` in `engine/game.py`
   - Update help text
   - Test with rich formatting

### Testing

- Write tests for new features
- Use pytest fixtures for setup
- Test async code with pytest-asyncio
- Aim for >80% coverage

```bash
pytest --cov=rag_quest --cov-report=html
```

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

2. **Make your changes**
   - Keep commits atomic and well-described
   - Run tests before committing
   - Format code (black, isort)

3. **Submit a PR**
   - Clear title and description
   - Link related issues
   - Include before/after examples if UI changes

4. **Respond to review**
   - Address feedback respectfully
   - Request re-review after changes

## What We're Looking For

### High Priority
- Bug fixes and stability improvements
- Better error messages and handling
- Performance optimizations
- Documentation improvements
- Example lore and worlds

### Medium Priority
- New LLM provider integrations
- UI/UX improvements
- Test coverage
- Code cleanup and refactoring

### Lower Priority (Future)
- New game mechanics (v0.2+)
- Web UI
- Multiplayer features
- Voice I/O

## Reporting Issues

Use GitHub Issues with:
- Clear title and description
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Python version and OS
- LLM provider and model being used

Example:
```
Title: RAG queries return incorrect context for location changes

Steps:
1. Create new game
2. Move to different location with: "I go to the forest"
3. Query with /look
4. RAG returns context from previous location

Expected: Context from forest
Actual: Context from starting location
```

## Documentation

- Update README.md for user-facing changes
- Add docstrings to new functions
- Include inline comments for complex logic
- Document new config options in .env.example

## Performance Considerations

- LightRAG queries should be <3 seconds
- Game loop should remain responsive
- Lore ingestion should show progress
- Lazy-load RAG on first use

## Community

- Be respectful and inclusive
- Help others with questions
- Share your custom worlds and lore
- Give feedback on ideas

## Questions?

- Open a discussion issue
- Check existing issues first
- Join the community (when available)

Thank you for helping make RAG-Quest amazing!
