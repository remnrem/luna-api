"""Allow ``python -m lunapi`` to invoke the Luna CLI."""

from .cli import main


raise SystemExit(main())
