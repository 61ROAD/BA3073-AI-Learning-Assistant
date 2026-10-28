from __future__ import annotations

import json
from typing import Any, Callable

from backend.artifacts.filesystem import ArtifactRun
from backend.pipelines.authorship import add_author_credit
from backend.pipelines.common import (
    PipelineError,
    PipelineResult,
    extract_fenced_or_raw,
    format_citations,
    format_log,
)
from backend.pipelines.html_to_pdf import (
    A4_PAGE,
    ConvertError,
    HtmlToPdfConverter,
)
from backend.providers.base import (
    ModelProviderError,
    TextGenerationProvider,
    TextGenerationRequest,
)
from backend.timing import RunTimingRecorder, measure_stage


def run_essay_html_pipeline(
    *,
    artifact_run: ArtifactRun,
    model_profile: dict[str, Any],
    model_provider: TextGenerationProvider,
    pdf_converter: HtmlToPdfConverter,
    task_text: str,
    context_bundle: str,
    output_preference: str | None,
    options: dict[str, Any] | None,
    search: dict[str, Any],
    max_output_tokens: int,
    emit_event: Callable[[str, str], None] | None = None,
    timing: RunTimingRecorder | None = None,
) -> PipelineResult:
    log_lines = [
        "Pipeline: essay_html",
        f"Output preference: {output_preference or 'pdf'}",
        "Stage: generate_source",
    ]
    system_prompt, user_prompt = build_essay_html_prompt(
        task_text=task_text,
        context_bundle=context_bundle,
        options=options or {},
        search=search,
    )
    if emit_event:
        emit_event("generate_source", "Generating essay HTML source")

    try:
        with measure_stage(timing, "provider_generation"):
            raw_output = model_provider.generate_text(
                TextGenerationRequest(
                    profile=model_profile,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_output_tokens=max_output_tokens,
                    temperature=0.2,
                )
            )
    except ModelProviderError as exc:
        raise PipelineError(
            exc.code,
            exc.message,
            stage="generate_source",
            log_lines=log_lines,
        ) from exc
    except Exception as exc:
        raise PipelineError(
            "provider_unavailable",
            "The model provider request failed.",
            stage="generate_source",
            log_lines=log_lines,
        ) from exc

    source = extract_fenced_or_raw(raw_output, accepted_languages={"html", "htm"})
    source = add_author_credit(source.strip()) + "\n"
    html_path = artifact_run.write_output(
        "main.html",
        source,
        kind="source",
        media_type="text/html",
    )
    log_lines.extend(["Output: output/main.html", "Stage: convert_pdf"])
    if emit_event:
        emit_event("convert_pdf", "Converting essay HTML to PDF")

    pdf_path = artifact_run.run_dir / "output" / "main.pdf"
    try:
        with measure_stage(timing, "convert_pdf"):
            convert_result = pdf_converter.convert(
                html_path=html_path,
                pdf_path=pdf_path,
                page_config=A4_PAGE,
            )
    except ConvertError as exc:
        artifact_run.write_log("convert.log", exc.log_text)
        raise PipelineError(
            "convert_failed",
            exc.message,
            stage="convert_pdf",
            log_lines=log_lines,
        ) from exc
    except Exception as exc:
        artifact_run.write_log(
            "convert.log",
            "HTML-to-PDF converter raised an unexpected error.\n",
        )
        raise PipelineError(
            "convert_failed",
            "HTML-to-PDF conversion failed.",
            stage="convert_pdf",
            log_lines=log_lines,
        ) from exc

    artifact_run.write_log("convert.log", convert_result.log_text)
    artifact_run.write_output(
        "main.pdf",
        convert_result.pdf_path.read_bytes(),
        kind="pdf",
        media_type="application/pdf",
    )
    log_lines.extend(["Convert: pdf_ok", "Output: output/main.pdf"])
    return PipelineResult(log_text=format_log(log_lines))


