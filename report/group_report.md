# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4-L3B-DAY10 |
| Tên nhóm | Transformer |
| Repository | https://github.com/ringge/K4-L3B-DAY10-Transformer-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

### Thành viên và phân công

Phân công dưới đây đối chiếu báo cáo cá nhân với commit triển khai và thống nhất với [`docs/TEAM.md`](../docs/TEAM.md).

| STT | Họ và tên | MSSV | Vai trò và phần việc sở hữu | Commit tiêu biểu |
| ---: | --- | --- | --- | --- |
| 1 | Trần Kim Phương | 2A202602565 | Trưởng nhóm; `src/ingestion/crossref.py`, `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py`, báo cáo đối chiếu | `f23df5f`, `7c41db2`, `e773859` |
| 2 | Trần Gia Thành | 2A202602626 | Cleaning, quality/freshness, test set; dashboard Streamlit bổ trợ | `71773ac`, `8582bf4`, `eb03bbf` |
| 3 | Nguyễn Minh Thái | 2A202602726 | `src/pipelines/phase1.py`, `generate_phase1_report` trong `src/observability/reporting.py` | `cb07796` |

Báo cáo riêng: [Trần Kim Phương](2A202602565_TranKimPhuong.md), [Trần Gia Thành](2A202602626_TranGiaThanh.md), [Nguyễn Minh Thái](2A202602726_NguyenMinhThai.md).

## 2. Tóm tắt kết quả

Nhóm hoàn thành luồng từ snapshot Crossref qua chuẩn hóa, ChromaDB, bộ đánh giá 10 câu, Great Expectations, freshness SLA, sáu kịch bản corruption và repair bằng cách dựng lại dữ liệu từ raw snapshot. Baseline tạo 24 clean records, index/manifest, test set, answers/metrics JSON, quality/freshness JSON và báo cáo Markdown. Trên các artifact đã commit, baseline có retrieval hit rate 100%, mean token F1 1.000, quality gate PASS (7/7 checks) và freshness PASS (1/24 record cũ). Corruption xóa 5 record mới, sửa nội dung/ngày và thêm 4 dòng trùng; corpus còn 23 dòng với 19 `paper_id` duy nhất. Bốn câu mất retrieval hit đều tham chiếu ID thuộc nhóm record bị xóa, nên thao tác này có bằng chứng trực tiếp nhất đối với retrieval. Bộ corruption kết hợp làm hit rate giảm còn 60%, token F1 còn 0.579, quality FAIL (5/7) và freshness FAIL (9/23 record cũ). Repair khôi phục 24 dòng, 7/7 checks, freshness PASS và hai metric retrieval/answer về baseline. Giới hạn quan trọng: benchmark chỉ có 10 câu sinh từ metadata; GX chưa bắt riêng noise/title bị cắt, và judge baseline dùng LLM trong khi hai trạng thái sau dùng heuristic fallback. Nhóm đã chạy 9 unit tests thành công; chưa chạy lại hai pipeline toàn phần trên phiên bản báo cáo này.

## 3. Kiến trúc và luồng dữ liệu

```text
Crossref /works hoặc data/raw/crossref_response.json (snapshot mặc định)
  -> data/raw/crossref_records.json -> cleaning -> data/clean/papers_clean.*
  -> MiniLM + ChromaDB papers-baseline -> test_set.json -> baseline metrics
  -> GX quality + freshness -> phase1_report.md
  -> sáu corruption trên bản sao clean data -> papers-corrupted -> quality/evaluation
  -> raw snapshot -> cleaning lại -> papers-repaired -> quality/evaluation
  -> corruption_report.md (cùng test set cho cả ba trạng thái)
```

