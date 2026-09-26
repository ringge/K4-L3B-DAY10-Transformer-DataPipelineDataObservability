# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Trần Kim Phương |
| MSSV | 2A202602565 |
| Khóa/Lớp | K4 |
| Tên nhóm | Transformer |
| Vai trò chính | Trưởng nhóm, tích hợp pipeline; trực tiếp triển khai Crossref ingestion, corruption và repair |
| Repository | https://github.com/ringge/K4-L3B-DAY10-Transformer-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

**Phạm vi bằng chứng:** Các phần việc trực tiếp dưới đây được đối chiếu với các commit `f23df5f`, `7c41db2`, `e773859` của tài khoản `ringge`.

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Thu thập và chuẩn hóa Crossref | `src/ingestion/crossref.py`: `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` | Crossref `/works` hoặc snapshot `data/raw/crossref_response.json` | `PaperRecord`, `data/raw/crossref_records.json` | Hoàn thành |
| Bộ sáu kịch bản corruption | `src/ingestion/corruption.py`: `corrupt_clean_dataframe` | DataFrame sạch từ `data/clean/papers_clean.json` | Dataset corrupted, `data/results/corruption_log.json` | Hoàn thành |
| Điều phối corruption → repair → so sánh | `src/pipelines/corruption_flow.py`: `main` | Clean dataset, raw snapshot, baseline metrics, test set | Corrupted/repaired datasets, embeddings, quality reports, answers/metrics | Hoàn thành |
| Báo cáo đối chiếu ba trạng thái | `src/observability/reporting.py`: `generate_corruption_report` | Metrics, quality/freshness, corruption log và answers | `data/reports/corruption_report.md` | Hoàn thành |

Output Crossref là đầu vào của cleaning. Dataset corrupted và repaired được quality, retrieval và evaluation sử dụng.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả và bằng chứng |
| --- | --- | --- |
| Bổ sung kiểm thử cho các phần đã chỉnh | Crossref, corruption/repair | `tests/test_crossref.py`, `tests/test_corruption.py`; các kiểm thử này đạt trong lần chạy bộ test hiện tại. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Parse Crossref và hỗ trợ retry/fallback | `src/ingestion/crossref.py`, `tests/test_crossref.py` | Record có DOI, title, abstract, author, subject và ngày; bỏ record thiếu trường thiết yếu | Test Crossref; `data/raw/crossref_records.json` |
| Tạo sáu lỗi dữ liệu có audit log | `src/ingestion/corruption.py`, `data/results/corruption_log.json` | Xóa 5 record mới, blank summary 2, inject noise 3, truncate title 3, làm cũ ngày 7, thêm 4 dòng duplicate; output 23 dòng/19 paper IDs duy nhất | `tests/test_corruption.py`; corruption log |
| Phục hồi từ raw snapshot và so sánh | `src/pipelines/corruption_flow.py`, `src/observability/reporting.py` | Dataset repaired 24 dòng, quality gate PASS, report ba trạng thái theo metric và câu hỏi | `data/reports/corruption_report.md`; JSON trong `data/results/` và `data/quality/` |

Output tiêu biểu là `data/reports/corruption_report.md`: trên cùng 10 câu hỏi, retrieval hit rate **100% → 60% → 100%**, quality gate **PASS → FAIL → PASS**, mean token F1 **1.000 → 0.579 → 1.000**. Báo cáo lấy số từ các JSON đã lưu.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline RAG có thể chạy không lỗi nhưng chất lượng câu trả lời giảm khi record bị mất, rỗng, trùng hoặc sai ngày. Tôi cần tạo lỗi có thể tái hiện, đo ảnh hưởng trên đúng bộ câu hỏi baseline và khôi phục từ nguồn sạch có thể truy vết. Ở bước ingestion, Crossref cũng có thể trả metadata thiếu, HTML trong abstract hoặc lỗi mạng.

### Cách triển khai

`parse_crossref_payload` kiểm tra `message.items`, chuẩn hóa HTML/whitespace, xử lý các biến thể ngày của Crossref và bỏ item thiếu DOI, title, abstract hoặc ngày xuất bản. `fetch_source_records` dùng snapshot sẵn có theo mặc định; khi refresh, request có timeout, thử lại tối đa ba lần với HTTP 429/5xx hoặc lỗi mạng, rồi fallback về snapshot nếu thất bại.

