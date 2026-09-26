# Member Role Report — Day 10: Data Pipeline & Data Observability

> Báo cáo cá nhân về phần triển khai Phase 1 và báo cáo baseline. Các số liệu Phase 2 bên dưới chỉ được trích dẫn làm kết quả đối chiếu của nhóm, không phải phần việc do cá nhân sở hữu.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Minh Thái             |
| MSSV               | 2A202602726                     |
| Khóa/Lớp         | K4              |
| Tên nhóm         | Transformer     |
| Vai trò chính    | Thành viên, phụ trách Phase 1 và baseline report |
| Repository         | https://github.com/ringge/K4-L3B-DAY10-Transformer-DataPipelineDataObservability|
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Điều phối baseline pipeline end-to-end | `src/pipelines/phase1.py::main` | Settings, Crossref records/snapshot | Clean CSV/JSON, Chroma baseline index, evaluation artifacts, quality/freshness results | Hoàn thành |
| Sinh báo cáo Phase 1 | `src/observability/reporting.py::generate_phase1_report` | Source summary, baseline metrics, quality và freshness payloads | `data/reports/phase1_report.md` | Hoàn thành |

Phạm vi ownership không bao gồm corruption injection, repair pipeline hoặc corruption comparison report.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| | ||

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Nối ingestion, cleaning, lưu clean data, indexing, evaluation và observability | `src/pipelines/phase1.py` | 24 records loaded và 24 records cleaned; test set 10 câu; baseline metrics được ghi ra file | Chạy `python script/run_phase1.py`; đối chiếu clean data, metrics và report artifacts |
| Tổng hợp kết quả baseline thành Markdown | `src/observability/reporting.py::generate_phase1_report` | Source summary, metrics, quality gate và freshness summary | `data/reports/phase1_report.md` có evaluation, 7/7 GX checks và freshness status | Đối chiếu nội dung report với JSON metrics/quality artifacts |

Output cụ thể được xác minh:

`data/reports/phase1_report.md` ghi 24 records loaded/cleaned, 10 evaluation samples, retrieval hit rate 100%, mean token F1 1.000, judge accuracy 100%, quality gate PASS (7/7 GX expectations) và freshness SLA PASS. Các giá trị khớp với `data/results/baseline_metrics.json` và `data/quality/baseline_quality_report.json`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trước khi có orchestration Phase 1, các module ingestion, cleaning, indexing, evaluation và observability chưa được chạy thành một quy trình thống nhất. Phần việc này kết nối chúng để tạo baseline có thể kiểm tra bằng metrics và báo cáo, thay vì chỉ có các hàm rời rạc.

### Cách triển khai

`main()` nạp Settings và thời điểm UTC, lấy records qua `fetch_source_records()` (ưu tiên snapshot local nếu không bật refresh), tạo dataframe chuẩn hóa, rồi ghi CSV/JSON. Dataframe được đưa vào Chroma baseline collection; test set được sinh theo thứ tự `paper_id` ổn định; evaluator chạy trên test set và ghi metrics/answers. Cuối cùng, quality gate chạy GX cùng freshness SLA, rồi report generator tổng hợp source, metrics và trạng thái chất lượng thành Markdown. Pipeline in các metric chính và đường dẫn report sau khi hoàn tất.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Settings; raw Crossref response/records; thời điểm chạy UTC |
| Output                         | Clean CSV/JSON; Chroma baseline collection; test set; baseline metrics/answers; quality/freshness JSON; Phase 1 Markdown report |
| Module phụ thuộc             | `ingestion.crossref`, `ingestion.cleaning`, `retrieval.index`, `evaluation.testset`, `evaluation.metrics`, `observability.quality`, `observability.reporting` |
| Module sử dụng output        | Các bước tiếp theo của Phase 1; corruption/repair flow dùng baseline clean data, evaluation set và metrics |
| Điều kiện lỗi cần xử lý | Snapshot không có usable records; clean dataframe rỗng/không đủ 10 records cho test set; thiếu dependencies hoặc lỗi GX/embedding/provider |

### Cách xác minh

```bash
python -m pip install -e .
python script/run_phase1.py
```

- **Kết quả mong đợi:** Sinh clean artifacts, index, test set, baseline metrics và report Phase 1.
- **Kết quả thực tế:** Report ghi 24/24 records được clean; có 10 samples; retrieval hit rate 1.0; mean token F1 1.0; judge accuracy 1.0; quality gate PASS với 7/7 expectations; freshness SLA PASS. Ragas được bỏ qua theo cấu hình mặc định.
- **Artifact/log:** `data/reports/phase1_report.md`, `data/results/baseline_metrics.json`, `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Pipeline cần lấy raw records nhưng vẫn chạy lặp lại được khi có snapshot local.
- **Các phương án đã cân nhắc:** Luôn gọi Crossref API mỗi lần chạy; hoặc mặc định dùng snapshot đã lưu và chỉ fetch khi bật `REFRESH_SOURCE`.
- **Phương án đã chọn:** Tái sử dụng `fetch_source_records()` với snapshot local mặc định.
- **Lý do:** Giảm phụ thuộc mạng/API và giúp dữ liệu đầu vào của lần benchmark có thể tái lập; vẫn có lựa chọn refresh rõ ràng khi cần cập nhật nguồn.
- **Bằng chứng quyết định phù hợp:** Lần chạy baseline tạo được 24 records và report ghi rõ source/query/filter cùng thời gian chạy; artifacts đầu ra được lưu để đối chiếu.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'pipelines'`; sau khi cấu hình source path, interpreter còn báo thiếu `dotenv`.
- **Lệnh hoặc bước tái hiện:** Chạy entrypoint bằng interpreter chưa cài project/dependencies.
- **Nguyên nhân gốc:** Project dùng `src` package layout và môi trường Python ban đầu chưa có các dependency khai báo.
- **Cách xử lý:** Cài project cùng dependencies ở editable mode bằng `python -m pip install -e .`, rồi chạy entrypoint trong môi trường đã cài.
- **Cách xác minh sau khi sửa:** `data/reports/phase1_report.md` và baseline JSON artifacts được tạo; report ghi 24 records và đủ các metrics/quality signals kỳ vọng.
- **Điều học được:** Khi import lỗi ở source-layout project, cần xác minh interpreter và editable installation trước khi kết luận lỗi nằm trong business logic.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

