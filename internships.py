"""Regras de domínio do módulo de estágios."""

from datetime import date
from urllib.parse import urlparse


MODALITIES = {
    "presencial": "Presencial",
    "hibrido": "Híbrido",
    "remoto": "Remoto",
}


def _required(form, name, label, limit):
    value = form.get(name, "").strip()
    if not value:
        raise ValueError(f"Preencha {label}.")
    if len(value) > limit:
        raise ValueError(f"{label.capitalize()} deve ter no máximo {limit} caracteres.")
    return value


def _optional(form, name, label, limit):
    value = form.get(name, "").strip()
    if len(value) > limit:
        raise ValueError(f"{label.capitalize()} deve ter no máximo {limit} caracteres.")
    return value


def safe_application_url(raw):
    value = (raw or "").strip()
    if not value:
        return None
    if len(value) > 2048:
        raise ValueError("O link de inscrição é muito longo.")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Use um link seguro iniciado por http:// ou https://.")
    return value


def validate_internship(form, allowed_classes, today=None):
    today = today or date.today()
    class_name = _required(form, "class_name", "a turma", 32)
    if class_name not in set(allowed_classes):
        raise ValueError("Você só pode publicar para uma turma vinculada à sua conta.")

    modality = form.get("modality", "").strip().lower()
    if modality not in MODALITIES:
        raise ValueError("Escolha uma modalidade válida.")

    deadline_text = _required(form, "deadline", "o prazo de inscrição", 10)
    try:
        deadline = date.fromisoformat(deadline_text)
    except ValueError as exc:
        raise ValueError("Informe um prazo de inscrição válido.") from exc
    if deadline < today:
        raise ValueError("O prazo de inscrição não pode estar no passado.")

    application_url = safe_application_url(form.get("application_url"))
    instructions = _optional(
        form, "application_instructions", "as instruções de inscrição", 3000
    )
    if not application_url and not instructions:
        raise ValueError("Informe um link ou instruções para o aluno se inscrever.")

    return {
        "company": _required(form, "company", "a empresa ou instituição", 120),
        "title": _required(form, "title", "o título da vaga", 160),
        "description": _required(form, "description", "a descrição da oportunidade", 10000),
        "location": _required(form, "location", "o local de atuação", 160),
        "modality": modality,
        "workload": _optional(form, "workload", "a carga horária", 80),
        "requirements": _optional(form, "requirements", "os requisitos", 5000),
        "application_url": application_url,
        "application_instructions": instructions,
        "deadline": deadline.isoformat(),
        "class_name": class_name,
    }


def present_internship(item, today=None):
    today = today or date.today()
    result = dict(item)
    deadline = date.fromisoformat(str(result["deadline"])[:10])
    remaining = (deadline - today).days
    result["days_left"] = remaining
    result["deadline_label"] = deadline.strftime("%d/%m/%Y")
    result["deadline_state"] = "today" if remaining == 0 else "soon" if remaining <= 7 else "open"
    result["deadline_copy"] = (
        "Último dia" if remaining == 0 else
        "1 dia restante" if remaining == 1 else
        f"{remaining} dias restantes"
    )
    result["modality_label"] = MODALITIES.get(result["modality"], result["modality"])
    return result