`corrupt_clean_dataframe` sao chép DataFrame sạch để không sửa baseline. Hàm xóa 20% record có `published` mới nhất, rồi sắp xếp theo `paper_id` và tác động lên các dải vị trí cố định: blank summary, thêm noise, cắt title, lùi ngày 730 ngày và tăng `age_days`, sau đó thêm bốn dòng duplicate. Hàm tính lại `summary_chars` và `text_for_embedding`, để index thực sự nhận dữ liệu đã bị sửa. Log lưu số dòng, ID và giá trị trước/sau.

`corruption_flow.py` xây index và đánh giá riêng cho corrupted. Bước repair đọc `data/raw/crossref_records.json` (hoặc response snapshot nếu file records không có), chạy lại cleaning, tạo index repaired riêng, chạy quality/freshness và evaluation trên cùng `data/eval/test_set.json`, rồi xuất bảng ba trạng thái. Với cùng raw snapshot và cùng thời điểm tính `age_days`, rebuild trả lại cùng dữ liệu sạch; kiểm thử so sánh hai DataFrame bằng `assert_frame_equal`. Nếu chạy sang ngày khác, `age_days` có thể đổi, nên tính idempotent ở đây áp dụng cho cùng đầu vào và mốc thời gian.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref `message.items`; clean DataFrame cần `paper_id`, `title`, `summary`, `published`, `age_days`, `authors_joined`, `categories_joined`, `summary_chars`, `text_for_embedding`; raw snapshot và test set. |
| Output | `PaperRecord`/raw records; corrupted DataFrame và log; repaired DataFrame; manifests, quality/freshness JSON, answers/metrics và comparison Markdown. |
| Module phụ thuộc | `core.config`, `core.utils`, `ingestion.cleaning`, `retrieval.index`, `observability.quality`, `evaluation.metrics`. |
| Module sử dụng output | Cleaning nhận raw records; index nhận DataFrame; quality/evaluation nhận dữ liệu và index; reporting nhận metrics và log. |
| Điều kiện lỗi cần xử lý | Payload Crossref sai schema; API rate limit/offline; thiếu snapshot; clean DataFrame thiếu cột, ID trùng hoặc ngày không hợp lệ; raw snapshot không tạo được record để repair. |

### Cách xác minh

Lệnh kiểm thử đã chạy trong repository hiện tại:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

- **Kết quả mong đợi:** Crossref parse/retry/fallback, sáu corruption, rebuild từ raw snapshot và report ba trạng thái đều đạt.
- **Kết quả thực tế:** 9 tests, `OK` (2026-09-26). Kết quả chạy pipeline toàn phần được đối chiếu qua artifact đã commit; tôi không chạy lại pipeline có gọi API/LLM trong lần viết báo cáo này.
- **Artifact/log:** `data/results/corruption_log.json`, `data/results/{baseline,corrupted,repaired}_metrics.json`, `data/quality/{baseline,corrupted,repaired}_quality_report.json`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần phục hồi sau corruption mà không giữ các trường đã bị sửa, đồng thời đo được ảnh hưởng đến RAG.
- **Các phương án đã cân nhắc:** (1) Sửa trực tiếp dataset corrupted theo log; (2) dựng lại từ raw snapshot Crossref bằng cùng hàm cleaning, rồi tạo index repaired riêng.
- **Phương án đã chọn:** Dựng lại từ raw snapshot; chạy lại quality/freshness và evaluation trên cùng test set.
- **Lý do:** Sửa từng trường dễ bỏ sót noise, duplicate, `age_days` hoặc `text_for_embedding`. Raw snapshot là mốc nguồn có thể truy vết; index riêng tránh lẫn các trạng thái. Đổi lại, phải chạy lại embedding và evaluation.
- **Bằng chứng:** `tests/test_corruption.py` xác nhận rebuild trả cùng DataFrame sạch với cùng ngày chạy. Artifact repaired có 24 records, 7/7 GX checks PASS, freshness PASS và retrieval hit rate 100%.

## 6. Một giới hạn observability chưa xử lý xong