| Khối | Input và xử lý | Output/artifact | Owner |
| --- | --- | --- | --- |
| Ingestion | Snapshot mặc định; tùy chọn gọi Crossref `/works`, retry rồi fallback | `data/raw/crossref_response.json`, `crossref_records.json` | Trần Kim Phương |
| Cleaning | Raw records; chuẩn hóa HTML, bỏ record thiếu, khử trùng lặp DOI | `data/clean/papers_clean.{csv,json}` | Trần Gia Thành |
| Embedding/index | `text_for_embedding` qua MiniLM, ChromaDB collection riêng | `data/chroma/`, `data/embeddings/papers_embeddings*.json` | Logic từ scaffold; Trần Gia Thành tích hợp baseline, Trần Kim Phương tích hợp corrupted/repaired và sửa manifest |
| Evaluation | 10 câu, DOI ground truth, retrieval hit, token F1, judge | `data/eval/test_set.json`, `data/results/*_answers.json`, `*_metrics.json` | Trần Gia Thành tạo test set; Nguyễn Minh Thái và Trần Kim Phương điều phối |
| Observability | 7 GX expectations và freshness SLA | `data/quality/*_quality_report.json`, `*_freshness_report.json` | Trần Gia Thành |
| Corruption/repair | Bản sao clean data; rebuild từ raw records | `data/clean/papers_clean_{corrupted,repaired}.*`, `data/results/corruption_log.json` | Trần Kim Phương |
| Orchestration/reporting | Chạy các khối theo thứ tự, tổng hợp artifact | `data/reports/phase1_report.md`, `corruption_report.md` | Nguyễn Minh Thái (baseline), Trần Kim Phương (comparison) |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị code/artifact xác nhận |
| --- | --- |
| `LLM_PROVIDER`, `LLM_MODEL` | custom, gpt-6-luna |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Nguồn/số record | Snapshot `data/raw/crossref_response.json`; `max_results=24`, raw records hiện có 24 |
| Retrieval `top_k` | 4 |
| Freshness | Cũ khi `age_days > 180`; SLA đạt nếu tỷ lệ cũ ≤ 25% |
| Random seed | Không dùng; test set và corruption chọn theo thứ tự xác định |
| `REFRESH_SOURCE` | Mặc định tắt; bật mới gọi Crossref trước khi fallback snapshot |
| `RUN_RAGAS` | Không bật trong artifacts hiện tại |

Cài project trong Python 3.11–3.13 và cấu hình credential cho provider nếu muốn dùng LLM judge. Chạy theo thứ tự:

```bash
python -m pip install -e .
python script/run_phase1.py
python script/run_corruption_flow.py
python -m unittest discover -s tests -v
```

Sau khi có artifacts, có thể mở dashboard bằng `streamlit run app/observability_dashboard.py`. Lần baseline mới sẽ **ghi lại** clean data, test set và metrics; corruption flow dùng các artifact baseline vừa tạo. Giữ snapshot và test set cố định nếu muốn đối chiếu với số liệu dưới đây.

| Lệnh/kiểm tra | Trạng thái xác minh | Bằng chứng |
| --- | --- | --- |
| Baseline pipeline | Artifact của lần chạy 2026-09-26 03:48:18 UTC; chưa chạy lại toàn phần trong lần hoàn thiện báo cáo | `data/reports/phase1_report.md`, `data/results/baseline_metrics.json` |
| Corruption/repair flow | Artifact commit ngày 2026-09-26; không có run timestamp riêng và chưa chạy lại toàn phần | `data/reports/corruption_report.md`, `data/results/{corrupted,repaired}_metrics.json` |
| Unit tests | 9 tests `OK` trên working tree hiện tại (2026-09-26) | `.venv/bin/python -m unittest discover -s tests -v` |

## 5. Ingestion, cleaning và data contract

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API `/works`; mặc định đọc snapshot `data/raw/crossref_response.json` |
| Query/filter ghi trong baseline report | `agentic retrieval augmented generation large language model`; `from-pub-date:2026-03-30,has-abstract:true` |
| Thời điểm | Baseline chạy `2026-09-26T03:48:18.825622+00:00`; thời điểm tải raw snapshot không được lưu |
| Số record | Snapshot 24 items → 24 raw records → 24 clean records |
| Retry/backoff khi refresh | Timeout 20 giây; tối đa 3 lần với lỗi mạng/HTTP 429/5xx; `Retry-After` tối đa 30 giây hoặc backoff lũy thừa; fallback snapshot nếu có |

| Trường/nhóm trường | Kiểu raw → clean | Bắt buộc | Xử lý khi thiếu/sai |
| --- | --- | --- | --- |
| `DOI` → `paper_id` | String → string | Có | Bỏ record rỗng; khử trùng lặp không phân biệt hoa thường |
| `title` → `title` | List/string → string | Có | Lấy text đầu tiên, bỏ HTML, chuẩn hóa whitespace |
| `abstract` → `summary` | HTML string → string | Có | Bỏ HTML/whitespace; bỏ record rỗng; tính `summary_chars` |
| `published`/biến thể → `published` | Crossref date → ISO date | Có | Thử `published`, `published-online`, `published-print`, `created`; bỏ ngày không hợp lệ |
| `author`, `subject` → `authors`, `categories`, các cột `*_joined` | List → list/string | Không | Chuẩn hóa, bỏ giá trị rỗng/trùng |
| `updated`, URL/PDF | Date/URL → string | Không | `updated` fallback ngày xuất bản; URL/PDF fallback DOI URL |
| Derived `age_days`, `text_for_embedding` | Integer, string | Có trong clean schema | Tính từ UTC run timestamp; ghép Title, Summary, Authors, Categories, Published |

