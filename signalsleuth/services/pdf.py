"""Minimal dependency-free PDF generation for feedback and question exports."""
from .. import db


def text_to_simple_pdf(lines):
    # Escape PDF string specials
    def esc(s):
        return str(s).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    y_start = 800
    content_ops = ["BT", "/F1 11 Tf", "14 TL", f"50 {y_start} Td"]
    first = True
    for line in lines:
        line = line[:110]
        if not first:
            content_ops.append("T*")
        first = False
        content_ops.append(f"({esc(line)}) Tj")
    content_ops.append("ET")
    stream = "\n".join(content_ops)
    objects = []
    objects.append("1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj")
    objects.append("2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj")
    objects.append(
        "3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj"
    )
    objects.append(f"4 0 obj<< /Length {len(stream)} >>stream\n{stream}\nendstream endobj")
    objects.append("5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj")
    out = ["%PDF-1.4"]
    offsets = [0]
    for obj in objects:
        offsets.append(sum(len(x) + 1 for x in out))
        out.append(obj)
    xref_pos = sum(len(x) + 1 for x in out)
    out.append(f"xref\n0 {len(objects)+1}")
    out.append("0000000000 65535 f ")
    for off in offsets[1:]:
        out.append(f"{off:010d} 00000 n ")
    out.append(f"trailer<< /Size {len(objects)+1} /Root 1 0 R >>")
    out.append(f"startxref\n{xref_pos}\n%%EOF")
    return ("\n".join(out)).encode("latin-1", errors="replace")


def build_feedback_pdf(user, chapter_num, level_num, row, feedback):
    """Minimal PDF generator (no external deps). Includes model answers after clear."""
    lines = []
    lines.append(f"Signal Sleuth — Level Feedback")
    lines.append(f"Student: {user.get('full_name') or ''} ({user.get('generated_username') or ''})")
    lines.append(f"ID: {user.get('student_id')}  Email: {user.get('email')}")
    lines.append(f"Chapter {chapter_num}  Level {level_num}")
    lines.append(f"Score: {row.get('best_score')}/{row.get('max_score')}  Attempts: {row.get('attempts')}  Cleared: {'Yes' if row.get('cleared') else 'No'}")
    lines.append("")
    lines.append("-" * 60)
    # Model answers from question bank
    try:
        bank = [q for q in db.list_question_bank(chapter_num) if int(q["level_num"]) == int(level_num)]
        if bank:
            lines.append("CORRECT / MODEL ANSWERS")
            for q in bank:
                lines.append(f"Q{q['q_index']}. {q['question_text']}")
                lines.append(f"   Answer: {q.get('model_answer') or '—'}")
            lines.append("-" * 60)
    except Exception:
        pass
    lines.append("YOUR SUBMISSION FEEDBACK")

    if isinstance(feedback, list):
        for i, item in enumerate(feedback, 1):
            if isinstance(item, dict):
                q = item.get("question") or item.get("q") or item.get("prompt") or f"Item {i}"
                a = item.get("answer") or item.get("a") or item.get("student_answer") or ""
                fdb = item.get("feedback") or item.get("correct") or item.get("note") or ""
                sc = item.get("score", "")
                lines.append(f"{i}. {q}")
                lines.append(f"   Your answer: {a}")
                if fdb:
                    lines.append(f"   Feedback: {fdb}")
                if sc != "":
                    lines.append(f"   Score: {sc}")
                lines.append("")
            else:
                lines.append(f"{i}. {item}")
                lines.append("")
    elif isinstance(feedback, dict):
        for k, v in feedback.items():
            lines.append(f"{k}: {v}")
    else:
        lines.append(str(feedback or "No detailed feedback stored."))
    return text_to_simple_pdf(lines)