- **Triệu chứng:** `data/results/corruption_log.json` ghi nhận 3 summary bị chèn noise và 3 title bị cắt ngắn. Tuy nhiên, trong `data/quality/corrupted_quality_report.json`, hai GX checks thất bại chỉ liên quan đến ID trùng và độ dài summary; chưa có tín hiệu riêng cho noise hoặc title bị cắt. Quality gate tổng thể vẫn FAIL vì các lỗi khác, nên không thể dùng kết quả FAIL đó để khẳng định hai lỗi này đã được phát hiện.
- **Bước tái hiện:** Đối chiếu sáu kịch bản trong corruption log với danh sách `expectations` và các check thất bại của corrupted quality report; xem các quy tắc hiện tại trong `src/observability/quality.py`.
- **Nguyên nhân gốc:** Bộ GX checks hiện có kiểm tra title không null và summary dài ít nhất 50 ký tự, nhưng không kiểm tra độ dài tối thiểu của title hoặc dấu hiệu noise trong summary. Corruption vẫn giữ các trường này là chuỗi hợp lệ theo những quy tắc đó.
- **Cách xử lý đã thực hiện:** Tôi ghi rõ từng thay đổi trong corruption log và rebuild dataset repaired từ raw snapshot; các artifact này cho phép truy vết và phục hồi dữ liệu. Chúng chưa bổ sung khả năng phát hiện riêng hai lỗi trên vào quality gate.
- **Phạm vi bị ảnh hưởng:** Khả năng phát hiện và giải thích lỗi của quality gate khi title bị cắt hoặc summary có noise; chưa có số đo riêng về tác động của từng kịch bản đến RAG.
- **Những gì đã loại trừ:** Đây không phải do corruption không được áp dụng: `tests/test_corruption.py` kiểm tra title ngắn, noise và việc cập nhật `text_for_embedding`; corruption log cũng ghi các record đã đổi.
- **Bước tiếp theo:** Thêm check phù hợp cho title quá ngắn và noise, chạy từng kịch bản riêng trên cùng test set, rồi đối chiếu số lỗi được phát hiện với thay đổi retrieval/answer metrics. Chưa ghi nhận bước này là đã hoàn thành.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref → vector index:** `fetch_source_records` đọc API/snapshot và ghi raw records; `build_clean_dataframe` chuẩn hóa, loại ID trùng, tính `age_days`, `summary_chars` và `text_for_embedding`. `LocalEmbeddingIndex.build` nhúng text bằng MiniLM rồi ghi vào collection ChromaDB; manifest trong `data/embeddings/` giữ metadata để load lại.
2. **Evaluation set và ground truth:** Mười câu hỏi trong `data/eval/test_set.json` có `ground_truth` và `ground_truth_doc_ids`. Retrieval hit được tính khi kết quả tìm kiếm chứa ít nhất một ID đúng; câu trả lời được so bằng token F1 và LLM judge. Hai phép đo giúp phân biệt lỗi tìm tài liệu với lỗi tạo câu trả lời.
3. **Quality và freshness:** GX checks kiểm tra row count, ID duy nhất, trường không null và độ dài summary. Freshness dùng `age_days` với ngưỡng 180 ngày; SLA pass nếu tỷ lệ record cũ không quá 25%. Freshness cũng tham gia vào `success` chung của quality report.
4. **Cùng test set:** Baseline, corrupted và repaired đều dùng đúng `data/eval/test_set.json`, nên metrics có thể đối chiếu theo cùng câu hỏi và ground-truth IDs. Đổi câu hỏi sẽ làm thay đổi phép đo.
5. **Đánh giá repair:** Kiểm tra repaired clean JSON/CSV và manifest, quality/freshness reports, metrics/answers và comparison report. Artifact hiện tại cho thấy 24 record, 7/7 GX checks và các agent metrics trở về baseline trên 10 câu hỏi; kết quả này chưa đại diện cho mọi câu hỏi ngoài bộ đo.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 100% | 60% | 100% | Bốn câu hỏi mất ground-truth document khỏi kết quả retrieval. |
| `mean_token_f1` | 1.000 | 0.579 | 1.000 | Corruption làm giảm chất lượng trả lời trên bộ test. |
| `judge_accuracy` | 100% | 50% | 100% | Năm trên mười câu bị judge đánh giá sai ở trạng thái corrupted. |
| `mean_judge_score` | 5.000/5 | 3.200/5 | 5.000/5 | Repaired trở về mức baseline trên bộ test. |
| Quality checks | PASS, 7/7 GX | FAIL, 5/7 GX | PASS, 7/7 GX | Corrupted fail ở ID duy nhất và độ dài summary; freshness cũng fail. |
| Freshness status | PASS, 1/24 cũ (4.2%) | FAIL, 9/23 cũ (39.1%) | PASS, 1/24 cũ (4.2%) | Corruption xóa record mới và lùi ngày 7 record. |

