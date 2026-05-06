# Design Template

## Problem

Xây dựng hệ thống nghiên cứu tự động cho query kỹ thuật (ví dụ: GraphRAG state-of-the-art), tạo câu trả lời có cấu trúc từ nhiều bước: thu thập thông tin, phân tích, và viết tổng hợp. Hệ thống cần trace được từng bước và benchmark được single-agent vs multi-agent theo latency, cost, quality.

## Why multi-agent?

Single-agent thường gộp tất cả nhiệm vụ trong một lần gọi model nên khó kiểm soát chất lượng từng bước, khó debug khi lỗi, và khó giải thích tại sao output tốt/xấu. Multi-agent cho phép tách vai trò rõ ràng:
- `Researcher` tối ưu thu thập nguồn.
- `Analyst` tối ưu phân tích và đánh giá bằng chứng.
- `Writer` tối ưu chất lượng câu trả lời cuối.
- `Supervisor` kiểm soát luồng, guardrails, và điều kiện dừng.

Nhờ vậy hệ thống dễ quan sát, dễ benchmark, và dễ cải tiến theo từng module.

## Agent roles

| Agent      | Responsibility                                                                                                  | Input                                                  | Output                                             | Failure mode                                                |
| ---------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ | -------------------------------------------------- | ----------------------------------------------------------- |
| Supervisor | Quyết định route tiếp theo (`researcher` / `analyst` / `writer` / `done`) theo state hiện tại và max iterations | `ResearchState` (notes, final_answer, iteration)       | Cập nhật `route_history`, `iteration`, trace route | Route sai thứ tự, loop dài, hoặc stop sớm                   |
| Researcher | Thu thập nguồn và tạo research notes tóm tắt                                                                    | Query + `max_sources`                                  | `sources`, `research_notes`                        | API search lỗi/không có key, nguồn trùng/lệch chủ đề        |
| Analyst    | Phân tích notes thành claims, gaps, confidence                                                                  | `query`, `research_notes`                              | `analysis_notes`                                   | Endpoint LLM lỗi hoặc phân tích hời hợt                     |
| Writer     | Tổng hợp câu trả lời cuối có cấu trúc và references                                                             | `query`, `research_notes`, `analysis_notes`, `sources` | `final_answer`                                     | Hallucination, thiếu references, nội dung chưa sát audience |

## Shared state

- `request`: chứa `query`, `max_sources`, `audience`, là input chuẩn cho toàn pipeline.
- `iteration`: đếm số vòng workflow, phục vụ guardrail dừng.
- `route_history`: lưu lịch sử route để debug hành vi supervisor.
- `sources`: danh sách `SourceDocument` thu thập bởi researcher.
- `research_notes`: tóm tắt từ researcher, làm input cho analyst/writer.
- `analysis_notes`: phân tích trung gian, làm input cho writer.
- `final_answer`: output cuối của hệ thống.
- `agent_results`: log kết quả từng agent (content + metadata như token/cost/duration).
- `trace`: sự kiện quan sát được theo bước (route, span timing, lỗi).
- `errors`: ghi lỗi không chặn cứng để vẫn trả state cuối cùng.

## Routing policy

Graph tuyến tính có điều kiện:

`START -> Supervisor -> {Researcher | Analyst | Writer | DONE}`

Luật định tuyến:
1. Nếu `iteration >= max_iterations` -> `done`.
2. Nếu chưa có `research_notes` -> `researcher`.
3. Nếu đã có `research_notes` nhưng chưa có `analysis_notes` -> `analyst`.
4. Nếu đã có `analysis_notes` nhưng chưa có `final_answer` -> `writer`.
5. Nếu đã có `final_answer` -> `done`.

Sau mỗi worker, quay lại Supervisor để quyết định bước kế tiếp.

## Guardrails

- Max iterations:
  - Dùng `MAX_ITERATIONS` (default 6) để chặn loop vô hạn.
- Timeout:
  - Mỗi LLM call dùng `TIMEOUT_SECONDS` (default 60).
- Retry:
  - `LLMClient` retry 2 lần với backoff ngắn.
- Fallback:
  - Nếu endpoint LLM lỗi/unavailable: trả `offline fallback response` để pipeline không crash.
  - Nếu search provider không sẵn: dùng local fallback documents.
- Validation:
  - Input/output chính dùng Pydantic schemas (`ResearchQuery`, `SourceDocument`, `ResearchState`, `BenchmarkMetrics`).
  - Query có ràng buộc `min_length`, nguồn có shape rõ ràng.

## Benchmark plan

### Queries
1. "Research GraphRAG state-of-the-art and write a 500-word summary"
2. "Compare multi-agent and single-agent orchestration patterns for enterprise assistants"
3. "Design guardrails for production AI agent workflow and explain trade-offs"

### Metrics
- `latency_seconds`: thời gian chạy end-to-end mỗi mode.
- `estimated_cost_usd`: tổng cost ước tính từ metadata từng agent.
- `quality_score` (0-10): heuristic dựa trên đủ các phần notes/analysis/final answer/references.
- `notes`: số iteration, số sources, số errors để đọc nhanh run health.

### Expected outcome
- Multi-agent thường có `quality_score` cao hơn baseline do tách bước và có nguồn/analysis rõ hơn.
- Multi-agent thường chậm hơn baseline (latency cao hơn) và có thể cost cao hơn.
- Trace của multi-agent phải giải thích được agent nào làm gì, ở vòng nào, và lỗi nằm ở đâu nếu có.
