# Thành viên và phân công nhóm Transformer

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4-L3B-DAY10 |
| Tên nhóm | Transformer |
| Repository nộp bài | https://github.com/ringge/K4-L3B-DAY10-Transformer-DataPipelineDataObservability |

## Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò chính | Báo cáo cá nhân |
| ---: | --- | --- | --- | --- | --- |
| 1 | Trần Kim Phương | 2A202602565 | tkphuong132@gmail.com | Trưởng nhóm; Crossref ingestion, corruption và repair | [2A202602565_TranKimPhuong.md](../report/2A202602565_TranKimPhuong.md) |
| 2 | Trần Gia Thành | 2A202602626 | giathanh232004@gmail.com | Cleaning, data quality/freshness và benchmark | [2A202602626_TranGiaThanh.md](../report/2A202602626_TranGiaThanh.md) |
| 3 | Nguyễn Minh Thái | 2A202602726 | minhthai030896@gmail.com | Điều phối baseline pipeline và báo cáo Phase 1 | [2A202602726_NguyenMinhThai.md](../report/2A202602726_NguyenMinhThai.md) |

## Phân công và bằng chứng

### Trần Kim Phương — ingestion, corruption và repair

| Deliverable | Phạm vi thực hiện | Output và cách kiểm tra | Commit tiêu biểu |
| --- | --- | --- | --- |
| Crossref ingestion | `src/ingestion/crossref.py`: parse metadata, dùng snapshot mặc định, retry/fallback khi refresh | `data/raw/crossref_response.json`, `data/raw/crossref_records.json`; `tests/test_crossref.py` | `f23df5f` |
| Sáu kịch bản corruption | `src/ingestion/corruption.py`: xóa record mới, blank summary, inject noise, truncate title, làm cũ ngày và duplicate; ghi log thay đổi | `data/clean/papers_clean_corrupted.{csv,json}`, `data/results/corruption_log.json`; `tests/test_corruption.py` | `7c41db2` |
| Repair và so sánh | `src/pipelines/corruption_flow.py` dựng lại từ raw snapshot, xây index riêng và đánh giá lại; `generate_corruption_report` trong `src/observability/reporting.py` | `data/clean/papers_clean_repaired.{csv,json}`, `data/results/{corrupted,repaired}_metrics.json`, `data/reports/corruption_report.md` | `e773859` |

Corruption và repair dùng lại `data/eval/test_set.json` của baseline. Commit `e773859` cũng sửa Chroma manifest sang đường dẫn tương đối và thêm `tests/test_index_manifest.py`.

### Trần Gia Thành — cleaning, observability và benchmark

| Deliverable | Phạm vi thực hiện | Output và cách kiểm tra | Commit tiêu biểu |
| --- | --- | --- | --- |
| Clean data và quality gate | `src/ingestion/cleaning.py` chuẩn hóa schema, `age_days`, `text_for_embedding`; `src/observability/quality.py` chạy 7 Great Expectations checks và freshness SLA | `data/clean/papers_clean.{csv,json}`, `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json` | `71773ac` |
| Evaluation set | `src/evaluation/testset.py` tạo 10 câu xác định từ clean data, gắn ground-truth DOI | `data/eval/test_set.json` với 3 summary, 3 authors, 2 date, 2 categories | `8582bf4` |
| Dashboard bổ trợ | `app/observability_dashboard.py` đọc artifact ba trạng thái và hiển thị KPI, phân bố `age_days`, cảnh báo quality/freshness | Giao diện Streamlit; dữ liệu lấy từ `data/results/`, `data/quality/`, `data/clean/` | `eb03bbf` |

Việc dùng `LocalEmbeddingIndex.build` cho baseline là tích hợp logic index có sẵn trong project; dashboard chỉ đọc artifact, không tạo metric hay sửa dữ liệu nguồn. Trần Gia Thành cũng cập nhật thông tin nhóm trong commit `9d30dce`.

### Nguyễn Minh Thái — baseline orchestration và report

| Deliverable | Phạm vi thực hiện | Output và cách kiểm tra | Commit tiêu biểu |
| --- | --- | --- | --- |
| Phase 1 end-to-end | `src/pipelines/phase1.py` nối Crossref ingestion → cleaning → Chroma baseline index → test set → evaluation → quality/freshness | `data/clean/papers_clean.{csv,json}`, `data/embeddings/papers_embeddings.json`, `data/results/baseline_{metrics,answers}.json`, quality artifacts | `cb07796` |
| Baseline report | `generate_phase1_report` trong `src/observability/reporting.py` tổng hợp source, evaluation và quality/freshness | `data/reports/phase1_report.md`: 24 raw/clean records, 10 câu, 7/7 GX checks PASS | `cb07796` |

Phạm vi này là điều phối baseline và báo cáo Phase 1; implementation corruption/repair và comparison report thuộc Trần Kim Phương.

## Tích hợp và kết quả chung

```text
Crossref snapshot → raw records → clean dataset → baseline index/evaluation
    → quality + freshness → corrupted dataset/index/evaluation
    → repair từ raw snapshot → repaired index/evaluation → báo cáo so sánh
```

Các artifact đã commit ghi nhận 24 → 23 → 24 dòng ở baseline → corrupted → repaired; retrieval hit rate 100% → 60% → 100%, mean token F1 1.000 → 0.579 → 1.000, GX checks 7/7 → 5/7 → 7/7 và freshness PASS → FAIL → PASS. Cả ba đánh giá dùng cùng test set 10 câu. `judge_accuracy` của corrupted là **60% (6/10)** theo `data/results/corrupted_metrics.json` và `data/results/corrupted_answers.json`. Xem [báo cáo nhóm](../report/group_report.md) để biết phương pháp, giới hạn và nguồn của từng chỉ số.

Lệnh kiểm tra hiện có: `.venv/bin/python -m unittest discover -s tests -v` (9 tests `OK` ngày 2026-09-26). Kết quả pipeline toàn phần trong báo cáo được đối chiếu từ artifact đã commit; chưa được chạy lại khi hoàn thiện tài liệu.