| Quy tắc cleaning | Dimension | Số record bị tác động trong snapshot | Bằng chứng |
| --- | --- | ---: | --- |
| Bỏ record thiếu DOI/title/summary/ngày hợp lệ | Completeness/validity | 0 sau parse; 24 raw → 24 clean | `data/raw/crossref_records.json`, `data/clean/papers_clean.json` |
| Khử trùng lặp `paper_id` | Uniqueness | 0 trong baseline | `data/quality/baseline_quality_report.json` |
| Chuẩn hóa HTML/whitespace và tạo derived fields | Consistency | Áp dụng cho 24 records; không lưu số giá trị đổi trước/sau | `src/ingestion/cleaning.py`, clean JSON |

`paper_id` là DOI và là ground-truth document ID. Chroma dùng `paper_id::row_index` làm record ID để chứa được dòng trùng ở trạng thái corrupted; metadata vẫn giữ DOI. `age_days = (run_timestamp_UTC - published_UTC).days`, nên có thể đổi khi chạy vào ngày khác.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 10, từ 10 `paper_id` đầu sau khi sort ổn định |
| `question_type` | 3 `summary`, 3 `authors`, 2 `date`, 2 `categories` |
| Ground truth | Lấy từ clean record; mỗi câu có một `ground_truth_doc_ids` là DOI gốc |
| Embedding/vector store | MiniLM; ChromaDB `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | 4; `answer_question` ưu tiên exact title lookup nếu câu hỏi chứa tiêu đề |
| Answer/judge | Answer lấy metadata của kết quả đầu; judge dùng LLM nếu khả dụng, fallback heuristic khi lỗi |
| Test set chung | `data/eval/test_set.json`; SHA-256 `b85b0571902f6bad6a81603cab7ca5e2133a93b6a8f8ae66bcc3606afa85a529` |

Corruption flow đọc lại cùng test set cho corrupted và repaired. Như vậy câu hỏi, đáp án chuẩn và DOI chuẩn giữ cố định. Tuy nhiên baseline judge reasoning đến từ LLM, còn cả 10 verdict của corrupted và repaired ghi `Fallback heuristic judge used because the LLM evaluator was unavailable.`; các metric judge không hoàn toàn cùng phương pháp chấm.

## 7. Kết quả baseline

| Artifact | Đường dẫn | Trạng thái |
| --- | --- | --- |
| Raw response/records | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Có; 24 records |
| Cleaned dataset | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Có; 24 records |
| Index/manifest | `data/chroma/`, `data/embeddings/papers_embeddings.json` | Có; `papers-baseline`, 24 documents |
| Evaluation set | `data/eval/test_set.json` | Có; 10 câu |
| Baseline metrics/answers | `data/results/baseline_metrics.json`, `data/results/baseline_answers.json` | Có |
| Quality/freshness | `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json` | Có |
| Baseline report | `data/reports/phase1_report.md` | Có |

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 10/10 câu có DOI đúng trong top 4 |
| `mean_token_f1` | 1.000 | Đáp án trùng từ với ground truth trên bộ test |
| `judge_accuracy` | 1.000 | 10/10 judge verdict đúng theo artifact baseline |
| `mean_judge_score` | 5.000/5 | Điểm trung bình của 10 câu |
| Ragas | Không chạy | JSON ghi `RUN_RAGAS=1` mới bật lượt đánh giá này |

Nguồn: `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`. Câu hỏi chứa exact title và đáp án sinh từ metadata nên baseline 100% không đại diện mọi truy vấn tự nhiên.

## 8. Data quality và freshness

| Check | Dimension | Ngưỡng/kỳ vọng | Baseline | Corrupted |
| --- | --- | --- | --- | --- |
| Row count | Completeness | ≥ 1 | PASS, 24 | PASS, 23 |
| `paper_id`, `title`, `summary`, `text_for_embedding` không null | Completeness | 4 expectations | PASS 4/4 | PASS 4/4; chuỗi rỗng khác null |
| `paper_id` duy nhất | Uniqueness | Không trùng | PASS | FAIL, 8 dòng thuộc 4 ID trùng |
| Độ dài `summary` | Validity | ≥ 50 ký tự | PASS | FAIL, 4 dòng rỗng gồm 2 dòng bị sửa và bản duplicate |
| Freshness SLA | Timeliness | Tỷ lệ `age_days > 180` ≤ 25% | PASS, 1/24 (4.2%) | FAIL, 9/23 (39.1%) |

Có **7 GX checks**: 1 row count, 4 not-null, 1 uniqueness, 1 summary length. Freshness bổ sung vào `success` tổng, không tính là check GX thứ tám. Nguồn: `data/quality/{baseline,corrupted,repaired}_quality_report.json` và các freshness report.

| Freshness | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| Latest published | 2026-07-22 | 2026-06-12 | 2026-07-22 |
| Oldest published | 2026-03-28 | 2024-05-14 | 2026-03-28 |
| Stale rows/ratio | 1/24, 4.2% | 9/23, 39.1% | 1/24, 4.2% |
| SLA status | PASS | FAIL | PASS |

## 9. Corruption scenarios và repair

Các thao tác áp dụng trên bản sao clean dataframe trong một lượt; số dòng mỗi scenario có thể chồng lấn và không cộng thành tổng record khác nhau.

| Corruption | Cách tạo và số bị tác động | Signal quan sát được | Repair |
| --- | --- | --- | --- |
| `drop_latest_records` | Xóa 20% record mới nhất: 5/24 | Latest published lùi về 2026-06-12; 4 ground-truth IDs bị xóa tương ứng 4 retrieval misses | Dựng lại từ raw |
| `blank_summary` | Đặt rỗng 2 summary | GX summary length FAIL; duplicate tạo 4 dòng vi phạm | Dựng lại summary |
| `inject_noise` | Tiền tố noise cho 3 summary | Có trong log và embedding text; GX không có check riêng | Dựng lại text |
| `truncate_title` | Cắt 3 title còn 7 ký tự | Có trong log; GX chỉ kiểm tra non-null | Dựng lại title |
| `stale_date` | Lùi ngày xuất bản của 7 record thêm 730 ngày, tăng `age_days` | Stale ratio 39.1%, SLA FAIL cùng tác động xóa record mới | Dựng lại ngày/age |
| `duplicate_rows` | Thêm 4 bản sao của 4 dòng đầu | 23 dòng, 19 `paper_id` duy nhất; GX uniqueness FAIL | Cleaning raw và index mới |

`data/results/corruption_log.json` có `input_rows=24`, `output_rows=23`, `unique_output_papers=19`; mỗi scenario ghi count, ID và thay đổi trước/sau hoặc vị trí duplicate. Code tính lại `summary_chars` và `text_for_embedding` trước khi index, nên lỗi nội dung vào retrieval corpus. Repair đọc `data/raw/crossref_records.json` (fallback về response snapshot), chạy lại cleaning, quality, index và evaluation; không vá corrupted dataframe. Unit test so sánh DataFrame rebuilt với clean data khi dùng cùng raw snapshot và mốc thời gian. `age_days` có thể khác nếu chạy vào ngày khác.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Phục hồi |
| --- | ---: | ---: | ---: | ---: | ---: |
| Records / unique IDs | 24 / 24 | 23 / 19 | 24 / 24 | −1 dòng, −5 ID duy nhất | Về baseline |
| `retrieval_hit_rate` | 1.000 | 0.600 | 1.000 | −0.400 | +0.400 |
| `mean_token_f1` | 1.000 | 0.579 | 1.000 | −0.421 | +0.421 |
| `judge_accuracy` | 1.000 | 0.600 | 1.000 | −0.400 | +0.400 |
| `mean_judge_score` | 5.000 | 3.200 | 5.000 | −1.800 | +1.800 |
| GX checks | 7/7 PASS | 5/7 FAIL | 7/7 PASS | −2 checks | +2 checks |
| Freshness | PASS; 4.2% stale | FAIL; 39.1% stale | PASS; 4.2% stale | +34.9 điểm % stale | Về baseline |

Nguồn: `data/results/{baseline,corrupted,repaired}_metrics.json`, `data/quality/{baseline,corrupted,repaired}_quality_report.json`, `data/reports/corruption_report.md`. JSON metrics và 6/10 verdict `correct=true` trong `corrupted_answers.json` xác nhận corrupted `judge_accuracy` là **60%**.

1. Xóa 5 record mới làm mất ground-truth DOI của `test-02`, `test-04`, `test-07`, `test-08`; đúng bốn câu này không còn retrieval hit. Cùng lượt, blank summary và duplicate làm GX còn 5/7, còn lùi ngày kết hợp xóa record mới đẩy stale ratio lên 39.1%. Bộ corruption kết hợp đi cùng mức giảm hit rate 100% → 60% và F1 1.000 → 0.579; chưa có ablation để gán riêng mức giảm answer metric cho từng lỗi.
2. Rebuild từ raw snapshot phục hồi 24 DOI duy nhất, GX 7/7 và freshness 1/24 stale. Trên cùng test set, hit rate và token F1 trở lại 1.000. `test-04` cho thấy retrieval miss vẫn có F1 1.000; ID hit và answer overlap cần được đọc riêng.

Judge baseline được chấm bằng LLM còn corrupted/repaired bằng heuristic fallback. Vì vậy không dùng delta judge như bằng chứng thuần về tác động dữ liệu cho đến khi chạy lại cả ba trạng thái với cùng evaluator.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Manifest Chroma trước commit repair lưu `persist_path` tuyệt đối theo máy tạo index, khiến load index từ checkout ở thư mục khác không portable.
- **Nguyên nhân:** `LocalEmbeddingIndex.build()` trước đó ghi `str(persist_path)` trực tiếp; consumer đọc lại đúng chuỗi này.
- **Cách xử lý:** Commit `e773859` đổi manifest sang đường dẫn tương đối `data/chroma`; `LocalEmbeddingIndex.load()` nối với project root nếu path tương đối và vẫn hỗ trợ manifest tuyệt đối cũ.
- **Cách xác minh:** `tests/test_index_manifest.py` kiểm hai dạng path; 9 unit tests hiện tại `OK`. Manifest đã commit ghi `persist_path: data/chroma`.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| GX chỉ yêu cầu row count ≥ 1, non-null title và summary dài ≥ 50 | Không cảnh báo trực tiếp mất 5 record, noise hay title ngắn | Thêm kiểm tra coverage so với raw, title length/noise và summary rỗng; chạy từng corruption riêng để đo phát hiện đúng/sai |
| 10 câu sinh từ metadata và có exact title | Dễ đạt baseline 100%; chưa đo truy vấn đa dạng | Bổ sung paraphrase/hard negatives và tập giữ riêng; so sánh theo nhóm câu |
| Judge đổi từ LLM ở baseline sang fallback ở hai trạng thái sau | Accuracy/score chưa hoàn toàn đồng nhất | Ghi provider, model, evaluator mode và run ID; rerun cả ba trạng thái cùng evaluator |
| Thiếu timestamp tải snapshot, run timestamp repair và mốc cố định tính `age_days` | Khó tái hiện chính xác freshness sau nhiều ngày | Lưu run manifest gồm raw hash, test-set hash, UTC timestamp và mốc tính age |
| Ragas không chạy | Chưa có faithfulness/context metrics | Bật lượt Ragas có kiểm soát và lưu cùng run ID khi đủ tài nguyên |

Dashboard `app/observability_dashboard.py` chỉ đọc và trực quan hóa artifact đã có; không tạo metric mới hay thay quality gate.

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository đối chiếu báo cáo cá nhân, remote và commit.
- [x] Phân công khớp ownership trong báo cáo cá nhân và commit triển khai.
- [ ] Hai lệnh pipeline toàn phần được chạy lại trên đúng phiên bản báo cáo này; hiện mới đối chiếu artifact đã commit và 9 unit tests.
- [x] Corrupted và repaired dùng lại `data/eval/test_set.json` của baseline.
- [x] Bảng metrics khớp JSON trong `data/results/`, kể cả correction `judge_accuracy=0.6`.
- [x] Quality/freshness conclusions khớp JSON trong `data/quality/`.
- [x] Các đường dẫn artifact được nêu có trong repository.
- [x] Có đủ ba báo cáo thành viên.
- [ ] Cần rà soát secret trên toàn bộ nội dung nộp cuối cùng; báo cáo này không chép `.env` hoặc API key.
