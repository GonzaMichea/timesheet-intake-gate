# Punto de entrada de la función Python en Vercel (design §1)
import sys
from pathlib import Path

# Vercel ejecuta este archivo desde api/; la raíz del repo debe estar en el path para importar backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.main import app  # noqa: E402

__all__ = ["app"]
