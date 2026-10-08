"""Small, private profile photographs owned by each authenticated account."""

import hashlib
import warnings
from datetime import datetime, timezone
from io import BytesIO

import database as db

MAX_SOURCE_BYTES = 5 * 1024 * 1024
MAX_PHOTO_BYTES = 192 * 1024
PHOTO_SIZE = 320


def normalize_photo(file_storage):
    """Decode the actual image, center-crop and strip all original metadata."""
    from PIL import Image, ImageOps, UnidentifiedImageError

    if not file_storage or not file_storage.filename:
        raise ValueError("Escolha uma foto em JPG ou PNG.")
    source = file_storage.read(MAX_SOURCE_BYTES + 1)
    if not source:
        raise ValueError("A foto selecionada está vazia.")
    if len(source) > MAX_SOURCE_BYTES:
        raise ValueError("Escolha uma foto de até 5 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(source)) as image:
                if image.format not in {"JPEG", "PNG"}:
                    raise ValueError("Envie uma foto em JPG ou PNG.")
                if image.width * image.height > 16_000_000:
                    raise ValueError("Esta imagem é muito grande. Escolha uma versão menor.")
                image.load()
                oriented = ImageOps.exif_transpose(image)
                square = ImageOps.fit(oriented.convert("RGBA"), (PHOTO_SIZE, PHOTO_SIZE),
                                      method=Image.Resampling.LANCZOS)
                flat = Image.new("RGB", square.size, "white")
                flat.paste(square, mask=square.getchannel("A"))
                output = BytesIO()
                flat.save(output, format="JPEG", quality=86, optimize=True)
                content = output.getvalue()
    except (UnidentifiedImageError, OSError, SyntaxError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("Não foi possível abrir esta foto. Envie um JPG ou PNG válido.") from exc
    if len(content) > MAX_PHOTO_BYTES:
        raise ValueError("Não foi possível otimizar esta foto. Escolha outra imagem.")
    return content


def photo_revision(username):
    with db.connection() as conn:
        row = conn.execute("SELECT revision FROM profile_photos WHERE username=?", (username,)).fetchone()
        return row["revision"] if row else ""


def get_photo(username):
    with db.connection() as conn:
        row = conn.execute("SELECT content, revision FROM profile_photos WHERE username=?", (username,)).fetchone()
        return dict(row) if row else None


def save_photo(username, content):
    revision = hashlib.sha256(content).hexdigest()
    with db.connection() as conn:
        conn.execute(
            """INSERT INTO profile_photos(username, content, revision, updated_at)
               VALUES(?,?,?,?) ON CONFLICT(username) DO UPDATE SET
               content=excluded.content, revision=excluded.revision, updated_at=excluded.updated_at""",
            (username, content, revision, datetime.now(timezone.utc).isoformat()),
        )
    return revision


def remove_photo(username):
    with db.connection() as conn:
        conn.execute("DELETE FROM profile_photos WHERE username=?", (username,))