Nguồn số: `data/results/{baseline,corrupted,repaired}_metrics.json`, `data/quality/{baseline,corrupted,repaired}_quality_report.json` và `data/reports/corruption_report.md`.

### Kết luận từ số liệu

1. **Corruption → signal → agent:** Xóa 5 record mới và làm cũ ngày 7 record khiến freshness từ 4.2% stale lên 39.1% stale; duplicate và blank summary làm GX còn 5/7 checks PASS. Retrieval hit rate giảm từ 100% xuống 60%; mean token F1 từ 1.000 xuống 0.579. Đây là tác động của *bộ corruption kết hợp*, chưa thể quy mọi thay đổi agent metric cho riêng một thao tác.
2. **Repair → signal → agent:** Rebuild từ raw snapshot khôi phục 24 record, loại duplicate/summary rỗng, đưa freshness về 1/24 stale và GX về 7/7 PASS. Trên cùng 10 câu hỏi, retrieval hit rate và mean token F1 trở lại 100% và 1.000.

**Corruption ảnh hưởng rõ nhất:** Với retrieval, `drop_latest_records` có bằng chứng trực tiếp nhất: cả bốn câu mất retrieval hit (`test-02`, `test-04`, `test-07`, `test-08`) đều có ground-truth ID nằm trong năm record đã xóa. Tôi đối chiếu `data/results/corruption_log.json` với `data/results/corrupted_answers.json`. Các lỗi được tiêm cùng lúc, nên chưa có ablation để định lượng ảnh hưởng độc lập của noise, truncate, stale date hay duplicate lên answer quality.

**Kết quả khác kỳ vọng đơn giản ban đầu:** Mất retrieval hit không đồng nghĩa token F1 bằng 0. `test-04` không hit nhưng F1 vẫn 1.000; `test-02` không hit nhưng F1 khoảng 0.788. Tôi kiểm tra các dòng tương ứng trong comparison report và answers JSON. Retrieval hit theo ID và trùng khớp từ trong câu trả lời là hai tín hiệu khác nhau. GX cũng không fail ở việc xóa record mới vì row count check chỉ yêu cầu ít nhất một dòng; freshness mới phát hiện thay đổi về độ mới. Noise và title bị cắt chưa có check chuyên biệt.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Giữ raw snapshot và clean dataset tách biệt giúp rebuild có thể truy vết; `age_days` cần gắn với mốc chạy nếu muốn so sánh lặp lại chính xác.
2. Quality gate cần nhiều tín hiệu: kiểm tra không null chưa phát hiện chuỗi rỗng; row count tối thiểu chưa phát hiện mất một nhóm record; freshness phát hiện thay đổi mà GX hiện tại bỏ sót.
3. RAG phải đo cả retrieval và answer. Một câu có thể trả lời gần đúng dù không truy xuất đúng ground-truth ID; report theo từng câu cho thấy khác biệt này.

### Nếu có thêm thời gian

Tôi sẽ chạy từng corruption riêng trên cùng test set và lưu delta theo kịch bản, để phân biệt tác động của việc xóa record với noise, duplicate và stale date. Tôi cũng sẽ thêm check tỷ lệ mất record so với raw snapshot, summary rỗng, title quá ngắn và dấu hiệu noise; đo hiệu quả bằng số lỗi phát hiện đúng, báo động sai và thay đổi retrieval/answer metrics của từng kịch bản.

## 10. Cam kết của thành viên

Các mục kỹ thuật đã được đối chiếu khi viết báo cáo. Các mục thể hiện cam kết hoặc khả năng trình bày cá nhân cần Trần Kim Phương tự xác nhận trước khi nộp.

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Kim Phương

**Ngày xác nhận:** Sep 26 2026
