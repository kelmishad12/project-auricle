# How to Contribute to Project Auricle

We would love to accept your patches and contributions to the Contextual Briefing Bot project.

## Before you begin

### Review our Architecture

Project Auricle is heavily designed around Hexagonal Architecture (Ports and Adapters) and LangGraph. 
Make sure you understand the `/core` (pure LLM logic) vs `/adapters` (concrete API integrations).
- API calls MUST NEVER be in `/core`.
- Pass dependencies strictly via Dependency Injection.

### Review our Community Guidelines

This project follows standard open source contribution guidelines. Please be respectful and rigorous in your code reviews.

## Contribution process

### Code Reviews

All submissions, including submissions by project members, require review. We
use [GitHub pull requests](https://docs.github.com/articles/about-pull-requests)
for this purpose.