1. `fetch_source_records()` đọc snapshot Crossref local theo mặc định (hoặc fetch khi cấu hình refresh), parser chuyển dữ liệu sang records; cleaning chuẩn hóa field, bỏ record thiếu ID/title/summary/ngày hợp lệ, khử trùng lặp và tạo `text_for_embedding`. Phase 1 lưu clean CSV/JSON, sau đó `LocalEmbeddingIndex.build()` embed nội dung và nạp documents/metadata vào Chroma collection `papers-baseline`.
2. Test set tạo câu hỏi có ground truth và `ground_truth_doc_ids`. Retrieval hit được tính khi ID ground truth nằm trong danh sách ID truy xuất; answer quality được đo bằng token F1 và judge verdict. Baseline có 10 câu test.
3. GX checks kiểm tra cấu trúc/chất lượng như row count, null, uniqueness và độ dài summary. Freshness monitoring dùng `published`/`age_days` để đo tuổi dữ liệu và áp SLA: tỷ lệ record cũ hơn ngưỡng 180 ngày không vượt 25%.
4. Dùng cùng test set giữ câu hỏi, ground truth và số mẫu cố định, vì thế chênh lệch metric có thể quy về trạng thái corpus/index thay vì thay đổi bộ đánh giá.
5. Trong quy trình nhóm, cần xác nhận clean artifacts được dựng lại từ raw snapshot, quality/freshness gate trở về trạng thái đạt và metrics trên cùng test set phục hồi gần baseline. Tôi không sở hữu phần triển khai repair Phase 2.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.000 | 0.600 | 1.000 | Baseline và repaired đạt toàn bộ hit; corrupted giảm 40 điểm phần trăm. Hai cột Phase 2 là số liệu artifact nhóm, không thuộc ownership cá nhân. |
| `mean_token_f1`      | 1.000 | 0.579 | 1.000 | Answer overlap giảm rõ ở trạng thái corrupted và trở lại baseline sau repair. |
| `judge_accuracy`     | 1.000 | 0.500 | 1.000 | Judge đúng 10/10 baseline, 5/10 corrupted, 10/10 repaired theo metrics đã lưu. |
| `mean_judge_score`   | 5.000 | 3.200 | 5.000 | Điểm trung bình giảm 1.8 điểm khi corpus corrupted. |
| Quality checks         | PASS (7/7) | FAIL (5/7) | PASS (7/7) | Lấy từ baseline/corruption/repaired quality artifacts của nhóm. |
| Freshness status       | PASS (4.2%) | FAIL (39.1%) | PASS (4.2%) | Corrupted vượt ngưỡng stale ratio 25%; repaired quay về baseline. |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. Corruption đồng thời xóa record mới, làm rỗng summary, tạo noise/truncate title, làm lùi ngày và tạo duplicate → quality giảm còn 5/7, stale ratio tăng từ 4.2% lên 39.1% và freshness FAIL → retrieval hit giảm 100% xuống 60%, mean token F1 từ 1.000 xuống 0.579.
2. Repair từ raw snapshot rồi clean/rebuild index → quality trở về 7/7, freshness PASS với stale ratio 4.2% → retrieval hit/F1/judge accuracy và mean judge score trở về các giá trị baseline trong artifacts nhóm.

Corruption nào ảnh hưởng rõ nhất và vì sao?

Trong bộ test này, stale-date làm hai câu hỏi date (`test-07`, `test-08`) mất retrieval hit; blank-summary làm F1 bằng 0 ở các câu summary bị ảnh hưởng dù retrieval hit vẫn đúng. Không thể tách chính xác phần đóng góp của từng lỗi vào tổng mức giảm vì nhiều corruption được tiêm cùng lúc. Các con số trên lấy từ corruption report/log của nhóm.

Kết quả nào khác với kỳ vọng ban đầu?

Baseline đạt 100% trên cả ba metric chính với chỉ 10 câu hỏi. Đây là kết quả của tập benchmark nhỏ, có câu hỏi được sinh trực tiếp từ metadata và câu hỏi chứa tiêu đề chính xác; không nên diễn giải thành chất lượng tổng quát trên truy vấn người dùng bất kỳ. Ragas không chạy (`RUN_RAGAS` không bật), nên không có các metric Ragas trong kết quả.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Pipeline end-to-end cần lưu artifacts trung gian có cấu trúc để mỗi bước có thể kiểm tra và tái sử dụng.
2. Quality gate và freshness đo các rủi ro khác nhau: dữ liệu có thể đủ schema nhưng đã cũ, nên cần cả hai tín hiệu.
3. Metadata và summary bị lỗi có thể làm retrieval/answer metrics suy giảm dù index vẫn trả về kết quả; cần đo trên test set ổn định.

### Nếu có thêm thời gian

Mở rộng evaluation set bằng các câu hỏi không chứa nguyên văn tiêu đề, tăng số câu và bổ sung holdout cố định để giảm phụ thuộc vào exact-title lookup. So sánh hit rate và token F1 trên cùng holdout, đồng thời bật Ragas riêng khi môi trường/API đã sẵn sàng.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Minh Thái
**Ngày xác nhận:** 2026-09-26
