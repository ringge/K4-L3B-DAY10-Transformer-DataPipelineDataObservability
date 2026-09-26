# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Trần Gia Thành |
| MSSV | 2A202602626 |
| Khóa/Lớp | K4 |
| Tên nhóm | Transformer |
| Vai trò chính | Teammate — phụ trách cleaning, data quality/freshness và benchmark baseline |
| Repository | https://github.com/ringge/K4-L3B-DAY10-Transformer-DataPipelineDataObservability |
| Ngày hoàn thành | 26/09/2026 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

Tôi trực tiếp hoàn thiện luồng biến raw Crossref records thành dataframe sẵn sàng embedding, kiểm soát data quality/freshness, và tạo bộ benchmark xác định cho baseline retrieval. **B1 — Interactive Observability Dashboard / Drift Monitor** là phần bổ trợ, dùng để trực quan hóa các artifact mà luồng dữ liệu và pipeline chung tạo ra. Lịch sử Git xác nhận các commit `71773ac`, `8582bf4` và `eb03bbf` đều do `GTee2004 tạo ngày 26/09/2026.

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Làm sạch dữ liệu sẵn sàng embedding | `src/ingestion/cleaning.py`: `build_clean_dataframe` | Raw Crossref records và `run_date` | Dataframe sạch có `text_for_embedding`, `age_days`, metadata chuẩn hóa và `paper_id` duy nhất | Hoàn thành |
| Quality gate và Freshness SLA | `src/observability/quality.py`: `run_data_quality_checks`, `build_freshness_report` | Clean dataframe và config freshness | Great Expectations report, freshness report, trạng thái quality/freshness | Hoàn thành |
| Benchmark test set và baseline vector index | `src/evaluation/testset.py`: `build_test_set`; tích hợp `src/retrieval/index.py` | Clean dataframe 24 dòng | `data/eval/test_set.json` gồm 10 câu và collection `papers-baseline` có 24 documents | Hoàn thành |

Dashboard là tầng đọc artifact, không gọi Crossref, không thay đổi raw source và không tự tạo metric mẫu. Với phần baseline index, tôi hoàn thiện logic benchmark và dùng `LocalEmbeddingIndex.build` sẵn có để xây index, không viết lại embedding/indexing logic.

### Việc bổ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả và bằng chứng |
| --- | --- | --- |
| Dashboard Streamlit cho live demo | `app/observability_dashboard.py` | Commit `eb03bbf`; trực quan hóa các quality, freshness và evaluation artifact đã có, không tạo hay sửa dữ liệu nguồn. |
| Cập nhật thông tin nhóm | `docs/TEAM.md` | Commit `9d30dce` do `GTee2004` tạo. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Chuẩn hóa dữ liệu và quality/freshness | `build_clean_dataframe`, `run_data_quality_checks`, `build_freshness_report` | 24 clean records, cột `text_for_embedding`, baseline quality PASS 7/7 và freshness PASS | `data/clean/papers_clean.json`, `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json` |
| Sinh benchmark xác định và index baseline | `build_test_set`; `LocalEmbeddingIndex.build` | 10 câu với 3 summary, 3 authors, 2 date, 2 categories; Chroma collection `papers-baseline` có 24 documents | `data/eval/test_set.json`, `data/embeddings/papers_embeddings.json`, `data/chroma/` |
| B1 hỗ trợ: nạp artifact và hiển thị KPI | `_artifact_paths`, `_load_snapshot`, `_show_state_kpis`, `_comparison_frame` | Đọc artifact ba trạng thái, cảnh báo khi thiếu/sai định dạng và hiển thị KPI so sánh | Mở dashboard hoặc đối chiếu JSON trong `data/results/`, `data/quality/` |
| B1 hỗ trợ: theo dõi age drift và alert | `_age_distribution`, `_show_age_chart`, `_show_alerts` | Histogram ba trạng thái, đường ngưỡng 180 ngày và alert quality/freshness | Cột `age_days` và freshness reports thực tế |

Dashboard chỉ trực quan hóa các output pipeline có sẵn sau đây:

- Baseline: 24 records, Quality PASS (7/7 expectations), Freshness PASS; retrieval hit rate 1.0, mean token F1 1.0, judge accuracy 1.0.
- Corrupted: 23 records, Quality FAIL (5/7), Freshness FAIL; retrieval hit rate 0.6, mean token F1 `0.579`, judge accuracy 0.6.
- Repaired: 24 records, Quality PASS (7/7), Freshness PASS; ba evaluation metric trên đều trở lại 1.0.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Dữ liệu raw cần được chuẩn hóa thành schema ổn định và được kiểm soát chất lượng trước khi đưa vào retrieval. Đồng thời cần một test set lặp lại được cùng index baseline đầy đủ. Đây là các vấn đề kỹ thuật cốt lõi tôi giải quyết. Khi các artifact của pipeline nằm ở nhiều file và ba trạng thái dữ liệu khác nhau, dashboard bổ trợ việc đọc chúng trong một giao diện có thể demo trực tiếp; nó không thay thế bước tạo dữ liệu, quality report, test set hay vector index.

### Cách triển khai

`build_clean_dataframe` làm sạch text, bỏ record thiếu trường thiết yếu, de-duplicate theo `paper_id`, tính `age_days` và ghép `text_for_embedding`. `run_data_quality_checks` chạy GX ephemeral context, kiểm tra row count, non-null, uniqueness và summary length; `build_freshness_report` tính stale ratio với ngưỡng 180 ngày. `build_test_set` sort theo `paper_id`, chọn 10 document đầu và tạo phân bổ 3/3/2/2 cho bốn question type. `LocalEmbeddingIndex.build` dùng embedding model cấu hình để replace collection và ghi manifest.

Với B1, `StateArtifactPaths` khai báo path dữ liệu, metrics, quality và freshness cho từng trạng thái. `_read_json_artifact` kiểm tra tồn tại và bắt lỗi parse JSON; `_load_snapshot` chỉ dựng dataframe khi JSON hợp lệ. Vì vậy dashboard vẫn hiển thị trạng thái còn lại và hướng dẫn chạy pipeline nếu một artifact chưa có.

Dashboard không hard-code bất kỳ metric nào: `_comparison_frame` và `_show_state_kpis` lấy giá trị từ `metrics`, `quality` và `freshness` đã nạp. Histogram chuyển `age_days` thành numeric, bỏ giá trị không parse được, sau đó tạo biểu đồ Vega-Lite. Đường tham chiếu lấy từ cấu hình 180 ngày, không chép một ngưỡng cố định trong dashboard. `_show_alerts` chỉ hiển thị error khi `quality.success is False` hoặc `freshness.is_fresh is False`.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `data/results/{baseline,corrupted,repaired}_metrics.json`; quality/freshness JSON; `data/clean/papers_clean*.json` có cột `age_days`. |
| Output | UI Streamlit: ba cột KPI, bảng so sánh, histogram age-days và Alerts. |
| Module phụ thuộc | `core.config.load_settings`, `core.utils.read_json`, Pandas, Streamlit. |
| Module sử dụng output | Người demo/giảng viên chạy `streamlit run app/observability_dashboard.py`; dashboard không là dependency ghi dữ liệu cho pipeline. |
| Điều kiện lỗi cần xử lý | Artifact thiếu, JSON không đọc được, JSON không phải object cho metrics/quality, hoặc thiếu cột `age_days`; app cảnh báo cụ thể thay vì crash. |

### Cách xác minh

```powershell
$env:PYTHONPATH = "src"
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"
python -c "from core.config import load_settings; from retrieval.index import LocalEmbeddingIndex; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); index=LocalEmbeddingIndex.build(df, s, s.paths.embeddings_json); print(f'Index hoàn thành: {index.collection_name}, documents={len(index.documents)}')"
python script/run_corruption_flow.py
streamlit run app/observability_dashboard.py
```

- **Kết quả mong đợi:** có đủ Baseline/Corrupted/Repaired, Corrupted hiện alert fail, chart có ngưỡng 180 ngày.
- **Kết quả theo artifact hiện tại:** Corrupted có `stale_rows=9`, `total_rows=23`, `stale_ratio=0.391304347826087`, `is_fresh=false`; baseline và repaired đều `1/24`, `0.041666666666666664`, `is_fresh=true`. Vì vậy hai alert của Corrupted là đúng dữ liệu.
- **Artifact/log đối chiếu:** `data/quality/corrupted_quality_report.json`, `data/quality/corrupted_freshness_report.json`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần một benchmark có thể chạy lại để so sánh retrieval giữa baseline, corrupted và repaired, nhưng không được dùng LLM/API key hoặc bịa ground truth.
- **Các phương án đã cân nhắc:** (1) tạo câu hỏi bằng LLM; (2) chọn ngẫu nhiên mỗi lần chạy; (3) tạo câu hỏi trực tiếp từ các cột dataframe, sort theo `paper_id` rồi chọn cố định 10 document.
- **Phương án đã chọn:** phương án (3), triển khai trong `build_test_set`.
- **Lý do:** cách này không phụ thuộc API/LLM, có ground truth truy vết được về chính dataframe và cho cùng test set ở các lần chạy với cùng input. Nó cũng tạo được đúng phân bổ 3 `summary`, 3 `authors`, 2 `date`, 2 `categories`.
- **Bằng chứng quyết định phù hợp:** `data/eval/test_set.json` có đúng 10 ID duy nhất, đủ bốn loại câu hỏi và mỗi item có `ground_truth_doc_ids`; evaluation metrics của ba trạng thái đều dùng `samples: 10`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `SyntaxError: f-string expression part cannot include a backslash` khi chạy quality-check one-liner có biểu thức `res[\"success\"]` trong f-string.
- **Lệnh hoặc bước tái hiện:** chạy `python -c` trong PowerShell với dấu nháy kép đã được escape bằng backslash bên trong biểu thức f-string.
- **Nguyên nhân gốc:** backslash nằm trong phần expression của f-string Python là không hợp lệ; đây là lỗi quoting của lệnh shell, không phải lỗi từ Great Expectations hay quality result.
- **Cách xử lý:** dùng `.format(res['success'])`, hoặc dùng cách quoting không đưa backslash vào f-string expression.
- **Cách xác minh sau khi sửa:** chạy `run_data_quality_checks` trên `papers_clean.json`; artifact `data/quality/test_quality_report.json` ghi report thành công và baseline quality report có `success: true`.
- **Điều học được:** với `python -c`, cần tách rõ quoting của PowerShell và quoting của Python; ưu tiên `.format()` khi biểu thức phải truy cập key chuỗi.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref đến vector index:** `fetch_source_records` dùng snapshot/local source hoặc Crossref response, parse thành `PaperRecord`; `build_clean_dataframe` chuẩn hóa, de-duplicate theo `paper_id`, tạo `text_for_embedding`; `LocalEmbeddingIndex.build` embed bằng `sentence-transformers/all-MiniLM-L6-v2` và rebuild collection Chroma theo từng trạng thái.
2. **Evaluation set và ground truth:** `build_test_set` sort theo `paper_id`, tạo 10 câu dữ liệu thực cùng `ground_truth_doc_ids`. `evaluate_pipeline` đánh dấu retrieval hit khi một retrieved ID thuộc danh sách ground-truth ID, đo token F1 giữa đáp án và ground truth, và tổng hợp judge accuracy/score.
3. **Quality và freshness khác nhau:** quality kiểm tra row count, non-null field, uniqueness `paper_id`, độ dài summary bằng Great Expectations. Freshness tính `age_days`, stale rows/ratio và SLA với ngưỡng 180 ngày; report hiện tại coi dữ liệu fresh khi stale ratio không quá 25%.
4. **Cùng test set cho ba trạng thái:** đây là control để thay đổi metric được quy về thay đổi corpus/index do corruption hoặc repair, không bị nhiễu bởi câu hỏi/ground truth khác nhau.
5. **Repair thành công:** pipeline rebuild repaired data từ `data/raw/crossref_records.json`, không vá dataframe corrupted. Thành công được chứng minh bởi 24 records, quality 7/7 PASS, freshness 1/24 stale (4.2%) PASS, và metrics evaluation trở lại hit rate/F1/judge accuracy 1.0. Đây là kết quả của flow chung; không phải hạng mục B2 tôi nhận ownership.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0 | 0.6 | 1.0 | Corruption làm mất 4/10 retrieval hits; rebuild phục hồi hoàn toàn. |
| `mean_token_f1` | 1.0 | 0.579 | 1.0 | Đáp án suy giảm rõ dù không phải mọi câu đều miss retrieval. |
| `judge_accuracy` | 1.0 | 0.6 | 1.0 | Kết quả judge cùng chiều với retrieval hit rate. |
| `mean_judge_score` | 5.0 | 3.2 | 5.0 | Chất lượng câu trả lời giảm từ mức tối đa xuống 3.2/5 rồi phục hồi. |
| Quality checks | PASS, 7/7 | FAIL, 5/7 | PASS, 7/7 | Duplicate `paper_id` và summary rỗng làm fail hai expectation của Corrupted. |
| Freshness status | PASS, 1/24 stale (4.2%) | FAIL, 9/23 stale (39.1%) | PASS, 1/24 stale (4.2%) | Corrupted vượt SLA stale ratio 25%; dashboard biểu diễn trực quan khác biệt này. |

### Kết luận từ số liệu

1. `drop_latest_records`, summary corruption, stale date và duplicate rows → quality từ 7/7 xuống 5/7 và freshness từ 4.2% stale lên 39.1% → retrieval hit rate từ 100% xuống 60%, token F1 từ 1.0 xuống khoảng 0.579.
2. Rebuild từ raw snapshot → quality/freshness phục hồi PASS → retrieval hit rate, token F1 và judge accuracy đều trở lại 1.0.

Ảnh hưởng rõ nhất đến observability là tổ hợp stale-date và duplicate/blank-summary: stale-date đẩy 7 bản ghi lùi 730 ngày, còn blank summary và duplicate rows làm fail hai data-quality expectation. Đây cũng giải thích vì sao dashboard phải hiển thị cả quality lẫn freshness thay vì chỉ một metric RAG.

Một điểm cần thận trọng là Ragas không có giá trị chạy trong các metrics hiện tại; artifact ghi rõ `Set RUN_RAGAS=1 to enable the slower Ragas pass.` Vì vậy báo cáo chỉ kết luận dựa trên các metric đã có giá trị thật, không suy diễn kết quả Ragas.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Cleaning phải tạo schema nhất quán, đặc biệt `text_for_embedding` và `age_days`, trước khi index hoặc giám sát downstream.
2. Benchmark xác định với ground-truth document ID là điều kiện để so sánh công bằng chất lượng retrieval qua nhiều phiên bản corpus.
3. Quality gate và freshness monitor đo hai loại rủi ro khác nhau; dashboard chỉ là cách bổ trợ để đọc chung các tín hiệu và cho thấy ảnh hưởng của data corruption đến RAG.

### Nếu có thêm thời gian

Tôi sẽ thêm test tự động cho các hàm đọc artifact của dashboard: fixture thiếu JSON, JSON sai format và dataframe thiếu `age_days`. Tiêu chí đo là app không phát exception, hiển thị đúng file thiếu và vẫn render được các trạng thái còn hợp lệ. Tôi cũng sẽ bổ sung một control để người dùng chọn phiên bản artifact hoặc khoảng thời gian run khi lịch sử runs được lưu nhiều hơn một lần.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Gia Thành
**Ngày xác nhận:** 2026-09-26
