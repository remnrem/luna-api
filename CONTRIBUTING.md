# Contributing to lunapi

Thank you for your interest in contributing. This document covers bug reports, feature requests, and pull requests.

## Bug reports

Open an issue on [GitHub Issues](https://github.com/remnrem/luna-api/issues) and include:

- Operating system and Python version
- `lunapi` version (`pip show lunapi`)
- A minimal description of what you did, what you expected, and what happened
- The full traceback if an exception was raised

## Feature requests

Open an issue labelled **enhancement** describing the use case and why existing functionality does not cover it.

## Pull requests

Note: `lunapi` wraps a compiled C/C++ extension (`lunapi0`). Most contributions will be to the Python layer in `src/lunapi/`. Changes to the C++ layer require a local build (see `INSTALL.md`).

1. Fork the repository and create a branch from `main`.
2. Install in editable mode with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
3. Make your changes. Add or update tests under `tests/` where relevant.
4. Run the test suite before submitting:
   ```bash
   pytest
   ```
5. Open a pull request against `main` with a short description of the change and the motivation.

Please keep pull requests focused — one logical change per PR makes review easier.

## Code style

The project follows [PEP 8](https://peps.python.org/pep-0008/). `black` and `isort` are used for formatting. Running `black .` and `isort .` before committing is appreciated but not required.

## Code of conduct

This project follows the [Contributor Covenant Code of Conduct v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating you agree to abide by its terms. Report unacceptable behaviour to `luna.remnrem@gmail.com`.

## Questions

For usage questions that are not bug reports, write to `luna.remnrem@gmail.com` or open a GitHub Discussion if the repository has that feature enabled.