def build_essay_html_prompt(
    *,
    task_text: str,
    context_bundle: str,
    options: dict[str, Any],
    search: dict[str, Any],
) -> tuple[str, str]:
    system_prompt = """
You are an academic technical report writer for the BA3073 assignment
"From AI Agent to Cloud Service".

Write a clear, evidence-based report about deploying the supplied AI Learning
Assistant. Return only a complete self-contained HTML document, without
Markdown fences or surrounding explanation.

Structure the report as follows:
1. Title and introduction: assignment purpose, scope, and application overview.
2. System architecture: explain the browser UI, FastAPI backend, Qwen-compatible
   model API, SQLite database, persistent workspace, and Docker Compose.
3. Task 1 - Local deployment: prerequisites, build and startup commands,
   health check, local UI verification, and an actual AI generation test.
   Explain how the report-generation instructions were improved.
4. Task 2 - Aliyun ECS deployment: target Linux CPU architecture, image build,
   Alibaba Cloud ACR push and pull, ECS container startup, port mapping,
   security-group restriction to the student's public IP, and UI verification.
5. Task 3 - Domain and secure access: DNS A record, Nginx reverse proxy,
   Certbot HTTPS, and a separate reverse-proxy access-control layer.
   Explain closing public access to port 14242 after verifying the proxy.
6. Security, persistence, and cost: API-key protection, encryption-key storage,
   the limitations of built-in BNBU authentication, persistent data volumes,
   relevant cloud costs, and resource cleanup.
7. Evaluation and improvements: actual results, encountered problems,
   limitations, and realistic future improvements.
8. Conclusion and references.

Explain what each important command does and why each component is needed.
Distinguish steps actually completed from proposed improvements.
Use concise paragraphs, numbered procedures, and small tables where useful.
Follow the language requested by the user.

Use only deployment facts and evidence supplied in the task and context.
Never invent successful tests, command output, IP addresses, domains,
certificate status, screenshots, citations, or costs.
If evidence is missing, insert a clearly labeled "Evidence required"
placeholder describing exactly what the student must supply.

Include evidence locations for:
- Task 1: local UI screenshot with browser address bar and local-ui-check.txt.
- Task 2: ECS UI screenshot with browser address bar and ecs-docker-check.txt.
- Task 3: the actual HTTPS domain URL and screenshot of the application after
  successful reverse-proxy access control, with browser address bar visible.
Explain how the access-control check was verified; do not treat the built-in
BNBU login as the required reverse-proxy protection.

Give each supplied screenshot a figure number, caption, and explanation.
Embed screenshot images only when usable inline image data is supplied.
Otherwise leave a labeled placeholder for later insertion; do not invent paths
or substitute a generated illustration for deployment evidence.
Never reproduce API keys, passwords, tokens, or other secrets.

Keep the final report within 20 A4 pages, including figures and references.
Target 10-15 pages to leave room for screenshots. Use readable print styling,
compact code blocks, and sensible page breaks. Page count must be checked
after PDF generation; do not claim it has been verified.
"""
    output_instruction = (
        "Return one complete self-contained HTML document. It must start with "
        "<!doctype html> and include <html>, <head>, and <body>. Include all CSS "
        "inside a <style> element: use a readable serif academic print layout, "
        "clear heading hierarchy, careful paragraph spacing, and CSS "
        "@page { size: A4; margin: 20mm; }. Do not use external stylesheet links, "
        "remote images, or remote HTTP(S) assets. If mathematical notation is "
        "needed, include inline KaTeX-compatible markup and any needed minimal "
        "KaTeX styling inline in the document; do not fetch KaTeX from a CDN at "
        "render time. Use inline SVG or CSS for diagrams. Cite any provided web "
        "sources in a References section using ordinary HTML. Do not wrap the "
        "answer in Markdown fences."
    )
    user_prompt = "\n\n".join(
        [
            "[Assignment Task]\n" + task_text.strip(),
            "[Prepared Context]\n" + context_bundle.strip(),
            "[Search Citations]\n" + format_citations(search),
            "[Options]\n" + json.dumps(options, sort_keys=True),
            "[Output Contract]\n" + output_instruction,
        ]
    )
    return system_prompt, user_prompt
